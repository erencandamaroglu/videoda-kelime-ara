"""Uygulama başlangıcı: python main.py"""
import os
import sys


def main():
    from PyQt6.QtCore import QLockFile
    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import QApplication, QMessageBox

    from arsiv.arayuz import AnaPencere
    from arsiv.yollar import IKON, KILIT_DOSYASI

    if os.name == 'nt':
        # Görev çubuğu python.exe yerine uygulamanın simgesini göstersin.
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('VideodaKelimeAra')
    uygulama = QApplication(sys.argv)
    uygulama.setApplicationName('Videoda Kelime Ara')
    uygulama.setStyle('Fusion')
    uygulama.setWindowIcon(QIcon(str(IKON)))
    kilit = QLockFile(str(KILIT_DOSYASI))
    kilit.setStaleLockTime(0)
    if not kilit.tryLock(100):
        QMessageBox.information(None, 'Videoda Kelime Ara', 'Uygulama zaten açık.')
        return 0
    pencere = AnaPencere()
    pencere.show()
    return uygulama.exec()


if __name__ == '__main__':
    sys.exit(main())
