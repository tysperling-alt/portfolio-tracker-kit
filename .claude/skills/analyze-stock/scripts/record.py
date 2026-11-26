#!/usr/bin/env python3
"""Lock, record, and read valuations for the analyze-stock skill.

This script is the only writer of data/valuations/<TICKER>.json. It turns the
skill's rules into checks that fail, so a broken rule stops the run.

Commands:
  record.py lock      --draft D [--model-result R] --out L      build and stamp the price-blind lock
  record.py lock      ... --revises OLD --reason-type error --reason "..." [--after-price]
  record.py verify    --lock L                                   confirm a lock was not edited
  record.py append    --lock L --audit A [--supersede]           add price audit and decision; write the record
  record.py blind     TICKER [--last N] [--with-report]          prior records with every price-dependent field removed
  record.py scorecard [TICKER]                                   forecast accuracy across records
  record.py validate  [TICKER]                                   check files against the schema and the hashes
  record.py calibrate [--current]                                cross-section check: price / value, tails, verdict shares
  record.py monthly-check                                        script-only monthly check: which holdings need a refresh
  record.py appendix  --lock L                                   render the report appendix (scenarios, forecasts, method notes)
  record.py headline  TICKER                                     render the first lines of the short report (after append)
  record.py tiers                                                risk tier of every valued record, so like businesses match
  record.py filing-check --draft D --model M | --lock L           compare share count and latest filing with SEC data

Standard library only (Python 3.9+). Formats: references/output-schema.md.
"""
import argparse
import copy
import hashlib
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bands  # noqa: E402

SCHEMA_PATH = bands.SKILL_DIR / "references" / "valuation-record.schema.json"
SCHEMA_VERSION = "2.0"
VALUED = ("resolved", "conditional", "range_only")
PRICE_EXPOSURE_KINDS = ("quote", "market_value", "multiple", "price_target", "valuation_opinion", "price_news", "other")
LOCK_WARNINGS = []
POST_PRICE_KEYS = ("audit", "rating", "decision", "next_review")
BUY_LABELS = ("Strong Buy", "Buy/Accumulate", "Starter Position")
NO_BUY_LABELS = ("Hold/Watchlist", "Avoid/Do Not Chase")
BLIND_START, BLIND_END = "<!-- price-blind:start -->", "<!-- price-blind:end -->"
die = bands.die


def load(path):
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        die(f"file not found: {path}")
    except json.JSONDecodeError as e:
        die(f"{path} is not valid JSON: {e}")


def need(obj, key, where):
    if not isinstance(obj, dict) or obj.get(key) is None:
        die(f"{where} is missing '{key}'")
    return obj[key]


# ---------- a small JSON Schema checker (the subset the schema file uses) ----------

def _is_type(v, t):
    if t == "null":
        return v is None
    if t == "boolean":
        return isinstance(v, bool)
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, {"string": str, "array": list, "object": dict}[t])


def check_schema(v, schema, root, path, errors, skip_required=()):
    if "$ref" in schema:
        target = root
        for part in schema["$ref"].lstrip("#/").split("/"):
            target = target[part]
        schema = {**target, **{k: x for k, x in schema.items() if k != "$ref"}}
    t = schema.get("type")
    if t is not None:
        types = [t] if isinstance(t, str) else t
        if not any(_is_type(v, x) for x in types):
            errors.append(f"{path or 'record'}: expected {' or '.join(types)}, got {type(v).__name__}")
            return
    if "const" in schema and v != schema["const"]:
        errors.append(f"{path}: must be {schema['const']!r}")
    if "enum" in schema and v not in schema["enum"]:
        errors.append(f"{path}: {v!r} is not one of {schema['enum']}")
    if v is None:
        return
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if "minimum" in schema and v < schema["minimum"]:
            errors.append(f"{path}: {v} is below {schema['minimum']}")
        if "maximum" in schema and v > schema["maximum"]:
            errors.append(f"{path}: {v} is above {schema['maximum']}")
        if "exclusiveMinimum" in schema and v <= schema["exclusiveMinimum"]:
            errors.append(f"{path}: {v} must be above {schema['exclusiveMinimum']}")
    if isinstance(v, str):
        if "pattern" in schema and not re.search(schema["pattern"], v):
            errors.append(f"{path}: {v!r} does not match the expected format")
        if len(v) < schema.get("minLength", 0):
            errors.append(f"{path}: text is too short")
    if isinstance(v, list):
        if len(v) > schema.get("maxItems", len(v)):
            errors.append(f"{path}: more than {schema['maxItems']} items")
        if len(v) < schema.get("minItems", 0):
            errors.append(f"{path}: fewer than {schema['minItems']} items")
        if "items" in schema:
            for i, item in enumerate(v):
                check_schema(item, schema["items"], root, f"{path}[{i}]", errors)
    if isinstance(v, dict):
        for key in schema.get("required", []):
            if key not in v and key not in skip_required:
                errors.append(f"{path + '.' if path else ''}{key}: required field is missing")
        props = schema.get("properties", {})
        for key, val in v.items():
            if key in props:
                check_schema(val, props[key], root, f"{path + '.' if path else ''}{key}", errors)
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path + '.' if path else ''}{key}: unknown field")


def schema_errors(record, partial=False):
    root = load(SCHEMA_PATH)
    errors = []
    check_schema(record, root["$defs"]["record"], root, "", errors, POST_PRICE_KEYS if partial else ())
    return errors


def fail_on(errors, what):
    if errors:
        print(f"ERROR: {what} failed {len(errors)} check(s):", file=sys.stderr)
        for e in errors:
            print(f" - {e}", file=sys.stderr)
        sys.exit(1)


# ---------- hashing ----------

