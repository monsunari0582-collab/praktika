from database.connection import get_connection

def compress_schedule(conn):
    cursor = conn.cursor()

    cursor.execute("SELECT ид FROM КЛАСС")
    классы = [row["ид"] for row in cursor.fetchall()]

    for класс_ид in классы:
        for день in range(1, 7):
            cursor.execute("""
                SELECT ид, номер_урока FROM УРОК
                WHERE класс_ид = ? AND день_недели = ?
                ORDER BY номер_урока
            """, (класс_ид, день))
            уроки = cursor.fetchall()

            for новый_номер, урок in enumerate(уроки, start=1):
                if урок["номер_урока"] != новый_номер:
                    cursor.execute("""
                        UPDATE УРОК SET номер_урока = ?
                        WHERE ид = ?
                    """, (новый_номер, урок["ид"]))

    conn.commit()


def generate_schedule():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM УРОК")
    conn.commit()

    cursor.execute("SELECT ид, параллель, буква FROM КЛАСС")
    классы = cursor.fetchall()

    cursor.execute("SELECT учитель_ид, предмет_ид FROM УЧИТЕЛЬ_ПРЕДМЕТ")
    учитель_предмет = cursor.fetchall()

    предмет_учителя = {}
    for row in учитель_предмет:
        пид = row["предмет_ид"]
        уид = row["учитель_ид"]
        if пид not in предмет_учителя:
            предмет_учителя[пид] = []
        предмет_учителя[пид].append(уид)

    cursor.execute("SELECT ид, макс_часов FROM УЧИТЕЛЬ")
    макс_часов_учителя = {row["ид"]: row["макс_часов"] for row in cursor.fetchall()}

    cursor.execute("""
        SELECT ид_сущности, значение
        FROM ОГРАНИЧЕНИЕ
        WHERE тип_сущности = 'учитель'
        AND тип_правила = 'нерабочий_день'
    """)
    нерабочие_дни = {}
    for row in cursor.fetchall():
        уид = row["ид_сущности"]
        день = int(row["значение"])
        if уид not in нерабочие_дни:
            нерабочие_дни[уид] = set()
        нерабочие_дни[уид].add(день)

    cursor.execute("SELECT учитель_ид, класс_ид FROM УЧИТЕЛЬ_КЛАСС")
    учитель_классы = {}
    for row in cursor.fetchall():
        уид = row["учитель_ид"]
        кид = row["класс_ид"]
        if уид not in учитель_классы:
            учитель_классы[уид] = set()
        учитель_классы[уид].add(кид)

    слоты = [(день, урок) for день in range(1, 7) for урок in range(1, 8)]

    занятые_учителя = {}
    занятые_классы = {}
    предмет_в_день = {}
    часов_учителя = {}

    уроки_добавлены = 0
    уроки_пропущены = 0

    for класс in классы:
        класс_ид = класс["ид"]

        cursor.execute("""
            SELECT предмет_ид, часов_в_неделю
            FROM УЧЕБНЫЙ_ПЛАН
            WHERE класс_ид = ?
        """, (класс_ид,))
        учебный_план = cursor.fetchall()

        for план in учебный_план:
            предмет_ид = план["предмет_ид"]
            часов = план["часов_в_неделю"]

            if предмет_ид not in предмет_учителя:
                уроки_пропущены += часов
                continue

            поставлено = 0

            for день, урок in слоты:
                if поставлено >= часов:
                    break

                if занятые_классы.get((класс_ид, день, урок)):
                    continue

                if предмет_в_день.get((класс_ид, предмет_ид, день)):
                    continue

                учитель_ид = None
                for уид in предмет_учителя[предмет_ид]:
                    if день in нерабочие_дни.get(уид, set()):
                        continue
                    if часов_учителя.get(уид, 0) >= макс_часов_учителя.get(уид, 18):
                        continue
                    if уид in учитель_классы and класс_ид not in учитель_классы[уид]:
                        continue
                    if уид not in занятые_учителя.get((день, урок), set()):
                        учитель_ид = уид
                        break

                if учитель_ид is None:
                    continue

                cursor.execute("""
                    INSERT INTO УРОК
                    (класс_ид, предмет_ид, учитель_ид, день_недели, номер_урока, статус)
                    VALUES (?, ?, ?, ?, ?, 'черновик')
                """, (класс_ид, предмет_ид, учитель_ид, день, урок))

                занятые_учителя.setdefault((день, урок), set()).add(учитель_ид)
                занятые_классы[(класс_ид, день, урок)] = True
                предмет_в_день[(класс_ид, предмет_ид, день)] = True
                часов_учителя[учитель_ид] = часов_учителя.get(учитель_ид, 0) + 1

                поставлено += 1
                уроки_добавлены += 1

    compress_schedule(conn)
    conn.close()

    return уроки_добавлены, уроки_пропущены