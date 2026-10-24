from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox,
    QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from database.connection import get_connection


ДНИ = {
    1: "Понедельник", 2: "Вторник", 3: "Среда",
    4: "Четверг", 5: "Пятница", 6: "Суббота"
}

ТИП_УЧИТЕЛЬ = "Учитель в двух местах"
ТИП_КЛАСС = "Несколько предметов у класса"
ТИП_НЕРАБОЧИЙ = "Урок в нерабочий день"

ЦВЕТА = {
    ТИП_УЧИТЕЛЬ: QColor("#fde2e2"),
    ТИП_КЛАСС: QColor("#fff1d6"),
    ТИП_НЕРАБОЧИЙ: QColor("#e3ecfb"),
}


class ConflictsTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        top_layout = QHBoxLayout()

        refresh_btn = QPushButton("Проверить")
        refresh_btn.clicked.connect(self.load_conflicts)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Все накладки", ТИП_УЧИТЕЛЬ, ТИП_КЛАСС, ТИП_НЕРАБОЧИЙ])
        self.type_combo.currentIndexChanged.connect(self.fill_table)

        top_layout.addWidget(refresh_btn)
        top_layout.addWidget(QLabel("Показать:"))
        top_layout.addWidget(self.type_combo)
        top_layout.addStretch()

        self.summary_label = QLabel()

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Тип", "День", "Урок", "Кто", "Что накладывается"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setWordWrap(True)

        layout.addLayout(top_layout)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.накладки = []
        self.load_conflicts()

    def load_conflicts(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT У.день_недели, У.номер_урока,
                   У.учитель_ид, У.класс_ид,
                   К.параллель || К.буква AS класс,
                   П.название AS предмет,
                   УЧ.фио AS учитель
            FROM УРОК У
            JOIN КЛАСС К ON У.класс_ид = К.ид
            JOIN ПРЕДМЕТ П ON У.предмет_ид = П.ид
            LEFT JOIN УЧИТЕЛЬ УЧ ON У.учитель_ид = УЧ.ид
            ORDER BY У.день_недели, У.номер_урока
        """)
        уроки = cursor.fetchall()

        cursor.execute("""
            SELECT ид_сущности, значение FROM ОГРАНИЧЕНИЕ
            WHERE тип_сущности = 'учитель' AND тип_правила = 'нерабочий_день'
        """)
        нерабочие = {(row["ид_сущности"], str(row["значение"])) for row in cursor.fetchall()}
        conn.close()

        по_учителю = {}
        по_классу = {}
        for урок in уроки:
            время = (урок["день_недели"], урок["номер_урока"])
            if урок["учитель_ид"] is not None:
                по_учителю.setdefault((урок["учитель_ид"],) + время, []).append(урок)
            по_классу.setdefault((урок["класс_ид"],) + время, []).append(урок)

        self.накладки = []

        for (_, день, номер), группа in по_учителю.items():
            if len(группа) > 1:
                что = ", ".join(f"{у['класс']} — {у['предмет']}" for у in группа)
                self.накладки.append((ТИП_УЧИТЕЛЬ, день, номер, группа[0]["учитель"], что))

        for (_, день, номер), группа in по_классу.items():
            if len(группа) > 1:
                что = ", ".join(f"{у['предмет']} ({у['учитель'] or 'без учителя'})" for у in группа)
                self.накладки.append((ТИП_КЛАСС, день, номер, группа[0]["класс"], что))

        for урок in уроки:
            if (урок["учитель_ид"], str(урок["день_недели"])) in нерабочие:
                что = f"{урок['класс']} — {урок['предмет']}"
                self.накладки.append((ТИП_НЕРАБОЧИЙ, урок["день_недели"], урок["номер_урока"], урок["учитель"], что))

        self.накладки.sort(key=lambda н: (н[1], н[2], н[0]))
        self.fill_table()

    def fill_table(self):
        фильтр = self.type_combo.currentText()
        строки = [н for н in self.накладки if фильтр == "Все накладки" or н[0] == фильтр]

        self.table.setRowCount(0)
        for тип, день, номер, кто, что in строки:
            r = self.table.rowCount()
            self.table.insertRow(r)
            значения = [тип, ДНИ.get(день, str(день)), f"{номер} урок", кто or "", что]
            for c, текст in enumerate(значения):
                item = QTableWidgetItem(текст)
                item.setBackground(ЦВЕТА[тип])
                if c in (1, 2):
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(r, c, item)
        self.table.resizeRowsToContents()

        if not self.накладки:
            self.summary_label.setText("Накладок не найдено ✔")
        else:
            по_типам = {}
            for н in self.накладки:
                по_типам[н[0]] = по_типам.get(н[0], 0) + 1
            детали = ", ".join(f"{тип.lower()}: {кол}" for тип, кол in по_типам.items())
            self.summary_label.setText(f"Найдено накладок: {len(self.накладки)} ({детали})")
