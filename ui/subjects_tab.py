from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QLabel, QMessageBox,
    QDialog, QDialogButtonBox, QHeaderView
)
from PySide6.QtGui import QColor
from database.connection import get_connection
from ui.table_actions import ActionBar, selected_rows


class EditSubjectDialog(QDialog):
    def __init__(self, название, краткое_имя, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактировать предмет")

        layout = QVBoxLayout()
        form_layout = QHBoxLayout()

        self.name_input = QLineEdit(название)
        self.short_name_input = QLineEdit(краткое_имя)

        form_layout.addWidget(QLabel("Название:"))
        form_layout.addWidget(self.name_input)
        form_layout.addWidget(QLabel("Краткое имя:"))
        form_layout.addWidget(self.short_name_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addLayout(form_layout)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def get_data(self):
        return self.name_input.text().strip(), self.short_name_input.text().strip()


class SubjectsTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        form_layout = QHBoxLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Название предмета")

        self.short_name_input = QLineEdit()
        self.short_name_input.setPlaceholderText("Краткое имя (напр. Матем.)")

        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self.add_subject)

        form_layout.addWidget(QLabel("Название:"))
        form_layout.addWidget(self.name_input)
        form_layout.addWidget(QLabel("Краткое имя:"))
        form_layout.addWidget(self.short_name_input)
        form_layout.addWidget(add_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Название", "Краткое имя"])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setColumnWidth(1, 150)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setDefaultSectionSize(36)

        self.actions_bar = ActionBar(
            lambda: self.table, self.delete_selected,
            [("Редактировать", self.edit_subject)]
        )
        self.actions_bar.attach(self.table)

        layout.addLayout(form_layout)
        layout.addWidget(self.actions_bar)
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.load_subjects()

    def load_subjects(self):
        conn = get_connection()
        cursor = conn.cursor()
        
        # Загружаем все предметы
        cursor.execute("SELECT ид, название, краткое_имя FROM ПРЕДМЕТ ORDER BY название")
        predmety = cursor.fetchall()
        
        # Определяем предметы с учителями
        cursor.execute("SELECT DISTINCT предмет_ид FROM УЧИТЕЛЬ_ПРЕДМЕТ")
        predmety_s_uchitelami = {row["предмет_ид"] for row in cursor.fetchall()}
        
        conn.close()

        self.table.setRowCount(0)
        for row in predmety:
            r = self.table.rowCount()
            self.table.insertRow(r)
            
            # Если предмет не имеет учителей - выделяем красным
            if row["ид"] not in predmety_s_uchitelami:
                name_cell = QTableWidgetItem(row["название"])
                short_cell = QTableWidgetItem(row["краткое_имя"] or "")
                
                name_cell.setBackground(QColor("#FFE0E0"))  # Светло-красный фон
                name_cell.setForeground(QColor("#CC0000"))  # Тёмно-красный текст
                short_cell.setBackground(QColor("#FFE0E0"))
                short_cell.setForeground(QColor("#CC0000"))
                
                self.table.setItem(r, 0, name_cell)
                self.table.setItem(r, 1, short_cell)
            else:
                # Обычные предметы с учителями
                self.table.setItem(r, 0, QTableWidgetItem(row["название"]))
                self.table.setItem(r, 1, QTableWidgetItem(row["краткое_имя"] or ""))
            
            self.table.item(r, 0).setData(256, row["ид"])

    def add_subject(self):
        название = self.name_input.text().strip()
        краткое_имя = self.short_name_input.text().strip()

        if not название:
            QMessageBox.warning(self, "Ошибка", "Введите название предмета")
            return

        if not краткое_имя:
            QMessageBox.warning(self, "Ошибка", "Введите краткое имя")
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO ПРЕДМЕТ (название, краткое_имя) VALUES (?, ?)",
            (название, краткое_имя)
        )
        conn.commit()
        conn.close()

        self.name_input.clear()
        self.short_name_input.clear()
        self.load_subjects()

    def edit_subject(self):
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Ошибка", "Выберите предмет")
            return

        row = self.table.currentRow()
        ид = self.table.item(row, 0).data(256)
        название = self.table.item(row, 0).text()
        краткое_имя = self.table.item(row, 1).text()

        dialog = EditSubjectDialog(название, краткое_имя, self)
        if dialog.exec() == QDialog.Accepted:
            новое_название, новое_краткое_имя = dialog.get_data()
            if not новое_название:
                QMessageBox.warning(self, "Ошибка", "Название не может быть пустым")
                return

            if not новое_краткое_имя:
                QMessageBox.warning(self, "Ошибка", "Краткое имя не может быть пустым")
                return

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE ПРЕДМЕТ SET название = ?, краткое_имя = ? WHERE ид = ?",
                (новое_название, новое_краткое_имя, ид)
            )
            conn.commit()
            conn.close()
            self.load_subjects()

    def delete_selected(self):
        выбранные_строки = selected_rows(self.table)
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