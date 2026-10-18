#!/usr/bin/env python3
"""Лабораторна робота №2 (АПКС): генерація параметрів друкованої плати з GUID.

GUID отримується детерміновано: UUID версії 5 (SHA-1 хеш) від повного імені
студента у просторі імен NAMESPACE_DNS. Кожна група GUID = квадратний
компонент U1..U5, довжина групи = сторона компонента в мм, кожен символ = пін.

Запуск:  python3 guid.py            -> друкує таблиці та оновлює docs/tables.md,
                                       netlist.csv, placement.csv
"""
import csv
import itertools
import uuid
from collections import defaultdict
from pathlib import Path

FULL_NAME = "Бартошко Олександр Ігорович"
BOARD_W, BOARD_H = 85.6, 53.98  # форм-фактор кредитної картки, мм

# Рекомендована розстановка (центр компонента, мм; початок координат - лівий нижній кут плати).
# Правило "чим більше зв'язків - тим ближче": U5 у центрі, U1/U4 (найбільше спільних кіл
# з U5) поруч із ним; U1 та U2 ближче до роз'єму J1, бо мають вільні піни.
PLACEMENT = {
    "J1": (5.0, 27.0),
    "U1": (24.0, 33.0),
    "U2": (22.0, 17.0),
    "U5": (44.0, 27.0),
    "U4": (62.0, 35.0),
    "U3": (62.0, 18.0),
}


def make_guid(name: str = FULL_NAME) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, name))


def components(guid: str):
    """[(ref, group, side_mm, [(pin_no, symbol), ...]), ...]"""
    result = []
    for i, group in enumerate(guid.split("-"), 1):
        pins = [(j, ch) for j, ch in enumerate(group, 1)]
        result.append((f"U{i}", group, len(group), pins))
    return result


def nets(comps):
    """Символ -> список пінів (ref, pin). Кола = символи, що трапляються >= 2 разів."""
    where = defaultdict(list)
    for ref, _, _, pins in comps:
        for pin, ch in pins:
            where[ch].append((ref, pin))
    connected = {ch: p for ch, p in sorted(where.items()) if len(p) >= 2}
    free = {ch: p[0] for ch, p in sorted(where.items()) if len(p) == 1}
    return where, connected, free


def weights(comps):
    """Кількість спільних кіл між парами компонентів."""
    sets = {ref: set(group) for ref, group, _, _ in comps}
    return {(a, b): len(sets[a] & sets[b]) for a, b in itertools.combinations(sets, 2)}


def pad_positions(side: float, n_pins: int):
    """Координати пінів відносно центру квадратного корпусу.

    Піни рівномірно по периметру, n_pins/4 на сторону, нумерація проти
    годинникової стрілки з лівого верхнього кута (як у мікросхем).
    """
    per_side = n_pins // 4
    pitch = side / (per_side + 1)
    h = side / 2
    pts = []
    for k in range(per_side):  # ліва сторона, згори донизу
        pts.append((-h, h - pitch * (k + 1)))
    for k in range(per_side):  # нижня, зліва направо
        pts.append((-h + pitch * (k + 1), -h))
    for k in range(per_side):  # права, знизу догори
        pts.append((h, -h + pitch * (k + 1)))
    for k in range(per_side):  # верхня, справа наліво
        pts.append((h - pitch * (k + 1), h))
    return pts, pitch


def self_check(guid, comps, where, connected, free):
    total = sum(len(p) for _, _, _, p in comps)
    assert total == 32, "GUID має містити 32 hex-символи"
    assert [c[2] for c in comps] == [8, 4, 4, 4, 12]
    counted = sum(len(p) for p in connected.values()) + len(free)
    assert counted == total, "кожен пін має бути врахований рівно один раз"
    for ref, (x, y) in PLACEMENT.items():
        side = next((c[2] for c in comps if c[0] == ref), None)
        # J1 - однорядна гребінка 1×N з кроком 2.54 мм, орієнтована вертикально
        hw, hh = (side / 2, side / 2) if side else (2.54 / 2, 2.54 * len(free) / 2)
        assert hw < x < BOARD_W - hw and hh < y < BOARD_H - hh, ref


