"""Собирает dashboard/index.html: агрегаты из DuckDB встраиваются в шаблон dashboard/template.html.

На страницу попадают только агрегаты — без имён гонщиков.
"""
from __future__ import annotations

import json
from pathlib import Path

from gravel.load import connect

ROOT = Path(__file__).resolve().parents[2]
DASH = ROOT / "dashboard"

NEWBIES_SQL = """
WITH act AS (
    SELECT r.*, d.is_long FROM fct_result r JOIN dim_race d ON d.race_id = r.race_id
    WHERE r.status <> 'dns'
),
first AS (SELECT rider_id, MIN(year) AS fy FROM act GROUP BY 1),
fs AS (
    SELECT a.rider_id, f.fy, ANY_VALUE(a.gender) AS gender, COUNT(*) AS starts,
           BOOL_OR(a.is_long) AS any_long, MEDIAN(a.pct_rank) AS med_pct,
           ARG_MIN(a.event_id, a.result_id) AS first_event
    FROM act a JOIN first f ON f.rider_id = a.rider_id AND a.year = f.fy
    GROUP BY 1, 2
),
ret AS (SELECT DISTINCT rider_id, year FROM act)
SELECT fs.*, (r.rider_id IS NOT NULL)::INT AS returned
FROM fs LEFT JOIN ret r ON r.rider_id = fs.rider_id AND r.year = fs.fy + 1
WHERE fy BETWEEN 2022 AND 2025
"""


def records(df):
    return json.loads(df.to_json(orient="records", force_ascii=False))


def build() -> dict:
    con = connect()
    q = lambda s: con.sql(s).df()

    season = q("SELECT * FROM mart_season ORDER BY year")
    cohort = q("SELECT cohort, season_n, riders, retention FROM mart_cohort WHERE cohort BETWEEN 2019 AND 2025")

    nb = q(NEWBIES_SQL)
    nb["starts_cat"] = nb["starts"].clip(upper=3).map({1: "1", 2: "2", 3: "3+"})
    nb["dist"] = nb["any_long"].map({False: "короткая", True: "длинная"})
    nb["quart"] = (nb["med_pct"] // 0.25).clip(upper=3).map({0: "топ-25%", 1: "25–50%", 2: "50–75%", 3: "хвост"})
    nb["sex"] = nb["gender"].map({"F": "женщины", "M": "мужчины"})

    def rate(col, order):
        g = nb.groupby(col)["returned"].agg(["mean", "size"]).reindex(order)
        return [{"label": k, "rate": round(float(r["mean"]), 4), "n": int(r["size"])} for k, r in g.iterrows()]

    aha = {
        "base": round(float(nb["returned"].mean()), 4),
        "n": int(len(nb)),
        "panels": [
            {"title": "Стартов в первом сезоне", "bars": rate("starts_cat", ["1", "2", "3+"])},
            {"title": "Первая дистанция", "bars": rate("dist", ["короткая", "длинная"])},
            {"title": "Квартиль места", "bars": rate("quart", ["топ-25%", "25–50%", "50–75%", "хвост"])},
            {"title": "Пол", "bars": rate("sex", ["женщины", "мужчины"])},
        ],
    }

    names = q("SELECT event_id, event_name FROM dim_event")
    entry = nb[nb.fy >= 2023].merge(names, left_on="first_event", right_on="event_id")
    eg = entry.groupby("event_name")["returned"].agg(["mean", "size"]).query("size >= 40").sort_values("mean", ascending=False)
    entry_points = {
        "base": round(float(entry["returned"].mean()), 4),
        "rows": [{"event": k, "rate": round(float(r["mean"]), 4), "n": int(r["size"])} for k, r in eg.iterrows()],
    }

    overlap = q("SELECT event_a, event_b, shared_riders, share_of_a FROM mart_event_overlap WHERE year = 2026")
    sizes = q("""SELECT e.event_name AS event, COUNT(DISTINCT r.rider_id) AS riders
                 FROM fct_result r JOIN dim_event e ON e.event_id = r.event_id
                 WHERE r.year = 2026 AND r.status <> 'dns' GROUP BY 1 ORDER BY 2 DESC""")

    speed = q("""
        SELECT e.event_name AS event, d.race_title AS race, d.distance_km AS km,
               COUNT(*) AS n,
               QUANTILE_CONT(r.speed_kmh, 0.25) AS q1, MEDIAN(r.speed_kmh) AS med,
               QUANTILE_CONT(r.speed_kmh, 0.75) AS q3, MAX(r.speed_kmh) AS top
        FROM fct_result r JOIN dim_race d ON d.race_id = r.race_id JOIN dim_event e ON e.event_id = r.event_id
        WHERE r.year = 2026 AND r.status = 'finished' AND r.speed_kmh IS NOT NULL AND d.bike_class = 'multi'
        GROUP BY ALL ORDER BY med DESC""").round(2)

    path = q("SELECT * FROM mart_distance_path WHERE first_year BETWEEN 2022 AND 2025 AND NOT first_season_long")
    funnel = [
        {"step": "Первый сезон — только короткая", "n": int(len(path))},
        {"step": "Вернулись в следующем сезоне", "n": int(path.returned_next.sum())},
        {"step": "…и проехали длинную", "n": int(path.long_next.sum())},
    ]

    totals = q("""SELECT (SELECT COUNT(*) FROM fct_result) AS results,
                         (SELECT COUNT(*) FROM dim_rider) AS riders,
                         (SELECT COUNT(*) FROM dim_event) AS events""")

    return {
        "season": records(season), "cohort": records(cohort), "aha": aha,
        "entry": entry_points, "overlap": records(overlap), "eventSizes": records(sizes),
        "speed": records(speed), "funnel": funnel, "totals": records(totals)[0],
    }


def main() -> None:
    data = build()
    (DASH / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    html = (DASH / "template.html").read_text(encoding="utf-8")
    html = html.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False))
    (DASH / "index.html").write_text(html, encoding="utf-8")
    print("dashboard/index.html written")


if __name__ == "__main__":
    main()
