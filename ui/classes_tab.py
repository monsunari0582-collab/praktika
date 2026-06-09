from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QLabel, QMessageBox,
    QDialog, QDialogButtonBox
)
from database.connection import get_connection


class EditClassDialog(QDialog):
    def __init__(self, параллель, буква, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактировать класс")

        layout = QVBoxLayout()
        form_layout = QHBoxLayout()

        self.grade_input = QLineEdit(параллель)
        self.section_input = QLineEdit(буква)

        form_layout.addWidget(QLabel("Параллель:"))
        form_layout.addWidget(self.grade_input)
        form_layout.addWidget(QLabel("Буква:"))
        form_layout.addWidget(self.section_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addLayout(form_layout)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def get_data(self):
        return self.grade_input.text().strip(), self.section_input.text().strip()


class ClassesTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        form_layout = QHBoxLayout()

        self.grade_input = QLineEdit()
        self.grade_input.setPlaceholderText("Параллель (напр. 9)")

        self.section_input = QLineEdit()
        self.section_input.setPlaceholderText("Буква (напр. А или пусто)")

        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self.add_class)

        form_layout.addWidget(QLabel("Параллель:"))
        form_layout.addWidget(self.grade_input)
        form_layout.addWidget(QLabel("Буква:"))
        form_layout.addWidget(self.section_input)
        form_layout.addWidget(add_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Класс", "Параллель"])
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
        edit_btn.clicked.connect(self.edit_class)

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
        self.load_classes()

    def load_classes(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ид, параллель, буква FROM КЛАСС ORDER BY CAST(параллель AS INTEGER), буква")
        rows = cursor.fetchall()
        conn.close()

        self.table.setRowCount(0)
        for row in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            название = f"{row['параллель']}{row['буква']}"
            self.table.setItem(r, 0, QTableWidgetItem(название))
            self.table.setItem(r, 1, QTableWidgetItem(row["параллель"]))
            self.table.item(r, 0).setData(256, row["ид"])

    def add_class(self):
        параллель = self.grade_input.text().strip()
        буква = self.section_input.text().strip()

        if not параллель:
            QMessageBox.warning(self, "Ошибка", "Введите параллель")
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO КЛАСС (параллель, буква) VALUES (?, ?)",
            (параллель, буква)
        )
        conn.commit()
        conn.close()

        self.grade_input.clear()
        self.section_input.clear()
        self.load_classes()

    def edit_class(self):
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Ошибка", "Выберите класс")
            return

        row = self.table.currentRow()
        ид = self.table.item(row, 0).data(256)
        параллель = self.table.item(row, 1).text()
        буква = self.table.item(row, 0).text().replace(параллель, "")

        dialog = EditClassDialog(параллель, буква, self)
        if dialog.exec() == QDialog.Accepted:
            новая_параллель, новая_буква = dialog.get_data()
            if not новая_параллель:
                QMessageBox.warning(self, "Ошибка", "Параллель не может быть пустой")
                return

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE КЛАСС SET параллель = ?, буква = ? WHERE ид = ?",
                (новая_параллель, новая_буква, ид)
            )
            conn.commit()
            conn.close()
            self.load_classes()

    def delete_selected(self):
        выбранные_строки = set(item.row() for item in self.table.selectedItems())
        if not выбранные_строки:
            QMessageBox.warning(self, "Ошибка", "Выберите классы")
            return

        ответ = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить выбранные классы ({len(выбранные_строки)} шт.)?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ответ == QMessageBox.No:
            return

        conn = get_connection()
        cursor = conn.cursor()
        for строка in выбранные_строки:
            ид = self.table.item(строка, 0).data(256)
            cursor.execute("DELETE FROM КЛАСС WHERE ид = ?", (ид,))
        conn.commit()
        conn.close()
        self.load_classes()