def lock_hash(record):
    """Hash of every price-blind field. Fields added after the price audit are left out."""
    r = copy.deepcopy(record)
    for k in POST_PRICE_KEYS:
        r.pop(k, None)
    r["lock"].pop("lock_sha256", None)
    r["price_isolation"]["orchestrator_knew_price_before_lock"] = None
    r["price_isolation"]["revised_after_price"] = None
    r.get("accountability", {}).pop("decision_grade", None)
    return hashlib.sha256(json.dumps(r, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def verify_hash(record, what):
    if lock_hash(record) != record["lock"].get("lock_sha256"):
        die(f"{what}: the lock hash does not match. A price-blind field was edited after locking. "
            "Do not edit lock files. To change a value, make a revised lock with 'record.py lock --revises'.")


def parse_dt(text, where):
    try:
        d = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        die(f"{where}: {text!r} is not an ISO date-time")
    if d.tzinfo is None:
        die(f"{where}: add a time zone offset, for example 2026-01-05T21:02:00+00:00")
    return d


# ---------- lock ----------

def build_partial(draft, result, settings, root):
    ticker = need(draft, "ticker", "draft").upper()
    lock_in = need(draft, "lock", "draft")
    status = need(lock_in, "valuation_status", "draft.lock")
    valued = status in VALUED
    is_fund = draft.get("asset_type") == "fund"
    if is_fund != (status == "not_applicable"):
        die("valuation_status 'not_applicable' is for funds, and funds must use it")
    if status == "conditional" and not lock_in.get("conditions"):
        die("a conditional valuation must state its condition in lock.conditions")
    if not str(draft.get("report_path", "")).startswith("analyses/"):
        die("report_path must be relative to the project folder and start with analyses/")

    records = bands.load_records(root, ticker)
    earlier = [r for r in records if r["date"] < draft["date"]]
    prior = earlier[-1] if earlier else None
    if draft["mode"] == "refresh" and not prior:
        die("refresh mode needs a prior record. Run full mode.")
    if draft["mode"] == "refresh" and not is_fund:
        fulls = [r["date"] for r in earlier if r.get("mode") == "full"]
        limit = settings["refresh"]["full_review_after_months"]
        age_days = (date.fromisoformat(draft["date"]) - date.fromisoformat(fulls[-1])).days if fulls else None
        if age_days is None or age_days > limit * 30.44:
            die(f"the last full analysis is more than {limit} months old (or there is none). Escalate to full mode.")

    dv, rates_in = draft.get("values") or {}, draft.get("rates") or {}
    thesis = draft.get("thesis") or {"decisive_questions": [], "key_assumptions": [], "key_risks": [],
                                     "decision_sensitive_assumptions": []}
    grades = draft.get("grades") or {}
    grades = {k: grades.get(k) for k in ("quality", "management", "cash_reliability", "distributability")}
    values = {"bear": None, "base": None, "bull": None, "weighted": None, "stress": None, "probabilities": None,
              "summaries": dv.get("summaries"), "terminal_share_base": None, "diluted_shares": None}
    rates = {"risk_free_observed": rates_in.get("risk_free_observed"), "risk_free_source": rates_in.get("risk_free_source"),
             "risk_free_used": None, "risk_tier": rates_in.get("risk_tier"),
             "risk_tier_reason": rates_in.get("risk_tier_reason"), "discount_rate": None, "required_return": None}
    detail_in = draft.get("confidence_detail") or {}
    detail = {"points": None, "total_points": None, "computed_level": None,
              "override": detail_in.get("override"), "evidence_gaps": detail_in.get("evidence_gaps", [])}
    level, basis, model_sha = None, lock_in.get("valuation_basis"), None

    if valued:
        if result:
            if result["ticker"].upper() != ticker:
                die("the model result is for a different ticker")
            if result["valuation_date"] != draft["date"]:
                die("the model's valuation_date must equal the analysis date")
            sc = result["scenarios"]
            for s in ("bear", "base", "bull"):
                values[s] = sc[s]["value_per_share"]
            values["probabilities"] = {s: sc[s]["probability"] for s in ("bear", "base", "bull")}
            values["stress"] = sc["stress"]["value_per_share"] if "stress" in sc else dv.get("stress")
            values["weighted"] = result["weighted_value"]
            values["terminal_share_base"] = sc["base"]["terminal_share"]
            values["diluted_shares"] = sc["base"]["diluted_shares"]
            model_rate, basis, model_sha = result["equity_rate"], result["basis"], result["model_sha256"]
            if basis == "equity" and abs(result["discount_rate"] - model_rate) > 0.00011:
                die("on equity basis the model's discount_rate must equal its equity_rate (the cost of equity)")
            if values["terminal_share_base"] is None:
                values["terminal_share_base"] = 1.0   # base operating value is zero or negative: least certain case
        else:
            for s in ("bear", "base", "bull", "stress"):
                values[s] = need(dv, s, "draft.values (no model result was given)")
            values["probabilities"] = need(dv, "probabilities", "draft.values")
            values["weighted"] = round(sum(values["probabilities"][s] * values[s] for s in ("bear", "base", "bull")), 2)
            values["terminal_share_base"] = dv.get("terminal_share_base")
            values["diluted_shares"] = dv.get("diluted_shares")
            model_rate = need(rates_in, "discount_rate", "draft.rates (no model result was given)")
            if not draft.get("model_path"):
                die("without a dcf.py model, model_path must point to the saved calculation script")
        if values["stress"] is None:
            die("a stress case is required: add a 'stress' scenario to the model")
        if abs(sum(values["probabilities"].values()) - 1) > 1e-6:
            die("bear, base, and bull probabilities must sum to 1")
        if any(not 0.10 <= p <= 0.70 for p in values["probabilities"].values()):
            die("keep each scenario probability between 10% and 70%")
        # v9, improvement 6d: a move away from the default probabilities needs a written base rate
        defaults = settings["default_probabilities"]
        moved_probs = any(abs(values["probabilities"][s] - defaults[s]) > 1e-6 for s in ("bear", "base", "bull"))
        values["probability_basis"] = dv.get("probability_basis")
        if moved_probs:
            pb = values["probability_basis"] or {}
            if not (pb.get("base_rate") and pb.get("source")):
                die("the probabilities differ from the defaults "
                    f"({defaults['bear']:.0%}/{defaults['base']:.0%}/{defaults['bull']:.0%}). Add values.probability_basis "
                    "with base_rate (the written base rate that justifies the move) and source (a row in references/base-rates.md "
                    "or a dated published source). Apply a base rate once: in the forecast or in the probabilities, not both.")
            if pb.get("not_also_in_forecast") is not True:
                die("values.probability_basis.not_also_in_forecast must be true: confirm the same base rate was not also "
                    "applied by fading the forecast. Charging one concern twice is the error this rule stops.")
        if not values["bear"] <= values["base"] <= values["bull"]:
            die("values must be ordered bear <= base <= bull")
        # v9, improvement 7: a value that rests mostly on the bull case is a range, not a point
        values["range_test"] = bands.range_only_test(values, settings)
        rt, rule = values["range_test"], settings["range_only"]
        if rt["trips"] and status != bands.RANGE_ONLY:
            die(f"the range-only test trips: the bull case supplies {rt['bull_share']:.0%} of fair value "
                f"(limit {rule['max_bull_share_of_value']:.0%}); (bull - bear) / fair value is {rt['spread']:.2f} "
                f"(limit {rule['max_spread_to_value']:.1f}). Either one trips it. "
                "This value cannot be stated with confidence. Set lock.valuation_status to 'range_only'.")
        if result:
            obs = rates_in.get("risk_free_observed")
            for s_name, g in (result.get("terminal_growth") or {}).items():
                if g is not None and obs is not None and g > obs:
                    LOCK_WARNINGS.append(f"{s_name}: terminal growth {g:.1%} is above the observed risk-free rate {obs:.2%} "
                                         "(not the floored rate). Justify it in the report or lower it.")
            LOCK_WARNINGS.extend(w for w in result.get("warnings", []) if "terminal growth" not in w)
        for k in ("quality", "management", "cash_reliability"):
            if grades[k] is None:
                die(f"grades.{k} is required for a valued stock")
        if len(thesis.get("decisive_questions", [])) != 3:
            die("set exactly three decisive questions")
        if len(draft.get("forecasts", [])) < 4 or not draft.get("milestones"):
            die("a valued stock needs at least four forecasts and at least one milestone so later runs can grade it")
        effects = {c.get("effect") for c in draft.get("change_conditions", [])}
        if not {"thesis_broken", "raise_value"} <= effects:
            die("change_conditions must include at least one 'thesis_broken' and at least one 'raise_value'. "
                "A list with only downside conditions is a bias.")

        prior_rf = bands.prior_risk_free(records, draft["date"]) if draft["mode"] == "refresh" else None
        rf = bands.risk_free_used(need(rates_in, "risk_free_observed", "draft.rates"), settings, prior_rf)
        disc = bands.discount_rate(rf, need(rates_in, "risk_tier", "draft.rates"), settings)
        if abs(model_rate - disc) > 0.00011:
            die(f"the model used a cost of equity of {model_rate}, but the settings give {disc} for tier "
                f"'{rates_in['risk_tier']}'. Run 'bands.py rates' and use its discount_rate "
                "(as equity_rate when the model is on firm basis).")
        rates.update(risk_free_used=rf, discount_rate=disc, required_return=bands.required_return(disc, settings))

        weak = sum(1 for q in thesis["decisive_questions"] if q.get("evidence_strength") == "weak")
        points = {"scenario_spread": bands.spread_points(values["bear"], values["bull"], values["weighted"]),
                  "terminal_share": bands.terminal_points(values["terminal_share_base"]),
                  "cash_reliability": bands.cash_points(grades["cash_reliability"]),
                  "evidence": bands.evidence_points(weak)}
        total = sum(points.values())
        level = bands.level_from_points(total)
        detail.update(points=points, total_points=total, computed_level=level)
        if detail["override"]:
            new = detail["override"].get("level")
            if new not in bands.LEVELS or abs(bands.LEVELS.index(new) - bands.LEVELS.index(level)) != 1:
                die("a confidence override may move the level by exactly one step")
            level = new
        if status == bands.RANGE_ONLY:
            band = bands.compute_bands(None, None, None, None, None, settings)
            band["fair_value"] = round(values["weighted"], 2)
        else:
            band = bands.compute_bands(values["weighted"], disc, rates["required_return"], rf, level, settings)
        # The fixed Buy / Hold / Sell rule applies to every valued status, range_only included.
        ab = bands.action_bands(values["weighted"], settings)
        band.update(buy_below_price=ab["buy_below_price"], sell_above_price=ab["sell_above_price"])
        band.update(range_low=values["bear"], range_high=values["bull"])
        band["valid_until"] = (date.fromisoformat(draft["date"]) + timedelta(days=settings["bands_valid_days"])).isoformat()
        prior_tier = next(((r.get("rates") or {}).get("risk_tier") for r in reversed(earlier)
                           if (r.get("rates") or {}).get("risk_tier")), None)
        if prior_tier and prior_tier != rates_in["risk_tier"]:
            LOCK_WARNINGS.append(f"risk tier changed from {prior_tier} to {rates_in['risk_tier']}. Say why in risk_tier_reason, "
                                 "and check 'record.py tiers' so like businesses get the same tier.")
    else:
        band = bands.compute_bands(None, None, None, None, None, settings)
        band.update(buy_below_price=None, sell_above_price=None, range_low=None, range_high=None)
        band["horizon_years"] = None
        band["valid_until"] = None
        if detail["override"]:
            die("no confidence override without a value")

    # price isolation: a blocked source in the list means price information was on screen
    iso = dict(need(draft, "price_isolation", "draft"))
    iso.setdefault("exposures", [])
    sources = draft.get("sources", [])
    for s in sources:
        url = (s.get("url") or "").lower()
        hit = next((d for d in settings["blocked_source_domains"] if d in url), None)
        if hit and not is_fund:
            iso["exposures"].append({"what": f"source list cites {hit}, a site that shows prices or valuation opinions",
                                     "source": s.get("url"), "current": True, "kind": "quote"})
            iso["status"] = "exposed"
    # v9, improvement 10: a price printed in the company's own filing is incidental. Only a quote,
    # a market value, a multiple, a target, or a valuation opinion makes a run 'exposed'.
    def real_leak(e):
        return e.get("current") and e.get("kind", "other") in PRICE_EXPOSURE_KINDS
    for e in iso["exposures"]:
        if "kind" not in e:
            die("each price_isolation exposure needs a 'kind': company_filing for a price printed in the company's own "
                f"filing, or one of {list(PRICE_EXPOSURE_KINDS)}. See references/price-isolation.md.")
    if iso["status"] in ("clean", "exposed") and iso["exposures"] and not any(real_leak(e) for e in iso["exposures"]) \
            and not any(d in (s.get("url") or "").lower() for s in sources for d in settings["blocked_source_domains"]):
        iso["status"] = "incidental"
    if iso["status"] in ("clean", "incidental") and any(real_leak(e) for e in iso["exposures"]):
        iso["status"] = "exposed"
    iso["orchestrator_knew_price_before_lock"] = None
    iso["revised_after_price"] = None

    acc = build_accountability(draft, earlier, prior, values["weighted"], settings)

    return {
        "schema_version": SCHEMA_VERSION, "ticker": ticker, "company_name": draft.get("company_name"),
        "asset_type": draft.get("asset_type"), "date": draft["date"], "mode": draft["mode"],
        "currency": draft.get("currency"), "report_path": draft["report_path"], "model_path": draft.get("model_path"),
        "information_cutoff": draft.get("information_cutoff"), "latest_filing_used": draft.get("latest_filing_used"),
        "price_isolation": iso,
        "settings_used": {k: settings[k] for k in ("hurdle_rate", "horizon_years", "equity_risk_premium", "risk_free_floor",
                                                   "trim_premium_share", "sell_premium_share", "settings_source",
                                                   "settings_version", "action_bands", "range_only")},
        "lock": {"locked_at": None, "lock_sha256": None, "valuation_status": status,
                 "conditions": lock_in.get("conditions"), "valuation_basis": basis if valued else None,
                 "primary_method": lock_in.get("primary_method"), "secondary_method": lock_in.get("secondary_method"),
                 "secondary_value": lock_in.get("secondary_value"), "method_notes": lock_in.get("method_notes"),
                 "model_sha256": model_sha, "revisions": []},
        "values": values, "rates": rates, "grades": grades,
        "confidence": level, "confidence_detail": detail, "thesis": thesis,
        "forecasts": draft.get("forecasts", []), "milestones": draft.get("milestones", []),
        "change_conditions": draft.get("change_conditions", []), "sources": sources,
        "bands": band, "fund": draft.get("fund"), "accountability": acc,
    }


def build_accountability(draft, records, prior, new_weighted, settings):
    acc_in = draft.get("accountability") or {}
    expected = prior["date"] if prior else None
    if acc_in.get("prior_record_date") != expected:
        die(f"accountability.prior_record_date must be {expected!r}: "
            + ("grade the latest prior record; this step is not optional." if expected
               else "there is no prior record, so set it to null."))
    by_date = {r["date"]: r for r in records}
    graded = []
    for g in acc_in.get("forecast_grades", []):
        src = by_date.get(g.get("from_record_date"))
        fc = next((f for f in (src or {}).get("forecasts", []) if f["id"] == g.get("forecast_id")), None)
        if not fc:
            die(f"forecast grade {g.get('forecast_id')} from {g.get('from_record_date')}: no such forecast on record. "
                "Grade only forecasts that exist in a prior record.")
        actual = need(g, "actual", "forecast grade")
        graded.append({"forecast_id": fc["id"], "from_record_date": src["date"], "actual": actual,
                       "actual_source": g.get("actual_source"), "metric": fc["metric"], "period_end": fc["period_end"],
                       "unit": fc["unit"], "forecast_low": fc["low"], "forecast_base": fc["base"], "forecast_high": fc["high"],
                       "error": round((actual - fc["base"]) / abs(fc["base"]), 4) if fc["base"] else None,
                       "within_range": fc["low"] <= actual <= fc["high"]})
    bridge = acc_in.get("value_bridge")
    prior_weighted = (prior.get("values") or {}).get("weighted") if prior else None
    if prior_weighted is not None and new_weighted is not None:
        if not bridge:
            die("a value bridge is required: explain the change from the prior weighted value")
        parts = sum(bridge[k] for k in ("time_roll", "rates", "shares_and_financing", "operations", "method"))
        tol = max(0.05, 0.002 * abs(new_weighted))
        if abs(bridge["prior_value"] - prior_weighted) > 0.011:
            die(f"value_bridge.prior_value must equal the prior weighted value {prior_weighted}")
        if abs(bridge["new_value"] - new_weighted) > 0.011:
            die(f"value_bridge.new_value must equal the new weighted value {new_weighted}")
        if abs(bridge["prior_value"] + parts - bridge["new_value"]) > tol:
            die(f"the value bridge does not sum: {bridge['prior_value']} + {round(parts, 2)} != {bridge['new_value']}")
        moved = abs(parts - bridge["time_roll"]) / prior_weighted if prior_weighted > 0 else 0
        if draft["mode"] == "refresh" and moved > settings["refresh"]["escalate_value_change"]:
            die(f"the value moved {moved:.0%} beyond the passage of time, above the "
                f"{settings['refresh']['escalate_value_change']:.0%} limit for a refresh. Escalate to full mode.")
    holds = acc_in.get("lock_holds")
    if draft["mode"] == "refresh" and holds is not True:
        die("refresh mode is only for a lock that still holds (lock_holds: true). "
            "If the prior analysis no longer stands, hand back 'escalate to full' instead of locking a refresh.")
    return {"prior_record_date": expected, "forecast_grades": graded,
            "milestone_updates": acc_in.get("milestone_updates", []),
            "change_conditions_tripped": acc_in.get("change_conditions_tripped", []),
            "value_bridge": bridge, "lock_holds": holds, "lessons": acc_in.get("lessons")}


def cmd_lock(a):
    root, settings = bands.find_root(a.root), bands.load_settings(a.root)
    out = Path(a.out)
    if out.exists():
        die(f"{out} exists. Lock files are never overwritten. For a revision, write a new file with --revises.")
    draft = load(a.draft)
    for key in ("ticker", "company_name", "asset_type", "date", "mode", "currency", "report_path", "information_cutoff"):
        need(draft, key, "draft")
    rec = build_partial(draft, load(a.model_result) if a.model_result else None, settings, root)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if a.revises:
        old = load(a.revises)
        verify_hash(old, a.revises)
        if old["ticker"] != rec["ticker"] or old["date"] != rec["date"]:
            die("a revision must be for the same ticker and date as the lock it revises")
        if not a.reason_type or not a.reason:
            die("a revision needs --reason-type (evidence, error, or method) and --reason")
        rec["lock"]["first_locked_at"] = old["lock"].get("first_locked_at") or old["lock"]["locked_at"]
        rec["lock"]["revisions"] = old["lock"]["revisions"] + [{
            "revised_at": now, "reason_type": a.reason_type, "reason": a.reason,
            "prior_lock_sha256": old["lock"]["lock_sha256"], "prior_weighted_value": old["values"]["weighted"],
            "after_price": bool(a.after_price)}]
    elif a.reason or a.reason_type or a.after_price:
        die("--reason, --reason-type, and --after-price only apply with --revises")
    rec["lock"]["locked_at"] = now
    rec["lock"].setdefault("first_locked_at", now)
    rec["lock"]["lock_sha256"] = "0" * 64
    fail_on(schema_errors(rec, partial=True), "the lock")
    rec["lock"]["lock_sha256"] = lock_hash(rec)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=2) + "\n")
    print_lock(rec, out)
    for w in LOCK_WARNINGS:
        print(f"  WARNING: {w}")


