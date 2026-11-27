import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from arsiv.isci import TaramaIscisi
from arsiv.sure_filtresi import SureFiltresi, video_suresi
from arsiv.veritabani import baglan


class SureTestleri(unittest.TestCase):
    def test_sinirlar_saniye_cinsinden(self):
        ust = SureFiltresi('en_fazla', en_fazla=10)
        self.assertTrue(ust.kabul_eder(600))
        self.assertFalse(ust.kabul_eder(600.01))
        alt = SureFiltresi('en_az', en_az=2)
        self.assertTrue(alt.kabul_eder(120))
        self.assertFalse(alt.kabul_eder(119.99))
        aralik = SureFiltresi('arasinda', 2.5, 10)
        for saniye, beklenen in [(149.99, False), (150, True), (600, True), (600.01, False)]:
            self.assertEqual(aralik.kabul_eder(saniye), beklenen)
        with self.assertRaises(ValueError):
            SureFiltresi('arasinda', 11, 10)

    def test_gercek_video_bilgisi(self):
        import av
        import numpy as np
        with tempfile.TemporaryDirectory() as klasor:
            yol = Path(klasor) / 'video.mp4'
            with av.open(str(yol), 'w') as kap:
                akis = kap.add_stream('mpeg4', rate=10)
                akis.width = akis.height = 32
                akis.pix_fmt = 'yuv420p'
                for _ in range(20):
                    kare = av.VideoFrame.from_ndarray(np.zeros((32, 32, 3), dtype=np.uint8), format='rgb24')
                    for paket in akis.encode(kare):
                        kap.mux(paket)
                for paket in akis.encode():
                    kap.mux(paket)
            self.assertAlmostEqual(video_suresi(yol), 2, places=2)

    def test_isci_modelden_once_filtreler_ve_ilerlemeyi_gunceller(self):
        with tempfile.TemporaryDirectory() as klasor:
            kok = Path(klasor)
            (kok / 'uzun.mp4').write_bytes(b'test')
            model = Mock()
            isci = TaramaIscisi([klasor], 'small', 'tr', sure_filtresi=SureFiltresi('en_fazla', en_fazla=10))
            sonuclar, ilerleme = [], []
            isci.sonuc.connect(sonuclar.append)
            isci.ilerleme.connect(lambda a, b: ilerleme.append((a, b)))
            with patch('arsiv.isci.baglan', side_effect=lambda: baglan(kok / 'test.sqlite3')), \
                    patch('arsiv.isci.incele', return_value={'duration': 601}), \
                    patch.dict('sys.modules', {'faster_whisper': SimpleNamespace(WhisperModel=model)}):
                isci.run()
            model.assert_not_called()
            self.assertIn('1 süre dışı', sonuclar[-1])
            self.assertEqual(ilerleme[-1], (1, 1))

    def test_suresi_okunamayan_islenmez(self):
        with tempfile.TemporaryDirectory() as klasor:
            kok = Path(klasor)
            (kok / 'bozuk.mp4').write_bytes(b'test')
            model = Mock()
            isci = TaramaIscisi([klasor], 'small', 'tr', sure_filtresi=SureFiltresi('en_fazla', en_fazla=10))
            sonuclar = []
            isci.sonuc.connect(sonuclar.append)
            with patch('arsiv.isci.baglan', side_effect=lambda: baglan(kok / 'test.sqlite3')), \
                    patch('arsiv.isci.incele', side_effect=ValueError('Süre okunamadı')), \
                    patch.dict('sys.modules', {'faster_whisper': SimpleNamespace(WhisperModel=model)}):
                isci.run()
            model.assert_not_called()
            self.assertIn('1 hata', sonuclar[-1])


if __name__ == '__main__':
    unittest.main()
