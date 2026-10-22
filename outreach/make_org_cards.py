"""Инфографика для сообщения организаторам РГС — в чёрно-белом стиле сайта gravelseries.ru.

Запуск: uv run python outreach/make_org_cards.py
"""
import subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
:root { --paper: #f5f5f3; --bg: #ffffff; --ink: #000000; --soft: #444444; --muted: #74746f; --quiet: #c9c9c4; }
html, body { width: 1080px; height: 1350px; background: var(--paper); color: var(--ink); font-family: "PT Sans", Arial, sans-serif; }
.card { width: 1080px; height: 1350px; padding: 64px 72px 48px; display: grid; grid-template-rows: auto 1fr auto; gap: 34px; }
.eyebrow { font-family: "PT Sans Narrow", "PT Sans", sans-serif; font-size: 26px; letter-spacing: .14em; text-transform: uppercase; color: var(--muted); }
h1 { font-family: "PT Sans Narrow", "PT Sans", sans-serif; font-weight: 700; text-transform: uppercase; font-size: 84px; line-height: .92; margin-top: 14px; }
.lede { font-size: 29px; line-height: 1.3; color: var(--soft); margin-top: 22px; max-width: 900px; }
.box { background: var(--bg); border: 2px solid var(--ink); padding: 32px 36px; }
.idea { border: 2px solid var(--ink); background: var(--ink); color: var(--bg); padding: 24px 32px; font-size: 27px; line-height: 1.3; }
.idea b { font-family: "PT Sans Narrow", sans-serif; text-transform: uppercase; letter-spacing: .08em; font-size: 26px; display: block; margin-bottom: 8px; color: #b6b6b0; }
.foot { display: flex; justify-content: space-between; align-items: end; border-top: 2px solid var(--ink); padding-top: 20px; font-size: 22px; color: var(--muted); }
.foot b { white-space: nowrap; font-family: "PT Sans Narrow", sans-serif; font-size: 30px; text-transform: uppercase; color: var(--ink); letter-spacing: .02em; }
"""

FOOT = '<div class="foot"><b>Русская гравийная серия</b><span>github.com/oiltsar/rgs-gravel-analytics</span></div>'


def page(body: str, extra: str = "") -> str:
    return f'<!doctype html><html lang="ru"><head><meta charset="utf-8"><style>{CSS}{extra}</style></head><body>{body}</body></html>'


def card_second_start() -> str:
    rows = [("1 гонка", 0.40, 1329, False), ("2 гонки", 0.65, 191, True), ("3 и больше", 0.82, 56, True)]
    bars = "".join(
        f'<div class="r"><div class="l">{label}<small>{n:,} чел.</small></div>'
        f'<div class="t"><div class="f {"on" if on else ""}" style="width:{v * 100:.0f}%"><span>{v:.0%}</span></div></div></div>'.replace(",", " ")
        for label, v, n, on in rows)
    extra = """
.r { display: grid; grid-template-columns: 210px 1fr; gap: 24px; align-items: center; margin-bottom: 26px; }
.l { font-family: "PT Sans Narrow"; font-weight: 700; font-size: 40px; text-transform: uppercase; line-height: 1; }
.l small { display: block; font-family: "PT Sans"; font-weight: 400; text-transform: none; font-size: 22px; color: var(--muted); margin-top: 6px; }
.t { height: 84px; border: 2px solid var(--ink); background: var(--bg); }
.f { height: 100%; background: repeating-linear-gradient(135deg, var(--quiet) 0 10px, var(--bg) 10px 20px); border-right: 2px solid var(--ink);
     display: flex; align-items: center; justify-content: flex-end; padding-right: 18px; }
.f.on { background: var(--ink); }
.f span { font-family: "PT Sans Narrow"; font-weight: 700; font-size: 64px; color: var(--ink); background: var(--bg); padding: 0 10px; }
.f.on span { color: var(--bg); background: transparent; }
.axis { display: flex; justify-content: space-between; margin-left: 234px; font-size: 22px; color: var(--muted); }
.note { font-size: 26px; color: var(--soft); margin-top: 26px; line-height: 1.35; }
"""
    return page(f"""
<div class="card">
  <div>
    <div class="eyebrow">Удержание новичков · 2023–2025</div>
    <h1>Вторая гонка<br>в первом сезоне</h1>
    <p class="lede">Сколько новичков вернулось на следующий год — в зависимости от того, сколько гонок серии они проехали в свой первый сезон.</p>
  </div>
  <div>
    <div class="box">
      {bars}
      <div class="axis"><span>0%</span><span>50%</span><span>100%</span></div>
      <p class="note">1 576 новичков. Эффект сохраняется с поправкой на год и на этап, с которого человек пришёл: шансы вернуться выше в 2,7–2,9 раза.</p>
    </div>
    <div class="idea" style="margin-top:22px"><b>Идея</b>Промокод на следующий этап своего региона для финишёров первой гонки — и проверить на половине новичков.</div>
  </div>
  {FOOT}
</div>""", extra)


def card_regions() -> str:
    rows = [("Гонщиков, 2026", "920", "225", "648"), ("В полном зачёте<br><small>4+ рейтинговые гонки</small>", "29", "48", "0")]
    body = "".join(f'<tr{" class=\'hl\'" if i == 1 else ""}><td class="k">{k}</td><td>{a}</td><td>{b}</td><td>{c}</td></tr>'
                   for i, (k, a, b, c) in enumerate(rows))
    extra = """
table { width: 100%; border-collapse: collapse; }
th { font-family: "PT Sans Narrow"; font-size: 24px; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); font-weight: 400;
     text-align: right; padding: 0 0 16px; border-bottom: 2px solid var(--ink); line-height: 1.15; vertical-align: bottom; }
th:first-child { text-align: left; }
td { font-family: "PT Sans Narrow"; font-weight: 700; font-size: 96px; text-align: right; padding: 26px 0; border-bottom: 1px solid var(--ink); line-height: 1; }
td.k { font-family: "PT Sans"; font-weight: 400; font-size: 30px; text-align: left; color: var(--ink); line-height: 1.2; }
td.k small { font-size: 21px; color: var(--muted); }
tr.hl td { background: var(--ink); color: var(--bg); }
tr.hl td.k { color: var(--bg); padding-left: 16px; }
tr.hl td:last-child { padding-right: 16px; }
tr:last-child td { border-bottom: 0; }
"""
    return page(f"""
<div class="card">
  <div>
    <div class="eyebrow">Регионы и общий зачёт · 2026</div>
    <h1>Только Центр —<br>ноль в зачёте</h1>
    <p class="lede">Полный зачёт — 4 рейтинговые гонки. Под Петербургом рейтинговых этапов четыре, в Центре два (Покрова в 2026 году вне рейтинга).</p>
  </div>
  <div>
    <div class="box">
      <table><tr><th></th><th>Только<br>Северо-Запад</th><th>Оба<br>региона</th><th>Только<br>Центр</th></tr>{body}</table>
    </div>
    <div class="idea" style="margin-top:22px"><b>Идея</b>Региональные зачёты «Север» и «Центр» с порогом 2 этапа и вернуть Покрову в рейтинг: в борьбе окажутся 143 гонщика в «Центре» и 356 в «Севере».</div>
  </div>
  {FOOT}
</div>""", extra)


def main() -> None:
    for name, html in [("org_01_second_start", card_second_start()), ("org_02_regions", card_regions())]:
        src = OUT / f"{name}.html"
        src.write_text(html, encoding="utf-8")
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1080,1350",
                        f"--screenshot={OUT / (name + '.png')}", f"file://{src}"], capture_output=True)
        print(name, (OUT / f"{name}.png").exists())


if __name__ == "__main__":
    main()
