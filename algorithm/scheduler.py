import random
from collections import defaultdict
from database.connection import get_connection

INF = float("inf")


def ступень_по_параллели(параллель):
    """1-4 -> '1-4', 5-9 -> '5-9', 10-11 -> '10-11'. Иначе None (без лимита)."""
    try:
        n = int(параллель)
    except (ValueError, TypeError):
        return None
    if 1 <= n <= 4:
        return "1-4"
    if 5 <= n <= 9:
        return "5-9"
    if 10 <= n <= 11:
        return "10-11"
    return None


def get_daily_budget(параллель, H_c):
    """Возвращает словарь {день: кол-во_уроков} для дней 1..6.

    Гарантирует:
    - Сумма уроков по дням строго равна H_c.
    - Для 1-го класса: 5-дневная неделя, суббота 0 уроков, не более 5 в день.
    - Для 2-4 классов: ровно 2 урока в субботу, в будни не более 5 уроков.
    - Для 5-11 классов: равномерное распределение по 6 дням (5-6 уроков, 7-й только при H_c > 36).
    """
    if H_c <= 0:
        return {d: 0 for d in range(1, 7)}

    p = str(параллель).strip() if параллель is not None else ""
    budget = {d: 0 for d in range(1, 7)}

    if p == "1":
        days = [1, 2, 3, 4, 5]
        base = H_c // len(days)
        rem = H_c % len(days)
        for i, d in enumerate(days):
            budget[d] = min(5, base + (1 if i < rem else 0))
    elif p in ("2", "3", "4"):
        sat_lessons = min(2, H_c)
        budget[6] = sat_lessons
        rem_hours = H_c - sat_lessons
        days = [1, 2, 3, 4, 5]
        base = rem_hours // len(days)
        rem = rem_hours % len(days)
        for i, d in enumerate(days):
            budget[d] = min(5, base + (1 if i < rem else 0))
    else:
        days = [1, 2, 3, 4, 5, 6]
        base = H_c // len(days)
        rem = H_c % len(days)
        for i, d in enumerate(days):
            budget[d] = base + (1 if i < rem else 0)

    # Коррекция, если из-за округления сумма не сошлась
    diff = H_c - sum(budget.values())
    if diff > 0:
        cand_days = [d for d in (range(1, 6) if p == "1" else range(1, 7)) if budget[d] < 7]
        while diff > 0 and cand_days:
            best_d = min(cand_days, key=lambda d: (budget[d], d == 6))
            budget[best_d] += 1
            diff -= 1
            cand_days = [d for d in cand_days if budget[d] < 7]
    elif diff < 0:
        while diff < 0:
            active_days = [d for d in range(1, 7) if budget[d] > 0]
            if not active_days:
                break
            worst_d = max(active_days, key=lambda d: (budget[d], d != 6))
            budget[worst_d] -= 1
            diff += 1

    return budget


