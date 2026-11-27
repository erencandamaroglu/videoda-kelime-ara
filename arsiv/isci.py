"""Arka plan işleri: klasör tarama + altyazı oluşturma (TaramaIscisi) ve kopuk bağ arama (BagIscisi)."""
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from .ceviri import _t
from .konusma import model_yukle
from .medya_bilgisi import dosya_md5, incele
from .sure_filtresi import SureFiltresi
from .veritabani import altyaziyi_kaydet, baglan, bilgiyi_guncelle, kok_oneki, kokleri_ekle, yolu_guncelle

UZANTILAR = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.webm', '.m4v', '.mpeg', '.mpg', '.ts', '.mts', '.m2ts', '.flv',
             '.3gp', '.vob', '.ogv'}


def videolari_bul(kokler, durdu, gunluk):
    """{yol: (boyut, mtime_ns)} ve okunamayan klasör/dosyalar. Windows'ta boyut ve tarih dizin
    listesinden gelir; her dosya ayrıca açılmaz (ağ sürücüsünde belirgin hız farkı)."""
    dosyalar, okunamayan = {}, []
    for kok in kokler:
        yigin = [kok]
        while yigin:
            if durdu():
                return dosyalar, okunamayan
            klasor = yigin.pop()
            try:
                with os.scandir(klasor) as girdiler:
                    for girdi in girdiler:
                        try:
                            if girdi.is_dir() and not girdi.is_symlink() and not girdi.is_junction():
                                yigin.append(girdi.path)
                            elif os.path.splitext(girdi.name)[1].lower() in UZANTILAR and girdi.is_file():
                                durum = girdi.stat()
                                dosyalar[os.path.abspath(girdi.path)] = (durum.st_size, durum.st_mtime_ns)
                        except OSError as hata:
                            gunluk(str(hata))
                            okunamayan.append(girdi.path)
            except OSError as hata:
                gunluk(str(hata))
                okunamayan.append(klasor)
    return dosyalar, okunamayan


def ayri_kokler(kokler):
    """Başka bir kökün altında kalan klasörleri çıkarır; aynı klasör iki kez gezilmez."""
    onekler = [os.path.normcase(kok_oneki(k)) for k in kokler]
    sonuc = []
    for i, kok in enumerate(kokler):
        if onekler[i] in onekler[:i]:
            continue
        if not any(j != i and onekler[i] != diger and onekler[i].startswith(diger) for j, diger in enumerate(onekler)):
            sonuc.append(kok)
    return sonuc


def altinda(yol, onekler):
    anahtar = os.path.normcase(yol)
    return any(anahtar == o.rstrip(os.sep) or anahtar.startswith(o) for o in onekler)


def degismemis(boyut_tarih, yol, onbellek):
    """Dizin listesindeki bilgi farklıysa dosyanın kendisinden bir kez daha kontrol edilir."""
    if onbellek == boyut_tarih:
        return True
    try:
        durum = os.stat(yol)
    except OSError:
        return False
    return (durum.st_size, durum.st_mtime_ns) == boyut_tarih


def tasinanlari_bul(kayiplar, yeni_dosyalar, durdu=lambda: False):
    """Kopuk kayıtları kayıtsız dosyalarla eşler: {id: (yeni yol, neden, kesin mi)}.
    Kesin: MD5 aynı; MD5 yoksa boyut ve tarih aynı. Yalnızca kesin olanlar otomatik uygulanabilir."""
    boyuta_gore, ada_gore = defaultdict(list), defaultdict(list)
    for yol, onbellek in yeni_dosyalar.items():
        boyuta_gore[onbellek[0]].append(yol)
        ada_gore[os.path.normcase(os.path.basename(yol))].append(yol)
    ozetler, kullanilan, sonuc = {}, set(), {}

    def md5_degeri(yol):
        if yol not in ozetler:
            try:
                ozetler[yol] = dosya_md5(yol, durdu)
            except OSError:
                ozetler[yol] = None
        return ozetler[yol]

    for kayit in kayiplar:
        if durdu():
            break
        ad = os.path.normcase(os.path.basename(kayit['path']))
        ayni_boyut = [y for y in boyuta_gore.get(kayit['size'], ()) if y not in kullanilan]
        if kayit['md5']:
            kesin, neden = [y for y in ayni_boyut if md5_degeri(y) == kayit['md5']], _t('MD5 aynı')
        else:
            kesin = [y for y in ayni_boyut if degismemis((kayit['size'], kayit['mtime']), y, yeni_dosyalar[y])]
            neden = _t('Boyut ve tarih aynı')
        ayni_adli = [y for y in kesin if os.path.normcase(os.path.basename(y)) == ad]
        secim = ayni_adli if len(ayni_adli) == 1 else kesin
        if len(secim) == 1:
            sonuc[kayit['id']] = (secim[0], neden, True)
            kullanilan.add(secim[0])
        elif kesin:
            sonuc[kayit['id']] = (kesin[0], _t('{sayi} kopya var; biri seçildi', sayi=len(kesin)), False)
        elif ayni_boyut and not kayit['md5']:
            sonuc[kayit['id']] = (ayni_boyut[0], _t('Yalnızca boyut aynı'), False)
        elif len(ada_gore.get(ad, ())) == 1 and ada_gore[ad][0] not in kullanilan:
            sonuc[kayit['id']] = (ada_gore[ad][0], _t('Yalnızca ad aynı'), False)
    return sonuc


