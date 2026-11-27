"""Arayüz dili. Kodda Türkçe metinler anahtardır; _t() seçili dil İngilizce ise karşılığını döndürür.

Kullanım: _t('{sayi} video bulundu', sayi=5). Yeni metin eklerken İngilizcesini ceviri_en.py'ye yazın;
tests/test_ceviri.py eksik çeviriyi yakalar."""
from .ceviri_en import INGILIZCE

DILLER = (('Türkçe', 'tr'), ('English', 'en'))
_dil = 'tr'


def dil_ayarla(dil):
    global _dil
    _dil = dil if dil in ('tr', 'en') else 'tr'


def dil_kodu():
    return _dil


def sistem_dili():
    """Ayar yoksa: Windows dili Türkçe ise 'tr', değilse 'en'."""
    from PyQt6.QtCore import QLocale
    return 'tr' if QLocale.system().name().lower().startswith('tr') else 'en'


def _t(metin, **degerler):
    if _dil == 'en':
        metin = INGILIZCE.get(metin, metin)
    return metin.format(**degerler) if degerler else metin


def ondalik(sayi, basamak=1):
    """Ondalık sayı: Türkçede virgül, İngilizcede nokta."""
    metin = f'{sayi:.{basamak}f}'
    return metin if _dil == 'en' else metin.replace('.', ',')


def yuzde(sayi, basamak=0):
    """Yüzde: Türkçede %12, İngilizcede 12%."""
    metin = ondalik(sayi, basamak)
    return f'{metin}%' if _dil == 'en' else f'%{metin}'
