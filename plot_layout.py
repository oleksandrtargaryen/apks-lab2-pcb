#!/usr/bin/env python3
"""Рисунок рекомендованої розстановки компонентів і ratsnest-зв'язків (потрібен matplotlib).

Запуск:  python3 plot_layout.py   -> docs/img/layout_preview.png
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

import guid as g


def main():
    root = Path(__file__).resolve().parent
    guid = g.make_guid()
    comps = g.components(guid)
    _, connected, free = g.nets(comps)

    pin_xy = {}
    fig, ax = plt.subplots(figsize=(10, 6.6))
    ax.add_patch(FancyBboxPatch((0, 0), g.BOARD_W, g.BOARD_H, boxstyle="round,pad=0,rounding_size=3.18",
                                fc="#1f6f43", ec="#e8c34a", lw=2))
    for ref, group, side, pins in comps:
        cx, cy = g.PLACEMENT[ref]
        ax.add_patch(Rectangle((cx - side / 2, cy - side / 2), side, side, fc="#222", ec="#ddd", lw=1))
        ax.text(cx, cy, f"{ref}\n{group}", ha="center", va="center", color="w", fontsize=7 if side < 8 else 8)
        pts, _ = g.pad_positions(side, len(pins))
        for (pin, ch), (dx, dy) in zip(pins, pts):
            x, y = cx + dx, cy + dy
            pin_xy[(ref, pin)] = (x, y)
            ax.plot(x, y, "s", color="#d9a441", ms=5)
            ax.annotate(ch, (x, y), xytext=(0, 5), textcoords="offset points", ha="center",
                        color="#fff6c8", fontsize=6)
    jx, jy = g.PLACEMENT["J1"]
    n = len(free)
    ax.add_patch(Rectangle((jx - 1.6, jy - 2.54 * n / 2), 3.2, 2.54 * n, fc="#111", ec="#ddd"))
    ax.text(jx, jy + 2.54 * n / 2 + 1.5, "J1", color="w", ha="center", fontsize=8)
    for k, (ch, (r, p)) in enumerate(free.items(), 1):
        y = jy + 2.54 * n / 2 - 2.54 * (k - 0.5)
        pin_xy[("J1", k)] = (jx, y)
        ax.plot(jx, y, "o", color="#d9a441", ms=6)
        x1, y1 = pin_xy[(r, p)]
        ax.plot([jx, x1], [y, y1], "--", color="#9fd3ff", lw=0.8)
        ax.text(jx - 2.2, y, ch, color="#fff6c8", fontsize=6, ha="right", va="center")
    for ch, pins in connected.items():
        pts = [pin_xy[p] for p in pins]
        # ratsnest як ланцюжок у порядку X - наближення мінімального дерева
        pts.sort()
        for a, b in zip(pts, pts[1:]):
            ax.plot([a[0], b[0]], [a[1], b[1]], "-", color="#9fd3ff", lw=0.7, alpha=0.85)
    ax.set_xlim(-3, g.BOARD_W + 3)
    ax.set_ylim(-3, g.BOARD_H + 3)
    ax.set_aspect("equal")
    ax.set_xlabel("X, мм")
    ax.set_ylabel("Y, мм")
    ax.set_title(f"Рекомендована розстановка, плата {g.BOARD_W}×{g.BOARD_H} мм, GUID {guid}", fontsize=9)
    out = root / "docs" / "img"
    out.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out / "layout_preview.png", dpi=180)
    print(out / "layout_preview.png")


if __name__ == "__main__":
    main()
