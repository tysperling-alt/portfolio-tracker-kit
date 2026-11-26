#!/usr/bin/env python3
"""Check the tracker's data files for errors. Run before every commit.

Checks:
- holdings.json: each account's positions + cash add up to its total (within $1),
  market_value = shares x price (within 1%), no negative or zero shares, required fields present.
- trades.jsonl: every line parses, required fields present, actions are known.
- valuations/*.json: every file parses as JSON.
Exit code 1 on any error.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
errors = []
# Account tax types. "roth" = tax-free growth (Roth IRA, Roth 401k), "traditional" = tax-deferred
# (traditional IRA, 401k, 403b), "taxable" = an ordinary brokerage account, "hsa" = health savings account.
TAX_TYPES = ("roth", "traditional", "taxable", "hsa", "other")


def check_holdings():
    path = ROOT / "data" / "holdings.json"
    if not path.exists():
        errors.append("data/holdings.json is missing. Run the first-run setup in CLAUDE.md to create it.")
        return
    d = json.loads(path.read_text())
    for key in ("as_of", "accounts"):
        if key not in d:
            errors.append(f"holdings.json: missing '{key}'")
    for a in d.get("accounts", []):
        name = a.get("name", "?")
        for key in ("id", "tax_type", "total_value", "cash", "positions"):
            if key not in a:
                errors.append(f"{name}: missing '{key}'")
        if a.get("tax_type") not in TAX_TYPES:
            errors.append(f"{name}: tax_type must be one of {', '.join(TAX_TYPES)}")
        if "purpose" in a and not isinstance(a["purpose"], str):
            errors.append(f"{name}: purpose must be plain text")
        total = a.get("cash", 0)
        seen = set()
        for p in a.get("positions", []):
            t = p.get("ticker", "?")
            if t in seen:
                errors.append(f"{name}: {t} listed twice; merge into one position")
            seen.add(t)
            for key in ("ticker", "type", "shares", "price", "market_value", "cost_basis"):
                if key not in p:
                    errors.append(f"{name} {t}: missing '{key}'")
            if p.get("shares", 0) <= 0:
                errors.append(f"{name} {t}: shares must be positive (remove the position if sold out)")
            se = p.get("stock_exposure")
            if se is not None and not (isinstance(se, (int, float)) and 0 <= se <= 1):
                errors.append(f"{name} {t}: stock_exposure must be a number from 0 to 1")
            mv, calc = p.get("market_value", 0), p.get("shares", 0) * p.get("price", 0)
            if mv and abs(calc - mv) / mv > 0.01:
                errors.append(f"{name} {t}: market_value {mv} != shares x price {calc:.2f}")
            total += mv
        if abs(total - a.get("total_value", 0)) > 1:
            errors.append(f"{name}: positions + cash = {total:.2f}, but total_value = {a.get('total_value')}")


def check_trades():
    path = ROOT / "data" / "trades.jsonl"
    if not path.exists():
        return
    for i, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            t = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"trades.jsonl line {i}: bad JSON ({e})")
            continue
        for key in ("date", "account", "ticker", "action", "shares", "price"):
            if key not in t:
                errors.append(f"trades.jsonl line {i}: missing '{key}'")
        if t.get("action") not in ("buy", "sell", "dividend-reinvest", "transfer-in", "transfer-out", "exercise"):
            errors.append(f"trades.jsonl line {i}: unknown action '{t.get('action')}'")


def check_valuations():
    for f in sorted((ROOT / "data" / "valuations").glob("*.json")):
        try:
            json.loads(f.read_text())
        except json.JSONDecodeError as e:
            errors.append(f"{f.name}: bad JSON ({e})")


check_holdings()
check_trades()
if (ROOT / "data" / "valuations").exists():
    check_valuations()

if errors:
    print(f"FAIL: {len(errors)} error(s)")
    for e in errors:
        print(" -", e)
    sys.exit(1)
print("OK: holdings, trades, and valuations pass")