def print_lock(rec, path):
    v, b = rec["values"], rec["bands"]
    print(f"LOCKED {rec['ticker']} {rec['date']} ({rec['mode']})  ->  {path}")
    print(f"  status {rec['lock']['valuation_status']}   price isolation {rec['price_isolation']['status']}   confidence {rec['confidence']}")
    if v["weighted"] is not None:
        print(f"  bear {v['bear']}  base {v['base']}  bull {v['bull']}  weighted {v['weighted']}  stress {v['stress']}")
        print(f"  discount rate {rec['rates']['discount_rate']:.2%}   required return {rec['rates']['required_return']:.2%}")
        if rec["lock"]["valuation_status"] == bands.RANGE_ONLY:
            print(f"  range only (status kept for history): range {b.get('range_low')} to {b.get('range_high')}")
        ab = bands.record_verdict_bands(rec, bands.load_settings())[0]
        if ab.get("buy_below_price") is not None:
            print(f"  call prices: buy below {ab['buy_below_price']}   sell above {ab['sell_above_price']}")
        print(f"  letter action prices: buy below {b['buy_below']}   trim above {b['trim_above']}   sell above {b['sell_above']}")
    if rec["lock"]["revisions"]:
        print(f"  revisions: {len(rec['lock']['revisions'])}")
    print(f"  sha256 {rec['lock']['lock_sha256']}")


