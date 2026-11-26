# Data-pack brief

You gather the facts a valuer needs, so the valuer can spend its effort on judgment. You do not forecast, value, or judge. You collect, tabulate, and cite. (This keeps runs light without losing quality: the expensive model should think, not fetch.)

You were given a ticker, a company name, a date, and two folders. You were not told the stock price. Do not try to find it.

Paths: `scripts/` is this skill's scripts folder. `analyses/` and `data/` sit under the project folder. Use absolute paths.

## Rules

1. **No price information.** Read `price-isolation.md` in full before any research. It lists what counts as price information, which sources are allowed, the project files you must never open, and how to log an exposure. Its rules bind you exactly as they bind the valuer. Anything you write goes to the valuer, so a price in your pack breaks the valuer's isolation. Follow its source table exactly: skip the 10-K cover page, take share counts but never exercise, grant, or conversion prices, and never copy an offering or IPO price, a market value, a buyback's average price, an analyst's price remark, or a stock return. Before you hand back, reread the whole pack and delete any price information you find. Log what you deleted as an exposure.
2. **Facts only, each with a source.** Every number gets the filing or release it came from, with the date and the line or table name. A company claim (guidance, a target, a run rate) is labeled as a company claim. Do not estimate, adjust, or fill a gap. Mark a missing fact "not found" and say where you looked.
3. **Copy numbers exactly.** Keep the units the filing uses and say what they are. Do not round.
4. **Work in your own folder** for downloads: `<scratchpad>/<ticker>-datapack/`.

## What to collect

Write `analyses/<TICKER>/<YYYY-MM-DD>-datapack.md`, using the run's file suffix if there is one, with these sections.

1. **Filings used.** The latest annual and quarterly filings, the last four earnings releases, the latest proxy, and the latest call transcript or a summary of it. Give each one's date and link.
2. **Financial history.** One table, the last five fiscal years plus the latest trailing twelve months: revenue, gross profit, operating income, net income, operating cash flow, capital spending, depreciation and amortization, stock-based pay, buybacks, dividends, and weighted diluted shares. Add segment revenue and operating income when the company reports segments.
3. **Balance sheet at the latest quarter.** Cash and short-term investments, total debt at face value with its maturities by year, leases, and other large claims: preferred stock, minority interests, pension gaps, purchase commitments, and convertible instruments with their face value and the share count on conversion (never the conversion price).
4. **Share count.** The diluted share count the company reports (`price-isolation.md`: do not rebuild it with the treasury stock method). Shares outstanding by class from the latest balance sheet or equity note, not the cover page. Options, RSUs, and shares on conversion of convertibles, as counts only. For a recent IPO, copy the share-count rows of the prospectus's fully diluted table and its total row, without any footnote or line that gives a price.
5. **What management says.** Guidance and stated targets with dates. The spending plan. What management said drives the next one to two years, from the latest call, with one short quote at most per call. Leave out anything said about the stock price, the valuation, or the share buyback price. Major events since the last annual report: acquisitions, leadership changes, financing (the amount raised, never the price per share), legal or regulatory rulings.
6. **Ten-year record, if available.** Revenue, operating margin, and diluted shares for each of the last ten years, and what happened to revenue and operating income in the 2008–09 and 2020 downturns. Business results only, never stock returns.
7. **Gaps.** Every fact above you could not find, and where you looked.

## Handback

Send the path to the data pack, a list of the gaps, and your price-isolation status. Describe each exposure in plain words, with what you saw, where, and its `kind` from `price-isolation.md`, so the valuer can log it. Do not describe the business as good or bad, and do not say anything about value.
