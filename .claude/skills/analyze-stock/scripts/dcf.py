#!/usr/bin/env python3
"""Discounted cash flow math for the analyze-stock skill.

The analyst writes the forecast into a model file (JSON). This script does the
discounting, the claims bridge, the roll to today's date, and the sensitivity
tests. The same model file always gives the same values. Standard library only.

Usage:
  dcf.py <model.json> --out <model-result.json>
  dcf.py <model.json> --solve-price 80      # after the lock only: what the price implies
                                            # (growth shift and price-implied return)

Model file format: see references/valuation.md, "The model file".
Money amounts and share counts must use the same scale (for example, both in millions).
All rates are decimals: 0.10 means 10% a year.
"""
import argparse
import copy
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

WEIGHTED = ("bear", "base", "bull")


class ModelError(Exception):
    pass


def die(msg):
    raise ModelError(msg)


def years_between(d0, d1):
    return (date.fromisoformat(d1) - date.fromisoformat(d0)).days / 365.25


def terminal_cash_flow(term, rate_for_fade=None):
    """Cash flow for the first year after the forecast, and the growth rate."""
    method = term.get("method", "none")
    if method == "gordon":
        return term["next_year_cash_flow"], term["growth"]
    if method == "value_driver":
        g = term["growth"]
        ronc = rate_for_fade if rate_for_fade is not None else term["return_on_new_capital"]
        if ronc <= g:
            die("terminal return_on_new_capital must be above terminal growth")
        return term["next_year_earnings"] * (1 - g / ronc), g
    return None, None


def value_scenario(name, sc, model, rate, equity_rate, fade=False):
    """Value one scenario. Returns a dict of the parts and the value per share."""
    basis, mid = model["basis"], model.get("mid_period", True)
    stub = years_between(model["model_date"], model["first_forecast_year_end"])
    if not 0 < stub <= 1.01:
        die("first_forecast_year_end must be within one year after model_date")
    flows = sc["cash_flows"]
    if not flows:
        die(f"{name}: cash_flows is empty")

    pv_explicit = 0.0
    for k, cf in enumerate(flows):
        if k == 0:
            t = stub / 2 if mid else stub          # the rest of the first forecast year
        else:
            t = stub + k - (0.5 if mid else 0.0)
        pv_explicit += cf / (1 + rate) ** t

    horizon = stub + len(flows) - 1
    term = sc.get("terminal", {"method": "none"})
    method = term.get("method", "none")
    if method in ("gordon", "value_driver"):
        cf_next, g = terminal_cash_flow(term, rate if fade and method == "value_driver" else None)
        if rate - g < 0.01:
            die(f"{name}: terminal growth {g} is too close to the discount rate {rate}; the formula breaks down")
        t_tv = horizon - (0.5 if mid else 0.0)      # mid-period flows after the horizon
        pv_terminal = (cf_next / (rate - g)) / (1 + rate) ** t_tv
    elif method == "fixed":
        pv_terminal = term["value"] / (1 + rate) ** horizon
    elif method == "none":
        pv_terminal = 0.0
    else:
        die(f"{name}: unknown terminal method {method!r}")

    operating = pv_explicit + pv_terminal
    c = sc.get("claims", {})
    allowed = {"firm": ("cash_and_investments", "other_assets", "debt", "leases", "other_claims"),
               "equity": ("excess_cash", "other_assets", "other_claims", "debt", "leases", "cash_and_investments")}
    unknown = sorted(set(c) - set(allowed.get(basis, ())))
    if basis in allowed and unknown:
        die(f"{name}: unknown claims keys {unknown} for {basis} basis. "
            f"Allowed: {list(allowed[basis][:5] if basis == 'firm' else allowed[basis][:3])}")
    if basis == "firm":
        equity = (operating + c.get("cash_and_investments", 0) + c.get("other_assets", 0)
                  - c.get("debt", 0) - c.get("leases", 0) - c.get("other_claims", 0))
    elif basis == "equity":
        for k in ("debt", "leases", "cash_and_investments"):
            if c.get(k):
                die(f"{name}: on equity basis the cash flows are already after interest and debt service. "
                    f"Remove claims.{k}. Use claims.excess_cash for cash the business does not need.")
        equity = operating + c.get("excess_cash", 0) + c.get("other_assets", 0) - c.get("other_claims", 0)
    else:
        die("basis must be 'equity' or 'firm'")

    shares = sc["diluted_shares"]
    if shares <= 0:
        die(f"{name}: diluted_shares must be positive")
    per_share_model_date = equity / shares
    roll = years_between(model["model_date"], model["valuation_date"])
    if roll < 0:
        die("valuation_date is before model_date")
    raw = per_share_model_date * (1 + equity_rate) ** roll - model.get("payouts_per_share_since_model_date", 0.0)
    return {
        "probability": sc.get("probability"),
        "pv_explicit": round(pv_explicit, 4),
        "pv_terminal": round(pv_terminal, 4),
        "terminal_share": round(pv_terminal / operating, 4) if operating > 0 else None,
        "operating_value": round(operating, 4),
        "equity_value_model_date": round(equity, 4),
        "diluted_shares": shares,
        "value_per_share_model_date": round(per_share_model_date, 4),
        "value_per_share_raw": round(raw, 4),
        "value_per_share": round(max(raw, 0.0), 2),   # a share cannot be worth less than zero
    }