def cmd_verify(a):
    rec = load(a.lock)
    verify_hash(rec, a.lock)
    fail_on(schema_errors(rec, partial=True), "the lock")
    print("OK: the lock is intact")
    print_lock(rec, a.lock)


# ---------- append ----------

def expectations_test(rec, audit, gap_required, settings):
    """Improvement 1 (v9). The audit names what the price assumes against the base case.
    Each large gap is sorted into input error, method convention, or business disagreement.
    A business disagreement with no named evidence lowers confidence one level; the value stands.
    Returns the method-convention entries for docs/method-log.md."""
    exp = audit.get("expectations")
    if not exp:
        die("v9 records need audit.expectations: two or three driver rows (what the price implies, what consensus "
            "expects for the next two years, what the base case assumes, the evidence for each difference) and gap_sources. "
            "See references/audit-and-decision.md Part 1, step 4.")
    drivers = exp.get("drivers") or []
    if not 2 <= len(drivers) <= 3:
        die("audit.expectations.drivers needs two or three rows: the main drivers of value")
    gaps = exp.get("gap_sources") or []
    if gap_required and not gaps:
        die("the gap between price and value is large. Sort it in audit.expectations.gap_sources: input_error, "
            "method_convention, or business_disagreement, with dollars per share for each.")
    if any(g.get("type") == "input_error" for g in gaps):
        die("an input error is not a gap to record: fix it with a revised lock ('record.py lock --revises ... "
            "--reason-type error --after-price'), then append the revised lock.")
    unsupported = [g for g in gaps if g.get("type") == "business_disagreement" and not (g.get("evidence") or "").strip()]
    level = rec["confidence"]
    if unsupported and level:
        level = bands.lower_level(level)
    audit["confidence_after_audit"] = level
    # Confidence is recorded but does not widen the bands. Range-only values get a call too.
    ab = bands.action_bands(rec["values"]["weighted"], settings)
    audit["verdict_bands_after_audit"] = {"buy_below_price": ab["buy_below_price"], "sell_above_price": ab["sell_above_price"]}
    audit["verdict"] = bands.verdict(audit["price"], ab)
    return [g for g in gaps if g.get("type") == "method_convention"]


def log_method_conventions(root, rec, entries):
    """A method convention is fixed for all stocks, not for one. Log it for the batch lead."""
    path = Path(root) / "docs" / "method-log.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("# Method log\n\nWritten by `record.py append`. Each entry is a method convention that an "
                        "expectations test found behind a gap between price and value. A convention is changed for all "
                        "stocks at once, never for one stock. Mark each entry decided when the method is changed or kept.\n")
    existing = path.read_text()
    with path.open("a") as f:
        for e in entries:
            line = (f"- {rec['date']} {rec['ticker']}: {e['explanation']} "
                    f"(about {e['dollars_per_share']:+,.2f} a share). Status: open.")
            if line not in existing:   # a --supersede rerun does not log the same entry twice
                f.write(f"\n{line}\n")

