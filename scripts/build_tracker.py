#!/usr/bin/env python3
"""Build the tracker page's data files from holdings, prices, and valuations.

Reads:  data/holdings.json, data/prices.json, data/valuations/<TICKER>.json (latest record each)
Writes: build/positions.json   one row per account x ticker, priced at the latest close
        build/valuations.json  one row per valued ticker: my value, Buy/Hold/Sell call, call prices, zone
        build/private.json     private-company holdings (no market price)
        build/performance.json each account vs the S&P 500 over 1 day, 1 month, 3 months, year to date, 1, 3, 5, 10 years
        build/analyses.json    newest analysis report text per ticker
        build/meetings.json    monthly meeting letters (rebalancing advice), newest first
Each file is {"rows": [...], "meta": [...]} so the page's Sources panel shows how it was made.
Run: python3 scripts/build_tracker.py
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BUILD = ROOT / "build"

# The verdict rule lives in the analyze-stock skill, so the report, the record, and the page agree.
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "analyze-stock" / "scripts"))
import bands  # noqa: E402


def load(p, default=None):
    return json.loads(p.read_text()) if p.exists() else default


def latest_valuation(ticker):
    """Return the newest record in data/valuations/<TICKER>.json, or None."""
    path = DATA / "valuations" / f"{ticker.replace('.', '-')}.json"
    d = load(path)
    if not d:
        return None
    records = d.get("records", d) if isinstance(d, dict) else d
    if isinstance(records, dict):
        records = [records]
    records = [r for r in records if isinstance(r, dict)]
    return max(records, key=lambda r: r.get("date", "")) if records else None


def pick(rec, *keys):
    """First present value among dotted keys, so the page survives small schema changes."""
    for k in keys:
        cur = rec
        for part in k.split("."):
            cur = cur.get(part) if isinstance(cur, dict) else None
        if cur is not None:
            return cur
    return None


PORTFOLIO_NOTE = ("> This is the valuation part of the report. The rating and the account-by-account moves "
                  "are in the Monthly meeting tab.")


def valuation_view(md):
    """Report text for the tracker's reader: drop the portfolio parts (Decision, Allocation, Summary).

    The page's analysis view judges price against value only; portfolio advice lives in the monthly letter.
    The full report stays on disk.
    """
    out, skip = [], False
    for line in md.splitlines():
        if line.startswith("## "):
            title = line[3:].strip().lower()
            skip = title.startswith("decision") or title.startswith("11.") or title.startswith("summary")
            if title.startswith("decision"):
                out += [PORTFOLIO_NOTE, ""]
        elif line.startswith("<!-- price-blind:start"):
            skip = False
        if skip:
            continue
        if re.match(r"^\s*(\*\*)?Rating[:*]", line):
            continue
        out.append(line)
    return "\n".join(out)


def verdict(price, rec, settings):
    """Buy / Hold / Sell for the page (fixed rule from settings): by default Buy at or below 0.80 x my value,
    Sell at or above 1.20 x my value, Hold in between. The same for every record, old or new,
    range-only included; confidence does not widen it. Returns (call, bands, basis)."""
    vb, basis = bands.record_verdict_bands(rec, settings)
    return bands.verdict(price, vb), vb, basis


def implied_return_now(rec, price):
    """Price-implied return at today's price, from the record's saved model file: the yearly return
    a buyer at this price earns if the weighted forecast comes true. None without a dcf.py model."""
    model = bands.load_model_for(rec, ROOT)
    if model is None or not price:
        return {"price_implied_return": None, "note": None}
    import dcf
    try:
        return dcf.implied_return(model, price)
    except Exception:  # one bad model must not stop the page build
        return {"price_implied_return": None, "note": "could not solve"}


def zone(price, buy, trim, sell):
    if price is None or buy is None:
        return "no bands"
    if price <= buy:
        return "buy zone"
    if sell is not None and price >= sell:
        return "sell zone"
    if trim is not None and price >= trim:
        return "trim zone"
    return "hold zone"


def main():
    holdings = load(DATA / "holdings.json")
    prices = load(DATA / "prices.json", {"prices": {}, "refreshed_at": None})
    px = prices["prices"]
    BUILD.mkdir(exist_ok=True)

    rows = []
    for a in holdings["accounts"]:
        for p in a["positions"]:
            live = px.get(p["ticker"], {}) if p["type"] != "cash" else {}
            price = live.get("price", p["price"])
            prev = live.get("previous_close") or (price if p["type"] == "cash" else None)
            mv = round(p["shares"] * price, 2)
            day_ps = round(price - prev, 4) if prev else None
            rows.append({
                "account": a["name"], "account_id": a["id"], "tax_type": a["tax_type"],
                "account_purpose": a.get("purpose", ""),
                "ticker": p["ticker"], "name": p["name"], "type": p["type"],
                # Share of this position that falls with the stock market (1 = all of it). Optional in holdings.json.
                "stock_exposure": p.get("stock_exposure"),
                "shares": p["shares"], "price": price, "previous_close": prev,
                "price_change": day_ps,
                "day_change_pct": round(price / prev - 1, 5) if prev else None,
                "day_change": round(p["shares"] * day_ps, 2) if day_ps is not None else None,
                "market_value": mv, "cost_basis": p["cost_basis"],
                "gain": round(mv - p["cost_basis"], 2),
                "gain_pct": round(mv / p["cost_basis"] - 1, 5) if p["cost_basis"] else None,
                "dividend_yield": live.get("dividend_yield"),
                "price_stale": p["type"] != "cash" and (bool(live.get("stale")) or not live),
            })
        if a.get("cash"):
            rows.append({
                "account": a["name"], "account_id": a["id"], "tax_type": a["tax_type"],
                "account_purpose": a.get("purpose", ""), "stock_exposure": 0,
                "ticker": "CASH", "name": "Cash", "type": "cash", "shares": a["cash"], "price": 1.0,
                "previous_close": 1.0, "price_change": 0.0, "day_change_pct": 0.0, "day_change": 0.0,
                "market_value": a["cash"], "cost_basis": a["cash"], "gain": 0.0, "gain_pct": 0.0,
                "dividend_yield": None, "price_stale": False,
            })
    total = sum(r["market_value"] for r in rows)
    acct_total = {}
    for r in rows:
        acct_total[r["account_id"]] = acct_total.get(r["account_id"], 0) + r["market_value"]
    for r in rows:
        r["weight"] = round(r["market_value"] / total, 5) if total else 0
        r["pct_of_account"] = round(r["market_value"] / acct_total[r["account_id"]], 5) if acct_total[r["account_id"]] else 0

    meta = [
        {"label": "Holdings as of", "value": holdings["as_of"]},
        {"label": "Prices refreshed", "value": str(prices.get("refreshed_at"))},
        {"label": "Price source", "value": prices.get("source", "holdings snapshot")},
        {"label": "Dividend yield", "value": "Trailing 12 months of dividends divided by the latest price"},
        {"label": "Built by", "value": "scripts/build_tracker.py"},
    ]

    # Performance: how each account's current holdings did over each period, against the S&P 500.
    # Uses adjusted closes, so dividends count. Trades and deposits during the period are not modeled.
    periods = ["1m", "3m", "ytd", "1y", "3y", "5y", "10y"]

    def ret(ticker, period):
        live = px.get(ticker, {})
        anchor = (live.get("return_anchors") or {}).get(period)
        return live["adj_now"] / anchor - 1 if anchor and live.get("adj_now") else None

    def group_perf(label, gid, members):
        out = {"group": label, "group_id": gid, "value": round(sum(r["market_value"] for r in members), 2)}
        prev_total = sum(r["shares"] * r["previous_close"] for r in members if r["previous_close"])
        now_total = sum(r["market_value"] for r in members if r["previous_close"])
        out["day"] = round(now_total / prev_total - 1, 5) if prev_total else None
        for per in periods:
            start, covered = 0.0, 0.0
            for r in members:
                rr = 0.0 if r["type"] == "cash" else ret(r["ticker"], per)
                if rr is None:
                    continue
                start += r["market_value"] / (1 + rr)
                covered += r["market_value"]
            out[per] = round(covered / start - 1, 5) if start else None
            out[per + "_coverage"] = round(covered / out["value"], 4) if out["value"] else None
        return out

    perf = [group_perf(a["name"], a["id"], [r for r in rows if r["account_id"] == a["id"]]) for a in holdings["accounts"]]
    perf.append(group_perf("All accounts", "all", rows))
    spy = px.get("SPY", {})
    sp = {"group": "S&P 500 (SPY)", "group_id": "spy", "value": None,
          "day": round(spy["price"] / spy["previous_close"] - 1, 5) if spy.get("previous_close") else None}
    for per in periods:
        r = ret("SPY", per)
        sp[per] = round(r, 5) if r is not None else None
        sp[per + "_coverage"] = 1.0 if r is not None else None
    perf.append(sp)
    (BUILD / "performance.json").write_text(json.dumps({"rows": perf, "meta": [
        {"label": "Method", "value": "Each account's current holdings, valued at the start of each period with adjusted closes "
                                     "(dividends reinvested). Trades, deposits, and withdrawals during the period are not counted, "
                                     "so this is how today's holdings did, not the account's actual return."},
        {"label": "Benchmark", "value": "SPY, an S&P 500 index fund, total return"},
        {"label": "Coverage", "value": "<period>_coverage is the share of the account's value with a full price history for that period"},
        {"label": "Prices refreshed", "value": str(prices.get("refreshed_at"))},
    ]}, indent=1) + "\n")

    # Latest analysis text per ticker, for the page's analysis reader.
    arows = []
    adir = ROOT / "analyses"
    if adir.exists():
        for tdir in sorted(p for p in adir.iterdir() if p.is_dir()):
            # A same-day re-run is saved as <date>-<n>.md and sorts after <date>.md.
            # Revision drafts (<date>-<n>-r2.md) are not reports and are skipped.
            def report_key(f):
                m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})(?:-(\d+))?\.md", f.name)
                return (m.group(1), int(m.group(2) or 1)) if m else None
            reports = sorted((f for f in tdir.glob("*.md") if report_key(f)), key=report_key)
            if reports:
                arows.append({"ticker": tdir.name.replace("-", "."), "date": report_key(reports[-1])[0],
                              "older_reports": len(reports) - 1, "text": valuation_view(reports[-1].read_text())})
    (BUILD / "analyses.json").write_text(json.dumps({"rows": arows, "meta": [
        {"label": "Source", "value": "analyses/<TICKER>/<date>[-n].md, newest report per ticker"}]}) + "\n")

    settings = bands.load_settings(ROOT)
    snapshot = {p["ticker"]: p["price"] for a in holdings["accounts"] for p in a["positions"]}
    vrows = []
    for t in sorted({r["ticker"] for r in rows if r["type"] in ("stock", "fund")}):
        v = latest_valuation(t)
        live = px.get(t, {})
        price = live.get("price", snapshot.get(t))
        price_stale = bool(live.get("stale")) or not live
        if not v:
            vrows.append({"ticker": t, "status": "not yet analyzed", "price": price, "price_stale": price_stale, "zone": "no bands"})
            continue
        buy = pick(v, "bands.buy_below", "buy_below")
        trim = pick(v, "bands.trim_above", "trim_above")
        sell = pick(v, "bands.sell_above", "sell_above")
        fair = pick(v, "values.weighted", "weighted_value", "values.base", "base_value")
        last = pick(v, "date", "analysis_date") or ""
        try:
            next_review = date.fromordinal(date.fromisoformat(last[:10]).toordinal() + 30).isoformat()
        except ValueError:
            next_review = None
        review_price = pick(v, "audit.price")
        valid_until = pick(v, "bands.valid_until")
        now_zone = zone(price, buy, trim, sell)
        moved = round(price / review_price - 1, 4) if price and review_price else None
        now_verdict, vb, vbasis = verdict(price, v, settings)
        ir_now = implied_return_now(v, price)
        # Today's rule at the review price, so a verdict string stored under an older rule never flags a change.
        review_verdict = verdict(review_price, v, settings)[0]
        status_v = pick(v, "lock.valuation_status")
        earnings = pick(v, "next_review.next_earnings_expected")
        earnings_passed = bool(earnings and earnings <= date.today().isoformat()
                               and earnings > (pick(v, "information_cutoff") or ""))
        vrows.append({
            "ticker": t, "status": "analyzed", "price": price, "price_stale": price_stale,
            "fair_value": fair,
            # Letter action prices (hurdle-based). Kept under their old names so the page keeps working.
            "buy_below": buy, "trim_above": trim, "sell_above": sell,
            "margin_of_safety": round(1 - price / fair, 4) if price and fair else None,
            "verdict": now_verdict,
            "verdict_at_review": review_verdict,
            "buy_below_price": vb.get("buy_below_price"), "sell_above_price": vb.get("sell_above_price"),
            "verdict_band_basis": vbasis if vb.get("buy_below_price") is not None else None,
            "valuation_status": status_v,
            "range_low": pick(v, "bands.range_low", "values.bear"), "range_high": pick(v, "bands.range_high", "values.bull"),
            "price_implied_return": ir_now["price_implied_return"],
            "price_implied_return_note": ir_now["note"],
            "price_implied_return_at_review": pick(v, "audit.price_implied_return"),
            "required_return": pick(v, "rates.discount_rate"),
            "price_vs_fair": round(price / fair - 1, 4) if price and fair else None,
            "quality": pick(v, "grades.quality", "quality_grade", "quality"),
            "confidence": pick(v, "confidence", "confidence.level"),
            "expected_return_10y": pick(v, "audit.expected_return_10y"),
            "price_isolation": pick(v, "price_isolation.status"),
            "price_at_review": review_price, "moved_since_review": moved,
            "bands_valid_until": valid_until,
            "bands_stale": bool(valid_until and valid_until < date.today().isoformat()),
            "last_review": last[:10], "next_review": pick(v, "next_review.due") or next_review,
            "zone": now_zone,
            # Off-cycle refresh trigger: the price crossed a call price since the review,
            # or the next earnings report has come out since the record's information cutoff.
            "needs_review": bool((review_verdict and now_verdict and review_verdict != now_verdict) or earnings_passed),
        })
    vmeta = [
        {"label": "Valuation records", "value": "data/valuations/<TICKER>.json, newest record per ticker"},
        {"label": "Method", "value": "analyze-stock skill. My value is the probability-weighted value per share. "
                                     "Call: Buy at or below 80% of my value (buy_below_price), Sell at or above 120% "
                                     "(sell_above_price), Hold in between. One fixed rule for every stock; confidence does "
                                     "not change it. required_return is the stock's discount rate, the "
                                     "return it should earn for its risk. buy_below, trim_above, and sell_above are the "
                                     "monthly letter's action prices."},
        {"label": "Prices refreshed", "value": str(prices.get("refreshed_at"))},
    ]
    (BUILD / "valuations.json").write_text(json.dumps({"rows": vrows, "meta": vmeta}, indent=1) + "\n")

    # Positions carry their stock's valuation verdict, in place of a broker's own rating column.
    vby = {v["ticker"]: v for v in vrows}
    for r in rows:
        v = vby.get(r["ticker"], {})
        r["verdict"] = v.get("verdict") if v.get("status") == "analyzed" else None
    (BUILD / "positions.json").write_text(json.dumps({"rows": rows, "meta": meta}, indent=1) + "\n")

    # Private-company holdings (optional): stock options by grant, or plain shares. No market price.
    prows = []
    for h in holdings.get("private_holdings", []):
        base = {"company": h["company"], "relationship": h.get("relationship", ""),
                "value_per_share": h.get("fair_market_value_per_share"), "note": h.get("valuation_note", "")}
        if "grants" in h:
            for g in h["grants"]:
                prows.append({**base, "holding": f"{g['grant']} options",
                              "units": g["granted"], "vested": g["vested"], "strike": g["strike"],
                              "cost_to_exercise_vested": round(g["vested"] * g["strike"], 2)})
        else:
            prows.append({**base, "holding": h.get("label", "Common stock"),
                          "units": h["shares"], "vested": h["shares"], "strike": None,
                          "cost_to_exercise_vested": None, "cost_basis": h.get("cost_basis")})
    (BUILD / "private.json").write_text(json.dumps({"rows": prows, "meta": [
        {"label": "Source", "value": f"{holdings.get('private_source', 'private_holdings in data/holdings.json')}, "
                                     f"holdings as of {holdings['as_of']}"}]}, indent=1) + "\n")

    # Monthly meeting letters (advisor-style rebalancing notes), newest first.
    mrows = []
    rdir = ROOT / "reviews"
    if rdir.exists():
        for f in sorted(rdir.glob("*-meeting.md"), reverse=True):
            text = f.read_text()
            title = next((l[2:].strip() for l in text.splitlines() if l.startswith("# ")), f.stem)
            mrows.append({"date": f.name[:10], "title": title, "text": text})
    (BUILD / "meetings.json").write_text(json.dumps({"rows": mrows, "meta": [
        {"label": "Source", "value": "reviews/<date>-meeting.md, written by the portfolio-review skill"}]}) + "\n")

    print(f"meetings {len(mrows)}, positions {len(rows)}, valuations {len(vrows)}, private {len(prows)}, total ${total:,.2f}")


if __name__ == "__main__":
    main()
