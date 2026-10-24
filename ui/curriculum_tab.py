from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTabWidget,
    QTableWidgetItem, QLabel, QMessageBox,
    QComboBox, QSpinBox, QDialog, QDialogButtonBox,
    QHeaderView
)
from PySide6.QtGui import QColor, QFont
from PySide6.QtCore import Qt
from database.connection import get_connection
from ui.table_actions import ActionBar, selected_rows


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

        self.class_tabs = QTabWidget()

        self.actions_bar = ActionBar(
            self.current_table, self.delete_selected,
            [("Редактировать", self.edit_plan)]
        )
        self.class_tabs.currentChanged.connect(self.update_total_hours)
        self.class_tabs.currentChanged.connect(self.actions_bar.update_state)

        # Label с итого часов
        self.total_hours_label = QLabel("ИТОГО ЧАСОВ: 0")
        self.total_hours_label.setStyleSheet("""
            QLabel {
                background-color: #E8F0FE;
                color: #2979B8;
                font-weight: bold;
                font-size: 12px;
                padding: 8px 12px;
                border-radius: 4px;
                border: 1px solid #BFD4E8;
            }
        """)

        layout.addLayout(form_layout)
        layout.addWidget(self.actions_bar)
        layout.addWidget(self.class_tabs)
        layout.addWidget(self.total_hours_label)

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

    def current_table(self):
        return self.class_tabs.currentWidget()

    def load_table(self):
        current_index = self.class_tabs.currentIndex()

        self.class_tabs.clear()

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ид, параллель, буква FROM КЛАСС ORDER BY CAST(параллель AS INTEGER), буква")
        классы = cursor.fetchall()

        for класс in классы:
            класс_ид = класс["ид"]
            название = f"{класс['параллель']}{класс['буква']}"

            table = QTableWidget()
            table.setColumnCount(2)
            table.setHorizontalHeaderLabels(["Предмет", "Часов в неделю"])
            table.horizontalHeader().setStretchLastSection(False)
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            table.setColumnWidth(1, 300)
            table.setSelectionBehavior(QTableWidget.SelectRows)
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.verticalHeader().setVisible(True)
            table.verticalHeader().setDefaultSectionSize(36)
            table.verticalHeader().setFixedWidth(40)

            cursor.execute("""
                SELECT П.название, УП.часов_в_неделю, УП.предмет_ид
                FROM УЧЕБНЫЙ_ПЛАН УП
                JOIN ПРЕДМЕТ П ON УП.предмет_ид = П.ид
                WHERE УП.класс_ид = ?
                ORDER BY П.название
            """, (класс_ид,))
            rows = cursor.fetchall()

            # Добавляем все предметы
            for row in rows:
                r = table.rowCount()
                table.insertRow(r)
                table.setItem(r, 0, QTableWidgetItem(row["название"]))
                table.setItem(r, 1, QTableWidgetItem(str(row["часов_в_неделю"])))
                table.item(r, 0).setData(256, класс_ид)
                table.item(r, 1).setData(256, row["предмет_ид"])

            self.class_tabs.addTab(table, название)
            self.actions_bar.attach(table)

        conn.close()

        if 0 <= current_index < self.class_tabs.count():
            self.class_tabs.setCurrentIndex(current_index)

        self.update_total_hours()
        self.actions_bar.update_state()

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
        self.update_total_hours()

    def edit_plan(self):
        table = self.current_table()
        if not table or not table.selectedItems():
            QMessageBox.warning(self, "Ошибка", "Выберите строку")
            return

        row = table.currentRow()
        
        класс_ид = table.item(row, 0).data(256)
        предмет_ид = table.item(row, 1).data(256)
        часов = int(table.item(row, 1).text())  # текст колонки "Часов в неделю"

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
            self.update_total_hours()

    def delete_selected(self):
        table = self.current_table()
        if not table:
            return

        выбранные_строки = selected_rows(table)
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
            класс_ид = table.item(строка, 0).data(256)
            предмет_ид = table.item(строка, 1).data(256)
            cursor.execute("""
                DELETE FROM УЧЕБНЫЙ_ПЛАН WHERE класс_ид = ? AND предмет_ид = ?
            """, (класс_ид, предмет_ид))
        conn.commit()
        conn.close()
        self.load_table()
        self.update_total_hours()

    def update_total_hours(self):
        """Обновляет label с общим количеством часов в текущем классе"""
        table = self.current_table()
        if not table:
            self.total_hours_label.setText("ИТОГО ЧАСОВ: 0")
            return

        total_hours = 0
        for row in range(table.rowCount()):
            try:
                часов = int(table.item(row, 1).text())
                total_hours += часов
            except (ValueError, TypeError):
                pass

        self.total_hours_label.setText(f"ИТОГО ЧАСОВ: {total_hours}")