---
name: analyze-stock
description: Value one stock or fund for the owner's long-term portfolio and produce one value per share ("my value"), a Buy, Hold, or Sell call by one fixed rule (Buy at or below 80% of my value, Sell at or above 120%), the return the stock earns at today's price, and a rating. Use when the user says "analyze <ticker>", "what is <company> worth", "should I buy, add to, trim, or sell <ticker>", "refresh <ticker>", "re-run the valuation", "is the thesis still intact", "what do you think of <company>'s earnings", or asks for a deep look at any company or ETF. Also use when the portfolio-review skill needs a refresh of a holding (after an earnings report, or when the price crossed a call price), and when a major event hits a holding (an earnings surprise, an acquisition, a CEO change, a guidance cut). Two modes: full (first analysis, once a year, or a major event) and refresh (after earnings or a band crossing, against the prior record). Writes a dated analysis to analyses/<TICKER>/ and a JSON record to data/valuations/<TICKER>.json for the tracker page. Analysis only; it never places trades.
---

# analyze-stock

Values one stock or fund for a long-term holder. The run fixes a fair value and its bands before anyone looks at the market price, then compares them with the price. It tests what the price assumes against the base case, and reports what a buyer earns at today's price. Allocation, size, tax, and account actions belong to the monthly meeting letter (portfolio-review), not to this run.

This is analysis for the owner's own decisions. It is not licensed financial advice. It never places, schedules, or sends a trade.

## What one run produces

1. A report at `analyses/<TICKER>/<YYYY-MM-DD>.md`.
2. A record appended to `data/valuations/<TICKER>.json`. The tracker page reads it.
3. The saved model, forecast script, lock, and audit file beside the report, so every number can be rerun.

File names use the ticker with a dot turned into a dash. Formats and the contract with `portfolio-review`, `portfolio-sync`, and the tracker: `references/output-schema.md`.

Paths in commands: `scripts/` is this skill's scripts folder. `analyses/`, `data/`, and `context/` sit under the project folder (the folder that holds this `.claude` folder). Use absolute paths.

## Seven rules that do not bend

1. **No price before the lock.** A separate agent, the valuer, builds the value without the price. Until the lock exists, nobody opens `data/prices.json`, `data/holdings.json`, `data/trades.jsonl`, `build/`, the tracker page, or a quote. Details: `references/price-isolation.md`.
2. **The base case is the best-supported outlook, not a cautious one.** Caution lives in three named places only: the stress case, the confidence bands, and position size. Do not optimize for caution anywhere else. Evidence is needed in both directions: a forecast below the company's own record needs it as much as one above the reference class.
3. **Never revise to match the price or to please the owner.** A lock changes only for new evidence, an error, or a better method, through a logged revision. A large gap between price and value triggers an audit of the model and the expectations test, not a change to the value. A gap the audit cannot explain with evidence lowers confidence one level; the value stands. The owner holding the stock, liking it, or pushing back is not evidence.
4. **Scripts do the arithmetic and enforce the rules.** `dcf.py` values the model and solves the price-implied return. `record.py` computes confidence, bands, the verdict, and every price-dependent number, renders the report's tables, and is the only writer of the valuations file. Never edit a lock file. Never type a computed number by hand.
5. **Never invent.** No made-up sources, inputs, calculations, or past decisions. Accountability uses the records on disk and nothing else.
6. **Buy, hold, and sell are separate decisions.** Every "no" says which kind it is. There is no quota of buys, and Hold is not a safe default.
7. **Value is the same in every account. Action is not.** Account actions, size, and tax are decided in the monthly letter, where every account's purpose and date are in view.

## Pick the path

