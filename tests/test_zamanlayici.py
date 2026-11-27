import unittest
from datetime import datetime, time

from arsiv.zamanlayici import aralik_sonu, etkin_aralik, saat_coz, sonraki_baslangic

GECE = (time(20, 0), time(7, 0))
GUNDUZ = (time(9, 0), time(17, 30))


class ZamanlayiciTestleri(unittest.TestCase):
    def test_gece_yarisini_asan_aralik(self):
        self.assertEqual(etkin_aralik(datetime(2026, 11, 18, 20, 0), *GECE), datetime(2026, 11, 18, 20, 0))
        self.assertEqual(etkin_aralik(datetime(2026, 11, 18, 23, 59), *GECE), datetime(2026, 11, 18, 20, 0))
        self.assertEqual(etkin_aralik(datetime(2026, 11, 19, 3, 0), *GECE), datetime(2026, 11, 18, 20, 0))
        self.assertIsNone(etkin_aralik(datetime(2026, 11, 19, 7, 0), *GECE))
        self.assertIsNone(etkin_aralik(datetime(2026, 11, 19, 12, 0), *GECE))
        self.assertIsNone(etkin_aralik(datetime(2026, 11, 19, 19, 59), *GECE))

    def test_ayni_gun_icindeki_aralik(self):
        self.assertEqual(etkin_aralik(datetime(2026, 11, 18, 9, 0), *GUNDUZ), datetime(2026, 11, 18, 9, 0))
        self.assertIsNone(etkin_aralik(datetime(2026, 11, 18, 17, 30), *GUNDUZ))
        self.assertIsNone(etkin_aralik(datetime(2026, 11, 18, 8, 59), *GUNDUZ))

    def test_esit_saatler_gecersiz(self):
        self.assertIsNone(etkin_aralik(datetime(2026, 11, 18, 20, 0), time(20, 0), time(20, 0)))

    def test_aralik_sonu_ve_sonraki_baslangic(self):
        self.assertEqual(aralik_sonu(datetime(2026, 11, 18, 20, 0), *GECE), datetime(2026, 11, 19, 7, 0))
        self.assertEqual(aralik_sonu(datetime(2026, 11, 18, 9, 0), *GUNDUZ), datetime(2026, 11, 18, 17, 30))
        self.assertEqual(sonraki_baslangic(datetime(2026, 11, 18, 12, 0), *GECE), datetime(2026, 11, 18, 20, 0))
        self.assertEqual(sonraki_baslangic(datetime(2026, 11, 18, 21, 0), *GECE), datetime(2026, 11, 19, 20, 0))

    def test_saat_coz(self):
        self.assertEqual(saat_coz('07:05', None), time(7, 5))
        self.assertEqual(saat_coz('bozuk', time(20, 0)), time(20, 0))


if __name__ == '__main__':
    unittest.main()
