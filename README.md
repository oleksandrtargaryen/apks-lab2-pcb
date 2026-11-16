# АПКС — Лабораторна робота №2: проєктування та топологія друкованої плати

**Студент:** Бартошко Олександр Ігорович, група КІ-408  
**Дисципліна:** Автоматизоване проєктування комп'ютерних систем

## Вихідні дані
- GUID (UUID v5 / SHA-1 від ПІБ): `81c375e7-d203-505f-a3ce-e051c5794f3a`
- Компоненти: U1 8×8 мм, U2/U3/U4 4×4 мм, U5 12×12 мм; плата ≤ 85.6×53.98 мм (кредитна картка)

## Вміст
| Файл | Призначення |
|---|---|
| `guid.py` | генерація GUID, розмірів, пінів, таблиці з'єднань, розстановки (+ самоперевірка) |
| `plot_layout.py` | рисунок рекомендованої розстановки з ratsnest (`docs/img/layout_preview.png`) |
| `docs/tables.md` | усі таблиці для звіту |
| `netlist.csv`, `placement.csv` | список з'єднань і координати |
| `docs/easyeda-guide.md` | покрокова інструкція виконання в EasyEDA |
| `easyeda/gen_easyeda.py` | генерація схеми й плати у форматі EasyEDA Std з тих самих даних (`easyeda/schematic.json`, `easyeda/pcb.json`) |
| `docs/img/schematic.png`, `pcb_layout.png`, `drc.png`, `pcb_3d.png`, `gerber.png` | скріни з EasyEDA: схема, топологія, DRC (0 помилок), 3D, генерація Gerber |
| `gerber/` | виробничі файли Gerber RS-274X (EasyEDA, 2 шари, 85.6 × 53.98 мм) |

## Результат у EasyEDA
- Проєкт `apks-lab2-pcb`: схема `Sheet_1` (U1–U5, J1, 14 кіл) і плата `PCB_credit_card`.
- Схема й плата вставлені через `api('applySource', …)` у вікні *Advanced → Extensions → Script*
  з `easyeda/schematic.json` і `easyeda/pcb.json`.
- Правила: доріжка 0.25 мм, зазор 0.2 мм, via 0.6 / 0.3 мм.
- Автотрасування (cloud): 37 з 37 з'єднань (100 %), 6 via, обидва шари.
- DRC: **0 помилок**, кола 14 / 14.

## Запуск
```bash
python3 guid.py          # таблиці (лише стандартна бібліотека)
pip install matplotlib && python3 plot_layout.py
python3 easyeda/gen_easyeda.py   # easyeda/schematic.json, easyeda/pcb.json
```
