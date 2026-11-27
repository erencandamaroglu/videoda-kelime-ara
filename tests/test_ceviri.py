import ast
import string
import unittest
from pathlib import Path

from arsiv import arayuz, bag_penceresi, ceviri
from arsiv.ceviri_en import INGILIZCE

KOK = Path(__file__).resolve().parent.parent

# _t()'ye değişkenle verilen metinler (sabit listeler, işçinin aşama/durum anahtarları)
DOLAYLI = {
    *arayuz.TARAMA_SUTUNLARI, *(etiket for etiket, _a in arayuz.LISTE_SUTUNLARI), *(etiket for etiket, _d in arayuz.DILLER),
    *bag_penceresi.SUTUNLAR,
    'Tüm süreler', 'En fazla (≤)', 'En az (≥)', 'İki süre arasında',
    'Otomatik (GPU varsa GPU)', 'GPU (NVIDIA CUDA)', 'CPU',
    'Varsayılan oynatıcıda aç', 'Klasörünü aç', 'Metni kopyala', 'SRT kaydet', 'Kapat',
    'Önerileri uygula', 'Dosyayı elle seç…', 'Başka klasörde ara…', 'Kayıttan kaldır',
    'Klasörler taranıyor', 'Video süreleri okunuyor', 'Altyazı oluşturuluyor', 'Video bilgileri okunuyor', 'MD5 hesaplanıyor',
    'Altyazı', 'MD5', 'Tamamlandı', 'Hata', 'Süre dışı', 'Durduruldu',
}


def koddaki_anahtarlar():
    anahtarlar = set()
    for dosya in [*KOK.glob('arsiv/*.py'), KOK / 'main.py']:
        for dugum in ast.walk(ast.parse(dosya.read_text(encoding='utf-8'))):
            if isinstance(dugum, ast.Call) and getattr(dugum.func, 'id', None) == '_t' and dugum.args:
                arg = dugum.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    anahtarlar.add(arg.value)
    return anahtarlar


def yer_tutucular(metin):
    return {ad for _metin, ad, _bicim, _donusum in string.Formatter().parse(metin) if ad}


class CeviriTestleri(unittest.TestCase):
    def tearDown(self):
        ceviri.dil_ayarla('tr')

    def test_tum_metinlerin_ingilizcesi_var(self):
        eksik = sorted((koddaki_anahtarlar() | DOLAYLI) - set(INGILIZCE))
        self.assertEqual(eksik, [], 'ceviri_en.py içinde eksik çeviri')

    def test_yer_tutucular_ayni(self):
        for tr, en in INGILIZCE.items():
            self.assertEqual(yer_tutucular(tr), yer_tutucular(en), tr)

    def test_dil_secimi(self):
        self.assertEqual(ceviri._t('{sayi} SRT dosyası kaydedildi.', sayi=3), '3 SRT dosyası kaydedildi.')
        ceviri.dil_ayarla('en')
        self.assertEqual(ceviri._t('{sayi} SRT dosyası kaydedildi.', sayi=3), '3 SRT files saved.')
        self.assertEqual((ceviri.yuzde(12.5, 1), ceviri.ondalik(1.25, 2)), ('12.5%', '1.25'))
        ceviri.dil_ayarla('tr')
        self.assertEqual((ceviri.yuzde(12.5, 1), ceviri.ondalik(1.25, 2)), ('%12,5', '1,25'))
        ceviri.dil_ayarla('fr')
        self.assertEqual(ceviri.dil_kodu(), 'tr')


if __name__ == '__main__':
    unittest.main()
