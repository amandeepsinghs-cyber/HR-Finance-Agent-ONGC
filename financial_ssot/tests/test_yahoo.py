"""P1.5 Yahoo loader + market-data provider chain tests (offline; no real network).

Packet docs/delegation/packets/v3/P1.5_yahoo_loader.md §6/§7; SPEC-01 §9.1 (D-45 chain).
"""
from __future__ import annotations

import csv
import io
import json
import zipfile
from datetime import date
from pathlib import Path

import pytest

from financial_ssot.extract import market_provider as mp
from financial_ssot.extract import yahoo

FIX = Path(__file__).parent / "fixtures"
TS = json.loads((FIX / "yahoo_timeseries_sample.json").read_text())
CHART = json.loads((FIX / "yahoo_chart_sample.json").read_text())


# ----------------------------------------------------------------- statements
def test_statement_rows_packet_example():
    rows = yahoo.parse_timeseries(TS, "yahoo_fundamentals_sample.json")
    r = next(x for x in rows if x["yahoo_type"] == "annualTotalAssets" and x["fiscal_year"] == "FY26")
    assert r["source_system"] == "yahoo" and r["scope"] == "consolidated"
    assert r["extraction_method"] == "yahoo_api" and r["period_type"] == "annual"
    assert r["currency"] == "INR" and r["source_doc"] == "yahoo_fundamentals_sample.json"
    assert r["value_inr_cr"] == pytest.approx(791905.18, abs=1e-6)


def test_flat_packet_form_and_fy_mapping():
    flat = {"annualTotalAssets": [{"asOfDate": "2026-03-31", "reportedValue": {"raw": 7919051800000.0},
                                   "currencyCode": "INR"}]}
    (r,) = yahoo.parse_timeseries(flat)
    assert (r["fiscal_year"], r["value_inr_cr"]) == ("FY26", pytest.approx(791905.18))
    assert yahoo.fiscal_year("2025-06-30") == "FY26" and yahoo.fiscal_year("2025-03-31") == "FY25"


def test_period_types_nulls_and_empty_series():
    rows = yahoo.parse_timeseries(TS)
    assert {r["period_type"] for r in rows} == {"annual", "quarterly"}
    q = [r for r in rows if r["period_type"] == "quarterly"]
    assert len(q) == 1 and q[0]["fiscal_year"] == "FY26"  # padded null skipped
    assert not [r for r in rows if r["yahoo_type"] == "annualOperatingCashFlow"]


def test_currency_rejection():
    rows, rej = yahoo.parse_timeseries_with_rejects(TS)
    assert not [r for r in rows if r["currency"] != "INR"]
    assert len(rej) == 1 and rej[0]["yahoo_type"] == "trailingEBITDA"
    assert rej[0]["value_inr"] is None and "USD" in rej[0]["reject_reason"]


def test_unknown_prefix_raises():
    with pytest.raises(ValueError):
        yahoo.period_type("weeklyFoo")


# ----------------------------------------------------------------- prices
def test_chart_rows_ist_dates_and_adjclose():
    rows = yahoo.parse_chart(CHART, "yahoo_chart_sample.json")
    assert len(rows) == 7  # one null close dropped
    assert rows[0] == {"ticker": "ONGC.NS", "date": "2026-03-23", "open": 999.0, "high": 1010.0, "low": 990.0,
                       "close": 1000.0, "adj_close": 999.0, "volume": 1000, "provider": "yahoo",
                       "source_doc": "yahoo_chart_sample.json"}
    assert rows[-1]["date"] == "2026-04-03"  # 20:00 UTC on 2-Apr = 01:30 IST on 3-Apr
    assert "2026-03-25" not in {r["date"] for r in rows}


