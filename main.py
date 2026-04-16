import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui.theme import apply_dark
from ui.main_window import MainWindow
from core.setup import sdk_ready, scrcpy_ready


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Android Emulator Manager")
    apply_dark(app)

    if not sdk_ready() or not scrcpy_ready():
        from ui.setup_wizard import SetupWizard
        wizard = SetupWizard()
        wizard.exec()

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
