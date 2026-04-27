import sys
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

from scifigure.app import SciFigureStudio


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("SciFigure AI Studio")
    app.setOrganizationName("SciFigure")
    app.setStyle("Fusion")
    app.setFont(QFont("Microsoft YaHei", 10))

    win = SciFigureStudio()
    win.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
