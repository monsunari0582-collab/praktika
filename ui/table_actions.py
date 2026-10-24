from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QTableWidget
)
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import Qt


def selected_rows(table):
    """Номера выбранных строк без скрытых фильтром (Ctrl+A выделяет и их)."""
    if table is None:
        return []
    return sorted({
        item.row() for item in table.selectedItems()
        if not table.isRowHidden(item.row())
    })


class ActionBar(QWidget):
    """Панель над таблицей: счётчик выбранных строк, действия и «Удалить».

    Выбор строк — как в обычных программах: клик, Ctrl/Shift+клик, Ctrl+A.
    Двойной клик по строке вызывает редактирование, клавиша Delete — удаление.

    get_table — функция, возвращающая текущую таблицу (у учебного плана
    таблиц несколько, по одной на класс). Каждую таблицу нужно передать в attach().
    actions — список (текст, обработчик) для кнопок, которым нужна ровно одна строка;
    первая из них вызывается двойным кликом.
    """

    def __init__(self, get_table, on_delete, actions=()):
        super().__init__()
        self.get_table = get_table
        self.on_delete = on_delete
        self.actions = list(actions)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 4, 0, 4)

        self.count_label = QLabel()
        self.count_label.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(self.count_label)
        layout.addStretch()

        self.action_buttons = []
        for текст, обработчик in self.actions:
            btn = QPushButton(текст)
            btn.setObjectName("btn_secondary")
            btn.clicked.connect(обработчик)
            layout.addWidget(btn)
            self.action_buttons.append(btn)

        if self.action_buttons:
            layout.addSpacing(16)

        self.delete_btn = QPushButton("Удалить")
        self.delete_btn.setObjectName("btn_danger")
        self.delete_btn.clicked.connect(on_delete)
        layout.addWidget(self.delete_btn)

        self.setLayout(layout)
        self.update_state()

    def attach(self, table):
        table.setSelectionMode(QTableWidget.ExtendedSelection)
        table.itemSelectionChanged.connect(self.update_state)
        if self.actions:
            table.doubleClicked.connect(lambda _index: self.actions[0][1]())
        shortcut = QShortcut(QKeySequence(Qt.Key_Delete), table)
        shortcut.setContext(Qt.WidgetShortcut)
        shortcut.activated.connect(self.on_delete)

    def update_state(self):
        n = len(selected_rows(self.get_table()))
        if n == 0:
            подсказка = "Ничего не выбрано · Ctrl+A — выбрать все, Delete — удалить"
            if self.actions:
                подсказка += ", двойной клик — изменить"
            self.count_label.setText(подсказка)
        else:
            self.count_label.setText(f"Выбрано: {n}")
        for btn in self.action_buttons:
            btn.setEnabled(n == 1)
        self.delete_btn.setEnabled(n > 0)
        self.delete_btn.setText("Удалить" if n <= 1 else f"Удалить ({n})")
