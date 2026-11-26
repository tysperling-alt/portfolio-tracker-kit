# Price audit, returns, rating, and allocation

The orchestrator loads this after `record.py verify` passes on the lock. Price is allowed from here on. Nothing in this file may change a value in the lock, except through the revision rule in `price-isolation.md`.

Write your answers into a copy of `references/audit.template.json` saved as `analyses/<TICKER>/<DATE>-audit.json`. The script computes every number that depends on price. Do not compute them by hand.

## Part 1: Price audit

Most of this part is scripted (v9). The orchestrator's own writing is the expectations table in step 4, about 300 words.

1. **Get the price.** Read `data/prices.json` first: use `prices.<TICKER>.price` and its `market_time`. If the ticker is missing or the price is more than three trading days old, look up a current quote. Record the price, the time with a time zone offset, and the source.
2. **Run the numbers.**
   ```
   python3 scripts/bands.py returns --lock analyses/<TICKER>/<DATE>-lock.json --price <price>
   ```
   This prints the call (Buy, Hold, or Sell), price ÷ my value, the margin of safety, the price-implied return (the headline: what a buyer at this price earns a year if the weighted forecast comes true), the growth shift the price implies, the price-implied return against the discount rate and the Treasury yield, the convergence figure, and whether a gap audit is required. `record.py append` recomputes all of these from the lock and the model, so nothing is typed by hand.
   Margin of safety is 1 − price ÷ my value. It is not upside. A negative number means the price is above my value.
3. **Find what the price implies, driver by driver.** The growth shift from step 2 is one number. Say it in business terms: what growth, margins, reinvestment, and length of advantage does the price need? To test one driver at a time, copy the model file to your scratch folder, change that driver, and rerun `dcf.py <copy> --solve-price <price>`. Never edit the locked model.
4. **The expectations test (required for every valued stock).** Fill `audit.expectations` in the audit file.
   - `drivers`: two or three rows, one per main driver of value. For each: what the price implies, what analyst consensus expects for the next two years (from a dated source, now that price information is allowed), what the base case assumes, and the evidence for the difference. Write `null` for the evidence when you have none. Do not invent it.
   - `gap_sources`: when the gap is large (the script says so), split it into parts, each with dollars per share:
     - `input_error`: a wrong input, such as a share count, a unit, or a missed debt. This is an error, not a gap. Fix it with a revised lock (step 6). `record.py append` refuses an input error in this list.
     - `method_convention`: a rule of the method that moves value one way for this kind of company, such as how a playbook treats listed stakes. `record.py append` writes it to `docs/method-log.md`. A convention changes for all stocks at once, never for one stock.
     - `business_disagreement`: you and the market expect different things from the business. Name the evidence in `evidence`. If there is none, leave `evidence` null: `record.py append` lowers the recorded confidence one level. The value and the call rule stand.
   This step never changes fair value. The rule holds: a value never moves to match a price.
5. **Market cross-checks.** These were off limits before the lock. Use them now as evidence, not as proof: the stock's multiples against its own history and against peers, recent insider buying and selling, and large holders' activity. If a cross-check surprises you, ask what the other side knows.
6. **Gap audit.** Required when the script says so: the margin of safety is beyond the large-gap threshold in either direction, or the price is below the bear value or above the bull value. A large gap means either the market is wrong or the model is. Check the model first:
   - Do the inputs match the filings? Units, share count, splits, currency. Run `python3 scripts/record.py filing-check --lock <lock>`.
   - Is anything counted twice or left out? Debt, leases, stock compensation, minority interests.
   - Are the scenario stories and probabilities still reasonable when you read them cold?
   - Write the strongest credible case for the other side (`opposing_case`), the assumptions that drive the disagreement, and the evidence that would settle it (`resolving_evidence`). Record what you concluded (`outcome`).
