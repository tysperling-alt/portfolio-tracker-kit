---
name: portfolio-review
description: Run the 30-day review of the owner's whole portfolio. Runs the script-only monthly check, refreshes only the holdings whose earnings came out or whose price crossed a call price (buy below or sell above), then checks concentration, account fit (each account's purpose and date), shared risk with the owner's job, cash, and drift, and proposes a short, ordered list of rebalancing moves with their tax cost. Writes an advisor-style meeting letter that the tracker page shows. Use when the user says "run the portfolio review", "monthly review", "rebalance check", "how's the portfolio", or when the monthly scheduled task fires. Also use for an off-cycle review when the tracker flags a holding (the price crossed a call price, or an earnings report came out). Analysis only; the owner places every trade.
---

# portfolio-review

The monthly pass over everything the owner holds. It answers three questions, in this order:

1. Is each holding still worth what we said, and where is its price against its buy-below and sell-above prices?
2. Does the portfolio as a whole fit the owner's goals, dates, and risks?
3. What, if anything, should they do this month, in which account, and what does it cost in tax?

"Do nothing" is a real answer and often the right one. This is not day trading. A move needs a reason that would still hold in a year.

This is analysis for the owner's own decisions, not licensed financial advice. It never places a trade.

## Inputs

- `data/holdings.json`: what they hold, by account, with each account's `purpose`. If `as_of` is more than 35 days old, say so in the first line of the report and ask for fresh brokerage screenshots (portfolio-sync, Mode B). Run the review on the data you have; do not wait.
- `data/prices.json`: refresh first with `python3 scripts/refresh_prices.py`.
- `data/valuations/<TICKER>.json`: each holding's records (analyze-stock writes them).
- `context/financial-picture.md`: goals, reserves, near-term needs and their dates, income and job risk. If it is more than 90 days old, flag it and list the facts that need updating.
- `data/investor-profile.json`: the owner's stated rules, in their words, with dates. A rule here overrides the financial picture where they differ. Ask any `open_questions` at most once per review, only when the answer would change a move.
- `context/analysis-settings.json`: the owner's overrides of analyze-stock defaults, if any.
- `data/targets.json`: target allocation per account pool, if the owner has set one. If not, the review proposes one as a decision for them, once, and does not repeat the ask every month.

## Step 1: decide what gets valued

Start with the script, not an agent:

```
python3 .claude/skills/analyze-stock/scripts/record.py monthly-check
```

It compares each holding's price with its call prices (80% and 120% of my value) and reads the next earnings date on each record. It says, per stock, whether a refresh or a full analysis is due. For a ten-year holder, value moves about 8% to 10% a year, so most months most holdings need no agent.

Build the list from holdings. For each ticker:

| Holding | Treatment |
|---|---|
| Individual stock, no record yet | analyze-stock `full` |
| Individual stock, the last full analysis over a year old | analyze-stock `full` |
| Individual stock, monthly-check says refresh (earnings reported, or the price crossed a call price) | analyze-stock `refresh` (it escalates to `full` by its own rules) |
| Individual stock, monthly-check says none | No agent. Carry the record forward. |
| Fund or ETF | analyze-stock fund path (no bands) |
| Any holding under 0.5% of the portfolio | No valuation. One paragraph: keep, exit, or grow it to a real size, and why. A position too small to matter still costs attention. |
| Cash and money funds | No valuation. Count toward the cash check in step 3. |
| Private holdings | No valuation. Note vesting, exercise cost, and any new value information. |

Run valuations in order of combined portfolio weight, largest first. Follow analyze-stock's "Running many tickers" rules and its model-and-effort table: a Sonnet data pack and an Opus valuer per ticker for a full analysis, a Sonnet valuer for a refresh, one Sonnet checker and one Opus auditor per group of about four tickers, and prices never in a dispatch. Most months only refreshes are due; a full analysis runs once a year per stock or after a major event. If the run cannot finish every analysis, finish the largest holdings, list the rest as carried to next month, and say so at the top.

## Step 2: holding table

For each holding: combined value across accounts, weight, call (Buy, Hold, or Sell, by the fixed rule on my value), the price-implied return beside the stock's discount rate, the action zone against the letter's buy, trim, and sell prices, rating, change since last month in my value and in price, and whether the thesis still holds. Mark any holding whose call changed.

Then run `python3 .claude/skills/analyze-stock/scripts/record.py calibrate`. If it prints a WARNING, put it at the top of the working review, beside one outside reading of the whole market (for example the S&P 500 forward earnings multiple against its 10-year average, with source and date).

## Step 3: portfolio checks

Work out each in numbers, from the files. Never estimate a number a file holds.

