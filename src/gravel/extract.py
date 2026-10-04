"""Extract: выгрузка сырых данных из открытого API gravelseries.ru.

Источники:
  /results/data.json                 — архив протоколов 2018–2026 (все гонки, все строки)
  /api/events                        — календарь текущего сезона
  /api/series/{year}/rankings        — рейтинг сезона с ID гонщиков (для валидации матчинга)

Сырые ответы сохраняются как есть в data/raw/ — пайплайн воспроизводим и не долбит сайт повторно.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests

BASE = "https://gravelseries.ru"
RAW = Path(__file__).resolve().parents[2] / "data" / "raw"
HEADERS = {"User-Agent": "gravel-analytics pet project (portfolio, non-commercial)"}
RANKING_SEASONS = (2024, 2025, 2026)


def _get(path: str, params: dict | None = None) -> dict | list:
    resp = requests.get(f"{BASE}{path}", params=params, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    time.sleep(0.5)  # вежливая пауза между запросами
    return resp.json()


def _save(name: str, payload) -> Path:
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def main(force: bool = False) -> None:
    targets = {
        "results.json": ("/results/data.json", None),
        "events.json": ("/api/events", None),
    }
    for season in RANKING_SEASONS:
        targets[f"rankings_{season}.json"] = (
            f"/api/series/{season}/rankings",
            {"gender": "all", "kind": "main", "best": "all", "limit": 5000},
        )

    for name, (path, params) in targets.items():
        if (RAW / name).exists() and not force:
            print(f"skip  {name} (уже скачан, --force для обновления)")
            continue
        print(f"fetch {name} <- {path}")
        _save(name, _get(path, params))


if __name__ == "__main__":
    import sys

    main(force="--force" in sys.argv)
