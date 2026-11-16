"""Генерація схеми й плати для EasyEDA Std (формат «compressed JSON» редактора 6.5).

Вхід — ті самі дані, що в guid.py / docs/tables.md (GUID -> компоненти, кола, розстановка).
Вихід:
  easyeda/schematic.json — принципова схема: U1–U5 (пін = символ GUID), J1, мітки кіл;
  easyeda/pcb.json       — плата 85.6 × 53.98 мм (кредитна картка), 2 шари,
                           футпринти SQ*_Ux з падами 1.0 × 0.6 мм, призначені кола.
Обидва файли вставляються в EasyEDA через api('applySource', ...) у вікні Script.
Запуск: python3 easyeda/gen_easyeda.py
"""
import json
import sys
from itertools import count
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from guid import BOARD_H, BOARD_W, PLACEMENT, components, make_guid, nets, pad_positions  # noqa: E402

_ids = count(1)


def gid():
    return f"gge{next(_ids)}"


def f(v):
    return f"{v:.4f}".rstrip("0").rstrip(".")


# --------------------------------------------------------------------------- дані
GUID = make_guid()
COMPS = components(GUID)
WHERE, CONNECTED, FREE = nets(COMPS)
J1_ORDER = sorted(FREE)  # 2, 4, 8, 9, d -> J1.1..J1.5 (як у docs/tables.md)


def net_of(ch):
    return f"N_{ch.upper()}" if ch in CONNECTED else f"FREE_{ch.upper()}"


# symbol pins: ref -> [(pin_no, label, net)]
SYM_PINS = {ref: [(n, ch, net_of(ch)) for n, ch in pins] for ref, _, _, pins in COMPS}
SYM_PINS["J1"] = [(i, str(i), net_of(ch)) for i, ch in enumerate(J1_ORDER, 1)]
SIDE = {ref: side for ref, _, side, _ in COMPS}

# --------------------------------------------------------------------------- схема
SCH_POS = {"J1": (120, 260), "U1": (330, 150), "U2": (330, 420), "U5": (600, 200), "U4": (860, 140), "U3": (860, 380)}
PIN_LEN, PITCH, BODY_W, STUB = 20, 20, 80, 30


def sch_pin(num, name, x, y, side):
    """side: -1 — пін зліва (вивід дивиться вліво), +1 — справа."""
    ex = x + side * PIN_LEN  # кінець виводу (точка з'єднання)
    rot = 180 if side < 0 else 0
    name_x, name_a = (x + 4, "start") if side < 0 else (x - 4, "end")
    num_x, num_a = (ex + 3, "start") if side < 0 else (ex - 3, "end")
    return "^^".join([
        f"P~show~0~{num}~{ex}~{y}~{rot}~{gid()}~0",
        f"{ex}~{y}",
        f"M {ex} {y} h {-side * PIN_LEN}~#880000",
        f"1~{name_x}~{y + 4}~0~{name}~{name_a}~~~#0000FF",
        f"1~{num_x}~{y - 3}~0~{num}~{num_a}~~~#0000FF",
        f"0~{ex}~{y}",
        "0~",
    ]), ex


def sch_symbol(ref, x0, y0):
    pins = SYM_PINS[ref]
    if ref == "J1":
        left, right = [], pins
        title = "HDR 1x5"
    else:
        half = (len(pins) + 1) // 2
        left, right = pins[:half], pins[half:]
        title = f"SQ{len(pins)}"
    rows = max(len(left), len(right))
    h = rows * PITCH + PITCH
    parts = [
        f"T~P~{x0}~{y0 - 8}~0~#000080~Arial~~~~~comment~{ref}~1~start~{gid()}~0~pinpart",
        f"T~N~{x0}~{y0 + h + 14}~0~#000080~Arial~~~~~comment~{title}~1~start~{gid()}~0~pinpart",
        f"R~{x0}~{y0}~~~{BODY_W}~{h}~#880000~1~0~#FFFFFF~{gid()}~0",
    ]
    extra = []  # дроти й мітки кіл поза символом
    for side, group in ((-1, left), (1, right)):
        bx = x0 if side < 0 else x0 + BODY_W
        for i, (num, label, net) in enumerate(group):
            y = y0 + PITCH * (i + 1)
            pin, ex = sch_pin(num, label, bx, y, side)
            parts.append(pin)
            nx = ex + side * STUB
            extra.append(f"W~{ex} {y} {nx} {y}~#008800~1~0~none~{gid()}~0")
            anchor = "end" if side < 0 else "start"
            extra.append(f"N~{nx}~{y}~0~#0000ff~{net}~{gid()}~{anchor}~{nx + side * 2}~{y - 3}~Times New Roman~")
    head = f"LIB~{x0}~{y0}~package`{title.replace(' ', '_')}_{ref}`spicePre`{ref[0]}`~~0~{gid()}~~~~0~~yes~yes"
    return "#@$".join([head] + parts), extra


def schematic():
    shapes = []
    for ref, (x, y) in SCH_POS.items():
        lib, extra = sch_symbol(ref, x, y)
        shapes.append(lib)
        shapes += extra
    shapes.append(f"T~L~330~560~0~#000000~Arial~12pt~bold~~~comment~ПІБ: Бартошко Олександр Ігорович, КІ-408; GUID {GUID}~1~start~{gid()}~0~")
    return {
        "head": {"docType": "1", "editorVersion": "6.5.61", "newgId": True, "c_para": {"Prefix Start": "1"}, "c_spiceCmd": None, "hasIdFlag": True},
        "canvas": "CA~1000~1000~#FFFFFF~yes~#CCCCCC~5~1000~1000~line~5~pixel~5~0~0",
        "shape": shapes,
    }


