from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QMessageBox,
    QHeaderView, QDialog, QDialogButtonBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from database.connection import get_connection
from algorithm import load_balancer as lb


ЦВЕТ_ВНИМАНИЕ = QColor("#fff1d6")
ЦВЕТ_ОШИБКА = QColor("#fde2e2")
ЦВЕТ_ИЗМЕНЕНИЕ = QColor("#e8f0fe")

НАЗВАНИЕ_СТУПЕНИ = {"1-4": "1–4 кл.", "5-9": "5–9 кл.", "10-11": "10–11 кл."}


def _ячейка(текст, по_центру=False, цвет=None, жирный=False):
    item = QTableWidgetItem(текст)
    if по_центру:
        item.setTextAlignment(Qt.AlignCenter)
    if цвет is not None:
        item.setBackground(цвет)
    if жирный:
        шрифт = QFont()
        шрифт.setBold(True)
        item.setFont(шрифт)
    return item


def _таблица(заголовки, растянуть):
    table = QTableWidget()
    table.setColumnCount(len(заголовки))
    table.setHorizontalHeaderLabels(заголовки)
    header = table.horizontalHeader()
    for c in range(len(заголовки)):
        header.setSectionResizeMode(c, QHeaderView.Stretch if c in растянуть else QHeaderView.ResizeToContents)
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    table.setSelectionMode(QTableWidget.NoSelection)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(36)
    return table


def _предметы_блока(data, блок):
    return ", ".join(f"{data['предметы'][п]} {ч}" for п, ч in блок["предметы"])


def _название_группы(data, группа):
    имена = sorted(data["предметы"][п] for п in группа["предметы"])
    if len(имена) > 4:
        имена = имена[:3] + [f"и ещё {len(имена) - 3}"]
    return f"{НАЗВАНИЕ_СТУПЕНИ[группа['ступень']]} · {', '.join(имена)}"


def _ступени_текст(data, учитель_ид):
    return ", ".join(ст for ст in lb.СТУПЕНИ if ст in data["учителя"][учитель_ид]["ступени"])


def _фио(data, у):
    if у is None:
        return "— не назначен —"
    if у == "разные":
        return "— разные учителя —"
    return data["учителя"][у]["фио"] if у in data["учителя"] else f"учитель №{у}"


class ProposalDialog(QDialog):
    """Предложенное распределение: было → станет. Применяется только по кнопке.

    варианты — список (группа, блоки, учителя_блоков) для одной или всех групп.
    """

    def __init__(self, data, варианты, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Предложенное распределение")
        self.resize(980, 660)

        одна_группа = len(варианты) == 1
        изменения = [
            (группа, б, у) for группа, блоки, предложение in варианты
            for б, у in zip(блоки, предложение) if у is not None and у != б["текущий"]
        ]
        всего_блоков = sum(len(блоки) for _, блоки, _ in варианты)

        layout = QVBoxLayout()
        layout.addWidget(QLabel(
            f"Изменится классов: {len(изменения)} из {всего_блоков}. "
            f"Программа делит классы так, чтобы общая нагрузка учителей была как можно ровнее."
        ))

        # Для одной группы показываем все классы, для всех — только изменения
        строки = (
            [(варианты[0][0], б, у) for б, у in zip(варианты[0][1], варианты[0][2])]
            if одна_группа else изменения
        )
        заголовки = ["Класс", "Предметы", "Часов", "Было", "Станет"]
        классы = _таблица(заголовки, растянуть={1, 3, 4})
        for группа, б, у in строки:
            r = классы.rowCount()
            классы.insertRow(r)
            изменено = у is not None and у != б["текущий"]
            значения = [б["класс"]["название"], _предметы_блока(data, б), str(б["часов"]),
                        _фио(data, б["текущий"]), _фио(data, у) if у is not None else "нет подходящего учителя"]
            for c, текст in enumerate(значения):
                классы.setItem(r, c, _ячейка(текст, по_центру=c in (0, 2),
                                             цвет=ЦВЕТ_ИЗМЕНЕНИЕ if изменено else None,
                                             жирный=изменено and c == 4))
        layout.addWidget(классы, 3)

        # Нагрузка учителей до и после
        блоки_все = [б for _, блоки, _ in варианты for б in блоки]
        учителя_все = [у for _, _, предложение in варианты for у in предложение]
        было = lb.loads_after(data, [], [])
        станет = lb.loads_after(data, блоки_все, учителя_все)
        затронутые = sorted(
            {у for группа, _, _ in варианты for у in группа["учителя"]},
            key=lambda у: data["учителя"][у]["фио"]
        )
        учителя = _таблица(["Учитель", "Было часов", "Станет часов"], растянуть={0})
        for у in затронутые:
            r = учителя.rowCount()
            учителя.insertRow(r)
            изменилось = было.get(у, 0) != станет.get(у, 0)
            for c, значение in enumerate([data["учителя"][у]["фио"], str(было.get(у, 0)), str(станет.get(у, 0))]):
                учителя.setItem(r, c, _ячейка(значение, по_центру=c > 0, жирный=изменилось and c == 2))
        layout.addWidget(QLabel("Нагрузка учителей (всего часов в неделю):"))
        layout.addWidget(учителя, 2)

        buttons = QDialogButtonBox()
        buttons.addButton("Применить", QDialogButtonBox.AcceptRole)
        отмена = buttons.addButton("Отмена", QDialogButtonBox.RejectRole)
        отмена.setObjectName("btn_secondary")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)


