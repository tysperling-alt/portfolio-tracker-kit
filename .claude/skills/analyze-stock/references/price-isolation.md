# Price isolation

Load this before any research. The valuer and the data-pack agent read all of it, and every rule for the valuer binds the data-pack agent too. The orchestrator reads "What the orchestrator must do".

## Why

A value estimate made after seeing the price drifts toward the price. Then "price versus value" tells the owner nothing. So the value, the scenarios, and the buy and sell bands are all fixed before anyone compares them with the market.

## What counts as price information

- The stock's price, past or present. Charts. Returns. 52-week highs and lows.
- Market value of the company (market cap) and enterprise value (market cap plus debt, less cash).
- Multiples built on price: price-to-earnings, EV/EBITDA, price-to-sales, dividend yield, free-cash-flow yield.
- Analyst price targets, ratings, and "undervalued" or "overvalued" commentary.
- Headlines about the stock moving.
- The owner's cost basis, position value, and trade prices.
- The tracker's own bands and ratings from past runs. They were made next to a price.

Not price information: the 10-year Treasury yield, exchange rates, commodity prices, peers' business results, industry data, and the reported fair value of listed shares the company holds as assets (a holding company's stock portfolio on its balance sheet).

## Three walls

1. **A separate agent.** The valuer is a subagent with a fresh context. The orchestrator gives it the ticker, the mode, the date, two folder paths, and in full mode the path to the run's data pack. Nothing else.
2. **A source allow-list.** The valuer reads primary documents only (list below), and never opens the project's price-bearing files.
3. **A stamped lock.** `scripts/record.py lock` writes the lock file with a time and a hash. Lock files are never edited. `record.py append` refuses a lock whose hash does not match.

## Files the valuer must never open

- `data/prices.json` (daily prices)
- `data/holdings.json` (prices, market values, cost basis)
- `data/trades.jsonl` (trade prices)
- `data/valuations/*.json` directly (past audits hold prices)
- `build/` and the tracker page
- Past reports in `analyses/` (their opening and later sections use price)

To read past work, the valuer runs `python3 scripts/record.py blind <TICKER> --with-report`. That prints prior records and the prior report with every price-dependent part removed. Prior model files (`analyses/<TICKER>/*-model.json`) and prior lock inputs are price-blind and may be read. So may the current run's data pack (`analyses/<TICKER>/<date>-datapack.md`), which a price-blind agent wrote under these same rules. If the valuer still finds price information in it, it logs that as an exposure. These commands are also price-blind and allowed: `record.py tiers` (every company's risk tier), `record.py filing-check` (share counts and filing dates from SEC), `record.py appendix` (tables rendered from a lock), and `references/base-rates.md`.

## Sources the valuer may use

- SEC filings on sec.gov: 10-K, 10-Q, 8-K earnings releases, proxy statements (DEF 14A), registration statements. For foreign companies: annual reports and 20-F or 40-F.
- The company's investor-relations pages: releases, call transcripts, presentations.
- Filings and transcripts of competitors, customers, and suppliers.
- Government and industry data. Regulator documents. Court records.
- The Treasury's daily yield page or FRED for the 10-year Treasury yield.
- Trade press on products, customers, and competition.

## Sources the valuer must not use before the lock

- Quote pages and finance portals. `settings.default.json` lists blocked domains. A blocked domain in the source list makes `record.py` mark the run `exposed`.
- Analyst reports, price targets, stock-picking articles, and valuation write-ups.
- News stories about the stock's moves.

## Search rules

- Prefer fetching a known filing address over an open web search. A search results page often shows a quote box.
- Phrase a search around the business fact: "<company> 10-K fiscal 2025 segment operating income". Do not use the words stock, share price, valuation, target, or buy in a query.
- If the search tool takes a domain filter, restrict it to sec.gov and the company's own site.
- Do not open a result from a blocked domain, even for a business fact. Find the fact in a filing.
- If a site asks automated clients for contact details, use a generic client name. Never put the owner's name or email in a request.

## Known leaks inside primary documents