| Situation | Path |
|---|---|
| The ticker is a fund (index fund, ETF, mutual fund, bond fund, commodity or crypto trust) | Fund review. Follow `references/funds.md`. No valuer, no bands. |
| No record in `data/valuations/` for this ticker | `full` |
| The last full analysis is more than 12 months old | `full` |
| A major event since the last record, or the owner asks for a full analysis | `full` |
| A record exists, and an earnings report came out since it or the price crossed a verdict band (`record.py monthly-check` says so) | `refresh` |
| A record exists and none of the above applies | Nothing to run. The monthly check is a script. |
| The valuer hands back "ESCALATE TO FULL" | Run `full` with a new valuer |
| A private company with no market price | Out of scope. Say so. |

To check for a record without reading prices, run `python3 scripts/record.py blind <TICKER>`. Do not open the valuations file yourself before the lock.

## Workflow

| Step | Who | What | Load |
|---|---|---|---|
| 1 | Orchestrator | Set up. Resolve ticker, company name, path, and today's date (the owner's local time zone). Note honestly whether you already know the price. | `references/price-isolation.md`, "What the orchestrator must do" |
| 1b | Data-pack agent (subagent, Sonnet) | Gather and cite the facts, price-blind. `full` mode only. | `references/datapack-brief.md` |
| 2 | Valuer (subagent) | Build the value and the lock from the data pack, price-blind. Write the price-blind part of the analysis. | the valuer loads its own references |
| 3 | Orchestrator | Check the lock. Challenge it. Still no price. | below |
| 4 | Orchestrator | Price audit: scripted numbers, then the expectations table (about 300 words). | `references/audit-and-decision.md` Part 1 |
| 5 | Orchestrator | Returns and rating. No allocation, size, or index comparison. | `references/audit-and-decision.md` Parts 2 and 3 |
| 6 | Orchestrator | Grade the prior decision. | `references/accountability.md` Part B |
| 7 | Orchestrator | Append the record. Validate. Write the narrative first page. | `references/audit-and-decision.md` Part 5, `references/document-layouts.md` |
| 8 | Orchestrator | Reply to the owner. | below |

### Model and effort per step

The expensive model does the judgment. Cheaper models and scripts do the fetching and the arithmetic checks. Do not trade away the three safeguards: price-blind valuation, the independent challenge, and the batch calibration check (`record.py calibrate`).

| Step | Model | Effort |
|---|---|---|
| 1b Data pack | Sonnet | default |
| 2 Valuer, `full` | Opus | `medium`. Use `high` when `record.py blind` shows prior confidence Low or Very low, when there is no prior record and the company has under three years of operating profit, or after a major event. |
| 2 Valuer, `refresh` | Sonnet | default. It escalates to `full` by its own rules. |
| 3 Input checks (verify, five inputs against the filings) | Sonnet, or the orchestrator itself for a single stock | default |
| 3 Challenge, then steps 4 to 7 including the first page | Opus, in one pass: the orchestrator itself for a single stock, or a batch auditor | `medium` |
| Price refresh, monthly check, calibrate | Scripts | none |

Never use a model above Opus for a routine run. The agent that challenges the lock also writes the report's first page in the same pass. No separate writer agent.

### Step 2: dispatch the valuer

For `full` mode, first start the data-pack agent (Sonnet) with this message, blanks filled: "Intent: the purpose is to gather cited facts for a price-blind valuation of <TICKER>. Done means a data pack at analyses/<TICKER>/<date>-datapack.md. If the plan breaks, protect price isolation. Read <skill folder>/references/datapack-brief.md and follow it. Ticker, company, analysis date, project folder, skill folder: <...>." Wait for its handback. Put any exposure it reports into the valuer's dispatch as a line "Data-pack exposures: <what, where, kind>", carrying no price, and the valuer adds each one to `price_isolation.exposures` in its lock draft, so `record.py lock` counts it.

Then start a fresh valuer subagent with the model and effort from the table above. Send exactly this, with the blanks filled, and nothing more:

