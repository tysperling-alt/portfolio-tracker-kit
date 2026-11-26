# Output: files, record fields, and the contract with other skills

The formal schema is `valuation-record.schema.json`. `scripts/record.py` validates against it and adds the cross-field rules below. This file explains both for people and for the skills that read the record.

## Files one run writes

All paths are relative to the project folder. `<T>` is the ticker in file-safe form: a dot becomes a dash, to match `scripts/build_tracker.py`.

| File | Written by | Price-blind? |
|---|---|---|
| `analyses/<T>/<DATE>-forecast.py` | valuer | yes |
| `analyses/<T>/<DATE>-model.json` | valuer | yes |
| `analyses/<T>/<DATE>-model-result.json` | `dcf.py` | yes |
| `analyses/<T>/<DATE>-lock-draft.json` | valuer | yes |
| `analyses/<T>/<DATE>-lock.json` (and `-lock-r1.json` for a revision) | `record.py lock` | yes; never edited |
| `analyses/<T>/<DATE>-audit.json` | orchestrator | no |
| `analyses/<T>/<DATE>.md` | valuer, then orchestrator | only between the markers |
| `data/valuations/<T>.json` | `record.py append` only | no |

## The valuations file

```json
{"schema_version": "2.0", "ticker": "TICKER", "records": [ ... ], "superseded_records": [ ... ]}
```

Schema version 2.0 started with v9. Records written before it carry 1.0 and stay valid. New fields are optional in the schema file so 1.0 records pass; `record.py` requires them on 2.0 records.

`records` holds one record per analysis date, oldest first. A same-day rerun moves the older record to `superseded_records`. Readers use `records` only.

## Record fields

Units: rates, returns, probabilities, and weights are decimals (0.10 is 10%). Values and prices are per share in `currency`.