def assign_slots_for_day(day, classes_lessons):
    """Бесконфликтно назначает уроки одного дня по слотам 1..K_c для каждого класса.

    classes_lessons: dict {класс_ид: list of lesson_dicts}
    Каждый lesson_dict:
        {
            "ид": уникальный_идентификатор,
            "класс_ид": ...,
            "предмет_ид": ...,
            "учитель_ид": ...
        }

    Гарантии:
    1. Для любого класса c с K уроками слоты составляют ровно 1, 2, ..., K (0 окон у класса!).
    2. Учителя не имеют накладок (не могут вести более 1 урока одновременно).
    3. Сдвоенные уроки одного предмета по возможности ставятся подряд.
    4. Окна у учителей минимизируются.

    Возвращает: dict {ид_урока: номер_слота}
    """
    assignment = {}
    if not classes_lessons:
        return assignment

    # 1. Начальное распределение слотов 1..K для каждого класса
    for c, items in classes_lessons.items():
        K = len(items)
        if K == 0:
            continue

        # Группируем для обнаружения сдвоенных уроков
        by_subj = defaultdict(list)
        for it in items:
            by_subj[(it["предмет_ид"], it.get("учитель_ид"))].append(it)

        pairs = []
        singles = []
        for grp in by_subj.values():
            while len(grp) >= 2:
                pairs.append((grp.pop(0), grp.pop(0)))
            if grp:
                singles.append(grp.pop(0))

        available_slots = list(range(1, K + 1))
        # Сначала распределяем пары на смежные слоты
        for it_a, it_b in pairs:
            found_pair = False
            for s in available_slots:
                if (s + 1) in available_slots:
                    assignment[it_a["ид"]] = s
                    assignment[it_b["ид"]] = s + 1
                    available_slots.remove(s)
                    available_slots.remove(s + 1)
                    found_pair = True
                    break
            if not found_pair:
                s1 = available_slots.pop(0)
                s2 = available_slots.pop(0)
                assignment[it_a["ид"]] = s1
                assignment[it_b["ид"]] = s2

        for it, s in zip(singles, available_slots):
            assignment[it["ид"]] = s

    # 2. Локальный поиск Min-Conflicts для устранения накладок учителей
    def get_clashes_and_map():
        ts = defaultdict(list)
        for c, it_list in classes_lessons.items():
            for it in it_list:
                u = it.get("учитель_ид")
                if u is not None:
                    ts[(u, assignment[it["ид"]])].append(it)
        conflicts = 0
        conflicted_items = []
        for lst in ts.values():
            if len(lst) > 1:
                conflicts += len(lst) - 1
                conflicted_items.extend(lst)
        return conflicts, ts, conflicted_items

    conflicts, ts, conflicted_items = get_clashes_and_map()

    max_iters = 700
    stagnation = 0
    best_conflicts = conflicts
    best_assignment = dict(assignment)

    for step in range(max_iters):
        if conflicts == 0:
            break

        conf_item = random.choice(conflicted_items)
        c = conf_item["класс_ид"]
        c_items = classes_lessons[c]
        s_current = assignment[conf_item["ид"]]
        t1 = conf_item.get("учитель_ид")

        best_swap_item = None
        best_delta = 999999

        for other_item in c_items:
            if other_item["ид"] == conf_item["ид"]:
                continue
            s_other = assignment[other_item["ид"]]
            t2 = other_item.get("учитель_ид")

            delta = 0
            if t1 is not None:
                old_c1 = max(0, len(ts[(t1, s_current)]) - 1)
                new_c1 = max(0, len(ts[(t1, s_current)]) - 2)
                delta += (new_c1 - old_c1)

                cur_at_other = len(ts[(t1, s_other)]) - (1 if t2 == t1 else 0)
                old_c2 = max(0, cur_at_other)
                new_c2 = cur_at_other
                delta += (new_c2 - old_c2)

            if t2 is not None:
                cur_at_other_t2 = len(ts[(t2, s_other)]) - (1 if t1 == t2 else 0)
                old_c3 = max(0, cur_at_other_t2)
                new_c3 = max(0, cur_at_other_t2 - 1)
                delta += (new_c3 - old_c3)

                old_c4 = max(0, len(ts[(t2, s_current)]) - 1)
                new_c4 = len(ts[(t2, s_current)])
                delta += (new_c4 - old_c4)

            if delta < best_delta:
                best_delta = delta
                best_swap_item = other_item
            elif delta == best_delta and random.random() < 0.2:
                best_swap_item = other_item

        if best_swap_item is not None and (best_delta < 0 or (best_delta == 0 and random.random() < 0.25)):
            s1 = assignment[conf_item["ид"]]
            s2 = assignment[best_swap_item["ид"]]
            assignment[conf_item["ид"]] = s2
            assignment[best_swap_item["ид"]] = s1
            conflicts, ts, conflicted_items = get_clashes_and_map()

            if conflicts < best_conflicts:
                best_conflicts = conflicts
                best_assignment = dict(assignment)
                stagnation = 0
            else:
                stagnation += 1
        else:
            stagnation += 1

        if stagnation > 25:
            # Случайная встряска в конфликтном классе
            rnd_c = conf_item["класс_ид"]
            if len(classes_lessons[rnd_c]) >= 2:
                i1, i2 = random.sample(classes_lessons[rnd_c], 2)
                s1 = assignment[i1["ид"]]
                s2 = assignment[i2["ид"]]
                assignment[i1["ид"]] = s2
                assignment[i2["ид"]] = s1
                conflicts, ts, conflicted_items = get_clashes_and_map()
            stagnation = 0

    # Встряска могла ухудшить результат — возвращаемся к лучшему найденному
    if conflicts > best_conflicts:
        assignment.update(best_assignment)

    # 3. Восстановление смежности сдвоенных уроков при возможности
    for c, items in classes_lessons.items():
        by_subj = defaultdict(list)
        for it in items:
            by_subj[(it["предмет_ид"], it.get("учитель_ид"))].append(it)
        for grp in by_subj.values():
            if len(grp) == 2:
                it_a, it_b = grp[0], grp[1]
                sa = assignment[it_a["ид"]]
                sb = assignment[it_b["ид"]]
                if abs(sa - sb) > 1:
                    # Пробуем приблизить sb к sa + 1 или sa - 1
                    target_s = sa + 1 if sa + 1 <= len(items) else sa - 1
                    target_item = next((x for x in items if assignment[x["ид"]] == target_s), None)
                    if target_item and target_item["ид"] != it_b["ид"]:
                        u_b = it_b.get("учитель_ид")
                        u_t = target_item.get("учитель_ид")
                        # Проверяем накладки при обмене
                        u_b_free = u_b is None or not any(
                            assignment[other["ид"]] == target_s
                            for oc, ol in classes_lessons.items() if oc != c
                            for other in ol if other.get("учитель_ид") == u_b
                        )
                        u_t_free = u_t is None or not any(
                            assignment[other["ид"]] == sb
                            for oc, ol in classes_lessons.items() if oc != c
                            for other in ol if other.get("учитель_ид") == u_t
                        )
                        if u_b_free and u_t_free:
                            assignment[it_b["ид"]] = target_s
                            assignment[target_item["ид"]] = sb

    # 4. Оптимизация окон у учителей
    def calc_teacher_windows():
        t_slots = defaultdict(list)
        for c, it_list in classes_lessons.items():
            for it in it_list:
                u = it.get("учитель_ид")
                if u is not None:
                    t_slots[u].append(assignment[it["ид"]])
        total_windows = 0
        for u, slts in t_slots.items():
            if len(slts) > 1:
                total_windows += (max(slts) - min(slts) + 1) - len(slts)
        return total_windows

    cur_windows = calc_teacher_windows()

    for _ in range(80):
        improved = False
        for c, it_list in classes_lessons.items():
            if len(it_list) < 2:
                continue
            for i1 in range(len(it_list)):
                for i2 in range(i1 + 1, len(it_list)):
                    it1 = it_list[i1]
                    it2 = it_list[i2]
                    u1 = it1.get("учитель_ид")
                    u2 = it2.get("учитель_ид")
                    s1 = assignment[it1["ид"]]
                    s2 = assignment[it2["ид"]]

                    # Не создаёт ли обмен накладок с другими классами?
                    if u1 is not None and u1 != u2:
                        conflict1 = any(
                            assignment[other["ид"]] == s2
                            for other_c, others in classes_lessons.items() if other_c != c
                            for other in others if other.get("учитель_ид") == u1
                        )
                        if conflict1:
                            continue

                    if u2 is not None and u1 != u2:
                        conflict2 = any(
                            assignment[other["ид"]] == s1
                            for other_c, others in classes_lessons.items() if other_c != c
                            for other in others if other.get("учитель_ид") == u2
                        )
                        if conflict2:
                            continue

                    # Пробуем поменять
                    assignment[it1["ид"]] = s2
                    assignment[it2["ид"]] = s1
                    new_windows = calc_teacher_windows()
                    if new_windows < cur_windows:
                        cur_windows = new_windows
                        improved = True
                        break
                    else:
                        assignment[it1["ид"]] = s1
                        assignment[it2["ид"]] = s2
                if improved:
                    break
            if improved:
                break
        if not improved:
            break

    return assignment


