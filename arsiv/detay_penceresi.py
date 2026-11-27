"""Detay penceresi: videonun tüm altyazısı ve gömülü oynatıcı. Ortak biçimlendirme yardımcıları da buradadır."""
import os
import re
import shutil
from pathlib import Path

from PyQt6.QtCore import QProcess, Qt, QUrl
from PyQt6.QtGui import QColor, QDesktopServices, QGuiApplication
from PyQt6.QtWidgets import (QCheckBox, QDialog, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QMessageBox,
                             QPushButton, QSlider, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from .ceviri import _t, ondalik
from .veritabani import sadelestir, srt_aktar, zaman_damgasi

QMediaPlayer = None  # DetayPenceresi ilk açıldığında yüklenir (aşağıya bakın)
ESLESME_ARKA_PLANI = QColor('#fff3b0')
ESLESME_YAZISI = QColor('#202020')


def vlc_bul():
    adaylar = [shutil.which('vlc')]
    for degisken in ('ProgramFiles', 'ProgramFiles(x86)', 'ProgramW6432'):
        if os.environ.get(degisken):
            adaylar.append(os.path.join(os.environ[degisken], 'VideoLAN', 'VLC', 'vlc.exe'))
    return next((a for a in adaylar if a and os.path.isfile(a)), None)


def gezginde_goster(yol):
    """Dosyanın klasörünü açar ve dosyayı seçili getirir (Windows Gezgini)."""
    yol = os.path.normpath(yol)
    if os.name == 'nt' and os.path.exists(yol):
        import ctypes
        shell32 = ctypes.windll.shell32
        shell32.SHParseDisplayName.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p),
                                               ctypes.c_ulong, ctypes.c_void_p]
        shell32.SHOpenFolderAndSelectItems.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_ulong]
        shell32.ILFree.argtypes = [ctypes.c_void_p]
        ctypes.windll.ole32.CoInitialize(None)
        pidl = ctypes.c_void_p()
        if shell32.SHParseDisplayName(yol, None, ctypes.byref(pidl), 0, None) == 0 and pidl:
            try:
                if shell32.SHOpenFolderAndSelectItems(pidl, 0, None, 0) == 0:
                    return
            finally:
                shell32.ILFree(pidl)
        if QProcess.startDetached('explorer.exe', [f'/select,{yol}']):
            return
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(yol).parent)))


def saat(milisaniye):
    """Süreyi 'S:DD:SS' veya 'DD:SS' olarak yazar."""
    saniye = max(0, milisaniye) // 1000
    sa, kalan = divmod(saniye, 3600)
    dk, sn = divmod(kalan, 60)
    return f'{sa}:{dk:02}:{sn:02}' if sa else f'{dk:02}:{sn:02}'


def okunur_boyut(boyut):
    if boyut is None:
        return ''
    for birim in ('B', 'KB', 'MB', 'GB', 'TB'):
        if boyut < 1024 or birim == 'TB':
            return f'{boyut:.0f} {birim}' if birim == 'B' else f'{ondalik(boyut)} {birim}'
        boyut /= 1024