| Group | Fields | Notes |
|---|---|---|
| Identity | `ticker`, `company_name`, `asset_type`, `date`, `mode`, `currency`, `report_path`, `model_path` | `mode` is `full` or `refresh`. |
| Evidence | `information_cutoff`, `latest_filing_used`, `sources` | The cutoff is the date of the newest evidence used. |
| `price_isolation` | `status`, `structure`, `exposures` (each with `kind` from 2.0), `orchestrator_knew_price_before_lock`, `revised_after_price` | Status: `clean`, `incidental`, `exposed`, `not_applicable`. A `company_filing` exposure is incidental. |
| `lock` | `locked_at`, `first_locked_at`, `lock_sha256`, `valuation_status`, `conditions`, `valuation_basis`, `primary_method`, `secondary_method`, `secondary_value`, `method_notes`, `model_sha256`, `revisions` | Status: `resolved`, `conditional`, `range_only` (2.0), `unresolved`, `not_applicable`. |
| `values` | `bear`, `base`, `bull`, `weighted`, `stress`, `probabilities`, `summaries`, `terminal_share_base`, `diluted_shares`, `probability_basis` (2.0), `range_test` (2.0) | `weighted` is the fair value. |
| `rates` | `risk_free_observed`, `risk_free_used`, `risk_tier`, `risk_tier_reason`, `discount_rate`, `required_return` | |
| `grades` | `quality`, `management`, `cash_reliability`, `distributability` | |
| Confidence | `confidence`, `confidence_detail` | `confidence` is the level as text. The detail holds the points and any override. |
| `thesis` | `summary`, `decisive_questions`, `key_assumptions`, `key_risks`, `decision_sensitive_assumptions` | |
| Gradeable | `forecasts`, `milestones`, `change_conditions` | Ids start with F, M, and C. |
| `bands` | Call prices: `buy_below_price`, `sell_above_price`. Retired v9 verdict bands, kept as history in older records: `underpriced_below`, `overpriced_above`, `verdict_ratio_low`, `verdict_ratio_high`. Also `range_low`, `range_high`. Action prices for the monthly letter: `buy_below`, `trim_above`, `sell_above`, `buy_return_rate`, `trim_return_rate`, `sell_return_rate`, `error_cushion`, `horizon_years`. Also `fair_value`, `valid_until`. | Formulas: `bands.md`. |
| `accountability` | `prior_record_date`, `forecast_grades`, `milestone_updates`, `change_conditions_tripped`, `value_bridge`, `lock_holds`, `lessons`, `decision_grade` | `decision_grade` is added after the price audit. |
| `audit` | `price`, `price_observed_at`, `price_source`, `market_cap`, `price_to_value`, `verdict` (Buy, Hold, or Sell; older records carry Underpriced, Fairly priced, Overpriced, or Cannot be valued with confidence), `confidence_after_audit`, `verdict_bands_after_audit` (the call prices; older records the retired v9 bands), `price_implied_return`, `price_implied_return_note`, `return_comparison`, `expectations`, `margin_of_safety`, `zone`, `expected_return_10y` (the convergence figure), `implied_growth_shift`, `implied_expectations`, `gap_audit`. 1.0 records also carry `expected_return_5y`, `scenario_returns_10y`, `return_from_gap_closing_10y`. | `price` is the price observed at audit time. The headline return is `price_implied_return`. |
| `rating` | `label`, `driver`, `rationale`, `no_buy_reason` | Labels: Strong Buy, Buy/Accumulate, Starter Position, Hold/Watchlist, Avoid/Do Not Chase, Trim, Sell. Drivers: price, fundamentals, uncertainty, portfolio fit. |
| `decision` | `currently_owned`, `current_weight`, `alternative`, `suggested_size_range`, `size_basis`, `size_adjustments`, `account_actions`, `action_summary` | Required on 1.0 records. Optional from 2.0: allocation moved to the monthly letter. |
| `next_review` | `due`, `next_earnings_expected`, `note` | |
| `settings_used` | hurdle rate, horizon, premium, floor, band shares, source; from 2.0 also `settings_version`, `range_only`, and `action_bands` (older records carry the retired `verdict_bands`) | Makes old records reproducible after a settings change. |
| `fund` | free-form facts | Funds only. |

## Rules the script enforces beyond the schema

At lock:

- A lock file is never overwritten. A revision is a new file that names the old one, with a reason type and a reason. The first lock time is kept.
- Values, probabilities, weighted value, discount rate, confidence, and bands come from the model result and the settings. The draft cannot set them (except values and probabilities when there is no `dcf.py` model).
- The model's cost of equity must equal the rate the settings give for the stated tier.
- Probabilities sum to 1, each between 10% and 70%. Values are ordered bear ≤ base ≤ bull. A stress value exists.
- Probabilities other than the defaults need `values.probability_basis` with a base rate, a source, and `not_also_in_forecast: true`.
- `resolved` and `conditional` are refused when the bull case supplies more than 60% of fair value or (bull − bear) ÷ fair value is 2.0 or more. Use `range_only`.
- Every exposure needs a `kind`. Only a current exposure of a kind other than `company_filing` makes the run `exposed`.
- Warnings (printed, not fatal): terminal growth above the observed risk-free rate; a risk tier that changed from the prior record.
- A valued stock has three decisive questions, quality, management, and cash reliability grades, at least four forecasts, at least one milestone, and change conditions that include both `thesis_broken` and `raise_value`.
- A conditional valuation states its condition. Funds use `not_applicable`, and only funds do.
- `accountability.prior_record_date` equals the latest earlier record's date, or null when none exists.
- Forecast grades must point at forecasts that exist in an earlier record. The script computes the error.
- When both the prior and new weighted values exist, a value bridge is required and must sum.
- Refresh mode needs a prior record and `lock_holds: true`.
- A blocked domain in `sources` sets price isolation to `exposed`. A current exposure in the log does the same.

At append:

