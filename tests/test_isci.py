import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

# patch.dict('sys.modules') bağlam dışında yeni yüklenen modülleri siler; numpy ikinci kez yüklenemediği için
# testlerden önce bir kez yüklenir (model_yukle numpy'yi kendi içinde içe aktarır).
import numpy  # noqa: F401

from arsiv.isci import BagIscisi, TaramaIscisi, ayri_kokler, tasinanlari_bul
from arsiv.konusma import model_yukle
from arsiv.sure_filtresi import SureFiltresi
from arsiv.veritabani import altyaziyi_kaydet, ara, baglan, kokleri_ekle, yolu_guncelle


def sahte_model(*_args, **_kwargs):
    model = Mock()
    model.transcribe.return_value = ([SimpleNamespace(start=0, end=1, text=' merhaba dünya')], SimpleNamespace(duration=1))
    return model


def sahte_whisper(model_uretici=sahte_model):
    return patch.dict('sys.modules', {'faster_whisper': SimpleNamespace(WhisperModel=Mock(side_effect=model_uretici))})


class TaramaTestleri(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.TemporaryDirectory()
        self.kok = Path(self.gecici.name) / 'videolar'
        self.kok.mkdir()
        self.db_yolu = Path(self.gecici.name) / 'test.sqlite3'

    def tearDown(self):
        self.gecici.cleanup()

    def veritabani(self):
        return patch('arsiv.isci.baglan', side_effect=lambda: baglan(self.db_yolu))

    def isciyi_calistir(self, **secenekler):
        isci = TaramaIscisi([str(self.kok)], 'small', 'tr', **secenekler)
        sonuclar, asamalar, gunluk = [], [], []
        isci.sonuc.connect(sonuclar.append)
        isci.asama.connect(lambda ad, toplam: asamalar.append((ad, toplam)))
        isci.gunluk.connect(gunluk.append)
        bilgi = {'duration': 75.5, 'codec': 'h264', 'width': 1920, 'height': 1080}
        with self.veritabani(), patch('arsiv.isci.incele', return_value=dict(bilgi)), sahte_whisper():
            isci.run()
        return sonuclar[-1], dict(asamalar), gunluk

    def adlar(self):
        db = baglan(self.db_yolu)
        adlar = {Path(k['path']).name: k['model'] for k in db.execute('SELECT path,model FROM videos')}
        db.close()
        return adlar

    def test_yalnizca_yeni_videolar_sayilir_ve_bilgileri_kaydedilir(self):
        for ad in ('a.mp4', 'b.mkv'):
            (self.kok / ad).write_bytes(ad.encode())
        sonuc, asamalar, _ = self.isciyi_calistir()
        self.assertEqual(asamalar['Altyazı oluşturuluyor'], 2)
        self.assertIn('2 işlendi', sonuc)
        (self.kok / 'c.mp4').write_bytes(b'yeni')
        sonuc, asamalar, gunluk = self.isciyi_calistir()
        self.assertEqual(asamalar['Altyazı oluşturuluyor'], 1)
        self.assertIn('1 işlendi, 2 önceden işlenmiş', sonuc)
        self.assertIn('3 video bulundu: 2 önceden işlenmiş, 1 işlenecek.', gunluk)
        db = baglan(self.db_yolu)
        kayit = db.execute("SELECT * FROM videos WHERE path LIKE '%b.mkv'").fetchone()
        self.assertEqual((kayit['format'], kayit['duration'], kayit['width'], kayit['codec']), ('MKV', 75.5, 1920, 'h264'))
        self.assertEqual(kayit['md5'], hashlib.md5(b'b.mkv').hexdigest())
        db.close()

    def test_eslesmeyen_kayiplar_bildirilir_silinmez(self):
        (self.kok / 'kalan.mp4').write_bytes(b'1')
        (self.kok / 'silinen.mp4').write_bytes(b'22')
        self.isciyi_calistir()
        (self.kok / 'silinen.mp4').unlink()
        sonuc, _, _ = self.isciyi_calistir()
        self.assertIn('1 kopuk kayıt', sonuc)
        self.assertEqual(sorted(self.adlar()), ['kalan.mp4', 'silinen.mp4'])
        db = baglan(self.db_yolu)
        self.assertEqual(len(ara(db, 'merhaba')), 2)
        db.close()

    def test_adi_degisen_ve_tasinan_dosyalar_altyazisini_korur(self):
        (self.kok / 'eski.mp4').write_bytes(b'video bir')
        (self.kok / 'tasinan.mp4').write_bytes(b'video iki!')
        self.isciyi_calistir()
        (self.kok / 'yeni').mkdir()
        (self.kok / 'eski.mp4').rename(self.kok / 'yeni ad.mp4')
        (self.kok / 'tasinan.mp4').rename(self.kok / 'yeni' / 'tasinan.mp4')
        os.utime(self.kok / 'yeni ad.mp4', (1000, 1000))  # tarih değişse de MD5 eşleşir
        sonuc, asamalar, _ = self.isciyi_calistir()
        self.assertIn('2 bağ düzeltildi', sonuc)
        self.assertEqual(asamalar['Altyazı oluşturuluyor'], 0)  # MD5 aynıysa yeni tarihle kaydedilir, yeniden işlenmez
        self.assertEqual(sorted(self.adlar()), ['tasinan.mp4', 'yeni ad.mp4'])

    def test_md5_olmayan_kayit_ayni_boyut_ve_tarih_ister(self):
        video = self.kok / 'a.mp4'
        video.write_bytes(b'12345')
        db = baglan(self.db_yolu)
        altyaziyi_kaydet(db, video, video.stat(), 'small', 'tr', [(0, 1, 'metin')])
        kayitlar = [dict(k) for k in db.execute('SELECT id,path,size,mtime,md5 FROM videos')]
        db.close()
        boyut, tarih = kayitlar[0]['size'], kayitlar[0]['mtime']
        diger = str(self.kok / 'b.mp4')
        self.assertEqual(tasinanlari_bul(kayitlar, {diger: (boyut, tarih)})[kayitlar[0]['id']], (diger, 'Boyut ve tarih aynı', True))
        with patch('arsiv.isci.os.stat', side_effect=OSError):
            self.assertFalse(tasinanlari_bul(kayitlar, {diger: (boyut, tarih + 1)})[kayitlar[0]['id']][2])
        self.assertEqual(tasinanlari_bul(kayitlar, {diger: (boyut + 1, tarih)}), {})
        ayni = str(self.kok / 'alt' / 'a.mp4')
        self.assertFalse(tasinanlari_bul(kayitlar, {ayni: (boyut + 1, tarih)})[kayitlar[0]['id']][2])

    def test_kopyalar_otomatik_baglanmaz(self):
        kayit = {'id': 1, 'path': str(self.kok / 'yok.mp4'), 'size': 5, 'mtime': 7, 'md5': None}
        dosyalar = {str(self.kok / 'k1.mp4'): (5, 7), str(self.kok / 'k2.mp4'): (5, 7)}
        self.assertFalse(tasinanlari_bul([kayit], dosyalar)[1][2])
        dosyalar[str(self.kok / 'yeni' / 'yok.mp4')] = (5, 7)  # aynı ad varsa o kopya seçilir
        self.assertEqual(tasinanlari_bul([kayit], dosyalar)[1], (str(self.kok / 'yeni' / 'yok.mp4'), 'Boyut ve tarih aynı', True))

    def test_bag_iscisi_kayiplari_onerilerle_bildirir(self):
        kalan = self.kok / 'kalan.mp4'
        kalan.write_bytes(b'1')
        kayip = self.kok / 'kayip.mp4'
        kayip.write_bytes(b'kayip video')
        db = baglan(self.db_yolu)
        for video in (kalan, kayip):
            altyaziyi_kaydet(db, video, video.stat(), 'small', 'tr', [(0, 1, 'metin')])
        kokleri_ekle(db, [self.kok])
        db.close()
        kayip.rename(self.kok / 'bulundu.mp4')
        isci = BagIscisi()
        bulunan = []
        isci.bulundu.connect(bulunan.append)
        with self.veritabani():
            isci.run()
        self.assertEqual([Path(k['path']).name for k in bulunan[0]], ['kayip.mp4'])
        self.assertEqual((Path(bulunan[1][0]['yeni_yol']).name, bulunan[1][0]['kesin']), ('bulundu.mp4', True))
        db = baglan(self.db_yolu)
        yolu_guncelle(db, bulunan[1][0]['id'], bulunan[1][0]['yeni_yol'], os.stat(bulunan[1][0]['yeni_yol']))
        self.assertEqual(len(ara(db, 'metin')), 2)
        db.close()
        self.assertEqual(sorted(self.adlar()), ['bulundu.mp4', 'kalan.mp4'])

    def test_okunamayan_klasor_temizlenmez(self):
        (self.kok / 'alt').mkdir()
        (self.kok / 'alt' / 'v.mp4').write_bytes(b'1')
        self.isciyi_calistir()
        gercek_scandir = os.scandir

        def hatali(yol):
            if str(yol).endswith('alt'):
                raise PermissionError('erişim yok')
            return gercek_scandir(yol)
        with patch('arsiv.isci.os.scandir', side_effect=hatali), patch('arsiv.isci.os.path.exists', return_value=False):
            sonuc, _, _ = self.isciyi_calistir()
        self.assertNotIn('kopuk', sonuc)

    def test_eksik_bilgiler_tamamlanir(self):
        video = self.kok / 'eski.mp4'
        video.write_bytes(b'eski video')
        db = baglan(self.db_yolu)
        altyaziyi_kaydet(db, video, video.stat(), 'small', 'tr', [(0, 1, 'metin')])
        db.close()
        sonuc, asamalar, _ = self.isciyi_calistir(bilgi_tamamla=True)
        self.assertEqual(asamalar['Altyazı oluşturuluyor'], 0)
        self.assertEqual(asamalar['MD5 hesaplanıyor'], 1)
        self.assertIn('1 videonun bilgisi tamamlandı', sonuc)
        db = baglan(self.db_yolu)
        kayit = db.execute('SELECT * FROM videos').fetchone()
        self.assertEqual((kayit['duration'], kayit['md5']), (75.5, hashlib.md5(b'eski video').hexdigest()))
        db.close()

    def test_yollar_verilince_yalnizca_onlar_yeni_modelle_islenir(self):
        for ad in ('a.mp4', 'b.mp4'):
            (self.kok / ad).write_bytes(ad.encode())
        self.isciyi_calistir()
        hedef = str(self.kok / 'a.mp4')
        isci = TaramaIscisi([], 'large-v3', 'tr', True, yollar=[hedef])
        sonuclar, durumlar = [], []
        isci.sonuc.connect(sonuclar.append)
        isci.oge_bitti.connect(lambda durum, not_: durumlar.append(durum))
        with self.veritabani(), patch('arsiv.isci.incele', return_value={'duration': 5}), sahte_whisper():
            isci.run()
        self.assertIn('1 işlendi', sonuclar[-1])
        self.assertEqual(durumlar, ['Tamamlandı'])
        self.assertEqual(self.adlar(), {'a.mp4': 'large-v3', 'b.mp4': 'small'})

    def test_oge_sinyalleri_ayrinti_ilerleme_ve_durum_bildirir(self):
        (self.kok / 'iyi.mp4').write_bytes(b'12345')
        isci = TaramaIscisi([str(self.kok)], 'small', 'tr')
        olaylar = []
        isci.ogeler_kuyrukta.connect(lambda ogeler, tur: olaylar.append(('kuyruk', [(Path(y).name, a, b) for y, a, b in ogeler], tur)))
        isci.oge_basladi.connect(lambda yol, tur: olaylar.append(('basla', Path(yol).name, tur)))
        isci.oge_ayrintisi.connect(lambda boyut, sure: olaylar.append(('ayrinti', boyut, sure)))
        isci.oge_ilerlemesi.connect(lambda yuzde: olaylar.append(('ilerleme', yuzde)))
        isci.oge_bitti.connect(lambda durum, not_: olaylar.append(('bitti', durum)))
        with self.veritabani(), patch('arsiv.isci.incele', return_value={'duration': 5}), sahte_whisper():
            isci.run()
        self.assertEqual(olaylar, [('kuyruk', [('iyi.mp4', 5, 5)], 'Altyazı'), ('basla', 'iyi.mp4', 'Altyazı'),
                                   ('ayrinti', 5, 5), ('ilerleme', 99), ('bitti', 'Tamamlandı')])

    def test_mevcut_isi_bitir_calisan_videoyu_tamamlar_kalanlari_atlar(self):
        for ad in ('a.mp4', 'b.mp4', 'c.mp4'):
            (self.kok / ad).write_bytes(ad.encode())
        isci = TaramaIscisi([str(self.kok)], 'small', 'tr')

        def durduran(*_args, **_kwargs):
            model = Mock()

            def transcribe(dosya_adi, **_):
                isci.mevcut_isi_bitir()  # zamanlayıcının bitiş saati ilk videonun ortasında geldi
                return [SimpleNamespace(start=0, end=1, text='metin')], SimpleNamespace(duration=1)
            model.transcribe.side_effect = transcribe
            return model
        sonuclar, biten = [], []
        isci.sonuc.connect(sonuclar.append)
        isci.oge_bitti.connect(lambda durum, not_: biten.append(durum))
        with self.veritabani(), patch('arsiv.isci.incele', return_value={'duration': 1}), sahte_whisper(durduran):
            isci.run()
        self.assertEqual(biten, ['Tamamlandı'])
        self.assertIn('Durduruldu: 1 işlendi', sonuclar[-1])
        self.assertEqual(set(self.adlar()), {'a.mp4'})

    def test_bekleyen_tum_videolar_bilinen_ayrintilarla_kuyruga_girer(self):
        for ad in ('a.mp4', 'b.mp4', 'c.mp4'):
            (self.kok / ad).write_bytes(ad.encode())
        self.isciyi_calistir()
        (self.kok / 'yeni.mp4').write_bytes(b'12345')
        isci = TaramaIscisi([str(self.kok)], 'large-v3', 'tr')
        kuyruklar = []
        isci.ogeler_kuyrukta.connect(lambda ogeler, tur: kuyruklar.append((tur, [(Path(y).name, a, b) for y, a, b in ogeler])))
        with self.veritabani(), patch('arsiv.isci.incele', return_value={'duration': 5}), sahte_whisper():
            isci.run()
        self.assertEqual(kuyruklar, [('Altyazı', [('a.mp4', 5, 75.5), ('b.mp4', 5, 75.5), ('c.mp4', 5, 75.5), ('yeni.mp4', 5, 5)])])

    def test_ilerleme_icerik_suresini_izler_hatalilari_dusurur(self):
        for ad in ('a_kisa.mp4', 'b_bozuk.mp4', 'c_uzun.mp4'):
            (self.kok / ad).write_bytes(ad.encode())
        sureler = {'a_kisa.mp4': 100.0, 'b_bozuk.mp4': 50.0, 'c_uzun.mp4': 900.0}

        def modelci(*_args, **_kwargs):
            model = Mock()

            def transcribe(dosya_adi, **_):
                if 'bozuk' in dosya_adi:
                    raise RuntimeError('bozuk dosya')
                return [SimpleNamespace(start=0, end=10, text='metin')], SimpleNamespace(duration=sureler[Path(dosya_adi).name])
            model.transcribe.side_effect = transcribe
            return model
        isci = TaramaIscisi([str(self.kok)], 'small', 'tr')
        icerik = []
        isci.icerik_ilerlemesi.connect(lambda biten, toplam: icerik.append((biten, toplam)))
        with self.veritabani(), patch('arsiv.isci.incele', side_effect=lambda y: {'duration': sureler[Path(y).name]}), \
                sahte_whisper(modelci):
            isci.run()
        self.assertEqual(icerik, [(10, 1050), (100, 1050), (100, 1000), (110, 1000), (1000, 1000)])

    def test_sureler_islemden_once_bir_kez_okunur(self):
        (self.kok / 'a.mp4').write_bytes(b'1')
        incele = Mock(return_value={'duration': 5})
        isci = TaramaIscisi([str(self.kok)], 'small', 'tr')
        with self.veritabani(), patch('arsiv.isci.incele', incele), sahte_whisper():
            isci.run()
        self.assertEqual(incele.call_count, 1)

    def test_sure_disi_videolar_toplam_icerige_katilmaz(self):
        for ad in ('kisa.mp4', 'uzun.mp4'):
            (self.kok / ad).write_bytes(ad.encode())
        isci = TaramaIscisi([str(self.kok)], 'small', 'tr', sure_filtresi=SureFiltresi('en_fazla', en_fazla=10))
        icerik = []
        isci.icerik_ilerlemesi.connect(lambda biten, toplam: icerik.append(toplam))
        with self.veritabani(), patch('arsiv.isci.incele', side_effect=lambda y: {'duration': 60 if 'kisa' in str(y) else 6000}), \
                sahte_whisper():
            isci.run()
        self.assertEqual(set(icerik), {60})

    def test_ic_ice_kokler_bir_kez_gezilir(self):
        ust, alt, diger = str(self.kok), str(self.kok / 'alt'), str(Path(self.gecici.name) / 'diger')
        self.assertEqual(ayri_kokler([alt, ust, diger, ust + os.sep]), [ust, diger])


class ModelYuklemeTestleri(unittest.TestCase):
    def test_gpu_hatasinda_cpuya_doner(self):
        olusturulan, gunluk = [], []

        def whisper(ad, device, compute_type, download_root):
            olusturulan.append((device, compute_type))
            model = Mock()
            if device == 'cuda':
                model.transcribe.side_effect = RuntimeError('cublas yok')
            return model
        with patch('arsiv.konusma.gpu_durumu', return_value=(True, 'hazır')), \
                patch.dict('sys.modules', {'faster_whisper': SimpleNamespace(WhisperModel=whisper)}):
            model_yukle('small', 'cuda', gunluk.append)
        self.assertEqual(olusturulan, [('cuda', 'float16'), ('cpu', 'int8')])
        self.assertTrue(any('cublas yok' in satir for satir in gunluk))

    def test_cpu_seciminde_gpuya_dokunulmaz(self):
        olusturulan = []
        with patch('arsiv.konusma.gpu_durumu', side_effect=AssertionError), \
                patch.dict('sys.modules', {'faster_whisper': SimpleNamespace(
                    WhisperModel=lambda ad, device, compute_type, download_root: olusturulan.append(device))}):
            model_yukle('small', 'cpu', lambda _: None)
        self.assertEqual(olusturulan, ['cpu'])


if __name__ == '__main__':
    unittest.main()
