"""SQLite arşivi: videolar, altyazı satırları ve FTS5 arama dizini.

Tablo ve sütun adları (videos, segments, path, duration...) mevcut veritabanıyla uyum için İngilizce kalır."""
import os
import re
import sqlite3
import unicodedata
from pathlib import Path

from .yollar import VERITABANI

INDEKS_SURUMU = 1
# Taramada okunan dosya bilgileri; eski veritabanlarına bu sütunlar sonradan eklenir.
BILGI_SUTUNLARI = {'format': 'TEXT', 'duration': 'REAL', 'codec': 'TEXT', 'width': 'INTEGER',
                   'height': 'INTEGER', 'md5': 'TEXT'}
LISTE_SIRASI = {'yol': 'v.path COLLATE NOCASE', 'tur': 'v.format', 'sure': 'v.duration', 'boyut': 'v.size',
                'cozunurluk': 'v.width*v.height', 'satir': 'satir', 'model': 'v.model', 'md5': 'v.md5'}


def sadelestir(metin):
    """Türkçe karakterler sadeleştirilir: ı/I/İ -> i, ş -> s, ç -> c, ğ -> g, ö -> o, ü -> u.
    Böylece "dusunurse" ile "DÜŞÜNÜRSE" aynı şekilde eşleşir."""
    metin = unicodedata.normalize('NFD', metin.replace('ı', 'i').replace('I', 'i').lower())
    return ''.join(c for c in metin if not unicodedata.combining(c))


def dosya_turu(yol):
    return os.path.splitext(yol)[1].lstrip('.').upper()


def kok_oneki(kok):
    kok = os.path.abspath(str(kok).strip().strip('"'))
    return kok if kok.endswith(os.sep) else kok + os.sep


