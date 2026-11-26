# Valuation

The valuer loads this for step 7 of a full analysis and for any refresh that changes the model. Everything here is price-blind.

Paths in commands: `scripts/` is this skill's scripts folder. `analyses/` and `data/` sit under the project folder. Use absolute paths for both.

## 1. Stance

- The base case is the best-supported outlook. It is not a conservative floor. If you would be equally surprised by a result above it or below it, it is the base case.
- Test upside and downside with equal effort. Do not accept a management claim because management made it. Do not reject one because it is ambitious.
- Caution has three homes, and only three: the stress case, the error cushion in the bands, and position size. Do not shade a growth rate, a margin, or a probability "to be safe."
- Weak evidence does not lower the value. It lowers confidence, or it makes the valuation conditional or unresolved (section 8).

## 2. The risk ledger: one home per risk

Each risk is counted once. Fill this table in the report.

| Risk | Home | How it is counted |
|---|---|---|

| Home | What belongs there |
|---|---|
| Cash flows and probabilities | Anything specific to the company that you can describe as an event: losing a customer, a failed product, a patent expiry, a lawsuit, a price war. |
| Discount rate | Only risk that an investor cannot diversify away: how hard the business falls when the whole economy falls, including the effect of debt. Section 3. |
| Error cushion | The chance that your own estimate is wrong. Set by the confidence score in section 9. |
| Position size | Overlap with the owner's other holdings and their job, liquidity, and how bad the stress case is. The orchestrator sets this after the lock. |

Putting one risk in two homes needs a written reason that the two charges cover different things.

## 3. Rates

Two rates, kept apart:

- **Discount rate.** The return an investor needs for bearing this stock's risk. It converts future cash into today's value.
- **Required return.** The return the owner needs to choose a single stock over a diversified fund. It is the larger of their hurdle rate (in settings) and the discount rate. It sets the buy-below price that the monthly letter uses. It never changes the value, and it does not set the valuation verdict.

Get both from the script. Do not compute them by hand.

```
python3 scripts/bands.py rates --risk-free-observed <10-year Treasury yield> --tier <tier> [--ticker T --mode refresh --date YYYY-MM-DD]
```

The script computes: risk-free rate used (the observed yield, with a floor) + equity risk premium + tier adjustment. In refresh mode it keeps the prior record's risk-free rate unless the yield moved half a point or more. This stops small rate moves from shifting every band every month.

Pick the tier from two kinds of evidence only: how the company's sales and profit behaved in economy-wide downturns, and its debt. Nothing else moves the tier.

| Tier | Evidence |
|---|---|
| `defensive` | Sales fell less than 5%, or grew, in the last two downturns. Low fixed costs. Debt under about 1.5 times yearly operating profit before depreciation, with long maturities. |
| `average` | Sales fell 5% to 15% in downturns. Debt under about 3 times. |
| `cyclical_or_levered` | Sales fell more than 15%, or profit fell by half, in downturns. Or debt above about 3 times. Or profits swing with a commodity price. |
| `speculative` | Survival depends on new outside money or on one unproven product. No steady profit yet. |

If the company has not lived through a downturn, use its closest peers' record.

Do not raise the tier for anything that is not an economy-wide downturn. These go in the scenarios and the cash flows, not the rate:

- An industry slump or inventory cycle that is not tied to the whole economy (for example, a chip downturn while the economy grows).
- A price war, a new rival, or a product failure.
- A large capital spending program or other spending commitment.
- Any other company-specific risk.

A risk charged in the rate and again in the bear case is charged twice.

Before choosing, run `python3 scripts/record.py tiers`. It lists the tier and reason of every company already valued. Like businesses get the same tier. If your tier differs from a similar company's, say why in `risk_tier_reason`, in terms of downturn record and debt. `record.py lock` warns when a ticker's tier changed from its prior record.

Do not use beta, and do not use market-value weights for debt and equity. Both come from prices and break price isolation.

Foreign companies: value in the currency of the cash flows. Use that country's 10-year government yield if it is a developed market. Otherwise use the US yield plus the expected inflation gap. Convert the value per share to the listing currency with the exchange rate on the analysis date, and note the ratio of listed shares to ordinary shares.

## 4. Methods

Use two methods that suit the business. The primary method sets the scenario values. The secondary method tests them.

Primary, for most companies: discounted owner cash, ten forecast years plus a terminal value, run through `scripts/dcf.py`.

Secondary, choose one that leans on different assumptions:

- Earnings power value: normalized owner cash with no growth, divided by the discount rate. The gap to the primary value is what you are paying for growth.
- Residual income: book value plus the present value of returns above the cost of equity. Suits banks and insurers.
- Dividend discount: for stable payers.
- Asset value: net asset value, replacement cost, or a supported sum of the parts. Suits real estate, holding companies, and resource companies.
- Justified multiple: a multiple of normalized earnings built from growth, return on capital, and the discount rate. Not a market multiple.

