from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QLabel, QMessageBox,
    QDialog, QDialogButtonBox
)
from database.connection import get_connection


class EditSubjectDialog(QDialog):
    def __init__(self, название, код, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактировать предмет")

        layout = QVBoxLayout()
        form_layout = QHBoxLayout()

        self.name_input = QLineEdit(название)
        self.code_input = QLineEdit(код)

        form_layout.addWidget(QLabel("Название:"))
        form_layout.addWidget(self.name_input)
        form_layout.addWidget(QLabel("Код:"))
        form_layout.addWidget(self.code_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addLayout(form_layout)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def get_data(self):
        return self.name_input.text().strip(), self.code_input.text().strip()


class SubjectsTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        form_layout = QHBoxLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Название предмета")

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Код (напр. MATH)")

        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self.add_subject)

        form_layout.addWidget(QLabel("Название:"))
        form_layout.addWidget(self.name_input)
        form_layout.addWidget(QLabel("Код:"))
        form_layout.addWidget(self.code_input)
        form_layout.addWidget(add_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Название", "Код"])
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
        edit_btn.clicked.connect(self.edit_subject)

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
        self.load_subjects()

    def load_subjects(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ид, название, код FROM ПРЕДМЕТ")
        rows = cursor.fetchall()
        conn.close()

        self.table.setRowCount(0)
        for row in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(row["название"]))
            self.table.setItem(r, 1, QTableWidgetItem(row["код"] or ""))
            self.table.item(r, 0).setData(256, row["ид"])

    def add_subject(self):
        название = self.name_input.text().strip()
        код = self.code_input.text().strip()

        if not название:
            QMessageBox.warning(self, "Ошибка", "Введите название предмета")
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO ПРЕДМЕТ (название, код) VALUES (?, ?)",
            (название, код)
        )
        conn.commit()
        conn.close()

        self.name_input.clear()
        self.code_input.clear()
        self.load_subjects()

    def edit_subject(self):
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Ошибка", "Выберите предмет")
            return

        row = self.table.currentRow()
        ид = self.table.item(row, 0).data(256)
        название = self.table.item(row, 0).text()
        код = self.table.item(row, 1).text()

        dialog = EditSubjectDialog(название, код, self)
        if dialog.exec() == QDialog.Accepted:
            новое_название, новый_код = dialog.get_data()
            if not новое_название:
                QMessageBox.warning(self, "Ошибка", "Название не может быть пустым")
                return

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE ПРЕДМЕТ SET название = ?, код = ? WHERE ид = ?",
                (новое_название, новый_код, ид)
            )
            conn.commit()
            conn.close()
            self.load_subjects()

    def delete_selected(self):
        выбранные_строки = set(item.row() for item in self.table.selectedItems())
        if not выбранные_строки:
            QMessageBox.warning(self, "Ошибка", "Выберите предметы")
            return

        ответ = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить выбранные предметы ({len(выбранные_строки)} шт.)?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ответ == QMessageBox.No:
            return

        conn = get_connection()
        cursor = conn.cursor()
        for строка in выбранные_строки:
            ид = self.table.item(строка, 0).data(256)
            cursor.execute("DELETE FROM ПРЕДМЕТ WHERE ид = ?", (ид,))
        conn.commit()
        conn.close()
        self.load_subjects()