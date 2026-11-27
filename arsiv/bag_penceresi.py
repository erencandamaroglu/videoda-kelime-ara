"""Kopuk bağlar penceresi: diskte bulunamayan kayıtları yeni yerine bağlar veya kayıttan kaldırır."""
import os
import sqlite3
from pathlib import Path

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QDialog, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QMessageBox, QProgressBar,
                             QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout)

from .detay_penceresi import okunur_boyut, saat
from .isci import UZANTILAR, BagIscisi
from .veritabani import videolari_sil, yolu_guncelle

SUTUNLAR = ['Kayıtlı yol', 'Boyut', 'Süre', 'Önerilen yeni yol', 'Neden']
KESIN_RENGI = QColor('#2e7d32')


class KopukBagPenceresi(QDialog):
    """Diskte bulunamayan kayıtlar: önerilen yola bağla, dosyayı elle seç veya kayıttan kaldır."""

    def __init__(self, ust, db, klasorler):
        super().__init__(ust)
        self.db, self.klasorler = db, klasorler
        self.satirlar, self.isci = [], None
        self.setWindowTitle('Kopuk bağlar')
        self.resize(1100, 620)
        duzen = QVBoxLayout(self)
        self.bilgi = QLabel('')
        self.bilgi.setWordWrap(True)
        duzen.addWidget(self.bilgi)
        self.ilerleme = QProgressBar()
        duzen.addWidget(self.ilerleme)
        self.tablo = QTableWidget(0, len(SUTUNLAR))
        self.tablo.setHorizontalHeaderLabels(SUTUNLAR)
        self.tablo.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tablo.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.tablo.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tablo.verticalHeader().setDefaultSectionSize(26)
        baslik = self.tablo.horizontalHeader()
        baslik.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        baslik.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        for sutun, genislik in ((1, 80), (2, 70), (4, 170)):
            self.tablo.setColumnWidth(sutun, genislik)
        duzen.addWidget(self.tablo)
        dugmeler = QHBoxLayout()
        self.eylemler = []
        for etiket, islev in [('Önerileri uygula', self.onerileri_uygula), ('Dosyayı elle seç…', self.dosya_sec),
                              ('Başka klasörde ara…', self.klasorde_ara), ('Kayıttan kaldır', self.kaldir)]:
            dugme = QPushButton(etiket)
            dugme.clicked.connect(islev)
            dugmeler.addWidget(dugme)
            self.eylemler.append(dugme)
        kapat = QPushButton('Kapat')
        kapat.clicked.connect(self.reject)
        dugmeler.addWidget(kapat)
        duzen.addLayout(dugmeler)
        duzen.addWidget(QLabel('Ctrl / Shift ile birden çok satır, Ctrl+A ile tümü seçilir. Yeşil öneriler kesin eşleşmedir; '
                               'kaldırmak altyazıyı da siler, video dosyasına dokunmaz.'))
        self.isciyi_baslat()

    def isciyi_baslat(self, kayiplar=None, kokler=None):
        for dugme in self.eylemler:
            dugme.setEnabled(False)
        self.ilerleme.setRange(0, 0)
        self.isci = BagIscisi(self.klasorler, kayiplar, kokler)
        self.isci.asama.connect(self.bilgi.setText)
        self.isci.ilerleme.connect(self.ilerlemeyi_guncelle)
        self.isci.bulundu.connect(self.birlestir)
        self.isci.hata.connect(lambda metin: QMessageBox.warning(self, 'Kopuk bağlar', metin))
        self.isci.finished.connect(self.isci_bitti)
        self.isci.start()

    def ilerlemeyi_guncelle(self, mevcut, toplam):
        self.ilerleme.setRange(0, max(1, toplam))
        self.ilerleme.setValue(mevcut)

    def isci_bitti(self):
        self.ilerleme.setRange(0, 1)
        self.ilerleme.setValue(1)
        for dugme in self.eylemler:
            dugme.setEnabled(True)
        self.satirlari_goster()

    def birlestir(self, satirlar):
        """Yeni aramanın sonucu eklenir; kesin öneri daha zayıf olanla değiştirilmez."""
        mevcut = {s['id']: s for s in self.satirlar}
        for satir in satirlar:
            eski = mevcut.get(satir['id'])
            if eski is None or (satir.get('yeni_yol') and not eski.get('kesin')):
                mevcut[satir['id']] = satir
        self.satirlar = sorted(mevcut.values(), key=lambda s: s['path'].lower())
        self.satirlari_goster()

    def satirlari_goster(self):
        self.tablo.setUpdatesEnabled(False)
        self.tablo.setRowCount(len(self.satirlar))
        for i, satir in enumerate(self.satirlar):
            sure = satir['duration']
            degerler = [satir['path'], okunur_boyut(satir['size']), saat(round(sure * 1000)) if sure is not None else '',
                        satir.get('yeni_yol') or '', satir.get('neden') or '']
            for j, metin in enumerate(degerler):
                oge = QTableWidgetItem(metin)
                oge.setToolTip(metin)
                if j in (3, 4) and satir.get('kesin'):
                    oge.setForeground(KESIN_RENGI)
                self.tablo.setItem(i, j, oge)
        self.tablo.setUpdatesEnabled(True)
        onerili = sum(1 for s in self.satirlar if s.get('yeni_yol'))
        if self.isci is None or not self.isci.isRunning():
            self.bilgi.setText(f'{len(self.satirlar)} kopuk kayıt, {onerili} tanesi için öneri var.' if self.satirlar
                               else 'Kopuk kayıt yok; tüm kayıtların dosyası yerinde.')

    def secili_satirlar(self):
        return [self.satirlar[indeks.row()] for indeks in self.tablo.selectionModel().selectedRows()]

    def yeniden_bagla(self, satir, yol):
        yolu_guncelle(self.db, satir['id'], yol, os.stat(yol))

    def listeden_cikar(self, satirlar):
        kimlikler = {s['id'] for s in satirlar}
        self.satirlar = [s for s in self.satirlar if s['id'] not in kimlikler]
        self.satirlari_goster()

    def onerileri_uygula(self):
        satirlar = [s for s in self.secili_satirlar() if s.get('yeni_yol')]
        if not satirlar:
            QMessageBox.information(self, 'Önerileri uygula', 'Önerisi olan satırları seçin.')
            return
        kesin_olmayan = sum(1 for s in satirlar if not s['kesin'])
        if kesin_olmayan and QMessageBox.question(self, 'Önerileri uygula',
                f'{len(satirlar)} önerinin {kesin_olmayan} tanesi kesin değil; altyazı başka bir videoya bağlanabilir. Uygulansın mı?') \
                != QMessageBox.StandardButton.Yes:
            return
        yapilan, hatalar = [], []
        for satir in satirlar:
            try:
                self.yeniden_bagla(satir, satir['yeni_yol'])
                yapilan.append(satir)
            except sqlite3.IntegrityError:
                hatalar.append(f'{satir["yeni_yol"]}: bu dosyanın zaten ayrı bir kaydı var.')
            except OSError as hata:
                hatalar.append(f'{satir["yeni_yol"]}: {hata}')
        self.listeden_cikar(yapilan)
        if hatalar:
            QMessageBox.warning(self, 'Önerileri uygula', f'{len(yapilan)} bağ düzeltildi. Düzeltilemeyenler:\n' + '\n'.join(hatalar[:20]))

    def dosya_sec(self):
        satirlar = self.secili_satirlar()
        if len(satirlar) != 1:
            QMessageBox.information(self, 'Dosyayı elle seç', 'Tek bir satır seçin.')
            return
        satir = satirlar[0]
        baslangic = Path(satir['path']).parent
        while not baslangic.is_dir() and baslangic != baslangic.parent:
            baslangic = baslangic.parent
        desenler = ' '.join(f'*{uzanti}' for uzanti in sorted(UZANTILAR))
        yol, _ = QFileDialog.getOpenFileName(self, 'Videonun yeni yeri', str(baslangic), f'Video ({desenler})')
        if not yol:
            return
        yol = os.path.normpath(yol)
        try:
            if os.stat(yol).st_size != satir['size'] and QMessageBox.question(self, 'Dosyayı elle seç',
                    'Seçilen dosyanın boyutu kayıttakinden farklı; farklı bir video olabilir. Altyazı yine de buna bağlansın mı?') \
                    != QMessageBox.StandardButton.Yes:
                return
            self.yeniden_bagla(satir, yol)
            self.listeden_cikar([satir])
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, 'Dosyayı elle seç', 'Bu dosyanın zaten ayrı bir kaydı var. Eski kaydı isterseniz kaldırabilirsiniz.')
        except OSError as hata:
            QMessageBox.warning(self, 'Dosyayı elle seç', str(hata))

    def klasorde_ara(self):
        if not self.satirlar:
            return
        klasor = QFileDialog.getExistingDirectory(self, 'Kopuk videoların aranacağı klasör')
        if klasor:
            self.isciyi_baslat(self.satirlar, [os.path.normpath(klasor)])

    def kaldir(self):
        satirlar = self.secili_satirlar()
        if not satirlar:
            QMessageBox.information(self, 'Kayıttan kaldır', 'Önce satır seçin.')
            return
        if QMessageBox.question(self, 'Kayıttan kaldır',
                f'{len(satirlar)} videonun kaydı ve altyazısı veritabanından silinecek. Bu işlem geri alınamaz. Devam edilsin mi?') \
                != QMessageBox.StandardButton.Yes:
            return
        videolari_sil(self.db, [s['id'] for s in satirlar])
        self.listeden_cikar(satirlar)

    def done(self, sonuc):
        if self.isci and self.isci.isRunning():
            self.isci.requestInterruption()
            self.isci.wait()
        super().done(sonuc)