```
Intent: the purpose is an independent, price-blind valuation of <TICKER> that can be trusted because the market price could not shape it. Done means a stamped lock file and the price-blind part of the report. If the plan breaks, protect price isolation: stop and report an exposure rather than hide it.

You are the valuer for the analyze-stock skill. Read <skill folder>/references/valuer-brief.md and follow it. It is your full instruction set.

Ticker: <TICKER>
Company: <name>
Mode: <full or refresh>
Data pack: <path, full mode only>
Data-pack exposures: <none, or what, where, kind; no price>
Analysis date: <YYYY-MM-DD>
Project folder: <absolute path>
Skill folder: <absolute path>

Do not look up the stock price. Do not open data/prices.json, data/holdings.json, data/trades.jsonl, build/, or any file in data/valuations/. Read past work only through scripts/record.py blind.
```

Leave out the price, whether the owner holds the stock, their cost basis, their opinion, why they asked, and any news about the stock moving. If you cannot start a subagent, follow `references/valuer-brief.md` yourself before any price lookup, and set `price_isolation.structure` to `single_agent` in the lock draft.

### Step 3: check and challenge the lock, before the price

1. Run `python3 scripts/record.py verify --lock <lock file>`. Paste the output.
2. Read the price-blind part of the report. For a full analysis, challenge it from both sides:
   - Is the base case the best-supported outlook, or did caution or optimism shade it? Name the line.
   - List each base-case driver (growth, margin, return on new investment) beside the company's five-year record, and count how many sit below it. Each one below needs named evidence. If most sit below and the evidence is thin, send it back to the valuer.
   - Does each number tie to a cited source? Spot-check three against the filings.
   - Does each risk have one home in the risk ledger?
   - Is the terminal value consistent with the quality grade and the stated length of advantage?
   - Are the bear and bull stories real causal stories of similar likelihood?
   - Would the three decisive questions, answered the other way, change the value? If not, they are the wrong questions.
3. If you find an error, missing evidence, or a better method, send it to the valuer in words that carry no price. The valuer makes a revised lock. Repeat step 1.
4. If the valuer reported an exposure, carry it into the report in plain words. Do not rerun to get a cleaner label.

### Steps 4 to 7

Follow `references/audit-and-decision.md` Parts 1, 2, 3, and 5 in order. It tells you how to fill the audit file and the commands that write and validate the record. Paste the output of each command. Part 4 (allocation and size) is for the monthly letter, not this run.

Then finish the report: write the narrative first page above the start marker (`references/document-layouts.md`), with its numbers from `record.py headline <TICKER>`, and add part F (price audit) below the end marker. Rebuild the tracker data with `python3 <project>/scripts/build_tracker.py`, run `python3 <project>/scripts/validate.py`, and republish the `valuations` and `analyses` datasets as CLAUDE.md's "Republish data" describes, so the report opens when the owner taps the symbol. In a `portfolio-review` batch, the batch does the rebuild and republish once at the end.

If the project is a git repo, commit the new files: `analyze <TICKER> (<mode>)`. The default `.gitignore` keeps analyses and valuations out of git, so usually only code changes are committed. Do not push unless the owner asks.

### Step 8: reply to the owner

Lead with the call. Four short paragraphs, in this order, in plain English:

1. **Call.** Buy, Hold, or Sell at today's price, and "I value it at $X", with price against my value in percent.
2. **Value.** Buy below and sell above prices (80% and 120% of my value), the bad and good cases, and today's price.
3. **Return.** What a buyer earns a year at today's price if the forecast is right, against the stock's discount rate and the 10-year Treasury yield.
4. **Uncertainty.** Confidence, where the base case differs from what the price assumes and the evidence for it, and what would change the call.

Then one line on price isolation if the status is `exposed`, and the path to the report. State times in the owner's local time zone. Do not hedge the call. Account actions wait for the monthly letter. If the owner disagrees, ask what evidence they have; change the model only if the evidence holds, and log it as a revision.

## Running many tickers (portfolio-review)

