from PySide6.QtWidgets import (
    QHeaderView,
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget,
    QTableWidgetItem, QLabel, QMessageBox,
    QComboBox, QSpinBox, QDialog, QDialogButtonBox
)
from PySide6.QtCore import Qt
from database.connection import get_connection


class EditTeacherClassDialog(QDialog):
    def __init__(self, учитель_фио, класс_название, часов, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Часы: {учитель_фио} — {класс_название}")

        layout = QVBoxLayout()
        form_layout = QHBoxLayout()

        self.hours_input = QSpinBox()
        self.hours_input.setMinimum(1)
        self.hours_input.setMaximum(40)
        self.hours_input.setValue(часов if часов > 0 else 1)

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


class TeacherClassTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        form_layout = QHBoxLayout()

        self.teacher_combo = QComboBox()
        self.class_combo = QComboBox()
        self.load_combos()

        self.hours_input = QSpinBox()
        self.hours_input.setMinimum(1)
        self.hours_input.setMaximum(40)
        self.hours_input.setValue(2)

        add_btn = QPushButton("Назначить")
        add_btn.clicked.connect(self.add_teacher_class)

        form_layout.addWidget(QLabel("Учитель:"))
        form_layout.addWidget(self.teacher_combo)
        form_layout.addWidget(QLabel("Класс:"))
        form_layout.addWidget(self.class_combo)
        form_layout.addWidget(QLabel("Часов в неделю:"))
        form_layout.addWidget(self.hours_input)
        form_layout.addWidget(add_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Учитель", "Класс", "Часов в неделю"])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setColumnWidth(1, 140)
        self.table.setColumnWidth(2, 160)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.MultiSelection)
        self.table.verticalHeader().setDefaultSectionSize(36)

        bottom_layout = QHBoxLayout()

        select_all_btn = QPushButton("Выбрать все")
        select_all_btn.clicked.connect(self.table.selectAll)

        deselect_btn = QPushButton("Снять выбор")
        deselect_btn.clicked.connect(self.table.clearSelection)

        edit_btn = QPushButton("Редактировать часы")
        edit_btn.clicked.connect(self.edit_selected)
        self.edit_btn = edit_btn

        disabled_style = """
            QPushButton:disabled {
                background-color: #E0E0E0;
                color: #999999;
                border: 1px solid #CCCCCC;
                opacity: 0.6;
            }
        """
        self.edit_btn.setStyleSheet(disabled_style)

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

        self.table.itemSelectionChanged.connect(self.update_button_states)
        self.update_button_states()

    def update_button_states(self):
        selected_rows = set(item.row() for item in self.table.selectedItems())
        self.edit_btn.setEnabled(len(selected_rows) == 1)

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
            SELECT У.фио, К.параллель, К.буква, УК.учитель_ид, УК.класс_ид, COALESCE(УК.часов, 0) AS часов
            FROM УЧИТЕЛЬ_КЛАСС УК
            JOIN УЧИТЕЛЬ У ON УК.учитель_ид = У.ид
            JOIN КЛАСС К ON УК.класс_ид = К.ид
            ORDER BY У.фио, CAST(К.параллель AS INTEGER), К.буква
        """)
        rows = cursor.fetchall()
        conn.close()

        self.table.setRowCount(0)
        for row in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            название = f"{row['параллель']}{row['буква']}"
            ч = row["часов"]

            it_teacher = QTableWidgetItem(row["фио"])
            it_class = QTableWidgetItem(название)
            it_hours = QTableWidgetItem(str(ч) if ч > 0 else "0")

            it_class.setTextAlignment(Qt.AlignCenter)
            it_hours.setTextAlignment(Qt.AlignCenter)

            self.table.setItem(r, 0, it_teacher)
            self.table.setItem(r, 1, it_class)
            self.table.setItem(r, 2, it_hours)

            self.table.item(r, 0).setData(256, row["учитель_ид"])
            self.table.item(r, 1).setData(256, row["класс_ид"])
            self.table.item(r, 2).setData(256, ч)

        self.update_button_states()

    def add_teacher_class(self):
        учитель_ид = self.teacher_combo.currentData()
        класс_ид = self.class_combo.currentData()
        часов = self.hours_input.value()

        if учитель_ид is None or класс_ид is None:
            QMessageBox.warning(self, "Ошибка", "Выберите учителя и класс")
            return

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT часов FROM УЧИТЕЛЬ_КЛАСС WHERE учитель_ид = ? AND класс_ид = ?
        """, (учитель_ид, класс_ид))
        existing = cursor.fetchone()

        if existing:
            ответ = QMessageBox.question(
                self, "Подтверждение",
                f"Такая привязка уже существует (сейчас: {existing['часов'] or 0} ч.). Обновить на {часов} ч.?",
                QMessageBox.Yes | QMessageBox.No
            )
            if ответ == QMessageBox.Yes:
                cursor.execute("""
                    UPDATE УЧИТЕЛЬ_КЛАСС SET часов = ? WHERE учитель_ид = ? AND класс_ид = ?
                """, (часов, учитель_ид, класс_ид))
                conn.commit()
            conn.close()
            self.load_table()
            return

        cursor.execute("""
            INSERT INTO УЧИТЕЛЬ_КЛАСС (учитель_ид, класс_ид, часов) VALUES (?, ?, ?)
        """, (учитель_ид, класс_ид, часов))
        conn.commit()
        conn.close()
        self.load_table()

    def edit_selected(self):
        selected_rows = list(set(item.row() for item in self.table.selectedItems()))
        if len(selected_rows) != 1:
            QMessageBox.warning(self, "Ошибка", "Выберите одну привязку для редактирования")
            return

        row = selected_rows[0]
        учитель_ид = self.table.item(row, 0).data(256)
        класс_ид = self.table.item(row, 1).data(256)
        учитель_фио = self.table.item(row, 0).text()
        класс_название = self.table.item(row, 1).text()
        часов = self.table.item(row, 2).data(256) or 0

        dialog = EditTeacherClassDialog(учитель_фио, класс_название, часов, self)
        if dialog.exec() == QDialog.Accepted:
            новые_часы = dialog.get_data()
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE УЧИТЕЛЬ_КЛАСС SET часов = ? WHERE учитель_ид = ? AND класс_ид = ?
            """, (новые_часы, учитель_ид, класс_ид))
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