def markdown(guid, comps, where, connected, free, w):
    out = [f"# Параметри плати\n", f"ПІБ: **{FULL_NAME}**  \n",
           f"GUID (uuid5, NAMESPACE_DNS): **`{guid}`**\n",
           "\n## Компоненти\n",
           "| Компонент | Група GUID | Довжина | Розмір, мм | Піни (номер:символ) |",
           "|---|---|---|---|---|"]
    for ref, group, side, pins in comps:
        pl = ", ".join(f"{p}:{c}" for p, c in pins)
        out.append(f"| {ref} | `{group}` | {side} | {side}×{side} | {pl} |")
    out += ["\n## Таблиця з'єднань (кола)\n",
            "| Коло | Символ | Піни | Кількість пінів |", "|---|---|---|---|"]
    for ch, pins in connected.items():
        out.append(f"| N_{ch.upper()} | `{ch}` | {', '.join(f'{r}.{p}' for r, p in pins)} | {len(pins)} |")
    out += ["\n## Вільні піни → роз'єм J1 (ліва коротка сторона)\n",
            "| Пін J1 | Коло | Пін компонента | Символ |", "|---|---|---|---|"]
    for k, (ch, (r, p)) in enumerate(free.items(), 1):
        out.append(f"| J1.{k} | FREE_{ch.upper()} | {r}.{p} | `{ch}` |")
    out += ["\n## Кількість спільних кіл між компонентами\n",
            "| Пара | Спільні кола |", "|---|---|"]
    for (a, b), v in sorted(w.items(), key=lambda x: -x[1]):
        out.append(f"| {a}–{b} | {v} |")
    out += ["\n## Рекомендована розстановка (центр, мм; (0,0) — лівий нижній кут)\n",
            "| Елемент | X | Y |", "|---|---|---|"]
    for ref, (x, y) in PLACEMENT.items():
        out.append(f"| {ref} | {x} | {y} |")
    out += ["\n## Футпринти (контактні площадки по периметру корпусу)\n",
            "| Компонент | Сторона, мм | Пінів на сторону | Крок, мм |", "|---|---|---|---|"]
    for ref, _, side, pins in comps:
        _, pitch = pad_positions(side, len(pins))
        out.append(f"| {ref} | {side} | {len(pins)//4} | {pitch:.2f} |")
    out.append("\n### Координати контактних площадок відносно центру футпринта, мм\n")
    for ref, _, side, pins in comps:
        pts, _ = pad_positions(side, len(pins))
        out += [f"**{ref}** ({side}×{side} мм)\n", "| Пін | Символ | X | Y |", "|---|---|---|---|"]
        for (pin, ch), (x, y) in zip(pins, pts):
            out.append(f"| {pin} | `{ch}` | {x:+.2f} | {y:+.2f} |")
        out.append("")
    return "\n".join(out) + "\n"


def main():
    root = Path(__file__).resolve().parent
    guid = make_guid()
    comps = components(guid)
    where, connected, free = nets(comps)
    w = weights(comps)
    self_check(guid, comps, where, connected, free)

    md = markdown(guid, comps, where, connected, free, w)
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs" / "tables.md").write_text(md, encoding="utf-8")
    with open(root / "netlist.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["net", "symbol", "ref", "pin"])
        for ch, pins in connected.items():
            for r, p in pins:
                wr.writerow([f"N_{ch.upper()}", ch, r, p])
        for k, (ch, (r, p)) in enumerate(free.items(), 1):
            wr.writerow([f"FREE_{ch.upper()}", ch, r, p])
            wr.writerow([f"FREE_{ch.upper()}", ch, "J1", k])
    with open(root / "placement.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["ref", "x_mm", "y_mm"])
        for ref, (x, y) in PLACEMENT.items():
            wr.writerow([ref, x, y])
    print(md)
    print("self-check: OK")


if __name__ == "__main__":
    main()
