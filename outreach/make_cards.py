"""Инфографика для поста РГС: три карточки 1080×1350 (HTML -> PNG через headless Chrome).

Запуск: uv run python outreach/make_cards.py
"""
import math
import subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# цифры сезона 2026 без Redline (не входит в календарь серии); считаются в notebooks/analysis.ipynb
RIDERS = {2023: 468, 2024: 643, 2025: 1315, 2026: 1793}
STARTS_2026, WOMEN_2026, WOMEN_2023 = 2730, 348, 84
KM_2026 = 249_000          # сумма дистанций финишёров (Покрова ~100 км)
RETURNED, TWO_PLUS, THREE_PLUS, ALL_SEVEN = 689, 552, 235, 4
STAGES = [  # дата, этап, регион, широта, долгота, участников
    ("13.06", "Спортмарафон Фест", "c", 54.75, 35.60, 356),
    ("20.06", "Царь Грейдер", "nw", 58.64, 30.31, 368),
    ("11.07", "SHULZ", "nw", 60.78, 29.85, 448),
    ("18.07", "Gravel Instinct", "c", 56.95, 35.65, 351),
    ("25.07", "Ардор", "nw", 60.607, 30.105, 231),
    ("01.08", "Покрова", "c", 56.29, 40.00, 326),
    ("15.08", "Fury Road", "nw", 60.631, 30.108, 641),
]

CSS = """
@page { size: 1080px 1350px; margin: 0; }
* { box-sizing: border-box; margin: 0; padding: 0; }
/* стиль gravelseries.ru: бумага, чёрная тушь, тонкие чёрные линейки, PT Sans Narrow заглавными */
:root { --bg: #f5f5f3; --paper: #ffffff; --ink: #000000; --ink2: #444444; --ink3: #74746f; --acc: #000000; --line: #000000; --quiet: #c9c9c4; }
html, body { width: 1080px; height: 1350px; background: var(--bg); color: var(--ink); font-family: "PT Sans", "Helvetica Neue", sans-serif; }
.card { width: 1080px; height: 1350px; padding: 84px 84px 64px; display: grid; grid-template-rows: auto 1fr auto; gap: 40px; position: relative; overflow: hidden; }
.eyebrow { font-family: "PT Sans Narrow", "PT Sans", sans-serif; font-size: 26px; letter-spacing: .14em; text-transform: uppercase; color: var(--ink3); }
h1 { font-family: "PT Sans Narrow", "Arial Narrow", sans-serif; font-weight: 700; text-transform: uppercase; font-size: 92px; line-height: .92; margin-top: 18px; }
.big { font-family: "PT Sans Narrow", sans-serif; font-weight: 700; line-height: .85; }
.foot { display: flex; justify-content: space-between; align-items: end; font-size: 22px; color: var(--ink3); border-top: 2px solid var(--line); padding-top: 22px; }
.foot b { color: var(--ink); font-family: "PT Sans Narrow", sans-serif; font-size: 30px; text-transform: uppercase; letter-spacing: .02em; }
"""


def page(body: str) -> str:
    return f'<!doctype html><html lang="ru"><head><meta charset="utf-8"><style>{CSS}</style></head><body>{body}</body></html>'


FOOT = '<div class="foot"><b>Русская гравийная серия</b><span>по протоколам gravelseries.ru</span></div>'


def card_growth() -> str:
    mx = max(RIDERS.values())
    bars = "".join(
        f'<div class="b"><span>{v:,}</span><i style="height:{v / mx * 240:.0f}px;{"background:var(--ink)" if y == 2026 else ""}"></i><em>{y}</em></div>'.replace(",", " ")
        for y, v in RIDERS.items())
    return page(f"""
<style>
.hero {{ display: grid; gap: 10px; align-content: start; }}
.hero .big {{ font-size: 230px; color: var(--acc); letter-spacing: -.02em; }}
.hero p {{ font-size: 40px; line-height: 1.15; }}
.bars {{ display: flex; gap: 26px; align-items: flex-end; height: 330px; margin-top: 28px; }}
.b {{ flex: 1; height: 100%; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; gap: 10px; }}
.b i, .b span, .b em {{ flex-shrink: 0; }}
.b span {{ font-family: "PT Sans Narrow"; font-weight: 700; font-size: 40px; }}
.b i {{ display: block; width: 100%; border: 2px solid var(--ink); background: repeating-linear-gradient(135deg, var(--quiet) 0 10px, var(--paper) 10px 20px); }}
.b em {{ font-style: normal; font-size: 28px; color: var(--ink2); }}
.row {{ display: grid; grid-template-columns: repeat(3, 1fr); margin-top: 26px; font-size: 30px; color: var(--ink2); border-top: 1px solid var(--ink); padding-top: 22px; }}
.row div:nth-child(2) {{ text-align: center; }} .row div:nth-child(3) {{ text-align: right; }}
.row b {{ display: block; font-family: "PT Sans Narrow"; font-size: 64px; color: var(--ink); line-height: 1; }}
</style>
<div class="card">
  <div><div class="eyebrow">Сезон 2026</div><h1>Нас стало<br>в 3,8 раза больше</h1></div>
  <div>
    <div class="hero"><div class="big">1 793</div><p>гонщика вышли на старт этапов серии в 2026 году</p></div>
    <div class="bars">{bars}</div>
    <div class="row"><div><b>2 730</b>стартов</div><div><b>7</b>этапов</div><div><b>2</b>региона</div></div>
  </div>
  {FOOT}
</div>""")