Market multiples and peer multiples are price information. They wait for the price audit.

State which assumptions the two methods share. Agreement between methods that share assumptions is not independent proof. Do not average the two. If they differ by more than a third, find out why and say which you trust. If they differ by more than double and you cannot explain it, the valuation is unresolved.

## 5. The model file

Copy `references/model.template.json` to `analyses/<TICKER>/<DATE>-model.json`. Build the forecast in a Python script saved as `analyses/<TICKER>/<DATE>-forecast.py`, so every number can be rerun. Then:

```
python3 scripts/dcf.py analyses/<TICKER>/<DATE>-model.json --out analyses/<TICKER>/<DATE>-model-result.json
```

| Field | Meaning |
|---|---|
| `basis` | `equity`: cash flows to shareholders, after interest, tax, and net debt service. `firm`: cash flows before interest, to all capital providers. |
| `model_date` | Date of the latest balance sheet used. |
| `valuation_date` | The analysis date. The script rolls the value forward from `model_date` at the cost of equity. |
| `first_forecast_year_end` | Fiscal year-end of forecast year 1. Must fall within one year after `model_date`. |
| `discount_rate` | The rate applied to the cash flows. Equity basis: the discount rate from `bands.py rates`. Firm basis: see below. |
| `equity_rate` | Firm basis only: the discount rate from `bands.py rates`. Omit on equity basis. |
| `risk_free_used` | From `bands.py rates`. Lets the script warn when terminal growth is above it. |
| `payouts_per_share_since_model_date` | Dividends paid per share between `model_date` and `valuation_date`. |
| `scenarios.<name>.probability` | For bear, base, and bull. They sum to 1. The stress scenario has none. |
| `scenarios.<name>.cash_flows` | One number per forecast year. **The first number covers only the rest of forecast year 1 after `model_date`**: the full-year forecast less the cash already earned. |
| `scenarios.<name>.terminal` | See section 6. |
| `scenarios.<name>.claims` | See below. |
| `scenarios.<name>.diluted_shares` | Today's diluted count as the company reports it. |

**Basis.** Use `equity` when debt is low or stable, and for all financial companies. Use `firm` when debt is large or changing. On firm basis, the discount rate is a blend: the cost of equity and the after-tax cost of debt, weighted by the company's target or book mix of equity and debt (not market values). Show the calculation in the forecast script.

**Claims, counted once.**

- Equity basis: `excess_cash` (cash the business does not need to operate), `other_assets` (stakes and assets that produce none of the forecast cash), `other_claims` (pension deficits, legal liabilities, preferred stock). Leave debt out: the cash flows already pay its interest and principal. Leave out interest income on the excess cash.
- Firm basis: `cash_and_investments`, `other_assets`, `debt`, `leases`, `other_claims`. Subtract `leases` only if the cash flows are before lease payments.
- Minority interests and preferred stock go in `other_claims`.

## 6. Terminal value

The terminal value is the worth of all years after the forecast.

- Prefer `value_driver`: `{"method": "value_driver", "next_year_earnings": E, "growth": g, "return_on_new_capital": R}`. The cash flow is E × (1 − g / R). Growth costs investment, so growth with low returns adds little.
- Set R in the terminal period by how long the advantage lasts. An Exceptional business may keep R above the discount rate. For most businesses, move R toward the discount rate. The script's `full_fade` test sets R equal to the discount rate: that is the value if the advantage is gone by the end of the forecast.
- `gordon`: `{"method": "gordon", "next_year_cash_flow": C, "growth": g}`. Use when you have the cash flow directly, as with dividends.
- `fixed`: a stated value at the end of the forecast, such as a liquidation or runoff value. `none`: a business with a finite life.
- Terminal growth should not exceed the **observed** risk-free rate, the yield you read on the analysis date, not the floored rate. The floor raises the discount rate. It does not make the economy grow faster. Put `risk_free_observed` in the model file. `dcf.py` and `record.py lock` both warn when terminal growth is above it. Justify any exception in the report.
- Report the terminal share of base value. Above 75%, most of the value rests on years you cannot see. That lowers confidence through the score in section 9.

## 7. Scenarios and probabilities

- **Base**: the single most likely path.
- **Bear** and **bull**: each a coherent story with causes, each about a one-in-four outcome. Change the drivers that the story changes. Do not apply the same haircut to every line.
- Check the bull case against the company's own ten-year record. A bull case whose growth or margin sits below what the company already achieved needs a reason.
- Start from the default probabilities in settings (25%, 50%, 25%). Move them only with a written base rate from `base-rates.md` or a dated published source. Put it in the lock draft under `values.probability_basis`: `base_rate` (what the rate says), `source` (the row or document), and `not_also_in_forecast: true`. The last one confirms you did not also fade the forecast for the same reason. `record.py lock` refuses moved probabilities without it. Keep each between 10% and 70%.
- Scenarios are not bounds. Results can fall outside them.
- **Stress**: the severe case from `business-analysis.md` section 11. No probability. Not in the weighting.
- An uncertain opportunity (a new product, a pending approval) is valued as: probability × payoff, less the cost to pursue it, at its expected timing. Put the expected value in the base case only when evidence supports the probability. Otherwise put the payoff in the bull case only. Never assume zero. Never assume full success. Never count it twice.