def test_weekly_closes_last_trading_day():
    wk = yahoo.weekly_closes(yahoo.parse_chart(CHART))
    got = {r.week_ending: (r.date, r.adj_close) for r in wk.itertuples()}
    assert got["2026-03-27"] == ("2026-03-27", 1003.0)  # Friday
    assert got["2026-04-03"] == ("2026-04-03", 1006.0)
    # week without a Friday bar -> last trading day of that week
    rows = [r for r in yahoo.parse_chart(CHART) if r["date"] != "2026-03-27"]
    got2 = {r.week_ending: r.date for r in yahoo.weekly_closes(rows).itertuples()}
    assert got2["2026-03-27"] == "2026-03-26"


def test_weekly_closes_falls_back_to_close_when_unadjusted():
    rows = [{"ticker": "X", "date": "2026-03-27", "close": 10.0, "adj_close": None}]
    assert yahoo.weekly_closes(rows).adj_close.tolist() == [10.0]


# ----------------------------------------------------------------- NSE parsing
OLD_BHAV = ("SYMBOL,SERIES,OPEN,HIGH,LOW,CLOSE,LAST,PREVCLOSE,TOTTRDQTY,TOTTRDVAL,TIMESTAMP,TOTALTRADES,ISIN,\n"
            "ONGC,BL,1.0,1.0,1.0,1.0,1.0,1.0,1,1,31-MAR-2017,1,INE213A01029,\n"
            "ONGC,EQ,100.0,110.0,90.0,105.0,105.0,100.0,1000,1,31-MAR-2017,1,INE213A01029,\n"
            "OIL,EQ,1.0,1.0,1.0,1.0,1.0,1.0,1,1,31-MAR-2017,1,INE274J01014,\n")
UDIFF = ("TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs,XpryDt,FininstrmActlXpryDt,StrkPric,"
         "OptnTp,FinInstrmNm,OpnPric,HghPric,LwPric,ClsPric,LastPric,PrvsClsgPric,UndrlygPric,SttlmPric,OpnIntrst,"
         "ChngInOpnIntrst,TtlTradgVol,TtlTrfVal,TtlNbOfTxsExctd,SsnId,NewBrdLotQty,Rmks,Rsvd1,Rsvd2,Rsvd3,Rsvd4\n"
         "2025-03-28,2025-03-28,CM,NSE,STK,2475,INE213A01029,ONGC,EQ,,,,,OIL AND NATURAL GAS CORP.,200.0,210.0,"
         "190.0,205.0,205.0,200.0,,205.0,,,2000,1,1,F1,1,,,,,\n")
IND = ("Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,Closing Index Value,Points Change,"
       "Change(%),Volume,Turnover (Rs. Cr.),P/E,P/B,Div Yield\n"
       "Nifty 50,31-03-2017,1000.0,1100.0,900.0,1050.0,0,0,5000,1,1,1,1\n"
       "Nifty Next 50,31-03-2017,1,1,1,1,0,0,1,1,1,1,1\n")


def _zip(path: Path, inner: str, text: str) -> Path:
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(inner, text)
    return path


@pytest.fixture()
def nse_dir(tmp_path):
    d = tmp_path / "nse"
    d.mkdir()
    _zip(d / "cm31MAR2017bhav.csv.zip", "cm31MAR2017bhav.csv", OLD_BHAV)
    _zip(d / "BhavCopy_NSE_CM_0_0_0_20250328_F_0000.csv.zip", "BhavCopy_NSE_CM_0_0_0_20250328_F_0000.csv", UDIFF)
    (d / "ind_close_all_31032017.csv").write_text(IND)
    return d


def test_nse_parsers_old_udiff_index(nse_dir):
    (o,) = mp.parse_bhavcopy(nse_dir / "cm31MAR2017bhav.csv.zip")
    assert (o["ticker"], o["date"], o["close"], o["adj_close"], o["provider"]) == (
        "ONGC.NS", "2017-03-31", 105.0, None, "nse_archive")
    (u,) = mp.parse_bhavcopy(nse_dir / "BhavCopy_NSE_CM_0_0_0_20250328_F_0000.csv.zip")
    assert (u["date"], u["close"], u["volume"]) == ("2025-03-28", 205.0, 2000)
    (i,) = mp.parse_index_close(nse_dir / "ind_close_all_31032017.csv")
    assert (i["ticker"], i["date"], i["close"]) == ("^NSEI", "2017-03-31", 1050.0)


