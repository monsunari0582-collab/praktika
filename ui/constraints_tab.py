from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget,
    QTableWidgetItem, QLabel, QMessageBox,
    QComboBox
)
from database.connection import get_connection


class ConstraintsTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        form_layout = QHBoxLayout()

        self.teacher_combo = QComboBox()
        self.load_teachers_combo()

        self.day_combo = QComboBox()
        self.day_combo.addItems([
            "Понедельник", "Вторник", "Среда",
            "Четверг", "Пятница", "Суббота"
        ])

        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self.add_constraint)

        form_layout.addWidget(QLabel("Учитель:"))
        form_layout.addWidget(self.teacher_combo)
        form_layout.addWidget(QLabel("Нерабочий день:"))
        form_layout.addWidget(self.day_combo)
        form_layout.addWidget(add_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Учитель", "Нерабочий день"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.MultiSelection)

        bottom_layout = QHBoxLayout()

        select_all_btn = QPushButton("Выбрать все")
        select_all_btn.clicked.connect(self.table.selectAll)

        deselect_btn = QPushButton("Снять выбор")
        deselect_btn.clicked.connect(self.table.clearSelection)

        delete_btn = QPushButton("Удалить выбранные")
        delete_btn.clicked.connect(self.delete_selected)

        bottom_layout.addWidget(select_all_btn)
        bottom_layout.addWidget(deselect_btn)
        bottom_layout.addWidget(delete_btn)

        layout.addLayout(form_layout)
        layout.addWidget(self.table)
        layout.addLayout(bottom_layout)

        self.setLayout(layout)
        self.load_table()

    def load_teachers_combo(self):
        self.teacher_combo.clear()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ид, фио FROM УЧИТЕЛЬ ORDER BY фио")
        for row in cursor.fetchall():
            self.teacher_combo.addItem(row["фио"], row["ид"])
        conn.close()

    def load_table(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT О.ид, У.фио, О.значение
            FROM ОГРАНИЧЕНИЕ О
            JOIN УЧИТЕЛЬ У ON О.ид_сущности = У.ид
            WHERE О.тип_сущности = 'учитель'
            AND О.тип_правила = 'нерабочий_день'
            ORDER BY У.фио
        """)
        rows = cursor.fetchall()
        conn.close()

        дни = {
            "1": "Понедельник", "2": "Вторник", "3": "Среда",
            "4": "Четверг", "5": "Пятница", "6": "Суббота"
        }

        self.table.setRowCount(0)
        for row in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(row["фио"]))
            self.table.setItem(r, 1, QTableWidgetItem(дни.get(row["значение"], row["значение"])))
            self.table.item(r, 0).setData(256, row["ид"])

    def add_constraint(self):
        учитель_ид = self.teacher_combo.currentData()
        день = self.day_combo.currentIndex() + 1

        if учитель_ид is None:
            QMessageBox.warning(self, "Ошибка", "Выберите учителя")
            return

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 1 FROM ОГРАНИЧЕНИЕ
            WHERE тип_сущности = 'учитель' AND ид_сущности = ?
            AND тип_правила = 'нерабочий_день' AND значение = ?
        """, (учитель_ид, str(день)))

        if cursor.fetchone():
            QMessageBox.warning(self, "Ошибка", "Такое ограничение уже есть")
            conn.close()
            return

        cursor.execute("""
            INSERT INTO ОГРАНИЧЕНИЕ (тип_сущности, ид_сущности, тип_правила, значение)
            VALUES ('учитель', ?, 'нерабочий_день', ?)
        """, (учитель_ид, str(день)))
        conn.commit()
        conn.close()
        self.load_table()

    def delete_selected(self):
        выбранные_строки = set(item.row() for item in self.table.selectedItems())
        if not выбранные_строки:
            QMessageBox.warning(self, "Ошибка", "Выберите строки")
            return

        conn = get_connection()
        cursor = conn.cursor()
        for строка in выбранные_строки:
            ид = self.table.item(строка, 0).data(256)
            cursor.execute("DELETE FROM ОГРАНИЧЕНИЕ WHERE ид = ?", (ид,))
        conn.commit()
        conn.close()
        self.load_table()