# Funds

Use this path when the ticker is a fund: an index fund, an exchange-traded fund (ETF), a mutual fund, a bond fund, a target-date fund, or a trust that holds a commodity or a cryptocurrency.

A fund is a basket priced at the market value of what it holds. It has no value separate from price, so there is no price-blind lock, no fair value, and no bands. The orchestrator runs this path itself, without a valuer. A fund is judged on four things: what it holds, what it costs, how it is built, and what job it does in the owner's portfolio.

The tracker shows a fund as "no bands." That is correct.

## Steps

1. **What it holds.** From the fund's own fact sheet and holdings page: the index or strategy, number of holdings, weight of the top ten, sector and country mix, and for bond funds the yield, the duration (how much the price falls when rates rise one point), and credit quality.
2. **What it costs.** Expense ratio. For index funds, how far returns trail the index. Turnover. Compare with the cheapest fund that does the same job.
3. **How it is built.** Flag these structures in plain words:
   - Leveraged or inverse funds reset daily. Over months they drift from the stated multiple and usually lose value. They do not suit a long-term holding.
   - Exchange-traded notes are debt of the issuing bank, not a basket of assets.
   - Funds that sell options for income cap the upside and keep most of the downside.
   - Single-stock funds add cost and structure risk to one company.
   - Commodity and cryptocurrency trusts hold an asset with no cash flows. There is nothing to value. The position is a view on the asset's price, limited by a size cap.
4. **Overlap.** Read `data/holdings.json`. How much of the fund is in companies the owner also holds directly? State the combined exposure to their largest names and, if the financial picture names one, to their employer's sector.
5. **Role and action.** Read `context/financial-picture.md`. Is this fund a core diversified holding, a reserve (cash-like or short bonds), or a concentrated bet? Does each account's use of it fit that account's purpose and date?
6. **Expected return, broad stock index funds only.** Give a building-block estimate: dividend yield, plus net buyback yield, plus long-run growth in earnings per share. Then state the range if valuations rise or fall over ten years. Label it an estimate. This number is the diversified alternative that every single-stock decision is compared with.

## Rating

Use the same labels, with this meaning:

| Label | Meaning for a fund |
|---|---|
| Buy/Accumulate | Add on the normal plan. It fits its role and is cheap for what it does. |
| Hold/Watchlist | Keep at the current weight. |
| Trim | Weight is above its role, or overlap creates concentration. |
| Sell | A cheaper or better-built fund does the same job, or the structure does not suit a long-term holder. Name the replacement. |

The driver is almost always `portfolio fit`. `no_buy_reason` for a Hold is `below required return` when the fund is simply at its target weight.

## Record

Fill `references/lock-draft.template.json` with:

- `asset_type`: `fund`
- `mode`: always `full`. A fund review is short, so the monthly run repeats it in full.
- `lock.valuation_status`: `not_applicable`
- `price_isolation`: `{"status": "not_applicable", "structure": "not_applicable", "exposures": []}`
- `fund`: an object with what you found, for example `index`, `expense_ratio`, `holdings_count`, `top_ten_weight`, `structure`, `structure_flags`, `overlap_note`, `role`, and for broad stock funds `expected_return_estimate` with its low and high.
- Leave out `values`, `rates`, `grades`, `thesis`, `forecasts`, `milestones`, and `change_conditions`.
- `accountability.prior_record_date`: the prior record's date, or null.

Then run `record.py lock` without `--model-result`, and finish with the audit file and `record.py append` as for a stock. Set `orchestrator_knew_price_before_lock` to whatever is true; it has no bearing on a fund. `suggested_size_range` is the fund's target weight range from its role.

## Report

Use the fund review layout in `document-layouts.md`. One page is enough.
