# Base rates

The valuer reads this at step 4 of a full analysis, before forecasting. A *base rate* is how often companies like this one achieved a result in the past. It is the outside view. Start from it, then adjust once for what the evidence shows about this company.

Every number here was checked against its source in late 2026. Re-check any number before relying on it in a later year. Each table names the source, the exhibit, and the page. A number marked **unverified** was not checked; do not use it as a source. If you need a base rate that is not here, cite a dated published source and say you read it, or label it "estimate from memory, not verified."

## How to use a base rate

1. Name the reference class: for example, "companies with sales above $50 billion."
2. Read off how often the class achieved what your base case assumes.
3. Adjust once for specific evidence about this company. Write the evidence down.
4. Apply the base rate in one place only: in the forecast or in the probabilities, not both. Charging one concern twice is an error. (`record.py lock` requires `values.probability_basis.not_also_in_forecast: true` when the probabilities move.)
5. A forecast **below** the company's own five-year record needs specific evidence too, just as a forecast above the reference class does.

## 1. Sales growth by company size, ten years, after inflation

Source: Michael J. Mauboussin, Dan Callahan, and Darius Majd, *The Base Rate Book: Integrating the Past to Better Anticipate the Future*, Credit Suisse, 26 September 2016. Exhibit 4, pages 24 and 25 (full universe: Exhibit 2, page 22). Data: Credit Suisse HOLT.

Sample: the 1,000 largest companies in the world by market value, 1950 to 2015, including companies that later died. Growth is the compound yearly growth of sales, adjusted for inflation, in 2015 dollars. Size is sales at the start of the period.

These are *real* rates: they exclude inflation. Compare them with a forecast in real terms. A nominal forecast of 7% a year with 2.5% inflation is about 4.4% real.

**Middle and average real growth over ten years**

| Starting sales | Median | Mean |
|---|---|---|
| $0 to $325 million | 9.8% | 12.6% |
| $325 to $700 million | 6.7% | 7.4% |
| $700 million to $1.25 billion | 5.7% | 6.2% |
| $1.25 to $2 billion | 5.1% | 5.7% |
| $2 to $3 billion | 4.5% | 5.1% |
| $3 to $4.5 billion | 4.1% | 4.4% |
| $4.5 to $7 billion | 3.7% | 3.9% |
| $7 to $12 billion | 3.2% | 3.3% |
| $12 to $25 billion | 2.7% | 2.9% |
| above $25 billion | 1.8% | 1.7% |
| above $50 billion | 1.1% | 0.8% |
| All companies | 4.9% | 5.8% |

**Share of companies in each ten-year real growth band, largest companies** (percent of companies; Exhibit 4, page 25)

| Ten-year real growth a year | $12 to $25 billion | above $25 billion | above $50 billion | All companies |
|---|---|---|---|---|
| below -10% | 2.0 | 3.6 | 4.4 | 1.3 |
| -10% to -5% | 5.7 | 9.0 | 9.8 | 3.2 |
| -5% to 0% | 20.2 | 22.9 | 26.9 | 12.4 |
| 0% to 5% | 41.7 | 37.1 | 37.8 | 34.2 |
| 5% to 10% | 20.8 | 20.2 | 17.2 | 28.3 |
| 10% to 15% | 6.3 | 5.8 | 3.0 | 11.6 |
| 15% to 20% | 2.5 | 1.3 | 0.9 | 4.5 |
| above 20% | 0.9 | 0.2 | 0.0 | 4.5 |

The "below -10%" and "above 20%" rows add up the source's narrower bands. Rows may not sum to exactly 100 because of rounding in the source.

Reading it: of companies that started with sales above $50 billion, the median grew 1.1% a year after inflation over the next ten years, and 3.9% grew faster than 10% a year. A base case near 10% a year for a company that size sits in the top 4% of the record. That can be right, but it needs specific evidence.

The book's five-year and three-year columns sit in the same exhibit. Read them from the source when the forecast period is shorter.

## 2. How long profitability lasts

Source: the same book. Correlations measure how closely this year's level predicts a later year's level. A value of 1 means no fading at all. A value of 0 means no link.

| Measure | Sample | One year | Three years | Four years | Five years | Where |
|---|---|---|---|---|---|---|
| Operating profit margin | top 1,000 companies, 1950 to 2015 | 0.91 | 0.79 | | 0.72 | "Persistence of Operating Profit Margin," Exhibit 1, PDF page 59 |
| Cash flow return on investment (HOLT's measure of return on capital) | global companies above $250 million market value, 1983 to 2015 | 0.78 | | 0.56 | | "Persistence of CFROI," Exhibit 1, PDF page 83 |

Two more findings from the same chapters. Over ten years, the gap in operating margin between the highest and lowest fifth of companies shrinks only from 0.21 to 0.15 (PDF page 60). Margins fade slowly. Returns on capital fade faster: the gap in cash flow return on investment between the highest and lowest fifth shrinks from 18 to 9 percentage points over ten years (PDF page 84).

What this means for a forecast. A company's own margin record is strong evidence for its future margin. A base case that cuts a high margin sharply needs a named cause, the same as a base case that raises one. Returns on new investment fade toward the average faster than margins do, so the terminal return on new capital should still move toward the discount rate.

The book prints no table of how many top-fifth companies stay in the top fifth after a set number of years. Do not quote one from memory.

## 3. Not yet in this file

These base rates are useful but not yet checked against a source. Until a row is added here with a source, label any use of them "estimate from memory, not verified."

- How often a company keeps a gross margin above a set level for ten years. **Unverified.**
- Base rates for drug approval by phase, for bank loan losses by cycle, and for mining project overruns. Read them from the sector's own published sources and cite them.

To add a row: read the source, copy the number exactly, and write the source title, date, exhibit or table, and page next to it. Never add a number from memory.