class SubjectLoadTab(QWidget):
    """Распределение классов между учителями и итоговая нагрузка."""

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        top_layout = QHBoxLayout()
        self.group_combo = QComboBox()
        self.group_combo.currentIndexChanged.connect(self.show_group)

        propose_btn = QPushButton("Распределить группу")
        propose_btn.setObjectName("btn_secondary")
        propose_btn.clicked.connect(self.propose)

        propose_all_btn = QPushButton("Распределить всё")
        propose_all_btn.clicked.connect(self.propose_all)

        top_layout.addWidget(QLabel("Группа предметов:"))
        top_layout.addWidget(self.group_combo, 1)
        top_layout.addWidget(propose_btn)
        top_layout.addWidget(propose_all_btn)

        hint = QLabel(
            "Программа сама делит классы между учителями, которые ведут предмет и работают в этой ступени, "
            "так, чтобы нагрузка была как можно ровнее. Все предметы, которые могут вести одни и те же учителя, "
            "в классе ведёт один учитель. Учителя можно поменять вручную прямо в таблице. "
            "⚠ — есть нераспределённые классы."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #7f8c8d;")

        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("font-weight: bold; padding: 4px 0;")

        self.teachers_table = _таблица(
            ["Учитель", "Работает в классах", "Часов в этой группе", "Всего часов"], растянуть={0}
        )
        self.classes_table = _таблица(["Класс", "Предметы и часы", "Часов", "Учитель"], растянуть={1, 3})

        layout.addLayout(top_layout)
        layout.addWidget(hint)
        layout.addWidget(self.summary_label)
        layout.addWidget(QLabel("Учителя:"))
        layout.addWidget(self.teachers_table)
        layout.addWidget(QLabel("Классы:"))
        layout.addWidget(self.classes_table, 1)

        self.setLayout(layout)
        self.data = None
        self.groups = []
        self.blocks = []
        self.load_table()

    # ---------- загрузка ----------

    def load_table(self):
        conn = get_connection()
        self.data = lb.load_data(conn.cursor())
        conn.close()
        self.groups = lb.find_groups(self.data)

        прежняя = self.group_combo.currentData()
        self.group_combo.blockSignals(True)
        self.group_combo.clear()
        первая_с_проблемой = None
        for i, группа in enumerate(self.groups):
            # Строковый ключ: findData не умеет сравнивать Python-объекты вроде frozenset
            ключ = группа["ступень"] + ":" + ",".join(map(str, sorted(группа["предметы"])))
            проблема = self._есть_проблема(группа)
            if проблема and первая_с_проблемой is None:
                первая_с_проблемой = i
            self.group_combo.addItem(f"{'⚠ ' if проблема else ''}{_название_группы(self.data, группа)}", ключ)

        индекс = self.group_combo.findData(прежняя) if прежняя is not None else -1
        if индекс < 0:
            индекс = первая_с_проблемой if первая_с_проблемой is not None else 0
        self.group_combo.setCurrentIndex(индекс)
        self.group_combo.blockSignals(False)
        self.show_group()

    def _есть_проблема(self, группа):
        return any(
            б["текущий"] is None or б["текущий"] == "разные" or not б["подходящие"]
            for б in lb.build_blocks(self.data, группа)
        )

    def current_group(self):
        i = self.group_combo.currentIndex()
        return self.groups[i] if 0 <= i < len(self.groups) else None

    # ---------- отображение ----------

    def show_group(self):
        self.classes_table.setRowCount(0)
        self.teachers_table.setRowCount(0)
        группа = self.current_group()
        if группа is None:
            self.summary_label.setText("Нет учебного плана")
            return

        data = self.data
        self.blocks = lb.build_blocks(data, группа)
        всего = lb.loads_after(data, [], [])
        ид_классов = {к["ид"] for к in группа["классы"]}

        в_группе = {у: 0 for у in группа["учителя"]}
        for (класс_ид, п), (у, часов) in data["назначения"].items():
            if класс_ид in ид_классов and п in группа["предметы"] and у in в_группе:
                в_группе[у] += часов or 0

        план = sum(б["часов"] for б in self.blocks)
        не_назначено = sum(б["часов"] for б in self.blocks if б["текущий"] is None)
        итог = f"По плану: {план} ч. · Учителей: {len(группа['учителя'])}"
        if группа["учителя"]:
            итог += f" · в среднем по {план / len(группа['учителя']):.1f} ч."
        else:
            итог += " — нет ни одного учителя этих предметов, работающего в этой ступени"
        if не_назначено:
            итог += f"\nНе распределено: {не_назначено} ч. — нажмите «Распределить группу»"
        self.summary_label.setText(итог)

        for i, блок in enumerate(self.blocks):
            r = self.classes_table.rowCount()
            self.classes_table.insertRow(r)
            self.classes_table.setItem(r, 0, _ячейка(блок["класс"]["название"], по_центру=True))
            self.classes_table.setItem(r, 1, _ячейка(_предметы_блока(data, блок)))
            self.classes_table.setItem(r, 2, _ячейка(str(блок["часов"]), по_центру=True))
            self.classes_table.setCellWidget(r, 3, self._выбор_учителя(i, блок))

        for у in группа["учителя"]:
            r = self.teachers_table.rowCount()
            self.teachers_table.insertRow(r)
            значения = [data["учителя"][у]["фио"], _ступени_текст(data, у), str(в_группе[у]), str(всего.get(у, 0))]
            for c, значение in enumerate(значения):
                self.teachers_table.setItem(r, c, _ячейка(значение, по_центру=c > 0, жирный=c == 3))

        # Учителей в группе немного — таблица по высоте содержимого, остальное место классам
        высота = self.teachers_table.horizontalHeader().height() + 4
        высота += sum(self.teachers_table.rowHeight(r) for r in range(self.teachers_table.rowCount()))
        self.teachers_table.setFixedHeight(min(высота, 260))

    def _выбор_учителя(self, индекс_блока, блок):
        if not блок["подходящие"]:
            label = QLabel("  нет учителя, который ведёт эти предметы в этой ступени")
            label.setStyleSheet("color: #e74c3c;")
            return label

        combo = QComboBox()
        # Обычный стиль QComboBox слишком высокий для строки таблицы
        combo.setStyleSheet("QComboBox { padding: 2px 8px; min-width: 0; border-radius: 4px; }")
        текущий = блок["текущий"]
        if текущий is None or текущий == "разные":
            combo.addItem(_фио(self.data, текущий), None)
        elif текущий not in блок["подходящие"]:
            combo.addItem(f"{_фио(self.data, текущий)} (не подходит: другая ступень или предметы)", текущий)
        for у in блок["подходящие"]:
            combo.addItem(self.data["учителя"][у]["фио"], у)
        combo.setCurrentIndex(max(0, combo.findData(текущий)) if текущий not in (None, "разные") else 0)
        combo.currentIndexChanged.connect(
            lambda _i, c=combo, n=индекс_блока: self.change_teacher(n, c.currentData())
        )
        return combo

    # ---------- изменения ----------

    def change_teacher(self, индекс_блока, учитель_ид):
        if учитель_ид is None:
            return
        conn = get_connection()
        cursor = conn.cursor()
        lb.apply_assignment(cursor, self.data, self.blocks[индекс_блока], учитель_ид)
        conn.commit()
        conn.close()
        self.load_table()

    def propose(self):
        группа = self.current_group()
        if группа is None:
            return
        self._предложить([(группа, self.blocks, lb.propose(self.data, группа, self.blocks))])

    def propose_all(self):
        self._предложить(lb.propose_all(self.data))

    def _предложить(self, варианты):
        есть_изменения = any(
            у is not None and у != б["текущий"]
            for _, блоки, предложение in варианты for б, у in zip(блоки, предложение)
        )
        if not есть_изменения:
            QMessageBox.information(self, "Распределение", "Текущее распределение уже самое ровное.")
            return

        dialog = ProposalDialog(self.data, варианты, self)
        if dialog.exec() != QDialog.Accepted:
            return

        conn = get_connection()
        cursor = conn.cursor()
        for _, блоки, предложение in варианты:
            for блок, учитель_ид in zip(блоки, предложение):
                if учитель_ид is not None and учитель_ид != блок["текущий"]:
                    lb.apply_assignment(cursor, self.data, блок, учитель_ид)
        conn.commit()
        conn.close()
        self.load_table()
