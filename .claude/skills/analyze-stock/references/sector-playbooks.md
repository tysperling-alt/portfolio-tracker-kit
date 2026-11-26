# Sector playbooks

The valuer loads only the section that fits the company. Each section says what drives value, what "owner cash" means there, which method fits, and the usual trap. All of it is price-blind. When a company spans two sectors, value the parts with their own playbooks and add them once.

## Contents

1. Software and subscriptions
2. Platforms, marketplaces, and advertising
3. Semiconductors and hardware
4. Banks and lenders
5. Insurers
6. Asset managers, exchanges, and payment networks
7. Real estate trusts and real assets
8. Cyclicals and commodities
9. Contractors and project businesses
10. Retailers and consumer brands
11. Drug and biotech companies
12. Utilities, pipelines, and regulated businesses
13. Holding companies and conglomerates
14. Unprofitable and early-stage companies
15. Bitcoin miners and other single-commodity processors

## 1. Software and subscriptions

- **Drivers**: net revenue retention (revenue this year from last year's customers), gross retention, cost to win a customer against the gross profit that customer brings over its life, and price increases that stick.
- **Owner cash**: free cash flow less stock compensation. Stock compensation is often 10% to 25% of revenue here. Ignoring it overstates value more than any other error. Also remove the lift from customers paying up front if growth is slowing: deferred revenue stops helping when billings flatten.
- **Method**: discounted owner cash. Model margins at maturity from the unit economics, not from management's target.
- **Trap**: counting "free cash flow" before stock compensation, then also assuming no dilution.

## 2. Platforms, marketplaces, and advertising

- **Drivers**: users or volume, the share of each transaction the platform keeps, and whether both sides of the market can leave. Test the counterfactual: what would sellers and advertisers do without it?
- **Owner cash**: as section 1. Separate the mature core from loss-making new ventures. Value each venture as an uncertain opportunity (valuation.md section 7), not at zero and not at management's story.
- **Method**: discounted owner cash for the core, plus opportunities valued one at a time.
- **Trap**: regulation and platform-fee disputes are events. Put them in scenarios with probabilities, not in the discount rate.

## 3. Semiconductors and hardware

- **Drivers**: unit demand through a full cycle, share, price per unit, and the capital the next generation needs. Customers build inventory in booms and burn it in busts.
- **Owner cash**: use a through-cycle margin and through-cycle capital spending. One peak year is not the base case. One trough year is not either.
- **Method**: discounted owner cash on mid-cycle figures. Tier is often `cyclical_or_levered`.
- **Trap**: extending a demand surge as if it were permanent. Test pull-forward: are customers buying ahead? Check customer concentration and what the largest customers say about their own spending.

## 4. Banks and lenders

- **Drivers**: the spread between loan yields and funding costs, credit losses through a cycle, the stability and cost of deposits, capital above the regulatory minimum, and operating costs against revenue.
- **Owner cash**: distributable earnings, which is profit less the capital that growth and regulators require. Industrial free cash flow has no meaning here. Debt is raw material, not financing.
- **Method**: equity basis always. Residual income (book value plus returns above the cost of equity) as primary or secondary. Use a through-cycle credit loss rate, not the latest year.
- **Trap**: low recent losses. Stress: deposit flight, losses at the level of the last severe downturn, and unrealized losses on securities.

## 5. Insurers

- **Drivers**: underwriting profit (premiums less claims and costs), reserve adequacy over time, investment income on the float (premiums held before claims are paid), and catastrophe exposure.
- **Owner cash**: distributable earnings after capital needs. Check reserve development for ten years: steady releases suggest prudence; steady additions suggest under-reserving.
- **Method**: equity basis. Residual income or book value plus the worth of future underwriting profit.
- **Trap**: one quiet catastrophe year. Use a multi-year average.

## 6. Asset managers, exchanges, and payment networks

- **Drivers**: assets or volume, fee rate, and how fixed the costs are. Asset managers: client flows and fee pressure. Exchanges and networks: volume, share, and regulatory limits on fees.
- **Owner cash**: free cash flow less stock compensation. Capital needs are light.
- **Method**: discounted owner cash.
- **Trap**: an asset manager's revenue moves with market levels. Model flows and fee rates. Do not extend a market rise.

## 7. Real estate trusts and real assets

- **Drivers**: occupancy, rent on renewal against expiring rent, lease length, tenant health, development pipeline, and debt maturities against asset life.
- **Owner cash**: funds from operations less recurring capital spending and leasing costs. Accounting depreciation overstates the real wear on good property and understates it on poor property.
- **Method**: net asset value from property income and a supported required yield as one method. Discounted cash flow or dividend discount as the other. Firm basis often fits because debt is large.
- **Trap**: refinancing. List maturities by year and stress the rate.

## 8. Cyclicals and commodities

- **Drivers**: where the company sits on the industry cost curve, reserve life or asset life, and the capital cycle (new supply follows high returns with a lag).
- **Owner cash**: at a mid-cycle price and margin. State the price assumed. Sustaining capital must hold production flat.
- **Method**: discounted owner cash on normalized figures, with scenarios set by price and volume. Asset value as the second method. Tier `cyclical_or_levered`.
- **Trap**: valuing peak earnings as normal. Test a 20% demand fall and the price at which the company stops covering cash costs.

## 9. Contractors and project businesses

- **Drivers**: backlog and its quality (fixed-price or cost-plus), margin in backlog against margin achieved, claims and change orders, and working-capital swings.
- **Owner cash**: watch percentage-of-completion accounting, where profit is booked on estimates. Compare cash collected with revenue booked over several years. Cash reliability is often Medium or Low.
- **Method**: discounted owner cash with margins from completed-project history. If growth comes from buying smaller contractors, judge what the acquisitions cost against what they earn.
- **Trap**: a rising backlog of underpriced fixed-price work.

## 10. Retailers and consumer brands

- **Drivers**: sales at stores open a year or more, new-store returns (cash profit in year three against cash invested), brand pricing power, and inventory turns.
- **Owner cash**: treat leases as debt-like. Maintenance spending includes store refreshes. Unit growth has a ceiling: state it.
- **Method**: discounted owner cash; firm basis if leases are large.
- **Trap**: growth from opening stores that earn poor returns.

## 11. Drug and biotech companies

- **Drivers**: each product's sales curve, patent expiry dates, and pipeline candidates with their odds of approval by phase.
- **Owner cash**: research spending is partly maintenance, since it replaces products that lose patents. Charge enough to hold the franchise.
- **Method**: value marketed products one by one to patent expiry. Value each pipeline candidate as probability × payoff less remaining cost. Sum once.
- **Trap**: a single-product company with a binary trial is usually `unresolved` or `conditional`, with a very small size.

## 12. Utilities, pipelines, and regulated businesses

- **Drivers**: the regulated asset base, allowed return against the cost of capital, the regulator's record, and capital spending plans.
- **Owner cash**: often negative free cash flow while the asset base grows. That is not poor quality if the allowed return covers the cost of capital. Dividends are funded partly by new capital: check that.
- **Method**: dividend discount or residual income on the asset base. Tier usually `defensive`.
- **Trap**: this is a long-lived, bond-like asset. A one-point change in the discount rate moves the value a lot. Report the sensitivity plainly.

## 13. Holding companies and conglomerates

- **Drivers**: the value of each part, capital allocation by the parent, parent costs, and taxes on moving cash up.
- **Method**: sum of the parts, each part valued by its own playbook with support. Subtract parent costs and parent debt once.
- **Listed stakes at market value.** A listed share the company holds as an asset is an observable fact, like cash. Value it at the fair value the company reports on its latest balance sheet (or in the investments note), less the deferred tax on the unrealized gain that the same filing reports. Do not substitute your own fundamental value for a stake the market prices daily. Take the figures from the company's own filing. Do not look up the held companies' quotes: the filing's number is enough, and a quote page breaks the source rules in `price-isolation.md`. Operating subsidiaries that are wholly owned or unlisted are still valued by their own playbooks.
- **Trap**: adding unsupported segment values, or counting cash at both the subsidiary and the parent.

## 14. Unprofitable and early-stage companies

- **Drivers**: unit economics today, the path to profit, cash on hand, and the burn rate.
- **Method**: scenarios must include failure and dilution. Model the shares the company will issue to fund losses. If no evidence supports a path to owner cash, the valuation is `unresolved`. Tier `speculative`.
- **Trap**: valuing the market size instead of the company's economics.

## 15. Bitcoin miners and other single-commodity processors

- **Drivers**: cost to produce one unit against the commodity price, power contracts, equipment age and replacement cycle, and share issuance.
- **Owner cash**: equipment wears out fast. Depreciation is a real cost. Share issuance to fund growth is dilution: track owner cash per share, not in total.
- **Method**: scenarios set by the commodity price and by the company's cost position. A newer line of business (for example leasing computing capacity) is an uncertain opportunity under valuation.md section 7.
- **Trap**: this is mostly a bet on the commodity. If the value depends on a commodity price you cannot forecast, say so and mark it `conditional` on a stated price.