Primary documents carry some price data. Do not seek these parts. If you need a nearby fact, take the fact and move on.

| Where | What leaks | Rule |
|---|---|---|
| 10-K cover page | market value held by non-affiliates | skip the cover page |
| 10-K Item 5 | performance graph, price history, average price paid in buybacks | take shares repurchased and dollars spent only |
| Earnings releases | buyback average price | same |
| Proxy statement | pay-versus-performance return table, dollar value of executive holdings | take share counts and ownership percentages |
| Stock compensation notes | grant prices, exercise prices, option values | take expense and share counts |
| Convertible debt notes | conversion price | take the share count on conversion |
| Call transcripts | analysts mention the stock price or multiple | ignore the remark |
| Form 4 insider filings | transaction prices | leave insider trades to the price audit |

Diluted share count: use the diluted count the company reports. Do not rebuild it with the treasury stock method, because that needs the stock price.

Discount rate: build it from the table in `valuation.md`. Do not use beta or market-value weights. Both come from prices.

## The exposure log and the status

Log every exposure in the lock draft under `price_isolation.exposures`, with what you saw, where, whether it was current (within about twelve months), and its `kind`:

| Kind | What it is | Effect on the status |
|---|---|---|
| `company_filing` | A price printed in the company's own filing or release: a buyback or offering price, a quarter-end price used in guidance, a grant or conversion price. | Always `incidental`. Companies print these routinely, and the method needs the filings. |
| `quote` | A current or recent share price from any other source: a quote page, a search result box, a news story. | `exposed` if current |
| `market_value` | The company's market value or enterprise value. | `exposed` if current |
| `multiple` | A price-to-earnings or other price-based multiple for this company. | `exposed` if current |
| `price_target` | An analyst's price target or rating. | `exposed` if current |
| `valuation_opinion` | Any "undervalued," "overvalued," or fair-value estimate by someone else. | `exposed` if current |
| `price_news` | A story about the stock moving. | `exposed` if current |
| `other` | Anything else that carries the stock's price. | `exposed` if current |

`record.py lock` sets the status from the log. It refuses an exposure without a `kind`.

| Status | Meaning |
|---|---|
| `clean` | You saw no price information during research. |
| `incidental` | You saw only prices printed in the company's own filings, or old or indirect price data, and did not use them. |
| `exposed` | A real leak: you saw a current quote, market value, multiple, price target, valuation opinion, or price story before the lock. |
| `not_applicable` | Funds. A fund has no price-blind value. |

An exposure does not stop the run. Hiding one does. Finish the valuation from the evidence, log the exposure, and tell the orchestrator in the handback. The report states the status in plain words, and the tracker can show it.

One limit cannot be removed: the model that runs this skill may remember an old price from its training. This is stated once, here, for every run. Do not repeat it in each report, and do not log it as an exposure. Do not use the memory. Do not test your value against it.

## What the orchestrator must do

- Do not look up the price, and do not open the price-bearing files, until `record.py verify` passes on the lock.
- If you already know the price (the owner said it, the tracker is open in this session, a batch run loaded prices), you cannot unknow it. Set `orchestrator_knew_price_before_lock` to true in the audit file. Keep it out of the dispatch prompt and out of every message to the valuer.
- Strip from the dispatch prompt: the price, the owner's view of the stock, whether they own it, their cost basis, why they asked, and any news about the stock's move.
- Never edit a lock file. Never retype a value from it into the record. `record.py append` copies the values.
- If you cannot dispatch a subagent, run the valuer brief yourself before any price lookup, and set `price_isolation.structure` to `single_agent`.

## Revising a lock

The first lock is kept. A revision is a new lock file made with `record.py lock --revises <old lock> --reason-type <evidence|error|method> --reason "<what and why>"`. Add `--after-price` if the price audit had started.

Three reasons are valid: new evidence, an error, or a better method. "The price is far from my value" is a reason to audit the model. It is never a reason to change it. Test for an after-price revision: would you make this change if the price sat on the other side of your value? If not, do not make it.

The owner disagreeing is not evidence. If they bring a fact, check the fact. If the fact holds, that is new evidence.