class BagIscisi(QThread):
    """Kopuk kayıtları bulur ve yeni yerlerini arar. kayiplar verilirse yalnızca verilen köklerde arama yapılır.
    bulundu sinyalindeki satırlar: veritabanı sütunları + 'yeni_yol', 'neden', 'kesin'."""
    asama = pyqtSignal(str)
    ilerleme = pyqtSignal(int, int)
    bulundu = pyqtSignal(list)
    hata = pyqtSignal(str)

    def __init__(self, klasorler=(), kayiplar=None, kokler=None):
        super().__init__()
        self.klasorler, self.kayiplar, self.arama_kokleri = list(klasorler), kayiplar, kokler

    def run(self):
        db = None
        try:
            db = baglan()
            kayitlar = [dict(s) for s in db.execute('SELECT id,path,size,mtime,md5,duration FROM videos ORDER BY path')]
            kayiplar = self.kayiplar if self.kayiplar is not None else self.kayiplari_bul(kayitlar)
            if not kayiplar or self.isInterruptionRequested():
                return
            self.bulundu.emit(kayiplar)
            kokler = self.arama_kokleri
            if kokler is None:
                kokler = [s['path'] for s in db.execute('SELECT path FROM scan_roots')] + self.klasorler
            kokler = ayri_kokler([k for k in kokler if os.path.isdir(k)])
            self.asama.emit(_t('{sayi} kopuk kayıt bulundu; yeni yerleri aranıyor (klasör taraması birkaç dakika sürebilir)...',
                               sayi=len(kayiplar)))
            self.ilerleme.emit(0, 0)
            dosyalar, _ = videolari_bul(kokler, self.isInterruptionRequested, lambda _: None)
            if self.isInterruptionRequested():
                return
            kayitli = {os.path.normcase(k['path']) for k in kayitlar}
            yeni_dosyalar = {y: o for y, o in dosyalar.items() if os.path.normcase(y) not in kayitli}
            tasinan = tasinanlari_bul(kayiplar, yeni_dosyalar, self.isInterruptionRequested)
            self.bulundu.emit([{**k, 'yeni_yol': tasinan[k['id']][0], 'neden': tasinan[k['id']][1], 'kesin': tasinan[k['id']][2]}
                               for k in kayiplar if k['id'] in tasinan])
        except Exception as hata:
            self.hata.emit(str(hata))
        finally:
            if db is not None:
                db.close()

    def kayiplari_bul(self, kayitlar):
        self.asama.emit(_t('{sayi} kaydın dosyası kontrol ediliyor...', sayi=len(kayitlar)))
        kayiplar = []
        with ThreadPoolExecutor(16) as havuz:
            for i, (kayit, var) in enumerate(zip(kayitlar, havuz.map(os.path.exists, [k['path'] for k in kayitlar])), 1):
                if self.isInterruptionRequested():
                    havuz.shutdown(cancel_futures=True)
                    break
                if not var:
                    kayiplar.append(kayit)
                if i % 100 == 0 or i == len(kayitlar):
                    self.ilerleme.emit(i, len(kayitlar))
        return kayiplar


