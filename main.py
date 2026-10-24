import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from database.init_db import init_database
from ui.style import STYLE

app = QApplication(sys.argv)
app.setStyleSheet(STYLE)

init_database()

window = MainWindow()
window.show()

sys.exit(app.exec())