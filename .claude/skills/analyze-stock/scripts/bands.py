#!/usr/bin/env python3
"""Rates, confidence, price bands, and return math for the analyze-stock skill.

Every band the tracker shows comes from the functions in this file, so anyone can
recompute a band from the saved record. Standard library only (Python 3.9+).

Commands:
  bands.py rates   --risk-free-observed 0.043 --tier average [--ticker T --mode refresh]
  bands.py compute --value 100 --discount-rate 0.088 --risk-free-used 0.043 --confidence Medium
  bands.py returns --lock analyses/T/2026-01-01-lock.json --price 80 [--model M]

Two kinds of band:
  action bands    buy_below_price and sell_above_price: my value (the probability-weighted
                  value) times 0.80 and 1.20, the same for every stock whatever the confidence.
                  They set the Buy / Hold / Sell call the tracker shows.
  letter prices   buy_below, trim_above, sell_above: built with the hurdle rate. They feed
                  the monthly letter only. They never set the call.
An older method version widened the verdict bands by confidence; that is retired.

All rates are decimals: 0.10 means 10% a year.
"""
import argparse
import json
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SETTINGS = SKILL_DIR / "references" / "settings.default.json"

LEVELS = ["High", "Medium", "Low", "Very low"]
TIERS = ["defensive", "average", "cyclical_or_levered", "speculative"]
ZONES = ["buy zone", "hold zone", "trim zone", "sell zone", "no bands"]
VERDICTS = ["Buy", "Hold", "Sell"]
# Verdict strings from an older method version. Kept so old records still validate.
OLD_VERDICTS = ["Underpriced", "Fairly priced", "Overpriced", "Cannot be valued with confidence"]
RANGE_ONLY = "range_only"


def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def find_root(root=None):
    """The project folder: the parent of the .claude folder this skill lives in."""
    if root:
        return Path(root).resolve()
    for parent in Path(__file__).resolve().parents:
        if parent.name == ".claude":
            return parent.parent
    return Path.cwd()


def safe_ticker(ticker):
    """File-safe ticker. Matches scripts/build_tracker.py: ABC.B -> ABC-B."""
    return ticker.upper().replace(".", "-").replace("/", "-")


def valuations_path(root, ticker):
    return Path(root) / "data" / "valuations" / f"{safe_ticker(ticker)}.json"


def load_records(root, ticker):
    """Current records for a ticker, oldest first. Empty list when there is no file."""
    path = valuations_path(root, ticker)
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    records = data.get("records", []) if isinstance(data, dict) else data
    return sorted([r for r in records if isinstance(r, dict)], key=lambda r: r.get("date", ""))


def _merge(base, over):
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _merge(base[k], v)
        else:
            base[k] = v


def load_settings(root=None):
    settings = json.loads(DEFAULT_SETTINGS.read_text())
    settings["settings_source"] = "skill defaults"
    override = find_root(root) / "context" / "analysis-settings.json"
    if override.exists():
        _merge(settings, json.loads(override.read_text()))
        settings["settings_source"] = "context/analysis-settings.json over skill defaults"
    return settings


# ---------- rates ----------

def risk_free_used(observed, settings, prior_used=None):
    """Observed 10-year Treasury yield, floored. A refresh keeps the prior rate
    unless the floored yield moved by the update threshold or more. This stops
    small rate moves from shifting every band every month."""
    floored = round(max(observed, settings["risk_free_floor"]), 4)
    if prior_used is not None and round(abs(floored - prior_used), 6) < settings["rate_update_threshold"]:
        return prior_used
    return floored


def prior_risk_free(records, before_date):
    """The rate used by the latest valued record dated before `before_date`, or None."""
    for r in reversed(records):
        rf = (r.get("rates") or {}).get("risk_free_used")
        if r.get("date", "") < before_date and rf is not None:
            return rf
    return None


def discount_rate(rf_used, tier, settings):
    if tier not in TIERS:
        die(f"risk tier must be one of {TIERS}, got {tier!r}")
    return round(rf_used + settings["equity_risk_premium"] + settings["risk_tier_adjustments"][tier], 4)


