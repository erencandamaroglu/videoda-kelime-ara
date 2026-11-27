"""README ekran görüntüleri: gerçek veriye dokunmadan, geçici örnek veritabanı ve ayarlarla.
Kullanım: python ekran_goruntusu.py <proje_kok> <tr|en> <cikti_klasoru>"""
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

kok, dil, cikti = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
sys.path.insert(0, str(kok))
cikti.mkdir(parents=True, exist_ok=True)

from PyQt6.QtCore import QSettings  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

uygulama = QApplication(sys.argv)
uygulama.setStyle('Fusion')

from arsiv.ceviri import dil_ayarla  # noqa: E402
dil_ayarla(dil)
from arsiv import arayuz  # noqa: E402
from arsiv.veritabani import altyaziyi_kaydet, baglan, kokleri_ekle  # noqa: E402

gecici = Path(tempfile.mkdtemp())
db_yolu, ini_yolu = gecici / 'ornek.sqlite3', gecici / 'ayarlar.ini'

KOKLER = [r'D:\Arşiv\Belgeseller', r'D:\Arşiv\Röportajlar', r'D:\Arşiv\Konferanslar']
VIDEOLAR = [
    (KOKLER[0] + r'\Doğa ve İnsan 01.mp4', 1520, 'small', [
        (12.4, 16.8, 'Hayat burada, nehrin kıyısında başlıyor.'),
        (95.0, 99.2, 'Her mevsim yeni bir hayat döngüsü getiriyor.'),
        (410.5, 414.0, 'Bu topraklarda hayatta kalmak sabır ister.')]),
    (KOKLER[0] + r'\Doğa ve İnsan 02.mp4', 1610, 'small', [
        (44.0, 48.1, 'Kuşların göç yolu binlerce kilometre sürüyor.'),
        (233.2, 237.9, 'Göçmen kuşlar için hayat, yolculuktan ibaret.')]),
    (KOKLER[0] + r'\Şehirler\Eski İstanbul.mkv', 2890, 'large-v3', [
        (61.0, 65.5, 'İstanbul’un sokaklarında hayat hiç durmaz.'),
        (802.3, 806.0, 'Çarşının sesi, şehrin kalp atışıdır.')]),
    (KOKLER[1] + r'\Usta ile Sohbet.mp4', 940, 'large-v3', [
        (20.2, 24.0, 'Bu mesleği babamdan öğrendim.'),
        (318.6, 323.1, 'Zanaat, sabırla geçen bir hayatın ürünüdür.')]),
    (KOKLER[1] + r'\Köy Hayatı.mov', 1275, 'large-v3', [
        (5.5, 9.0, 'Sabah ezanıyla birlikte hayat başlar köyde.'),
        (600.0, 604.4, 'Ekmeği kendi fırınımızda pişiririz.')]),
    (KOKLER[2] + r'\Bilim Günleri 2026 - Açılış.mp4', 3600, 'large-v3', [
        (130.0, 134.6, 'Bilim, hayatımızın her alanına dokunuyor.'),
        (1801.0, 1805.2, 'Sorularınızı oturum sonunda alacağız.')]),
]

db = baglan(db_yolu)
for i, (yol, sure, model, satirlar) in enumerate(VIDEOLAR):
    durum = SimpleNamespace(st_size=int(sure * 1.9e6), st_mtime_ns=1_700_000_000_000_000_000 + i)
    altyaziyi_kaydet(db, yol, durum, model, 'tr', satirlar,
                     {'duration': sure, 'codec': 'h264', 'width': 1920, 'height': 1080, 'md5': __import__('hashlib').md5(yol.encode()).hexdigest()})
kokleri_ekle(db, KOKLER)

ayar = QSettings(str(ini_yolu), QSettings.Format.IniFormat)
ayar.setValue('folders/paths', '\n'.join(KOKLER))
ayar.setValue('scan/model', 'large-v3')
ayar.setValue('search/thumbnails', False)
ayar.setValue('schedule/enabled', True)
ayar.setValue('schedule/start', '20:00')
ayar.setValue('schedule/end', '07:00')
ayar.sync()

with patch.object(arayuz, 'baglan', lambda: db), patch.object(arayuz, 'AYARLAR', ini_yolu), \
        patch.object(arayuz, 'gpu_durumu', lambda: (True, arayuz._t('{sayi} NVIDIA GPU kullanıma hazır.', sayi=1))):
    p = arayuz.AnaPencere()
    p.taramayi_baslat = lambda otomatik=False: False  # zamanlayıcı gerçek tarama başlatmasın
    p.resize(1280, 760)
    p.kokleri_yenile()
    p.zamanlayici_tik()

    # Klasör tarama: örnek bir tarama ortası
    p.tarama_satirlari, p.oge_etkin, p.ilerleme_sayilari = {}, False, None
    yeni = [(KOKLER[2] + rf'\Bilim Günleri 2026 - Oturum {n}.mp4', int(s * 1.9e6), s)
            for n, s in [(1, 2710), (2, 3120), (3, 2480), (4, 2950), (5, 1830), (6, 2240)]]
    p.ogeler_kuyrukta(yeni, 'Altyazı')
    for yol, _boyut, _sure in yeni[:3]:
        p.oge_basladi(yol, 'Altyazı')
        p.oge_cubugu.setValue(100)
        p.oge_bitti('Tamamlandı', '')
    for satir, gecen in zip(range(3), ('3:41', '4:12', '3:18')):
        p.tarama_listesi.item(satir, arayuz.SUTUN_GECEN).setText(gecen)
    p.oge_basladi(yeni[3][0], 'Altyazı')
    p.oge_cubugu.setValue(46)
    p.tarama_listesi.item(3, arayuz.SUTUN_GECEN).setText('1:52')
    p.asamayi_guncelle('Altyazı oluşturuluyor', len(yeni))
    p.ilerlemeyi_guncelle(3, len(yeni))
    p.icerik_ilerleme = (8310 + 1357, sum(s for _y, _b, s in yeni))
    p.ilerlemeyi_goster()
    p.durum.setText(arayuz._t('{ad}: {mevcut} / {toplam} video', ad=arayuz._t('Altyazı oluşturuluyor'), mevcut=3, toplam=6)
                    + arayuz._t(' • Tahmini kalan: {kalan} • Tahmini bitiş: {bitis}', kalan=arayuz.sure_metni(1460), bitis='21:47'))
    for satir in [arayuz._t('{bulunan} video bulundu: {atlanan} önceden işlenmiş, {bekleyen} işlenecek.', bulunan=12, atlanan=6, bekleyen=6)]:
        p.gunluk.appendPlainText(satir)

    def kaydet(sekme, ad):
        p.sekmeler.setCurrentIndex(sekme)
        uygulama.processEvents()
        p.grab().save(str(cikti / f'{dil}_{ad}.png'))

    kaydet(0, 'tarama')
    p.sorgu.setText('hayat')
    p.bul()
    p.tablo.selectRow(0)
    kaydet(1, 'arama')
    kaydet(2, 'liste')
    kaydet(3, 'ayarlar')
    p.onizleme_yukleyici.durdur()
print('tamam', dil)
