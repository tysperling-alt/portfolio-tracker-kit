# Layouts for the report

Each run saves one report for the owner at `analyses/<TICKER>/<YYYY-MM-DD>.md`. Use the ticker's file-safe form in the path: a dot becomes a dash. If a file for that date exists, add `-2` to the file name.

## Writing rules

- Plain English. Short sentences. Short paragraphs. Active voice. No em dashes.
- Define a technical term the first time it appears, in a few words.
- Use the same word for the same thing throughout. In owner-facing text the probability-weighted value is "my value" ("I value it at $X"), because "fair value" is jargon to most readers. The records and appendix keep the field name fair value.
- Stake an opinion. Lead with one value and one call, and never hide behind a range or a confidence label. Describe uncertainty this way: name the assumptions that move the value most, give their dollar effect, and say whether that uncertainty changes the call. The reader knows investing is uncertain and wants an opinion based on the research.
- Lead every section with its conclusion. Detail follows.
- Give numbers with units and dates. Show percentages to one decimal place and per-share values to cents.
- Mark what kind of statement each key claim is: fact (with source), company claim, estimate, or judgment.
- State the decision. Do not hedge it. If the evidence is thin, say that once, in the confidence line.
- Tables are for numbers. Reasoning goes in sentences.
- The first page is a narrative, not a list of model outputs. It reads like a letter from an advisor who studied the company: the evidence sits inside the sentences that use it, with the number, the date, and the source. It explains the business case and what the company itself is betting will happen. It ends with a plain recommendation. 800 to 1,100 words.
- Model terms stay out of the first page: no "owner cash", "terminal value", "expectations test", "change condition C5", "basis points", tier names, or forecast ids. Say what they mean instead. The appendix keeps the terms.
- The title carries the call: **Buy**, **Hold**, or **Sell**. Buy when the price is at least 20% below my value, Sell when it is at least 20% above, Hold in between. The rule is the same for every stock and every confidence level (`bands.md`).
- Allocation, size, drawdown, tax, and the index-fund comparison are decided in the monthly meeting letter, not in a single-stock report. The first page's "What I recommend" section states the call and the buy-below and sell-above prices and repeats, in one or two sentences, what the latest monthly letter suggests for the owner's shares and why (price, or size and the account's purpose and date). If no letter covers the stock yet, say the next letter will set the action. The report must make the price evaluation and the recommendation clear.
- Do not write a sentence that the model may remember old prices. `price-isolation.md` states it once for every run.
- Keep a full report under about 2,700 words, appendix included. Tables the script renders do not count against the valuer's own writing.

## Who writes what

The valuer creates the file with a title placeholder and everything between the two price-blind markers: the appendix parts B and C in its own words, and parts A, D, and E pasted from `record.py appendix`. The orchestrator writes the first page last, above the start marker, using `record.py headline <TICKER>` for its numbers. Keep both markers exactly as shown, once each. `record.py blind --with-report` shows later valuers only what sits between them.

## Full analysis

```markdown
# <Company> (<TICKER>): <Buy | Hold | Sell>

<Opening, in this pattern: "<Company> is a <call> at $<price>. I value it at $<value>." Then the yearly return at today's price against what the stock should earn for its risk; "I would buy below $<B> and sell above $<S>"; what to do with the owner's shares, in one sentence; and the price date and time (local time zone).>

<Second paragraph: what I like about the business and the main uncertainty, two to four sentences, with the key evidence.>

## The business

<What it sells, who pays, and why they keep paying. Where the profit comes from, with the two or three numbers that show it. What protects it from rivals, and the evidence. Two or three short paragraphs.>

## What the company is betting on

<Management's own plan for the next few years, from the latest annual report, call, or investor day, with the date and source: where it is spending money, what it expects that spending to produce, and its stated targets or guidance. Then what has to go right, and what is already working or not, with evidence. Two or three short paragraphs.>

## What the price asks you to believe

<What future the price implies, in plain terms. Then what I expect and why, with the evidence inline: the company's own record, how often companies this size do it, what analysts expect for the next year or two. Where I differ from the market and why. Two or three short paragraphs.>

## How wrong I could be

<The two assumptions that move my value most, each with its dollar effect (for example, "If margins stop at 18% instead of 22%, the value is $410"). The one-point required-return sensitivity from `record.py headline`. The bad case and good case values with their chances, in one sentence each, and the permanent-loss stress case. Then one sentence that says whether this uncertainty is large enough to change the call, and why.>

## What I recommend

<The call, the buy-below and sell-above prices, and the reason, in two or three sentences. Then what the latest monthly letter suggests for the owner's shares and why (price, or size and the account's purpose and date), in one or two sentences.>

## What would change my mind

<One result that would raise the value and one that would lower it, each with a number and a date. The next earnings report and its expected date (local time zone). What changed since the last analysis, in one sentence.>

**The numbers**

| | |
|---|---|
| Call | <Buy / Hold / Sell> |
| Price (<date and time, local>) | <price> |
| My value | <value> |
| Buy below / sell above | <0.80 x value> / <1.20 x value> |
| Yearly return if you buy at this price and my forecast is right | <price-implied return> |
| Return this stock should earn for its risk | <discount rate> (10-year Treasury <rate>) |
| Bad case / good case | <bear> / <bull> |
| Confidence | <level> |

This is analysis for the owner's own decisions. It is not licensed financial advice, and it places no trades.

---

<!-- price-blind:start -->

<paste the output of `record.py appendix --lock <lock>`, part A, here>

## B. Owner cash

<The owner-cash bridge table for the base year and the last three to five years. Each large gap to reported earnings explained. Stock compensation, dilution, and buybacks, counted once. Accounting flags, or "none found".>
<One line: "About X% of the value pays for growth" (earnings power value against fair value). No full second-method section unless it changed the result.>
**Cash reliability: <grade>. Distributability: <grade>. Reinvestment return: <x%>.**

## C. Business and risks

<What it sells, who pays, why demand exists, who holds bargaining power. Two to four short paragraphs.>
<The outside view: the base-rate row from `base-rates.md`, and the table of each driver against its five-year record.>
<The two lenses that move value, one row each: mechanism, evidence, competing explanation, test, effect on value.>
<The three decisive questions with answers and evidence strength.>
<The failure chain, the stress case, and the upside pre-mortem.>
**Quality: <grade>. Management: <grade>, with two sentences. Show the seven-factor table only when an integrity problem caps the grade.**

<paste parts D and E from `record.py appendix` here: forecasts to grade, milestones, change conditions, method notes, sources>

<!-- price-blind:end -->

## F. Price audit

<The expectations table: driver, what the price implies, consensus for the next two years, the base case, the evidence for the difference.>
<Gap sources, if the gap is large: input error, method convention, business disagreement, with dollars per share. Any confidence change.>
<Market cross-checks. Gap audit if required: the strongest opposing case, the evidence that would settle it, the outcome.>
<The convergence figure, on one line: "If the price falls to my fair value within ten years: x% a year.">
<Rating and driver in one sentence. Any revision after price: what, why, and the first lock's value.>
<Accountability: grade of the prior decision, or "No prior record.">
```

The valuer's prose for parts B and C runs about 600 to 900 words. The orchestrator's first page runs 800 to 1,100 words, and part F about 300. The orchestrator builds the numbers table from `record.py headline <TICKER>` and draws the business and the company's bets from part C, the filings in part E, and the latest earnings call.

## Refresh

A refresh is short. It answers one question: does the prior analysis still stand?

```markdown
# <Company> (<TICKER>): refresh, <YYYY-MM-DD>

This is analysis for the owner's own decisions. It is not licensed financial advice, and it places no trades.

## Decision

<Written last. Start from `record.py headline <TICKER>`. Then: what changed since <prior date>, whether the prior analysis still stands, and the change in fair value, verdict, and confidence. 150 to 250 words.>

<!-- price-blind:start -->

## 1. What is new since <prior information cutoff>

<Filings, results, and events, each with its date and source. Or: "Nothing material.">

## 2. Past forecasts

<Forecast grades. Milestone updates. Each change condition: tested, tripped or not.>

## 3. Does the prior analysis still stand?

<Yes, with the escalation checks listed and passed. A "no" does not produce a refresh; the run becomes a full analysis.>

## 4. Updated value

<What changed in the model. The value bridge table. Then paste `record.py appendix --lock <lock>`.>

## Sources

<!-- price-blind:end -->

## 5. Price audit and decision

<The expectations table if the gap is large or the verdict changed. Rating and driver. Grade of the prior decision.>
```

## Fund review

```markdown
# <Fund name> (<TICKER>): fund review, <YYYY-MM-DD>

This is analysis for the owner's own decisions. It is not licensed financial advice, and it places no trades.

## Decision

<Rating, the fund's role, the action in each account, and the replacement if any.>

## What it holds
## What it costs
## How it is built
## Overlap with direct holdings
## Role, weight, and action by account
## Expected return (broad stock index funds only)
## Sources
```

A fund review has no price-blind markers. A fund has no price-blind value.
