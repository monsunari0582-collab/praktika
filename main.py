import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from database.init_db import init_database
# from database.fill_school_data import fill_school_data
from ui.style import STYLE

app = QApplication(sys.argv)
app.setStyleSheet(STYLE)

init_database()
# fill_school_data()

window = MainWindow()
window.show()

sys.exit(app.exec())



# asdfsfsfsdfs