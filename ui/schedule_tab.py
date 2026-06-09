from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem,
    QPushButton, QTabWidget, QMessageBox
)
from PySide6.QtCore import Qt
from database.connection import get_connection


class ScheduleTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        top_layout = QHBoxLayout()

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_schedule)

        clear_btn = QPushButton("Очистить расписание")
        clear_btn.clicked.connect(self.clear_schedule)

        top_layout.addWidget(refresh_btn)
        top_layout.addWidget(clear_btn)
        top_layout.addStretch()

        self.class_tabs = QTabWidget()

        layout.addLayout(top_layout)
        layout.addWidget(self.class_tabs)

        self.setLayout(layout)
        self.load_schedule()

    def load_schedule(self):
        self.class_tabs.clear()

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ид, параллель, буква FROM КЛАСС ORDER BY CAST(параллель AS INTEGER), буква")
        классы = cursor.fetchall()
        conn.close()

        for класс in классы:
            класс_ид = класс["ид"]
            название = f"{класс['параллель']}{класс['буква']}"

            table = QTableWidget()
            table.setColumnCount(6)
            table.setHorizontalHeaderLabels([
                "Понедельник", "Вторник", "Среда",
                "Четверг", "Пятница", "Суббота"
            ])
            table.setRowCount(7)
            table.setVerticalHeaderLabels([
                "1 урок", "2 урок", "3 урок", "4 урок",
                "5 урок", "6 урок", "7 урок"
            ])
            table.horizontalHeader().setStretchLastSection(True)
            table.setEditTriggers(QTableWidget.NoEditTriggers)

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT У.день_недели, У.номер_урока,
                       П.название AS предмет, УЧ.фио AS учитель
                FROM УРОК У
                JOIN ПРЕДМЕТ П ON У.предмет_ид = П.ид
                JOIN УЧИТЕЛЬ УЧ ON У.учитель_ид = УЧ.ид
                WHERE У.класс_ид = ?
                ORDER BY У.день_недели, У.номер_урока
            """, (класс_ид,))
            rows = cursor.fetchall()
            conn.close()

            for row in rows:
                день = row["день_недели"] - 1
                урок = row["номер_урока"] - 1

                if 0 <= день <= 5 and 0 <= урок <= 6:
                    текст = f"{row['предмет']}\n{row['учитель']}"
                    item = QTableWidgetItem(текст)
                    item.setTextAlignment(Qt.AlignCenter)
                    table.setItem(урок, день, item)

            table.resizeRowsToContents()
            self.class_tabs.addTab(table, название)

    def clear_schedule(self):
        ответ = QMessageBox.question(
            self, "Подтверждение",
            "Вы уверены что хотите очистить расписание?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ответ == QMessageBox.Yes:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM УРОК")
            conn.commit()
            conn.close()

            self.load_schedule()
            QMessageBox.information(self, "Готово", "Расписание очищено")