def required_return(disc_rate, settings):
    """The larger of the owner's hurdle rate and the stock's own discount rate."""
    return round(max(settings["hurdle_rate"], disc_rate), 4)


# ---------- confidence ----------

def spread_points(bear, bull, weighted):
    if not weighted or weighted <= 0:
        return 3
    spread = (bull - bear) / weighted
    return 0 if spread < 0.5 else 1 if spread < 1.0 else 2 if spread < 1.5 else 3


def terminal_points(share):
    if share is None:
        return 0
    return 0 if share < 0.60 else 1 if share <= 0.75 else 2


def cash_points(cash_reliability):
    return {"High": 0, "Medium": 1, "Low": 2}[cash_reliability]


def evidence_points(weak_count):
    return min(weak_count, 2)


def level_from_points(total):
    return "High" if total <= 2 else "Medium" if total <= 4 else "Low" if total <= 6 else "Very low"


# ---------- bands ----------

def _anchor(value, disc_rate, target_rate, years):
    """Price at which the forecast annual return over `years` equals target_rate,
    when the business value grows at disc_rate and price meets value at the end."""
    return value * ((1 + disc_rate) / (1 + target_rate)) ** years


def compute_bands(value, disc_rate, req_return, rf_used, level, settings):
    """Return the band dict. All inputs are price-blind."""
    empty = {"fair_value": None, "buy_below": None, "trim_above": None, "sell_above": None,
             "buy_return_rate": None, "trim_return_rate": None, "sell_return_rate": None,
             "error_cushion": None, "horizon_years": settings["horizon_years"]}
    if value is None or level is None:
        return empty
    if value <= 0:
        empty["fair_value"] = 0.0
        return empty
    if level not in LEVELS:
        die(f"confidence must be one of {LEVELS}, got {level!r}")
    if disc_rate <= rf_used:
        die("discount rate must be above the risk-free rate")
    years = settings["horizon_years"]
    cushion = settings["error_cushion"][level]
    premium = disc_rate - rf_used
    trim_rate = round(rf_used + settings["trim_premium_share"] * premium, 4)
    sell_rate = round(rf_used + settings["sell_premium_share"] * premium, 4)
    return {
        "fair_value": round(value, 2),
        "buy_below": round(_anchor(value, disc_rate, req_return, years) * (1 - cushion), 2),
        "trim_above": round(_anchor(value, disc_rate, trim_rate, years) * (1 + cushion), 2),
        "sell_above": round(_anchor(value, disc_rate, sell_rate, years) * (1 + cushion), 2),
        "buy_return_rate": req_return,
        "trim_return_rate": trim_rate,
        "sell_return_rate": sell_rate,
        "error_cushion": cushion,
        "horizon_years": years,
    }


def action_bands(value, settings):
    """The fixed Buy / Hold / Sell rule (settings action_bands): by default Buy at or below 0.80 x my value,
    Sell at or above 1.20 x my value, Hold in between. Confidence does not widen it."""
    out = {"buy_below_price": None, "sell_above_price": None, "buy_ratio": None, "sell_ratio": None}
    if value is None or value <= 0:
        return out
    ab = settings["action_bands"]
    out.update(buy_below_price=round(value * ab["buy_below"], 2), sell_above_price=round(value * ab["sell_above"], 2),
               buy_ratio=ab["buy_below"], sell_ratio=ab["sell_above"])
    return out


def verdict_bands(value, level, settings):
    """Kept for older callers. `level` is ignored: confidence no longer widens the bands."""
    return action_bands(value, settings)


def verdict(price, bands, status=None):
    """Buy / Hold / Sell from price and the action bands. Same rule as scripts/build_tracker.py.
    `status` is ignored: a range-only value gets a call from its weighted value like any other."""
    low, high = bands.get("buy_below_price"), bands.get("sell_above_price")
    if price is None or low is None or high is None:
        return None
    if price <= low:
        return "Buy"
    if price >= high:
        return "Sell"
    return "Hold"