# --------------------------------------------------------------------------- плата
U = 1 / 0.254  # мм -> одиниці EasyEDA PCB (10 mil)
OX, OY = 4000, 3000  # початок координат плати в полотні (лівий нижній кут)
PAD_L, PAD_W = 1.0, 0.6


def P(x_mm, y_mm):
    """мм від лівого нижнього кута плати -> координати полотна (вісь Y полотна донизу)."""
    return OX + x_mm * U, OY - y_mm * U


def pad_poly(cx, cy, w, h):
    return " ".join(f"{f(x)} {f(y)}" for x, y in ((cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2), (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)))


def footprint(ref, pins, pad_xy, side_mm, xc, yc, name):
    cx, cy = P(xc, yc)
    parts = []
    for (num, label, net), (dx, dy) in zip(pins, pad_xy):
        px, py = P(xc + dx, yc + dy)
        horizontal = abs(abs(dx) - side_mm / 2) < 1e-6 and side_mm > 0  # пад на лівій/правій стороні
        w, h = (PAD_L * U, PAD_W * U) if horizontal else (PAD_W * U, PAD_L * U)
        parts.append(f"PAD~RECT~{f(px)}~{f(py)}~{f(w)}~{f(h)}~1~{net}~{num}~0~{pad_poly(px, py, w, h)}~0~{gid()}~0~~Y~0~0~0.2~{f(px)},{f(py)}")
    if side_mm:
        hs = side_mm / 2 * U
        pts = [(cx - hs, cy - hs), (cx + hs, cy - hs), (cx + hs, cy + hs), (cx - hs, cy + hs), (cx - hs, cy - hs)]
        parts.append(f"TRACK~0.6~3~~{' '.join(f'{f(x)} {f(y)}' for x, y in pts)}~{gid()}~0")
        parts.append(f"CIRCLE~{f(cx - hs + 1.2 * U)}~{f(cy - hs + 1.2 * U)}~1.2~0.6~3~{gid()}~0~~")
    head = f"LIB~{f(cx)}~{f(cy)}~package`{name}`pre`{ref}`~0~0~{gid()}~1~~0"
    return "#@$".join([head] + parts)


def pcb():
    shapes = []
    # контур кредитної картки з радіусом 3.18 мм
    r = 3.18
    x0, y0 = P(0, 0)
    x1, y1 = P(BOARD_W, BOARD_H)
    R = r * U
    segs = [
        (x0 + R, y0, x1 - R, y0), (x1, y0 - R, x1, y1 + R), (x1 - R, y1, x0 + R, y1), (x0, y1 + R, x0, y0 - R),
    ]
    for a, b, c, d in segs:
        shapes.append(f"TRACK~1~10~~{f(a)} {f(b)} {f(c)} {f(d)}~{gid()}~0")
    arcs = [
        (x1 - R, y0, x1, y0 - R), (x1, y1 + R, x1 - R, y1), (x0 + R, y1, x0, y1 + R), (x0, y0 - R, x0 + R, y0),
    ]
    for a, b, c, d in arcs:
        shapes.append(f"ARC~1~10~~M {f(a)} {f(b)} A {f(R)} {f(R)} 0 0 0 {f(c)} {f(d)}~~{gid()}~0")
    for ref, (xc, yc) in PLACEMENT.items():
        pins = SYM_PINS[ref]
        if ref == "J1":
            pad_xy = [(0.0, (3 - i) * 2.54) for i in range(1, 6)]  # 1x5, крок 2.54, J1.1 зверху
            shapes.append(footprint(ref, pins, pad_xy, 0, xc, yc, "HDR_1x5_SMD"))
        else:
            side = SIDE[ref]
            pts, _ = pad_positions(side, len(pins))
            shapes.append(footprint(ref, pins, pts, side, xc, yc, f"SQ{side}_{ref}"))
    return {
        "head": {"docType": "3", "editorVersion": "6.5.61", "newgId": True, "c_para": {}, "hasIdFlag": True},
        "canvas": "CA~1000~1000~#000000~yes~#FFFFFF~10~1000~1000~line~0.5~mm~1~45~~0.5~4000~3000~0~yes",
        "shape": shapes,
        # правила DRC (одиниці EasyEDA = 10 mil): доріжка 0.25, зазор 0.2, via 0.6 / отвір 0.3 мм
        "DRCRULE": {"Default": {"trackWidth": round(0.25 * U, 3), "clearance": round(0.2 * U, 3), "viaHoleDiameter": round(0.6 * U, 3), "viaHoleD": round(0.3 * U, 3)}, "isRealtime": True, "isDrcOnRoutingOrPlaceVia": False, "checkObjectToCopperarea": True, "showDRCRangeLine": True},
    }


if __name__ == "__main__":
    out = ROOT / "easyeda"
    (out / "schematic.json").write_text(json.dumps(schematic(), ensure_ascii=False))
    (out / "pcb.json").write_text(json.dumps(pcb(), ensure_ascii=False))
    nets_used = sorted({n for p in SYM_PINS.values() for _, _, n in p})
    print("кола:", len(nets_used), nets_used)
    print("OK:", out / "schematic.json", out / "pcb.json")
