# Business, financials, management, and failure

The valuer loads this for steps 2 to 6 of a full analysis. Everything here is price-blind.

Label every statement in the report as one of four kinds. A **fact** comes from a dated primary source. A **company claim** is what management says and you have not verified. An **estimate** is your number. A **judgment** is your conclusion. Seek evidence against your own view at every step. Never invent a source, an input, or a calculation. If you could not find a fact, say so and list it as an evidence gap.

## 1. Three decisive questions

Set these before deep research. A decisive question is one whose answer would move the value by 15% or more, or break the thesis.

- Write each as a question that evidence can answer. "Can it hold price increases above inflation without losing customers?" works. "Is it a good company?" does not.
- At the end, answer each one and grade the evidence: `strong` (several independent primary sources agree), `moderate` (one good source or indirect support), `weak` (mostly company claims or your inference).
- The questions drive the research plan, the scenarios, and the change conditions. A weak answer lowers confidence. It does not lower the base case.

## 2. What the business is

Explain in plain words: what it sells, who pays, what the customer would do without it, why demand exists, how long customers stay, who holds bargaining power (customers, suppliers, the company), how much of the value it creates it keeps as profit, and how much cash that leaves per share.

## 3. The outside view first

Before you forecast, name the reference class and its record. Example: "large companies growing sales above 15% a year for ten years." State how often companies in that class achieved what your base case assumes. Take the number from `base-rates.md` and cite its row. If the rate you need is not there, cite a dated published source you read. If you rely on memory, label it "estimate from memory, not verified." Then adjust for what the evidence shows about this company.

The evidence rule works in both directions:

- A base case far **above** the reference-class record needs specific evidence, not optimism.
- A base case **below** the company's own five-year record needs specific evidence too. Name the cause: a lost customer, a price cut, a cost that will rise. "The reference class grows more slowly" is not enough by itself when the company has beaten the class for years.
- Apply the base rate once: in the forecast or in the probabilities, not both.

Write a short table: each main driver (growth, margin, return on new investment), its five-year record, the reference-class rate, and the base case. Count how many base-case drivers sit below the company's own record. The orchestrator checks that count at step 3.

## 4. Three to five lenses

Pick the lenses that fit. Do not use all of them by habit.

| Lens | Question it answers |
|---|---|
| Customer counterfactual | What does the customer lose or pay if the product disappears? How much of that value does the company capture? |
| Moat and competitive response | What stops a well-funded rival? How will rivals and new entrants respond to this company's profits? |
| Incentives | What are managers, sales staff, customers, and regulators paid to do? |
| Incremental returns | What does each new dollar invested earn? Compare with the average return. |
| Base rates and inversion | How do businesses like this usually fare? What would have to be true for this to fail? |
| Capital cycle | Is money flooding into this industry or leaving it? Supply follows returns with a lag. |
| Duration mismatch | Does the company fund long assets with short money, or promise long-term value on short-term demand? |

For each lens, fill one row:

| Lens | Mechanism | Evidence | Competing explanation | Test that would settle it | Effect on value |
|---|---|---|---|---|---|

Then test second-order effects (what happens after the first effect) and name one or two comparable companies that failed and why.

## 5. Growth

Split past and forecast growth into volume, price, mix, market growth, share gain, and acquisitions. Then:

