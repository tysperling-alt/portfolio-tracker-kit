# Accountability

Every run grades the last one. Part A is price-blind and belongs to the valuer, before the new forecast is built. Part B needs prices and belongs to the orchestrator, after the price audit.

Use only records on disk. Never reconstruct a past forecast or decision from memory. If there is no prior record, say "no prior record" and set `accountability.prior_record_date` to null. `record.py lock` checks this either way.

## Part A: forecasts, milestones, conditions, and the value bridge (valuer)

Read the prior work:

```
python3 scripts/record.py blind <TICKER> --with-report
```

### 1. Grade the forecasts

For each forecast in a prior record whose period has ended and has not been graded yet, find the reported result in a filing. Add one row to `accountability.forecast_grades` in the lock draft:

```json
{"forecast_id": "F1", "from_record_date": "YYYY-MM-DD", "actual": 1012, "actual_source": "10-K fiscal 20XX, income statement"}
```

The script fills in the forecast's low, base, and high, computes the error as (actual − base) ÷ |base|, and marks whether the result fell inside the range. Use the same definition of the metric as the forecast did. If the company changed the definition, restate or drop the grade and say why.

### 2. Update the milestones

For each open milestone, add a row to `milestone_updates` with status `met`, `missed`, `open`, or `dropped`, and a note with the evidence. Carry the full current list, with new statuses, into the new record's `milestones`.

### 3. Test the change conditions

Check each change condition against the evidence. List the ids that tripped in `change_conditions_tripped`. A tripped condition with effect `thesis_broken` or `full_review` ends a refresh: hand back "escalate to full."

### 4. Learn from the grades before forecasting

- One miss is noise. Read it, do not react to it.
- Three or more graded forecasts of the same kind that miss in the same direction are a bias. Run `python3 scripts/record.py scorecard <TICKER>` (or with no ticker for all holdings). Where it flags a bias, find the cause in the method: for example, extending a recent growth rate, or trusting guidance. Change the method and say so in `lessons`.
- Do not add a flat discount to future forecasts to make up for past misses. Do not let a string of misses force a rating. Bias calls for a review of the method, nothing more.
- Separate the kinds of error. A **forecast error** is a wrong operating number. A **model error** is right operations turned into a wrong value: a bad discount rate, a double count, a wrong share count. Price movement is neither.

### 5. Bridge the value change

When a prior weighted value exists, explain the move to the new one in `value_bridge`. Find each part by changing one thing at a time in a scratch copy of the prior model and rerunning `dcf.py`, in this order:

| Part | Change made |
|---|---|
| `time_roll` | Only the valuation date moves to today. |
| `rates` | Then the discount rate changes, if it did. |
| `shares_and_financing` | Then the share count, cash, debt, and other claims update. |
| `operations` | Then the cash flow forecasts and scenario probabilities update. |
| `method` | Whatever remains: a changed method, a corrected error, a split restatement. |

The parts must sum from `prior_value` to `new_value`. The script checks it. A value that moves mostly through `method` needs a clear reason in the report.

## Part B: grade the past decision (orchestrator, after the price audit)

Required when a prior record exists. Read the prior record's `rating`, `decision`, and `audit` directly from `data/valuations/<TICKER>.json`. Add `decision_grade` to the audit file:

```json
{
  "graded_record_date": "YYYY-MM-DD",
  "rating_then": "Buy/Accumulate",
  "alternative_name": "the alternative named in that record",
  "stock_total_return": 0.0,
  "alternative_total_return": 0.0,
  "verdict": "one or two sentences",
  "error_type": "too_early"
}
```

Rules:

- Judge against the alternative named at the time, over the same dates, both with dividends. From v9 a stock record may have no `decision` block; then use the broad stock index fund named in that month's meeting letter (`reviews/<date>-meeting.md`) as the alternative, and say so. A rejection is graded the same way: did the alternative beat the stock? So is a decision to hold cash.
- Judge at the stated horizon. Before three years have passed, price says little. Use `too_early`, report the returns as information, and grade on the operating forecasts from Part A instead: a decision is on track when the business is doing what the forecast said.
- `error_type`: `none`, `forecast` (the operating outlook was wrong), `model` (the valuation method was wrong), `allocation` (the value was right but the size, account, or alternative was wrong), or `too_early`.
- A good outcome from a wrong forecast is still a forecast error. A bad price move with the business on track is not an error.
- If `data/trades.jsonl` shows a trade since the prior record, note whether it matched the rating and where the trade price sat against the bands.

Put the lesson, if there is one, in the report's accountability section. Keep it to what would change a future decision.
