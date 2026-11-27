"""Arama sonuçlarındaki önizleme kareleri: arka planda üretilir, veriler/onizlemeler altında saklanır."""
import hashlib
import os
import threading

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

from .yollar import ONIZLEME_KLASORU

GENISLIK = 192


def onbellek_dosyasi(yol, saniye):
    try:
        degisme = os.stat(yol).st_mtime_ns
    except OSError:
        return None
    anahtar = hashlib.sha1(f'{yol}|{degisme}|{saniye:.1f}|{GENISLIK}'.encode('utf-8')).hexdigest()
    return ONIZLEME_KLASORU / anahtar[:2] / f'{anahtar}.jpg'


def kare_cikar(yol, saniye):
    """Videodan verilen saniyedeki kareyi küçültülmüş QImage olarak döndürür."""
    import av
    with av.open(yol) as kap:
        akis = kap.streams.video[0]
        akis.thread_type = 'AUTO'
        if saniye > 0:
            kap.seek(int(saniye / akis.time_base), stream=akis, backward=True)
        for kare in kap.decode(akis):
            if kare.time is None or kare.time >= saniye - 0.05:
                yukseklik = max(2, round(kare.height * GENISLIK / kare.width / 2) * 2)
                rgb = kare.reformat(width=GENISLIK, height=yukseklik, format='rgb24')
                duzlem = rgb.planes[0]
                return QImage(bytes(duzlem), GENISLIK, yukseklik, duzlem.line_size, QImage.Format.Format_RGB888).copy()
    return QImage()


class OnizlemeYukleyici(QThread):
    """Önizleme görüntülerini arka planda üretir; önbellekte varsa oradan okur.
    Kuyruk her yeni aramada değiştirilir; ekranda görünen satırlar öne alınabilir."""
    hazir = pyqtSignal(str, float, QImage)

    def __init__(self, ust=None):
        super().__init__(ust)
        self.kuyruk = []
        self.kosul = threading.Condition()
        self.duruyor = False

    def iste(self, ogeler):
        with self.kosul:
            self.kuyruk = list(dict.fromkeys(ogeler))
            self.kosul.notify()

    def one_al(self, ogeler):
        with self.kosul:
            on = [oge for oge in ogeler if oge in self.kuyruk]
            self.kuyruk = on + [oge for oge in self.kuyruk if oge not in on]

    def temizle(self):
        self.iste([])

    def durdur(self):
        with self.kosul:
            self.duruyor = True
            self.kuyruk = []
            self.kosul.notify()
        self.wait(5000)

    def run(self):
        while True:
            with self.kosul:
                while not self.kuyruk and not self.duruyor:
                    self.kosul.wait()
                if self.duruyor:
                    return
                yol, saniye = self.kuyruk.pop(0)
            self.hazir.emit(yol, saniye, self.yukle(yol, saniye))

    def yukle(self, yol, saniye):
        hedef = onbellek_dosyasi(yol, saniye)
        if hedef is None:
            return QImage()
        if hedef.exists():
            goruntu = QImage(str(hedef))
            if not goruntu.isNull():
                return goruntu
        try:
            # Konuşmanın başladığı an çoğu zaman geçiş karesine denk gelir; biraz ileriden alınır.
            goruntu = kare_cikar(yol, saniye + 0.5)
        except Exception:
            try:
                goruntu = kare_cikar(yol, 0)
            except Exception:
                return QImage()
        if not goruntu.isNull():
            try:
                hedef.parent.mkdir(parents=True, exist_ok=True)
                gecici = hedef.with_suffix('.tmp')
                if goruntu.save(str(gecici), 'JPG', 80):
                    gecici.replace(hedef)
            except OSError:
                pass
        return goruntu
