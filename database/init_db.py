from database.connection import get_connection

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
            макс_часов INTEGER DEFAULT 18
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
    """)

    conn.commit()
    conn.close()