def range_only_test(values, settings):
    """Improvement 7. True when the bull case supplies most of the fair value, or the
    bear-to-bull range is wide against it. A value like that is a range, not a point."""
    w, bull, bear = values.get("weighted"), values.get("bull"), values.get("bear")
    p = (values.get("probabilities") or {}).get("bull")
    rule = settings["range_only"]
    if not w or w <= 0 or bull is None or bear is None or p is None:
        return {"trips": False, "bull_share": None, "spread": None}
    bull_share = round(p * bull / w, 4)
    spread = round((bull - bear) / w, 4)
    trips = bull_share > rule["max_bull_share_of_value"] or spread >= rule["max_spread_to_value"]
    return {"trips": trips, "bull_share": bull_share, "spread": spread}


def record_verdict_bands(record, settings):
    """Action bands for any record, old or new: my value (values.weighted) times the fixed ratios
    in today's settings. Stored verdict bands from an older method version are history and are not used. Returns (bands, basis)."""
    value = (record.get("values") or {}).get("weighted")
    return action_bands(value, settings), "my value x the fixed 20% rule"


def lower_level(level):
    """One confidence step down. Very low stays Very low."""
    return LEVELS[min(LEVELS.index(level) + 1, len(LEVELS) - 1)]


def zone(price, bands):
    """Same rule as scripts/build_tracker.py, so the report and the page agree."""
    buy, trim, sell = bands.get("buy_below"), bands.get("trim_above"), bands.get("sell_above")
    if price is None or buy is None:
        return "no bands"
    if price <= buy:
        return "buy zone"
    if sell is not None and price >= sell:
        return "sell zone"
    if trim is not None and price >= trim:
        return "trim zone"
    return "hold zone"


def annual_return(price, value, disc_rate, years):
    """Convergence return: the yearly return from buying at `price` IF the business value
    grows at disc_rate (payouts included) AND the price meets fair value after `years`.
    Reports label it "if the price falls to my value within ten years". It is not
    the headline; the price-implied return is (dcf.implied_return)."""
    if value is None or price is None or price <= 0:
        return None
    if value <= 0:
        return -1.0
    return round((1 + disc_rate) * (value / price) ** (1.0 / years) - 1, 4)


def load_model_for(record, root=None, model_path=None):
    """The saved dcf.py model behind a lock, or None (for example a custom calculation script)."""
    rel = model_path or record.get("model_path")
    if not rel:
        return None
    path = Path(rel) if Path(rel).is_absolute() else find_root(root) / rel
    if path.suffix != ".json" or not path.exists():
        return None
    raw = path.read_bytes()
    want = (record.get("lock") or {}).get("model_sha256")
    if want and model_path is None:
        import hashlib
        if hashlib.sha256(raw).hexdigest() != want:
            return None   # the model file changed after the lock; do not compute from it
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def audit_numbers(record, price, settings, model=None):
    """Price-dependent numbers for the audit, computed from a lock (partial record).

    Headline: the price-implied return, the yearly return a buyer at `price` earns if the
    model's cash flows come true and nothing is assumed about the future price.
    The convergence figure (expected_return_10y) is kept as one labeled line."""
    values, bands, rates = record["values"], record["bands"], record["rates"]
    status = record["lock"]["valuation_status"]
    fair, r = values.get("weighted"), rates.get("discount_rate")
    out = {"price_to_value": None, "margin_of_safety": None, "verdict": verdict(price, action_bands(values.get("weighted"), settings)),
           "zone": zone(price, bands), "price_implied_return": None, "price_implied_return_note": None,
           "implied_growth_shift": None, "expected_return_10y": None,
           "return_comparison": None, "gap_audit_required": False}
    if fair is None or r is None:
        return out
    out["price_to_value"] = round(price / fair, 4) if fair > 0 else None
    out["margin_of_safety"] = round(1 - price / fair, 4) if fair > 0 else None
    out["expected_return_10y"] = annual_return(price, fair, r, 10)
    if model is not None:
        import dcf  # same folder
        try:
            implied = dcf.implied_return(model, price)
            out["price_implied_return"] = implied["price_implied_return"]
            out["price_implied_return_note"] = implied["note"]
            out["implied_growth_shift"] = dcf.solve_price(model, price)
        except dcf.ModelError as e:
            out["price_implied_return_note"] = f"could not solve: {e}"
    else:
        out["price_implied_return_note"] = "no dcf.py model file; compute it from the saved calculation script"
    rf_obs = rates.get("risk_free_observed")
    pir = out["price_implied_return"]
    out["return_comparison"] = {
        "discount_rate": r, "risk_free_observed": rf_obs,
        "implied_minus_discount_rate": round(pir - r, 4) if pir is not None else None,
        "implied_minus_risk_free": round(pir - rf_obs, 4) if pir is not None and rf_obs is not None else None}
    mos = out["margin_of_safety"]
    out["gap_audit_required"] = bool(
        (mos is not None and abs(mos) > settings["large_gap_threshold"])
        or (values.get("bear") is not None and price < values["bear"])
        or (values.get("bull") is not None and price > values["bull"]))
    return out