def cmd_append(a):
    root, settings = bands.find_root(a.root), bands.load_settings(a.root)
    rec = load(a.lock)
    verify_hash(rec, a.lock)
    add = load(a.audit)
    audit = dict(need(add, "audit", "audit file"))
    price = need(audit, "price", "audit")
    nums = bands.audit_numbers(rec, price, settings, bands.load_model_for(rec, root))
    gap = dict(audit.get("gap_audit") or {})
    gap["required"] = nums.pop("gap_audit_required")
    if gap["required"] and not (gap.get("opposing_case") and gap.get("resolving_evidence")):
        die("the gap between price and value is large (or the price is outside the bear-to-bull range). "
            "Run the model audit: fill audit.gap_audit.opposing_case and resolving_evidence.")
    audit.update(nums)
    audit["gap_audit"] = gap
    method_entries = []
    if rec.get("schema_version") == SCHEMA_VERSION and rec["lock"]["valuation_status"] in VALUED:
        method_entries = expectations_test(rec, audit, gap["required"], settings)

    v2 = rec.get("schema_version") == SCHEMA_VERSION
    rating = need(add, "rating", "audit file")
    # v9: allocation, size, and per-account actions move to the monthly letter. A 2.0 record may omit them.
    decision = add.get("decision") if v2 else need(add, "decision", "audit file")
    label = rating.get("label")
    if label in NO_BUY_LABELS and not rating.get("no_buy_reason"):
        die("Hold/Watchlist and Avoid/Do Not Chase need rating.no_buy_reason: "
            "'below required return', 'expected loss', or 'insufficient evidence'")
    if rec["lock"]["valuation_status"] == "unresolved" and label in ("Strong Buy", "Buy/Accumulate"):
        die("an unresolved valuation cannot carry a Strong Buy or Buy/Accumulate rating")
    if rec["lock"]["valuation_status"] == bands.RANGE_ONLY and label in ("Strong Buy", "Buy/Accumulate"):
        die("a range-only valuation cannot carry a Strong Buy or Buy/Accumulate rating")
    if decision:
        size = need(decision, "suggested_size_range", "decision")
        if size["low"] > size["high"]:
            die("suggested_size_range.low is above high")
        if decision.get("currently_owned") and not decision.get("account_actions"):
            die("the stock is owned: give one account_actions row per account that holds it")

    knew = add.get("orchestrator_knew_price_before_lock")
    if not isinstance(knew, bool):
        die("audit file needs orchestrator_knew_price_before_lock: true or false")
    first_lock = rec["lock"].get("first_locked_at") or rec["lock"]["locked_at"]
    if parse_dt(need(audit, "price_observed_at", "audit"), "audit.price_observed_at") < parse_dt(first_lock, "lock.first_locked_at") and not knew:
        die("the audit price was observed before the lock existed. "
            "Set orchestrator_knew_price_before_lock to true so the record is honest about it.")

    earlier = [r for r in bands.load_records(root, rec["ticker"]) if r["date"] < rec["date"]]
    grade = add.get("decision_grade")
    if earlier and not grade:
        die(f"a prior record exists ({earlier[-1]['date']}). Grade its decision: add decision_grade to the audit file.")
    if grade and (not earlier or grade.get("graded_record_date") != earlier[-1]["date"]):
        die("decision_grade.graded_record_date must be the date of the latest prior record")

    rec["price_isolation"]["orchestrator_knew_price_before_lock"] = knew
    rec["price_isolation"]["revised_after_price"] = any(x["after_price"] for x in rec["lock"]["revisions"])
    rec["accountability"]["decision_grade"] = grade
    rec.update(audit=audit, rating=rating, next_review=need(add, "next_review", "audit file"))
    if decision:
        rec["decision"] = decision
    fail_on(schema_errors(rec), "the record")
    verify_hash(rec, "assembled record")

    path = bands.valuations_path(root, rec["ticker"])
    data = load(path) if path.exists() else {"schema_version": SCHEMA_VERSION, "ticker": rec["ticker"], "records": []}
    data["schema_version"] = SCHEMA_VERSION
    if data.get("ticker") != rec["ticker"]:
        die(f"{path} belongs to {data.get('ticker')}")
    newer = [r for r in data["records"] if r["date"] > rec["date"]]
    if newer:
        die(f"a newer record ({newer[-1]['date']}) already exists; records are appended in date order")
    same = [r for r in data["records"] if r["date"] == rec["date"]]
    if same:
        if not a.supersede:
            die(f"a record for {rec['date']} already exists. Pass --supersede to replace it (the old one is kept as history).")
        data.setdefault("superseded_records", []).extend(same)
        data["records"] = [r for r in data["records"] if r["date"] != rec["date"]]
    data["records"].append(rec)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    os.replace(tmp, path)
    if method_entries:
        log_method_conventions(root, rec, method_entries)

    b = rec["bands"]
    print(f"RECORDED {rec['ticker']} {rec['date']} ({rec['mode']})  ->  {path}")
    print(f"  price {price}   call: {audit.get('verdict')}   price / my value {audit.get('price_to_value')}")
    if audit.get("confidence_after_audit") and audit["confidence_after_audit"] != rec["confidence"]:
        print(f"  confidence lowered to {audit['confidence_after_audit']} by the expectations test (the value and the call rule stand)")
    pir = audit.get("price_implied_return")
    print(f"  price-implied return: {pir:.1%} a year" if pir is not None else f"  price-implied return: {audit.get('price_implied_return_note')}")
    conv = audit.get("expected_return_10y")
    if conv is not None:
        print(f"  if the price falls to my value within ten years: {conv:.1%} a year")
    print(f"  letter action prices: buy below {b['buy_below']}   trim above {b['trim_above']}   sell above {b['sell_above']}   zone: {audit['zone']}")
    for e in method_entries:
        print(f"  METHOD LOG: {e['explanation'][:90]} -> docs/method-log.md")
    print(f"  rating {label}   driver: {rating.get('driver')}")
    print(f"  records on file: {len(data['records'])}")


# ---------- blind view ----------

def blind_record(rec):
    r = copy.deepcopy(rec)
    for k in POST_PRICE_KEYS:
        r.pop(k, None)
    r.get("accountability", {}).pop("decision_grade", None)
    iso = r.get("price_isolation", {})
    iso.pop("exposures", None)
    iso.pop("orchestrator_knew_price_before_lock", None)
    for rev in r.get("lock", {}).get("revisions", []):
        if rev.get("after_price"):
            rev["reason"] = "(removed from the blind view)"
    return r


def cmd_blind(a):
    root = bands.find_root(a.root)
    records = bands.load_records(root, a.ticker)
    if not records:
        print(json.dumps({"ticker": a.ticker.upper(), "records": [], "note": "no prior record"}, indent=2))
        return
    shown = records[-a.last:]
    print(json.dumps({"ticker": a.ticker.upper(), "records_on_file": len(records),
                      "note": "price-dependent fields are removed on purpose; do not look for them",
                      "records": [blind_record(r) for r in shown]}, indent=2))
    if a.with_report:
        report = root / shown[-1]["report_path"]
        print("\n===== price-blind part of the latest report =====")
        if not report.exists():
            print(f"(report not found: {shown[-1]['report_path']})")
            return
        text = report.read_text()
        start = text.find(BLIND_START)
        end = text.find(BLIND_END, start + len(BLIND_START)) if start >= 0 else -1
        if start >= 0 and end > start and text.count(BLIND_START) == 1 and text.count(BLIND_END) == 1:
            print(text[start + len(BLIND_START):end].strip())
        else:
            print("(the report does not have exactly one price-blind block in the right order, so none of it is shown)")


# ---------- scorecard and validate ----------

def cmd_scorecard(a):
    root = bands.find_root(a.root)
    folder = root / "data" / "valuations"
    files = [bands.valuations_path(root, a.ticker)] if a.ticker else sorted(folder.glob("*.json"))
    latest = {}
    for f in files:
        if not f.exists():
            continue
        data = load(f)
        for rec in data.get("records", []):
            for g in rec.get("accountability", {}).get("forecast_grades", []):
                latest[(data["ticker"], g["from_record_date"], g["forecast_id"])] = g
    if not latest:
        print("No graded forecasts yet.")
        return
    by_metric = {}
    for (ticker, _, _), g in latest.items():
        if g.get("error") is not None:
            by_metric.setdefault(g["metric"], []).append((ticker, g["error"], g["within_range"]))
    print(f"{'metric':<34}{'graded':>7}{'mean error':>12}{'in range':>10}  note")
    for metric, rows in sorted(by_metric.items()):
        errs = [e for _, e, _ in rows]
        mean = sum(errs) / len(errs)
        same_sign = max(sum(e > 0 for e in errs), sum(e < 0 for e in errs)) / len(errs)
        note = ""
        if len(errs) >= 3 and same_sign >= 0.75 and abs(mean) > 0.05:
            note = "BIAS: forecasts ran too " + ("low" if mean > 0 else "high") + "; review the forecasting method"
        print(f"{metric[:33]:<34}{len(errs):>7}{mean:>+12.1%}{sum(w for _, _, w in rows) / len(rows):>10.0%}  {note}")
    print("\nError = (actual - base forecast) / |base forecast|. Positive means results beat the forecast.")


