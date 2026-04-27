from PyQt5.QtWidgets import QApplication
from core.callMain import AppMain
import sys

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = AppMain()
    main.show()
    sys.exit(app.exec())
