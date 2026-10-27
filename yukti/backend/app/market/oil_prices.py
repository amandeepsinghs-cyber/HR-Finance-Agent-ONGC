"""Crude-oil benchmark prices (Brent / WTI): saved daily history + incremental live updates from Yahoo Finance (26-Oct).

- History: one JSON file per benchmark in app/market/history/ ({"YYYY-MM-DD": close}), shipped with the app (seed of
  ~12 years) and kept up to date on disk where writable. Each refresh asks Yahoo ONLY for the days after the last saved
  date (with a 5-day overlap so late corrections overwrite), so a request normally fetches a handful of days.
- Today: Yahoo's live intraday price is reported separately (`live`) and shown as the last point of daily charts.
- Source: Yahoo Finance chart API, front-month futures: Brent = BZ=F, WTI = CL=F (USD/bbl). Unofficial feed: fine for a
  demo; for production, swap `_fetch_range` for a licensed/official feed (e.g. US EIA RBRTE/RWTC) or a BigQuery table.
- Fiscal-year averages use Indian FYs (Apr-Mar); the running FY is provisional.
- Refresh at most every 10 minutes (in-memory); if Yahoo is unreachable the saved history is served, flagged `stale`.
- Public market data: no persona restriction.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger("yukti.market.oil")

BENCHMARKS: Dict[str, Dict[str, str]] = {
    "brent": {"symbol": "BZ=F", "label": "Brent crude", "short": "Brent", "unit": "$/bbl"},
    "wti": {"symbol": "CL=F", "label": "WTI crude", "short": "WTI", "unit": "$/bbl"},
    # 27-Oct: the rupee explains much of ONGC's revenue resilience (prices are dollar-linked, books are in rupees)
    "inr": {"symbol": "INR=X", "label": "Rupee per US dollar", "short": "₹/$", "unit": "₹ per $"},
}
CACHE_TTL_S = int(os.getenv("YUKTI_OIL_CACHE_S", "600"))
OVERLAP_DAYS = 5
_YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
_HIST_DIR = Path(os.getenv("YUKTI_OIL_HISTORY_DIR", str(Path(__file__).resolve().parent / "history")))

_lock = threading.Lock()
# benchmark -> (refreshed_at_epoch, payload)
_mem: Dict[str, Tuple[float, Dict[str, Any]]] = {}
# benchmark -> {"YYYY-MM-DD": close}
_hist: Dict[str, Dict[str, float]] = {}


def normalize_benchmark(value: Optional[str]) -> str:
    v = (value or "brent").strip().lower()
    if v in ("wti", "cl", "cl=f", "west texas", "west texas intermediate", "nymex"):
        return "wti"
    if v in ("inr", "inr=x", "rupee", "rupees", "usd", "usdinr", "usd/inr", "inr/usd", "dollar", "fx", "forex", "currency", "exchange rate", "₹/$"):
        return "inr"
    return "brent"


def _fy_of(dt: datetime) -> int:
    """Indian fiscal year number (end year): 15-Jun-2025 -> 2026 (FY26)."""
    return dt.year + 1 if dt.month >= 4 else dt.year


def _hist_path(benchmark: str) -> Path:
    return _HIST_DIR / f"{benchmark}_daily.json"


def _load_history(benchmark: str) -> Dict[str, float]:
    if benchmark not in _hist:
        try:
            _hist[benchmark] = {k: float(v) for k, v in json.loads(_hist_path(benchmark).read_text()).items()}
        except Exception:  # noqa: BLE001 - no saved history yet
            _hist[benchmark] = {}
    return _hist[benchmark]


def _save_history(benchmark: str, h: Dict[str, float]) -> None:
    try:
        _HIST_DIR.mkdir(parents=True, exist_ok=True)
        tmp = _hist_path(benchmark).with_suffix(".tmp")
        tmp.write_text(json.dumps(dict(sorted(h.items())), separators=(",", ":")))
        tmp.replace(_hist_path(benchmark))
    except Exception as e:  # noqa: BLE001 - read-only filesystem (e.g. Cloud Run): history stays in memory
        logger.info(f"oil history not saved to disk ({type(e).__name__}); kept in memory")


def _fetch_range(symbol: str, start: Optional[datetime]) -> Tuple[Dict[str, float], Dict[str, Any]]:
    """Daily closes from `start` (or the last 12 years) to now, plus Yahoo's quote meta."""
    params: Dict[str, Any] = {"interval": "1d"}
    if start is None:
        params["range"] = "12y"
    else:
        params["period1"] = int(start.timestamp())
        params["period2"] = int(time.time()) + 86400
    r = httpx.get(_YAHOO.format(symbol=symbol), params=params, headers={"User-Agent": "Mozilla/5.0 (Yukti AI demo)"}, timeout=8.0)
    r.raise_for_status()
    res = (r.json().get("chart") or {}).get("result") or []
    if not res:
        raise ValueError("empty chart result")
    res = res[0]
    ts = res.get("timestamp") or []
    closes = ((res.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
    out = {
        datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d"): round(float(c), 2)
        for t, c in zip(ts, closes)
        if c is not None and c > 0
    }
    return out, res.get("meta") or {}


def _refresh(benchmark: str) -> Tuple[Dict[str, float], Dict[str, Any], int, int]:
    """Merges only the missing days into the saved history. Returns (history, meta, saved_days, new_days)."""
    spec = BENCHMARKS[benchmark]
    h = _load_history(benchmark)
    saved = len(h)
    start = None
    if h:
        last = datetime.strptime(max(h), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        start = last - timedelta(days=OVERLAP_DAYS)
    fresh, meta = _fetch_range(spec["symbol"], start)
    new_days = len([d for d in fresh if d not in h])
    changed = new_days > 0 or any(h.get(d) != v for d, v in fresh.items())
    h.update(fresh)
    if changed:
        _save_history(benchmark, h)
    return h, meta, saved, new_days


def _payload(benchmark: str, h: Dict[str, float], meta: Dict[str, Any], saved: int, new_days: int, stale: bool) -> Dict[str, Any]:
    spec = BENCHMARKS[benchmark]
    days = sorted(h.items())
    now = datetime.now(timezone.utc)
    cur_fy = _fy_of(now)
    by_fy: Dict[int, List[float]] = {}
    by_month: Dict[str, List[float]] = {}
    for d, c in days:
        dt = datetime.strptime(d, "%Y-%m-%d")
        by_fy.setdefault(_fy_of(dt), []).append(c)
        by_month.setdefault(d[:7], []).append(c)
    fy_series = [
        {"fy": f"FY{fy % 100:02d}", "avg": round(sum(v) / len(v), 2), "days": len(v), "provisional": fy == cur_fy}
        for fy, v in sorted(by_fy.items())
        if len(v) >= 20
    ]
    monthly = [{"month": m, "avg": round(sum(v) / len(v), 2)} for m, v in sorted(by_month.items())]
    year_ago = (now - timedelta(days=366)).strftime("%Y-%m-%d")
    daily = [{"date": d, "close": c} for d, c in days if d >= year_ago]
    price = meta.get("regularMarketPrice") or (days[-1][1] if days else None)
    prev = meta.get("chartPreviousClose") or meta.get("previousClose")
    change_pct = meta.get("regularMarketChangePercent")
    if change_pct is None and prev and price:
        change_pct = (price - prev) / prev * 100
    as_of = meta.get("regularMarketTime")
    return {
        "benchmark": benchmark,
        "symbol": spec["symbol"],
        "label": spec["label"],
        "short": spec["short"],
        "unit": spec["unit"],
        "currency": meta.get("currency") or "USD",
        "live": {
            "price": round(float(price), 2) if price else None,
            "change_pct": round(float(change_pct), 2) if change_pct is not None else None,
            "as_of": datetime.fromtimestamp(as_of, tz=timezone.utc).isoformat() if as_of else (f"{days[-1][0]}T00:00:00+00:00" if days else None),
        },
        "fy_series": fy_series,
        "monthly": monthly,
        "daily": daily,
        "history": {"days": len(days), "first": days[0][0] if days else None, "last": days[-1][0] if days else None,
                    "saved_days": saved, "new_days": new_days},
        "source": f"Yahoo Finance ({spec['symbol']}{', front-month futures' if benchmark != 'inr' else ''}; daily closes, saved history + live updates)",
        "fetched_at": now.isoformat(),
        "stale": stale,
    }


def get_daily_history(benchmark: str) -> Dict[str, float]:
    """Full saved daily history ({date: close}) after a refresh (call get_oil_prices first)."""
    return dict(_load_history(normalize_benchmark(benchmark)))


def get_oil_prices(benchmark: str) -> Dict[str, Any]:
    """Payload for the benchmark; raises RuntimeError only when there is neither live data nor saved history."""
    benchmark = normalize_benchmark(benchmark)
    with _lock:
        hit = _mem.get(benchmark)
        if hit and time.time() - hit[0] < CACHE_TTL_S:
            return hit[1]
        try:
            h, meta, saved, new_days = _refresh(benchmark)
            data = _payload(benchmark, h, meta, saved, new_days, stale=False)
            logger.info(f"oil {benchmark}: {saved} days from saved history, {new_days} new days fetched live")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"oil price fetch failed for {benchmark}: {type(e).__name__}: {e}")
            h = _load_history(benchmark)
            if not h:
                raise RuntimeError("Live oil prices are unavailable right now.") from e
            data = _payload(benchmark, h, {}, len(h), 0, stale=True)
            _mem[benchmark] = (time.time() - CACHE_TTL_S + 60, data)  # retry Yahoo in a minute
            return data
        _mem[benchmark] = (time.time(), data)
        return data
