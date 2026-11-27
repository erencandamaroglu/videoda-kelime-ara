"""Ana pencere: klasör tarama, kelime arama / SRT, video listesi ve ayarlar sekmeleri.

ayarlar.ini anahtarları (scan/model, folders/paths, schedule/start ...) eski sürümle uyum için değiştirilmez."""
import math
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

from PyQt6.QtCore import QEvent, QSettings, QSize, Qt, QTime, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices, QPixmap, QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFormLayout,
                             QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QSpinBox, QStyle,
                             QStyleOptionComboBox, QStylePainter, QTableWidget, QTableWidgetItem, QTabWidget, QTimeEdit,
                             QVBoxLayout, QWidget)

from .bag_penceresi import KopukBagPenceresi
from .detay_penceresi import DetayPenceresi, gezginde_goster, okunur_boyut, saat
from .isci import TaramaIscisi
from .konusma import gpu_durumu
from .onizleme import OnizlemeYukleyici
from .sure_filtresi import ESKI_MODLAR, SureFiltresi
from .veritabani import (ara, baglan, dosya_turu, kokleri_listele, modelleri_listele, srt_aktar, video_yollari,
                         videolari_listele, zaman_damgasi)
from .yollar import AYARLAR
from .zamanlayici import aralik_sonu, etkin_aralik, saat_coz, sonraki_baslangic, uyanik_tut

ONIZLEME_SUTUNU, ONIZLEME_GENISLIGI, ONIZLEME_YUKSEKLIGI = 4, 160, 90
LISTE_SUTUNLARI = [('Video / tam yol', 'yol'), ('Tür', 'tur'), ('Süre', 'sure'), ('Boyut', 'boyut'),
                   ('Çözünürlük', 'cozunurluk'), ('Satır', 'satir'), ('Model / dil', 'model'), ('MD5', 'md5')]
MODELLER = ['small', 'base', 'medium', 'large-v3', 'tiny']
DILLER = [('Türkçe', 'tr'), ('Otomatik algıla', 'auto'), ('İngilizce', 'en')]
TARAMA_SUTUNLARI = ['Video', 'Klasör', 'Tür', 'Boyut', 'Süre', 'İşlem', 'Durum', 'İlerleme', 'Geçen süre']
SUTUN_BOYUT, SUTUN_SURE, SUTUN_DURUM, SUTUN_CUBUK, SUTUN_GECEN = 3, 4, 6, 7, 8
TAHMIN_EN_AZ_SANIYE = 30
ZAMANLAYICI_ARALIGI_MS = 30_000
VARSAYILAN_KLASORLER = []  # ilk açılışta liste boştur; klasörler "Ekle" ile seçilir ve ayarlar.ini'de saklanır


def kalan_sure_tahmini(biten, toplam, ilk, gecen):
    """Kalan saniye: bu işlemde şimdiye kadarki hızla. ilk: ölçümün başladığı andaki değer.
    Yeterli ölçüm yoksa None."""
    if gecen < TAHMIN_EN_AZ_SANIYE or biten <= ilk:
        return None
    return max(0, toplam - biten) * gecen / (biten - ilk)


def sure_metni(saniye):
    dakika = round(saniye / 60)
    if dakika < 1:
        return '1 dk\'dan az'
    gun, kalan = divmod(dakika, 1440)
    sa, dakika = divmod(kalan, 60)
    if gun:
        return f'{gun} gün {sa} sa'
    return f'{sa} sa {dakika} dk' if sa else f'{dakika} dk'


def bitis_metni(saniye, simdi=None):
    simdi = simdi or datetime.now()
    bitis = simdi + timedelta(seconds=saniye)
    return bitis.strftime('%H:%M') if bitis.date() == simdi.date() else bitis.strftime('%d.%m.%Y %H:%M')


class AralikFiltresi(QWidget):
    """İsteğe bağlı alt/üst sınır. 0 (—) o tarafta sınır olmadığı anlamına gelir."""
    degisti = pyqtSignal()

    def __init__(self, etiket, sonek, carpan, en_fazla):
        super().__init__()
        self.carpan = carpan
        duzen = QHBoxLayout(self)
        duzen.setContentsMargins(0, 0, 0, 0)
        duzen.addWidget(QLabel(etiket))
        self.alt, self.ust = QDoubleSpinBox(), QDoubleSpinBox()
        for kutu, ipucu in ((self.alt, 'En az'), (self.ust, 'En fazla')):
            kutu.setRange(0, en_fazla)
            kutu.setDecimals(1)
            kutu.setSuffix(sonek)
            kutu.setSpecialValueText('—')
            kutu.setToolTip(f'{ipucu} (sınırlar dahil). — : sınır yok')
            kutu.setMinimumWidth(95)
            kutu.editingFinished.connect(self.degistiyse_bildir)
            duzen.addWidget(kutu)
            if kutu is self.alt:
                duzen.addWidget(QLabel('–'))
        self.son = (0, 0)

    def degistiyse_bildir(self):
        if (self.alt.value(), self.ust.value()) != self.son:
            self.son = (self.alt.value(), self.ust.value())
            self.degisti.emit()

    def sinirlar(self):
        alt, ust = self.alt.value(), self.ust.value()
        if alt and ust and alt > ust:
            raise ValueError('Alt sınır üst sınırdan büyük olamaz.')
        return (alt * self.carpan if alt else None, ust * self.carpan if ust else None)


class KlasorFiltresi(QComboBox):
    """Onay kutulu klasör listesi; liste açıkken birden fazla klasör işaretlenebilir."""
    degisti = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setModel(QStandardItemModel(self))
        self.view().viewport().installEventFilter(self)
        self.ozet = 'Tüm klasörler'

    def klasorleri_ayarla(self, klasorler):
        secili = set(self.secili())
        self.model().clear()
        tumu = QStandardItem('Tüm klasörler')
        tumu.setCheckable(True)
        self.model().appendRow(tumu)
        for yol, sayi in klasorler:
            oge = QStandardItem(f'{yol}  ({sayi} video)')
            oge.setData(yol, Qt.ItemDataRole.UserRole)
            oge.setCheckable(True)
            oge.setCheckState(Qt.CheckState.Checked if yol in secili else Qt.CheckState.Unchecked)
            self.model().appendRow(oge)
        self.tumu_ogesini_esitle()

    def klasor_ogeleri(self):
        return [self.model().item(i) for i in range(1, self.model().rowCount())]

    def secili(self):
        return [oge.data(Qt.ItemDataRole.UserRole) for oge in self.klasor_ogeleri()
                if oge.checkState() == Qt.CheckState.Checked]

    def tumu_ogesini_esitle(self):
        tumu = self.model().item(0)
        if tumu is not None:
            tumu.setCheckState(Qt.CheckState.Unchecked if self.secili() else Qt.CheckState.Checked)
        adlar = [Path(y).name or y for y in self.secili()]
        self.setToolTip('\n'.join(self.secili()) or 'Tüm klasörlerde aranır')
        self.ozet = ('Tüm klasörler' if not adlar else adlar[0] if len(adlar) == 1
                     else f'{len(adlar)} klasör: ' + ', '.join(adlar))
        self.update()

    def eventFilter(self, nesne, olay):
        if nesne is self.view().viewport() and olay.type() == QEvent.Type.MouseButtonRelease:
            indeks = self.view().indexAt(olay.position().toPoint())
            if indeks.isValid():
                if indeks.row() == 0:
                    for oge in self.klasor_ogeleri():
                        oge.setCheckState(Qt.CheckState.Unchecked)
                else:
                    oge = self.model().item(indeks.row())
                    oge.setCheckState(Qt.CheckState.Unchecked if oge.checkState() == Qt.CheckState.Checked
                                      else Qt.CheckState.Checked)
                self.tumu_ogesini_esitle()
                self.degisti.emit()
            return True
        return super().eventFilter(nesne, olay)

    def paintEvent(self, olay):
        boyaci = QStylePainter(self)
        secenek = QStyleOptionComboBox()
        self.initStyleOption(secenek)
        secenek.currentText = self.ozet
        boyaci.drawComplexControl(QStyle.ComplexControl.CC_ComboBox, secenek)
        boyaci.drawControl(QStyle.ControlElement.CE_ComboBoxLabel, secenek)


