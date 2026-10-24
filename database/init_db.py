from database.connection import get_connection


def _ensure_column(cursor, table, column, decl):
    """Добавляет колонку в таблицу, если её ещё нет (для старых баз)."""
    cursor.execute(f"PRAGMA table_info({table})")
    существующие = [row[1] for row in cursor.fetchall()]
    if column not in существующие:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
        return True
    return False


# Ступени, в которых может работать учитель: колонка в УЧИТЕЛЬ -> диапазон параллелей
СТУПЕНИ_УЧИТЕЛЯ = {
    "работает_1_4": (1, 4),
    "работает_5_9": (5, 9),
    "работает_10_11": (10, 11),
}


def _заполнить_ступени(cursor, колонка, от, до):
    """Для старой базы: ступень отмечается, если у учителя был лимит на неё
    или уже есть назначения в классах этой ступени."""
    лимит = колонка.replace("работает_", "часов_")
    cursor.execute(f"""
        UPDATE УЧИТЕЛЬ SET {колонка} = 1
        WHERE COALESCE({лимит}, 0) > 0
           OR ид IN (
               SELECT УПК.учитель_ид FROM УЧИТЕЛЬ_ПРЕДМЕТ_КЛАСС УПК
               JOIN КЛАСС К ON К.ид = УПК.класс_ид
               WHERE CAST(К.параллель AS INTEGER) BETWEEN ? AND ?
           )
    """, (от, до))


def init_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS КЛАСС (
            ид        INTEGER PRIMARY KEY AUTOINCREMENT,
            параллель TEXT NOT NULL,
            буква     TEXT NOT NULL,
            UNIQUE(параллель, буква)
        );

        CREATE TABLE IF NOT EXISTS ПРЕДМЕТ (
            ид            INTEGER PRIMARY KEY AUTOINCREMENT,
            название      TEXT NOT NULL,
            код           TEXT UNIQUE,
            краткое_имя   TEXT
        );

        CREATE TABLE IF NOT EXISTS УЧИТЕЛЬ (
            ид         INTEGER PRIMARY KEY AUTOINCREMENT,
            фио        TEXT NOT NULL,
            макс_часов INTEGER DEFAULT 18,
            часов_1_4   INTEGER DEFAULT 0,
            часов_5_9   INTEGER DEFAULT 0,
            часов_10_11 INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS УЧИТЕЛЬ_ПРЕДМЕТ (
            учитель_ид   INTEGER,
            предмет_ид   INTEGER,
            PRIMARY KEY (учитель_ид, предмет_ид),
            FOREIGN KEY (учитель_ид) REFERENCES УЧИТЕЛЬ(ид),
            FOREIGN KEY (предмет_ид) REFERENCES ПРЕДМЕТ(ид)
        );

        CREATE TABLE IF NOT EXISTS УЧИТЕЛЬ_КЛАСС (
            учитель_ид  INTEGER,
            класс_ид    INTEGER,
            часов       INTEGER DEFAULT 0,
            PRIMARY KEY (учитель_ид, класс_ид), 
            FOREIGN KEY (учитель_ид) REFERENCES УЧИТЕЛЬ(ид),
            FOREIGN KEY (класс_ид)   REFERENCES КЛАСС(ид)
        );

        CREATE TABLE IF NOT EXISTS УЧЕБНЫЙ_ПЛАН (
            класс_ид       INTEGER,
            предмет_ид     INTEGER,
            часов_в_неделю INTEGER NOT NULL,
            PRIMARY KEY (класс_ид, предмет_ид),
            FOREIGN KEY (класс_ид)   REFERENCES КЛАСС(ид),
            FOREIGN KEY (предмет_ид) REFERENCES ПРЕДМЕТ(ид)
        );

        CREATE TABLE IF NOT EXISTS УРОК (
            ид           INTEGER PRIMARY KEY AUTOINCREMENT,
            класс_ид     INTEGER,
            предмет_ид   INTEGER,
            учитель_ид   INTEGER,
            день_недели  INTEGER NOT NULL,
            номер_урока  INTEGER NOT NULL,
            статус       TEXT DEFAULT 'черновик',
            FOREIGN KEY (класс_ид)   REFERENCES КЛАСС(ид),
            FOREIGN KEY (предмет_ид) REFERENCES ПРЕДМЕТ(ид),
            FOREIGN KEY (учитель_ид) REFERENCES УЧИТЕЛЬ(ид)
        );

        CREATE TABLE IF NOT EXISTS ОГРАНИЧЕНИЕ (
            ид           INTEGER PRIMARY KEY AUTOINCREMENT,
            тип_сущности TEXT NOT NULL,
            ид_сущности  INTEGER NOT NULL,
            тип_правила  TEXT NOT NULL,
            значение     TEXT
        );

        CREATE TABLE IF NOT EXISTS УЧИТЕЛЬ_ПРЕДМЕТ_КЛАСС (
            ид         INTEGER PRIMARY KEY AUTOINCREMENT,
            учитель_ид INTEGER NOT NULL,
            предмет_ид INTEGER NOT NULL,
            класс_ид   INTEGER NOT NULL,
            часов      INTEGER NOT NULL DEFAULT 0,
            UNIQUE(класс_ид, предмет_ид),
            FOREIGN KEY (учитель_ид) REFERENCES УЧИТЕЛЬ(ид),
            FOREIGN KEY (предмет_ид) REFERENCES ПРЕДМЕТ(ид),
            FOREIGN KEY (класс_ид)   REFERENCES КЛАСС(ид)
        );
    """)

    # Миграция старой базы: дописываем колонки тарифа и часов, если их ещё нет
    _ensure_column(cursor, "УЧИТЕЛЬ", "часов_1_4", "INTEGER DEFAULT 0")
    _ensure_column(cursor, "УЧИТЕЛЬ", "часов_5_9", "INTEGER DEFAULT 0")
    _ensure_column(cursor, "УЧИТЕЛЬ", "часов_10_11", "INTEGER DEFAULT 0")
    _ensure_column(cursor, "УЧИТЕЛЬ_КЛАСС", "часов", "INTEGER DEFAULT 0")
    for колонка, (от, до) in СТУПЕНИ_УЧИТЕЛЯ.items():
        if _ensure_column(cursor, "УЧИТЕЛЬ", колонка, "INTEGER DEFAULT 0"):
            _заполнить_ступени(cursor, колонка, от, до)

    # Автоматический перенос связей, если таблица назначений пустая
    cursor.execute("SELECT COUNT(*) FROM УЧИТЕЛЬ_ПРЕДМЕТ_КЛАСС")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT OR IGNORE INTO УЧИТЕЛЬ_ПРЕДМЕТ_КЛАСС (учитель_ид, предмет_ид, класс_ид, часов)
            SELECT УК.учитель_ид, УП.предмет_ид, УК.класс_ид, COALESCE(УПЛ.часов_в_неделю, УК.часов, 0)
            FROM УЧИТЕЛЬ_КЛАСС УК
            JOIN УЧИТЕЛЬ_ПРЕДМЕТ УП ON УК.учитель_ид = УП.учитель_ид
            JOIN УЧЕБНЫЙ_ПЛАН УПЛ ON УК.класс_ид = УПЛ.класс_ид AND УП.предмет_ид = УПЛ.предмет_ид
        """)

    conn.commit()
    conn.close()