- The lock hash must match. Editing any price-blind field after the lock breaks it.
- The script computes price ÷ my value, the call, the price-implied return and growth shift (from the saved model), the convergence figure, margin of safety, zone, and whether a gap audit is required. A required gap audit must have an opposing case and resolving evidence.
- 2.0 records need `audit.expectations` with two or three driver rows. A required gap audit also needs `gap_sources`. An `input_error` is refused (fix it with a revised lock). A `business_disagreement` without evidence lowers `confidence_after_audit` one level; the value and the call rule stand. Each `method_convention` is appended to `docs/method-log.md`.
- Hold/Watchlist and Avoid/Do Not Chase need `no_buy_reason`.
- An unresolved or range-only valuation cannot be rated Strong Buy or Buy/Accumulate.
- When `decision` is present, an owned stock needs at least one `account_actions` row.
- If the audit price was observed before the first lock time, `orchestrator_knew_price_before_lock` must be true.
- If an earlier record exists, `decision_grade` is required and must grade it.
- Records are appended in date order. A same-day rerun needs `--supersede`.

## Contract with the tracker

`scripts/build_tracker.py` reads the newest record in each file. It imports the call rule from this skill's `scripts/bands.py`, so the record and the page agree. These paths are stable:

| Tracker field | Record path |
|---|---|
| My value | `values.weighted` (same number as `bands.fair_value`) |
| Call | price today against `values.weighted` × 0.80 (Buy below) and × 1.20 (Sell above), computed with today's `action_bands` for every record, old or new, range-only included. Stored verdicts and v9 bands are not used. |
| Range | `bands.range_low`, `bands.range_high` (1.0 records: `values.bear`, `values.bull`) |
| Price-implied return | computed at today's price from the record's model file; `audit.price_implied_return` is the figure at review time |
| Required return | `rates.discount_rate`, the return the stock should earn for its risk |
| Buy below, trim above, sell above | `bands.buy_below`, `bands.trim_above`, `bands.sell_above` (the letter's action prices; kept under these names so the page keeps working) |
| Quality | `grades.quality` |
| Confidence | `confidence` |
| Last review | `date` |

Also available to show: `bands.valid_until`, `price_isolation.status`, `lock.valuation_status`, `audit.price` at review time (the call at review time is recomputed with today's rule), and `next_review.due`.

Null bands are normal for funds, unresolved valuations, and a value of zero. Range-only locks have no letter action prices but do have call prices.

`needs_review` is set when the price crossed a call price since the review, or when the next earnings date on the record has passed. A new call is a prompt to run a refresh, not an instruction to trade.

## Contract with portfolio-review

- Call this skill once per holding. Choose the mode by the rules in `SKILL.md`. Funds take the fund path.
- A batch run has prices loaded. That is fine as long as the batch orchestrator passes nothing price-related to each valuer and sets `orchestrator_knew_price_before_lock` to true.
- Run valuers one ticker each. Do not share one valuer across tickers.
- Use `python3 scripts/record.py scorecard` for forecast accuracy, `python3 scripts/record.py calibrate` for the cross-section check, and `python3 scripts/record.py validate` before committing.
- For ranking holdings against each other, compare the price-implied return, `confidence`, and the weight the letter computes. Size and account actions are the letter's job from v9.
- The monthly check is `python3 scripts/record.py monthly-check`, with no agent. A refresh is due after each earnings report and when the price crosses a call price. A full analysis is due once a year.

## Contract with portfolio-sync

- This skill reads `data/holdings.json` only after the lock: `accounts[].id`, `tax_type`, `cash`, `positions[].ticker`, `shares`, `cost_basis`, and `private_holdings`. It never writes to it.
- `decision.account_actions[].account_id` uses the account ids from that file.
- portfolio-sync compares a trade price with `bands` in the newest record. Bands past `valid_until` should be reported as stale.
- This skill reads `data/trades.jsonl` only after the lock, to note whether a trade matched the prior rating.