class DetayPenceresi(QDialog):
    """Seçili videonun tüm altyazısı ve gömülü oynatıcı. Satıra tıklayınca video o saniyeden oynar."""

    def __init__(self, ust, yol, satirlar, baslangic=0.0, sorgu='', tam_kelime=False):
        # QtMultimedia (FFmpeg DLL'leri) ağ paylaşımından ~20 sn'de yüklenir; açılışı yavaşlatmasın diye
        # yalnızca detay penceresi ilk açıldığında yüklenir.
        global QMediaPlayer
        from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
        from PyQt6.QtMultimediaWidgets import QVideoWidget
        super().__init__(ust)
        self.yol, self.satirlar = yol, satirlar
        self.setWindowTitle(_t('Detay • {ad}', ad=Path(yol).name))
        self.resize(1300, 760)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        duzen = QVBoxLayout(self)
        baslik = QLabel(yol)
        baslik.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        baslik.setWordWrap(True)
        baslik.setStyleSheet('font-weight:600')
        duzen.addWidget(baslik)

        bolucu = QSplitter()
        oynatici_kutusu = QWidget()
        oynatici_duzeni = QVBoxLayout(oynatici_kutusu)
        oynatici_duzeni.setContentsMargins(0, 0, 0, 0)
        self.video = QVideoWidget()
        self.video.setMinimumSize(420, 240)
        oynatici_duzeni.addWidget(self.video, 1)
        self.altyazi = QLabel()
        self.altyazi.setWordWrap(True)
        self.altyazi.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.altyazi.setMinimumHeight(48)
        self.altyazi.setStyleSheet('font-size:15px;padding:4px')
        oynatici_duzeni.addWidget(self.altyazi)
        kontroller = QHBoxLayout()
        self.oynat_dugmesi = QPushButton(_t('Oynat'))
        self.oynat_dugmesi.clicked.connect(self.oynat_duraklat)
        kontroller.addWidget(self.oynat_dugmesi)
        self.kaydirici = QSlider(Qt.Orientation.Horizontal)
        self.kaydirici.sliderMoved.connect(lambda deger: self.oynatici.setPosition(deger))
        kontroller.addWidget(self.kaydirici, 1)
        self.zaman_etiketi = QLabel('00:00 / 00:00')
        kontroller.addWidget(self.zaman_etiketi)
        oynatici_duzeni.addLayout(kontroller)
        bolucu.addWidget(oynatici_kutusu)

        self.tablo = QTableWidget(len(satirlar), 3)
        self.tablo.setHorizontalHeaderLabels([_t('Başlangıç'), _t('Bitiş'), _t('Altyazı')])
        self.tablo.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tablo.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tablo.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tablo.setWordWrap(True)
        self.tablo.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tablo.setColumnWidth(0, 95)
        self.tablo.setColumnWidth(1, 95)
        kelimeler = re.findall(r'\w+', sadelestir(sorgu))
        self.eslesen = 0
        for i, (a, b, metin) in enumerate(satirlar):
            parcalar = re.findall(r'\w+', sadelestir(metin))
            isabet = kelimeler and any(p == k if tam_kelime else p.startswith(k) for k in kelimeler for p in parcalar)
            self.eslesen += bool(isabet)
            for j, deger in enumerate([zaman_damgasi(a), zaman_damgasi(b), metin]):
                oge = QTableWidgetItem(deger)
                oge.setToolTip(metin)
                if isabet:
                    oge.setBackground(ESLESME_ARKA_PLANI)
                    oge.setForeground(ESLESME_YAZISI)
                self.tablo.setItem(i, j, oge)
        self.tablo.resizeRowsToContents()
        self.tablo.cellClicked.connect(self.satira_git)
        bolucu.addWidget(self.tablo)
        bolucu.setSizes([620, 680])
        duzen.addWidget(bolucu, 1)

        bilgi = QHBoxLayout()
        self.takip = QCheckBox(_t('Oynatırken altyazıyı takip et'))
        self.takip.setChecked(True)
        bilgi.addWidget(self.takip)
        bilgi.addStretch()
        bilgi.addWidget(QLabel(_t('{sayi} satır', sayi=len(satirlar))
                               + (_t(' • {sayi} satırda aranan kelime var (sarı)', sayi=self.eslesen) if kelimeler else '')
                               + _t(' • Satıra tıklayın: video o saniyeden oynar.')))
        duzen.addLayout(bilgi)

        dugmeler = QHBoxLayout()
        self.vlc = vlc_bul()
        vlc_dugmesi = QPushButton(_t("VLC'de bu saniyeden aç"))
        vlc_dugmesi.setEnabled(bool(self.vlc))
        vlc_dugmesi.setToolTip(self.vlc or _t('VLC bulunamadı. https://www.videolan.org adresinden kurulabilir.'))
        vlc_dugmesi.clicked.connect(self.vlc_ac)
        dugmeler.addWidget(vlc_dugmesi)
        for etiket, islev in [('Varsayılan oynatıcıda aç', self.varsayilanda_ac), ('Klasörünü aç', self.klasoru_ac),
                              ('Metni kopyala', self.metni_kopyala), ('SRT kaydet', self.srt_kaydet), ('Kapat', self.close)]:
            dugme = QPushButton(_t(etiket))
            dugme.clicked.connect(islev)
            dugmeler.addWidget(dugme)
        duzen.addLayout(dugmeler)

        self.ses = QAudioOutput(self)
        self.oynatici = QMediaPlayer(self)
        self.oynatici.setAudioOutput(self.ses)
        self.oynatici.setVideoOutput(self.video)
        self.oynatici.durationChanged.connect(self.sure_degisti)
        self.oynatici.positionChanged.connect(self.konum_degisti)
        self.oynatici.playbackStateChanged.connect(self.oynatma_durumu_degisti)
        self.oynatici.errorOccurred.connect(self.medya_hatasi)
        self.oynatici.mediaStatusChanged.connect(self.medya_durumu_degisti)
        self.bekleyen_konum = None
        self.oynatici.setSource(QUrl.fromLocalFile(yol))

        satir = self.satir_bul(baslangic * 1000)
        if satir is not None:
            self.tablo.selectRow(satir)
            self.tablo.scrollToItem(self.tablo.item(satir, 0), QTableWidget.ScrollHint.PositionAtCenter)
        self.konuma_git(baslangic)

    def satir_bul(self, milisaniye):
        saniye = milisaniye / 1000
        mevcut = None
        for i, (a, _b, _) in enumerate(self.satirlar):
            if a <= saniye + 0.01:
                mevcut = i
            if a > saniye:
                break
        return mevcut

    def gecerli_saniye(self):
        return self.oynatici.position() / 1000

    def konuma_git(self, saniye, oynat=True):
        # Video yüklenmeden yapılan konum değişikliği yok sayılır; yüklenince uygulanır.
        if self.oynatici.mediaStatus() in (QMediaPlayer.MediaStatus.NoMedia, QMediaPlayer.MediaStatus.LoadingMedia):
            self.bekleyen_konum = (saniye, oynat)
            return
        self.oynatici.setPosition(int(saniye * 1000))
        if oynat:
            self.oynatici.play()

    def medya_durumu_degisti(self, durum):
        if durum == QMediaPlayer.MediaStatus.LoadedMedia and self.bekleyen_konum:
            saniye, oynat = self.bekleyen_konum
            self.bekleyen_konum = None
            self.konuma_git(saniye, oynat)

    def satira_git(self, satir, _sutun=None):
        self.konuma_git(self.satirlar[satir][0])

    def oynat_duraklat(self):
        if self.oynatici.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.oynatici.pause()
        else:
            self.oynatici.play()

    def oynatma_durumu_degisti(self, durum):
        self.oynat_dugmesi.setText(_t('Duraklat') if durum == QMediaPlayer.PlaybackState.PlayingState else _t('Oynat'))

    def sure_degisti(self, sure):
        self.kaydirici.setRange(0, sure)

    def konum_degisti(self, konum):
        if not self.kaydirici.isSliderDown():
            self.kaydirici.setValue(konum)
        self.zaman_etiketi.setText(f'{saat(konum)} / {saat(self.oynatici.duration())}')
        satir = self.satir_bul(konum)
        icinde = satir is not None and konum / 1000 <= self.satirlar[satir][1] + 0.3
        self.altyazi.setText(self.satirlar[satir][2] if icinde else '')
        if (satir is not None and self.takip.isChecked()
                and self.oynatici.playbackState() == QMediaPlayer.PlaybackState.PlayingState
                and self.tablo.currentRow() != satir):
            self.tablo.selectRow(satir)
            self.tablo.scrollToItem(self.tablo.item(satir, 0), QTableWidget.ScrollHint.EnsureVisible)

    def medya_hatasi(self, _hata, mesaj):
        self.altyazi.setText(_t('Video burada oynatılamadı: {mesaj}\nVLC veya varsayılan oynatıcı düğmesini kullanın.',
                                mesaj=mesaj))

    def vlc_ac(self):
        self.oynatici.pause()
        if not QProcess.startDetached(self.vlc, [f'--start-time={self.gecerli_saniye():.2f}', self.yol]):
            QMessageBox.warning(self, _t('VLC açılamadı'), self.vlc)

    def varsayilanda_ac(self):
        self.oynatici.pause()
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(self.yol)):
            QMessageBox.warning(self, _t('Video açılamadı'), _t('Dosya yolunu ve varsayılan oynatıcınızı kontrol edin.'))

    def klasoru_ac(self):
        gezginde_goster(self.yol)

    def metni_kopyala(self):
        QGuiApplication.clipboard().setText('\n'.join(metin for _, _, metin in self.satirlar))

    def srt_kaydet(self):
        hedef, _filtre = QFileDialog.getSaveFileName(self, _t('SRT kaydet'), str(Path(self.yol).with_suffix('.srt')),
                                                     _t('Altyazı (*.srt)'))
        if hedef:
            try:
                srt_aktar(self.satirlar, hedef)
            except Exception as hata:
                QMessageBox.warning(self, _t('Dışa aktarma hatası'), str(hata))

    def done(self, sonuc):
        self.oynatici.stop()
        self.oynatici.setSource(QUrl())
        super().done(sonuc)
