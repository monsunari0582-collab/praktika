from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QLabel, QMessageBox,
    QDialog, QDialogButtonBox, QCheckBox,
    QHeaderView
)
from PySide6.QtGui import QColor, QFont
from PySide6.QtCore import Qt
from database.connection import get_connection
from ui.table_actions import ActionBar, selected_rows


def _ступень(параллель):
    """Определяет ступень по параллели: 1-4 / 5-9 / 10-11. Иначе None."""
    try:
        n = int(параллель)
    except (ValueError, TypeError):
        return None
    if 1 <= n <= 4:
        return "1-4"
    if 5 <= n <= 9:
        return "5-9"
    if 10 <= n <= 11:
        return "10-11"
    return None


class TeacherHoursDialog(QDialog):
    """Показывает плановую и фактическую нагрузку учителя (по ступеням и по классам)."""
    def __init__(self, учитель_ид, фио, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Часы учителя: {фио}")
        self.setGeometry(100, 100, 720, 620)

        layout = QVBoxLayout()

        conn = get_connection()
        cursor = conn.cursor()

        # Часы по распределению предметов (их считает программа, а не вводит пользователь)
        cursor.execute("""
            SELECT К.ид, К.параллель, К.буква, SUM(УПК.часов) as часов
            FROM УЧИТЕЛЬ_ПРЕДМЕТ_КЛАСС УПК
            JOIN КЛАСС К ON УПК.класс_ид = К.ид
            WHERE УПК.учитель_ид = ?
            GROUP BY К.ид, К.параллель, К.буква
            ORDER BY CAST(К.параллель AS INTEGER), К.буква
        """, (учитель_ид,))
        план_классы = {row["ид"]: (f"{row['параллель']}{row['буква']}", row["параллель"], row["часов"] or 0)
                       for row in cursor.fetchall()}

        # Фактическая нагрузка ИЗ РАСПИСАНИЯ (таблица УРОК)
        cursor.execute("""
            SELECT У.класс_ид, П.название, К.параллель, К.буква, COUNT(*) AS часов
            FROM УРОК У
            JOIN ПРЕДМЕТ П ON У.предмет_ид = П.ид
            JOIN КЛАСС К ON У.класс_ид = К.ид
            WHERE У.учитель_ид = ?
            GROUP BY У.класс_ид, П.название, К.параллель, К.буква
            ORDER BY CAST(К.параллель AS INTEGER), К.буква, П.название
        """, (учитель_ид,))
        детали = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) AS n FROM УРОК")
        расписание_есть = cursor.fetchone()["n"] > 0
        conn.close()

        # Считаем факт по ступеням и по классам
        факт = {"1-4": 0, "5-9": 0, "10-11": 0}
        факт_вне = 0
        факт_по_классам = {}  # класс_ид -> часов

        for row in детали:
            b = _ступень(row["параллель"])
            if b is None:
                факт_вне += row["часов"]
            else:
                факт[b] += row["часов"]
            факт_по_классам[row["класс_ид"]] = факт_по_классам.get(row["класс_ид"], 0) + row["часов"]

        распределено = sum(ч for _, _, ч in план_классы.values())
        факт_всего = sum(факт.values()) + факт_вне

        # --- Баннер сверху ---
        if распределено == 0 and факт_всего == 0:
            текст = "Учителю пока ничего не распределено."
            bg, fg = "#FFF4E0", "#B8860B"
        elif not расписание_есть:
            текст = (f"По распределению: {распределено} ч в неделю. Расписание ещё не составлено — "
                     f"нажмите «Составить расписание», чтобы увидеть, сколько встало.")
            bg, fg = "#FFF4E0", "#B8860B"
        elif факт_всего == распределено:
            текст = f"По распределению: {распределено} ч · В расписании: {факт_всего} ч · всё встало"
            bg, fg = "#E0F5E0", "#1B7A1B"
        else:
            текст = (f"По распределению: {распределено} ч · В расписании: {факт_всего} ч · "
                     f"не встало {распределено - факт_всего} ч")
            bg, fg = "#FFE0E0", "#CC0000"

        banner = QLabel(текст)
        banner.setWordWrap(True)
        banner.setStyleSheet(
            f"QLabel {{ background-color:{bg}; color:{fg}; font-weight:bold; "
            f"padding:10px 12px; border-radius:6px; }}"
        )
        layout.addWidget(banner)

        # --- Таблица по классам (План vs Факт) ---
        все_ид_классов = set(план_классы.keys()) | set(факт_по_классам.keys())
        if все_ид_классов:
            layout.addWidget(QLabel("Нагрузка по классам (план и факт в расписании):"))
            class_table = QTableWidget()
            class_table.setColumnCount(4)
            class_table.setHorizontalHeaderLabels(["Класс", "Распределено (ч)", "В расписании (ч)", "Статус"])
            class_table.horizontalHeader().setStretchLastSection(False)
            class_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            class_table.setColumnWidth(1, 100)
            class_table.setColumnWidth(2, 130)
            class_table.setColumnWidth(3, 140)
            class_table.setEditTriggers(QTableWidget.NoEditTriggers)
            class_table.setSelectionMode(QTableWidget.NoSelection)
            class_table.verticalHeader().setVisible(False)
            class_table.verticalHeader().setDefaultSectionSize(32)

            conn = get_connection()
            c2 = conn.cursor()
            c2.execute("SELECT ид, параллель, буква FROM КЛАСС ORDER BY CAST(параллель AS INTEGER), буква")
            инфо_классов = {row["ид"]: f"{row['параллель']}{row['буква']}" for row in c2.fetchall()}
            conn.close()

            # Сортируем классы
            список_классов = sorted(
                list(все_ид_классов),
                key=lambda x: (int(''.join(filter(str.isdigit, инфо_классов.get(x, '0'))) or 0), инфо_классов.get(x, ''))
            )

            for кл_ид in список_классов:
                назв = инфо_классов.get(кл_ид, f"Класс #{кл_ид}")
                пл = план_классы.get(кл_ид, (None, None, 0))[2]
                фкт = факт_по_классам.get(кл_ид, 0)

                r = class_table.rowCount()
                class_table.insertRow(r)
                class_table.setItem(r, 0, QTableWidgetItem(назв))

                it_p = QTableWidgetItem(str(пл) if пл > 0 else "—")
                it_f = QTableWidgetItem(str(фкт))
                it_p.setTextAlignment(Qt.AlignCenter)
                it_f.setTextAlignment(Qt.AlignCenter)
                class_table.setItem(r, 1, it_p)
                class_table.setItem(r, 2, it_f)

                if пл == 0 and фкт == 0:
                    ст_текст, цвет = "—", "#7f8c8d"
                elif пл == 0 and фкт > 0:
                    ст_текст, цвет = "не распределено", "#B8860B"
                elif пл == фкт:
                    ст_текст, цвет = "заполнено", "#1B7A1B"
                elif фкт < пл:
                    ст_текст, цвет = f"не встало {пл - фкт}", "#B8860B"
                else:
                    ст_текст, цвет = f"лишние {фкт - пл}", "#CC0000"

                it_st = QTableWidgetItem(ст_текст)
                it_st.setForeground(QColor(цвет))
                it_st.setFont(QFont("Arial", 9, QFont.Bold))
                class_table.setItem(r, 3, it_st)

            class_table.setFixedHeight(min(class_table.rowCount() * 32 + 40, 180))
            layout.addWidget(class_table)

        # --- Детальная таблица (из расписания) ---
        layout.addWidget(QLabel("Подробно из расписания (предмет · класс · часы):"))
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Предмет", "Класс", "Часов в неделю"])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setColumnWidth(1, 80)
        self.table.setColumnWidth(2, 120)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        for row in детали:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(row["название"]))
            кл = QTableWidgetItem(f"{row['параллель']}{row['буква']}")
            кл.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 1, кл)
            чч = QTableWidgetItem(str(row["часов"]))
            чч.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 2, чч)

        layout.addWidget(self.table)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self.setLayout(layout)