def baglan(yol=VERITABANI):
    Path(yol).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(yol, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.create_function('sadelestir', 1, sadelestir, deterministic=True)
    db.create_function('yol_anahtari', 1, os.path.normcase, deterministic=True)
    db.create_function('dosya_turu', 1, dosya_turu, deterministic=True)
    db.executescript('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY, path TEXT UNIQUE NOT NULL,
            size INTEGER NOT NULL, mtime INTEGER NOT NULL,
            status TEXT NOT NULL, error TEXT, model TEXT, language TEXT);
        CREATE TABLE IF NOT EXISTS segments (
            id INTEGER PRIMARY KEY, video_id INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
            start REAL NOT NULL, end REAL NOT NULL, text TEXT NOT NULL);
        CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(text, tokenize='unicode61 remove_diacritics 0');
        CREATE INDEX IF NOT EXISTS segments_video ON segments(video_id);
        CREATE TABLE IF NOT EXISTS scan_roots (path TEXT PRIMARY KEY);
    ''')
    # Model/dil listesi tüm tabloyu taramasın (ağ sürücüsünde ~20 sn). İlk açılışta bir kez oluşturulur.
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='index' AND name='videos_model_dil'").fetchone():
        with db:
            db.execute('CREATE INDEX videos_model_dil ON videos(model, language)')
    sutunlar = {satir[1] for satir in db.execute('PRAGMA table_info(videos)')}
    eksik = [ad for ad in BILGI_SUTUNLARI if ad not in sutunlar]
    if eksik:
        with db:
            for ad in eksik:
                db.execute(f'ALTER TABLE videos ADD COLUMN {ad} {BILGI_SUTUNLARI[ad]}')
            if 'format' in eksik:
                db.execute('UPDATE videos SET format=dosya_turu(path)')
    if db.execute('PRAGMA user_version').fetchone()[0] < INDEKS_SURUMU:
        with db:
            db.execute('DELETE FROM search_index')
            db.execute('INSERT INTO search_index(rowid,text) SELECT id,sadelestir(text) FROM segments')
            db.execute(f'PRAGMA user_version={INDEKS_SURUMU}')
    return db


def kokleri_ekle(db, kokler):
    with db:
        db.executemany('INSERT OR IGNORE INTO scan_roots(path) VALUES(?)', [(kok_oneki(k),) for k in kokler])


def kokleri_listele(db, ek=()):
    """Kaydı bulunan tarama klasörlerini (yol, video sayısı) olarak döndürür."""
    onekler = {s['path'] for s in db.execute('SELECT path FROM scan_roots')}
    onekler.update(kok_oneki(k) for k in ek)
    # Yollar tek seferde, tablodan değil küçük benzersiz yol dizininden okunur; her kök için ayrı tarama yapılmaz.
    yollar = [os.path.normcase(s[0]) for s in db.execute('SELECT path FROM videos')]
    sonuc = []
    for onek in sorted(onekler, key=str.lower):
        anahtar = os.path.normcase(onek)
        sayi = sum(1 for yol in yollar if yol.startswith(anahtar))
        if sayi:
            sonuc.append((onek.rstrip(os.sep) if len(onek) > 3 else onek, sayi))
    return sonuc


def altyaziyi_kaydet(db, yol, durum, model, dil, satirlar, bilgi=None):
    """durum: os.stat sonucu. bilgi: incele() sonucu ve 'md5'; eksik anahtarlar boş kalır, sonraki taramada tamamlanır."""
    bilgi = bilgi or {}
    degerler = [bilgi.get(ad) for ad in BILGI_SUTUNLARI if ad != 'format']
    with db:
        db.execute('''INSERT INTO videos(path,size,mtime,status,model,language,format,duration,codec,width,height,md5)
            VALUES(?,?,?,'done',?,?,?,?,?,?,?,?)
            ON CONFLICT(path) DO UPDATE SET size=excluded.size,mtime=excluded.mtime,
            status='done',error=NULL,model=excluded.model,language=excluded.language,format=excluded.format,
            duration=excluded.duration,codec=excluded.codec,width=excluded.width,height=excluded.height,
            md5=excluded.md5''',
            (str(yol), durum.st_size, durum.st_mtime_ns, model, dil, dosya_turu(str(yol)), *degerler))
        video_id = db.execute('SELECT id FROM videos WHERE path=?', (str(yol),)).fetchone()[0]
        db.execute('DELETE FROM search_index WHERE rowid IN (SELECT id FROM segments WHERE video_id=?)', (video_id,))
        db.execute('DELETE FROM segments WHERE video_id=?', (video_id,))
        for bas, bit, metin in satirlar:
            imlec = db.execute('INSERT INTO segments(video_id,start,end,text) VALUES(?,?,?,?)', (video_id, bas, bit, metin))
            db.execute('INSERT INTO search_index(rowid,text) VALUES(?,?)', (imlec.lastrowid, sadelestir(metin)))


def bilgiyi_guncelle(db, video_id, bilgi):
    adlar = [ad for ad in BILGI_SUTUNLARI if ad in bilgi]
    if adlar:
        with db:
            db.execute(f"UPDATE videos SET {','.join(ad + '=?' for ad in adlar)} WHERE id=?",
                       (*[bilgi[ad] for ad in adlar], video_id))


def yolu_guncelle(db, video_id, yol, durum):
    """Kaydı yeni dosya yoluna bağlar; altyazı korunur. Boyut değiştiyse MD5 ve süre yeniden okunmak üzere boşaltılır."""
    with db:
        db.execute("""UPDATE videos SET md5=CASE WHEN size=? THEN md5 END, duration=CASE WHEN size=? THEN duration END,
            path=?,size=?,mtime=?,format=? WHERE id=?""",
            (durum.st_size, durum.st_size, str(yol), durum.st_size, durum.st_mtime_ns, dosya_turu(str(yol)), video_id))


def videolari_sil(db, kimlikler):
    kimlikler = list(kimlikler)
    with db:
        for i in range(0, len(kimlikler), 500):
            parca = kimlikler[i:i + 500]
            isaretler = ','.join('?' * len(parca))
            db.execute(f'DELETE FROM search_index WHERE rowid IN (SELECT id FROM segments WHERE video_id IN ({isaretler}))', parca)
            db.execute(f'DELETE FROM videos WHERE id IN ({isaretler})', parca)


def video_kosullari(kokler=None, sure=(None, None), boyut=(None, None)):
    """Klasör, süre (saniye) ve boyut (bayt) koşulları; None olan sınır uygulanmaz.
    Süresi henüz okunmamış videolar süre sınırı varken dışarıda kalır."""
    kosullar, parametreler = [], []
    onekler = [kok_oneki(k) for k in (kokler or ())]
    if onekler:
        kosullar.append('(' + ' OR '.join(['yol_anahtari(substr(v.path,1,?))=yol_anahtari(?)'] * len(onekler)) + ')')
        for onek in onekler:
            parametreler += [len(onek), onek]
    for sutun, (alt, ust) in (('duration', sure), ('size', boyut)):
        if alt is not None:
            kosullar.append(f'v.{sutun}>=?')
            parametreler.append(alt)
        if ust is not None:
            kosullar.append(f'v.{sutun}<=?')
            parametreler.append(ust)
    return kosullar, parametreler


def liste_filtresi(kokler, ad, sure, boyut, model):
    """model: (model, dil) çifti veya None."""
    kosullar, parametreler = video_kosullari(kokler, sure, boyut)
    if sadelestir(ad.strip()):
        kosullar.append('instr(sadelestir(v.path),?)>0')
        parametreler.append(sadelestir(ad.strip()))
    if model:
        kosullar.append('v.model IS ? AND v.language IS ?')
        parametreler += list(model)
    return (' WHERE ' + ' AND '.join(kosullar) if kosullar else ''), parametreler


def videolari_listele(db, kokler=None, ad='', sure=(None, None), boyut=(None, None), model=None,
                      sira='yol', azalan=False, sinir=100, atla=0):
    """Sayfalı video listesi: (toplam sayı, satırlar). ad yolun herhangi bir yerinde aranır.
    Satırlarda altyazı satır sayısı 'satir' sütunundadır."""
    nerede, parametreler = liste_filtresi(kokler, ad, sure, boyut, model)
    toplam = db.execute('SELECT count(*) FROM videos v' + nerede, parametreler).fetchone()[0]
    satirlar = db.execute(f'''SELECT v.*,(SELECT count(*) FROM segments s WHERE s.video_id=v.id) AS satir
        FROM videos v{nerede} ORDER BY {LISTE_SIRASI[sira]} {'DESC' if azalan else 'ASC'}, v.path COLLATE NOCASE
        LIMIT ? OFFSET ?''', (*parametreler, sinir, atla)).fetchall()
    return toplam, satirlar


def video_yollari(db, kokler=None, ad='', sure=(None, None), boyut=(None, None), model=None):
    """videolari_listele ile aynı filtrelere uyan tüm videoların yolları (sayfa sınırı olmadan)."""
    nerede, parametreler = liste_filtresi(kokler, ad, sure, boyut, model)
    return [satir[0] for satir in db.execute('SELECT v.path FROM videos v' + nerede, parametreler)]


def modelleri_listele(db):
    """Kayıtlardaki (model, dil, video sayısı) birleşimleri."""
    return [tuple(satir) for satir in db.execute(
        'SELECT model,language,count(*) FROM videos GROUP BY model,language ORDER BY count(*) DESC')]


def ara(db, sorgu, sinir=1000, kokler=None, tam_kelime=False, kapsam='satir', sure=(None, None), boyut=(None, None)):
    """Kelimeleri ayrı ayrı arar. kapsam='satir': hepsi aynı altyazı satırında olmalı.
    kapsam='video': hepsi aynı videoda geçmeli (farklı satırlarda olabilir); bu videolarda
    kelimelerden herhangi birini içeren satırlar listelenir. tam_kelime=False iken kelime başı
    eşleşir ("hayat" -> "hayatımız"). kokler verilirse yalnızca bu klasörlerin altındaki videolar aranır.
    sure (saniye) ve boyut (bayt) (alt, üst) sınırlarıdır; None sınırsız demektir."""
    kelimeler = re.findall(r'\w+', sadelestir(sorgu))
    if not kelimeler:
        return []
    terimler = ['"' + kelime + '"' + ('' if tam_kelime else '*') for kelime in dict.fromkeys(kelimeler)]
    sql = """SELECT v.path,s.start,s.end,s.text FROM search_index f
        JOIN segments s ON s.id=f.rowid JOIN videos v ON v.id=s.video_id
        WHERE search_index MATCH ?"""
    if kapsam == 'video':
        parametreler = [' OR '.join(terimler)]
        if len(terimler) > 1:
            her_biri = """SELECT s.video_id FROM search_index f JOIN segments s ON s.id=f.rowid
                WHERE search_index MATCH ?"""
            sql += ' AND s.video_id IN (' + ' INTERSECT '.join([her_biri] * len(terimler)) + ')'
            parametreler += terimler
    else:
        parametreler = [' AND '.join(terimler)]
    kosullar, ek = video_kosullari(kokler, sure, boyut)
    sql += ''.join(' AND ' + k for k in kosullar)
    parametreler += ek
    return db.execute(sql + ' ORDER BY v.path,s.start LIMIT ?', (*parametreler, sinir)).fetchall()


def zaman_damgasi(saniye):
    ms = max(0, round(saniye * 1000))
    sa, ms = divmod(ms, 3600000)
    dk, ms = divmod(ms, 60000)
    sn, ms = divmod(ms, 1000)
    return f'{sa:02}:{dk:02}:{sn:02},{ms:03}'


def srt_aktar(satirlar, hedef):
    metin = '\n\n'.join(f'{i}\n{zaman_damgasi(a)} --> {zaman_damgasi(b)}\n{t}' for i, (a, b, t) in enumerate(satirlar, 1))
    hedef = Path(hedef)
    gecici = hedef.with_suffix(hedef.suffix + '.tmp')
    gecici.write_text(metin + '\n', encoding='utf-8-sig')
    gecici.replace(hedef)
