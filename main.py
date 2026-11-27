"""Uygulama başlangıcı: python main.py"""
import os
import sys


def main():
    from PyQt6.QtCore import QLockFile
    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import QApplication, QMessageBox

    from PyQt6.QtCore import QSettings

    from arsiv.ceviri import _t, dil_ayarla, sistem_dili
    from arsiv.yollar import AYARLAR, IKON, KILIT_DOSYASI

    # Arayüz dili pencere kurulmadan önce seçilir; ayar yoksa Windows diline göre.
    dil_ayarla(QSettings(str(AYARLAR), QSettings.Format.IniFormat).value('ui/language', sistem_dili(), type=str))
    from arsiv.arayuz import AnaPencere

    if os.name == 'nt':
        # Görev çubuğu python.exe yerine uygulamanın simgesini göstersin.
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('VideodaKelimeAra')
    uygulama = QApplication(sys.argv)
    uygulama.setApplicationName(_t('Videoda Kelime Ara'))
    uygulama.setStyle('Fusion')
    uygulama.setWindowIcon(QIcon(str(IKON)))
    kilit = QLockFile(str(KILIT_DOSYASI))
    kilit.setStaleLockTime(0)
    if not kilit.tryLock(100):
        QMessageBox.information(None, _t('Videoda Kelime Ara'), _t('Uygulama zaten açık.'))
        return 0
    pencere = AnaPencere()
    pencere.show()
    sonuc = uygulama.exec()
    if pencere.yeniden_baslat:  # arayüz dili değişti: kilidi bırakıp aynı komutla yeniden aç
        import subprocess
        kilit.unlock()
        subprocess.Popen([sys.executable, *sys.argv])
    return sonuc


if __name__ == '__main__':
    sys.exit(main())