# Ступени, в которых может работать учитель, и колонки таблицы УЧИТЕЛЬ
СТУПЕНИ_УЧИТЕЛЯ = [("1-4", "работает_1_4"), ("5-9", "работает_5_9"), ("10-11", "работает_10_11")]


def _флажки_ступеней(отмечено=()):
    """Флажки «1-4 / 5-9 / 10-11 кл.» в одну строку: (layout, {ступень: QCheckBox})."""
    layout = QHBoxLayout()
    флажки = {}
    for ступень, _ in СТУПЕНИ_УЧИТЕЛЯ:
        cb = QCheckBox(f"{ступень} кл.")
        cb.setChecked(ступень in отмечено)
        layout.addWidget(cb)
        флажки[ступень] = cb
    return layout, флажки


def _сохранить_ступени(cursor, учитель_ид, ступени):
    cursor.execute(
        "UPDATE УЧИТЕЛЬ SET работает_1_4 = ?, работает_5_9 = ?, работает_10_11 = ? WHERE ид = ?",
        tuple(int(ст in ступени) for ст, _ in СТУПЕНИ_УЧИТЕЛЯ) + (учитель_ид,)
    )


class EditTeacherDialog(QDialog):
    def __init__(self, фио, ступени, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактировать учителя")

        layout = QVBoxLayout()
        form_layout = QHBoxLayout()

        self.fio_input = QLineEdit(фио)

        form_layout.addWidget(QLabel("ФИО:"))
        form_layout.addWidget(self.fio_input)

        stages_layout, self.флажки = _флажки_ступеней(ступени)
        stages_layout.insertWidget(0, QLabel("Работает в классах:"))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addLayout(form_layout)
        layout.addLayout(stages_layout)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def get_data(self):
        ступени = {ст for ст, cb in self.флажки.items() if cb.isChecked()}
        return self.fio_input.text().strip(), ступени


class TeachersTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        form_layout = QHBoxLayout()

        self.fio_input = QLineEdit()
        self.fio_input.setPlaceholderText("ФИО учителя")

        stages_layout, self.флажки = _флажки_ступеней()

        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self.add_teacher)

        form_layout.addWidget(QLabel("ФИО:"))
        form_layout.addWidget(self.fio_input, 1)
        form_layout.addWidget(QLabel("Работает в классах:"))
        form_layout.addLayout(stages_layout)
        form_layout.addWidget(add_btn)

        hint = QLabel(
            "Часы не вводятся: их считает программа по распределению предметов "
            "(вкладка «Нагрузка по предметам» → «Распределить всё»)."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #7f8c8d;")

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ФИО", "Работает в классах", "1-4 кл", "5-9 кл", "10-11 кл", "Всего часов"])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setColumnWidth(1, 170)
        self.table.setColumnWidth(2, 70)
        self.table.setColumnWidth(3, 70)
        self.table.setColumnWidth(4, 80)
        self.table.setColumnWidth(5, 100)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setDefaultSectionSize(36)

        self.actions_bar = ActionBar(
            lambda: self.table, self.delete_selected,
            [
                ("Редактировать", self.edit_teacher),
                ("Просмотреть часы", self.view_teacher_hours),
            ]
        )
        self.actions_bar.attach(self.table)

        layout.addLayout(form_layout)
        layout.addWidget(hint)
        layout.addWidget(self.actions_bar)
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.load_teachers()

    def load_teachers(self):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT ид, фио, работает_1_4, работает_5_9, работает_10_11
            FROM УЧИТЕЛЬ ORDER BY фио
        """)
        teachers = cursor.fetchall()

        # Часы по распределению предметов, по ступеням
        cursor.execute("""
            SELECT УПК.учитель_ид, К.параллель, SUM(COALESCE(УПК.часов, 0)) AS часов_сумма
            FROM УЧИТЕЛЬ_ПРЕДМЕТ_КЛАСС УПК
            JOIN КЛАСС К ON УПК.класс_ид = К.ид
            GROUP BY УПК.учитель_ид, К.параллель
        """)
        часы = {}
        for row in cursor.fetchall():
            st = _ступень(row["параллель"])
            по_ступеням = часы.setdefault(row["учитель_ид"], {"1-4": 0, "5-9": 0, "10-11": 0})
            if st:
                по_ступеням[st] += row["часов_сумма"]
        conn.close()

        self.table.setRowCount(0)
        for row in teachers:
            r = self.table.rowCount()
            self.table.insertRow(r)
            uid = row["ид"]

            ступени = [ст for ст, кол in СТУПЕНИ_УЧИТЕЛЯ if row[кол]]
            по_ступеням = часы.get(uid, {"1-4": 0, "5-9": 0, "10-11": 0})
            всего = sum(по_ступеням.values())

            фио_item = QTableWidgetItem(row["фио"])
            ступени_item = QTableWidgetItem(", ".join(ступени) if ступени else "не указано")
            if not ступени:
                # Без ступеней учителя нельзя распределить автоматически
                ступени_item.setForeground(QColor("#CC0000"))
                фио_item.setForeground(QColor("#CC0000"))

            items = [QTableWidgetItem(str(по_ступеням[ст])) for ст, _ in СТУПЕНИ_УЧИТЕЛЯ]
            item_всего = QTableWidgetItem(str(всего))
            for it in items + [item_всего]:
                it.setTextAlignment(Qt.AlignCenter)
            item_всего.setForeground(QColor("#2979B8"))
            item_всего.setFont(QFont("Arial", 10, QFont.Bold))

            self.table.setItem(r, 0, фио_item)
            self.table.setItem(r, 1, ступени_item)
            for c, it in enumerate(items, start=2):
                self.table.setItem(r, c, it)
            self.table.setItem(r, 5, item_всего)
            self.table.item(r, 0).setData(256, uid)
            self.table.item(r, 1).setData(256, ступени)

    def add_teacher(self):
        фио = self.fio_input.text().strip()
        ступени = {ст for ст, cb in self.флажки.items() if cb.isChecked()}

        if not фио:
            QMessageBox.warning(self, "Ошибка", "Введите ФИО учителя")
            return
        if not ступени:
            QMessageBox.warning(self, "Ошибка", "Отметьте, в каких классах работает учитель")
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO УЧИТЕЛЬ (фио) VALUES (?)", (фио,))
        _сохранить_ступени(cursor, cursor.lastrowid, ступени)
        conn.commit()
        conn.close()

        self.fio_input.clear()
        for cb in self.флажки.values():
            cb.setChecked(False)
        self.load_teachers()

    def edit_teacher(self):
        строки = selected_rows(self.table)
        if len(строки) != 1:
            QMessageBox.warning(self, "Ошибка", "Выберите одного учителя")
            return

        row = строки[0]
        ид = self.table.item(row, 0).data(256)
        фио = self.table.item(row, 0).text()
        ступени = self.table.item(row, 1).data(256)

        dialog = EditTeacherDialog(фио, ступени, self)
        if dialog.exec() == QDialog.Accepted:
            новое_фио, новые_ступени = dialog.get_data()
            if not новое_фио:
                QMessageBox.warning(self, "Ошибка", "ФИО не может быть пустым")
                return

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE УЧИТЕЛЬ SET фио = ? WHERE ид = ?", (новое_фио, ид))
            _сохранить_ступени(cursor, ид, новые_ступени)
            conn.commit()
            conn.close()
            self.load_teachers()

    def delete_selected(self):
        выбранные_строки = selected_rows(self.table)
        if not выбранные_строки:
            QMessageBox.warning(self, "Ошибка", "Выберите учителей")
            return

        ответ = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить выбранных учителей ({len(выбранные_строки)} шт.)?\n"
            f"Их классы станут нераспределёнными.",
            QMessageBox.Yes | QMessageBox.No
        )
        if ответ == QMessageBox.No:
            return

        conn = get_connection()
        cursor = conn.cursor()
        for строка in выбранные_строки:
            ид = self.table.item(строка, 0).data(256)
            cursor.execute("DELETE FROM УЧИТЕЛЬ WHERE ид = ?", (ид,))
            cursor.execute("DELETE FROM УЧИТЕЛЬ_КЛАСС WHERE учитель_ид = ?", (ид,))
            cursor.execute("DELETE FROM УЧИТЕЛЬ_ПРЕДМЕТ WHERE учитель_ид = ?", (ид,))
            # Иначе в распределении остались бы назначения несуществующего учителя
            cursor.execute("DELETE FROM УЧИТЕЛЬ_ПРЕДМЕТ_КЛАСС WHERE учитель_ид = ?", (ид,))
        conn.commit()
        conn.close()
        self.load_teachers()

    def view_teacher_hours(self):
        строки = selected_rows(self.table)
        if len(строки) != 1:
            QMessageBox.warning(self, "Ошибка", "Выберите одного учителя")
            return

        row = строки[0]
        ид = self.table.item(row, 0).data(256)
        фио = self.table.item(row, 0).text()

        dialog = TeacherHoursDialog(ид, фио, self)
        dialog.exec()