def test_nse_urls_switch_format():
    eq, ix = mp.nse_urls(date(2017, 3, 31))
    assert eq.endswith("/content/historical/EQUITIES/2017/MAR/cm31MAR2017bhav.csv.zip")
    assert ix.endswith("/content/indices/ind_close_all_31032017.csv")
    assert mp.nse_urls(date(2025, 3, 28))[0].endswith("/content/cm/BhavCopy_NSE_CM_0_0_0_20250328_F_0000.csv.zip")


# ----------------------------------------------------------------- chain
def _yahoo_dir(tmp_path):
    d = tmp_path / "yahoo"
    d.mkdir()
    (d / "yahoo_chart_ONGC.NS_10y_1d_20261023T000000Z.json").write_text(json.dumps(CHART))
    return d


def _seed(tmp_path, rows=True):
    p = tmp_path / "market_prices_seed.csv"
    with p.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(mp.SEED_COLUMNS)
        if rows:
            w.writerow(["ONGC.NS", "2017-03-31", "185.0", "", "https://example.invalid/x", "tester", "2026-10-23"])
    return p


def test_chain_order_yahoo_first(tmp_path, nse_dir):
    chain = mp.MarketChain([mp.YahooFileProvider(_yahoo_dir(tmp_path)), mp.NseArchiveProvider(nse_dir),
                            mp.ManualSeedProvider(_seed(tmp_path))])
    r = chain.get_prices("ONGC.NS", "2026-03-01", "2026-04-30")
    assert r.provider == "yahoo" and r.tried == ["yahoo"] and len(r.rows) == 7


def test_chain_falls_back_to_nse_then_seed(tmp_path, nse_dir):
    chain = mp.MarketChain([mp.YahooFileProvider(tmp_path / "missing"), mp.NseArchiveProvider(nse_dir),
                            mp.ManualSeedProvider(_seed(tmp_path))])
    r = chain.get_prices("ONGC.NS", "2017-01-01", "2025-12-31")
    assert r.provider == "nse_archive" and r.tried == ["yahoo", "nse_archive"]
    assert [x["date"] for x in r.rows] == ["2017-03-31", "2025-03-28"]
    chain2 = mp.MarketChain([mp.YahooFileProvider(tmp_path / "missing"), mp.NseArchiveProvider(tmp_path / "none"),
                             mp.ManualSeedProvider(_seed(tmp_path))])
    r2 = chain2.get_prices("ONGC.NS", "2017-01-01", "2017-12-31")
    assert r2.provider == "manual_seed" and r2.rows[0]["close"] == 185.0
    assert r2.tried == ["yahoo", "nse_archive", "manual_seed"]


def test_market_data_unavailable(tmp_path):
    chain = mp.MarketChain([mp.YahooFileProvider(tmp_path / "a"), mp.NseArchiveProvider(tmp_path / "b"),
                            mp.ManualSeedProvider(_seed(tmp_path, rows=False))])
    with pytest.raises(mp.MarketDataUnavailable, match="tried yahoo, nse_archive, manual_seed"):
        chain.get_prices("^NSEI", "2017-01-01", "2026-03-31")


# ----------------------------------------------------------------- fetchers (mocked HTTP)
class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.urls = []

    def __call__(self, url):
        self.urls.append(url)
        return self.responses.pop(0)