- Tie growth to the investment that produces it and to the return on that investment. Growth that earns less than the discount rate destroys value.
- State the runway: how long the company can keep investing at high returns.
- Test for pull-forward (demand borrowed from future years) and deferred spending (costs pushed out to flatter today's margins).
- Market size is not customer economics. A large market says nothing about what one customer is worth.

## 6. Quality grade

Grade the business as the evidence shows it, not as management describes it. Check pricing power, switching costs, scale advantages, barriers to entry, customer and supplier concentration, cyclicality, regulation, and how long the advantage should last.

| Grade | Standard |
|---|---|
| Exceptional | Returns on capital far above the cost of capital for ten years or more, through a downturn. Price increases stick. Customers have no good substitute or face high switching costs. Long runway to reinvest at high returns. No single point of dependence. |
| High | A clear advantage and returns above the cost of capital through a cycle. One or two real weaknesses, such as some cyclicality or a limited runway. |
| Good | A sound business with returns modestly above the cost of capital. The advantage is real but narrow, or could erode within ten years. |
| Mixed | Strong parts and weak parts. Returns near the cost of capital. The advantage is unproven or eroding. |
| Weak | Sells something close to a commodity. Returns below the cost of capital over a cycle. Needs good conditions, debt, or outside money. |
| Poor | In structural decline, or loses money in normal conditions and depends on new capital. |

Quality goes into the forecast: a better business gets a longer runway and higher returns in the cash flows. Do not also adjust the discount rate or the bands for quality.

## 7. Financial review

Cover three to five fiscal years plus the interim periods since: sales, margins, earnings, operating cash flow, capital spending, working capital, buybacks and dividends, debt and its maturities, leases, share count, and acquisitions.

Run the calculations in Python and save the script next to the model file. Do not do multi-step arithmetic in your head.

## 8. Owner cash reconciliation

Owner cash is the cash the business could pay to its owners each year and still hold its competitive position. Build this bridge for each of the last three to five years and for the forecast base year.

| Line | Note |
|---|---|
| Operating cash flow | from the cash flow statement |
| less stock compensation | It was added back. It is a real cost. Subtract it. |
| less working-capital timing | Remove gains that will reverse. Use a multi-year average. |
| less recurring "one-time" items | A charge that appears most years is a cost. |
| adjust cash taxes | Use the rate the company will pay over time. |
| less lease principal payments | if not already in operating cash flow |
| less maintenance investment | Capital spending, capitalized software, and small acquisitions needed to hold the competitive position. Not only to keep the assets running. |
| **= owner cash before growth investment** | |
| less growth investment | Charge it. Then credit the returns it earns at the company's demonstrated return on new investment, faded toward the reference class. State both numbers. |
| **= distributable cash** | divide by diluted shares for the per-share figure |

Rules:

- Count stock compensation once. This skill's method: subtract the expense from cash flow, and use today's diluted share count. Do not also grow the share count for future awards. A buyback that only offsets new awards returns nothing to owners.
- Do not shrink the future share count for buybacks. The cash that pays for them is already in the cash flows.
- Reconcile to reported earnings. Explain each large gap between earnings and owner cash.
- Low free cash flow alone does not mean poor quality. A company that invests heavily at high returns has low free cash flow and high value.

Grade three things separately:

| Measure | High | Medium | Low |
|---|---|---|---|
| **Cash reliability**: do reported profits turn into cash? | Operating cash flow is 90% or more of earnings over five years. Few adjustments. Revenue recurs or is under contract. | 70% to 90%, or large swings, or meaningful adjustments. | Under 70%. Large recurring adjustments. Profits rest on estimates such as reserves, marks, or percentage-of-completion. |
| **Distributability**: can the cash reach owners? | Cash sits at the parent, free of restrictions. Debt is low. | Part is trapped abroad, held for regulators, or needed for debt service. | Most is restricted, pledged, or needed to survive. |
| **Reinvestment returns** | State the number: change in after-tax operating profit divided by change in invested capital, over three to five years. | | |

## 9. Accounting checks

Flag any of these and say what it does to cash reliability:

- Receivables or inventory growing faster than sales.
- Revenue recognized before cash, or changes in recognition policy.
- Costs capitalized that peers expense.
- Acquisitions that hide weak organic growth.
- Adjusted profit far above reported profit, year after year.
- Reserve releases, gains on sales, or tax items carrying earnings.
- Obligations outside the balance sheet: purchase commitments, guarantees, pensions.
- Auditor change, restatement, material weakness, late filings, related-party dealings.

If you cannot trust the accounts, the valuation is `unresolved`.

## 10. Management grade

Score seven factors from 0 to 2 each. Use share counts and ownership percentages from the proxy statement. Skip dollar values of holdings and insider trade prices; those are price information.

| Factor | 2 | 1 | 0 |
|---|---|---|---|
| Ownership | Leaders hold large stakes bought or held over years | Modest stakes | Trivial stakes, or steady selling of granted shares |
| Incentives | Pay tied to per-share value and returns on capital over three years or more | Mixed | Pay tied to size, adjusted profit, or short-term targets |
| Candor | Reports bad news plainly; consistent metrics | Some spin | Changes metrics, hides problems, blames others |
| Execution | Meets its own operating targets most years | Uneven | Misses often |
| Governance | Independent board, one share class or fair treatment, clean related-party record | Some concerns | Controlled or conflicted without protection for outside owners |
| Capital allocation | Acquisitions and buybacks earned good returns | Mixed record | Overpaid, bought back high, diluted owners |
| Per-share results | Owner cash and book value per share grew well over five to ten years | Grew slowly | Flat or down |

Total 12 to 14 is A. 9 to 11 is B. 6 to 8 is C. 3 to 5 is D. 0 to 2 is F. An integrity failure (restatement for misconduct, self-dealing, misleading investors) caps the grade at D.

Make two tables: promises against outcomes for the last three to five years, and each large acquisition's cost against what it earns now. Operating excellence is not shareholder alignment. Grade them apart.

## 11. Failure analysis

Build the bear case as a chain of causes, not a discount. Answer:

- **Permanent loss.** What sequence of events destroys value for good? How likely is it?
- **Warnings.** What would you see first? These become change conditions.
- **Funding.** List debt maturities by year, covenants, and available liquidity. Could the company refinance in a bad market?
- **Survival.** How many quarters of cash does it have if revenue falls and credit closes?

Then build the stress case. It is a severe but plausible outcome, about one in twenty. Use the shocks that fit: a 20% fall in demand, margin compression, higher interest rates on refinancing, a working-capital squeeze, a lower terminal value. For a cyclical business, first restate earnings at the middle of the cycle, then apply the stress.

The stress case feeds position size. It is not part of the probability weighting.

Then run an upside pre-mortem, the mirror of the failure chain. Assume the business is worth twice the base case in ten years. What happened? Name the two or three causes and say whether today's evidence shows any of them starting. If one is already under way, the bull case should carry it, and the base case may need it too.

## Sector playbook

Before modeling, load the matching section of `sector-playbooks.md`. The owner-cash bridge above fits most operating companies. Banks, insurers, real estate trusts, and resource companies need their own measures.
