"""Proje klasörüne göre sabit yollar. Veriler ve modeller proje klasöründe durur (ağ paylaşımından
birden çok bilgisayar aynı arşivi kullanır)."""
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
VERI_KLASORU = KOK / 'veriler'
VERITABANI = VERI_KLASORU / 'altyazilar.sqlite3'
AYARLAR = VERI_KLASORU / 'ayarlar.ini'
ONIZLEME_KLASORU = VERI_KLASORU / 'onizlemeler'
MODEL_KLASORU = KOK / 'modeller'
IKON = KOK / 'varliklar' / 'simge.ico'
KILIT_DOSYASI = KOK / 'uygulama.lock'