def test_yahoo_backoff_then_success(tmp_path):
    sleeps = []
    c = FakeClient([(429, b""), (429, b""), (200, b'{"raw": true}')])
    f = mp.YahooFetcher(tmp_path, client=c, sleep=sleeps.append, stamp="20261023T000000Z")
    p = f.get("https://example.invalid/chart", "yahoo_chart_ONGC.NS_10y_1d")
    assert p.name == "yahoo_chart_ONGC.NS_10y_1d_20261023T000000Z.json"
    assert p.read_bytes() == b'{"raw": true}'  # stored untouched
    assert sleeps == [60, 3.0, 120, 3.0]


def test_yahoo_persistent_429_raises_after_6_attempts(tmp_path):
    sleeps = []
    c = FakeClient([(429, b"")] * 10)
    f = mp.YahooFetcher(tmp_path, client=c, sleep=sleeps.append)
    with pytest.raises(mp.YahooRateLimited, match="non-blocking"):
        f.get("https://example.invalid/x", "ep")
    assert len(c.urls) == 6 and [s for s in sleeps if s != 3.0] == [60, 120, 240, 480, 960]
    assert not list(tmp_path.iterdir())


def test_yahoo_backoff_cap(tmp_path):
    sleeps = []
    f = mp.YahooFetcher(tmp_path, client=FakeClient([(429, b"")] * 10), sleep=sleeps.append)
    f.MAX_ATTEMPTS = 9
    with pytest.raises(mp.YahooRateLimited):
        f.get("u", "ep")
    assert max(sleeps) == 3600


def test_cli_exit_code_3_on_persistent_429(monkeypatch, tmp_path, capsys):
    def boom(self):
        raise mp.YahooRateLimited(yahoo.RATE_LIMIT_MSG)

    monkeypatch.setattr(mp.YahooFetcher, "fetch_all", boom)
    assert yahoo.main(["--fetch", "--yahoo-dir", str(tmp_path), "--out", str(tmp_path / "o.parquet")]) == 3
    assert "Yahoo rate-limited; loader skipped (non-blocking)" in capsys.readouterr().out


def test_cli_from_files(tmp_path):
    d = _yahoo_dir(tmp_path)
    (d / "yahoo_fundamentals_ONGC.NS_balance_annual_part1_20261023T000000Z.json").write_text(json.dumps(TS))
    out = tmp_path / "yahoo_raw.parquet"
    assert yahoo.main(["--from-files", "--yahoo-dir", str(d), "--out", str(out)]) == 0
    import pandas as pd

    assert len(pd.read_parquet(out)) == 3 and len(pd.read_parquet(tmp_path / "yahoo_prices.parquet")) == 7


def test_pending_keys_and_endpoints():
    keys = yahoo.pending_keys()
    assert "TotalAssets" in keys["BAL"] and "OperatingCashFlow" in keys["CF"] and "TotalRevenue" in keys["INC"]
    eps = dict(mp.YahooFetcher(client=FakeClient([])).endpoints())
    assert "yahoo_chart_NSEI_10y_1d" in eps and not any("balance_trailing" in k for k in eps)
    assert all("crumb" not in u and "cookie" not in u.lower() for u in eps.values())


def _zip_bytes(text):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("x.csv", text)
    return b.getvalue()


def test_nse_fetcher_walks_back_over_holiday_and_writes_manifest(tmp_path):
    # FY18: 31-Mar-2018 Sat, 30 Fri (holiday 404), 29 Thu (holiday 404), 28 Wed (200)
    sleeps = []
    c = FakeClient([(404, b"<html/>"), (404, b"<html/>"), (200, _zip_bytes(OLD_BHAV)), (200, IND.encode())])
    f = mp.NseArchiveFetcher(tmp_path, client=c, sleep=sleeps.append)
    r = f.fetch_fy_end("FY18")
    assert r["trade_date"] == "2018-03-28" and r["equity_file"] == "cm28MAR2018bhav.csv.zip"
    assert r["index_file"] == "ind_close_all_28032018.csv"
    assert len(c.urls) == 4 and sleeps == [3.0, 3.0, 3.0]
    man = list(csv.DictReader((tmp_path / "_fetch_manifest.csv").open()))
    assert [m["file"] for m in man] == ["cm28MAR2018bhav.csv.zip", "ind_close_all_28032018.csv"]
    assert all(len(m["sha256"]) == 64 and m["url"].startswith("https://nsearchives.nseindia.com/") for m in man)


