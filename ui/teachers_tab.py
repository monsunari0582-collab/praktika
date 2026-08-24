from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QLabel, QMessageBox,
    QDialog, QDialogButtonBox,
    QHeaderView
)
from PySide6.QtGui import QColor, QFont
from PySide6.QtCore import Qt
from database.connection import get_connection


class TeacherHoursDialog(QDialog):
    def __init__(self, учитель_ид, фио, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Часы учителя: {фио}")
        self.setGeometry(100, 100, 600, 400)

        layout = QVBoxLayout()

        # Таблица с предметами и часами
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Предмет", "Класс", "Часов в неделю"])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setColumnWidth(1, 80)
        self.table.setColumnWidth(2, 120)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        # Загружаем предметы учителя
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT П.название, К.параллель, К.буква, УП.часов_в_неделю
            FROM УЧИТЕЛЬ_ПРЕДМЕТ УП_П
            JOIN ПРЕДМЕТ П ON УП_П.предмет_ид = П.ид
            JOIN УЧИТЕЛЬ_КЛАСС УЧ_К ON УП_П.учитель_ид = УЧ_К.учитель_ид
            JOIN КЛАСС К ON УЧ_К.класс_ид = К.ид
            JOIN УЧЕБНЫЙ_ПЛАН УП ON УП.класс_ид = К.ид AND УП.предмет_ид = П.ид
            WHERE УП_П.учитель_ид = ?
            ORDER BY П.название, К.параллель, К.буква
        """, (учитель_ид,))
        
        rows = cursor.fetchall()
        total_hours = 0

        for row in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(row["название"]))
            self.table.setItem(r, 1, QTableWidgetItem(f"{row['параллель']}{row['буква']}"))
            self.table.setItem(r, 2, QTableWidgetItem(str(row["часов_в_неделю"])))
            total_hours += row["часов_в_неделю"]

        # Итоговая строка
        if rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            
            итого_cell = QTableWidgetItem("ИТОГО:")
            итого_cell.setFont(QFont("Arial", 10, QFont.Bold))
            итого_cell.setBackground(QColor("#E8F0FE"))
            итого_cell.setForeground(QColor("#2979B8"))
            self.table.setItem(r, 0, итого_cell)
            
            часов_cell = QTableWidgetItem(str(total_hours))
            часов_cell.setFont(QFont("Arial", 10, QFont.Bold))
            часов_cell.setBackground(QColor("#E8F0FE"))
            часов_cell.setForeground(QColor("#2979B8"))
            часов_cell.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 2, часов_cell)

        conn.close()

        layout.addWidget(self.table)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self.setLayout(layout)


class EditTeacherDialog(QDialog):
    def __init__(self, фио, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактировать учителя")

        layout = QVBoxLayout()
        form_layout = QHBoxLayout()

        self.fio_input = QLineEdit(фио)

        form_layout.addWidget(QLabel("ФИО:"))
        form_layout.addWidget(self.fio_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addLayout(form_layout)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def get_data(self):
        return self.fio_input.text().strip()


class TeachersTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        form_layout = QHBoxLayout()

        self.fio_input = QLineEdit()
        self.fio_input.setPlaceholderText("ФИО учителя")

        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self.add_teacher)

        form_layout.addWidget(QLabel("ФИО:"))
        form_layout.addWidget(self.fio_input)
        form_layout.addWidget(add_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(1)
        self.table.setHorizontalHeaderLabels(["ФИО"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.MultiSelection)
        self.table.verticalHeader().setDefaultSectionSize(36)

        bottom_layout = QHBoxLayout()

        select_all_btn = QPushButton("Выбрать всех")
        select_all_btn.clicked.connect(self.table.selectAll)

        deselect_btn = QPushButton("Снять выбор")
        deselect_btn.clicked.connect(self.table.clearSelection)

        view_hours_btn = QPushButton("Просмотреть часы")
        view_hours_btn.clicked.connect(self.view_teacher_hours)

        edit_btn = QPushButton("Редактировать")
        edit_btn.clicked.connect(self.edit_teacher)

        delete_btn = QPushButton("Удалить выбранных")
        delete_btn.clicked.connect(self.delete_selected)

        bottom_layout.addWidget(select_all_btn)
        bottom_layout.addWidget(deselect_btn)
        bottom_layout.addWidget(view_hours_btn)
        bottom_layout.addWidget(edit_btn)
        bottom_layout.addWidget(delete_btn)

        # Сохраняем ссылки на кнопки
        self.view_hours_btn = view_hours_btn
        self.edit_btn = edit_btn

        # Стили для отключенных кнопок
        disabled_style = """
            QPushButton:disabled {
                background-color: #E0E0E0;
                color: #999999;
                border: 1px solid #CCCCCC;
                opacity: 0.6;
            }
        """
        view_hours_btn.setStyleSheet(disabled_style)
        edit_btn.setStyleSheet(disabled_style)

        layout.addLayout(form_layout)
        layout.addWidget(self.table)
        layout.addLayout(bottom_layout)

        self.setLayout(layout)
        self.load_teachers()

        # Подключаем сигнал выделения
        self.table.itemSelectionChanged.connect(self.update_button_states)
        
        # Изначально кнопки отключены
        self.update_button_states()

    def load_teachers(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ид, фио FROM УЧИТЕЛЬ")
        rows = cursor.fetchall()
        conn.close()

        self.table.setRowCount(0)
        for row in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(row["фио"]))
            self.table.item(r, 0).setData(256, row["ид"])

    def add_teacher(self):
        фио = self.fio_input.text().strip()

        if not фио:
            QMessageBox.warning(self, "Ошибка", "Введите ФИО учителя")
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO УЧИТЕЛЬ (фио) VALUES (?)",
            (фио,)
        )
        conn.commit()
        conn.close()

        self.fio_input.clear()
        self.load_teachers()

    def edit_teacher(self):
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Ошибка", "Выберите учителя")
            return

        row = self.table.currentRow()
        ид = self.table.item(row, 0).data(256)
        фио = self.table.item(row, 0).text()

        dialog = EditTeacherDialog(фио, self)
        if dialog.exec() == QDialog.Accepted:
            новое_фио = dialog.get_data()
            if not новое_фио:
                QMessageBox.warning(self, "Ошибка", "ФИО не может быть пустым")
                return

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE УЧИТЕЛЬ SET фио = ? WHERE ид = ?",
                (новое_фио, ид)
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

    def view_teacher_hours(self):
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Ошибка", "Выберите учителя")
            return

        row = self.table.currentRow()
        ид = self.table.item(row, 0).data(256)
        фио = self.table.item(row, 0).text()

        dialog = TeacherHoursDialog(ид, фио, self)
        dialog.exec()

    def update_button_states(self):
        """Отключает кнопки если выбрано не 1 учитель"""
        количество_выбранных = len(set(item.row() for item in self.table.selectedItems()))
        self.view_hours_btn.setEnabled(количество_выбранных == 1)
        self.edit_btn.setEnabled(количество_выбранных == 1)