def run(model, rate_shift=0.0, growth_shift=0.0, fade=False):
    m = copy.deepcopy(model)
    rate = m["discount_rate"] + rate_shift
    equity_rate = m.get("equity_rate", m["discount_rate"]) + rate_shift
    out = {}
    for name, sc in m["scenarios"].items():
        if growth_shift and sc.get("terminal", {}).get("method") in ("gordon", "value_driver"):
            sc["terminal"]["growth"] += growth_shift
        out[name] = value_scenario(name, sc, m, rate, equity_rate, fade)
    return out


def weighted(results):
    return round(sum(results[s]["probability"] * results[s]["value_per_share"] for s in WEIGHTED), 2)


def check(model):
    for key in ("ticker", "basis", "model_date", "valuation_date", "first_forecast_year_end", "discount_rate", "scenarios"):
        if key not in model:
            die(f"model file is missing '{key}'")
    for s in WEIGHTED:
        if s not in model["scenarios"]:
            die(f"model file needs a '{s}' scenario")
        p = model["scenarios"][s].get("probability")
        if p is None or not 0 < p < 1:
            die(f"{s}: probability must be between 0 and 1")
    total = sum(model["scenarios"][s]["probability"] for s in WEIGHTED)
    if abs(total - 1) > 1e-6:
        die(f"bear, base, and bull probabilities sum to {total}, not 1")
    extra = set(model["scenarios"]) - set(WEIGHTED) - {"stress"}
    if extra:
        die(f"unknown scenarios {sorted(extra)}; use bear, base, bull, and stress")


def safe_run(model, **kw):
    """A sensitivity run. Returns None when the shifted inputs break the formula."""
    try:
        return run(model, **kw)
    except ModelError:
        return None


def solve_price(model, price):
    """Growth shift x, applied every forecast year to the base case, at which the
    base value equals `price`. Year k's cash flow is scaled by (1+x)^k."""
    def base_value(x):
        m = copy.deepcopy(model)
        sc = m["scenarios"]["base"]
        n = len(sc["cash_flows"])
        sc["cash_flows"] = [cf * (1 + x) ** (k + 1) for k, cf in enumerate(sc["cash_flows"])]
        term = sc.get("terminal", {})
        for key in ("next_year_cash_flow", "next_year_earnings", "value"):
            if key in term:
                term[key] *= (1 + x) ** n
        return value_scenario("base", sc, m, m["discount_rate"], m.get("equity_rate", m["discount_rate"]))["value_per_share_raw"]

    lo, hi = -0.5, 1.0
    f_lo, f_hi = base_value(lo) - price, base_value(hi) - price
    if f_lo * f_hi > 0:
        return None
    for _ in range(80):
        mid = (lo + hi) / 2
        f_mid = base_value(mid) - price
        if f_lo * f_mid <= 0:
            hi = mid
        else:
            lo, f_lo = mid, f_mid
    return round((lo + hi) / 2, 4)


