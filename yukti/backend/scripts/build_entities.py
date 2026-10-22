"""Builds `app/semantic/entities.json` (B1.2): the single entity dictionary source.

Reads the dimension tables (READ-ONLY SELECTs) and writes code -> attributes for
work centres, disciplines, fields and grades. Curated aliases (Hindi/Hinglish,
colloquial names, regions) live in `app/semantic/entity_aliases.yaml` and are
merged at load time by `app/semantic/entities.py`, so re-running this script never
drops hand-written aliases.

Usage (from yukti/backend): .venv/bin/python scripts/build_entities.py
"""

import datetime
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.cloud import bigquery  # noqa: E402

from app.config import BQ_LOCATION, GCP_PROJECT, JOB_LABELS  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "app" / "semantic" / "entities.json"


def _rows(client: bigquery.Client, sql: str):
    cfg = bigquery.QueryJobConfig(labels=JOB_LABELS, maximum_bytes_billed=500_000_000)
    return [dict(r) for r in client.query(sql, job_config=cfg).result()]


def _clean(d):
    out = {}
    for k, v in d.items():
        if v is None:
            continue
        if hasattr(v, "isoformat"):
            v = v.isoformat()
        elif not isinstance(v, (str, int, float, bool, list)):
            v = str(v)
        out[k] = v
    return out


def main() -> None:
    c = bigquery.Client(project=GCP_PROJECT, location=BQ_LOCATION)
    wcs = _rows(c, "SELECT wc_id, name, short_name, city, state, sector, cluster_id, hard_station_cat, "
                   "onshore_offshore, type FROM `%s.hrfin_silver.dim_work_centre` ORDER BY wc_id" % GCP_PROJECT)
    discs = _rows(c, "SELECT discipline_id, code, name, function FROM `%s.hrfin_silver.dim_discipline` "
                     "ORDER BY discipline_id" % GCP_PROJECT)
    grades = _rows(c, "SELECT grade_id, cadre, designation, level_order FROM `%s.hrfin_silver.dim_grade` "
                      "ORDER BY level_order" % GCP_PROJECT)
    fields = _rows(c, "SELECT field_id, ANY_VALUE(field_name) AS name, ANY_VALUE(asset_wc_id) AS asset_wc_id, "
                      "ANY_VALUE(basin) AS basin, ANY_VALUE(onshore_offshore) AS onshore_offshore "
                      "FROM `%s.hrfin_gold.ssot_field_economics_360` WHERE field_id IS NOT NULL "
                      "GROUP BY field_id ORDER BY field_id" % GCP_PROJECT)
    payload = {
        "version": 1,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "source": {"work_centres": "hrfin_silver.dim_work_centre", "disciplines": "hrfin_silver.dim_discipline",
                   "grades": "hrfin_silver.dim_grade", "fields": "hrfin_gold.ssot_field_economics_360"},
        "work_centres": {r["wc_id"]: _clean({k: v for k, v in r.items() if k != "wc_id"}) for r in wcs},
        "disciplines": {r["discipline_id"]: _clean({k: v for k, v in r.items() if k != "discipline_id"}) for r in discs},
        "grades": {r["grade_id"]: _clean({k: v for k, v in r.items() if k != "grade_id"}) for r in grades},
        "fields": {r["field_id"]: _clean({k: v for k, v in r.items() if k != "field_id"}) for r in fields},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT}: {len(wcs)} work centres, {len(discs)} disciplines, {len(grades)} grades, {len(fields)} fields")


if __name__ == "__main__":
    main()
