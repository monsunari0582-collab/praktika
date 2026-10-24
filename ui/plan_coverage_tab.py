from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QCheckBox,
    QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from collections import defaultdict

from database.connection import get_connection
from algorithm.scheduler import ступень_по_параллели


ОК = "ok"
ВНИМАНИЕ = "warning"
ОШИБКА = "error"

ЦВЕТА = {
    ОК: QColor("#e6f4ea"),
    ВНИМАНИЕ: QColor("#fff1d6"),
    ОШИБКА: QColor("#fde2e2"),
}


class PlanCoverageTab(QWidget):
    """Сверка учебного плана с распределением учителей и готовым расписанием."""

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        top_layout = QHBoxLayout()

        refresh_btn = QPushButton("Проверить")
        refresh_btn.clicked.connect(self.load_coverage)

        self.class_combo = QComboBox()
        self.class_combo.currentIndexChanged.connect(self.fill_table)

        self.problems_only = QCheckBox("Только проблемы")
        self.problems_only.toggled.connect(self.fill_table)

        top_layout.addWidget(refresh_btn)
        top_layout.addWidget(QLabel("Класс:"))
        top_layout.addWidget(self.class_combo)
        top_layout.addWidget(self.problems_only)
        top_layout.addStretch()

        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Класс", "Предмет", "По плану", "Распределено", "Учитель", "В расписании", "Статус"
        ])
        header = self.table.horizontalHeader()
        for c in (0, 2, 3, 5):
            header.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(6, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setDefaultSectionSize(36)

        layout.addLayout(top_layout)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.строки = []
        self.есть_расписание = False
        self.load_coverage()

    def load_coverage(self):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT ид, параллель, буква FROM КЛАСС ORDER BY CAST(параллель AS INTEGER), буква")
        строки_классов = cursor.fetchall()
        классы = [(row["ид"], f"{row['параллель']}{row['буква']}") for row in строки_классов]
        порядок_класса = {ид: i for i, (ид, _) in enumerate(классы)}
        название_класса = dict(классы)
        ступень_класса = {row["ид"]: ступень_по_параллели(row["параллель"]) for row in строки_классов}

        cursor.execute("SELECT ид, название FROM ПРЕДМЕТ")
        # В некоторых названиях есть переносы строк — в строке таблицы они обрезаются
        название_предмета = {row["ид"]: " ".join(row["название"].split()) for row in cursor.fetchall()}

        cursor.execute("SELECT класс_ид, предмет_ид, часов_в_неделю FROM УЧЕБНЫЙ_ПЛАН")
        план = {(row["класс_ид"], row["предмет_ид"]): row["часов_в_неделю"] for row in cursor.fetchall()}

        cursor.execute("""
            SELECT УПК.класс_ид, УПК.предмет_ид, УПК.часов, У.фио
            FROM УЧИТЕЛЬ_ПРЕДМЕТ_КЛАСС УПК
            JOIN УЧИТЕЛЬ У ON УПК.учитель_ид = У.ид
        """)
        распределено = {(row["класс_ид"], row["предмет_ид"]): (row["часов"], row["фио"]) for row in cursor.fetchall()}

        # Подходящие учителя: ведут предмет и работают в ступени класса
        cursor.execute("""
            SELECT УП.предмет_ид, У.работает_1_4, У.работает_5_9, У.работает_10_11
            FROM УЧИТЕЛЬ_ПРЕДМЕТ УП JOIN УЧИТЕЛЬ У ON У.ид = УП.учитель_ид
        """)
        кандидатов = defaultdict(int)  # (предмет_ид, ступень) -> сколько учителей
        for row in cursor.fetchall():
            for ступень, колонка in (("1-4", "работает_1_4"), ("5-9", "работает_5_9"), ("10-11", "работает_10_11")):
                if row[колонка]:
                    кандидатов[(row["предмет_ид"], ступень)] += 1

        cursor.execute("""
            SELECT У.класс_ид, У.предмет_ид, COUNT(*) AS n, MIN(УЧ.фио) AS фио
            FROM УРОК У
            LEFT JOIN УЧИТЕЛЬ УЧ ON У.учитель_ид = УЧ.ид
            GROUP BY У.класс_ид, У.предмет_ид
        """)
        в_расписании = {(row["класс_ид"], row["предмет_ид"]): (row["n"], row["фио"]) for row in cursor.fetchall()}
        conn.close()

        self.есть_расписание = bool(в_расписании)
        self.строки = []

        for ключ in set(план) | set(распределено):
            класс_ид, предмет_ид = ключ
            if класс_ид not in название_класса:
                continue
            нужно = план.get(ключ)
            назн_часов, фио = распределено.get(ключ, (None, None))
            поставлено, фио_в_расписании = в_расписании.get(ключ, (0, None))

            учитель = фио or ""
            if not фио and фио_в_расписании:
                учитель = f"{фио_в_расписании} (подобран автоматически)"

            подходящих = кандидатов.get((предмет_ид, ступень_класса[класс_ид]), 0)

            if нужно is None:
                статус, текст = ОШИБКА, "Назначено, но предмета нет в учебном плане"
            elif назн_часов is None and not подходящих:
                статус, текст = ОШИБКА, "Нет учителя по этому предмету, работающего в этих классах"
            elif назн_часов is not None and назн_часов < нужно:
                статус, текст = ОШИБКА, f"Распределено меньше плана на {нужно - назн_часов} ч."
            elif self.есть_расписание and поставлено < нужно:
                статус, текст = ОШИБКА, f"Не поставлено в расписание {нужно - поставлено} ч."
            elif назн_часов is not None and назн_часов > нужно:
                статус, текст = ВНИМАНИЕ, f"Распределено больше плана на {назн_часов - нужно} ч."
            elif назн_часов is None:
                статус, текст = ВНИМАНИЕ, (
                    f"Не распределено — учитель подберётся автоматически "
                    f"(подходящих: {подходящих})"
                )
            else:
                статус, текст = ОК, "Всё в порядке"

            self.строки.append({
                "класс_ид": класс_ид,
                "порядок": (порядок_класса[класс_ид], название_предмета.get(предмет_ид, "")),
                "значения": [
                    название_класса[класс_ид],
                    название_предмета.get(предмет_ид, str(предмет_ид)),
                    "—" if нужно is None else str(нужно),
                    "—" if назн_часов is None else str(назн_часов),
                    учитель,
                    str(поставлено) if self.есть_расписание else "—",
                    текст,
                ],
                "статус": статус,
                "нужно": нужно or 0,
                "назначено": назн_часов or 0,
                "поставлено": поставлено,
            })

        self.строки.sort(key=lambda с: с["порядок"])

        выбранный = self.class_combo.currentData()
        self.class_combo.blockSignals(True)
        self.class_combo.clear()
        self.class_combo.addItem("Все классы", None)
        for ид, название in классы:
            self.class_combo.addItem(название, ид)
        индекс = self.class_combo.findData(выбранный)
        self.class_combo.setCurrentIndex(индекс if индекс >= 0 else 0)
        self.class_combo.blockSignals(False)

        self.fill_table()

    def fill_table(self):
        класс_ид = self.class_combo.currentData()
        строки = [с for с in self.строки if класс_ид is None or с["класс_ид"] == класс_ид]

        план = sum(с["нужно"] for с in строки)
        назначено = sum(min(с["назначено"], с["нужно"]) for с in строки)
        поставлено = sum(с["поставлено"] for с in строки)
        ошибок = sum(с["статус"] == ОШИБКА for с in строки)
        предупреждений = sum(с["статус"] == ВНИМАНИЕ for с in строки)

        итог = f"По плану: {план} ч. · Распределено учителям: {назначено} ч."
        if self.есть_расписание:
            итог += f" · В расписании: {поставлено} ч."
        else:
            итог += " · Расписание ещё не составлено"
        if ошибок or предупреждений:
            итог += f"\nПроблем: {ошибок} · Требуют внимания: {предупреждений}"
        else:
            итог += "\nВсё заполнено ✔"
        self.summary_label.setText(итог)

        if self.problems_only.isChecked():
            # Сначала ошибки, затем то, что требует внимания
            строки = sorted(
                (с for с in строки if с["статус"] != ОК),
                key=lambda с: с["статус"] != ОШИБКА
            )

        self.table.setRowCount(0)
        for с in строки:
            r = self.table.rowCount()
            self.table.insertRow(r)
            for c, текст in enumerate(с["значения"]):
                item = QTableWidgetItem(текст)
                item.setBackground(ЦВЕТА[с["статус"]])
                if c in (0, 2, 3, 5):
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(r, c, item)
