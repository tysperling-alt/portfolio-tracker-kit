# Price bands: the call prices and the letter's action prices

`scripts/bands.py` computes two kinds of band when the lock is made. Every input is price-blind. The bands exist before anyone looks at the market price. This file explains the formulas so anyone can recompute a band from the saved record.

- **Call prices** (buy below, sell above) set the Buy / Hold / Sell call the tracker shows. They depend only on my value.
- **Action prices** (buy below, trim above, sell above in `bands.buy_below` and the rest) use the owner's hurdle rate. They feed the monthly letter only. They never set the call.

## Call prices: one fixed rule for every stock

My value is the probability-weighted value per share (`values.weighted`). Reports say "I value it at $X."

```
buy_below_price  = my value × 0.80
sell_above_price = my value × 1.20
```

The call is **Buy** when the price is at or below `buy_below_price`, **Sell** when it is at or above `sell_above_price`, and **Hold** in between. The rule is the same for every stock. Confidence is recorded but does not widen it. The point is a committed call on every stock. The ratios live in `action_bands` in the settings.

**Range only.** A lock with status `range_only` keeps that status for history. The call still uses the weighted value, like any other stock.

**Older records.** The tracker, `record.py headline`, and `record.py calibrate` compute the call prices for every record from its weighted value with today's ratios. Stored v9 bands and stored verdict strings are history only.

**Retired: confidence-widened verdict bands.** An older method version used Morningstar's 5-star and 1-star thresholds by confidence (80/125% for High, 70/135% Medium, 60/155% Low, 50/175% Very low), widened one level more when the expectations test found unsupported disagreement. The wide bands left most stocks "fairly priced," which is not a committed call. Records made under that version keep `underpriced_below`, `overpriced_above`, and `verdict_bands_after_audit` as history.

## Action prices (monthly letter)

### The idea in three sentences

Fair value is the probability-weighted value per share. Each band is the price at which the convergence return over the horizon hits a set level. Each band is then moved further from fair value by an error cushion that grows as confidence falls.

## Inputs

| Input | Symbol | Where it comes from |
|---|---|---|
| Fair value per share | V | `values.weighted` |
| Discount rate | r | `rates.discount_rate`: risk-free rate used + equity risk premium + tier adjustment |
| Risk-free rate used | f | `rates.risk_free_used`: the 10-year Treasury yield, with a floor |
| Required return | h | `rates.required_return`: the larger of the hurdle rate and r |
| Horizon in years | N | `settings.horizon_years` |
| Error cushion | c | `settings.error_cushion` for the confidence level |

### The return assumption

If the model is right, the value of the business to its owners grows at r a year, counting cash paid out. Assume price meets value at the end of N years. Then buying at price P gives a yearly return of:

```
return(P) = (1 + r) × (V / P)^(1/N) − 1
```

At P = V the return is r. Below V it is higher. Above V it is lower. Solving for the price that gives a target return t:

```
anchor(t) = V × ((1 + r) / (1 + t))^N
```

This is the **convergence** assumption: price meets value. It is used to place the action prices. It is not the headline return. The headline is the price-implied return from `dcf.py`, which assumes nothing about the future price (see `audit-and-decision.md`, Part 2).

### The three action prices

```
buy_below  = anchor(h)                 × (1 − c)
trim_above = anchor(f + 0.5 × (r − f)) × (1 + c)
sell_above = anchor(f)                 × (1 + c)
```

In words:

- **Buy below**: the price at which the convergence return equals the required return, less the error cushion. Below this price, the stock clears the owner's hurdle even if the value estimate is too high by the cushion.
- **Trim above**: the price at which the convergence return keeps only half of the extra return this stock should pay over a Treasury bond, plus the error cushion.
- **Sell above**: the price at which the convergence return equals the Treasury yield, plus the error cushion. Above this price the stock offers no extra return for its risk, even if the value estimate is too low by the cushion.

The 0.5 and the 0 are `trim_premium_share` and `sell_premium_share` in settings.

### The error cushion

| Confidence | Cushion |
|---|---|
| High | 5% |
| Medium | 15% |
| Low | 25% |
| Very low | 35% |

Confidence comes from the four-factor score in `valuation.md` section 9. The cushion is where estimation error is charged in the action prices. It works in both directions: lower confidence means a lower buy price and higher trim and sell prices. With a fuzzy value, the right response to a price near value is to do nothing.

