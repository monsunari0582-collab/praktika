from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QLabel, QMessageBox,
    QSpinBox, QDialog, QDialogButtonBox,
    QHeaderView
)
from database.connection import get_connection


class EditTeacherDialog(QDialog):
    def __init__(self, фио, макс_часов, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактировать учителя")

        layout = QVBoxLayout()
        form_layout = QHBoxLayout()

        self.fio_input = QLineEdit(фио)
        self.hours_input = QSpinBox()
        self.hours_input.setMinimum(1)
        self.hours_input.setMaximum(36)
        self.hours_input.setValue(макс_часов)

        form_layout.addWidget(QLabel("ФИО:"))
        form_layout.addWidget(self.fio_input)
        form_layout.addWidget(QLabel("Макс. часов:"))
        form_layout.addWidget(self.hours_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addLayout(form_layout)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def get_data(self):
        return self.fio_input.text().strip(), self.hours_input.value()


class TeachersTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        form_layout = QHBoxLayout()

        self.fio_input = QLineEdit()
        self.fio_input.setPlaceholderText("ФИО учителя")

        self.hours_input = QSpinBox()
        self.hours_input.setMinimum(1)
        self.hours_input.setMaximum(36)
        self.hours_input.setValue(18)

        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self.add_teacher)

        form_layout.addWidget(QLabel("ФИО:"))
        form_layout.addWidget(self.fio_input)
        form_layout.addWidget(QLabel("Макс. часов в неделю:"))
        form_layout.addWidget(self.hours_input)
        form_layout.addWidget(add_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["ФИО", "Макс. часов"])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setColumnWidth(1, 120)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.MultiSelection)

        bottom_layout = QHBoxLayout()

        select_all_btn = QPushButton("Выбрать всех")
        select_all_btn.clicked.connect(self.table.selectAll)

        deselect_btn = QPushButton("Снять выбор")
        deselect_btn.clicked.connect(self.table.clearSelection)

        edit_btn = QPushButton("Редактировать")
        edit_btn.clicked.connect(self.edit_teacher)

        delete_btn = QPushButton("Удалить выбранных")
        delete_btn.clicked.connect(self.delete_selected)

        bottom_layout.addWidget(select_all_btn)
        bottom_layout.addWidget(deselect_btn)
        bottom_layout.addWidget(edit_btn)
        bottom_layout.addWidget(delete_btn)

        layout.addLayout(form_layout)
        layout.addWidget(self.table)
        layout.addLayout(bottom_layout)

        self.setLayout(layout)
        self.load_teachers()

    def load_teachers(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ид, фио, макс_часов FROM УЧИТЕЛЬ")
        rows = cursor.fetchall()
        conn.close()

        self.table.setRowCount(0)
        for row in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(row["фио"]))
            self.table.setItem(r, 1, QTableWidgetItem(str(row["макс_часов"])))
            self.table.item(r, 0).setData(256, row["ид"])

    def add_teacher(self):
        фио = self.fio_input.text().strip()
        часов = self.hours_input.value()

        if not фио:
            QMessageBox.warning(self, "Ошибка", "Введите ФИО учителя")
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO УЧИТЕЛЬ (фио, макс_часов) VALUES (?, ?)",
            (фио, часов)
        )
        conn.commit()
        conn.close()

        self.fio_input.clear()
        self.hours_input.setValue(18)
        self.load_teachers()

    def edit_teacher(self):
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Ошибка", "Выберите учителя")
            return

        row = self.table.currentRow()
        ид = self.table.item(row, 0).data(256)
        фио = self.table.item(row, 0).text()
        макс_часов = int(self.table.item(row, 1).text())

        dialog = EditTeacherDialog(фио, макс_часов, self)
        if dialog.exec() == QDialog.Accepted:
            новое_фио, новые_часы = dialog.get_data()
            if not новое_фио:
                QMessageBox.warning(self, "Ошибка", "ФИО не может быть пустым")
                return

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE УЧИТЕЛЬ SET фио = ?, макс_часов = ? WHERE ид = ?",
                (новое_фио, новые_часы, ид)
            )
            conn.commit()
            conn.close()
            self.load_teachers()

    def delete_selected(self):
        выбранные_строки = set(item.row() for item in self.table.selectedItems())
        if not выбранные_строки:
            QMessageBox.warning(self, "Ошибка", "Выберите учителей")
            return

        ответ = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить выбранных учителей ({len(выбранные_строки)} шт.)?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ответ == QMessageBox.No:
            return

        conn = get_connection()
        cursor = conn.cursor()
        for строка in выбранные_строки:
            ид = self.table.item(строка, 0).data(256)
            cursor.execute("DELETE FROM УЧИТЕЛЬ WHERE ид = ?", (ид,))
        conn.commit()
        conn.close()
        self.load_teachers()