class YenidenIslePenceresi(QDialog):
    """Toplu yeniden işlemede kullanılacak model ve dilin seçimi."""

    def __init__(self, ust, sayi, model, dil):
        super().__init__(ust)
        self.setWindowTitle('Yeniden işle')
        duzen = QVBoxLayout(self)
        duzen.addWidget(QLabel(f'{sayi} videonun altyazısı seçilen modelle yeniden oluşturulacak.\n'
                               'Eski altyazı, yenisi başarıyla kaydedilene kadar korunur.'))
        form = QFormLayout()
        self.model = QComboBox()
        self.model.addItems(MODELLER)
        self.model.setCurrentText(model)
        self.dil = QComboBox()
        for etiket, deger in DILLER:
            self.dil.addItem(etiket, deger)
        self.dil.setCurrentIndex(max(0, self.dil.findData(dil)))
        form.addRow('Model:', self.model)
        form.addRow('Dil:', self.dil)
        duzen.addLayout(form)
        dugmeler = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        dugmeler.accepted.connect(self.accept)
        dugmeler.rejected.connect(self.reject)
        duzen.addWidget(dugmeler)


class AnaPencere(QMainWindow):
    def __init__(self):
        super().__init__()
        self.isci = None
        self.zamanli_calisma = False
        self.db = baglan()
        self.ayarlar = QSettings(str(AYARLAR), QSettings.Format.IniFormat)
        self.setWindowTitle('Videoda Kelime Ara')
        self.resize(1150, 800)
        self.sekmeler = QTabWidget()
        self.setCentralWidget(self.sekmeler)
        self.tarama_sekmesini_kur()
        self.arama_sekmesini_kur()
        self.video_listesini_kur()
        self.ayarlar_sekmesini_kur()
        self.sekmeler.currentChanged.connect(self.sekme_degisti)
        # Klasör/model listeleri veritabanından okunur; pencere beklemeden açılsın diye sonra doldurulur.
        QTimer.singleShot(0, self.kokleri_yenile)
        self.zamanlayici = QTimer(self)
        self.zamanlayici.setInterval(ZAMANLAYICI_ARALIGI_MS)
        self.zamanlayici.timeout.connect(self.zamanlayici_tik)
        self.zamanlayici.start()
        QTimer.singleShot(2000, self.zamanlayici_tik)

    # ---------- Klasör tarama sekmesi ----------

    def tarama_sekmesini_kur(self):
        sayfa = QWidget()
        duzen = QVBoxLayout(sayfa)
        baslik = QLabel('Video klasörleri')
        baslik.setStyleSheet('font-size:22px;font-weight:600')
        duzen.addWidget(baslik)
        duzen.addWidget(QLabel('Yalnızca işaretli klasörler taranır; alt klasörler de dahildir. Liste ve işaretler hatırlanır.'))
        klasor_satiri = QHBoxLayout()
        self.klasorler = QListWidget()
        self.klasorler.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.klasorler.setMaximumHeight(125)
        klasor_satiri.addWidget(self.klasorler)
        klasor_dugmeleri = QVBoxLayout()
        for etiket, islev in [('Ekle', self.klasor_ekle), ('Çıkar', self.klasorleri_cikar),
                              ('Tümünü seç', lambda: self.klasorleri_isaretle(True)),
                              ('Hiçbirini seçme', lambda: self.klasorleri_isaretle(False))]:
            dugme = QPushButton(etiket)
            dugme.clicked.connect(islev)
            klasor_dugmeleri.addWidget(dugme)
        klasor_dugmeleri.addStretch()
        klasor_satiri.addLayout(klasor_dugmeleri)
        duzen.addLayout(klasor_satiri)
        self.klasorleri_yukle()
        secenekler = QHBoxLayout()
        self.model = QComboBox()
        self.model.addItems(MODELLER)
        self.model.setCurrentText(self.ayarlar.value('scan/model', 'large-v3', type=str))
        self.model.currentTextChanged.connect(lambda deger: self.ayarlar.setValue('scan/model', deger))
        self.dil = QComboBox()
        for etiket, deger in DILLER:
            self.dil.addItem(etiket, deger)
        self.dil.setCurrentIndex(max(0, self.dil.findData(self.ayarlar.value('scan/language', 'tr', type=str))))
        self.dil.currentIndexChanged.connect(lambda: self.ayarlar.setValue('scan/language', self.dil.currentData()))
        secenekler.addWidget(QLabel('Model:'))
        secenekler.addWidget(self.model)
        secenekler.addWidget(QLabel('Dil:'))
        secenekler.addWidget(self.dil)
        self.yeniden_olustur = QCheckBox('İşlenenleri yeniden oluştur')
        secenekler.addWidget(self.yeniden_olustur)
        self.bilgi_tamamla = QCheckBox('Eksik video bilgilerini ve MD5 değerlerini tamamla')
        self.bilgi_tamamla.setToolTip('Önceden işlenmiş videoların süre, tür, çözünürlük ve MD5 değerleri altyazı işinden sonra\n'
                                      'tamamlanır. MD5 için dosyanın tamamı okunur; büyük arşivde uzun sürebilir.\n'
                                      'Durdurulursa kalan videolar sonraki taramada devam eder.')
        self.bilgi_tamamla.setChecked(self.ayarlar.value('scan/complete_info', True, type=bool))
        self.bilgi_tamamla.toggled.connect(lambda acik: self.ayarlar.setValue('scan/complete_info', acik))
        secenekler.addWidget(self.bilgi_tamamla)
        secenekler.addStretch()
        duzen.addLayout(secenekler)
        sure_satiri = QHBoxLayout()
        sure_satiri.addWidget(QLabel('Video süresi:'))
        self.sure_modu = QComboBox()
        for etiket, deger in [('Tüm süreler', 'tumu'), ('En fazla (≤)', 'en_fazla'),
                              ('En az (≥)', 'en_az'), ('İki süre arasında', 'arasinda')]:
            self.sure_modu.addItem(etiket, deger)
        sure_satiri.addWidget(self.sure_modu)
        self.sure_alt = QDoubleSpinBox()
        self.sure_ust = QDoubleSpinBox()
        for kutu in (self.sure_alt, self.sure_ust):
            kutu.setRange(0, 100000)
            kutu.setDecimals(2)
            kutu.setSuffix(' dk')
        kayitli_mod = self.ayarlar.value('scan/duration_mode', 'tumu', type=str)
        self.sure_modu.setCurrentIndex(max(0, self.sure_modu.findData(ESKI_MODLAR.get(kayitli_mod, kayitli_mod))))
        self.sure_alt.setValue(self.ayarlar.value('scan/duration_min', 1.0, type=float))
        self.sure_ust.setValue(self.ayarlar.value('scan/duration_max', 10.0, type=float))
        self.sure_modu.currentIndexChanged.connect(lambda: self.ayarlar.setValue('scan/duration_mode', self.sure_modu.currentData()))
        self.sure_alt.valueChanged.connect(lambda deger: self.ayarlar.setValue('scan/duration_min', deger))
        self.sure_ust.valueChanged.connect(lambda deger: self.ayarlar.setValue('scan/duration_max', deger))
        self.sure_alt_etiketi = QLabel('Alt sınır:')
        self.sure_ust_etiketi = QLabel('Üst sınır:')
        for bilesen in (self.sure_alt_etiketi, self.sure_alt, self.sure_ust_etiketi, self.sure_ust):
            sure_satiri.addWidget(bilesen)
        sure_satiri.addStretch()
        duzen.addLayout(sure_satiri)
        duzen.addWidget(QLabel('Süre sınırları dahildir. Filtre dışındaki videolar işlenmez; mevcut kayıtlar korunur.'))
        self.sure_modu.currentIndexChanged.connect(self.sure_kontrollerini_guncelle)
        self.sure_kontrollerini_guncelle()
        ipucu = QLabel('small: dengeli • base/tiny: daha hızlı • medium/large-v3: daha yavaş, daha fazla bellek\n'
                       'İlk model indirmesi internet gerektirir. Sonraki işlemler yereldir. GPU / CPU seçimi Ayarlar sekmesindedir.')
        ipucu.setWordWrap(True)
        duzen.addWidget(ipucu)
        eylemler = QHBoxLayout()
        self.baslat_dugmesi = QPushButton('Tara ve altyazıları oluştur')
        self.baslat_dugmesi.clicked.connect(lambda: self.taramayi_baslat())
        self.durdur_dugmesi = QPushButton('Durdur')
        self.durdur_dugmesi.setEnabled(False)
        self.durdur_dugmesi.clicked.connect(self.durdur)
        eylemler.addWidget(self.baslat_dugmesi)
        eylemler.addWidget(self.durdur_dugmesi)
        duzen.addLayout(eylemler)
        self.ilerleme = QProgressBar()
        duzen.addWidget(self.ilerleme)
        self.durum = QLabel('Hazır')
        duzen.addWidget(self.durum)
        self.gunluk = QPlainTextEdit()
        self.gunluk.setReadOnly(True)
        self.gunluk.setMaximumBlockCount(3000)
        self.tarama_listesi = QTableWidget(0, len(TARAMA_SUTUNLARI))
        self.tarama_listesi.setHorizontalHeaderLabels(TARAMA_SUTUNLARI)
        self.tarama_listesi.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tarama_listesi.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tarama_listesi.verticalHeader().setDefaultSectionSize(26)
        self.tarama_listesi.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        for sutun in (0, 1):
            self.tarama_listesi.horizontalHeader().setSectionResizeMode(sutun, QHeaderView.ResizeMode.Stretch)
        for sutun, genislik in enumerate((0, 0, 50, 75, 65, 60, 90, 90, 70)):
            if genislik:
                self.tarama_listesi.setColumnWidth(sutun, genislik)
        self.tarama_saati = QTimer(self)
        self.tarama_saati.setInterval(1000)
        self.tarama_saati.timeout.connect(self.tarama_tik)
        alt_sekmeler = QTabWidget()
        alt_sekmeler.addTab(self.tarama_listesi, 'Liste')
        alt_sekmeler.addTab(self.gunluk, 'Detaylı log')
        duzen.addWidget(alt_sekmeler, 1)
        self.sekmeler.addTab(sayfa, 'Klasör tarama')

    # ---------- Kelime arama sekmesi ----------

    def arama_sekmesini_kur(self):
        sayfa = QWidget()
        duzen = QVBoxLayout(sayfa)
        satir = QHBoxLayout()
        self.sorgu = QLineEdit()
        self.sorgu.setPlaceholderText('Kelime yazın: hayat  •  Birden fazla kelime: birine mi muhtaç')
        self.sorgu.returnPressed.connect(self.bul)
        dugme = QPushButton('Ara')
        dugme.clicked.connect(self.bul)
        satir.addWidget(self.sorgu)
        satir.addWidget(dugme)
        duzen.addLayout(satir)
        filtreler = QHBoxLayout()
        filtreler.addWidget(QLabel('Klasör:'))
        self.arama_klasoru = KlasorFiltresi()
        self.arama_klasoru.setMinimumWidth(420)
        self.arama_klasoru.degisti.connect(self.sorgu_varsa_bul)
        filtreler.addWidget(self.arama_klasoru)
        yenile = QPushButton('Listeyi yenile')
        yenile.clicked.connect(self.kokleri_yenile)
        filtreler.addWidget(yenile)
        self.tam_kelime = QCheckBox('Yalnızca tam kelime')
        self.tam_kelime.setToolTip('Kapalıyken "hayat" araması "hayatı", "hayatımız" gibi ekli halleri de bulur.')
        self.tam_kelime.toggled.connect(self.sorgu_varsa_bul)
        filtreler.addWidget(self.tam_kelime)
        filtreler.addWidget(QLabel('Kapsam:'))
        self.kapsam = QComboBox()
        self.kapsam.addItem('Aynı videoda (parçalı)', 'video')
        self.kapsam.addItem('Aynı satırda', 'satir')
        self.kapsam.setToolTip('Aynı videoda: her kelime ayrı aranır; hepsinin geçtiği videolardaki ilgili satırlar listelenir.\n'
                               'Aynı satırda: tüm kelimeler aynı altyazı satırında olmalıdır.')
        self.kapsam.currentIndexChanged.connect(self.sorgu_varsa_bul)
        filtreler.addWidget(self.kapsam)
        self.onizleme_goster = QCheckBox('Görüntüleri göster')
        self.onizleme_goster.setToolTip('İlk eşleşme saniyesindeki kare arka planda üretilir ve veriler\\onizlemeler klasöründe saklanır.')
        self.onizleme_goster.setChecked(self.ayarlar.value('search/thumbnails', True, type=bool))
        self.onizleme_goster.toggled.connect(self.onizleme_degisti)
        filtreler.addWidget(self.onizleme_goster)
        filtreler.addStretch()
        duzen.addLayout(filtreler)
        araliklar = QHBoxLayout()
        self.arama_suresi = AralikFiltresi('Süre:', ' dk', 60, 100000)
        self.arama_boyutu = AralikFiltresi('Boyut:', ' MB', 1024 * 1024, 10_000_000)
        for bilesen in (self.arama_suresi, self.arama_boyutu):
            bilesen.degisti.connect(self.sorgu_varsa_bul)
            araliklar.addWidget(bilesen)
        araliklar.addWidget(QLabel('(isteğe bağlı; — sınır yok. Süresi henüz okunmamış videolar süre filtresinde listelenmez.)'))
        araliklar.addStretch()
        duzen.addLayout(araliklar)
        self.sayi = QLabel('Büyük/küçük harf ve Türkçe karakter duyarsızdır: "dusunce" yazınca "Düşünce" de bulunur.')
        duzen.addWidget(self.sayi)
        self.tablo = QTableWidget(0, 5)
        self.tablo.setHorizontalHeaderLabels(['Video / tam yol', 'İlk eşleşme', 'Eşleşen satır', 'Altyazı (ilk eşleşen satır)', 'Görüntü'])
        self.tablo.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tablo.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tablo.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tablo.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tablo.horizontalHeader().moveSection(ONIZLEME_SUTUNU, 0)
        self.tablo.setColumnWidth(ONIZLEME_SUTUNU, ONIZLEME_GENISLIGI + 8)
        self.tablo.setIconSize(QSize(ONIZLEME_GENISLIGI, ONIZLEME_YUKSEKLIGI))
        self.tablo.setColumnWidth(0, 350)
        self.tablo.cellDoubleClicked.connect(lambda *_: self.detay_goster())
        self.tablo.verticalScrollBar().valueChanged.connect(self.gorunen_onizlemeleri_one_al)
        self.onizleme_satirlari = {}
        self.onizleme_yukleyici = OnizlemeYukleyici(self)
        self.onizleme_yukleyici.hazir.connect(self.onizleme_hazir)
        self.onizleme_yukleyici.start()
        self.tablo.setColumnHidden(ONIZLEME_SUTUNU, not self.onizleme_goster.isChecked())
        duzen.addWidget(self.tablo)
        dugmeler = QHBoxLayout()
        for etiket, islev in [('Detay', self.detay_goster), ('Videoyu aç', self.videoyu_ac), ('Klasörünü aç', self.klasoru_ac),
                              ('Seçili videonun SRT dosyasını kaydet', self.srt_kaydet),
                              ('Tüm altyazıları SRT olarak dışa aktar', self.tumunu_aktar)]:
            dugme = QPushButton(etiket)
            dugme.clicked.connect(islev)
            dugmeler.addWidget(dugme)
        duzen.addLayout(dugmeler)
        duzen.addWidget(QLabel('Detay (veya satıra çift tıklama): videonun tüm altyazısı ve oynatıcı açılır; video seçili satırın saniyesinden başlar.'))
        self.sekmeler.addTab(sayfa, 'Kelime arama / SRT')

    # ---------- Ayarlar sekmesi ve zamanlayıcı ----------

    def ayarlar_sekmesini_kur(self):
        self.ayarlar_sayfasi = QWidget()
        sayfa = QVBoxLayout(self.ayarlar_sayfasi)
        form = QFormLayout()
        self.birim = QComboBox()
        for etiket, deger in [('Otomatik (GPU varsa GPU)', 'auto'), ('GPU (NVIDIA CUDA)', 'cuda'), ('CPU', 'cpu')]:
            self.birim.addItem(etiket, deger)
        self.birim.setCurrentIndex(max(0, self.birim.findData(self.ayarlar.value('processing/device', 'auto', type=str))))
        self.birim.currentIndexChanged.connect(lambda: self.ayarlar.setValue('processing/device', self.birim.currentData()))
        form.addRow('İşlem birimi:', self.birim)
        self.gpu_notu = QLabel('')
        self.gpu_notu.setWordWrap(True)
        form.addRow('GPU durumu:', self.gpu_notu)
        sayfa.addLayout(form)
        not_ = QLabel('Ayarlar bir sonraki taramada geçerli olur. GPU başlatılamazsa işlem CPU ile sürer ve bu durum Detaylı log sekmesine yazılır.')
        not_.setWordWrap(True)
        sayfa.addWidget(not_)
        sayfa.addWidget(self.zamanlayici_kutusunu_kur())
        sayfa.addStretch()
        self.sekmeler.addTab(self.ayarlar_sayfasi, 'Ayarlar')

    def zamanlayici_kutusunu_kur(self):
        kutu = QGroupBox('Otomatik tarama zamanlayıcısı')
        duzen = QVBoxLayout(kutu)
        self.zamanlayici_acik = QCheckBox('Belirlenen saatlerde otomatik tara')
        self.zamanlayici_acik.setChecked(self.ayarlar.value('schedule/enabled', False, type=bool))
        duzen.addWidget(self.zamanlayici_acik)
        satir = QHBoxLayout()
        self.zaman_baslangic, self.zaman_bitis = QTimeEdit(), QTimeEdit()
        for kutucuk, anahtar, varsayilan in ((self.zaman_baslangic, 'start', '20:00'), (self.zaman_bitis, 'end', '07:00')):
            kutucuk.setDisplayFormat('HH:mm')
            deger = saat_coz(self.ayarlar.value(f'schedule/{anahtar}', varsayilan, type=str), saat_coz(varsayilan, None))
            kutucuk.setTime(QTime(deger.hour, deger.minute))
        satir.addWidget(QLabel('Başlangıç:'))
        satir.addWidget(self.zaman_baslangic)
        satir.addWidget(QLabel('Bitiş:'))
        satir.addWidget(self.zaman_bitis)
        satir.addStretch()
        duzen.addLayout(satir)
        bilgi = QLabel('Başlangıç saatinde, Klasör tarama sekmesindeki işaretli klasörler ve ayarlarla (model, dil, süre filtresi, '
                       'eksik bilgileri tamamla) tarama başlar. "İşlenenleri yeniden oluştur" otomatik taramada kullanılmaz.\n'
                       'Bitiş saatinde işlenmekte olan video tamamlanır, sıradaki videolar bir sonraki aralığa kalır. '
                       'Bitiş başlangıçtan küçükse aralık gece yarısını aşar (ör. 20:00 – 07:00).\n'
                       'Her aralıkta bir kez çalışır. Uygulamanın açık kalması gerekir; tarama sürerken bilgisayarın uykuya geçmesi engellenir.')
        bilgi.setWordWrap(True)
        duzen.addWidget(bilgi)
        self.zamanlayici_durumu = QLabel('')
        self.zamanlayici_durumu.setWordWrap(True)
        duzen.addWidget(self.zamanlayici_durumu)
        self.zamanlayici_acik.toggled.connect(self.zamanlayici_degisti)
        self.zaman_baslangic.timeChanged.connect(self.zamanlayici_degisti)
        self.zaman_bitis.timeChanged.connect(self.zamanlayici_degisti)
        return kutu

    def zamanlayici_saatleri(self):
        return (saat_coz(self.zaman_baslangic.time().toString('HH:mm'), None),
                saat_coz(self.zaman_bitis.time().toString('HH:mm'), None))

    def zamanlayici_degisti(self):
        baslangic, bitis = self.zamanlayici_saatleri()
        self.ayarlar.setValue('schedule/enabled', self.zamanlayici_acik.isChecked())
        self.ayarlar.setValue('schedule/start', baslangic.strftime('%H:%M'))
        self.ayarlar.setValue('schedule/end', bitis.strftime('%H:%M'))
        self.zamanlayici_tik()

    def zamanli_tarama_metni(self, aralik, baslangic, bitis):
        return (f'Otomatik tarama sürüyor; {aralik_sonu(aralik, baslangic, bitis):%d.%m.%Y %H:%M} '
                'itibarıyla işlenmekte olan video bitince durdurulacak.')

    def zamanlayici_tik(self):
        """Zamanlayıcı: aralığa girildiyse taramayı başlatır, bitiş saati geldiyse yumuşak durdurur."""
        simdi = datetime.now()
        baslangic, bitis = self.zamanlayici_saatleri()
        calisiyor = bool(self.isci and self.isci.isRunning())
        if self.zamanli_calisma and calisiyor and not self.isci.yumusak_dur and simdi >= self.zamanli_bitis:
            self.isci.mevcut_isi_bitir()
            self.gunluk.appendPlainText(f'[{simdi:%H:%M}] Zamanlayıcı: bitiş saati geldi; işlenmekte olan video tamamlanıp durdurulacak.')
            self.durum.setText('Zamanlayıcı bitiş saati: işlenmekte olan video tamamlanıp durdurulacak...')
        if self.zamanli_calisma and calisiyor:
            self.zamanlayici_durumu.setText(self.zamanli_tarama_metni(self.zamanli_aralik, baslangic, bitis))
            return
        if not self.zamanlayici_acik.isChecked():
            self.zamanlayici_durumu.setText('Zamanlayıcı kapalı.')
            return
        if baslangic == bitis:
            self.zamanlayici_durumu.setText('Başlangıç ve bitiş saati aynı olamaz.')
            return
        aralik = etkin_aralik(simdi, baslangic, bitis)
        anahtar = aralik.isoformat(timespec='minutes') if aralik else None
        if aralik and anahtar != self.ayarlar.value('schedule/last_window', '', type=str):
            if calisiyor:
                self.zamanlayici_durumu.setText('Otomatik tarama zamanı geldi; devam eden işlem bitince başlayacak.')
                return
            self.ayarlar.setValue('schedule/last_window', anahtar)
            self.gunluk.appendPlainText(f'[{simdi:%H:%M}] Zamanlayıcı: otomatik tarama başlatılıyor.')
            if self.taramayi_baslat(otomatik=True):
                self.zamanli_calisma, self.zamanli_aralik = True, aralik
                self.zamanli_bitis = aralik_sonu(aralik, baslangic, bitis)
                self.zamanlayici_durumu.setText(self.zamanli_tarama_metni(aralik, baslangic, bitis))
                return
        sonraki = sonraki_baslangic(simdi, baslangic, bitis)
        self.zamanlayici_durumu.setText(f'Sonraki otomatik tarama: {sonraki:%d.%m.%Y %H:%M} – '
                                        f'{aralik_sonu(sonraki, baslangic, bitis):%d.%m.%Y %H:%M}')

    def sekme_degisti(self):
        gecerli = self.sekmeler.currentWidget()
        if gecerli is self.liste_sayfasi and not self.liste_yuklendi:
            self.videolari_yukle()
        elif gecerli is self.ayarlar_sayfasi and not self.gpu_notu.text():
            self.gpu_notu.setText(gpu_durumu()[1])

    # ---------- Video listesi sekmesi ----------

    def video_listesini_kur(self):
        self.liste_sayfasi = QWidget()
        self.liste_yuklendi, self.liste_sayfa_no, self.liste_sirasi, self.liste_azalan = False, 1, 'yol', False
        duzen = QVBoxLayout(self.liste_sayfasi)
        filtreler = QHBoxLayout()
        filtreler.addWidget(QLabel('Klasör:'))
        self.liste_klasoru = KlasorFiltresi()
        self.liste_klasoru.setMinimumWidth(300)
        self.liste_klasoru.degisti.connect(lambda: self.videolari_yukle())
        filtreler.addWidget(self.liste_klasoru)
        filtreler.addWidget(QLabel('Model / dil:'))
        self.liste_modeli = QComboBox()
        self.liste_modeli.setMinimumWidth(180)
        self.liste_modeli.currentIndexChanged.connect(lambda: self.videolari_yukle())
        filtreler.addWidget(self.liste_modeli)
        self.liste_adi = QLineEdit()
        self.liste_adi.setPlaceholderText('Ad / yol içerir (isteğe bağlı)')
        self.liste_adi.returnPressed.connect(lambda: self.videolari_yukle())
        filtreler.addWidget(self.liste_adi)
        duzen.addLayout(filtreler)
        araliklar = QHBoxLayout()
        self.liste_suresi = AralikFiltresi('Süre:', ' dk', 60, 100000)
        self.liste_boyutu = AralikFiltresi('Boyut:', ' MB', 1024 * 1024, 10_000_000)
        for bilesen in (self.liste_suresi, self.liste_boyutu):
            bilesen.degisti.connect(lambda: self.videolari_yukle())
            araliklar.addWidget(bilesen)
        uygula = QPushButton('Uygula / yenile')
        uygula.clicked.connect(lambda: self.videolari_yukle(self.liste_sayfa_no))
        araliklar.addWidget(uygula)
        araliklar.addStretch()
        duzen.addLayout(araliklar)
        self.liste_tablosu = QTableWidget(0, len(LISTE_SUTUNLARI))
        self.liste_tablosu.setHorizontalHeaderLabels([etiket for etiket, _ in LISTE_SUTUNLARI])
        self.liste_tablosu.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.liste_tablosu.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.liste_tablosu.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.liste_tablosu.verticalHeader().setDefaultSectionSize(26)
        baslik = self.liste_tablosu.horizontalHeader()
        baslik.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        baslik.setSortIndicatorShown(True)
        baslik.setSortIndicator(0, Qt.SortOrder.AscendingOrder)
        baslik.sectionClicked.connect(self.videolari_sirala)
        for sutun, genislik in enumerate((0, 55, 75, 85, 95, 55, 110, 240)):
            if genislik:
                self.liste_tablosu.setColumnWidth(sutun, genislik)
        self.liste_tablosu.cellDoubleClicked.connect(lambda *_: self.detay_goster())
        duzen.addWidget(self.liste_tablosu)
        sayfalama = QHBoxLayout()
        self.liste_bilgisi = QLabel('')
        sayfalama.addWidget(self.liste_bilgisi)
        sayfalama.addStretch()
        sayfalama.addWidget(QLabel('Sayfa başına:'))
        self.sayfa_boyutu = QComboBox()
        self.sayfa_boyutu.addItems(['50', '100', '200', '500'])
        self.sayfa_boyutu.setCurrentText(self.ayarlar.value('list/page_size', '100', type=str))
        self.sayfa_boyutu.currentTextChanged.connect(self.sayfa_boyutu_degisti)
        sayfalama.addWidget(self.sayfa_boyutu)
        self.onceki_sayfa = QPushButton('◀ Önceki')
        self.onceki_sayfa.clicked.connect(lambda: self.videolari_yukle(self.liste_sayfa_no - 1))
        sayfalama.addWidget(self.onceki_sayfa)
        sayfalama.addWidget(QLabel('Sayfa'))
        self.sayfa_numarasi = QSpinBox()
        self.sayfa_numarasi.setKeyboardTracking(False)
        self.sayfa_numarasi.valueChanged.connect(lambda no: no != self.liste_sayfa_no and self.videolari_yukle(no))
        sayfalama.addWidget(self.sayfa_numarasi)
        self.sayfa_sayisi = QLabel('/ 1')
        sayfalama.addWidget(self.sayfa_sayisi)
        self.sonraki_sayfa = QPushButton('Sonraki ▶')
        self.sonraki_sayfa.clicked.connect(lambda: self.videolari_yukle(self.liste_sayfa_no + 1))
        sayfalama.addWidget(self.sonraki_sayfa)
        duzen.addLayout(sayfalama)
        dugmeler = QHBoxLayout()
        for etiket, islev in [('Detay', self.detay_goster), ('Videoyu aç', self.videoyu_ac), ('Klasörünü aç', self.klasoru_ac),
                              ('Seçili videonun SRT dosyasını kaydet', self.srt_kaydet)]:
            dugme = QPushButton(etiket)
            dugme.clicked.connect(islev)
            dugmeler.addWidget(dugme)
        duzen.addLayout(dugmeler)
        yeniden = QHBoxLayout()
        for etiket, islev in [('Seçilileri yeniden işle', self.secilileri_yeniden_isle),
                              ('Filtreye uyan tüm videoları yeniden işle', self.filtreyi_yeniden_isle),
                              ('Kopuk bağları kontrol et', self.baglari_kontrol_et)]:
            dugme = QPushButton(etiket)
            dugme.clicked.connect(islev)
            yeniden.addWidget(dugme)
        duzen.addLayout(yeniden)
        duzen.addWidget(QLabel('Sütun başlığına tıklayarak sıralayın. Ctrl / Shift ile birden çok satır seçilir. Boş süre/MD5: bilgi henüz okunmadı '
                               '(tarama sekmesinde "Eksik video bilgilerini ve MD5 değerlerini tamamla").'))
        self.sekmeler.addTab(self.liste_sayfasi, 'Video listesi')

    def videolari_sirala(self, sutun):
        anahtar = LISTE_SUTUNLARI[sutun][1]
        self.liste_azalan = not self.liste_azalan if anahtar == self.liste_sirasi else False
        self.liste_sirasi = anahtar
        self.liste_tablosu.horizontalHeader().setSortIndicator(
            sutun, Qt.SortOrder.DescendingOrder if self.liste_azalan else Qt.SortOrder.AscendingOrder)
        self.videolari_yukle()

    def sayfa_boyutu_degisti(self, boyut):
        self.ayarlar.setValue('list/page_size', boyut)
        self.videolari_yukle()

    def videolari_yukle(self, sayfa=1):
        try:
            boyut = int(self.sayfa_boyutu.currentText())
            toplam, satirlar = videolari_listele(
                self.db, kokler=self.liste_klasoru.secili(), ad=self.liste_adi.text(),
                sure=self.liste_suresi.sinirlar(), boyut=self.liste_boyutu.sinirlar(),
                model=self.liste_modeli.currentData(), sira=self.liste_sirasi, azalan=self.liste_azalan,
                sinir=boyut, atla=(max(1, sayfa) - 1) * boyut)
        except Exception as hata:
            QMessageBox.warning(self, 'Video listesi', str(hata))
            return
        sayfalar = max(1, math.ceil(toplam / boyut))
        if sayfa > sayfalar or sayfa < 1:
            return self.videolari_yukle(min(max(1, sayfa), sayfalar))
        self.liste_yuklendi, self.liste_sayfa_no = True, sayfa
        sag = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        self.liste_tablosu.setRowCount(len(satirlar))
        for i, satir in enumerate(satirlar):
            cozunurluk = f"{satir['width']}×{satir['height']}" if satir['width'] and satir['height'] else ''
            degerler = [(satir['path'], satir['path'], None),
                        (satir['format'] or '', None, Qt.AlignmentFlag.AlignCenter),
                        (saat(round(satir['duration'] * 1000)) if satir['duration'] is not None else '', None, sag),
                        (okunur_boyut(satir['size']), f"{satir['size']:,} bayt".replace(',', '.'), sag),
                        (cozunurluk, satir['codec'], Qt.AlignmentFlag.AlignCenter),
                        (str(satir['satir']), None, sag),
                        (f"{satir['model']} / {satir['language']}", None, None),
                        (satir['md5'] or '', None, None)]
            for j, (metin, ipucu, hiza) in enumerate(degerler):
                oge = QTableWidgetItem(metin)
                if ipucu:
                    oge.setToolTip(str(ipucu))
                if hiza is not None:
                    oge.setTextAlignment(hiza)
                self.liste_tablosu.setItem(i, j, oge)
        self.sayfa_numarasi.blockSignals(True)
        self.sayfa_numarasi.setRange(1, sayfalar)
        self.sayfa_numarasi.setValue(sayfa)
        self.sayfa_numarasi.blockSignals(False)
        self.sayfa_sayisi.setText(f'/ {sayfalar}')
        self.onceki_sayfa.setEnabled(sayfa > 1)
        self.sonraki_sayfa.setEnabled(sayfa < sayfalar)
        ilk = (sayfa - 1) * boyut + 1 if satirlar else 0
        self.liste_bilgisi.setText(f'{toplam} video • {ilk}–{ilk + len(satirlar) - 1 if satirlar else 0} gösteriliyor')
        self.liste_tablosu.scrollToTop()

    def baglari_kontrol_et(self):
        KopukBagPenceresi(self, self.db, self.klasor_yollari()).exec()
        self.kokleri_yenile()
        self.videolari_yukle(self.liste_sayfa_no)

    def secilileri_yeniden_isle(self):
        satirlar = self.liste_tablosu.selectionModel().selectedRows()
        self.yeniden_isle([self.liste_tablosu.item(indeks.row(), 0).text() for indeks in satirlar])

    def filtreyi_yeniden_isle(self):
        try:
            self.yeniden_isle(video_yollari(self.db, kokler=self.liste_klasoru.secili(), ad=self.liste_adi.text(),
                                            sure=self.liste_suresi.sinirlar(), boyut=self.liste_boyutu.sinirlar(),
                                            model=self.liste_modeli.currentData()))
        except Exception as hata:
            QMessageBox.warning(self, 'Yeniden işle', str(hata))

    def yeniden_isle(self, yollar):
        if self.isci and self.isci.isRunning():
            QMessageBox.information(self, 'Yeniden işle', 'Devam eden işlem bitmeden yeni işlem başlatılamaz.')
            return
        if not yollar:
            QMessageBox.information(self, 'Yeniden işle', 'İşlenecek video yok. Önce listeden video seçin veya filtreyi değiştirin.')
            return
        pencere = YenidenIslePenceresi(self, len(yollar), self.model.currentText(), self.dil.currentData())
        if pencere.exec() != QDialog.DialogCode.Accepted:
            return
        self.sekmeler.setCurrentIndex(0)
        self.isciyi_baslat([], pencere.model.currentText(), pencere.dil.currentData(), True, SureFiltresi(), False, yollar)

    def etkin_tablo(self):
        return self.liste_tablosu if self.sekmeler.currentWidget() is self.liste_sayfasi else self.tablo

    # ---------- Klasör listesi ----------

    def klasorleri_yukle(self):
        isaretsiz = set(self.ayarlar.value('folders/unchecked', '', type=str).splitlines())
        for satir in self.ayarlar.value('folders/paths', '\n'.join(VARSAYILAN_KLASORLER), type=str).splitlines():
            yol = satir.strip().strip('"')
            if yol:
                self.klasor_ogesi_ekle(yol, yol not in isaretsiz)
        self.klasorler.itemChanged.connect(lambda: self.klasorleri_kaydet())

    def klasor_ogesi_ekle(self, yol, isaretli=True):
        oge = QListWidgetItem(yol)
        oge.setFlags(oge.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        oge.setCheckState(Qt.CheckState.Checked if isaretli else Qt.CheckState.Unchecked)
        self.klasorler.addItem(oge)

    def klasor_yollari(self, yalniz_isaretli=False):
        ogeler = [self.klasorler.item(i) for i in range(self.klasorler.count())]
        return [oge.text() for oge in ogeler if not yalniz_isaretli or oge.checkState() == Qt.CheckState.Checked]

    def klasor_ekle(self):
        klasor = QFileDialog.getExistingDirectory(self, 'Video klasörü seçin')
        if not klasor:
            return
        klasor = os.path.normpath(klasor)
        anahtar = os.path.normcase(klasor)
        if any(os.path.normcase(os.path.normpath(yol)) == anahtar for yol in self.klasor_yollari()):
            QMessageBox.information(self, 'Klasör ekle', 'Bu klasör listede zaten var.')
            return
        self.klasor_ogesi_ekle(klasor)
        self.klasorleri_kaydet()

    def klasorleri_cikar(self):
        """Klasörü yalnızca listeden çıkarır; kayıtlı altyazılara dokunmaz."""
        for oge in self.klasorler.selectedItems():
            self.klasorler.takeItem(self.klasorler.row(oge))
        self.klasorleri_kaydet()

    def klasorleri_isaretle(self, isaretli):
        self.klasorler.blockSignals(True)
        for i in range(self.klasorler.count()):
            self.klasorler.item(i).setCheckState(Qt.CheckState.Checked if isaretli else Qt.CheckState.Unchecked)
        self.klasorler.blockSignals(False)
        self.klasorleri_kaydet()

    def klasorleri_kaydet(self):
        isaretli = set(self.klasor_yollari(yalniz_isaretli=True))
        self.ayarlar.setValue('folders/paths', '\n'.join(self.klasor_yollari()))
        self.ayarlar.setValue('folders/unchecked', '\n'.join(y for y in self.klasor_yollari() if y not in isaretli))
        self.ayarlar.sync()
        if self.ayarlar.status() != QSettings.Status.NoError:
            QMessageBox.warning(self, 'Klasör listesi kaydedilemedi',
                                'veriler/ayarlar.ini dosyasına yazılamadı. Ağ bağlantısını ve yazma iznini kontrol edin.')
            return False
        return True

    def sure_kontrollerini_guncelle(self):
        mod = self.sure_modu.currentData()
        for bilesen in (self.sure_alt_etiketi, self.sure_alt):
            bilesen.setVisible(mod in ('en_az', 'arasinda'))
        for bilesen in (self.sure_ust_etiketi, self.sure_ust):
            bilesen.setVisible(mod in ('en_fazla', 'arasinda'))

    # ---------- Tarama ve ilerleme ----------

    def taramayi_baslat(self, otomatik=False):
        """otomatik: zamanlayıcıdan başlatıldı; uyarılar pencere açmadan loga yazılır, erişilemeyen klasörler atlanır.
        Tarama başladıysa True döner."""
        def uyar(baslik, metin):
            if otomatik:
                self.gunluk.appendPlainText(f'Zamanlayıcı — {baslik}: {metin}')
                self.durum.setText(f'Otomatik tarama başlatılamadı: {metin}')
            else:
                QMessageBox.warning(self, baslik, metin)
        if not otomatik and not self.klasorleri_kaydet():
            return False
        try:
            sure_filtresi = SureFiltresi(self.sure_modu.currentData(), self.sure_alt.value(), self.sure_ust.value())
        except ValueError as hata:
            uyar('Süre filtresi', str(hata))
            return False
        kokler = self.klasor_yollari(yalniz_isaretli=True)
        if not kokler:
            uyar('Klasör kontrolü', 'Taranacak en az bir klasör işaretleyin.')
            return False
        erisilemeyen = [y for y in kokler if not Path(y).is_dir()]
        if erisilemeyen and not otomatik:
            uyar('Klasör kontrolü', 'Bu klasörlere erişilemiyor:\n' + '\n'.join(erisilemeyen))
            return False
        if erisilemeyen:
            self.gunluk.appendPlainText('Zamanlayıcı — erişilemeyen klasörler atlandı:\n' + '\n'.join(erisilemeyen))
            kokler = [y for y in kokler if y not in erisilemeyen]
            if not kokler:
                uyar('Klasör kontrolü', 'İşaretli klasörlerin hiçbirine erişilemiyor.')
                return False
        self.durum.setText('Otomatik tarama: klasörler taranıyor...' if otomatik else 'Klasörler taranıyor...')
        self.isciyi_baslat(kokler, self.model.currentText(), self.dil.currentData(),
                           False if otomatik else self.yeniden_olustur.isChecked(),
                           sure_filtresi, self.bilgi_tamamla.isChecked())
        return True

    def isciyi_baslat(self, kokler, model, dil, yeniden, sure_filtresi, bilgi_tamamla, yollar=None):
        self.baslat_dugmesi.setEnabled(False)
        self.durdur_dugmesi.setEnabled(True)
        self.ilerleme.setRange(0, 0)
        self.tarama_listesi.setRowCount(0)
        self.tarama_satirlari = {}
        self.oge_etkin = False
        self.ilerleme_sayilari = None
        self.tarama_saati.start()
        self.isci = TaramaIscisi(kokler, model, dil, yeniden, sure_filtresi, bilgi_tamamla, self.birim.currentData(), yollar)
        for bilesen in (self.sure_modu, self.sure_alt, self.sure_ust, self.bilgi_tamamla):
            bilesen.setEnabled(False)
        self.isci.gunluk.connect(self.gunluk.appendPlainText)
        self.isci.asama.connect(self.asamayi_guncelle)
        self.isci.ilerleme.connect(self.ilerlemeyi_guncelle)
        self.isci.icerik_ilerlemesi.connect(self.icerigi_guncelle)
        self.isci.ogeler_kuyrukta.connect(self.ogeler_kuyrukta)
        self.isci.oge_basladi.connect(self.oge_basladi)
        self.isci.oge_ayrintisi.connect(self.oge_ayrintisi)
        self.isci.oge_ilerlemesi.connect(self.oge_ilerlemesi)
        self.isci.oge_bitti.connect(self.oge_bitti)
        self.isci.sonuc.connect(self.tarama_sonucu)
        self.isci.finished.connect(self.isci_bitti)
        uyanik_tut(True)
        self.isci.start()

    def ogeler_kuyrukta(self, ogeler, is_turu):
        """İşlenecek videoların tamamı baştan listelenir; sırası gelince durumu değişir."""
        tablo = self.tarama_listesi
        sag = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        satir = tablo.rowCount()
        tablo.setUpdatesEnabled(False)
        tablo.setRowCount(satir + len(ogeler))
        for yol, boyut, sure in ogeler:
            self.tarama_satirlari[(yol, is_turu)] = satir
            for sutun, (metin, hiza) in enumerate([
                    (Path(yol).name, None), (str(Path(yol).parent), None), (dosya_turu(yol), Qt.AlignmentFlag.AlignCenter),
                    (okunur_boyut(boyut), sag), (saat(round(sure * 1000)) if sure is not None else '', sag),
                    (is_turu, None), ('Bekliyor', None), ('', sag), ('', sag)]):
                oge = QTableWidgetItem(metin)
                if hiza is not None:
                    oge.setTextAlignment(hiza)
                tablo.setItem(satir, sutun, oge)
            tablo.item(satir, 0).setToolTip(yol)
            tablo.item(satir, 1).setToolTip(str(Path(yol).parent))
            satir += 1
        tablo.setUpdatesEnabled(True)

    def oge_basladi(self, yol, is_turu):
        tablo = self.tarama_listesi
        self.oge_satiri = self.tarama_satirlari[(yol, is_turu)]
        tablo.item(self.oge_satiri, SUTUN_DURUM).setText('İşleniyor')
        self.oge_cubugu = QProgressBar()
        self.oge_cubugu.setRange(0, 100)
        self.oge_cubugu.setValue(0)
        tablo.setCellWidget(self.oge_satiri, SUTUN_CUBUK, self.oge_cubugu)
        tablo.scrollToItem(tablo.item(self.oge_satiri, 0), QTableWidget.ScrollHint.PositionAtCenter)
        self.oge_saati = time.monotonic()
        self.oge_etkin = True

    def oge_ayrintisi(self, boyut, sure):
        if boyut is not None:
            self.tarama_listesi.item(self.oge_satiri, SUTUN_BOYUT).setText(okunur_boyut(boyut))
        if sure is not None:
            self.tarama_listesi.item(self.oge_satiri, SUTUN_SURE).setText(saat(round(sure * 1000)))

    def oge_ilerlemesi(self, yuzde):
        self.oge_cubugu.setValue(yuzde)

    def oge_suresini_goster(self):
        self.tarama_listesi.item(self.oge_satiri, SUTUN_GECEN).setText(saat(round((time.monotonic() - self.oge_saati) * 1000)))

    def oge_bitti(self, durum, not_):
        tablo = self.tarama_listesi
        satir = self.oge_satiri
        yuzde = self.oge_cubugu.value()
        self.oge_cubugu.hide()
        tablo.removeCellWidget(satir, SUTUN_CUBUK)
        tablo.item(satir, SUTUN_CUBUK).setText(f'%{100 if durum == "Tamamlandı" else yuzde}')
        self.oge_suresini_goster()
        tablo.item(satir, SUTUN_DURUM).setText(durum)
        if durum == 'Hata':
            tablo.item(satir, SUTUN_DURUM).setForeground(QColor('#c62828'))
        if not_:
            tablo.item(satir, SUTUN_DURUM).setToolTip(not_)
        self.oge_etkin = False

    def tarama_tik(self):
        if self.oge_etkin:
            self.oge_suresini_goster()
        self.ilerlemeyi_goster()

    def tarama_sonucu(self, metin):
        self.tarama_saati.stop()
        self.oge_etkin = False
        self.durum.setText(metin)

    def asamayi_guncelle(self, ad, toplam):
        """toplam yalnızca bu aşamada gerçekten işlenecek video sayısıdır; -1 süresiz bekleme."""
        self.asama_adi = ad
        self.icerik_ilerleme = None
        self.tahmin_baslangici = None
        if toplam < 0:
            self.ilerleme_sayilari = None
            self.ilerleme.setRange(0, 0)
            self.durum.setText(ad + '...')
        else:
            self.ilerlemeyi_guncelle(0, toplam)

    def ilerlemeyi_guncelle(self, mevcut, toplam):
        self.ilerleme_sayilari = (mevcut, toplam)
        self.ilerlemeyi_goster()

    def icerigi_guncelle(self, biten, toplam):
        self.icerik_ilerleme = (biten, toplam)
        self.ilerlemeyi_goster()

    def ilerlemeyi_goster(self):
        """Altyazı aşamasında çubuk ve kalan süre içerik süresine, diğer aşamalarda video adedine göredir."""
        if not self.ilerleme_sayilari:
            return
        ad = getattr(self, 'asama_adi', 'İşleniyor')
        mevcut, toplam = self.ilerleme_sayilari
        if not toplam:
            self.ilerleme.setRange(0, 1)
            self.ilerleme.setValue(1)
            self.ilerleme.setFormat(f'{ad}: işlenecek video yok')
            return
        icerik = self.icerik_ilerleme
        if icerik and icerik[1] > 0:
            deger, en_fazla = icerik
            yuzde = f'%{deger * 100 / en_fazla:.1f}'.replace('.', ',')
            self.ilerleme.setRange(0, 10000)
            self.ilerleme.setValue(int(deger * 10000 / en_fazla))
            self.ilerleme.setFormat(f'{ad}: {yuzde}  ({saat(round(deger * 1000))} / {saat(round(en_fazla * 1000))} içerik)')
        else:
            deger, en_fazla = mevcut, toplam
            self.ilerleme.setRange(0, toplam)
            self.ilerleme.setValue(mevcut)
            self.ilerleme.setFormat(f'{ad}: %v / %m  (%p%)')
        if self.tahmin_baslangici is None and deger > 0:
            self.tahmin_baslangici = (time.monotonic(), deger)
        metin = f'{ad}: {mevcut} / {toplam} video'
        if self.tahmin_baslangici and deger < en_fazla:
            kalan = kalan_sure_tahmini(deger, en_fazla, self.tahmin_baslangici[1], time.monotonic() - self.tahmin_baslangici[0])
            metin += (' • Tahmini kalan: hesaplanıyor...' if kalan is None
                      else f' • Tahmini kalan: {sure_metni(kalan)} • Tahmini bitiş: {bitis_metni(kalan)}')
        self.durum.setText(metin)

    def durdur(self):
        if self.isci:
            self.isci.requestInterruption()
            self.durdur_dugmesi.setEnabled(False)
            self.durum.setText('Durduruluyor; devam eden model yükleme / ses çözümleme adımı bekleniyor...')

    def isci_bitti(self):
        uyanik_tut(False)
        if self.zamanli_calisma:
            self.zamanli_calisma = False
            self.gunluk.appendPlainText(f'[{datetime.now():%H:%M}] Zamanlayıcı: otomatik tarama sona erdi. {self.durum.text()}')
            QTimer.singleShot(0, self.zamanlayici_tik)
        for bilesen in (self.sure_modu, self.sure_alt, self.sure_ust, self.bilgi_tamamla):
            bilesen.setEnabled(True)
        self.baslat_dugmesi.setEnabled(True)
        self.durdur_dugmesi.setEnabled(False)
        if self.ilerleme.maximum() == 0:
            self.ilerleme.setRange(0, 1)
        self.kokleri_yenile()
        if self.liste_yuklendi:
            self.videolari_yukle(self.liste_sayfa_no)

    def kokleri_yenile(self):
        try:
            kokler = kokleri_listele(self.db, self.klasor_yollari())
            self.arama_klasoru.klasorleri_ayarla(kokler)
            self.liste_klasoru.klasorleri_ayarla(kokler)
            self.modelleri_yenile()
        except Exception as hata:
            QMessageBox.warning(self, 'Klasör listesi', str(hata))

    def modelleri_yenile(self):
        gecerli = self.liste_modeli.currentData()
        self.liste_modeli.blockSignals(True)
        self.liste_modeli.clear()
        self.liste_modeli.addItem('Tüm modeller', None)
        for model, dil, sayi in modelleri_listele(self.db):
            self.liste_modeli.addItem(f'{model} / {dil}  ({sayi} video)', (model, dil))
            if (model, dil) == gecerli:
                self.liste_modeli.setCurrentIndex(self.liste_modeli.count() - 1)
        self.liste_modeli.blockSignals(False)

    # ---------- Önizlemeler ----------

    def onizleme_degisti(self, acik):
        self.ayarlar.setValue('search/thumbnails', acik)
        self.tablo.setColumnHidden(ONIZLEME_SUTUNU, not acik)
        if not acik:
            for satir in range(self.tablo.rowCount()):
                oge = self.tablo.item(satir, ONIZLEME_SUTUNU)
                if oge and oge.data(Qt.ItemDataRole.DecorationRole) is None:
                    oge.setText('')
        self.onizlemeleri_yukle()

    def onizlemeleri_yukle(self):
        acik = self.onizleme_goster.isChecked()
        self.tablo.verticalHeader().setDefaultSectionSize(ONIZLEME_YUKSEKLIGI + 6 if acik else 30)
        if not acik:
            self.onizleme_yukleyici.temizle()
            return
        bekleyen = []
        for anahtar, satir in self.onizleme_satirlari.items():
            oge = self.tablo.item(satir, ONIZLEME_SUTUNU)
            if oge and oge.data(Qt.ItemDataRole.DecorationRole) is None:
                oge.setText('Yükleniyor…')
                bekleyen.append(anahtar)
        self.onizleme_yukleyici.iste(bekleyen)
        self.gorunen_onizlemeleri_one_al()

    def gorunen_onizlemeleri_one_al(self, *_):
        if not self.onizleme_goster.isChecked() or not self.onizleme_satirlari:
            return
        ust = max(0, self.tablo.rowAt(0))
        alt = self.tablo.rowAt(self.tablo.viewport().height() - 1)
        alt = self.tablo.rowCount() - 1 if alt < 0 else alt
        gorunen = set(range(ust, alt + 1))
        self.onizleme_yukleyici.one_al([anahtar for anahtar, satir in self.onizleme_satirlari.items() if satir in gorunen])

    def onizleme_hazir(self, yol, saniye, goruntu):
        satir = self.onizleme_satirlari.get((yol, saniye))
        oge = self.tablo.item(satir, ONIZLEME_SUTUNU) if satir is not None else None
        if oge is None:
            return
        if goruntu.isNull():
            oge.setText('Görüntü yok')
            return
        oge.setText('')
        oge.setData(Qt.ItemDataRole.DecorationRole, QPixmap.fromImage(goruntu).scaled(
            ONIZLEME_GENISLIGI, ONIZLEME_YUKSEKLIGI, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    # ---------- Arama ve seçili video işlemleri ----------

    def sorgu_varsa_bul(self, *_):
        if self.sorgu.text().strip():
            self.bul()

    def bul(self):
        try:
            satirlar = ara(self.db, self.sorgu.text(), sinir=50000, kokler=self.arama_klasoru.secili(),
                           tam_kelime=self.tam_kelime.isChecked(), kapsam=self.kapsam.currentData(),
                           sure=self.arama_suresi.sinirlar(), boyut=self.arama_boyutu.sinirlar())
            videolar = {}
            for satir in satirlar:
                videolar.setdefault(satir['path'], []).append(satir)
            gosterilen = list(videolar.items())[:1000]
            self.tablo.setRowCount(len(gosterilen))
            for i, (yol, eslesenler) in enumerate(gosterilen):
                ilk = eslesenler[0]
                onizleme = '\n'.join(f"{zaman_damgasi(s['start'])}  {s['text']}" for s in eslesenler[:15])
                if len(eslesenler) > 15:
                    onizleme += f'\n… {len(eslesenler) - 15} satır daha (Detay)'
                for j, (deger, ipucu) in enumerate([(yol, yol), (zaman_damgasi(ilk['start']), onizleme),
                                                    (str(len(eslesenler)), onizleme), (ilk['text'], onizleme)]):
                    oge = QTableWidgetItem(deger)
                    oge.setToolTip(ipucu)
                    oge.setData(Qt.ItemDataRole.UserRole, ilk['start'])
                    if j == 2:
                        oge.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.tablo.setItem(i, j, oge)
                kucuk_resim = QTableWidgetItem('Yükleniyor…' if self.onizleme_goster.isChecked() else '')
                kucuk_resim.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                kucuk_resim.setData(Qt.ItemDataRole.UserRole, ilk['start'])
                self.tablo.setItem(i, ONIZLEME_SUTUNU, kucuk_resim)
            self.onizleme_satirlari = {(yol, eslesenler[0]['start']): i for i, (yol, eslesenler) in enumerate(gosterilen)}
            self.onizlemeleri_yukle()
            self.son_sorgu = (self.sorgu.text(), self.tam_kelime.isChecked())
            not_ = ' İlk 1000 video gösteriliyor; aramanızı daraltın.' if len(videolar) > 1000 or len(satirlar) == 50000 else ''
            self.sayi.setText(f'{len(videolar)} video ({len(satirlar)} eşleşen satır). Satırların tamamı için Detay.' + not_)
        except Exception as hata:
            QMessageBox.warning(self, 'Arama hatası', str(hata))

    def secili_yol(self):
        tablo = self.etkin_tablo()
        satir = tablo.currentRow()
        return tablo.item(satir, 0).text() if satir >= 0 and tablo.item(satir, 0) else None

    def detay_goster(self):
        yol = self.secili_yol()
        if not yol:
            QMessageBox.information(self, 'Satır seçin', 'Önce listeden bir satır seçin.')
            return
        tablo = self.etkin_tablo()
        baslangic = tablo.item(tablo.currentRow(), 0).data(Qt.ItemDataRole.UserRole) or 0
        sorgu, tam_kelime = getattr(self, 'son_sorgu', ('', False)) if tablo is self.tablo else ('', False)
        try:
            pencere = DetayPenceresi(self, yol, [tuple(s) for s in self.altyazi_satirlari(yol)], baslangic, sorgu, tam_kelime)
        except Exception as hata:
            QMessageBox.warning(self, 'Detay açılamadı', str(hata))
            return
        pencere.exec()

    def videoyu_ac(self):
        yol = self.secili_yol()
        if yol and not QDesktopServices.openUrl(QUrl.fromLocalFile(yol)):
            QMessageBox.warning(self, 'Video açılamadı', 'Dosya yolunu ve varsayılan oynatıcınızı kontrol edin.')

    def klasoru_ac(self):
        yol = self.secili_yol()
        if yol:
            gezginde_goster(yol)

    def altyazi_satirlari(self, yol):
        return self.db.execute('SELECT s.start,s.end,s.text FROM segments s JOIN videos v ON v.id=s.video_id '
                               'WHERE v.path=? ORDER BY s.start', (yol,)).fetchall()

    def srt_kaydet(self):
        yol = self.secili_yol()
        if not yol:
            QMessageBox.information(self, 'Video seçin', 'Önce listeden bir video seçin.')
            return
        hedef, _ = QFileDialog.getSaveFileName(self, 'SRT kaydet', str(Path(yol).with_suffix('.srt')), 'Altyazı (*.srt)')
        if hedef:
            try:
                srt_aktar(self.altyazi_satirlari(yol), hedef)
            except Exception as hata:
                QMessageBox.warning(self, 'Dışa aktarma hatası', str(hata))

    def tumunu_aktar(self):
        klasor = QFileDialog.getExistingDirectory(self, 'SRT dosyalarının kaydedileceği klasör')
        if not klasor:
            return
        try:
            kayitlar = self.db.execute("SELECT id,path FROM videos WHERE status='done'").fetchall()
            for kayit in kayitlar:
                srt_aktar(self.altyazi_satirlari(kayit['path']), Path(klasor) / f"{Path(kayit['path']).stem}_{kayit['id']}.srt")
            QMessageBox.information(self, 'Dışa aktarma', f'{len(kayitlar)} SRT dosyası kaydedildi.')
        except Exception as hata:
            QMessageBox.warning(self, 'Dışa aktarma hatası', str(hata))

    def closeEvent(self, olay):
        if not self.klasorleri_kaydet():
            olay.ignore()
            return
        if self.isci and self.isci.isRunning():
            self.durdur()
            QMessageBox.information(self, 'İşlem durduruluyor', 'İşlem durduktan sonra pencereyi kapatabilirsiniz. Tamamlanan videolar kaydedilmiştir.')
            olay.ignore()
            return
        self.onizleme_yukleyici.durdur()
        self.db.close()
        olay.accept()