1. **Concentration.** Combined weight per company across all accounts, including look-through for the index funds where it matters (an S&P 500 fund holds several percent in each of the largest tech names). Set each stock's size range here, with `analyze-stock/references/audit-and-decision.md` Part 4: the single-stock run does not set it. Flag any company over its range and any group of correlated names (for example, the large tech platforms together) over about a third of the portfolio.
2. **Account fit.** Money has a date. Read each account's `purpose` in holdings and any matching rule in `data/investor-profile.json`. Long-horizon money (retirement in 15+ years) can ride out a deep fall. Money needed within about five years cannot: for it, a fall of 30% to 50% is a real risk to the goal, not a paper loss. For every account or slice with a date inside five years, state plainly how much of it sits in stocks, what a 35% fall would do to it, and whether the owner's stated slack (for example "I could wait one more year") would likely cover a recovery. When near-term money is invested in stocks, this is the most important check.
3. **Shared risk.** If the financial picture names the owner's employer or industry, or `private_holdings` holds employer equity, count the holdings that fall in the same conditions that would cost the owner income. For example, tech stocks and a tech job tend to fall together.
4. **Cash.** Cash and cash-like funds per account against any reserve or near-term need in the financial picture. Idle cash in a retirement account is a drag; cash in a near-term fund may be the point.
5. **Drift.** If `data/targets.json` exists, each pool's current mix against target. Act only when drift passes the band set there (default: 5 percentage points).
6. **Small and stale positions.** Positions under 0.5%, and losers held only to avoid taking the loss.

## Step 4: moves

Write at most five moves, ordered by importance. Each move names: the account, the ticker, buy or sell, about how much in dollars, the reason (which check or which band), the tax effect, and the alternative if they do nothing.

Tax rules for the moves (US accounts; adapt to the owner's country if the financial picture says otherwise):

- Prefer making changes inside tax-sheltered accounts (Roth or traditional IRA, 401k, HSA). Trades there have no tax.
- In a taxable account, estimate the gain from the cost basis in holdings. Say whether it is long-term (held more than a year) or short-term when the lot dates are known; when they are not, say the term is unknown. Note any loss that could offset a gain, and the 30-day wash-sale rule if a sale at a loss would be followed by a buy of the same stock.
- Never let tax alone keep a position that is clearly too large for money with a near date. Show the tax cost next to the risk it removes.

A move can be "add" as well as "trim". A holding in its buy zone with room under its size range is a candidate for new money.

The hurdle rate and the action prices live here. The buy-below price needs the hurdle return (default 10% a year) with the error cushion, and the trim and sell prices mark where the extra return over Treasuries is half gone or all gone. When a move compares a stock with an index fund, use the one setting `index_expected_return` (see its note in `settings.default.json`), and mention the lower outside estimates there when the comparison decides the move. Run the tax check in Part 4, step 7, with the stock's price-implied return.

## Step 5: write, publish, hand off

1. Write the working review to `reviews/<YYYY-MM-DD>.md`: holding table, portfolio checks, moves, carried items, and data-freshness notes. This is the record.
2. Write the meeting letter to `reviews/<YYYY-MM-DD>-meeting.md`. It is what the owner reads, in the tracker's Monthly meeting section. Write it as a monthly meeting with a financial advisor: warm, plain, direct, in the second person ("your retirement money"). Title line `# <Month YYYY> meeting`, then the one-line disclaimer, then these sections:
   - **Where you stand**: total value, gain over cost, each account's value and purpose, and past-year return against the S&P 500 (from `build/performance.json`), in one short table.
   - **The main conversation**: the one portfolio issue that matters most this month, explained in a few paragraphs with dollar figures.
   - **What I recommend, in order**: the moves from step 4, grouped as tax-free moves in sheltered accounts first, then loss sales, then taxable moves, each with account, size in dollars, estimated tax, and the reason. Write each move as its own bold numbered line, `**1. <move in one sentence>.**`, followed by its detail; the page lists these lines as the month's moves. Say which moves depend on my values and which stand regardless.
   - **What I would leave alone**, and why.
   - **Questions for you before next month**: only questions whose answers would change a move.
   - **Next meeting**: the date and what you will check.
   From the second meeting on, open with what changed since last month and whether the owner made the suggested moves (from `data/trades.jsonl`).
3. `python3 scripts/build_tracker.py`, then republish the `positions`, `valuations`, `performance`, `analyses`, and `meetings` datasets (CLAUDE.md, "Republish data"). The company tiles show only Buy, Hold, or Sell calls against my value. Portfolio advice appears only in the meeting letter.
4. `python3 scripts/validate.py` and the analyze-stock `record.py validate` and `record.py scorecard`. Paste the output.
5. Reviews are personal data and stay out of git by default. Commit only code changes, and only if the project is a git repo. Do not push unless the owner asks.
6. Reply to the owner in two or three sentences pointing them to the Monthly meeting section, plus anything they must send or decide (screenshots, a setting). Times in the owner's local time zone.

## Off-cycle review

When the tracker's `needs_review` flag is set for a holding (the price crossed a call price since the last review, or the next earnings report came out), run analyze-stock `refresh` on that holding alone, then steps 3 and 4 only if the result changes a move. Do not rerun the whole portfolio.
