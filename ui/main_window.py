from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QMessageBox,
    QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from ui.classes_tab import ClassesTab
from ui.subjects_tab import SubjectsTab
from ui.curriculum_tab import CurriculumTab
from ui.teachers_tab import TeachersTab
from ui.teacher_subject_tab import TeacherSubjectTab
from ui.teacher_class_tab import TeacherClassTab
from ui.constraints_tab import ConstraintsTab
from ui.schedule_tab import ScheduleTab
from algorithm.scheduler import generate_schedule


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Расписание школы")
        self.setMinimumSize(1300, 800)
        self.setWindowIcon(QIcon("icon.ico"))

        central = QWidget()
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        central.setLayout(main_layout)
        self.setCentralWidget(central)

        # Боковое меню
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        sidebar.setLayout(sidebar_layout)

        title = QLabel("Расписание")
        title.setObjectName("sidebar_title")
        subtitle = QLabel("школы")
        subtitle.setObjectName("sidebar_subtitle")

        sidebar_layout.addWidget(title)
        sidebar_layout.addWidget(subtitle)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #2c3e50; margin: 0 16px;")
        sidebar_layout.addWidget(line)
        sidebar_layout.addSpacing(8)

        self.nav_buttons = []
        nav_items = [
            ("Классы", 0),
            ("Учителя", 1),
            ("Ограничения", 2),
            ("Расписание", 3),
        ]

        for text, index in nav_items:
            btn = QPushButton(text)
            btn.setObjectName("nav_btn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, i=index: self.switch_page(i))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        sidebar_layout.addStretch()

        generate_btn = QPushButton("Составить расписание")
        generate_btn.setObjectName("generate_btn")
        generate_btn.setFixedHeight(56)
        generate_btn.setCursor(Qt.PointingHandCursor)
        generate_btn.clicked.connect(self.generate)
        sidebar_layout.addWidget(generate_btn)

        # Правая часть
        right_widget = QWidget()
        right_widget.setObjectName("content_area")
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_widget.setLayout(right_layout)

        self.stack = QStackedWidget()

        # Страница Классы
        classes_page = QWidget()
        classes_page_layout = QVBoxLayout()
        classes_page_layout.setContentsMargins(24, 20, 24, 20)
        classes_title = QLabel("Классы")
        classes_title.setObjectName("page_title")
        classes_page_layout.addWidget(classes_title)
        classes_inner = QTabWidget()
        self.classes_tab = ClassesTab()
        self.subjects_tab = SubjectsTab()
        self.curriculum_tab = CurriculumTab()
        classes_inner.addTab(self.classes_tab, "Классы")
        classes_inner.addTab(self.subjects_tab, "Предметы")
        classes_inner.addTab(self.curriculum_tab, "Учебный план")
        classes_inner.currentChanged.connect(self.on_classes_inner_changed)
        classes_page_layout.addWidget(classes_inner)
        classes_page.setLayout(classes_page_layout)

        # Страница Учителя
        teachers_page = QWidget()
        teachers_page_layout = QVBoxLayout()
        teachers_page_layout.setContentsMargins(24, 20, 24, 20)
        teachers_title = QLabel("Учителя")
        teachers_title.setObjectName("page_title")
        teachers_page_layout.addWidget(teachers_title)
        teachers_inner = QTabWidget()
        self.teachers_tab = TeachersTab()
        self.teacher_subject_tab = TeacherSubjectTab()
        self.teacher_class_tab = TeacherClassTab()
        teachers_inner.addTab(self.teachers_tab, "Учителя")
        teachers_inner.addTab(self.teacher_subject_tab, "Предметы учителя")
        teachers_inner.addTab(self.teacher_class_tab, "Классы учителя")
        teachers_inner.currentChanged.connect(self.on_teachers_inner_changed)
        teachers_page_layout.addWidget(teachers_inner)
        teachers_page.setLayout(teachers_page_layout)

        # Страница Ограничения
        constraints_page = QWidget()
        constraints_page_layout = QVBoxLayout()
        constraints_page_layout.setContentsMargins(24, 20, 24, 20)
        constraints_title = QLabel("Ограничения")
        constraints_title.setObjectName("page_title")
        constraints_page_layout.addWidget(constraints_title)
        self.constraints_tab = ConstraintsTab()
        constraints_page_layout.addWidget(self.constraints_tab)
        constraints_page.setLayout(constraints_page_layout)

        # Страница Расписание
        schedule_page = QWidget()
        schedule_page_layout = QVBoxLayout()
        schedule_page_layout.setContentsMargins(24, 20, 24, 20)
        schedule_title = QLabel("Расписание")
        schedule_title.setObjectName("page_title")
        schedule_page_layout.addWidget(schedule_title)
        self.schedule_tab = ScheduleTab()
        schedule_page_layout.addWidget(self.schedule_tab)
        schedule_page.setLayout(schedule_page_layout)

        self.stack.addWidget(classes_page)
        self.stack.addWidget(teachers_page)
        self.stack.addWidget(constraints_page)
        self.stack.addWidget(schedule_page)

        right_layout.addWidget(self.stack)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(right_widget)

        self.switch_page(0)

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            if i == index:
                btn.setObjectName("nav_btn_active")
            else:
                btn.setObjectName("nav_btn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if index == 2:
            self.constraints_tab.load_teachers_combo()
            self.constraints_tab.load_table()
        elif index == 3:
            self.schedule_tab.load_schedule()

    def on_classes_inner_changed(self, index):
        tabs = [self.classes_tab, self.subjects_tab, self.curriculum_tab]
        current = tabs[index]
        if hasattr(current, 'load_classes'):
            current.load_classes()
        if hasattr(current, 'load_subjects'):
            current.load_subjects()
        if hasattr(current, 'load_combos'):
            current.load_combos()
        if hasattr(current, 'load_table'):
            current.load_table()

    def on_teachers_inner_changed(self, index):
        tabs = [self.teachers_tab, self.teacher_subject_tab, self.teacher_class_tab]
        current = tabs[index]
        if hasattr(current, 'load_teachers'):
            current.load_teachers()
        if hasattr(current, 'load_combos'):
            current.load_combos()
        if hasattr(current, 'load_table'):
            current.load_table()

    def generate(self):
        добавлено, пропущено, пропущенные_список = generate_schedule()
        self.schedule_tab.load_schedule()
        self.switch_page(3)
        текст = f"Расписание составлено!\nУроков добавлено: {добавлено}\nНе удалось поставить: {пропущено}"
        if пропущенные_список:
            текст += "\n\nПропущенные уроки:\n" + "\n".join(пропущенные_список)
        QMessageBox.information(self, "Готово", текст)