from PySide6.QtWidgets import (
    QHeaderView,
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget,
    QTableWidgetItem, QLabel, QMessageBox,
    QComboBox, QSpinBox, QDialog, QDialogButtonBox,
    QLineEdit
)
from PySide6.QtCore import Qt
from database.connection import get_connection
from ui.table_actions import ActionBar, selected_rows


class EditAssignmentHoursDialog(QDialog):
    def __init__(self, учитель_фио, предмет_название, класс_название, часов, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Часы: {предмет_название} ({класс_название})")

        layout = QVBoxLayout()
        form_layout = QHBoxLayout()

        self.hours_input = QSpinBox()
        self.hours_input.setMinimum(1)
        self.hours_input.setMaximum(40)
        self.hours_input.setValue(часов if часов > 0 else 1)

        info_label = QLabel(f"<b>Учитель:</b> {учитель_фио}<br><b>Предмет:</b> {предмет_название} ({класс_название})")
        layout.addWidget(info_label)

        form_layout.addWidget(QLabel("Часов в неделю:"))
        form_layout.addWidget(self.hours_input)
        layout.addLayout(form_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def get_data(self):
        return self.hours_input.value()


def _sync_teacher_class(cursor, учитель_ид, класс_ид):
    cursor.execute("""
        SELECT SUM(часов) as сумм FROM УЧИТЕЛЬ_ПРЕДМЕТ_КЛАСС
        WHERE учитель_ид = ? AND класс_ид = ?
    """, (учитель_ид, класс_ид))
    row = cursor.fetchone()
    сумм = (row["сумм"] if row and row["сумм"] else 0)
    if сумм > 0:
        cursor.execute("""
            INSERT OR REPLACE INTO УЧИТЕЛЬ_КЛАСС (учитель_ид, класс_ид, часов)
            VALUES (?, ?, ?)
        """, (учитель_ид, класс_ид, сумм))
    else:
        cursor.execute("""
            DELETE FROM УЧИТЕЛЬ_КЛАСС WHERE учитель_ид = ? AND класс_ид = ?
        """, (учитель_ид, класс_ид))


class TeacherSubjectClassTab(QWidget):
    """Вкладка распределения предметов по классам: Учитель — Предмет — Класс."""
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        # Верхняя панель: выбор учителя, предмета, класса и часов
        form_layout = QHBoxLayout()

        self.teacher_combo = QComboBox()
        self.subject_combo = QComboBox()
        self.class_combo = QComboBox()
        self.hours_input = QSpinBox()
        self.hours_input.setMinimum(1)
        self.hours_input.setMaximum(40)
        self.hours_input.setValue(2)

        self.teacher_combo.currentIndexChanged.connect(self.on_teacher_changed)
        self.subject_combo.currentIndexChanged.connect(self.on_subject_or_class_changed)
        self.class_combo.currentIndexChanged.connect(self.on_subject_or_class_changed)

        add_btn = QPushButton("Назначить")
        add_btn.clicked.connect(self.add_assignment)

        form_layout.addWidget(QLabel("Учитель:"))
        form_layout.addWidget(self.teacher_combo, 2)
        form_layout.addWidget(QLabel("Предмет:"))
        form_layout.addWidget(self.subject_combo, 2)
        form_layout.addWidget(QLabel("Класс:"))
        form_layout.addWidget(self.class_combo, 1)
        form_layout.addWidget(QLabel("Часов в неделю:"))
        form_layout.addWidget(self.hours_input, 1)
        form_layout.addWidget(add_btn)

        # Панель фильтра
        filter_layout = QHBoxLayout()
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Быстрый поиск по учителю, предмету или классу...")
        self.filter_input.textChanged.connect(self.apply_filter)
        filter_layout.addWidget(QLabel("Поиск:"))
        filter_layout.addWidget(self.filter_input)

        # Таблица назначений
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Учитель", "Предмет", "Класс", "Часов в неделю"])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(2, 120)
        self.table.setColumnWidth(3, 140)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setDefaultSectionSize(36)

        self.actions_bar = ActionBar(
            lambda: self.table, self.delete_selected,
            [("Редактировать часы", self.edit_selected)]
        )
        self.actions_bar.attach(self.table)

        layout.addLayout(form_layout)
        layout.addLayout(filter_layout)
        layout.addWidget(self.actions_bar)
        layout.addWidget(self.table)

        self.setLayout(layout)

        self.load_combos()
        self.load_table()

    def load_combos(self):
        conn = get_connection()
        cursor = conn.cursor()

        cur_teacher = self.teacher_combo.currentData()
        cur_class = self.class_combo.currentData()

        # 1. Учителя
        self.teacher_combo.blockSignals(True)
        self.teacher_combo.clear()
        cursor.execute("SELECT ид, фио FROM УЧИТЕЛЬ ORDER BY фио")
        for row in cursor.fetchall():
            self.teacher_combo.addItem(row["фио"], row["ид"])
        self.teacher_combo.blockSignals(False)

        if cur_teacher:
            idx = self.teacher_combo.findData(cur_teacher)
            if idx >= 0:
                self.teacher_combo.setCurrentIndex(idx)

        # 2. Классы
        self.class_combo.blockSignals(True)
        self.class_combo.clear()
        cursor.execute("SELECT ид, параллель, буква FROM КЛАСС ORDER BY CAST(параллель AS INTEGER), буква")
        for row in cursor.fetchall():
            название = f"{row['параллель']}{row['буква']}"
            self.class_combo.addItem(название, row["ид"])
        self.class_combo.blockSignals(False)

        if cur_class:
            idx = self.class_combo.findData(cur_class)
            if idx >= 0:
                self.class_combo.setCurrentIndex(idx)

        conn.close()

        # Обновляем предметы учителя
        self.on_teacher_changed()

    def on_teacher_changed(self):
        """Фильтрует список предметов, показывая только те, что ведёт данный учитель."""
        учитель_ид = self.teacher_combo.currentData()
        self.subject_combo.blockSignals(True)
        self.subject_combo.clear()

        if учитель_ид is not None:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT П.ид, П.название
                FROM УЧИТЕЛЬ_ПРЕДМЕТ УП
                JOIN ПРЕДМЕТ П ON УП.предмет_ид = П.ид
                WHERE УП.учитель_ид = ?
                ORDER BY П.название
            """, (учитель_ид,))
            rows = cursor.fetchall()
            conn.close()

            for row in rows:
                self.subject_combo.addItem(row["название"], row["ид"])

        if self.subject_combo.count() == 0:
            self.subject_combo.addItem("— нет предметов у учителя —", None)

        self.subject_combo.blockSignals(False)
        self.on_subject_or_class_changed()

    def on_subject_or_class_changed(self):
        """Подтягивает часы из учебного плана выбранного класса по данному предмету."""
        класс_ид = self.class_combo.currentData()
        предмет_ид = self.subject_combo.currentData()

        if класс_ид is None or предмет_ид is None:
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT часов_в_неделю FROM УЧЕБНЫЙ_ПЛАН
            WHERE класс_ид = ? AND предмет_ид = ?
        """, (класс_ид, предмет_ид))
        row = cursor.fetchone()
        conn.close()

        if row and row["часов_в_неделю"]:
            self.hours_input.setValue(row["часов_в_неделю"])

    def load_table(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT УПК.ид, У.фио, П.название as предмет, К.параллель, К.буква,
                   УПК.учитель_ид, УПК.предмет_ид, УПК.класс_ид, УПК.часов
            FROM УЧИТЕЛЬ_ПРЕДМЕТ_КЛАСС УПК
            JOIN УЧИТЕЛЬ У ON УПК.учитель_ид = У.ид
            JOIN ПРЕДМЕТ П ON УПК.предмет_ид = П.ид
            JOIN КЛАСС К ON УПК.класс_ид = К.ид
            ORDER BY CAST(К.параллель AS INTEGER), К.буква, П.название, У.фио
        """)
        rows = cursor.fetchall()
        conn.close()

        self.table.setRowCount(0)
        for row in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            класс_название = f"{row['параллель']}{row['буква']}"
            ч = row["часов"]

            it_teacher = QTableWidgetItem(row["фио"])
            it_subject = QTableWidgetItem(row["предмет"])
            it_class = QTableWidgetItem(класс_название)
            it_hours = QTableWidgetItem(str(ч))

            it_class.setTextAlignment(Qt.AlignCenter)
            it_hours.setTextAlignment(Qt.AlignCenter)

            self.table.setItem(r, 0, it_teacher)
            self.table.setItem(r, 1, it_subject)
            self.table.setItem(r, 2, it_class)
            self.table.setItem(r, 3, it_hours)

            # Сохраняем ID в ячейках
            self.table.item(r, 0).setData(256, row["учитель_ид"])
            self.table.item(r, 1).setData(256, row["предмет_ид"])
            self.table.item(r, 2).setData(256, row["класс_ид"])
            self.table.item(r, 3).setData(256, row["ид"])  # первичный ключ

        self.apply_filter()

    def apply_filter(self):
        text = self.filter_input.text().strip().lower()
        for r in range(self.table.rowCount()):
            if not text:
                self.table.setRowHidden(r, False)
                continue
            row_text = " ".join([
                self.table.item(r, 0).text().lower(),
                self.table.item(r, 1).text().lower(),
                self.table.item(r, 2).text().lower()
            ])
            self.table.setRowHidden(r, text not in row_text)
        # Скрытые фильтром строки не считаются выбранными
        self.actions_bar.update_state()

    def add_assignment(self):
        учитель_ид = self.teacher_combo.currentData()
        предмет_ид = self.subject_combo.currentData()
        класс_ид = self.class_combo.currentData()
        часов = self.hours_input.value()

        if учитель_ид is None or предмет_ид is None or класс_ид is None:
            QMessageBox.warning(self, "Ошибка", "Выберите учителя, предмет и класс")
            return

        conn = get_connection()
        cursor = conn.cursor()

        # Проверяем, назначен ли уже этот предмет в этом классе
        cursor.execute("""
            SELECT УПК.учитель_ид, У.фио, УПК.часов
            FROM УЧИТЕЛЬ_ПРЕДМЕТ_КЛАСС УПК
            JOIN УЧИТЕЛЬ У ON УПК.учитель_ид = У.ид
            WHERE УПК.класс_ид = ? AND УПК.предмет_ид = ?
        """, (класс_ид, предмет_ид))
        existing = cursor.fetchone()

        предмет_название = self.subject_combo.currentText()
        класс_название = self.class_combo.currentText()
        учитель_фио = self.teacher_combo.currentText()

        if existing:
            текущий_учитель_ид = existing["учитель_ид"]
            текущий_фио = existing["фио"]
            if текущий_учитель_ид == учитель_ид:
                ответ = QMessageBox.question(
                    self, "Подтверждение",
                    f"Предмет «{предмет_название}» в {класс_название} уже ведёт {учитель_фио} ({existing['часов']} ч.). Обновить часы на {часов} ч.?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if ответ == QMessageBox.Yes:
                    cursor.execute("""
                        UPDATE УЧИТЕЛЬ_ПРЕДМЕТ_КЛАСС SET часов = ?
                        WHERE класс_ид = ? AND предмет_ид = ?
                    """, (часов, класс_ид, предмет_ид))
                    _sync_teacher_class(cursor, учитель_ид, класс_ид)
                    conn.commit()
                conn.close()
                self.load_table()
                return
            else:
                ответ = QMessageBox.question(
                    self, "Переназначение учителя",
                    f"Предмет «{предмет_название}» в {класс_название} сейчас ведёт <b>{текущий_фио}</b>.<br>"
                    f"Переназначить на <b>{учитель_фио}</b> ({часов} ч.)?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if ответ == QMessageBox.No:
                    conn.close()
                    return
                cursor.execute("""
                    UPDATE УЧИТЕЛЬ_ПРЕДМЕТ_КЛАСС SET учитель_ид = ?, часов = ?
                    WHERE класс_ид = ? AND предмет_ид = ?
                """, (учитель_ид, часов, класс_ид, предмет_ид))
                _sync_teacher_class(cursor, текущий_учитель_ид, класс_ид)
                _sync_teacher_class(cursor, учитель_ид, класс_ид)
                conn.commit()
                conn.close()
                self.load_table()
                return

        # Добавляем новое назначение
        cursor.execute("""
            INSERT INTO УЧИТЕЛЬ_ПРЕДМЕТ_КЛАСС (учитель_ид, предмет_ид, класс_ид, часов)
            VALUES (?, ?, ?, ?)
        """, (учитель_ид, предмет_ид, класс_ид, часов))
        _sync_teacher_class(cursor, учитель_ид, класс_ид)
        conn.commit()
        conn.close()
        self.load_table()

    def edit_selected(self):
        строки = selected_rows(self.table)
        if len(строки) != 1:
            QMessageBox.warning(self, "Ошибка", "Выберите одну строку для редактирования")
            return

        row = строки[0]
        учитель_ид = self.table.item(row, 0).data(256)
        класс_ид = self.table.item(row, 2).data(256)
        учитель_фио = self.table.item(row, 0).text()
        предмет_название = self.table.item(row, 1).text()
        класс_название = self.table.item(row, 2).text()
        часов = int(self.table.item(row, 3).text() or "0")
        запись_ид = self.table.item(row, 3).data(256)

        dialog = EditAssignmentHoursDialog(учитель_фио, предмет_название, класс_название, часов, self)
        if dialog.exec() == QDialog.Accepted:
            новые_часы = dialog.get_data()
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE УЧИТЕЛЬ_ПРЕДМЕТ_КЛАСС SET часов = ? WHERE ид = ?
            """, (новые_часы, запись_ид))
            _sync_teacher_class(cursor, учитель_ид, класс_ид)
            conn.commit()
            conn.close()
            self.load_table()

    def delete_selected(self):
        выбранные_строки = selected_rows(self.table)
        if not выбранные_строки:
            QMessageBox.warning(self, "Ошибка", "Выберите строки для удаления")
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
        пары_для_синхр = set()
        for строка in выбранные_строки:
            учитель_ид = self.table.item(строка, 0).data(256)
            класс_ид = self.table.item(строка, 2).data(256)
            пары_для_синхр.add((учитель_ид, класс_ид))
            запись_ид = self.table.item(строка, 3).data(256)
            cursor.execute("DELETE FROM УЧИТЕЛЬ_ПРЕДМЕТ_КЛАСС WHERE ид = ?", (запись_ид,))

        for у_ид, к_ид in пары_для_синхр:
            _sync_teacher_class(cursor, у_ид, к_ид)

        conn.commit()
        conn.close()
        self.load_table()