def cmd_validate(a):
    root = bands.find_root(a.root)
    folder = root / "data" / "valuations"
    files = [bands.valuations_path(root, a.ticker)] if a.ticker else sorted(folder.glob("*.json"))
    schema, errors, count = load(SCHEMA_PATH), [], 0
    for f in files:
        if not f.exists():
            errors.append(f"{f.name}: file not found")
            continue
        data, errs = load(f), []
        check_schema(data, schema, schema, "", errs)
        for rec in data.get("records", []) if isinstance(data, dict) else []:
            count += 1
            if isinstance(rec, dict) and "lock" in rec and "price_isolation" in rec and lock_hash(rec) != rec["lock"].get("lock_sha256"):
                errs.append(f"record {rec.get('date')}: lock hash mismatch (a price-blind field was edited)")
        errors += [f"{f.name}: {e}" for e in errs]
    fail_on(errors, "validation")
    print(f"OK: {len(files)} file(s), {count} record(s) pass the schema and the lock hashes")



# ---------- cross-section, monthly check, rendering ----------

def latest_records(root):
    """Newest record per ticker, from every valuations file."""
    out = []
    for f in sorted((Path(root) / "data" / "valuations").glob("*.json")):
        data = load(f)
        recs = [r for r in data.get("records", []) if isinstance(r, dict)]
        if recs:
            out.append(max(recs, key=lambda r: r.get("date", "")))
    return out


def current_prices(root):
    path = Path(root) / "data" / "prices.json"
    if not path.exists():
        return {}
    return {t: v.get("price") for t, v in load(path).get("prices", {}).items() if isinstance(v, dict)}