7. **Revise only for evidence, an error, or a better method.** If the audit finds one, describe the problem to the valuer without stating the price, and have it produce a revised lock with `record.py lock --revises ... --after-price`. The first lock stays on file. A gap alone is never a reason to revise.

## Part 2: Returns

The headline is the **price-implied return**: the yearly return a buyer at today's price earns by holding, if the weighted forecast comes true. It assumes nothing about the future price. Compare it with two numbers:

- **The stock's discount rate.** Is the stock priced to earn the return its risk needs? A price-implied return below the discount rate means the price is above my value.
- **The 10-year Treasury yield.** The return with no stock risk.

The script also prints one **convergence figure**, labeled "if the price falls to my value within ten years." It assumes the market comes round to this method's value. Report it on one line, with that label, and never as the headline.

Do not compare the stock with an index fund in the single-stock report. That comparison uses one setting, `index_expected_return`, and belongs to the monthly letter.

## Part 3: Rating

The call is a fact about price and my value: Buy at or below 80% of my value, Sell at or above 120%, Hold in between. The rule is the same for every stock; confidence does not widen it. The rating is a short judgment about the stock alone, with a named driver. Account actions, size, and tax are the monthly letter's job.

| Call | Default rating |
|---|---|
| Buy | Buy/Accumulate. Strong Buy when quality is High or Exceptional, confidence is High or Medium, and the stress value is well above zero. Range-only locks: Starter Position at most (the script refuses Strong Buy and Buy/Accumulate). |
| Hold, price below my value | Starter Position when quality is High or Exceptional and confidence is High or Medium. Otherwise Hold/Watchlist. |
| Hold, price above my value | Hold/Watchlist |
| Sell | Avoid/Do Not Chase |
| No value (unresolved) | Hold/Watchlist or Avoid/Do Not Chase, reason "insufficient evidence" |

Avoid/Do Not Chase means do not buy. It is not a call to bet against the stock. Trim and Sell are portfolio decisions for the monthly letter, with one exception: when a change condition with effect `thesis_broken` tripped, the rating is Sell or Trim with driver `fundamentals`, whatever the call.

Departures from the table are allowed. State the reason in one sentence and name the driver:

| Driver | When it is the main reason |
|---|---|
| `price` | The call decides it. |
| `fundamentals` | The business changed. |
| `uncertainty` | Evidence is thin. For example, Starter Position instead of Buy/Accumulate. |
| `portfolio fit` | Set only by the monthly letter. |

Hold/Watchlist and Avoid/Do Not Chase need `no_buy_reason`:

- **Below required return.** The price-implied return is positive but under the discount rate. The business may be fine. The price is not low enough.
- **Expected loss.** The price-implied return is below what cash pays.
- **Insufficient evidence.** The valuation is range-only or unresolved, or the decisive questions lack support.

Do not move a rating toward what the owner seems to want. Their ownership and their opinion are not evidence about the business.

## Part 4: Allocation and size (monthly letter only)

From v9 this part is not done in a single-stock run. The portfolio-review skill uses it once a month for the whole portfolio, and the meeting letter carries the result. The hurdle rate and the action prices (buy below, trim above, sell above) live there too. A single-stock run leaves `decision` out of the audit file.

Value is the same in every account. Action is not. Read these only after the lock:

- `context/financial-picture.md`: goals, horizon, reserves, what counts as long-term money, each account's purpose and date, tax rates, job and income risk, tolerance for losses. Read its numbers at run time. Use its own definition of long-term investments excluding reserves. If the file marks a figure as stale or uncertain, carry that warning into the report.
- `data/investor-profile.json`: the owner's stated rules, in their words, with dates (for example, how much of the taxable account is set aside for a near-term goal). A rule here overrides an older or inferred statement in the financial picture. No prices are in it, but read it after the lock like the rest of this list.
- `data/holdings.json`: which accounts hold the stock, shares, cost basis, each account's `tax_type`, cash, and `private_holdings`.