class TaramaIscisi(QThread):
    gunluk = pyqtSignal(str)
    asama = pyqtSignal(str, int)
    ilerleme = pyqtSignal(int, int)
    ogeler_kuyrukta = pyqtSignal(list, str)
    icerik_ilerlemesi = pyqtSignal(float, float)
    oge_basladi = pyqtSignal(str, str)
    oge_ayrintisi = pyqtSignal(object, object)
    oge_ilerlemesi = pyqtSignal(int)
    oge_bitti = pyqtSignal(str, str)
    sonuc = pyqtSignal(str)

    def __init__(self, kokler, model, dil, yeniden=False, sure_filtresi=None, bilgi_tamamla=False,
                 birim='cpu', yollar=None):
        """yollar verilirse klasör taranmaz, yalnızca bu videolar işlenir (toplu yeniden işleme)."""
        super().__init__()
        self.kokler, self.model_adi, self.dil, self.yeniden = kokler, model, dil, yeniden
        self.sure_filtresi = sure_filtresi or SureFiltresi()
        self.bilgi_tamamla = bilgi_tamamla
        self.birim, self.yollar = birim, yollar
        self.yumusak_dur = False

    def mevcut_isi_bitir(self):
        """Yumuşak durdurma: işlenmekte olan video tamamlanır, sıradaki videolara geçilmez."""
        self.yumusak_dur = True

    def durmali(self):
        """Yeni bir videoya başlanmamalı mı? (Durdur düğmesi veya zamanlayıcının bitiş saati)"""
        return self.yumusak_dur or self.isInterruptionRequested()

    def run(self):
        db = None
        try:
            dosyalar, baglanan, kopuk = {}, 0, 0
            if self.yollar is not None:
                db = baglan()
                bekleyen = sorted(self.yollar)
                atlanan = 0
                self.gunluk.emit(_t('{sayi} video yeniden işlenecek.', sayi=len(bekleyen)))
            else:
                kokler = []
                for kok in self.kokler:
                    if Path(kok).is_dir():
                        kokler.append(kok)
                    else:
                        self.gunluk.emit(_t('Klasör bulunamadı: {kok}', kok=kok))
                self.asama.emit('Klasörler taranıyor', -1)
                dosyalar, okunamayan = videolari_bul(ayri_kokler(kokler), self.durmali, self.gunluk.emit)
                if self.durmali():
                    self.sonuc.emit(_t('Tarama durduruldu.'))
                    return
                db = baglan()
                kokleri_ekle(db, kokler)
                baglanan, kopuk = self.kopuklari_bagla(db, kokler, dosyalar, okunamayan)
                bilinen = {os.path.normcase(k['path']): k for k in db.execute('SELECT * FROM videos')}
                bekleyen = [d for d in sorted(dosyalar) if not self.guncel_mi(bilinen.get(os.path.normcase(d)), d, dosyalar[d])]
                atlanan = len(dosyalar) - len(bekleyen)
                self.gunluk.emit(_t('{bulunan} video bulundu: {atlanan} önceden işlenmiş, {bekleyen} işlenecek.',
                                    bulunan=len(dosyalar), atlanan=atlanan, bekleyen=len(bekleyen)))
            self.gunluk.emit(_t('Süre filtresi: {aciklama}', aciklama=self.sure_filtresi.aciklama()))
            bilinen = {os.path.normcase(k['path']): k for k in db.execute('SELECT path,size,duration FROM videos')}
            okunan = self.sureleri_oku(bekleyen, bilinen)
            ogeler = [self.kuyruk_ogesi(y, dosyalar, bilinen, okunan) for y in bekleyen]
            self.ogeler_kuyrukta.emit(ogeler, 'Altyazı')
            islenen, sure_disi, hatali = self.altyazi_olustur(db, bekleyen, okunan, {y: s for y, _, s in ogeler if s})
            tamamlanan = bilgi_hatasi = 0
            if self.bilgi_tamamla and not self.durmali():
                tamamlanan, bilgi_hatasi = self.eksik_bilgileri_tamamla(db, dosyalar)
            onek = _t('Durduruldu') if self.durmali() else _t('Tamamlandı')
            ozet = _t('{onek}: {islenen} işlendi, {atlanan} önceden işlenmiş, {sure_disi} süre dışı, {hatali} hata',
                      onek=onek, islenen=islenen, atlanan=atlanan, sure_disi=sure_disi, hatali=hatali)
            if baglanan:
                ozet += _t(', {sayi} bağ düzeltildi', sayi=baglanan)
            if kopuk:
                ozet += _t(', {sayi} kopuk kayıt (Video listesi > Kopuk bağları kontrol et)', sayi=kopuk)
            if tamamlanan or bilgi_hatasi:
                ozet += _t(', {sayi} videonun bilgisi tamamlandı', sayi=tamamlanan)
            if bilgi_hatasi:
                ozet += _t(', {sayi} bilgi okunamadı', sayi=bilgi_hatasi)
            self.sonuc.emit(ozet + '.')
        except Exception as hata:
            self.sonuc.emit(_t('İşlem başarısız: {hata}', hata=hata))
        finally:
            if db is not None:
                db.close()

    @staticmethod
    def kuyruk_ogesi(yol, dosyalar, bilinen, okunan):
        """(yol, boyut, süre): liste baştan tam gösterilsin diye. Süre önce dosyadan, yoksa kayıttan alınır."""
        eski = bilinen.get(os.path.normcase(yol))
        boyut = dosyalar[yol][0] if yol in dosyalar else (eski['size'] if eski else None)
        sure = okunan[yol]['duration'] if yol in okunan else (eski['duration'] if eski else None)
        return yol, boyut, sure

    def sureleri_oku(self, bekleyen, bilinen):
        """Süresi kayıtta olmayan videoların başlığını paralel okur: {yol: incele sonucu}. Okunamayanlar atlanır."""
        yapilacak = [y for y in bekleyen if not (bilinen.get(os.path.normcase(y)) and bilinen[os.path.normcase(y)]['duration'])]
        okunan = {}
        if not yapilacak:
            return okunan

        def oku(yol):
            if self.durmali():
                return None
            try:
                return incele(yol)
            except Exception:
                return None
        self.asama.emit('Video süreleri okunuyor', len(yapilacak))
        with ThreadPoolExecutor(8) as havuz:
            for i, (yol, bilgi) in enumerate(zip(yapilacak, havuz.map(oku, yapilacak)), 1):
                if bilgi:
                    okunan[yol] = bilgi
                self.ilerleme.emit(i, len(yapilacak))
        return okunan

    def guncel_mi(self, eski, yol, onbellek):
        if self.yeniden or not eski or eski['status'] != 'done':
            return False
        if eski['model'] != self.model_adi or eski['language'] != self.dil:
            return False
        return degismemis((eski['size'], eski['mtime']), yol, onbellek)

    def kopuklari_bagla(self, db, kokler, dosyalar, okunamayan):
        """Taşınan veya adı değişen videoların bağını kesin eşleşmede düzeltir; altyazı korunur, yeniden işlenmez.
        Eşleşmeyen kayıtlar silinmez, kopuk olarak bildirilir. Okunamayan klasörlerin altındakilere bakılmaz."""
        onekler = [os.path.normcase(kok_oneki(k)) for k in kokler]
        engelli = [os.path.normcase(kok_oneki(y)) for y in okunamayan]
        kayitlar = [dict(k) for k in db.execute('SELECT id,path,size,mtime,md5 FROM videos')]
        kayitli = {os.path.normcase(k['path']) for k in kayitlar}
        bulunan = {os.path.normcase(y) for y in dosyalar}
        kayiplar = [k for k in kayitlar if os.path.normcase(k['path']) not in bulunan and altinda(k['path'], onekler)
                    and not altinda(k['path'], engelli) and not os.path.exists(k['path'])]
        if not kayiplar:
            return 0, 0
        yeni_dosyalar = {y: o for y, o in dosyalar.items() if os.path.normcase(y) not in kayitli}
        tasinan = tasinanlari_bul(kayiplar, yeni_dosyalar, self.durmali)
        baglanan = 0
        for kayit in kayiplar:
            yol, _, kesin = tasinan.get(kayit['id'], (None, None, False))
            if kesin:
                yolu_guncelle(db, kayit['id'], yol, os.stat(yol))
                baglanan += 1
                self.gunluk.emit(_t('Bağ düzeltildi: {eski} -> {yeni}', eski=kayit['path'], yeni=yol))
            else:
                self.gunluk.emit(_t('Kopuk kayıt (dosya bulunamadı): {yol}', yol=kayit['path']))
        return baglanan, len(kayiplar) - baglanan

    def altyazi_olustur(self, db, bekleyen, okunan, sureler):
        """sureler: {yol: saniye}. İlerleme video adedine değil, işlenen içerik süresine göre bildirilir;
        süre dışı kalan ve hata veren videolar toplamdan düşülür, böylece hız hesabını şişirmez."""
        model = None
        islenen = sure_disi = hatali = 0
        toplam = len(bekleyen)
        filtreli = self.sure_filtresi.mod != 'tumu'
        icerik_toplami = sum(s for s in sureler.values() if not filtreli or self.sure_filtresi.kabul_eder(s))
        icerik_biten = 0.0
        self.asama.emit('Altyazı oluşturuluyor', toplam)
        for i, dosya_adi in enumerate(bekleyen, 1):
            if self.durmali():
                break
            self.ilerleme.emit(i - 1, toplam)
            yol = Path(dosya_adi)
            self.oge_basladi.emit(dosya_adi, 'Altyazı')
            durum_metni, not_ = 'Durduruldu', ''
            try:
                durum = yol.stat()
                try:
                    ayrinti = dict(okunan[dosya_adi]) if dosya_adi in okunan else incele(yol)
                except Exception as hata:
                    ayrinti = {}
                    self.gunluk.emit(_t('Video bilgileri okunamadı: {ad} ({hata})', ad=yol.name, hata=hata))
                self.oge_ayrintisi.emit(durum.st_size, ayrinti.get('duration'))
                if filtreli:
                    if ayrinti.get('duration') is None:
                        raise ValueError(_t('Video süresi okunamadı; süre filtresi açık olduğu için işlenmedi.'))
                    if not self.sure_filtresi.kabul_eder(ayrinti['duration']):
                        sure_disi += 1
                        durum_metni = 'Süre dışı'
                        self.gunluk.emit(_t('Süre nedeniyle atlandı: {ad} ({dk} dk)', ad=yol.name, dk=f'{ayrinti["duration"] / 60:.2f}'))
                        continue
                if model is None:
                    self.gunluk.emit(_t('Konuşma modeli yükleniyor; ilk kullanımda internetten indirilir...'))
                    model = model_yukle(self.model_adi, self.birim, self.gunluk.emit)
                self.gunluk.emit(_t('[{i}/{toplam}] İşleniyor: {dosya}', i=i, toplam=toplam, dosya=dosya_adi))
                akis, bilgi = model.transcribe(dosya_adi, language=None if self.dil == 'auto' else self.dil,
                                               vad_filter=True, beam_size=5)
                satirlar = []
                son_bildirim = -30
                for parca in akis:
                    if self.isInterruptionRequested():
                        break
                    satirlar.append((parca.start, parca.end, parca.text.strip()))
                    if bilgi.duration:
                        self.oge_ilerlemesi.emit(min(99, int(parca.end * 100 / bilgi.duration)))
                    self.icerik_ilerlemesi.emit(icerik_biten + min(parca.end, sureler.get(dosya_adi, 0)), icerik_toplami)
                    if parca.end - son_bildirim >= 30:
                        self.gunluk.emit(_t('  {ad}: {sn} / {toplam} saniye', ad=yol.name, sn=f'{parca.end:.0f}', toplam=f'{bilgi.duration:.0f}'))
                        son_bildirim = parca.end
                if self.isInterruptionRequested():
                    break
                ayrinti['md5'] = dosya_md5(yol, self.isInterruptionRequested)
                if self.isInterruptionRequested():
                    break
                sonra = yol.stat()
                if (sonra.st_size, sonra.st_mtime_ns) != (durum.st_size, durum.st_mtime_ns):
                    raise RuntimeError(_t('Video işlem sırasında değişti; yeniden tarayın.'))
                altyaziyi_kaydet(db, yol, durum, self.model_adi, self.dil, satirlar, ayrinti)
                islenen += 1
                durum_metni = 'Tamamlandı'
                self.gunluk.emit(_t('Kaydedildi: {ad} ({sayi} altyazı satırı)', ad=yol.name, sayi=len(satirlar)))
            except Exception as hata:
                hatali += 1
                durum_metni, not_ = 'Hata', str(hata)
                self.gunluk.emit(_t('HATA — {dosya}: {hata}', dosya=dosya_adi, hata=hata))
            finally:
                self.oge_bitti.emit(durum_metni, not_)
                self.ilerleme.emit(i, toplam)
                agirlik = sureler.get(dosya_adi, 0)
                if durum_metni == 'Tamamlandı':
                    icerik_biten += agirlik
                elif durum_metni == 'Hata':
                    icerik_toplami -= agirlik
                self.icerik_ilerlemesi.emit(icerik_biten, icerik_toplami)
        if not self.durmali():
            self.ilerleme.emit(toplam, toplam)
        return islenen, sure_disi, hatali

    def eksik_bilgileri_tamamla(self, db, dosyalar):
        """Önceden işlenmiş videoların eksik süre/tür/çözünürlük ve MD5 değerlerini tamamlar.
        Önce hızlı olan başlık bilgileri, sonra dosyanın tamamını okuyan MD5 hesaplanır."""
        bulunan = {os.path.normcase(y): (y, o) for y, o in dosyalar.items()}
        kayitlar = []
        for kayit in db.execute("SELECT id,path,size,mtime,duration,md5 FROM videos WHERE status='done' "
                                "AND (duration IS NULL OR md5 IS NULL) ORDER BY path"):
            yol, onbellek = bulunan.get(os.path.normcase(kayit['path']), (None, None))
            if yol and degismemis((kayit['size'], kayit['mtime']), yol, onbellek):
                kayitlar.append(kayit)
        tamamlanan, hatali = set(), 0
        sureler = {k['id']: k['duration'] for k in kayitlar}
        for ad, md5_turu, yapilacak in (('Video bilgileri okunuyor', False, [k for k in kayitlar if k['duration'] is None]),
                                        ('MD5 hesaplanıyor', True, [k for k in kayitlar if k['md5'] is None])):
            if self.durmali():
                break
            self.gunluk.emit(_t('{ad}: {sayi} video.', ad=_t(ad), sayi=len(yapilacak)))
            self.asama.emit(ad, len(yapilacak))
            if md5_turu:
                self.ogeler_kuyrukta.emit([(k['path'], k['size'], sureler[k['id']]) for k in yapilacak], 'MD5')
            for i, kayit in enumerate(yapilacak, 1):
                if self.durmali():
                    break
                self.ilerleme.emit(i - 1, len(yapilacak))
                try:
                    if not md5_turu:
                        bilgi = incele(kayit['path'])
                        sureler[kayit['id']] = bilgi['duration']
                        bilgiyi_guncelle(db, kayit['id'], bilgi)
                    else:
                        self.gunluk.emit(f'[{i}/{len(yapilacak)}] MD5: {kayit["path"]}')
                        self.oge_basladi.emit(kayit['path'], 'MD5')
                        self.oge_ayrintisi.emit(kayit['size'], sureler[kayit['id']])
                        durum_metni, not_ = 'Durduruldu', ''
                        try:
                            md5 = dosya_md5(kayit['path'], self.isInterruptionRequested,
                                            lambda okunan: self.oge_ilerlemesi.emit(int(okunan * 100 / max(1, kayit['size']))))
                            if md5 is None:
                                break
                            durum_metni = 'Tamamlandı'
                        except Exception as hata:
                            durum_metni, not_ = 'Hata', str(hata)
                            raise
                        finally:
                            self.oge_bitti.emit(durum_metni, not_)
                        durum = os.stat(kayit['path'])
                        if (durum.st_size, durum.st_mtime_ns) != (kayit['size'], kayit['mtime']):
                            raise RuntimeError(_t('Video değişmiş; bir sonraki taramada yeniden işlenecek.'))
                        bilgiyi_guncelle(db, kayit['id'], {'md5': md5})
                    tamamlanan.add(kayit['id'])
                except Exception as hata:
                    hatali += 1
                    self.gunluk.emit(_t('Bilgi okunamadı — {yol}: {hata}', yol=kayit['path'], hata=hata))
                finally:
                    self.ilerleme.emit(i, len(yapilacak))
        return len(tamamlanan), hatali
