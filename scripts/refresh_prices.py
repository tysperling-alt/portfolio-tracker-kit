#!/usr/bin/env python3
"""Refresh prices for every ticker in data/holdings.json and data/watchlist.json, plus the S&P 500 (SPY).

Also stores adjusted-close return anchors (1 month, 3 months, year to date, 1, 3, 5 and 10 years) for
total-return comparisons, and trailing 12-month dividends for the dividend yield.

Writes data/prices.json. Uses Yahoo Finance's free chart endpoint (no key, no cost).
Run: python3 scripts/refresh_prices.py
Exit code 1 if any ticker failed, so a scheduled run can flag it.
"""
import json
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOLDINGS = ROOT / "data" / "holdings.json"
WATCHLIST = ROOT / "data" / "watchlist.json"
OUT = ROOT / "data" / "prices.json"

# Tracker ticker -> Yahoo symbol, where they differ beyond the dot (a class-share dot becomes a dash
# automatically, so "ABC.B" is fetched as "ABC-B"). Add an entry here for any other mismatch.
YAHOO_SYMBOL = {}
SKIP_TYPES = {"cash"}  # money funds are fixed at $1.00
BENCHMARKS = ["SPY"]  # S&P 500, for account comparisons


def tickers():
    found = set()
    for a in json.loads(HOLDINGS.read_text())["accounts"]:
        for p in a["positions"]:
            if p["type"] not in SKIP_TYPES:
                found.add(p["ticker"])
    if WATCHLIST.exists():
        for w in json.loads(WATCHLIST.read_text()).get("tickers", []):
            found.add(w["ticker"] if isinstance(w, dict) else w)
    found.update(BENCHMARKS)
    return sorted(found)


def _close_on_or_before(series, day):
    """Last adjusted close in series dated on or before `day`; None if the series starts later."""
    best = None
    for d, v in series:
        if d > day:
            break
        best = v
    return best


def fetch(ticker):
    sym = YAHOO_SYMBOL.get(ticker, ticker.replace(".", "-"))
    # Ten years of daily closes, so the page can compare returns over 1, 3, 5 and 10 years.
    # An explicit start a month past ten years, because range=10y can start a few days short.
    start = int(time.time()) - 3700 * 86400
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
           f"?period1={start}&period2={int(time.time())}&interval=1d&events=div")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        res = json.load(r)["chart"]["result"][0]
    meta = res["meta"]
    tz = timezone(timedelta(seconds=meta.get("gmtoffset", -18000)))
    days = [datetime.fromtimestamp(t, tz).date() for t in res.get("timestamp", [])]
    closes = res["indicators"]["quote"][0]["close"]
    adj = (res["indicators"].get("adjclose") or [{}])[0].get("adjclose") or closes
    market_day = datetime.fromtimestamp(meta["regularMarketTime"], tz).date()
    price = meta["regularMarketPrice"]
    # Previous close: the last real close on a day before the latest market day.
    prev = next((c for d, c in zip(reversed(days), reversed(closes)) if c is not None and d < market_day), None)
    # Adjusted closes (dividends folded in) give total return, not just price change.
    series = [(d, a) for d, a in zip(days, adj) if a is not None]
    adj_now = series[-1][1] if series else None
    if series and series[-1][0] < market_day:  # today's bar not posted yet: scale by the price move
        last_close = next((c for c in reversed(closes) if c is not None), None)
        if last_close:
            adj_now = series[-1][1] * price / last_close
    def years_back(days):
        """Close about `days` ago; None when the history does not reach that far (a recent listing)."""
        target = market_day - timedelta(days=days)
        if not series or series[0][0] > target + timedelta(days=5):
            return None
        # History that starts up to 5 days after the target still counts, using its first close.
        return _close_on_or_before(series, target) or series[0][1]

    anchors = {
        "1m": _close_on_or_before(series, market_day - timedelta(days=30)),
        "3m": _close_on_or_before(series, market_day - timedelta(days=91)),
        "ytd": _close_on_or_before(series, date(market_day.year, 1, 1) - timedelta(days=1)),
        "1y": years_back(365),
        "3y": years_back(1096),
        "5y": years_back(1826),
        "10y": years_back(3650),
    }
    cutoff = datetime.combine(market_day - timedelta(days=365), datetime.min.time(), tz).timestamp()
    divs = res.get("events", {}).get("dividends", {}).values()
    div_ttm = sum(v["amount"] for v in divs if v["date"] >= cutoff)
    return {
        "price": price,
        "previous_close": prev,
        "market_day": market_day.isoformat(),
        "market_time": datetime.fromtimestamp(meta["regularMarketTime"], timezone.utc).isoformat(),
        "fifty_two_week_high": meta.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": meta.get("fiftyTwoWeekLow"),
        "dividends_ttm": round(div_ttm, 4),
        "dividend_yield": round(div_ttm / price, 5) if price else None,
        "adj_now": adj_now,
        "return_anchors": anchors,
    }


def main():
    prior = json.loads(OUT.read_text())["prices"] if OUT.exists() else {}
    prices, failed, ok = {}, [], 0
    for t in tickers():
        try:
            prices[t] = fetch(t)
            ok += 1
        except Exception as e:  # keep the last good price, mark it stale
            failed.append(f"{t}: {e}")
            if t in prior:
                prices[t] = {**prior[t], "stale": True}
        time.sleep(0.3)
    OUT.write_text(json.dumps({
        "refreshed_at": datetime.now(timezone.utc).isoformat(),
        "source": "Yahoo Finance chart endpoint",
        "failed": failed,
        "prices": prices,
    }, indent=2) + "\n")
    print(f"{ok} refreshed, {len(failed)} failed -> {OUT}")
    for f in failed:
        print("FAILED", f)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