### What moves an action price

- A higher fair value moves all three up in proportion.
- A higher risk tier raises r. That lowers fair value through the model. It also widens the trim and sell bands, because a riskier stock should pay more over Treasuries before it is called expensive.
- When r is at or above the hurdle rate, the required return equals r, and the buy band is fair value less the cushion.
- Lower confidence widens all three.
- Business quality does not enter here. It is already in the cash flows.

### Worked example with made-up numbers

A made-up company: V = 24.66, r = 8.8%, f = 4.3%, hurdle 10% so h = 10%, N = 10, confidence Medium so c = 15%.

```
buy anchor  = 24.66 × (1.088 / 1.100)^10  = 24.66 × 0.8961 = 22.10
buy_below   = 22.10 × 0.85                                  = 18.78

trim rate   = 4.3% + 0.5 × (8.8% − 4.3%)                    = 6.55%
trim anchor = 24.66 × (1.088 / 1.0655)^10 = 24.66 × 1.2324 = 30.39
trim_above  = 30.39 × 1.15                                  = 34.95

sell anchor = 24.66 × (1.088 / 1.043)^10  = 24.66 × 1.5258 = 37.63
sell_above  = 37.63 × 1.15                                  = 43.27
```

The call prices for the same company are 24.66 × 0.80 = 19.73 (Buy below) and 24.66 × 1.20 = 29.59 (Sell above), whatever the confidence.

Check it: `python3 scripts/bands.py compute --value 24.66 --discount-rate 0.088 --risk-free-used 0.043 --confidence Medium`

### Zones

A zone places the price against the action prices. The monthly letter uses it. The same rule runs in `scripts/bands.py` and in `scripts/build_tracker.py`:

| Zone | Rule |
|---|---|
| `buy zone` | price at or below buy_below |
| `hold zone` | between buy_below and trim_above |
| `trim zone` | at or above trim_above, below sell_above |
| `sell zone` | at or above sell_above |
| `no bands` | range-only or unresolved valuation, a value of zero, or a fund |

A zone is a fact about price and the action prices. A rating is a judgment made at review time, with a named driver. When the daily price crosses a call price between reviews, that is a prompt to run a refresh. It is not an instruction to trade.

The hold zone is wide by design. A long-term holder who pays tax on gains should act rarely.

## Shelf life

`bands.valid_until` is the analysis date plus `bands_valid_days` (45). Value grows about r a year, so bands drift up slowly. A refresh after each earnings report rolls them forward. After the valid-until date the tracker marks the bands stale; for a ten-year holder a stale band between earnings reports is normal, and the monthly check (`record.py monthly-check`) decides whether a refresh is due.

After a stock split, the old per-share bands are wrong. A refresh must restate them before comparing.

## Settings

Defaults are in `references/settings.default.json`. To change one, put only that key in `context/analysis-settings.json`. Each record stores the settings it used, so old records stay reproducible after a change.

| Setting | Default | Effect |
|---|---|---|
| `action_bands` | 0.80 / 1.20 | Buy at or below 80% of my value, Sell at or above 120%. The same for every stock. |
| `range_only` | bull share 60%, spread 2.0 | When the lock must be marked range-only (history; the call is unchanged). |
| `index_expected_return` | 8.4% | The index fund's expected return. The monthly letter only. |
| `calibration_warning` | 0.80 to 1.25, tails 3 | When `record.py calibrate` warns. |
| `hurdle_rate` | 10% | Higher means lower buy-below prices. The monthly letter only. |
| `horizon_years` | 10 | Longer means lower buy-below and higher trim and sell prices. |
| `error_cushion` | 5 / 15 / 25 / 35% | Larger means wider bands. |
| `risk_free_floor` | 4% | Stops very low bond yields from inflating every value. |
| `equity_risk_premium` | 3.75% | The extra return expected from stocks over Treasuries. |
| `risk_tier_adjustments` | −1 / 0 / +1.5 / +3 points | Per tier, added to the discount rate. |
| `trim_premium_share`, `sell_premium_share` | 0.5, 0 | Where the trim and sell bands sit. |
| `rate_update_threshold` | 0.5 point | A refresh keeps the prior risk-free rate unless the yield moved this much. |