If either file is missing, give the size as a percentage range only, skip the per-account actions, and say what was missing.

### Steps

1. **Current weight.** Position value at the audit price across all accounts, divided by long-term investments excluding reserves. Put it in `decision.current_weight`.
2. **Each account's purpose.** Money with a use date inside about five years is not long-term money, wherever it sits. In such an account, do not add stock risk. For stock already there, the question is the account's plan, not the stock's value: the action can be Trim or Sell with driver `portfolio fit` even in the hold zone. The same stock can be an add in a retirement account and a trim in an account set aside for a nearer goal.
3. **Shared risk.** Does this stock fall in the same years the owner's income is at risk? Count their employer's sector, their `private_holdings` (employer options and former-employer stock are exposure to those companies and their sector), and other holdings that move with this one. Reduce the size for overlap, and say by how much.
4. **Drawdown test.** State what a 30% and a 50% fall in this stock would cost, in dollars and as a share of long-term investments. Check that against the tolerance in the financial picture.
5. **Size range for new money**, as a share of long-term investments excluding reserves. "Buy zone" here means the price is at or below the record's buy-below action price:

   | Case | Range |
   |---|---|
   | Exceptional quality, price in the buy zone, confidence High or Medium | 5% to 10% |
   | High quality or better in the buy zone; or Exceptional quality below fair value | 3% to 5% |
   | Good quality or better, price below fair value | 1% to 3% |
   | Confidence Low or Very low, with a supported thesis and price in the buy zone | 0.5% to 2% |
   | Unresolved valuation or unsupported speculation | 0% |

   Reduce for shared risk and for a stress value near zero. If the financial picture sets a tighter per-name limit, the tighter limit wins. A small size cannot fix a poor return: if the price-implied return is below the required return (the larger of the hurdle rate and the discount rate), the size for new money is 0%.
6. **An existing position above the range** is a `portfolio fit` flag, not an automatic sale. Weigh the trim against tax and the alternative. A position above `position_review_weight` in settings always gets an explicit sentence in the report.
7. **Tax check before any Trim or Sell in a taxable account.** Read the tax rate from the financial picture and the cost basis from holdings.
   ```
   keep            = 1 − tax rate × (price − cost basis per share) ÷ price      (when there is a gain)
   return to beat  = (1 + price-implied return of this stock) ÷ keep^(1/N) − 1
   ```
   Selling makes sense when the alternative's expected return is above the return to beat, or when the reason to sell is fundamentals or the account's purpose rather than price. This test leans slightly toward holding, because the tax is mostly deferred, not avoided. In a retirement account the tax rate on a trade is zero and the test falls away. Where the same action is possible in two accounts, prefer the one where it costs no tax and fits the account's horizon. Cost basis is used here and nowhere else. What the owner paid has no bearing on value or on the rating.
8. **Name the action and the alternative** in `decision.action_summary`: maintain the allocation, diversify into a named fund, buy another named investment, reduce risk, or hold cash with a reason. Fill one `account_actions` row per account that holds the stock or would be the right place to buy it.

## Part 5: Write the record

1. Add `decision_grade` if a prior record exists (`accountability.md`, Part B).
2. Set `next_review.next_earnings_expected` to the next earnings date. The monthly check (`record.py monthly-check`) uses it to call a refresh after the report. Set `next_review.due` to the day after that date, or earlier if a change condition is close.
3. Run:
   ```
   python3 scripts/record.py append --lock analyses/<TICKER>/<DATE>-lock.json --audit analyses/<TICKER>/<DATE>-audit.json
   python3 scripts/record.py validate <TICKER>
   ```
   Paste both outputs. Fix what the script rejects in the audit file. Never in the lock.
4. Get the numbers for the first page: `python3 scripts/record.py headline <TICKER>`. Copy them into the first page's numbers table exactly; do not recompute them. Write the narrative around them per `document-layouts.md`.
