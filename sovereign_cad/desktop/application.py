import sys

from PySide6.QtWidgets import QApplication

from sovereign_cad.desktop.main_window import MainWindow


def main():

    app = QApplication(sys.argv)

    app.setApplicationName(
        "SovereignCAD"
    )

    window = MainWindow()

    window.show()

    sys.exit(app.exec())
