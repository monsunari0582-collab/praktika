from PySide6.QtWidgets import (
    QHeaderView,
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget,
    QTableWidgetItem, QLabel, QMessageBox,
    QComboBox
)
from database.connection import get_connection


class TeacherClassTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        form_layout = QHBoxLayout()

        self.teacher_combo = QComboBox()
        self.class_combo = QComboBox()
        self.load_combos()

        add_btn = QPushButton("Назначить")
        add_btn.clicked.connect(self.add_teacher_class)

        form_layout.addWidget(QLabel("Учитель:"))
        form_layout.addWidget(self.teacher_combo)
        form_layout.addWidget(QLabel("Класс:"))
        form_layout.addWidget(self.class_combo)
        form_layout.addWidget(add_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Учитель", "Класс"])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setColumnWidth(1, 150)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.MultiSelection)
        self.table.verticalHeader().setDefaultSectionSize(36)

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

    def load_combos(self):
        conn = get_connection()
        cursor = conn.cursor()

        self.teacher_combo.clear()
        cursor.execute("SELECT ид, фио FROM УЧИТЕЛЬ ORDER BY фио")
        for row in cursor.fetchall():
            self.teacher_combo.addItem(row["фио"], row["ид"])

        self.class_combo.clear()
        cursor.execute("SELECT ид, параллель, буква FROM КЛАСС ORDER BY CAST(параллель AS INTEGER), буква")
        for row in cursor.fetchall():
            название = f"{row['параллель']}{row['буква']}"
            self.class_combo.addItem(название, row["ид"])

        conn.close()

    def load_table(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT У.фио, К.параллель, К.буква, УК.учитель_ид, УК.класс_ид
            FROM УЧИТЕЛЬ_КЛАСС УК
            JOIN УЧИТЕЛЬ У ON УК.учитель_ид = У.ид
            JOIN КЛАСС К ON УК.класс_ид = К.ид
            ORDER BY У.фио, CAST(К.параллель AS INTEGER)
        """)
        rows = cursor.fetchall()
        conn.close()

        self.table.setRowCount(0)
        for row in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            название = f"{row['параллель']}{row['буква']}"
            self.table.setItem(r, 0, QTableWidgetItem(row["фио"]))
            self.table.setItem(r, 1, QTableWidgetItem(название))
            self.table.item(r, 0).setData(256, row["учитель_ид"])
            self.table.item(r, 1).setData(256, row["класс_ид"])

    def add_teacher_class(self):
        учитель_ид = self.teacher_combo.currentData()
        класс_ид = self.class_combo.currentData()

        if учитель_ид is None or класс_ид is None:
            QMessageBox.warning(self, "Ошибка", "Выберите учителя и класс")
            return

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 1 FROM УЧИТЕЛЬ_КЛАСС WHERE учитель_ид = ? AND класс_ид = ?
        """, (учитель_ид, класс_ид))

        if cursor.fetchone():
            QMessageBox.warning(self, "Ошибка", "Такая привязка уже существует")
            conn.close()
            return

        cursor.execute("""
            INSERT INTO УЧИТЕЛЬ_КЛАСС (учитель_ид, класс_ид) VALUES (?, ?)
        """, (учитель_ид, класс_ид))
        conn.commit()
        conn.close()
        self.load_table()

    def delete_selected(self):
        выбранные_строки = set(item.row() for item in self.table.selectedItems())
        if not выбранные_строки:
            QMessageBox.warning(self, "Ошибка", "Выберите строки")
            return

        ответ = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить выбранные привязки ({len(выбранные_строки)} шт.)?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ответ == QMessageBox.No:
            return

        conn = get_connection()
        cursor = conn.cursor()
        for строка in выбранные_строки:
            учитель_ид = self.table.item(строка, 0).data(256)
            класс_ид = self.table.item(строка, 1).data(256)
            cursor.execute("""
                DELETE FROM УЧИТЕЛЬ_КЛАСС WHERE учитель_ид = ? AND класс_ид = ?
            """, (учитель_ид, класс_ид))
        conn.commit()
        conn.close()
        self.load_table()