def cmd_calibrate(a):
    """Improvement 3 (v9). Is the method one-sided across the batch? Post-price: orchestrator only."""
    root, settings = bands.find_root(a.root), bands.load_settings(a.root)
    live = current_prices(root) if a.current else {}
    rows = []
    for rec in latest_records(root):
        if rec.get("lock", {}).get("valuation_status") not in VALUED:
            continue
        price = live.get(rec["ticker"]) if a.current else (rec.get("audit") or {}).get("price")
        v = rec["values"]
        if price is None or not v.get("weighted"):
            continue
        vb, basis = bands.record_verdict_bands(rec, settings)
        rows.append({"ticker": rec["ticker"], "price": price, "fair_value": v["weighted"],
                     "ratio": round(price / v["weighted"], 3),
                     "above_bull": v.get("bull") is not None and price > v["bull"],
                     "below_bear": v.get("bear") is not None and price < v["bear"],
                     "verdict": bands.verdict(price, vb), "verdict_basis": basis})
    if not rows:
        print("No valued records with a price.")
        return
    ratios = sorted(r["ratio"] for r in rows)
    n = len(ratios)
    median = ratios[n // 2] if n % 2 else round((ratios[n // 2 - 1] + ratios[n // 2]) / 2, 3)
    above, below = sum(r["above_bull"] for r in rows), sum(r["below_bear"] for r in rows)
    shares = {}
    for r in rows:
        shares[r["verdict"]] = shares.get(r["verdict"], 0) + 1
    cw = settings["calibration_warning"]
    warnings = []
    if not cw["median_ratio_low"] <= median <= cw["median_ratio_high"]:
        warnings.append(f"the middle price / fair value is {median:.2f}, outside {cw['median_ratio_low']:.2f} to "
                        f"{cw['median_ratio_high']:.2f}: fair values run {'low' if median > 1 else 'high'} against the market")
    if abs(above - below) > cw["max_tail_imbalance"]:
        warnings.append(f"{above} prices sit above the bull case and {below} below the bear case: the scenario ranges sit "
                        f"too {'low' if above > below else 'high'}")
    if a.json:
        print(json.dumps({"stocks": n, "median_price_to_value": median, "above_bull": above, "below_bear": below,
                          "verdict_shares": shares, "warnings": warnings, "rows": rows}, indent=2))
        return
    for w in warnings:
        print(f"WARNING: {w}")
    print(f"{n} valued stocks, prices from {'data/prices.json' if a.current else 'each record audit'}")
    print(f"  middle price / my value: {median:.2f}")
    print(f"  price above the bull case: {above}   price below the bear case: {below}")
    order = {k: i for i, k in enumerate(bands.VERDICTS)}
    print("  calls: " + ", ".join(f"{k} {v} ({v / n:.0%})" for k, v in sorted(shares.items(), key=lambda x: order.get(x[0], 9))))
    print(f"\n{'ticker':<8}{'price':>10}{'my value':>12}{'ratio':>8}  call")
    for r in sorted(rows, key=lambda r: r["ratio"]):
        tail = " (above bull)" if r["above_bull"] else " (below bear)" if r["below_bear"] else ""
        print(f"{r['ticker']:<8}{r['price']:>10,.2f}{r['fair_value']:>12,.2f}{r['ratio']:>8.2f}  {r['verdict']}{tail}")
    print("\nThe batch review must compare these numbers with one outside reading of the whole market "
          "(for example the S&P 500 forward earnings multiple against its 10-year average) and say so at the top.")


def cmd_monthly_check(a):
    """Improvement 8 (v9). The monthly check, with no agent: which holdings need a refresh or a full run."""
    root, settings = bands.find_root(a.root), bands.load_settings(a.root)
    today = a.date or date.today().isoformat()
    live = current_prices(root)
    limit_days = settings["refresh"]["full_review_after_months"] * 30.44
    rows = []
    for rec in latest_records(root):
        status = rec.get("lock", {}).get("valuation_status")
        if status not in VALUED:
            continue
        price = live.get(rec["ticker"])
        vb, _ = bands.record_verdict_bands(rec, settings)
        now = bands.verdict(price, vb, status) if price else None
        au = rec.get("audit") or {}
        then = bands.verdict(au.get("price"), vb)   # today's rule at the review price, so old strings never trigger
        reasons = []
        fulls = [r["date"] for r in bands.load_records(root, rec["ticker"]) if r.get("mode") == "full"]
        age = (date.fromisoformat(today) - date.fromisoformat(fulls[-1])).days if fulls else None
        if age is None or age > limit_days:
            reasons.append("full: the last full analysis is over a year old (or there is none)")
        earn = (rec.get("next_review") or {}).get("next_earnings_expected")
        if settings["refresh"].get("refresh_after_earnings") and earn and earn <= today and earn > rec.get("information_cutoff", ""):
            reasons.append(f"refresh: earnings expected {earn} have been reported since the record")
        if settings["refresh"].get("refresh_on_verdict_change") and now and then and now != then:
            reasons.append(f"refresh: price crossed a call price ({then} -> {now})")
        if price is None:
            reasons.append("check: no current price in data/prices.json")
        if not earn:
            reasons.append("note: no next earnings date on the record, so the earnings trigger cannot fire; add one at the next refresh")
        rows.append({"ticker": rec["ticker"], "price": price, "fair_value": rec["values"].get("weighted"),
                     "verdict_at_review": then, "verdict_now": now, "record_date": rec["date"],
                     "next_earnings_expected": earn, "action": reasons or ["none"]})
    if a.json:
        print(json.dumps(rows, indent=2))
        return
    print(f"Monthly check {today} (local date). No agent runs unless a row says so.")
    for r in rows:
        print(f"  {r['ticker']:<7} {r['verdict_now'] or '-':<6} {'; '.join(r['action'])}")


def md_money(x, cur="USD"):
    if x is None:
        return "n/a"
    sym = "$" if cur == "USD" else f"{cur} "
    return f"{sym}{x:,.2f}"


def cmd_appendix(a):
    """Improvement 9 (v9). Render appendix parts A, D, and E from the lock. Price-blind: the valuer may run it."""
    rec = load(a.lock)
    verify_hash(rec, a.lock)
    v, b, r, cur = rec["values"], rec["bands"], rec["rates"], rec.get("currency", "USD")
    out = []
    if v.get("weighted") is not None:
        out += ["## A. Scenarios", "", "| Scenario | Probability | Value per share | Story |", "|---|---|---|---|"]
        summ = v.get("summaries") or {}
        for s_name in ("bear", "base", "bull"):
            out.append(f"| {s_name.capitalize()} | {v['probabilities'][s_name]:.0%} | {md_money(v[s_name], cur)} | {summ.get(s_name, '')} |")
        out.append(f"| Stress | not weighted | {md_money(v.get('stress'), cur)} | {summ.get('stress', '')} |")
        out.append(f"| **My value (weighted)** | | **{md_money(v['weighted'], cur)}** | |")
        if v.get("terminal_share_base") is not None:
            out += ["", f"Terminal value is {v['terminal_share_base']:.0%} of the base value."]
        out.append("")
    out += ["## D. Forecasts to grade, milestones, and change conditions", "",
            "| Id | Forecast | Period end | Low | Base | High | Unit |", "|---|---|---|---|---|---|---|"]
    out += [f"| {f['id']} | {f['metric']} | {f['period_end']} | {f['low']:,} | {f['base']:,} | {f['high']:,} | {f['unit']} |"
            for f in rec.get("forecasts", [])]
    out += ["", "| Id | Milestone | Target | By | Status |", "|---|---|---|---|---|"]
    out += [f"| {m['id']} | {m['metric']} | {m['target']} | {m['by_date']} | {m['status']} |" for m in rec.get("milestones", [])]
    out += ["", "| Id | Change condition | Effect |", "|---|---|---|"]
    out += [f"| {c['id']} | {c['condition']} | {c['effect'].replace('_', ' ')} |" for c in rec.get("change_conditions", [])]
    out += ["", "## E. Method notes", ""]
    if r.get("discount_rate") is not None:
        out.append(f"- Discount rate {r['discount_rate']:.2%}: risk-free rate used {r['risk_free_used']:.2%} "
                   f"(observed {r['risk_free_observed']:.2%}, {r.get('risk_free_source') or 'source not given'}) plus the "
                   f"equity risk premium {rec['settings_used']['equity_risk_premium']:.2%}, tier `{r['risk_tier']}`. "
                   f"Tier reason: {r.get('risk_tier_reason') or 'not given'}")
    cd = rec.get("confidence_detail") or {}
    if cd.get("points"):
        pts = cd["points"]
        out.append(f"- Confidence {rec['confidence']} ({cd['total_points']} points: spread {pts['scenario_spread']}, "
                   f"terminal {pts['terminal_share']}, cash {pts['cash_reliability']}, evidence {pts['evidence']})"
                   + (f"; override: {cd['override']['reason']}" if cd.get("override") else "") + ".")
    if rec["lock"]["valuation_status"] == bands.RANGE_ONLY:
        rt = v.get("range_test") or {}
        out.append(f"- Wide range: the bull case supplies {rt.get('bull_share') or 0:.0%} of my value and the range, "
                   f"{md_money(b.get('range_low'), cur)} to {md_money(b.get('range_high'), cur)}, is "
                   f"{rt.get('spread') or 0:.2f} times my value. The call still uses the weighted value.")
    ab = bands.record_verdict_bands(rec, bands.load_settings())[0]
    if ab.get("buy_below_price") is not None:
        out.append(f"- Call rule (the same for every stock): Buy below {md_money(ab['buy_below_price'], cur)} "
                   f"({ab['buy_ratio']:.0%} of my value), Sell above {md_money(ab['sell_above_price'], cur)} "
                   f"({ab['sell_ratio']:.0%}), Hold in between.")
    if v.get("probability_basis"):
        out.append(f"- Probabilities moved from the defaults: {v['probability_basis']['base_rate']} "
                   f"(source: {v['probability_basis']['source']}).")
    iso = rec["price_isolation"]
    kinds = sorted({e.get("kind", "not classified") for e in iso.get("exposures", [])})
    out.append(f"- Price lock: {iso['status']}, {iso['structure']} structure"
               + (f"; logged exposures: {', '.join(kinds)}" if kinds else "; nothing logged") + ". "
               f"Locked {rec['lock']['locked_at']}, sha256 `{rec['lock']['lock_sha256'][:12]}`"
               + (f", {len(rec['lock']['revisions'])} revision(s)" if rec['lock']['revisions'] else "") + ".")
    lf = rec.get("latest_filing_used") or {}
    out.append(f"- Information cutoff {rec['information_cutoff']}."
               + (f" Latest filing used: {lf.get('form')} for the period ended {lf.get('period_end')}." if lf else ""))
    out += ["", "### Sources", ""]
    out += [f"- {s_['title']}" + (f", {s_['date']}" if s_.get("date") else "") + (f". {s_['url']}" if s_.get("url") else "")
            for s_ in rec.get("sources", [])]
    print("\n".join(out))


def cmd_headline(a):
    """The numeric lines of the short report's first page, from the appended record.
    Uses the fixed Buy / Hold / Sell rule on my value, whatever the record's stored verdict says."""
    root, settings = bands.find_root(a.root), bands.load_settings(a.root)
    recs = bands.load_records(root, a.ticker)
    if not recs:
        die(f"no record for {a.ticker}")
    rec = recs[-1]
    au, v, cur = rec.get("audit") or {}, rec["values"], rec.get("currency", "USD")
    if not au:
        die("the newest record has no audit; run record.py append first")
    status, price = rec["lock"]["valuation_status"], au["price"]
    name = rec.get("company_name") or rec["ticker"]
    if not v.get("weighted") or v["weighted"] <= 0:
        print(f"{name} has no call at {md_money(price, cur)}: there is no supported value above zero ({status}).")
        return
    ab = bands.action_bands(v["weighted"], settings)
    call = bands.verdict(price, ab)
    lines = [f"{name} is a {call} at {md_money(price, cur)}. I value it at {md_money(v['weighted'], cur)}.",
             f"Buy below {md_money(ab['buy_below_price'], cur)}. Sell above {md_money(ab['sell_above_price'], cur)}."]
    pir, r = au.get("price_implied_return"), rec["rates"].get("discount_rate")
    rf = rec["rates"].get("risk_free_observed")
    earn = (f"At today's price you earn about {pir:.1%} a year if my forecast is right." if pir is not None
            else f"At today's price the yearly return is {au.get('price_implied_return_note') or 'not computed'}.")
    if r is not None:
        earn += f" This stock should earn {r:.1%} for its risk" + (f" (10-year Treasury {rf:.2%})." if rf is not None else ".")
    lines.append(earn)
    pr = v.get("probabilities") or {}
    if v.get("bear") is not None and v.get("bull") is not None:
        pb, pu = pr.get("bear"), pr.get("bull")
        if pb is not None and pu is not None and abs(pb - pu) < 1e-9:
            odds = f"each about a {pb:.0%} chance"
        else:
            odds = ", ".join(x for x in (f"bad about {pb:.0%}" if pb is not None else "",
                                          f"good about {pu:.0%}" if pu is not None else "") if x) or "chances not recorded"
        lines.append(f"Bad case {md_money(v['bear'], cur)}, good case {md_money(v['bull'], cur)} ({odds}).")
    model = bands.load_model_for(rec, root)
    if model is not None:
        import dcf
        hi_run, lo_run = dcf.safe_run(model, rate_shift=0.01), dcf.safe_run(model, rate_shift=-0.01)
        hi = md_money(dcf.weighted(hi_run), cur) if hi_run else "could not compute"
        lo = md_money(dcf.weighted(lo_run), cur) if lo_run else "could not compute"
        lines.append(f"One point higher required return: {hi}. One point lower: {lo}.")
    else:
        lines.append("Sensitivity to the required return: no saved model file for this record.")
    lines.append(f"Confidence: {au.get('confidence_after_audit') or rec['confidence']}.")
    print("\n".join(lines))


def cmd_tiers(a):
    """Improvement 6b (v9). The tier register, derived from the records. Price-blind: the valuer may run it."""
    root = bands.find_root(a.root)
    rows = []
    for rec in latest_records(root):
        r = rec.get("rates") or {}
        if r.get("risk_tier"):
            rows.append((r["risk_tier"], rec["ticker"], rec.get("company_name", ""), rec["date"], r.get("risk_tier_reason") or ""))
    order = {t: i for i, t in enumerate(bands.TIERS)}
    print("Risk tier register (newest record per ticker). From v9, tiers come from economy-wide downturns and debt only.")
    for tier, t, name, d, reason in sorted(rows, key=lambda x: (order.get(x[0], 9), x[1])):
        print(f"  {tier:<20} {t:<7} {d}  {name}: {reason[:140]}")


def cmd_filing_check(a):
    """Improvement 8 (v9). Compare the lock's share count and latest filing with SEC's XBRL data.
    Prints share counts and filing dates only. It never prints market value fields, so the
    valuer may run it before the lock. SEC asks automated clients to name themselves: set
    SEC_USER_AGENT in the environment to your own client string if SEC refuses the default."""
    import urllib.request
    if a.lock:
        rec = load(a.lock)
    elif a.draft and a.model:
        draft, model = load(a.draft), load(a.model)
        rec = {"ticker": need(draft, "ticker", "draft").upper(), "date": need(draft, "date", "draft"),
               "latest_filing_used": draft.get("latest_filing_used"),
               "values": {"diluted_shares": model["scenarios"]["base"]["diluted_shares"]}}
    else:
        die("give --lock, or --draft and --model (before the lock)")
    agent = os.environ.get("SEC_USER_AGENT")
    if not agent:
        print("NOT RUN: SEC refuses unnamed automated clients. The owner sets SEC_USER_AGENT in their own environment "
              "to enable this check. Until then, check the share count and latest filing date by hand.")
        sys.exit(2)
    headers = {"User-Agent": agent}

    def get(url):
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    try:
        tickers = get("https://www.sec.gov/files/company_tickers.json")
        sec_ticker = rec["ticker"].replace(".", "-")
        cik = next((row["cik_str"] for row in tickers.values() if row["ticker"].upper() in (rec["ticker"], sec_ticker)), None)
        if cik is None:
            print(f"NOT RUN: {rec['ticker']} is not in SEC's ticker list. Check the share count by hand.")
            sys.exit(2)
        facts = get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json")
    except Exception as e:  # network or SEC refusal: report, do not fail the run
        print(f"NOT RUN: could not read SEC data ({type(e).__name__}: {e}). Check the share count by hand.")
        sys.exit(2)
    findings, problems = [], 0
    usg = facts.get("facts", {}).get("us-gaap", {})
    series = usg.get("WeightedAverageNumberOfDilutedSharesOutstanding", {}).get("units", {}).get("shares") or []
    quarterly = [x for x in series if x.get("form") in ("10-Q", "10-K") and x.get("filed", "") <= rec["date"]]
    lock_shares = rec["values"].get("diluted_shares")
    if quarterly and lock_shares:
        last = max(quarterly, key=lambda x: (x["end"], x.get("filed", "")))
        scale = min((10 ** k for k in (0, 3, 6, 9)), key=lambda m: abs(lock_shares * m / last["val"] - 1))
        diff = lock_shares * scale / last["val"] - 1
        ok = abs(diff) <= 0.03
        problems += not ok
        findings.append(f"{'OK  ' if ok else 'FLAG'} diluted shares: lock {lock_shares:,} x {scale:,} vs SEC "
                        f"{last['val']:,} (weighted diluted, period ended {last['end']}, {last['form']} filed {last.get('filed')}): "
                        f"{diff:+.1%}")
    else:
        findings.append("SKIP diluted shares: no us-gaap diluted share series (an IFRS filer?) or no share count in the lock")
    filed = [x for k in ("WeightedAverageNumberOfDilutedSharesOutstanding", "Revenues",
                         "RevenueFromContractWithCustomerExcludingAssessedTax", "NetIncomeLoss")
             for unit in (usg.get(k, {}).get("units", {}) or {}).values() for x in unit
             if x.get("form") in ("10-Q", "10-K") and x.get("filed", "") <= rec["date"]]
    used = (rec.get("latest_filing_used") or {}).get("filed")
    if filed and used:
        newest = max(filed, key=lambda x: x.get("filed", ""))
        ok = newest["filed"] <= used
        problems += not ok
        findings.append(f"{'OK  ' if ok else 'FLAG'} latest filing: lock used one filed {used}; SEC's newest {newest['form']} "
                        f"before the analysis date was filed {newest['filed']}")
    print(f"Filing check {rec['ticker']} ({facts.get('entityName')}), CIK {cik}")
    for f_ in findings:
        print(f"  {f_}")
    print("  " + ("No problems found." if not problems else f"{problems} flag(s): check them against the filing before the lock."))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("lock")
    p.add_argument("--draft", required=True)
    p.add_argument("--model-result")
    p.add_argument("--out", required=True)
    p.add_argument("--revises")
    p.add_argument("--reason-type", choices=["evidence", "error", "method"])
    p.add_argument("--reason")
    p.add_argument("--after-price", action="store_true")
    p.set_defaults(fn=cmd_lock)

    p = sub.add_parser("verify")
    p.add_argument("--lock", required=True)
    p.set_defaults(fn=cmd_verify)

    p = sub.add_parser("append")
    p.add_argument("--lock", required=True)
    p.add_argument("--audit", required=True)
    p.add_argument("--supersede", action="store_true")
    p.set_defaults(fn=cmd_append)

    p = sub.add_parser("blind")
    p.add_argument("ticker")
    p.add_argument("--last", type=int, default=2)
    p.add_argument("--with-report", action="store_true")
    p.set_defaults(fn=cmd_blind)

    p = sub.add_parser("scorecard")
    p.add_argument("ticker", nargs="?")
    p.set_defaults(fn=cmd_scorecard)

    p = sub.add_parser("validate")
    p.add_argument("ticker", nargs="?")
    p.set_defaults(fn=cmd_validate)

    p = sub.add_parser("calibrate", help="after prices: middle price / value, tails, and verdict shares across the batch")
    p.add_argument("--current", action="store_true", help="use data/prices.json instead of each record's audit price")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_calibrate)

    p = sub.add_parser("monthly-check", help="script-only monthly check: which holdings need a refresh or a full run")
    p.add_argument("--date", help="today, YYYY-MM-DD (default: today)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_monthly_check)

    p = sub.add_parser("appendix", help="render report appendix parts A, D, and E from a lock (price-blind)")
    p.add_argument("--lock", required=True)
    p.set_defaults(fn=cmd_appendix)

    p = sub.add_parser("headline", help="render the first lines of the short report from the newest record")
    p.add_argument("ticker")
    p.set_defaults(fn=cmd_headline)

    p = sub.add_parser("tiers", help="risk tier of every valued record (price-blind)")
    p.set_defaults(fn=cmd_tiers)

    p = sub.add_parser("filing-check", help="compare the share count and latest filing with SEC data (before or after the lock)")
    p.add_argument("--lock")
    p.add_argument("--draft", help="before the lock: the lock draft")
    p.add_argument("--model", help="before the lock: the dcf.py model file")
    p.set_defaults(fn=cmd_filing_check)

    for parser in sub.choices.values():
        parser.add_argument("--root", help="project folder (default: found from this script's location)")
    a = ap.parse_args()
    try:
        a.fn(a)
    except (KeyError, TypeError, ValueError) as e:
        die(f"an input file is malformed ({type(e).__name__}: {e}). "
            "Compare it with the templates in references/.")


if __name__ == "__main__":
    main()