# ---------- command line ----------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("rates", help="discount rate and required return for a risk tier")
    p.add_argument("--risk-free-observed", type=float, required=True, help="10-year Treasury yield as a decimal")
    p.add_argument("--tier", required=True, choices=TIERS)
    p.add_argument("--ticker", help="with --mode refresh, carry the prior record's rate when the yield barely moved")
    p.add_argument("--mode", choices=["full", "refresh"], default="full")
    p.add_argument("--date", help="analysis date, YYYY-MM-DD (default: today)")
    p.add_argument("--root")

    p = sub.add_parser("compute", help="bands from a value (a calculator; record.py lock does this for real runs)")
    p.add_argument("--value", type=float, required=True)
    p.add_argument("--discount-rate", type=float, required=True)
    p.add_argument("--risk-free-used", type=float, required=True)
    p.add_argument("--confidence", required=True, choices=LEVELS)
    p.add_argument("--root")

    p = sub.add_parser("returns", help="verdict, price-implied return, convergence figure, and gap check at a price (after the lock only)")
    p.add_argument("--lock", required=True)
    p.add_argument("--price", type=float, required=True)
    p.add_argument("--model", help="the dcf.py model file (default: the lock's model_path)")
    p.add_argument("--root")

    a = ap.parse_args()
    settings = load_settings(a.root)

    if a.cmd == "rates":
        prior = None
        if a.mode == "refresh" and a.ticker:
            from datetime import date as _date
            prior = prior_risk_free(load_records(find_root(a.root), a.ticker), a.date or _date.today().isoformat())
        rf = risk_free_used(a.risk_free_observed, settings, prior)
        dr = discount_rate(rf, a.tier, settings)
        print(json.dumps({"risk_free_observed": a.risk_free_observed, "risk_free_used": rf,
                          "carried_from_prior_record": prior is not None and rf == prior,
                          "risk_tier": a.tier, "discount_rate": dr,
                          "required_return": required_return(dr, settings),
                          "settings_source": settings["settings_source"]}, indent=2))
    elif a.cmd == "compute":
        req = required_return(a.discount_rate, settings)
        out = compute_bands(a.value, a.discount_rate, req, a.risk_free_used, a.confidence, settings)
        out.update(action_bands(a.value, settings))
        print(json.dumps(out, indent=2))
    elif a.cmd == "returns":
        record = json.loads(Path(a.lock).read_text())
        nums = audit_numbers(record, a.price, settings, load_model_for(record, a.root, a.model))
        print(json.dumps(nums, indent=2))
        pir, conv = nums["price_implied_return"], nums["expected_return_10y"]
        print(f"\nWhat you earn at this price: {pir:.1%} a year if you hold and the forecast is right."
              if pir is not None else f"\nPrice-implied return: {nums['price_implied_return_note']}", file=sys.stderr)
        if conv is not None:
            print(f"If the price falls to my value within ten years: {conv:.1%} a year.", file=sys.stderr)


if __name__ == "__main__":
    main()