def card_km() -> str:
    laps = KM_2026 / 40_075
    return page(f"""
<style>
.km .big {{ font-size: 200px; color: var(--acc); letter-spacing: -.02em; white-space: nowrap; }}
.km .big small {{ font-size: 110px; }}
.km p {{ font-size: 46px; line-height: 1.15; margin-top: 14px; }}
.earth {{ display: flex; justify-content: space-between; margin: 44px 0 10px; }}
.earth i {{ width: 132px; height: 132px; border-radius: 50%; border: 5px solid var(--ink); display: block; position: relative; background: var(--paper); }}
.earth i::after {{ content: ""; position: absolute; inset: 26px 8px; border-top: 3px solid var(--ink); border-bottom: 3px solid var(--ink); border-radius: 50%; opacity: .5; }}
.earth i.part {{ border-style: dashed; opacity: .45; }}
.facts {{ display: grid; grid-template-columns: 1fr 1fr; gap: 30px 48px; margin-top: 64px; }}
.facts div {{ font-size: 32px; color: var(--ink2); line-height: 1.25; border-left: 6px solid var(--ink); padding-left: 22px; }}
.facts b {{ display: block; font-family: "PT Sans Narrow"; font-size: 110px; color: var(--ink); line-height: 1; margin-bottom: 6px; }}
</style>
<div class="card">
  <div><div class="eyebrow">Сезон 2026</div><h1>Вместе — шесть раз<br>вокруг Земли</h1></div>
  <div class="km">
    <div class="big">249 000 <small>км</small></div>
    <p>проехали все финишёры этапов серии за сезон</p>
    <div class="earth">{'<i></i>' * int(laps)}</div>
    <div class="facts">
      <div><b>689</b>гонщиков вернулись после сезона 2025</div>
      <div><b>{WOMEN_2026}</b>женщин на старте — в 4 раза больше, чем в 2023</div>
    </div>
  </div>
  {FOOT}
</div>""")


def card_map() -> str:
    rows = "".join(
        f'<li><span class="d">{d}</span><i class="{r}"></i>'
        f'<span class="n">{name}{" <em>вне зачёта</em>" if name == "Покрова" else ""}</span><span class="p">{n}</span></li>'
        for d, name, r, _, _, n in STAGES)
    return page(f"""
<style>
ul {{ list-style: none; display: grid; gap: 0; border-top: 2px solid var(--line); }}
li {{ display: grid; grid-template-columns: 120px 30px 1fr auto; gap: 18px; align-items: center; padding: 20px 0; border-bottom: 1px solid var(--line); }}
li .d {{ font-family: "PT Sans Narrow"; letter-spacing: .08em; font-size: 32px; color: var(--ink3); }}
li i {{ width: 26px; height: 26px; border-radius: 50%; display: block; border: 4px solid var(--ink); }}
li i.nw {{ background: var(--ink); }} li i.c {{ background: var(--paper); }}
ul {{ background: var(--paper); border: 2px solid var(--ink) !important; padding: 0 28px; }}
li:last-child {{ border-bottom: 0 !important; }}
li .n {{ font-family: "PT Sans Narrow"; font-weight: 700; font-size: 50px; text-transform: uppercase; line-height: 1; }}
li .n em {{ font-family: "PT Sans"; font-weight: 400; font-style: normal; text-transform: none; font-size: 24px; color: var(--ink3); margin-left: 10px; vertical-align: middle; }}
li .p {{ font-family: "PT Sans Narrow"; font-weight: 700; font-size: 44px; color: var(--ink); }}
.legend {{ display: flex; flex-wrap: wrap; gap: 14px 34px; font-size: 28px; color: var(--ink2); margin-top: 30px; }}
.legend i {{ display: inline-block; width: 20px; height: 20px; border-radius: 50%; margin-right: 10px; vertical-align: -2px; }}
</style>
<div class="card">
  <div><div class="eyebrow">Сезон 2026</div><h1>Семь гонок<br>за одно лето</h1></div>
  <div>
    <ul>{rows}</ul>
    <div class="legend"><span><i style="background:var(--ink);border:3px solid var(--ink)"></i>под Петербургом и Новгородом</span><span><i style="background:var(--paper);border:3px solid var(--ink)"></i>в центре России</span><span>число — участников на старте</span></div>
  </div>
  {FOOT}
</div>""")


def main() -> None:
    for name, html in [("01_growth", card_growth()), ("02_km", card_km()), ("03_calendar", card_map())]:
        src = OUT / f"{name}.html"
        src.write_text(html, encoding="utf-8")
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1080,1350",
                        f"--screenshot={OUT / (name + '.png')}", f"file://{src}"], capture_output=True)
        print(name, (OUT / f"{name}.png").exists())


if __name__ == "__main__":
    main()