- Per ticker: one data-pack agent (full mode only), then one valuer. Run tickers in parallel. Never reuse a valuer across tickers.
- Per group of about four tickers: one Sonnet checker runs step 3's input checks (`record.py verify`, five inputs against the filings) and reports any error before prices are read. Then one Opus auditor at medium effort does the challenge and steps 4 to 7, including the narrative first page, in one pass. It finishes the challenge of all its tickers before it reads any price, and stops a ticker if the challenge finds an error.
- The batch orchestrator has prices loaded. That is allowed, because it never touches a lock value. It must set `orchestrator_knew_price_before_lock` to true in each audit file and keep prices out of every dispatch.
- Run `python3 scripts/record.py validate`, `python3 scripts/record.py scorecard`, and `python3 scripts/record.py calibrate` once at the end. Put any calibrate WARNING at the top of the batch review, next to one outside reading of the whole market.

## Settings

Defaults: `references/settings.default.json`. The owner's overrides, if any: `context/analysis-settings.json` (only the keys they changed). Each record stores the settings it used. What each setting does: `references/bands.md`.

## Reference index

| File | Read when |
|---|---|
| `references/price-isolation.md` | Before any research. What counts as price information, allowed sources, the exposure log, revisions. |
| `references/datapack-brief.md` | The data-pack agent's instructions (full mode, before the valuer). |
| `references/valuer-brief.md` | The valuer's instructions for full and refresh modes. |
| `references/business-analysis.md` | Business, lenses, quality grade, owner cash, management grade, failure analysis. |
| `references/base-rates.md` | The outside view: verified base rates for growth and for how long profitability lasts. |
| `references/sector-playbooks.md` | The one section that matches the company's sector. |
| `references/valuation.md` | Rates, methods, the model file, scenarios, confidence, the lock. |
| `references/bands.md` | The verdict bands, and the letter's buy, trim, and sell prices, with a worked example. |
| `references/audit-and-decision.md` | After the lock: price audit, expectations test, returns, rating, writing the record. Part 4 (allocation) is for the monthly letter. |
| `references/accountability.md` | Grading past forecasts (valuer) and past decisions (orchestrator). |
| `references/funds.md` | Any fund. |
| `references/document-layouts.md` | Layouts and writing rules for the report. |
| `references/output-schema.md` | Record fields, enforced rules, and the contract with the tracker and the other skills. |
| `references/valuation-record.schema.json` | The formal schema. |
| `references/*.template.json` | Fill-in shapes for the model, the lock draft, and the audit file. |

## Scripts

| Command | Use |
|---|---|
| `scripts/bands.py rates` | Discount rate and required return for a risk tier. |
| `scripts/dcf.py <model> --out <result>` | Value the scenarios. `--solve-price` (after the lock) shows the growth shift and the price-implied return. |
| `scripts/record.py tiers` | Price-blind. Every valued company's risk tier, so like businesses match. |
| `scripts/record.py filing-check` | Price-blind. Share count and latest filing date against SEC data. |
| `scripts/record.py lock` | Build and stamp the lock. `--revises` for a logged revision. |
| `scripts/record.py verify` | Confirm a lock was not edited. |
| `scripts/record.py appendix` | Price-blind. Render report parts A, D, and E from the lock. |
| `scripts/bands.py returns` | After the lock: verdict, price-implied return, convergence figure, gap check. |
| `scripts/record.py append` | Add the audit, run the expectations test, write the record. |
| `scripts/record.py headline` | After append: the first lines of the first page's numbers table. |
| `scripts/record.py blind` | Past records and analysis with price-dependent parts removed. |
| `scripts/record.py scorecard` | Forecast accuracy across records. |
| `scripts/record.py calibrate` | After prices: middle price ÷ fair value, tails, and verdict shares across the batch. |
| `scripts/record.py monthly-check` | The monthly check, with no agent: which holdings need a refresh or a full run. |
| `scripts/record.py validate` | Check files against the schema and the lock hashes. |
