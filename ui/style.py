STYLE = """
    * {
        font-family: Segoe UI;
        font-size: 13px;
    }

    QMainWindow, QWidget {
        background-color: #f4f6f9;
        color: #2c3e50;
    }

    /* Боковое меню */
    #sidebar {
        background-color: #1e2a3a;
        border-right: none;
    }

    #sidebar_title {
        color: #ffffff;
        font-size: 16px;
        font-weight: bold;
        padding: 20px 16px 10px 16px;
        background-color: #1e2a3a;
    }

    #sidebar_subtitle {
        color: #7f8c8d;
        font-size: 11px;
        padding: 0px 16px 20px 16px;
        background-color: #1e2a3a;
    }

    #nav_btn {
        background-color: transparent;
        color: #bdc3c7;
        border: none;
        border-radius: 8px;
        padding: 12px 16px;
        text-align: left;
        font-size: 13px;
        margin: 2px 8px;
    }

    #nav_btn:hover {
        background-color: #2c3e50;
        color: #ffffff;
    }

    #nav_btn_active {
        background-color: #2979b8;
        color: #ffffff;
        border: none;
        border-radius: 8px;
        padding: 12px 16px;
        text-align: left;
        font-size: 13px;
        font-weight: bold;
        margin: 2px 8px;
    }

    /* Основная область */
    #content_area {
        background-color: #f4f6f9;
    }

    #page_title {
        color: #1e2a3a;
        font-size: 22px;
        font-weight: bold;
        padding: 8px 0px;
    }

    /* Карточка */
    #card {
        background-color: #ffffff;
        border-radius: 12px;
        border: 1px solid #e8ecf0;
    }

    /* Таблицы */
    QTableWidget {
        background-color: #ffffff;
        border: 1px solid #e8ecf0;
        border-radius: 8px;
        gridline-color: #f0f3f6;
        outline: none;
    }

    QTableWidget::item {
        padding: 6px 8px 10px 8px;
        border-bottom: 1px solid #f0f3f6;
    }

    QTableWidget::item:selected {
        background-color: #e8f0fe;
        color: #1e2a3a;
    }

    QHeaderView::section {
        background-color: #f8f9fb;
        color: #7f8c8d;
        padding: 10px 8px;
        border: none;
        border-bottom: 2px solid #e8ecf0;
        font-weight: bold;
        font-size: 12px;
    }

    /* Поля ввода */
    QLineEdit {
        background-color: #ffffff;
        border: 1.5px solid #e8ecf0;
        border-radius: 8px;
        padding: 8px 12px;
        color: #2c3e50;
        font-size: 13px;
    }

    QLineEdit:focus {
        border: 1.5px solid #2979b8;
    }

    QComboBox {
        background-color: #ffffff;
        border: 1.5px solid #e8ecf0;
        border-radius: 8px;
        padding: 8px 12px;
        color: #2c3e50;
        font-size: 13px;
        min-width: 150px;
    }

    QComboBox:focus {
        border: 1.5px solid #2979b8;
    }

    QComboBox::drop-down {
        border: none;
        width: 20px;
    }

    QComboBox QAbstractItemView {
        background-color: #ffffff;
        border: 1px solid #e8ecf0;
        border-radius: 8px;
        selection-background-color: #e8f0fe;
        selection-color: #2c3e50;
    }

    QSpinBox {
        background-color: #ffffff;
        border: 1.5px solid #e8ecf0;
        border-radius: 8px;
        padding: 8px 12px;
        color: #2c3e50;
        font-size: 13px;
    }

    QSpinBox:focus {
        border: 1.5px solid #2979b8;
    }

    /* Кнопки */
    QPushButton {
        background-color: #2979b8;
        color: #ffffff;
        border: none;
        border-radius: 8px;
        padding: 9px 18px;
        font-weight: bold;
        font-size: 13px;
    }

    QPushButton:hover {
        background-color: #1a5f9a;
    }

    QPushButton:pressed {
        background-color: #0d4a7a;
    }

    /* Вторичные кнопки */
    #btn_secondary {
        background-color: #f0f3f6;
        color: #2c3e50;
        border: 1px solid #e8ecf0;
        border-radius: 8px;
        padding: 9px 18px;
        font-weight: bold;
    }

    #btn_secondary:hover {
        background-color: #e8ecf0;
    }

    /* Кнопка удалить */
    #btn_danger {
        background-color: #fff0f0;
        color: #e74c3c;
        border: 1px solid #ffd5d5;
        border-radius: 8px;
        padding: 9px 18px;
        font-weight: bold;
    }

    #btn_danger:hover {
        background-color: #ffe0e0;
    }

    /* Вкладки внутри страниц */
    QTabWidget::pane {
        border: 1px solid #e8ecf0;
        border-radius: 8px;
        background-color: #ffffff;
        top: -1px;
    }

    QTabBar::tab {
        background-color: #f4f6f9;
        color: #7f8c8d;
        padding: 10px 20px;
        margin-right: 4px;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        border: 1px solid #e8ecf0;
        font-weight: bold;
    }

    QTabBar::tab:selected {
        background-color: #ffffff;
        color: #2979b8;
        border-bottom: 2px solid #2979b8;
    }

    QTabBar::tab:hover {
        background-color: #e8f0fe;
        color: #2979b8;
    }

    QLabel {
        color: #2c3e50;
        background-color: transparent;
    }

    QMessageBox {
        background-color: #f4f6f9;
    }

    QMessageBox QPushButton {
        min-width: 80px;
    }

    QDialog {
        background-color: #f4f6f9;
    }

    /* Большая кнопка составить расписание */
    #generate_btn {
        background-color: #2979b8;
        color: #ffffff;
        border: none;
        border-radius: 0px;
        padding: 14px;
        font-size: 15px;
        font-weight: bold;
    }

    #generate_btn:hover {
        background-color: #1a5f9a;
    }

    #generate_btn:pressed {
        background-color: #0d4a7a;
    }
"""