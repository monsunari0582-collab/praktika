from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget,
    QTableWidgetItem, QLabel, QMessageBox,
    QComboBox
)
from database.connection import get_connection


class TeacherSubjectTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        form_layout = QHBoxLayout()

        self.teacher_combo = QComboBox()
        self.subject_combo = QComboBox()
        self.load_combos()

        add_btn = QPushButton("Назначить")
        add_btn.clicked.connect(self.add_teacher_subject)

        form_layout.addWidget(QLabel("Учитель:"))
        form_layout.addWidget(self.teacher_combo)
        form_layout.addWidget(QLabel("Предмет:"))
        form_layout.addWidget(self.subject_combo)
        form_layout.addWidget(add_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Учитель", "Предмет"])
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

    def load_combos(self):
        conn = get_connection()
        cursor = conn.cursor()

        self.teacher_combo.clear()
        cursor.execute("SELECT ид, фио FROM УЧИТЕЛЬ ORDER BY фио")
        for row in cursor.fetchall():
            self.teacher_combo.addItem(row["фио"], row["ид"])

        self.subject_combo.clear()
        cursor.execute("SELECT ид, название FROM ПРЕДМЕТ ORDER BY название")
        for row in cursor.fetchall():
            self.subject_combo.addItem(row["название"], row["ид"])

        conn.close()

    def load_table(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT У.фио, П.название, УП.учитель_ид, УП.предмет_ид
            FROM УЧИТЕЛЬ_ПРЕДМЕТ УП
            JOIN УЧИТЕЛЬ У ON УП.учитель_ид = У.ид
            JOIN ПРЕДМЕТ П ON УП.предмет_ид = П.ид
            ORDER BY У.фио
        """)
        rows = cursor.fetchall()
        conn.close()

        self.table.setRowCount(0)
        for row in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(row["фио"]))
            self.table.setItem(r, 1, QTableWidgetItem(row["название"]))
            self.table.item(r, 0).setData(256, row["учитель_ид"])
            self.table.item(r, 1).setData(256, row["предмет_ид"])

    def add_teacher_subject(self):
        учитель_ид = self.teacher_combo.currentData()
        предмет_ид = self.subject_combo.currentData()

        if учитель_ид is None or предмет_ид is None:
            QMessageBox.warning(self, "Ошибка", "Выберите учителя и предмет")
            return

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 1 FROM УЧИТЕЛЬ_ПРЕДМЕТ WHERE учитель_ид = ? AND предмет_ид = ?
        """, (учитель_ид, предмет_ид))

        if cursor.fetchone():
            QMessageBox.warning(self, "Ошибка", "Этот учитель уже преподаёт этот предмет")
            conn.close()
            return

        cursor.execute("""
            INSERT INTO УЧИТЕЛЬ_ПРЕДМЕТ (учитель_ид, предмет_ид) VALUES (?, ?)
        """, (учитель_ид, предмет_ид))
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
            f"Удалить выбранные назначения ({len(выбранные_строки)} шт.)?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ответ == QMessageBox.No:
            return

        conn = get_connection()
        cursor = conn.cursor()
        for строка in выбранные_строки:
            учитель_ид = self.table.item(строка, 0).data(256)
            предмет_ид = self.table.item(строка, 1).data(256)
            cursor.execute("""
                DELETE FROM УЧИТЕЛЬ_ПРЕДМЕТ WHERE учитель_ид = ? AND предмет_ид = ?
            """, (учитель_ид, предмет_ид))
        conn.commit()
        conn.close()
        self.load_table()