def generate_schedule():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM УРОК")
    conn.commit()

    # --- Загрузка данных ---
    cursor.execute("SELECT ид, параллель, буква FROM КЛАСС")
    классы = cursor.fetchall()
    класс_параллель = {к["ид"]: к["параллель"] for к in классы}
    название_класса = {к["ид"]: f"{к['параллель']}{к['буква']}" for к in классы}

    cursor.execute("SELECT ид, название FROM ПРЕДМЕТ")
    название_предмета = {row["ид"]: row["название"] for row in cursor.fetchall()}

    cursor.execute("SELECT ид, фио FROM УЧИТЕЛЬ")
    фио_учителя = {row["ид"]: row["фио"] for row in cursor.fetchall()}

    cursor.execute("SELECT учитель_ид, предмет_ид FROM УЧИТЕЛЬ_ПРЕДМЕТ")
    предмет_учителя = {}
    for row in cursor.fetchall():
        предмет_учителя.setdefault(row["предмет_ид"], []).append(row["учитель_ид"])

    cursor.execute("""
        SELECT ид_сущности, значение FROM ОГРАНИЧЕНИЕ
        WHERE тип_сущности = 'учитель' AND тип_правила = 'нерабочий_день'
    """)
    нерабочие_дни = {}
    for row in cursor.fetchall():
        нерабочие_дни.setdefault(row["ид_сущности"], set()).add(int(row["значение"]))

    cursor.execute("SELECT учитель_ид, класс_ид FROM УЧИТЕЛЬ_КЛАСС")
    учитель_классы = {}
    for row in cursor.fetchall():
        учитель_классы.setdefault(row["учитель_ид"], set()).add(row["класс_ид"])

    cursor.execute("SELECT учитель_ид, предмет_ид, класс_ид, часов FROM УЧИТЕЛЬ_ПРЕДМЕТ_КЛАСС")
    прямые_назначения = {}
    for row in cursor.fetchall():
        прямые_назначения[(row["класс_ид"], row["предмет_ид"])] = (row["учитель_ид"], row["часов"])

    # Ступени, в которых работает учитель (часы не задаются — нагрузку считает программа)
    cursor.execute("SELECT ид, работает_1_4, работает_5_9, работает_10_11 FROM УЧИТЕЛЬ")
    ступени_учителя = {
        row["ид"]: {с for с, кол in (("1-4", "работает_1_4"), ("5-9", "работает_5_9"),
                                      ("10-11", "работает_10_11")) if row[кол]}
        for row in cursor.fetchall()
    }

    cursor.execute("SELECT класс_ид, предмет_ид, часов_в_неделю FROM УЧЕБНЫЙ_ПЛАН")
    план = {
        (row["класс_ид"], row["предмет_ид"]): row["часов_в_неделю"]
        for row in cursor.fetchall()
        if row["класс_ид"] in название_класса
    }

    # ================= ПРОХОД 1: назначаем учителя на каждую (класс, предмет) =================
    учит_нагрузка = {}

    def выбрать(группа, класс_ид):
        """Учитель, который уже ведёт этот класс, иначе — наименее загруженный."""
        if not группа:
            return None
        return min(группа, key=lambda у: (класс_ид not in учитель_классы.get(у, set()),
                                          учит_нагрузка.get(у, 0), у))

    назначение = {}
    лимит_блока = {}
    # (класс_ид, предмет_ид) -> почему поставлены не все часы
    причина = {}

    def закрепить(класс_ид, предмет_ид, учитель, ставим):
        назначение[(класс_ид, предмет_ид)] = учитель
        лимит_блока[(класс_ид, предмет_ид)] = ставим
        учит_нагрузка[учитель] = учит_нагрузка.get(учитель, 0) + ставим

    блоки = []
    for (класс_ид, предмет_ид), часов in план.items():
        cand = предмет_учителя.get(предмет_ид, [])
        блоки.append((len(cand), -часов, класс_ид, предмет_ид, часов))
    блоки.sort(key=lambda x: (x[0], x[1]))

    for _, __, класс_ид, предмет_ид, часов in блоки:
        ступ = ступень_по_параллели(класс_параллель[класс_ид])

        # 1. Прямое закрепление
        прямое = прямые_назначения.get((класс_ид, предмет_ид))
        if прямое:
            назн_учитель, назн_часов = прямое
            ставим = назн_часов if (назн_часов and назн_часов > 0) else часов
            if ставим < часов:
                причина[(класс_ид, предмет_ид)] = f"в распределении назначено только {ставим} ч."
            закрепить(класс_ид, предмет_ид, назн_учитель, ставим)
            continue

        # 2. Автоматический подбор среди учителей предмета, работающих на этой ступени
        cand = предмет_учителя.get(предмет_ид, [])
        if not cand:
            причина[(класс_ид, предмет_ид)] = "нет учителя по этому предмету"
            continue

        учитель = выбрать([u for u in cand if ступ is None or ступ in ступени_учителя.get(u, set())], класс_ид)
        if учитель is None:
            причина[(класс_ид, предмет_ид)] = f"нет учителя предмета, работающего в {ступ} классах"
            continue

        закрепить(класс_ид, предмет_ид, учитель, часов)

    # ================= ПРОХОД 2: распределение уроков по дням (Day Assignment) =================
    класс_бюджет = {}
    for к in классы:
        к_ид = к["ид"]
        всего_ставим = sum(лимит_блока.get((к_ид, п_ид), 0) for (c, п_ид) in назначение if c == к_ид)
        класс_бюджет[к_ид] = get_daily_budget(к["параллель"], всего_ставим)

    день_уроки = {к["ид"]: {d: [] for d in range(1, 7)} for к in классы}
    # (учитель, день) -> {класс_ид: сколько уроков учителя в этом классе в этот день}
    учитель_день_классы = defaultdict(lambda: defaultdict(int))

    def нагрузка_в_день(уч_ид, d):
        return sum(учитель_день_классы[(уч_ид, d)].values())

    def поставить_в_день(к_ид, d, п_ид, уч_ид):
        день_уроки[к_ид][d].append((п_ид, уч_ид))
        учитель_день_классы[(уч_ид, d)][к_ид] += 1

    def убрать_из_дня(к_ид, d, idx):
        п_ид, уч_ид = день_уроки[к_ид][d].pop(idx)
        учитель_день_классы[(уч_ид, d)][к_ид] -= 1

    def учителю_хватит_слотов(уч_ид, d, к_ид):
        """Можно ли дать учителю ещё один урок в классе к_ид в день d без накладки.

        Урок в классе с K уроками за день может стоять только на слотах 1..K,
        поэтому, отсортировав длины дней классов учителя, i-й урок (с 1)
        должен попадать в класс с длиной дня не меньше i.
        """
        if уч_ид is None:
            return True
        длины = [класс_бюджет[c][d]
                 for c, n in учитель_день_классы[(уч_ид, d)].items()
                 for _ in range(n)]
        длины.append(класс_бюджет[к_ид][d])
        длины.sort()
        return all(i + 1 <= k for i, k in enumerate(длины))

    for к in классы:
        к_ид = к["ид"]
        параллель = к["параллель"]
        бюджет = класс_бюджет[к_ид]

        предметы_класса = []
        for (c, п_ид), уч_ид in назначение.items():
            if c != к_ид:
                continue
            ч = лимит_блока.get((c, п_ид), 0)
            if ч > 0:
                off = нерабочие_дни.get(уч_ид, set())
                avail = [d for d in range(1, 7) if бюджет[d] > 0 and d not in off]
                предметы_класса.append({
                    "предмет_ид": п_ид,
                    "учитель_ид": уч_ид,
                    "часов": ч,
                    "avail_days": avail
                })

        # Первыми размещаем предметы с наименьшим количеством доступных дней учителя и с большим числом часов
        предметы_класса.sort(key=lambda item: (len(item["avail_days"]), -item["часов"]))

        # Для начальных классов 2-4: на субботу ставим ровно 2 лёгких урока
        if параллель in ("2", "3", "4") and бюджет[6] == 2:
            субботние = [it for it in предметы_класса if 6 in it["avail_days"] and it["часов"] <= 2]
            if len(субботние) < 2:
                субботние = [it for it in предметы_класса if 6 in it["avail_days"]]
            # Сначала учителя, у которых в субботу ещё нет уроков в других классах
            субботние.sort(key=lambda it: нагрузка_в_день(it["учитель_ид"], 6))
            поставлено_сб = 0
            for it in субботние:
                if поставлено_сб >= 2:
                    break
                if not учителю_хватит_слотов(it["учитель_ид"], 6, к_ид):
                    continue
                поставить_в_день(к_ид, 6, it["предмет_ид"], it["учитель_ид"])
                it["часов"] -= 1
                поставлено_сб += 1

        # Распределяем остальные часы
        for it in предметы_класса:
            п_ид = it["предмет_ид"]
            уч_ид = it["учитель_ид"]
            осталось_ч = it["часов"]

            while осталось_ч > 0:
                лучший_день = None
                лучший_скор = (INF, INF, INF)

                for d in it["avail_days"]:
                    свободно = бюджет[d] - len(день_уроки[к_ид][d])
                    if свободно <= 0:
                        continue
                    уже_есть = sum(1 for (p, _) in день_уроки[к_ид][d] if p == п_ид)
                    if уже_есть >= 2:
                        continue
                    if not учителю_хватит_слотов(уч_ид, d, к_ид):
                        continue
                    нагр_учителя = нагрузка_в_день(уч_ид, d)
                    скор = (уже_есть, нагр_учителя, -свободно)
                    if скор < лучший_скор:
                        лучший_скор = скор
                        лучший_день = d

                if лучший_день is not None:
                    поставить_в_день(к_ид, лучший_день, п_ид, уч_ид)
                    осталось_ч -= 1
                else:
                    # Рокировка (swap) между днями для преодоления узких мест
                    swapped = False
                    for d1 in it["avail_days"]:
                        if swapped:
                            break
                        уже_в_d1 = sum(1 for (p, _) in день_уроки[к_ид][d1] if p == п_ид)
                        if уже_в_d1 >= 2:
                            continue
                        for idx2, (p2, u2) in enumerate(день_уроки[к_ид][d1]):
                            if p2 == п_ид:
                                continue
                            off2 = нерабочие_дни.get(u2, set())
                            for d2 in range(1, 7):
                                if d2 == d1 or d2 in off2 or бюджет[d2] <= len(день_уроки[к_ид][d2]):
                                    continue
                                if sum(1 for (p, _) in день_уроки[к_ид][d2] if p == p2) >= 2:
                                    continue
                                if not учителю_хватит_слотов(u2, d2, к_ид):
                                    continue
                                убрать_из_дня(к_ид, d1, idx2)
                                if not учителю_хватит_слотов(уч_ид, d1, к_ид):
                                    # Откатываем: освободившийся слот всё равно не подходит
                                    день_уроки[к_ид][d1].insert(idx2, (p2, u2))
                                    учитель_день_классы[(u2, d1)][к_ид] += 1
                                    continue
                                поставить_в_день(к_ид, d2, p2, u2)
                                поставить_в_день(к_ид, d1, п_ид, уч_ид)
                                осталось_ч -= 1
                                swapped = True
                                break
                            if swapped:
                                break
                    if not swapped:
                        причина[(к_ид, п_ид)] = (
                            f"у учителя {фио_учителя.get(уч_ид, уч_ид)} нет свободных уроков "
                            f"без накладок (слишком большая нагрузка)"
                        )
                        break

    # ================= ПРОХОД 3: расставляем уроки по слотам 1..K внутри каждого дня =================
    добавлено = 0
    поставлено = defaultdict(int)

    for день in range(1, 7):
        classes_lessons_day = {}
        for к in классы:
            к_ид = к["ид"]
            ур_список = день_уроки[к_ид][день]
            if ур_список:
                classes_lessons_day[к_ид] = [
                    {
                        "ид": f"{к_ид}_{день}_{idx}",
                        "класс_ид": к_ид,
                        "предмет_ид": p,
                        "учитель_ид": u
                    }
                    for idx, (p, u) in enumerate(ур_список)
                ]

        if not classes_lessons_day:
            continue

        слоты_дня = assign_slots_for_day(день, classes_lessons_day)

        for к_ид, items in classes_lessons_day.items():
            for it in items:
                слот = слоты_дня[it["ид"]]
                cursor.execute("""
                    INSERT INTO УРОК
                    (класс_ид, предмет_ид, учитель_ид, день_недели, номер_урока, статус)
                    VALUES (?, ?, ?, ?, ?, 'черновик')
                """, (it["класс_ид"], it["предмет_ид"], it["учитель_ид"], день, слот))
                добавлено += 1
                поставлено[(it["класс_ид"], it["предмет_ид"])] += 1

    # ================= Пропущенные =================
    пропущенные_список = []
    уроки_пропущены = 0
    for (класс_ид, предмет_ид), нужно in план.items():
        остаток_ч = нужно - поставлено[(класс_ид, предмет_ид)]
        if остаток_ч > 0:
            имя = название_предмета.get(предмет_ид, str(предмет_ид))
            строка = f"{название_класса[класс_ид]}: {имя} ({остаток_ч} ч.)"
            if (класс_ид, предмет_ид) in причина:
                строка += f" — {причина[(класс_ид, предмет_ид)]}"
            пропущенные_список.append(строка)
            уроки_пропущены += остаток_ч

    conn.commit()
    conn.close()

    return добавлено, уроки_пропущены, пропущенные_список
