"""Build market_prices_seed.csv from official NSE March bhavcopies in knowledge/public_sources/market_data/nse/.

For each fiscal year (FY17-FY26), selects the last NSE trading day of March present on disk,
extracts the ONGC EQ series close price, and writes knowledge/public_sources/market_data/manual/market_prices_seed.csv
with full bhavcopy file name, URL, and sha256 lineage from _fetch_manifest.csv.
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import Any

from financial_ssot.extract.market_provider import (
    MANUAL_SEED,
    NSE_DIR,
    NSE_MANIFEST,
    SEED_COLUMNS,
    parse_bhavcopy,
)


def build_market_prices_seed(
    nse_dir: Path = NSE_DIR,
    manifest_csv: Path = NSE_MANIFEST,
    out_csv: Path = MANUAL_SEED,
) -> list[dict[str, Any]]:
    """Extract last March trading day ONGC EQ close per FY (FY17-FY26) and write market_prices_seed.csv."""
    nse_dir = Path(nse_dir)
    manifest_csv = Path(manifest_csv)
    out_csv = Path(out_csv)

    manifest_by_file: dict[str, dict[str, str]] = {}
    if manifest_csv.exists():
        with open(manifest_csv, "r", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                fname = (row.get("file") or "").strip()
                if fname:
                    manifest_by_file[fname] = {k: (v or "").strip() for k, v in row.items() if k}

    by_fy: dict[str, dict[str, Any]] = {}
    for path in sorted(nse_dir.iterdir()):
        name = path.name
        if not ((name.startswith("cm") and "bhav" in name) or name.startswith("BhavCopy_NSE_CM_")):
            continue
        for row in parse_bhavcopy(path):
            if row.get("ticker") != "ONGC.NS":
                continue
            dt = str(row.get("date") or "")
            if len(dt) != 10 or dt[5:7] != "03":
                continue
            yr = int(dt[:4])
            if not (2017 <= yr <= 2026):
                continue
            fy = f"FY{str(yr)[2:]}"
            if fy not in by_fy or dt > by_fy[fy]["date"]:
                m_row = manifest_by_file.get(name, {})
                actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
                sha256 = m_row.get("sha256") or actual_sha
                if m_row.get("sha256") and m_row["sha256"] != actual_sha:
                    raise ValueError(f"SHA256 mismatch for {name}: manifest={m_row['sha256']} vs actual={actual_sha}")
                url = m_row.get("url") or ""
                fetched_utc = m_row.get("fetched_utc") or ""
                by_fy[fy] = {
                    "fiscal_year": fy,
                    "ticker": "ONGC.NS",
                    "date": dt,
                    "close": row["close"],
                    "adj_close": "",
                    "file": name,
                    "sha256": sha256,
                    "source_url": url,
                    "retrieved_by": f"financial_ssot.wacc.build_market_seed (file={name}; sha256={sha256})",
                    "retrieved_at": fetched_utc,
                }

    seed_rows: list[dict[str, Any]] = [by_fy[fy] for fy in sorted(by_fy.keys())]

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=SEED_COLUMNS)
        writer.writeheader()
        for r in seed_rows:
            writer.writerow({col: r[col] for col in SEED_COLUMNS})

    return seed_rows


def main() -> None:
    rows = build_market_prices_seed()
    print(f"Wrote {len(rows)} FY-end ONGC.NS rows to {MANUAL_SEED}:")
    for r in rows:
        print(f"  {r['fiscal_year']}: date={r['date']} close={r['close']} file={r['file']}")


if __name__ == "__main__":
    main()
