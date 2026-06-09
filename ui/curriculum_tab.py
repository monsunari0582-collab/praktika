from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget,
    QTableWidgetItem, QLabel, QMessageBox,
    QComboBox, QSpinBox, QDialog, QDialogButtonBox
)
from database.connection import get_connection


class EditCurriculumDialog(QDialog):
    def __init__(self, часов, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактировать часы")

        layout = QVBoxLayout()
        form_layout = QHBoxLayout()

        self.hours_input = QSpinBox()
        self.hours_input.setMinimum(1)
        self.hours_input.setMaximum(10)
        self.hours_input.setValue(часов)

        form_layout.addWidget(QLabel("Часов в неделю:"))
        form_layout.addWidget(self.hours_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addLayout(form_layout)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def get_data(self):
        return self.hours_input.value()


class CurriculumTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        form_layout = QHBoxLayout()

        self.class_combo = QComboBox()
        self.subject_combo = QComboBox()
        self.load_combos()

        self.hours_input = QSpinBox()
        self.hours_input.setMinimum(1)
        self.hours_input.setMaximum(10)
        self.hours_input.setValue(2)

        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self.add_plan)

        form_layout.addWidget(QLabel("Класс:"))
        form_layout.addWidget(self.class_combo)
        form_layout.addWidget(QLabel("Предмет:"))
        form_layout.addWidget(self.subject_combo)
        form_layout.addWidget(QLabel("Часов в неделю:"))
        form_layout.addWidget(self.hours_input)
        form_layout.addWidget(add_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Класс", "Предмет", "Часов в неделю"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.MultiSelection)

        bottom_layout = QHBoxLayout()

        select_all_btn = QPushButton("Выбрать все")
        select_all_btn.clicked.connect(self.table.selectAll)

        deselect_btn = QPushButton("Снять выбор")
        deselect_btn.clicked.connect(self.table.clearSelection)

        edit_btn = QPushButton("Редактировать")
        edit_btn.clicked.connect(self.edit_plan)

        delete_btn = QPushButton("Удалить выбранные")
        delete_btn.clicked.connect(self.delete_selected)

        bottom_layout.addWidget(select_all_btn)
        bottom_layout.addWidget(deselect_btn)
        bottom_layout.addWidget(edit_btn)
        bottom_layout.addWidget(delete_btn)

        layout.addLayout(form_layout)
        layout.addWidget(self.table)
        layout.addLayout(bottom_layout)

        self.setLayout(layout)
        self.load_table()

    def load_combos(self):
        conn = get_connection()
        cursor = conn.cursor()

        self.class_combo.clear()
        cursor.execute("SELECT ид, параллель, буква FROM КЛАСС ORDER BY CAST(параллель AS INTEGER), буква")
        for row in cursor.fetchall():
            название = f"{row['параллель']}{row['буква']}"
            self.class_combo.addItem(название, row["ид"])

        self.subject_combo.clear()
        cursor.execute("SELECT ид, название FROM ПРЕДМЕТ ORDER BY название")
        for row in cursor.fetchall():
            self.subject_combo.addItem(row["название"], row["ид"])

        conn.close()

    def load_table(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT К.параллель, К.буква, П.название,
                   УП.часов_в_неделю, УП.класс_ид, УП.предмет_ид
            FROM УЧЕБНЫЙ_ПЛАН УП
            JOIN КЛАСС К ON УП.класс_ид = К.ид
            JOIN ПРЕДМЕТ П ON УП.предмет_ид = П.ид
            ORDER BY CAST(К.параллель AS INTEGER), К.буква, П.название
        """)
        rows = cursor.fetchall()
        conn.close()

        self.table.setRowCount(0)
        for row in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            название = f"{row['параллель']}{row['буква']}"
            self.table.setItem(r, 0, QTableWidgetItem(название))
            self.table.setItem(r, 1, QTableWidgetItem(row["название"]))
            self.table.setItem(r, 2, QTableWidgetItem(str(row["часов_в_неделю"])))
            self.table.item(r, 0).setData(256, row["класс_ид"])
            self.table.item(r, 1).setData(256, row["предмет_ид"])

    def add_plan(self):
        класс_ид = self.class_combo.currentData()
        предмет_ид = self.subject_combo.currentData()
        часов = self.hours_input.value()

        if класс_ид is None or предмет_ид is None:
            QMessageBox.warning(self, "Ошибка", "Выберите класс и предмет")
            return

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 1 FROM УЧЕБНЫЙ_ПЛАН WHERE класс_ид = ? AND предмет_ид = ?
        """, (класс_ид, предмет_ид))

        if cursor.fetchone():
            QMessageBox.warning(self, "Ошибка", "Этот предмет уже есть в плане этого класса")
            conn.close()
            return

        cursor.execute("""
            INSERT INTO УЧЕБНЫЙ_ПЛАН (класс_ид, предмет_ид, часов_в_неделю)
            VALUES (?, ?, ?)
        """, (класс_ид, предмет_ид, часов))
        conn.commit()
        conn.close()
        self.load_table()

    def edit_plan(self):
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Ошибка", "Выберите строку")
            return

        row = self.table.currentRow()
        класс_ид = self.table.item(row, 0).data(256)
        предмет_ид = self.table.item(row, 1).data(256)
        часов = int(self.table.item(row, 2).text())

        dialog = EditCurriculumDialog(часов, self)
        if dialog.exec() == QDialog.Accepted:
            новые_часы = dialog.get_data()
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE УЧЕБНЫЙ_ПЛАН SET часов_в_неделю = ?
                WHERE класс_ид = ? AND предмет_ид = ?
            """, (новые_часы, класс_ид, предмет_ид))
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
            f"Удалить выбранные записи ({len(выбранные_строки)} шт.)?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ответ == QMessageBox.No:
            return

        conn = get_connection()
        cursor = conn.cursor()
        for строка in выбранные_строки:
            класс_ид = self.table.item(строка, 0).data(256)
            предмет_ид = self.table.item(строка, 1).data(256)
            cursor.execute("""
                DELETE FROM УЧЕБНЫЙ_ПЛАН WHERE класс_ид = ? AND предмет_ид = ?
            """, (класс_ид, предмет_ид))
        conn.commit()
        conn.close()
        self.load_table()