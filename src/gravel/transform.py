"""Transform: сырые протоколы -> чистые таблицы (parquet) в звёздной схеме.

  dim_event   — этап серии в конкретный год
  dim_race    — дистанция внутри этапа (км, «длинная/короткая», класс велосипеда)
  dim_rider   — гонщик после сведения дублей имён (entity resolution)
  fct_result  — одна строка = один старт гонщика

Основные проблемы сырых данных и как они решаются:
  * имена в разном порядке и регистре («ЦАРЕВ СЕРГЕЙ», «Сергей Царев»), ё/е, двойные фамилии
    -> ключ = отсортированные токены в нижнем регистре; фамилия в скобках даёт алиас
  * 6 форматов времени («4:15:39», «03:28:43.32», «5:03:49,55», «-», «?»)
  * пустой статус: с очками -> финиш без времени, без очков -> сход
  * дистанция в км указана не везде -> парсим из названия, иначе NaN + уровень long/short из maxPoints
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"

# Единые названия этапов (slug в архиве -> человекочитаемое имя)
EVENT_NAMES = {
    "gravelking": "Gravel King",
    "reverse-side": "Обратная сторона",
    "sport-marafon-fest": "Спортмарафон Фест",
    "shulz-gravel-weekend": "SHULZ Gravel Weekend",
    "tsar-grader": "Царь Грейдер",
    "gravel-instinct": "Gravel Instinct",
    "modder": "Моддер / Ардор",
    "ardor": "Моддер / Ардор",
    "pokrova": "Покрова",
    "fury-road": "Fury Road",
    "redline": "Redline",
}
# «Моддер» и «Ардор» — одна и та же гонка под разными именами (в 2026 на сайте: modder-ardor)
EVENT_SERIES_KEY = {"modder": "modder-ardor", "ardor": "modder-ardor"}

STATUS_MAP = {"FINISHED": "finished", "DNF": "dnf", "DNS": "dns", "DSQ": "dsq"}


# ---------------------------------------------------------------- helpers
def parse_time(raw: str | None) -> float:
    """'4:15:39' | '03:28:43.32' | '5:03:49,55' -> секунды; мусор -> NaN."""
    if not raw:
        return np.nan
    m = re.fullmatch(r"(\d{1,2}):(\d{2}):(\d{2})(?:[.,](\d+))?", raw.strip())
    if not m:
        return np.nan
    h, mi, s, frac = m.groups()
    return int(h) * 3600 + int(mi) * 60 + int(s) + (float(f"0.{frac}") if frac else 0.0)


def parse_distance_km(race_id: str, title: str) -> float:
    for text in (title, race_id):
        m = re.search(r"(\d{2,3})\s*км", text) or re.search(r"BIKE\s+(\d{2,3})", text)
        if m:
            return float(m.group(1))
    if re.fullmatch(r"\d{2,3}", race_id):
        return float(race_id)
    return np.nan


def bike_class(title: str, race_id: str) -> str:
    t = f"{title} {race_id}".lower()
    if "фикс" in t or "fixed" in t:
        return "fixed"
    return "multi"


_PARENS = re.compile(r"\(([^)]*)\)")
_PATRONYMIC = re.compile(r".+(ович|евич|ьич|овна|евна|ична)$")
# уменьшительные -> полные имена (в протоколах один человек бывает и «Дима», и «Дмитрий»)
NICKNAMES = {
    "саша": "александр", "дима": "дмитрий", "гоша": "георгий", "женя": "евгений",
    "леша": "алексей", "алеша": "алексей", "сережа": "сергей", "миша": "михаил",
    "коля": "николай", "андрюша": "андрей", "паша": "павел", "вова": "владимир",
    "володя": "владимир", "костя": "константин", "катя": "екатерина", "настя": "анастасия",
    "маша": "мария", "оля": "ольга", "лена": "елена", "таня": "татьяна", "юля": "юлия",
    "ваня": "иван", "петя": "петр", "слава": "вячеслав", "витя": "виктор", "толя": "анатолий",
    "антоша": "антон", "никита": "никита", "даша": "дарья", "наташа": "наталья",
}


def name_tokens(name: str) -> list[str]:
    s = name.lower().replace("ё", "е")
    s = re.sub(r"[^a-zа-я\s()-]", " ", s)
    tokens = [t for t in s.split() if t]
    if len(tokens) == 3:  # «Фамилия Имя Отчество» / «Имя Отчество Фамилия» -> без отчества
        for i in (2, 1):  # отчество никогда не стоит первым (а «-вич» бывает и у фамилий)
            if _PATRONYMIC.fullmatch(tokens[i]):
                tokens.pop(i)
                break
    return [NICKNAMES.get(t, t) for t in tokens]


def name_keys(name: str) -> tuple[str, list[str]]:
    """Основной ключ + алиасы. «Бегак (Голобородько) Александра» ->
    key='александра бегак', aliases=['александра голобородько']."""
    base = _PARENS.sub(" ", name)
    tokens = name_tokens(base)
    key = " ".join(sorted(tokens))
    aliases = []
    for inner in _PARENS.findall(name):
        alt = name_tokens(inner)
        if alt and len(tokens) >= 2:
            # фамилия в скобках заменяет первый токен (порядок «Фамилия (Девичья) Имя»)
            first_name = [t for t in tokens if t != name_tokens(base)[0]]
            aliases.append(" ".join(sorted(alt + first_name)))
    return key, aliases


def title_case(name: str) -> str:
    return " ".join(p.capitalize() if p.isupper() or p.islower() else p for p in name.split())


# ---------------------------------------------------------------- build
def build() -> dict[str, pd.DataFrame]:
    archive = json.loads((RAW / "results.json").read_text(encoding="utf-8"))

    events, races, rows = [], [], []
    for ev in archive["events"]:
        event_id = f"{ev['slug']}-{ev['year']}"
        events.append({
            "event_id": event_id,
            "slug": ev["slug"],
            "series_key": EVENT_SERIES_KEY.get(ev["slug"], ev["slug"]),
            "event_name": EVENT_NAMES.get(ev["slug"], ev["title"]),
            "year": ev["year"],
            "start_date": pd.to_datetime(ev["startDate"]) if ev["startDate"] else pd.NaT,
            "source_url": ev["sourceUrl"],
        })
        for r in ev["races"]:
            race_id = f"{event_id}/{r['id']}"
            races.append({
                "race_id": race_id,
                "event_id": event_id,
                "race_title": r["title"],
                "distance_km": parse_distance_km(r["id"], r["title"]),
                "max_points": r["maxPoints"],
                "is_long": r["maxPoints"] == 1000,
                "bike_class": bike_class(r["title"], r["id"]),
                "place_kind": r["placeKind"],
            })
            for x in r["rows"]:
                rows.append({"race_id": race_id, "event_id": event_id, "year": ev["year"], **x})

    dim_event = pd.DataFrame(events)
    dim_race = pd.DataFrame(races)
    raw = pd.DataFrame(rows)

    # --- статус
    status = raw["status"].map(STATUS_MAP)
    empty = raw["status"].eq("")
    status = status.mask(empty & raw["points"].notna(), "finished")
    status = status.mask(empty & raw["points"].isna(), "dnf")
    raw["status"] = status

    # --- время, пол
    raw["time_s"] = raw["time"].map(parse_time)
    raw.loc[raw["status"] != "finished", "time_s"] = np.nan
    raw["gender"] = raw["gender"].map({"М": "M", "Ж": "F"})

    # --- entity resolution
    keys = raw["name"].map(name_keys)
    raw["name_key"] = keys.str[0]
    alias_to_key = {}
    for key, aliases in keys:
        for a in aliases:
            alias_to_key[a] = key
    raw["name_key"] = raw["name_key"].replace(alias_to_key)
    # пол, если пропущен — берём у того же гонщика из других стартов
    g = raw.groupby("name_key")["gender"].agg(lambda s: s.mode().iat[0] if s.notna().any() else None)
    raw["gender"] = raw["gender"].fillna(raw["name_key"].map(g))

    rider_ids = {k: f"R{i:05d}" for i, k in enumerate(sorted(raw["name_key"].unique()), start=1)}
    raw["rider_id"] = raw["name_key"].map(rider_ids)

    # --- позиция внутри гонки: перцентиль среди финишёров своего пола (0 = победитель, 1 = последний)
    fin = raw["status"].eq("finished")
    raw["finishers_in_group"] = raw[fin].groupby(["race_id", "gender"])["race_id"].transform("size")
    raw["place_in_group"] = raw[fin].groupby(["race_id", "gender"])["time_s"].rank(method="min")
    # где времени нет — используем place из протокола
    no_time = fin & raw["place_in_group"].isna()
    raw.loc[no_time, "place_in_group"] = raw[no_time].groupby(["race_id", "gender"])["place"].rank(method="min")
    raw["pct_rank"] = (raw["place_in_group"] - 1) / (raw["finishers_in_group"] - 1).replace(0, np.nan)

    # --- скорость там, где известна дистанция
    raw = raw.merge(dim_race[["race_id", "distance_km"]], on="race_id", how="left")
    raw["speed_kmh"] = raw["distance_km"] / (raw["time_s"] / 3600)
    raw.loc[~raw["speed_kmh"].between(8, 50), "speed_kmh"] = np.nan  # отсекаем ошибки протоколов

    fct_result = raw.reset_index(drop=True)
    fct_result.insert(0, "result_id", np.arange(1, len(fct_result) + 1))
    fct_result = fct_result[[
        "result_id", "rider_id", "race_id", "event_id", "year", "name", "gender", "bib", "team",
        "category", "status", "place", "points", "time_s", "speed_kmh",
        "place_in_group", "finishers_in_group", "pct_rank",
    ]].rename(columns={"name": "name_raw"})

    # --- dim_rider
    display = (fct_result.groupby("rider_id")["name_raw"]
               .agg(lambda s: title_case(s.value_counts().index[0])))
    dim_rider = (fct_result.groupby("rider_id")
                 .agg(gender=("gender", lambda s: s.mode().iat[0] if s.notna().any() else None),
                      first_year=("year", "min"), last_year=("year", "max"),
                      starts=("result_id", "size"),
                      finishes=("status", lambda s: (s == "finished").sum()),
                      seasons=("year", "nunique"))
                 .join(display.rename("display_name"))
                 .reset_index())
    dim_rider["name_key"] = dim_rider["rider_id"].map({v: k for k, v in rider_ids.items()})

    return {"dim_event": dim_event, "dim_race": dim_race, "dim_rider": dim_rider, "fct_result": fct_result}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, df in build().items():
        df.to_parquet(OUT / f"{name}.parquet", index=False)
        print(f"{name:<11} {len(df):>6} rows")


if __name__ == "__main__":
    main()
