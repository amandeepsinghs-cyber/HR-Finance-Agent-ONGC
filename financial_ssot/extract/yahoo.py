"""Yahoo Finance loader (P1.5): saved fundamentals-timeseries + chart JSON -> bronze rows.

SPEC-01 §3 (rank 5), §4.4, §9.1; SPEC-02 §3.1.  Packet: docs/delegation/packets/v3/P1.5_yahoo_loader.md

Offline by default: it parses raw JSON files saved (untouched) under
``knowledge/public_sources/market_data/yahoo/``.  Network access happens only through
:class:`financial_ssot.extract.market_provider.YahooFetcher` (``--fetch``), which is polite
(1 request / 3 s, back-off 60 s -> 3600 s on HTTP 429, max 6 attempts per run) and never
uses cookie/crumb tricks or proxies.  A persistent 429 exits with code 3 (non-blocking).

Rules:

1. Statement rows: ``source_system='yahoo'``, ``scope='consolidated'`` (Yahoo serves the
   consolidated statements only), ``extraction_method='yahoo_api'``, ``fiscal_year`` from
   ``asOfDate`` (Apr-Mar Indian FY: 2026-03-31 -> FY26, 2025-06-30 -> FY26),
   ``period_type`` from the key prefix (annual/quarterly/trailing), ``yahoo_type`` (the full
   key, e.g. ``annualTotalAssets``), ``value_inr`` + ``value_inr_cr`` (= /1e7).  Values whose
   ``currencyCode`` is not INR are rejected (returned by :func:`parse_timeseries_with_rejects`).
2. Price rows: ``ticker, date (IST trading date), open, high, low, close, adj_close, volume,
   provider, source_doc``.  Chart timestamps are UTC epochs; the IST date is
   ``utc + 5:30``.
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

EXTRACTOR_VERSION = "yahoo/1.0.0"
APP_ROOT = Path(__file__).resolve().parents[2]
YAHOO_DIR = APP_ROOT / "knowledge" / "public_sources" / "market_data" / "yahoo"
PENDING_SCRIPT = YAHOO_DIR / "_PENDING_fetch_script_yahoo.py"
IST = timezone(timedelta(hours=5, minutes=30))
PERIOD_PREFIXES = ("annual", "quarterly", "trailing")
EXIT_RATE_LIMITED = 3
RATE_LIMIT_MSG = "Yahoo rate-limited; loader skipped (non-blocking)"


def fiscal_year(as_of: str) -> str:
    """Indian FY label (Apr-Mar) of an ISO date: 2026-03-31 -> 'FY26', 2025-04-30 -> 'FY26'."""
    d = datetime.strptime(as_of[:10], "%Y-%m-%d").date()
    end_year = d.year + 1 if d.month >= 4 else d.year
    return f"FY{end_year % 100:02d}"


def period_type(yahoo_type: str) -> str:
    for p in PERIOD_PREFIXES:
        if yahoo_type.startswith(p):
            return p
    raise ValueError(f"unknown Yahoo period prefix: {yahoo_type!r}")


def _series(doc: dict):
    """Yield (yahoo_type, [points]) from either the real API envelope
    (``{"timeseries": {"result": [{"meta": {"type": [k]}, k: [...]}, ...]}}``) or the packet's
    flat form (``{k: [...]}``)."""
    ts = doc.get("timeseries") if isinstance(doc, dict) else None
    if isinstance(ts, dict):
        for res in ts.get("result") or []:
            types = (res.get("meta") or {}).get("type") or [k for k in res if k.startswith(PERIOD_PREFIXES)]
            for k in types:
                yield k, res.get(k) or []
        return
    for k, v in doc.items():
        if isinstance(k, str) and k.startswith(PERIOD_PREFIXES) and isinstance(v, list):
            yield k, v


def parse_timeseries_with_rejects(doc: dict, source_doc: str = "", ticker: str = "ONGC.NS",
                                  extracted_at: str | None = None) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    rejects: list[dict] = []
    for ytype, points in _series(doc):
        ptype = period_type(ytype)
        for p in points:
            if not p or "reportedValue" not in p:
                continue  # padTimeSeries=true yields nulls
            raw = (p.get("reportedValue") or {}).get("raw")
            if raw is None:
                continue
            row = {
                "source_system": "yahoo",
                "scope": "consolidated",
                "extraction_method": "yahoo_api",
                "extractor_version": EXTRACTOR_VERSION,
                "ticker": ticker,
                "yahoo_type": ytype,
                "period_type": ptype,
                "as_of_date": p.get("asOfDate"),
                "fiscal_year": fiscal_year(p["asOfDate"]),
                "yahoo_period": p.get("periodType"),
                "currency": p.get("currencyCode"),
                "value_inr": float(raw),
                "value_inr_cr": float(raw) / 1e7,
                "source_doc": source_doc,
                "extracted_at": extracted_at,
            }
            if row["currency"] != "INR":
                row["reject_reason"] = f"currency {row['currency']!r} != INR"
                row["value_inr"] = row["value_inr_cr"] = None
                rejects.append(row)
            else:
                rows.append(row)
    return rows, rejects


def parse_timeseries(doc: dict, source_doc: str = "", ticker: str = "ONGC.NS",
                     extracted_at: str | None = None) -> list[dict]:
    """Bronze statement rows (consolidated, INR only)."""
    return parse_timeseries_with_rejects(doc, source_doc, ticker, extracted_at)[0]


def ist_date(epoch: int) -> str:
    return datetime.fromtimestamp(int(epoch), tz=timezone.utc).astimezone(IST).date().isoformat()


def chart_interval(meta: dict, source_doc: str = "") -> str | None:
    """Bar interval: ``meta.dataGranularity`` (e.g. '1d', '1mo'), else parsed from the saved file
    name (``yahoo_chart_<SYM>_<range>_<interval>_...``), else None."""
    g = (meta or {}).get("dataGranularity")
    if g:
        return str(g)
    for iv in ("1d", "1wk", "1mo", "3mo"):
        if f"_{iv}_" in source_doc or source_doc.endswith(f"_{iv}.json"):
            return iv
    return None


def parse_chart(doc: dict, source_doc: str = "", provider: str = "yahoo") -> list[dict]:
    """Price rows from a v8 chart response; bars with a null close are skipped.  Each row carries
    ``interval`` so monthly bars can never be mistaken for daily bars (G4 M1)."""
    out: list[dict] = []
    for res in (doc.get("chart") or {}).get("result") or []:
        meta = res.get("meta") or {}
        ticker = meta.get("symbol")
        interval = chart_interval(meta, source_doc)
        if meta.get("currency") not in (None, "INR"):
            raise ValueError(f"non-INR chart for {ticker}: {meta.get('currency')}")
        ts = res.get("timestamp") or []
        ind = res.get("indicators") or {}
        q = (ind.get("quote") or [{}])[0]
        adj = ((ind.get("adjclose") or [{}])[0] or {}).get("adjclose") or [None] * len(ts)

        def at(arr, i):
            return arr[i] if arr is not None and i < len(arr) else None

        for i, t in enumerate(ts):
            close = at(q.get("close"), i)
            if close is None:
                continue
            vol = at(q.get("volume"), i)
            out.append({
                "ticker": ticker, "date": ist_date(t),
                "open": at(q.get("open"), i), "high": at(q.get("high"), i),
                "low": at(q.get("low"), i), "close": float(close),
                "adj_close": None if at(adj, i) is None else float(at(adj, i)),
                "volume": None if vol is None else int(vol),
                "interval": interval, "provider": provider, "source_doc": source_doc,
            })
    return out


def weekly_closes(rows):
    """One row per week (W-FRI): the last trading day's adjusted close (``adj_close``, falling
    back to ``close`` for unadjusted providers).  Accepts a DataFrame or a list of dicts."""
    import pandas as pd

    df = pd.DataFrame(rows).copy()
    if df.empty:
        return pd.DataFrame(columns=["ticker", "week_ending", "date", "adj_close"])
    df["date"] = pd.to_datetime(df["date"])
    adj = df["adj_close"] if "adj_close" in df else pd.Series([None] * len(df), index=df.index)
    df["adj_close"] = adj.astype("float64").fillna(df["close"].astype("float64"))
    df["week_ending"] = df["date"].dt.to_period("W-FRI").dt.end_time.dt.normalize()
    df = df.sort_values(["ticker", "date"])
    last = df.groupby(["ticker", "week_ending"], as_index=False).tail(1)
    out = last[["ticker", "week_ending", "date", "adj_close"]].reset_index(drop=True)
    out["date"] = out["date"].dt.date.astype(str)
    out["week_ending"] = out["week_ending"].dt.date.astype(str)
    return out


def classify(path: Path) -> str | None:
    n = path.name
    if not n.endswith(".json") or n.startswith("_"):
        return None
    if n.startswith(("yahoo_fundamentals", "timeseries")):
        return "timeseries"
    if n.startswith(("yahoo_chart", "chart")):
        return "chart"
    return None


def load_dir(yahoo_dir: Path = YAHOO_DIR, extracted_at: str | None = None):
    """(statement_rows, price_rows, rejects) from every saved Yahoo JSON file in ``yahoo_dir``."""
    st, px, rej = [], [], []
    for f in sorted(Path(yahoo_dir).glob("*.json")):
        kind = classify(f)
        if kind is None:
            continue
        doc = json.loads(f.read_text(encoding="utf-8"))
        if kind == "timeseries":
            r, j = parse_timeseries_with_rejects(doc, f.name, extracted_at=extracted_at)
            st += r
            rej += j
        else:
            px += parse_chart(doc, f.name)
    return st, px, rej


def pending_keys(path: Path = PENDING_SCRIPT) -> dict[str, list[str]]:
    """Statement key lists (INC/BAL/CF) read from the pending fetch script without executing it."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    keys: dict[str, list[str]] = {}
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name) and node.targets[0].id in ("INC", "BAL", "CF")):
            v = node.value
            if isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) and isinstance(v.func.value, ast.Constant):
                keys[node.targets[0].id] = v.func.value.value.split()
    return keys


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--from-files", action="store_true", help="parse saved JSON (offline)")
    mode.add_argument("--fetch", action="store_true", help="polite live fetch (only when O instructs)")
    ap.add_argument("--yahoo-dir", default=str(YAHOO_DIR))
    ap.add_argument("--out", default="financial_ssot/out/yahoo_raw.parquet")
    args = ap.parse_args(argv)

    if args.fetch:
        from financial_ssot.extract.market_provider import YahooFetcher, YahooRateLimited

        try:
            saved = YahooFetcher(out_dir=Path(args.yahoo_dir)).fetch_all()
        except YahooRateLimited:
            print(RATE_LIMIT_MSG)
            return EXIT_RATE_LIMITED
        print(f"saved {len(saved)} Yahoo files")

    import pandas as pd

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    st, px, rej = load_dir(Path(args.yahoo_dir), stamp)
    if not st and not px:
        print(f"no saved Yahoo JSON in {args.yahoo_dir}; {RATE_LIMIT_MSG}")
        return EXIT_RATE_LIMITED
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(st).to_parquet(out, index=False)
    pxo = out.with_name("yahoo_prices.parquet")
    pd.DataFrame(px).to_parquet(pxo, index=False)
    print(f"wrote {out} ({len(st)} statement rows, {len(rej)} rejected) and {pxo} ({len(px)} price rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
