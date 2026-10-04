-- Витрины для анализа. Строятся поверх parquet из data/processed (см. src/gravel/load.py).
-- Логика «серия = продукт, гонщик = пользователь, старт = сессия».

-- 1. Сезонные метрики: аудитория, новички, возвраты, доля женщин -----------------------
CREATE OR REPLACE VIEW mart_season AS
WITH rider_year AS (
    SELECT r.rider_id, r.year, d.gender, d.first_year,
           COUNT(*)                         AS starts,
           COUNT(DISTINCT r.event_id)       AS events
    FROM fct_result r JOIN dim_rider d USING (rider_id)
    WHERE r.status <> 'dns'
    GROUP BY ALL
),
prev AS (
    SELECT rider_id, year FROM rider_year
)
SELECT ry.year,
       (SELECT COUNT(*) FROM dim_event e WHERE e.year = ry.year)                AS n_events,
       COUNT(*)                                                                AS riders,
       SUM(starts)                                                             AS starts,
       ROUND(AVG(starts), 2)                                                   AS starts_per_rider,
       SUM((first_year = ry.year)::INT)                                        AS new_riders,
       SUM((p.rider_id IS NOT NULL)::INT)                                      AS retained_from_prev,
       SUM((first_year < ry.year AND p.rider_id IS NULL)::INT)                 AS resurrected,
       ROUND(AVG((gender = 'F')::INT), 3)                                      AS female_share,
       ROUND(AVG((events >= 2)::INT), 3)                                       AS multi_event_share
FROM rider_year ry
LEFT JOIN prev p ON p.rider_id = ry.rider_id AND p.year = ry.year - 1
GROUP BY ry.year
ORDER BY ry.year;

-- 2. Когорты по году первого старта: доля вернувшихся в сезон N --------------------------
CREATE OR REPLACE VIEW mart_cohort AS
WITH active AS (
    SELECT DISTINCT rider_id, year FROM fct_result WHERE status <> 'dns'
),
cohort AS (
    SELECT rider_id, MIN(year) AS cohort FROM active GROUP BY rider_id
),
counts AS (
    SELECT c.cohort, a.year, COUNT(*) AS riders
    FROM active a JOIN cohort c USING (rider_id)
    GROUP BY ALL
)
SELECT cohort, year, year - cohort AS season_n, riders,
       ROUND(riders / FIRST_VALUE(riders) OVER (PARTITION BY cohort ORDER BY year), 3) AS retention
FROM counts
ORDER BY cohort, year;

-- 3. Пересечение аудиторий этапов в сезоне (Жаккар) ------------------------------------
CREATE OR REPLACE VIEW mart_event_overlap AS
WITH a AS (
    SELECT DISTINCT r.year, e.series_key, e.event_name, r.rider_id
    FROM fct_result r JOIN dim_event e USING (event_id)
    WHERE r.status <> 'dns'
),
size AS (SELECT year, series_key, COUNT(*) AS n FROM a GROUP BY ALL),
pairs AS (
    SELECT x.year, x.series_key AS key_a, y.series_key AS key_b,
           ANY_VALUE(x.event_name) AS event_a, ANY_VALUE(y.event_name) AS event_b,
           COUNT(*) AS shared_riders
    FROM a x JOIN a y ON x.year = y.year AND x.rider_id = y.rider_id AND x.series_key <> y.series_key
    GROUP BY ALL
)
SELECT p.year, p.event_a, p.event_b, p.shared_riders,
       na.n AS riders_a,
       ROUND(p.shared_riders / na.n, 3)                          AS share_of_a,  -- доля аудитории A, бывшая и на B
       ROUND(p.shared_riders / (na.n + nb.n - p.shared_riders), 3) AS jaccard
FROM pairs p
JOIN size na ON na.year = p.year AND na.series_key = p.key_a
JOIN size nb ON nb.year = p.year AND nb.series_key = p.key_b;

-- 4. Воронка дистанций: короткая в первом сезоне -> длинная в следующем ----------------
-- Окно наблюдения одинаковое для всех когорт: первый сезон + следующий.
-- «Начал с короткой» = в первом сезоне только короткие дистанции (у старых этапов нет дат,
-- поэтому порядок стартов внутри сезона не определён).
CREATE OR REPLACE VIEW mart_distance_path AS
WITH s AS (
    SELECT r.rider_id, r.year, d.is_long
    FROM fct_result r JOIN dim_race d ON d.race_id = r.race_id
    WHERE r.status <> 'dns'
),
first AS (SELECT rider_id, MIN(year) AS first_year FROM s GROUP BY 1)
SELECT f.rider_id,
       f.first_year,
       BOOL_OR(s.is_long) FILTER (WHERE s.year = f.first_year)          AS first_season_long,
       COUNT(*) FILTER (WHERE s.year = f.first_year)                    AS first_season_starts,
       COUNT(*) FILTER (WHERE s.year = f.first_year + 1) > 0            AS returned_next,
       COALESCE(BOOL_OR(s.is_long) FILTER (WHERE s.year = f.first_year + 1), FALSE) AS long_next
FROM first f JOIN s ON s.rider_id = f.rider_id
GROUP BY ALL;

-- 5. Сходы по гонкам (только протоколы, где DNF/DNS вообще фиксируются) -----------------
CREATE OR REPLACE VIEW mart_dnf AS
SELECT e.event_name, e.year, d.race_title, d.distance_km, d.is_long,
       COUNT(*) FILTER (WHERE status <> 'dns')                               AS starters,
       COUNT(*) FILTER (WHERE status = 'dnf')                                AS dnf,
       ROUND(COUNT(*) FILTER (WHERE status = 'dnf')
             / NULLIF(COUNT(*) FILTER (WHERE status <> 'dns'), 0), 3)        AS dnf_rate,
       ROUND(COUNT(*) FILTER (WHERE status = 'dns') / COUNT(*), 3)           AS dns_rate
FROM fct_result r
JOIN dim_race d ON d.race_id = r.race_id
JOIN dim_event e ON e.event_id = r.event_id
GROUP BY ALL
HAVING COUNT(*) FILTER (WHERE status IN ('dnf', 'dns')) > 0;

-- 6. Прогресс вернувшихся: перцентиль места в соседних сезонах (длинные дистанции) -----
CREATE OR REPLACE VIEW mart_progress AS
WITH best AS (
    SELECT r.rider_id, r.year, MIN(r.pct_rank) AS best_pct, MEDIAN(r.pct_rank) AS med_pct
    FROM fct_result r JOIN dim_race d USING (race_id)
    WHERE r.status = 'finished' AND d.is_long AND r.pct_rank IS NOT NULL
    GROUP BY ALL
)
SELECT a.rider_id, a.year AS year_from, b.year AS year_to,
       a.med_pct AS pct_from, b.med_pct AS pct_to,
       b.med_pct - a.med_pct AS delta   -- < 0 = стал быстрее относительно поля
FROM best a JOIN best b ON a.rider_id = b.rider_id AND b.year = a.year + 1;
