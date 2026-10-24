"""Market-data provider chain (P1.5, sponsor decision D-45): Yahoo -> NSE public archives -> manual seed.

SPEC-01 §9.1; SPEC-02 §3.1.  Packet: docs/delegation/packets/v3/P1.5_yahoo_loader.md

``MarketChain.get_prices(ticker, start, end)`` tries, in order:

1. :class:`YahooFileProvider` - saved Yahoo chart JSON (``market_data/yahoo/``).
2. :class:`NseArchiveProvider` - saved NSE public-archive files (``market_data/nse/``):
   equity bhavcopy (old ``cmDDMONYYYYbhav.csv.zip`` up to 05-Jul-2024, UDiFF
   ``BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000.csv.zip`` after) for ONGC (series EQ) and the
   daily index close file ``ind_close_all_DDMMYYYY.csv`` for NIFTY 50.  Closes are
   **unadjusted** (``adj_close`` = None; :func:`yahoo.weekly_closes` falls back to close).
3. :class:`ManualSeedProvider` - ``market_data/manual/market_prices_seed.csv``.

It returns a :class:`PriceResult` (rows + provider used) or raises
:class:`MarketDataUnavailable` (callers degrade: SPEC-02 industry-beta fallback).

Fetchers (network; never run by tests, which inject a fake client):

* :class:`YahooFetcher` - 1 request / 3 s; on HTTP 429 back-off 60, 120, 240 ... s (cap
  3600 s), max 6 attempts per run, then :class:`YahooRateLimited` (CLI exit code 3).  Raw
  bodies are written unmodified.  No cookie/crumb tricks, no proxies.
* :class:`NseArchiveFetcher` - documented public ``nsearchives.nseindia.com`` file URLs
  only, plain GET, no cookies/session priming, >= 3 s between requests, low volume (FY-end
  dates).  HTTP 403/429 (bot protection) stops the run - it is never worked around.  Each
  saved file gets a manifest row (file, url, fetched_utc, bytes, sha256).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
import time
import urllib.parse
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Protocol

from financial_ssot.extract import yahoo

APP_ROOT = yahoo.APP_ROOT
MARKET_DIR = APP_ROOT / "knowledge" / "public_sources" / "market_data"
NSE_DIR = MARKET_DIR / "nse"
NSE_MANIFEST = NSE_DIR / "_fetch_manifest.csv"
MANUAL_SEED = MARKET_DIR / "manual" / "market_prices_seed.csv"
SEED_COLUMNS = ["ticker", "date", "close", "adj_close", "source_url", "retrieved_by", "retrieved_at"]
PRICE_COLUMNS = ["ticker", "date", "open", "high", "low", "close", "adj_close", "volume", "interval", "provider",
                 "source_doc"]
MANIFEST_COLUMNS = ["file", "url", "fetched_utc", "http_status", "bytes", "sha256", "fiscal_year", "trade_date", "notes"]
# Single fixed User-Agent for Yahoo and NSE (G4 should-fix 1, documented): a static desktop-browser
# string, never rotated; nothing else is spoofed (no cookies, crumbs, session priming, proxies or
# parallel requests).  Recorded in docs/reviews/P1.5_evidence.md §8 against D-45.
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# ticker <-> NSE identifiers
NSE_EQUITY = {"ONGC.NS": "ONGC"}
NSE_INDEX = {"^NSEI": "NIFTY 50"}
UDIFF_FROM = date(2024, 7, 8)  # first trading day of the UDiFF bhavcopy format
NSE_BASE = "https://nsearchives.nseindia.com"

HttpClient = Callable[[str], "tuple[int, bytes]"]


class MarketDataUnavailable(RuntimeError):
    """No provider in the chain has prices for the request (callers degrade)."""


class YahooRateLimited(RuntimeError):
    """Yahoo kept answering HTTP 429 for the whole attempt budget of this run."""


class NseBlocked(RuntimeError):
    """NSE answered 403/429 (bot protection); the run stops - never bypassed."""


@dataclass
class PriceResult:
    rows: list[dict]
    provider: str
    tried: list[str] = field(default_factory=list)


class MarketProvider(Protocol):
    name: str

    def get_prices(self, ticker: str, start: str, end: str) -> list[dict]: ...


def _in_range(rows: list[dict], ticker: str, start: str, end: str) -> list[dict]:
    return sorted((r for r in rows if r["ticker"] == ticker and start <= r["date"] <= end), key=lambda r: r["date"])


def _dedupe(rows: list[dict]) -> list[dict]:
    """One row per (ticker, date, interval); later files win (newer download of the same bar)."""
    seen: dict[tuple, dict] = {}
    for r in rows:
        seen[(r["ticker"], r["date"], r.get("interval"))] = r
    return list(seen.values())


def prefer_daily(rows: list[dict]) -> list[dict]:
    """Daily series only (G4 M1): dedupe by (ticker, date, interval), then keep ``1d`` bars.
    Monthly/weekly bars never overwrite or pad a daily series.  If a ticker has no ``1d`` bars
    at all it gets no rows here (the chain then falls through to the next provider)."""
    return [r for r in _dedupe(rows) if r.get("interval") == "1d"]


# --------------------------------------------------------------------------- providers
class YahooFileProvider:
    name = "yahoo"

    def __init__(self, yahoo_dir: Path = yahoo.YAHOO_DIR):
        self.dir = Path(yahoo_dir)

    def get_prices(self, ticker, start, end):
        if not self.dir.exists():
            return []
        rows: list[dict] = []
        for f in sorted(self.dir.glob("*.json")):
            if yahoo.classify(f) == "chart":
                rows += yahoo.parse_chart(json.loads(f.read_text(encoding="utf-8")), f.name)
        return _in_range(prefer_daily(rows), ticker, start, end)


def _f(x):
    x = (x or "").strip()
    return None if x in ("", "-", "NA") else float(x.replace(",", ""))


def _csv_text(path: Path) -> str:
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as z:
            name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
            return z.read(name).decode("utf-8-sig")
    return path.read_text(encoding="utf-8-sig")


def parse_bhavcopy(path: Path, symbols: dict[str, str] = NSE_EQUITY) -> list[dict]:
    """Equity bhavcopy (old or UDiFF format, .csv or .csv.zip) -> price rows for ``symbols``
    (ticker -> NSE symbol), series EQ only."""
    path = Path(path)
    want = {v: k for k, v in symbols.items()}
    out = []
    for r in csv.DictReader(io.StringIO(_csv_text(path))):
        r = {k.strip(): (v or "").strip() for k, v in r.items() if k}
        if "TckrSymb" in r:  # UDiFF
            sym, series = r["TckrSymb"], r.get("SctySrs")
            d = r["TradDt"][:10]
            o, h, lo, c, vol = r["OpnPric"], r["HghPric"], r["LwPric"], r["ClsPric"], r.get("TtlTradgVol")
        else:  # legacy cmDDMONYYYYbhav.csv
            sym, series = r.get("SYMBOL"), r.get("SERIES")
            d = datetime.strptime(r["TIMESTAMP"], "%d-%b-%Y").date().isoformat()
            o, h, lo, c, vol = r["OPEN"], r["HIGH"], r["LOW"], r["CLOSE"], r.get("TOTTRDQTY")
        if sym in want and series == "EQ":
            out.append({"ticker": want[sym], "date": d, "open": _f(o), "high": _f(h), "low": _f(lo),
                        "close": _f(c), "adj_close": None, "volume": None if not vol else int(float(vol)),
                        "interval": "1d", "provider": "nse_archive", "source_doc": path.name})
    return out


def parse_index_close(path: Path, indices: dict[str, str] = NSE_INDEX) -> list[dict]:
    """``ind_close_all_DDMMYYYY.csv`` -> price rows for ``indices`` (ticker -> index name)."""
    path = Path(path)
    want = {v.upper(): k for k, v in indices.items()}
    out = []
    for r in csv.DictReader(io.StringIO(_csv_text(path))):
        r = {k.strip(): (v or "").strip() for k, v in r.items() if k}
        name = r.get("Index Name", "").upper()
        if name in want:
            d = datetime.strptime(r["Index Date"], "%d-%m-%Y").date().isoformat()
            vol = _f(r.get("Volume"))
            out.append({"ticker": want[name], "date": d, "open": _f(r.get("Open Index Value")),
                        "high": _f(r.get("High Index Value")), "low": _f(r.get("Low Index Value")),
                        "close": _f(r.get("Closing Index Value")), "adj_close": None,
                        "volume": None if vol is None else int(vol),
                        "interval": "1d", "provider": "nse_archive", "source_doc": path.name})
    return out


class NseArchiveProvider:
    name = "nse_archive"

    def __init__(self, nse_dir: Path = NSE_DIR):
        self.dir = Path(nse_dir)

    def all_rows(self) -> list[dict]:
        rows: list[dict] = []
        if not self.dir.exists():
            return rows
        for f in sorted(self.dir.iterdir()):
            n = f.name
            if n.startswith("ind_close_all_"):
                rows += parse_index_close(f)
            elif (n.startswith("cm") and "bhav" in n) or n.startswith("BhavCopy_NSE_CM_"):
                rows += parse_bhavcopy(f)
        return _dedupe(rows)

    def get_prices(self, ticker, start, end):
        return _in_range(self.all_rows(), ticker, start, end)

    def weekly_closes(self, ticker: str, start: str, end: str):
        """W-FRI weekly closes (last trading day of each week; unadjusted close) for the 2-yr
        weekly beta (SPEC-02 §3.1, computed in P1.9)."""
        return yahoo.weekly_closes(self.get_prices(ticker, start, end))


class ManualSeedProvider:
    name = "manual_seed"

    def __init__(self, seed_csv: Path = MANUAL_SEED):
        self.path = Path(seed_csv)

    def get_prices(self, ticker, start, end):
        if not self.path.exists():
            return []
        rows = []
        with self.path.open(encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                if not r.get("ticker") or not r.get("close"):
                    continue
                rows.append({"ticker": r["ticker"], "date": r["date"], "open": None, "high": None, "low": None,
                             "close": float(r["close"]), "adj_close": _f(r.get("adj_close")), "volume": None,
                             "interval": "1d", "provider": "manual_seed", "source_doc": r.get("source_url") or self.path.name})
        return _in_range(rows, ticker, start, end)


class MarketChain:
    """Yahoo files -> NSE archive files -> manual seed (SPEC-01 §9.1 priority order)."""

    def __init__(self, providers: list | None = None):
        self.providers = providers if providers is not None else [
            YahooFileProvider(), NseArchiveProvider(), ManualSeedProvider()]

    def get_prices(self, ticker: str, start: str, end: str) -> PriceResult:
        tried = []
        for p in self.providers:
            tried.append(p.name)
            rows = p.get_prices(ticker, start, end)
            if rows:
                return PriceResult(rows, p.name, tried)
        raise MarketDataUnavailable(f"no prices for {ticker} {start}..{end} (tried {', '.join(tried)})")

    def weekly_closes(self, ticker: str, start: str, end: str):
        """(weekly DataFrame, provider) from the first provider with prices."""
        pr = self.get_prices(ticker, start, end)
        return yahoo.weekly_closes(pr.rows), pr.provider


# --------------------------------------------------------------------------- fetchers
def default_client(url: str) -> tuple[int, bytes]:
    """Plain GET (no cookies, no session priming, no proxy)."""
    import requests

    r = requests.get(url, headers={"User-Agent": UA, "Accept": "*/*"}, timeout=60, allow_redirects=True)
    return r.status_code, r.content


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


class YahooFetcher:
    MIN_INTERVAL_S = 3.0
    BACKOFF_START_S = 60
    BACKOFF_CAP_S = 3600
    MAX_ATTEMPTS = 6

    def __init__(self, out_dir: Path = yahoo.YAHOO_DIR, client: HttpClient | None = None,
                 sleep: Callable[[float], None] = time.sleep, stamp: str | None = None):
        self.out_dir = Path(out_dir)
        self.client = client or default_client
        self.sleep = sleep
        self.stamp = stamp or utc_stamp()
        self.attempts = 0
        self.sleeps: list[float] = []
        self._requested = False

    def _wait(self, s: float):
        self.sleeps.append(s)
        self.sleep(s)

    def get(self, url: str, endpoint: str) -> Path:
        """Fetch one URL; on 429 back off exponentially.  Raw body saved unmodified as
        ``<endpoint>_<UTC>.json``.  Raises :class:`YahooRateLimited` when the run budget of
        6 attempts is spent."""
        backoff = self.BACKOFF_START_S
        while True:
            if self.attempts >= self.MAX_ATTEMPTS:
                raise YahooRateLimited(yahoo.RATE_LIMIT_MSG)
            if self._requested:
                self._wait(self.MIN_INTERVAL_S)
            self._requested = True
            self.attempts += 1
            status, body = self.client(url)
            if status == 200:
                self.out_dir.mkdir(parents=True, exist_ok=True)
                path = self.out_dir / f"{endpoint}_{self.stamp}.json"
                path.write_bytes(body)
                return path
            if status == 429:
                if self.attempts >= self.MAX_ATTEMPTS:
                    raise YahooRateLimited(yahoo.RATE_LIMIT_MSG)
                self._wait(backoff)
                backoff = min(backoff * 2, self.BACKOFF_CAP_S)
                continue
            raise RuntimeError(f"Yahoo HTTP {status} for {endpoint}")

    def endpoints(self) -> list[tuple[str, str]]:
        """(endpoint_name, url) pairs, same set as ``_PENDING_fetch_script_yahoo.py``."""
        keys = yahoo.pending_keys()
        p2 = int(time.time()) + 86400
        eps = []
        for stmt, k in (("income", "INC"), ("balance", "BAL"), ("cashflow", "CF")):
            for freq in ("annual", "quarterly", "trailing"):
                if freq == "trailing" and stmt == "balance":
                    continue
                types = [freq + x for x in keys.get(k, [])]
                for i in range(0, len(types), 60):
                    q = urllib.parse.urlencode({"symbol": "ONGC.NS", "type": ",".join(types[i:i + 60]),
                                                "merge": "false", "padTimeSeries": "true",
                                                "period1": "493590046", "period2": str(p2)})
                    eps.append((f"yahoo_fundamentals_ONGC.NS_{stmt}_{freq}_part{i // 60 + 1}",
                                "https://query1.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/ONGC.NS?" + q))
        for sym in ("ONGC.NS", "^NSEI"):
            for rng, iv in (("max", "1mo"), ("10y", "1d")):
                eps.append((f"yahoo_chart_{sym.replace('^', '')}_{rng}_{iv}",
                            f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}"
                            f"?range={rng}&interval={iv}&events=div%2Csplit&includeAdjustedClose=true"))
        return eps

    def fetch_all(self) -> list[Path]:
        return [self.get(url, ep) for ep, url in self.endpoints()]


def nse_urls(d: date) -> tuple[str, str]:
    """(equity bhavcopy URL, index close URL) for trade date ``d``."""
    if d >= UDIFF_FROM:
        eq = f"{NSE_BASE}/content/cm/BhavCopy_NSE_CM_0_0_0_{d:%Y%m%d}_F_0000.csv.zip"
    else:
        mon = d.strftime("%b").upper()
        eq = f"{NSE_BASE}/content/historical/EQUITIES/{d.year}/{mon}/cm{d:%d}{mon}{d.year}bhav.csv.zip"
    return eq, f"{NSE_BASE}/content/indices/ind_close_all_{d:%d%m%Y}.csv"


def fy_end(fy: str) -> date:
    return date(2000 + int(fy[2:]), 3, 31)


class NseArchiveFetcher:
    MIN_INTERVAL_S = 3.0
    MAX_STEP_BACK_DAYS = 7

    def __init__(self, out_dir: Path = NSE_DIR, client: HttpClient | None = None,
                 sleep: Callable[[float], None] = time.sleep, manifest: Path | None = None):
        self.out_dir = Path(out_dir)
        self.client = client or default_client
        self.sleep = sleep
        self.manifest = Path(manifest) if manifest else self.out_dir / NSE_MANIFEST.name
        self.gaps_file = self.out_dir / "_fetch_gaps.csv"
        self.gaps: list[dict] = []
        self.requests = 0

    def _get(self, url: str) -> tuple[int, bytes]:
        if self.requests:
            self.sleep(self.MIN_INTERVAL_S)
        self.requests += 1
        status, body = self.client(url)
        if status in (403, 429):
            raise NseBlocked(f"NSE HTTP {status} for {url}; stopping (no workaround attempted)")
        return status, body

    def _save(self, url: str, body: bytes, fy: str, d: date, notes: str = "") -> Path:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        path = self.out_dir / url.rsplit("/", 1)[1]
        path.write_bytes(body)
        new = not self.manifest.exists()
        with self.manifest.open("a", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=MANIFEST_COLUMNS)
            if new:
                w.writeheader()
            w.writerow({"file": path.name, "url": url,
                        "fetched_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "http_status": 200, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                        "fiscal_year": fy, "trade_date": d.isoformat(), "notes": notes})
        return path

    def _gap(self, url: str, status: int, label: str, d: date, notes: str = "") -> None:
        """Record a missing file explicitly (G4 should-fix 3) so equity and index series can be
        aligned by the caller (inner join on date) instead of silently carrying a None."""
        self.gaps.append({"label": label, "trade_date": d.isoformat(), "url": url, "http_status": status,
                          "notes": notes or "index close missing for a date whose equity file exists"})
        self.out_dir.mkdir(parents=True, exist_ok=True)
        new = not self.gaps_file.exists()
        with self.gaps_file.open("a", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["logged_utc", "label", "trade_date", "url", "http_status", "notes"])
            if new:
                w.writeheader()
            w.writerow({"logged_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **self.gaps[-1]})
        return None

    def fetch_fy_end(self, fy: str) -> dict:
        """Last NSE trading day on/before 31-Mar of ``fy``: walk back over weekends (no request)
        and holidays (404 on the equity file), then fetch the index close for the same date."""
        d = fy_end(fy)
        for _ in range(self.MAX_STEP_BACK_DAYS + 1):
            if d.weekday() < 5:
                eq_url, ix_url = nse_urls(d)
                status, body = self._get(eq_url)
                if status == 200 and body[:2] == b"PK":
                    eq = self._save(eq_url, body, fy, d, "equity bhavcopy (unadjusted)")
                    s2, b2 = self._get(ix_url)
                    ix = (self._save(ix_url, b2, fy, d, "index close (NIFTY 50 etc.)") if s2 == 200
                          else self._gap(ix_url, s2, fy, d))
                    return {"fiscal_year": fy, "trade_date": d.isoformat(), "equity_file": eq.name,
                            "index_file": ix.name if ix else None, "index_status": s2, "gap": ix is None}
            d -= timedelta(days=1)
        return {"fiscal_year": fy, "trade_date": None, "equity_file": None, "index_file": None, "index_status": None,
                "gap": True}

    def fetch_fy_ends(self, fys: list[str]) -> list[dict]:
        return [self.fetch_fy_end(fy) for fy in fys]

    def fetch_week(self, friday: date) -> dict:
        """Last NSE trading day of the Mon-Fri week ending ``friday``: try Fri, Thu, ... Mon
        (404 = holiday).  Dates whose equity + index files are already stored cost no request."""
        d = friday
        week = f"W{friday.isoformat()}"
        while d.weekday() <= 4 and d > friday - timedelta(days=5):
            eq_url, ix_url = nse_urls(d)
            eq_p, ix_p = self.out_dir / eq_url.rsplit("/", 1)[1], self.out_dir / ix_url.rsplit("/", 1)[1]
            if eq_p.exists() and ix_p.exists():
                return {"week_ending": friday.isoformat(), "trade_date": d.isoformat(), "equity_file": eq_p.name,
                        "index_file": ix_p.name, "index_status": 200, "cached": True, "gap": False}
            status, body = (200, eq_p.read_bytes()) if eq_p.exists() else self._get(eq_url)
            if status == 200 and body[:2] == b"PK":
                if not eq_p.exists():
                    self._save(eq_url, body, week, d, "weekly close: equity bhavcopy (unadjusted)")
                s2, b2 = self._get(ix_url)
                ix = (self._save(ix_url, b2, week, d, "weekly close: index close") if s2 == 200
                      else self._gap(ix_url, s2, week, d))
                return {"week_ending": friday.isoformat(), "trade_date": d.isoformat(), "equity_file": eq_p.name,
                        "index_file": ix.name if ix else None, "index_status": s2, "cached": False,
                        "gap": ix is None}
            d -= timedelta(days=1)
        self._gap(nse_urls(friday)[0], 404, week, friday, "no trading day found Mon-Fri")
        return {"week_ending": friday.isoformat(), "trade_date": None, "equity_file": None, "index_file": None,
                "index_status": None, "cached": False, "gap": True}

    def fetch_weekly(self, first_friday: date, last_friday: date, log=print) -> list[dict]:
        out = []
        d = last_friday
        while d >= first_friday:
            r = self.fetch_week(d)
            log(r)
            out.append(r)
            d -= timedelta(days=7)
        return out


def last_friday_on_or_before(d: date) -> date:
    return d - timedelta(days=(d.weekday() - 4) % 7)


def fy_range(spec: str) -> list[str]:
    a, b = spec.upper().split("..")
    return [f"FY{y:02d}" for y in range(int(a[2:]), int(b[2:]) + 1)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fetch-nse-fy-ends", metavar="FY17..FY26", help="polite NSE archive fetch (D-45)")
    ap.add_argument("--fetch-nse-weekly", type=int, metavar="N_WEEKS",
                    help="last trading day of each of the last N complete weeks (lead beta decision; 104 = 2 yr)")
    ap.add_argument("--out", default="financial_ssot/out/market_prices.parquet")
    ap.add_argument("--start", default="2012-04-01")
    ap.add_argument("--end", default=date.today().isoformat())
    args = ap.parse_args(argv)
    if args.fetch_nse_weekly:
        last = last_friday_on_or_before(date.today() - timedelta(days=1))
        first = last - timedelta(days=7 * (args.fetch_nse_weekly - 1))
        f = NseArchiveFetcher()
        try:
            res = f.fetch_weekly(first, last)
        except NseBlocked as e:
            print(e)
            return 3
        print(f"weekly: {len(res)} weeks {first}..{last}, {sum(1 for r in res if r['trade_date'])} with data, "
              f"{f.requests} requests, {len(f.gaps)} gaps" + (f" (see {f.gaps_file})" if f.gaps else ""))
    if args.fetch_nse_fy_ends:
        try:
            nf = NseArchiveFetcher()
            res = nf.fetch_fy_ends(fy_range(args.fetch_nse_fy_ends))
        except NseBlocked as e:
            print(e)
            return 3
        for r in res:
            print(r)
        print(f"fy-ends: {len(res)} FYs, {nf.requests} requests, {len(nf.gaps)} gaps")
    import pandas as pd

    chain = MarketChain()
    rows = []
    for t in ("ONGC.NS", "^NSEI"):
        try:
            pr = chain.get_prices(t, args.start, args.end)
            print(f"{t}: {len(pr.rows)} rows from {pr.provider} (tried {pr.tried})")
            rows += pr.rows
        except MarketDataUnavailable as e:
            print(f"{t}: {e}")
    if rows:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows, columns=PRICE_COLUMNS).to_parquet(out, index=False)
        print(f"wrote {out} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
