# Financial picture (FICTIONAL example)

Every fact below is made up. Claude writes your real file to `context/financial-picture.md` from a few short questions on first run. That folder is git-ignored, so it stays on your computer.

The portfolio-review and analyze-stock skills read this file for goals, dates, reserves, and risk. Keep it short. Update it when your life changes, and at least once a year.

## 1. As-of date and sources

- As of: 2026-01-02.
- Sources: the owner's answers in chat; brokerage screenshots for account values.

## 2. Goals and horizon

- Retirement in about 25 years. The retirement IRA is for this.
- A large purchase in about 5 years, possibly paid partly from the brokerage account. Amount not yet decided.

## 3. Net worth composition

- Investment accounts: see `data/holdings.json` (values change with prices; do not copy them here).
- Home equity: none.
- Debts: none besides a car loan with 2 years left.

## 4. Reserves to exclude from investable capital

- Emergency fund: 6 months of expenses, held in a savings account outside the tracker. Not long-term money.

## 5. Income and employment risk

- Salaried job in the software industry. Tech stocks and tech jobs tend to fall in the same downturns, so count tech holdings as shared risk.
- No employer stock or options.

## 6. Account types and tax notes

- Retirement IRA: traditional (tax-deferred). Trades inside it have no tax.
- Brokerage: taxable. Federal long-term capital gains rate 15%; state rate 5%.

## 7. Risk tolerance and behavior

- Has held through a 30% fall before without selling.
- A 35% fall in the goal money would delay the purchase. Could wait about one more year.

## 8. Cash flow

- Adds about $500 a month to the brokerage account.

## 9. Gaps (questions for the owner)

- How much of the brokerage account is goal money?
- Target allocation for the retirement IRA (not yet set).

## 10. Implications for the tracker

- Treat the retirement IRA as long-term money.
- Treat up to half of the brokerage account as near-term money in the account-fit check until the owner narrows it.
- Single-company limit: 10% of long-term investments (from `data/investor-profile.json`).