The script computes the weighted value. Read the sensitivity lines it prints: discount rate up and down one point, terminal growth up and down one point, and full fade. An assumption is **decision-sensitive** when a plausible change in it moves the weighted value by 15% or more. List those.

## 8. Resolved, conditional, or unresolved

| Status | Use when |
|---|---|
| `resolved` | The evidence supports a base case and two methods roughly agree. |
| `conditional` | The value holds only if a stated condition is true, such as a contract renewal. State the condition in `lock.conditions` and the value if it fails. |
| `range_only` | The scenarios can be built, but the bull case supplies most of the value or the range is very wide. `record.py lock` requires this status when the bull case supplies more than 60% of fair value, or when (bull − bear) ÷ fair value is 2.0 or more. The record keeps the values. The status is kept for history. The Buy / Hold / Sell call still uses the weighted value, by the same fixed rule as every other stock. |
| `unresolved` | You cannot build base-case owner cash from the evidence. Or the value rests mostly on one event you cannot handicap. Or the accounts cannot be trusted. Or the two methods differ by more than double with no explanation. |

Range-only and unresolved are findings, not failures. Do not force a number. The record then carries no values and no bands, and the tracker shows that. Unsupported segment values added together are not a valuation.

## 9. Confidence

Confidence measures how wrong the value could be. The script computes it from four scores. You supply the inputs. You do not pick the level.

| Factor | 0 points | 1 point | 2 points | 3 points |
|---|---|---|---|---|
| Scenario spread: (bull − bear) ÷ weighted value | under 0.5 | 0.5 to 1.0 | 1.0 to 1.5 | 1.5 or more |
| Terminal share of base value | under 60% | 60% to 75% | over 75% | |
| Cash reliability grade | High | Medium | Low | |
| Decisive questions with `weak` evidence | none | one | two or three | |

Total 0 to 2 is High. 3 to 4 is Medium. 5 to 6 is Low. 7 or more is Very low.

You may move the level one step with `confidence_detail.override`, giving the level and a reason the four factors miss. The record keeps both the computed level and the override.

Do not widen the scenarios to look humble or narrow them to look sure. The spread should be your honest one-in-four outcomes.

## 10. Forecasts, milestones, and change conditions

These make the analysis gradeable. `record.py lock` rejects a valued stock without them.

- **Forecasts**: at least four. Next fiscal year's revenue, operating margin (or the sector's key measure), owner cash per share, and diluted shares. Add the driver behind each decisive question. Give `low`, `base`, and `high`, where low to high should hold the result four times in five.
- **Milestones**: two to five cash-flow checkpoints, each with a number and a date.
- **Change conditions**: three to six testable events. Include at least one with effect `thesis_broken` and at least one with effect `raise_value`. A list with only downside conditions is a bias.

## 11. Lock

1. Copy `references/lock-draft.template.json` to `analyses/<TICKER>/<DATE>-lock-draft.json` and fill it. Do not type values, probabilities, the discount rate, confidence, or bands. The script takes those from the model result and the settings. Give each logged exposure a `kind` (see `price-isolation.md`). Before locking, run `python3 scripts/record.py filing-check --draft <lock draft> --model <model file>`. It compares the diluted share count and the latest filing date with SEC's data and prints nothing about price. If SEC refuses the request or the company files under IFRS, check both by hand.
2. Run:
   ```
   python3 scripts/record.py lock --draft analyses/<TICKER>/<DATE>-lock-draft.json \
     --model-result analyses/<TICKER>/<DATE>-model-result.json \
     --out analyses/<TICKER>/<DATE>-lock.json
   ```
3. Fix whatever the script rejects, in the draft or the model, and run it again. The lock file is written only when every check passes. After that it is never edited.
4. Render the appendix tables from the lock: `python3 scripts/record.py appendix --lock analyses/<TICKER>/<DATE>-lock.json`. Paste its output into the report. Do not retype those tables by hand.

Without a `dcf.py` model (for example a bank valued by residual income), put the bear, base, bull, and stress values, the probabilities, and the discount rate in the draft under `values` and `rates`, point `model_path` at your saved calculation script, and omit `--model-result`.

For an unresolved valuation, set `lock.valuation_status` to `unresolved`, leave values out, and still fill the thesis, grades where you can, evidence gaps, and change conditions that would let a later run resolve it.