def test_nse_fetcher_stops_on_bot_protection(tmp_path):
    f = mp.NseArchiveFetcher(tmp_path, client=FakeClient([(403, b"")]), sleep=lambda s: None)
    with pytest.raises(mp.NseBlocked):
        f.fetch_fy_end("FY17")


def test_nse_weekly_fetch_holiday_friday_and_cache(tmp_path):
    # week ending Fri 2017-03-31: Fri 404 -> Thu 30-Mar 200; second run is fully cached (0 requests)
    c = FakeClient([(404, b""), (200, _zip_bytes(OLD_BHAV)), (200, IND.encode())])
    f = mp.NseArchiveFetcher(tmp_path, client=c, sleep=lambda s: None)
    (r,) = f.fetch_weekly(date(2017, 3, 31), date(2017, 3, 31), log=lambda x: None)
    assert r["trade_date"] == "2017-03-30" and not r["cached"] and len(c.urls) == 3
    c2 = FakeClient([(404, b"")])
    f2 = mp.NseArchiveFetcher(tmp_path, client=c2, sleep=lambda s: None)
    r2 = f2.fetch_week(date(2017, 3, 31))  # Fri re-probed once (holiday), Thu served from disk
    assert r2["cached"] is True and r2["trade_date"] == "2017-03-30" and len(c2.urls) == 1
    assert mp.last_friday_on_or_before(date(2026, 10, 22)) == date(2026, 10, 16)
    assert mp.last_friday_on_or_before(date(2026, 10, 16)) == date(2026, 10, 16)


def test_nse_provider_weekly_closes(nse_dir):
    wk = mp.NseArchiveProvider(nse_dir).weekly_closes("^NSEI", "2017-01-01", "2017-12-31")
    assert wk.to_dict("records") == [{"ticker": "^NSEI", "week_ending": "2017-03-31", "date": "2017-03-31",
                                      "adj_close": 1050.0}]
    chain = mp.MarketChain([mp.NseArchiveProvider(nse_dir)])
    wk2, prov = chain.weekly_closes("ONGC.NS", "2017-01-01", "2025-12-31")
    assert prov == "nse_archive" and wk2.adj_close.tolist() == [105.0, 205.0]


# ----------------------------------------------------------------- real files (skip when absent)
REAL_TS = sorted(yahoo.YAHOO_DIR.glob("yahoo_fundamentals_*balance_annual*.json"))


@pytest.mark.skipif(not REAL_TS, reason="Yahoo HTTP 429: no real fundamentals saved yet")
def test_real_yahoo_fy26_consolidated_matches_ar():
    st, _, _ = yahoo.load_dir()
    ta = [r for r in st if r["yahoo_type"] == "annualTotalAssets" and r["fiscal_year"] == "FY26"]
    assert ta and abs(ta[-1]["value_inr_cr"] - 791905.18) <= 1.0  # diag_A §2, AR FY26 consolidated


REAL_NSE = mp.NSE_DIR / "cm31MAR2017bhav.csv.zip"


@pytest.mark.skipif(not REAL_NSE.exists(), reason="NSE archive files not fetched")
def test_real_nse_fy_end_closes():
    rows = mp.NseArchiveProvider().all_rows()
    ongc = {r["date"]: r["close"] for r in rows if r["ticker"] == "ONGC.NS"}
    nifty = {r["date"]: r["close"] for r in rows if r["ticker"] == "^NSEI"}
    assert ongc["2017-03-31"] == 185.0 and nifty["2017-03-31"] == 9173.75