def implied_return(model, price):
    """Price-implied return: the yearly return a buyer at `price` earns if the model's
    probability-weighted cash flows come true. It is the discount rate at which the
    weighted value equals the price. No assumption about the future price is needed.

    The solver moves the discount rate (and, on firm basis, the cost of equity) by the
    same shift x, and reports the cost of equity plus x. When the price is above the
    value at the lowest rate the terminal formula allows, the answer is a bound."""
    equity_rate = model.get("equity_rate", model["discount_rate"])
    growths = [sc.get("terminal", {}).get("growth") for sc in model["scenarios"].values()
               if sc.get("terminal", {}).get("method") in ("gordon", "value_driver")]
    lo = max([g + 0.0101 - model["discount_rate"] for g in growths if g is not None] + [-model["discount_rate"] + 0.0001])
    hi = 0.50

    def value_at(x):
        res = safe_run(model, rate_shift=x)
        return None if res is None else weighted(res)

    v_lo, v_hi = value_at(lo), value_at(hi)
    if v_lo is None or v_hi is None:
        die("the model breaks inside the search range for the price-implied return")
    if price > v_lo:
        bound = round(equity_rate + lo, 4)
        return {"price_implied_return": None, "bound": "below", "bound_value": bound,
                "note": f"under {bound:.1%} a year (the price is above the value at the lowest discount rate the terminal formula allows)"}
    if price < v_hi:
        bound = round(equity_rate + hi, 4)
        return {"price_implied_return": None, "bound": "above", "bound_value": bound,
                "note": f"above {bound:.1%} a year"}
    for _ in range(80):
        mid = (lo + hi) / 2
        v = value_at(mid)
        if v is None or v > price:
            lo = mid
        else:
            hi = mid
    pir = round(equity_rate + (lo + hi) / 2, 4)
    return {"price_implied_return": pir, "bound": None, "bound_value": None,
            "note": f"{pir:.1%} a year if you buy at {price:,.2f}, hold, and the weighted forecast comes true"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model")
    ap.add_argument("--out", help="write the result JSON here")
    ap.add_argument("--solve-price", type=float,
                    help="AFTER THE LOCK ONLY. Print the yearly growth shift to the base case that the price "
                         "implies, and the price-implied return.")
    a = ap.parse_args()

    raw = Path(a.model).read_bytes()
    model = json.loads(raw)
    check(model)

    if a.solve_price is not None:
        x = solve_price(model, a.solve_price)
        ir = implied_return(model, a.solve_price)
        print(json.dumps({"price": a.solve_price, "implied_growth_shift": x,
                          "meaning": ("no growth shift between -50% and +100% a year reaches this price" if x is None else
                                      f"the price matches the base case if cash flows grow {abs(x):.1%} a year "
                                      f"{'faster' if x > 0 else 'slower'} than forecast, every forecast year"),
                          "price_implied_return": ir["price_implied_return"],
                          "price_implied_return_bound": ir["bound"] and {"side": ir["bound"], "value": ir["bound_value"]},
                          "price_implied_return_meaning": ir["note"]}, indent=2))
        return

    results = run(model)
    warnings = []
    for name, r in results.items():
        if r["value_per_share_raw"] < 0:
            warnings.append(f"{name}: raw value per share is negative; floored at zero")
        if r["terminal_share"] is not None and r["terminal_share"] > 0.80:
            warnings.append(f"{name}: {r['terminal_share']:.0%} of the value comes from the terminal value")
        g = model["scenarios"][name].get("terminal", {}).get("growth")
        # Check against the OBSERVED yield, not the floored one (v9, improvement 6c): a floor
        # raises the discount rate but does not make the economy grow faster.
        rf_obs, rf_used = model.get("risk_free_observed"), model.get("risk_free_used")
        rf = rf_obs if rf_obs is not None else rf_used
        label = "observed risk-free rate" if rf_obs is not None else "risk-free rate used (add risk_free_observed to the model)"
        if g is not None and rf is not None and g > rf:
            warnings.append(f"{name}: terminal growth {g:.1%} is above the {label} {rf:.2%}; justify it or lower it")
    if not (results["bear"]["value_per_share"] <= results["base"]["value_per_share"] <= results["bull"]["value_per_share"]):
        warnings.append("values are not ordered bear <= base <= bull")
    if model.get("risk_free_observed") is None and any(
            sc.get("terminal", {}).get("growth") is not None for sc in model["scenarios"].values()):
        warnings.append("risk_free_observed is missing; the terminal-growth check fell back to the floored rate")
    if years_between(model["model_date"], model["valuation_date"]) > 0.5:
        warnings.append("model_date is more than six months before valuation_date; use a newer balance sheet if one exists")

    def base_and_weighted(res):
        return None if res is None else {"base": res["base"]["value_per_share"], "weighted": weighted(res)}

    out = {
        "ticker": model["ticker"],
        "currency": model.get("currency"),
        "basis": model["basis"],
        "model_date": model["model_date"],
        "valuation_date": model["valuation_date"],
        "discount_rate": model["discount_rate"],
        "equity_rate": model.get("equity_rate", model["discount_rate"]),
        "scenarios": results,
        "terminal_growth": {n: model["scenarios"][n].get("terminal", {}).get("growth") for n in results},
        "risk_free_observed": model.get("risk_free_observed"),
        "weighted_value": weighted(results),
        "sensitivity": {
            "rate_plus_1pt": base_and_weighted(safe_run(model, rate_shift=0.01)),
            "rate_minus_1pt": base_and_weighted(safe_run(model, rate_shift=-0.01)),
            "terminal_growth_plus_1pt": base_and_weighted(safe_run(model, growth_shift=0.01)),
            "terminal_growth_minus_1pt": base_and_weighted(safe_run(model, growth_shift=-0.01)),
            "full_fade": base_and_weighted(safe_run(model, fade=True)),
        },
        "warnings": warnings,
        "model_sha256": hashlib.sha256(raw).hexdigest(),
    }
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=2) + "\n")

    print(f"{model['ticker']}  value per share on {model['valuation_date']}  (discount rate {model['discount_rate']:.2%})")
    for name in ("stress", "bear", "base", "bull"):
        if name in results:
            r = results[name]
            p = "   -  " if r["probability"] is None else f"{r['probability']:>5.0%} "
            ts = "  n/a" if r["terminal_share"] is None else f"{r['terminal_share']:>5.0%}"
            print(f"  {name:<7}{p} {r['value_per_share']:>12,.2f}   terminal share {ts}")
    print(f"  weighted       {out['weighted_value']:>12,.2f}")
    for label, v in out["sensitivity"].items():
        if v:
            print(f"  {label:<26} base {v['base']:>10,.2f}   weighted {v['weighted']:>10,.2f}")
    for w in warnings:
        print(f"  WARNING: {w}")


if __name__ == "__main__":
    try:
        main()
    except ModelError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except (KeyError, TypeError, ValueError) as e:
        print(f"ERROR: the model file is malformed ({type(e).__name__}: {e}). "
              "Compare it with references/model.template.json.", file=sys.stderr)
        sys.exit(1)
