---
name: portfolio-sync
description: Create or update the tracker's holdings. Use on first run, when the owner shares screenshots of their brokerage positions and data/holdings.json does not exist yet; when they share new brokerage screenshots or private-company equity screenshots; or when they report a trade ("bought 10 shares of ACME in my IRA at $150", "sold half my index fund", "trimmed ACME"). Logs every trade, updates shares and cost basis, flags holdings that changed without a logged trade, then refreshes prices and the tracker page. Use for any change to what the owner holds. Not for valuation; that is analyze-stock.
---

# portfolio-sync

Keeps `data/holdings.json` equal to what the owner actually holds, and keeps a dated record of why it changed.

The owner places every trade themselves. This skill only records trades. It never places, schedules, or recommends a trade.

## Files

- `data/holdings.json`: current positions by account. Share counts and cost basis are the source of truth here. Prices in this file are "as of last sync" only; the page reads fresh prices from `data/prices.json`. The shape is in `examples/holdings.example.json`.
- `data/trades.jsonl`: one JSON line per trade, newest last. Append only. Never rewrite past lines; record a correction as a new line with `"correction_of": <line number>`.
- `scripts/validate.py`: must pass before anything is published.

All three are personal data. The default `.gitignore` keeps them out of git.

### holdings.json fields

- Top level: `as_of` (date of the screenshots), `source` (for example "Brokerage screenshots"), `accounts`, and optional `private_holdings`.
- Each account: `id` (short, lowercase, hyphenated, for example `retirement-ira`), `name` (what the page shows, for example "Retirement IRA"), `broker`, `tax_type` (`roth`, `traditional`, `taxable`, `hsa`, or `other`), `purpose` (one plain line in the owner's words, for example "Retirement, 25+ years" or "College savings in about 10 years"), `total_value`, `cash`, `positions`.
- Each position: `ticker`, `name`, `type` (`stock`, `fund`, `cash-equivalent`, or `cash`), `shares`, `price`, `market_value`, `cost_basis`. Optional `stock_exposure`: the share of the position that falls with the stock market, from 0 to 1. Leave it out for stocks and stock funds (they count as 1). Set it for a bond fund (0), a balanced fund (for example 0.6), or anything that does not move with stocks. The page uses it for the "35% stock fall" column.
- `private_holdings` (optional): private-company stock options or shares. Options: `{"id", "company", "relationship", "type": "options", "grants": [{"grant", "issued", "granted", "vested", "exercised", "strike"}], "fair_market_value_per_share", "valuation_note"}`. Shares: `{"id", "company", "relationship", "type": "common", "shares", "cost_basis", "fair_market_value_per_share", "valuation_note"}`. Never invent a value per share; leave it null until a 409A valuation or a priced round gives one.

## Mode 0: first run (no data/holdings.json yet)

1. Read every screenshot. For each account: the account's name as the broker shows it, account type, total value, cash, and every position (ticker, name, shares, price, market value, cost basis). Leave out account numbers, even partial ones. Do not record the owner's name.
2. If a screenshot is cut off or a column is missing (often cost basis), say exactly what is missing and ask for one more screenshot. Do not guess a number. If the owner cannot get it, use `cost_basis` = `market_value` and note that in `source`.
3. Ask, in one short message, for each account: what the money is for and when it will be needed, in plain words ("What is this account for, and roughly when will you use it?"). Store the answer as `purpose`. Ask the account type only when the screenshot does not make it clear.
4. Pick each `type`: an individual company is `stock`; an index fund, ETF, or mutual fund is `fund`; a money market fund or a Treasury-bill fund is `cash-equivalent`; uninvested cash goes in the account's `cash` field. Set `stock_exposure` for any bond fund, balanced fund, or target-date fund.
5. Write `data/holdings.json`, set `as_of` to the screenshot date, and go to Finish.

## Mode A: the owner reports a trade

1. **Parse** each trade into: date (default today, in the owner's local time zone), account (an existing account `id`, or a new one), ticker, action (`buy`, `sell`, `dividend-reinvest`, `transfer-in`, `transfer-out`, `exercise`), shares, price per share, and the owner's reason in their own words if they gave one.
2. **Fill gaps without asking when the answer is safe.** If they give dollars and not shares, compute shares from the price. If they say "half", compute from current shares. If they do not name the account and the ticker is held in only one account, use that account. Ask one short question only when the answer changes the record and you cannot infer it: for example, a ticker held in two accounts with no account named.
3. **Append** to `data/trades.jsonl`:
   `{"date","account","ticker","action","shares","price","amount","reason","source":"chat","logged_at"}`
4. **Update** the position in `data/holdings.json`:
   - Buy: shares += n. cost_basis += n × price. Set price to the trade price and recompute market_value.
   - Sell: shares −= n. cost_basis −= (n / old shares) × old cost_basis (average-cost method; the broker may use specific lots, so a screenshot sync can correct it later). Remove the position if shares reach zero. For a taxable-account sale, record `realized_gain` = proceeds − basis removed in the trade line, and mark it short-term if the lot is under a year old, when known.
   - Dividend reinvest: shares += n, cost_basis += amount. Cash does not change.
   - Transfer in or out: shares and cost_basis move between accounts unchanged. If the other account is not tracked, adjust only this one and say so.
   - Exercise (private options): in `private_holdings`, move the exercised count from vested to a new common-stock lot with cost = shares × strike. Note that exercising some option types (for example US incentive stock options) can trigger alternative minimum tax, and that the owner should check with a tax preparer before exercising.
   - Fund the trade from the account's `cash` field first, then from its money market or other `cash-equivalent` position if cash would go negative. Never leave cash negative; if neither covers it, ask which position funded the buy.
   - Set `total_value` = positions + cash so the validator passes.
   - A new ticker gets a new position with `type` (`stock`, `fund`, `cash-equivalent`, `cash`).
   - Set `as_of` to today.
5. **Check the valuation record.** If the ticker has a file in `data/valuations/`, compare the trade price to its bands. Tell the owner in one line where the trade sat (for example: "Bought below the buy-below price of $X" or "Sold under my value of $X"). This is information for the accountability record, not a judgment. If a buy is in a ticker with no valuation, say that analyze-stock has not covered it yet, and add it to the next portfolio-review.

## Mode B: the owner shares new screenshots

1. Read every position from each screenshot: ticker, shares, price, market value, cost basis, account totals, and cash. Leave out account numbers. Brokerage layouts differ (for example Schwab, Fidelity, Vanguard, or a robo-advisor); match columns by their headers, not their position.
2. Compare against `data/holdings.json`. Build a change list: new tickers, removed tickers, and share changes.
3. Match each change against `data/trades.jsonl` since the last sync. Report any change with no logged trade as "unlogged": dividend reinvestment explains small fractional increases; for anything else, ask for the date and reason in one line, and log it with `"source":"screenshot-reconcile"`.
4. Before writing, show the owner the change list. If any position would be removed, ask them to confirm it was sold, since a cropped or scrolled screenshot can miss rows. Then replace the account data with the screenshot values. Screenshot cost basis wins over the average-cost estimate.
5. For private-company equity screenshots (from an equity-management site or a grant letter), update `private_holdings`: grants, vested, exercised, strike, and any value shown. Never invent a fair market value.

## Finish (all modes)

1. `python3 scripts/validate.py`. Paste the output. Fix any error before going on.
2. `python3 scripts/refresh_prices.py` (adds prices for any new ticker).
3. `python3 scripts/build_tracker.py`, then republish every dataset whose file changed: `positions`, `valuations`, and `performance` after any change, and `private` too after a private-equity change (CLAUDE.md, "Republish data"). On first run, CLAUDE.md's setup procedure creates the artifact instead.
4. Do not commit personal data. If the owner has opted in to tracking data in a private repo (README, "Keeping your data in git"), commit there with a message like `sync: <action> <ticker> (<account>)`. Do not push unless the owner asks.
5. Reply in two or three sentences: what changed, where the position now sits against its bands, and anything unlogged.
