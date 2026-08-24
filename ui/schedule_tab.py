from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem,
    QPushButton, QTabWidget, QMessageBox,
    QHeaderView, QFileDialog
)
from PySide6.QtCore import Qt
from database.connection import get_connection
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Side, Font, PatternFill
from openpyxl.utils import get_column_letter
import os


class ScheduleTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        top_layout = QHBoxLayout()

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_schedule)

        export_btn = QPushButton("Экспортировать в Excel")
        export_btn.clicked.connect(self.export_to_excel)

        clear_btn = QPushButton("Очистить расписание")
        clear_btn.clicked.connect(self.clear_schedule)

        top_layout.addWidget(refresh_btn)
        top_layout.addWidget(export_btn)
        top_layout.addWidget(clear_btn)
        top_layout.addStretch()

        self.class_tabs = QTabWidget()

        layout.addLayout(top_layout)
        layout.addWidget(self.class_tabs)

        self.setLayout(layout)
        self.load_schedule()

    def load_schedule(self):
        self.class_tabs.clear()

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ид, параллель, буква FROM КЛАСС ORDER BY CAST(параллель AS INTEGER), буква")
        классы = cursor.fetchall()
        conn.close()

        for класс in классы:
            класс_ид = класс["ид"]
            название = f"{класс['параллель']}{класс['буква']}"

            table = QTableWidget()
            table.setColumnCount(6)
            table.setHorizontalHeaderLabels([
                "Понедельник", "Вторник", "Среда",
                "Четверг", "Пятница", "Суббота"
            ])
            table.setRowCount(7)
            table.setVerticalHeaderLabels([
                "1 урок", "2 урок", "3 урок", "4 урок",
                "5 урок", "6 урок", "7 урок"
            ])
            table.horizontalHeader().setStretchLastSection(False)
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            table.setEditTriggers(QTableWidget.NoEditTriggers)

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT У.день_недели, У.номер_урока,
                       П.название AS предмет, УЧ.фио AS учитель
                FROM УРОК У
                JOIN ПРЕДМЕТ П ON У.предмет_ид = П.ид
                LEFT JOIN УЧИТЕЛЬ УЧ ON У.учитель_ид = УЧ.ид
                WHERE У.класс_ид = ?
                ORDER BY У.день_недели, У.номер_урока
            """, (класс_ид,))
            rows = cursor.fetchall()
            conn.close()

            for row in rows:
                день = row["день_недели"] - 1
                урок = row["номер_урока"] - 1

                if 0 <= день <= 5 and 0 <= урок <= 6:
                    учитель = row['учитель'] or ""
                    текст = f"{row['предмет']}\n{учитель}".strip()
                    item = QTableWidgetItem(текст)
                    item.setTextAlignment(Qt.AlignCenter)
                    table.setItem(урок, день, item)

            table.verticalHeader().setDefaultSectionSize(75)
            self.class_tabs.addTab(table, название)

    def clear_schedule(self):
        ответ = QMessageBox.question(
            self, "Подтверждение",
            "Вы уверены что хотите очистить расписание?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ответ == QMessageBox.Yes:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM УРОК")
            conn.commit()
            conn.close()

            self.load_schedule()
            QMessageBox.information(self, "Готово", "Расписание очищено")

    def export_to_excel(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить расписание", "", "Excel файлы (*.xlsx)"
        )
        if not file_path:
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Загружаем классы
            cursor.execute("SELECT ид, параллель, буква FROM КЛАСС ORDER BY CAST(параллель AS INTEGER), буква")
            классы = cursor.fetchall()

            # Создаём workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "Расписание"

            дни_названия = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]
            
            # Блок утверждения - ДИНАМИЧЕСКИ справа от таблицы
            утверждение_col = len(классы) + 4  # +4 = 2 для дня/урока + 2 отступа
            
            # "Утверждаю" в строке 1
            ws.cell(1, утверждение_col, "Утверждаю")
            ws.cell(1, утверждение_col).font = Font(italic=True, size=10)

            # Заголовок расписания в строке 2
            ws['B2'] = "Расписание уроков на 2025-2026 учебный год"
            ws['B2'].font = Font(bold=True, size=12)
            ws['B2'].alignment = Alignment(horizontal="center", vertical="center")

            # "Директор школы:" и подпись в строке 2
            ws.cell(2, утверждение_col, "Директор школы:")
            ws.cell(2, утверждение_col).font = Font(size=9)
            ws.cell(2, утверждение_col + 1, "Куулар А.Т")
            ws.cell(2, утверждение_col + 1).font = Font(size=9)

            # Заголовки в строке 3
            ws['A3'] = "День"
            ws['B3'] = "Урок"
            for col, класс in enumerate(классы, start=3):
                ws.cell(3, col, класс['параллель'])

            # Стиль заголовков
            header_fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
            header_font = Font(bold=True, size=10)
            
            for col in range(1, len(классы) + 3):
                cell = ws.cell(3, col)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")
            
            ws.row_dimensions[3].height = 18

            current_row = 4

            # Для каждого дня недели
            for номер_дня, день_название in enumerate(дни_названия, start=1):
                # Для каждого урока (1-7)
                for номер_урока in range(1, 8):
                    # День недели (только для первого урока)
                    if номер_урока == 1:
                        ws.cell(current_row, 1, день_название)
                        ws.cell(current_row, 1).font = Font(bold=True, size=10)
                    
                    ws.cell(current_row, 1).alignment = Alignment(horizontal="center", vertical="center")

                    # Номер урока
                    ws.cell(current_row, 2, номер_урока)
                    ws.cell(current_row, 2).font = Font(bold=True, size=10)
                    ws.cell(current_row, 2).alignment = Alignment(horizontal="center", vertical="center")

                    # Для каждого класса
                    for col, класс in enumerate(классы, start=3):
                        класс_ид = класс["ид"]

                        # Загружаем предмет
                        cursor.execute("""
                            SELECT П.название AS предмет
                            FROM УРОК У
                            JOIN ПРЕДМЕТ П ON У.предмет_ид = П.ид
                            WHERE У.класс_ид = ? AND У.день_недели = ? AND У.номер_урока = ?
                            LIMIT 1
                        """, (класс_ид, номер_дня, номер_урока))
                        урок = cursor.fetchone()

                        предмет = урок["предмет"] if урок else ""
                        
                        cell = ws.cell(current_row, col, предмет)
                        cell.alignment = Alignment(horizontal="center", vertical="center")
                        cell.font = Font(size=10)

                    ws.row_dimensions[current_row].height = 18
                    current_row += 1

            # Установка ширины колонок - как в примере
            ws.column_dimensions['A'].width = 14  # День
            ws.column_dimensions['B'].width = 5   # Урок
            for col in range(3, len(классы) + 3):
                col_letter = get_column_letter(col)
                ws.column_dimensions[col_letter].width = 14  # Классы

            # Ширина для блока утверждения
            ws.column_dimensions[get_column_letter(утверждение_col)].width = 18
            ws.column_dimensions[get_column_letter(утверждение_col + 1)].width = 15

            # Печать
            ws.print_options.horizontalCentered = True
            ws.page_setup.paperSize = ws.PAPERSIZE_A4
            ws.page_setup.orientation = 'landscape'

            wb.save(file_path)
            QMessageBox.information(self, "Готово", f"Расписание сохранено в:\n{file_path}")
            conn.close()

        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка при экспорте:\n{str(e)}")