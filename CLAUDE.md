# Portfolio tracker kit: instructions for Claude

This repo builds a personal stock-portfolio tracker for whoever cloned it (the owner). The tracker is a private claude.ai Artifact: a dashboard page (`page/index.html`) that reads six data files built from the owner's holdings. Prices come free from Yahoo Finance. Three skills do the work:

- `portfolio-sync`: reads brokerage screenshots into `data/holdings.json` and logs trades.
- `analyze-stock`: values one stock without looking at its price first, and writes `analyses/<TICKER>/` and `data/valuations/<TICKER>.json`.
- `portfolio-review`: the monthly review, and an advisor-style meeting letter in `reviews/`.

Rules that always apply:

- This is analysis for the owner's own decisions. It is not licensed financial advice. Never place, schedule, or send a trade. Never log in to a brokerage.
- The owner's financial data stays on their computer. Never put it in a URL, a web request, or a commit (the `.gitignore` already excludes it). Never record account numbers.
- Write to the owner in plain, short sentences. Define any finance term the first time you use it.
- State dates and times in the owner's local time zone.

## First message

When someone opens this repo for the first time, or gives you its link, your first reply introduces the kit and lets them decide before they share anything. Send it before you read any of their files or ask for data. Do it whenever `data/holdings.json` does not exist yet.

1. **Show what it looks like.** Send the four preview images in `docs/` (use your tool for sending files to the user if you have one; otherwise tell them the images are in the repo's README on GitHub, where they show inline). Say clearly that every company and number in them is made up.
2. **Send this message**, in your own voice, kept close to this:

   > This kit builds you a private dashboard of your investments, as a page in your own claude.ai account. Here's what it looks like, filled with made-up companies so you can judge it first.
   >
   > **What you get:** your total and accounts at a glance; a photo tile for each stock, sized by how much you own, with a Buy, Hold, or Sell call and how far its price is above or below a value I work out; your returns against the S&P 500 over 1 month to 10 years; and a short monthly letter on what, if anything, to change.
   >
   > **How it works:**
   > 1. You send a screenshot of each account's holdings.
   > 2. I read it, ask a few plain questions about what each account is for, and build your page. About 10 to 15 minutes.
   > 3. Prices update when you ask (or weekly, if you want). I can also value your larger stocks one at a time.
   >
   > **Privacy:** your numbers stay on your computer and in your private claude.ai page. They are never added to this repo. Crop out account numbers before you send anything. This is analysis to help you think, not licensed financial advice, and I never place trades.
   >
   > Want to click around a live sample first? I can publish the made-up version to your claude.ai in a couple of minutes.
   >
   > If you'd like to go ahead, send a screenshot of your investment allocation: the positions page of each account, showing each holding's shares or value. The cost basis column helps but is optional.

3. **Then wait.** If they ask for the live sample, follow "Live sample" below. If they send screenshots, go to "First run". If they decline, stop; do not ask again in that conversation.

## Live sample

Publishes the dashboard filled with the fictional data in `examples/demo/`, so the person can try it before sharing anything. It uses the same steps as "4. Create the artifact" under "First run", with these differences:

- Title the artifact "Portfolio Tracker Sample".
- Upload the six files in `examples/demo/` instead of `build/`, plus `page/photos/HERO.jpg` and `page/photos/SKYLINE.jpg`.
- In the page you store as `files/index.html`, set `OWNER_TITLE` to `'Sample portfolio'`, `HERO` to the bull photo's `/_blob/` address, and `FUND_PHOTO` to the skyline's. Leave `PHOTOS` empty; the sample companies show as dark tiles. Do not change `page/index.html` on disk.
- Mark every dataset `fixed: true` and say "Sample data, fictional" in its `updated.by`.

Tell them it is a sample with made-up companies, and that their real page will be a separate one. Then repeat the screenshot request from "First message".

## First run

Start here when `data/holdings.json` does not exist and the person has sent screenshots (see "First message" first). Tell the owner in one line what you are about to do, then work through the steps. Ask questions in small batches, in plain words.

### 1. Holdings from screenshots

1. If the owner has not shared screenshots yet, ask for screenshots of each brokerage account's positions page, with the cost basis column showing. One screenshot per account is fine; scroll and take more if the list is long. Tell them to crop out account numbers.
2. Follow the `portfolio-sync` skill, Mode 0. It writes `data/holdings.json` and asks, for each account, what the money is for and when it will be needed. That answer goes in each account's `purpose` field, and the page shows it.
3. Run `python3 scripts/validate.py` and paste the output. Fix any error before going on.

### 2. Financial picture and investor profile

Ask these questions, in two or three short messages. Skip any the owner does not want to answer; note it as a gap.

- What is each account for, and when will you need the money? (Already asked in step 1; confirm.)
- Do you have an emergency fund outside these accounts? About how many months of expenses?
- Is any of this money for something in the next five years (a home, school, a car, a wedding)? Roughly how much, and when? If stocks fell 35% right before then, could you wait a year?
- What do you do for work, and in what industry? Do you hold stock or options in your employer or another private company?
- Have you lived through a big market fall while invested? What did you do?
- Any rules you want me to follow, such as "no single stock over 10%" or "never sell in my IRA"?
- Roughly what tax rate do you pay on long-term capital gains (federal and state)? "Not sure" is fine.

Then write:

- `context/financial-picture.md`, in the shape of `examples/financial-picture.example.md`. Use the owner's answers only; do not copy the example's facts.
- `data/investor-profile.json`, in the shape of `examples/investor-profile.example.json`: one rule per stated rule, with today's date, the account it applies to (or null), the rule, the owner's own words in `owner_words`, and what it means for the review. Put unanswered questions in `open_questions`.

If the owner has private-company equity, add it to `private_holdings` in `data/holdings.json` (shape in the `portfolio-sync` skill). Otherwise leave that list empty, and the page hides the private section.

### 3. Prices and build

```
python3 scripts/refresh_prices.py
python3 scripts/build_tracker.py
```

The first pulls ten years of daily prices for every holding, the watchlist (`data/watchlist.json`), and SPY (the S&P 500 benchmark) into `data/prices.json`. If a ticker fails, check its symbol on the broker's screenshot; add a mapping to `YAHOO_SYMBOL` in `scripts/refresh_prices.py` only when Yahoo uses a different symbol. The second writes six files to `build/`.

### 4. Create the artifact

1. Call the Artifact tool with `action: "quickstart"` and `intent: "other"`, describing a dashboard that reads six JSON data files. If the result names a Dashboard or Data artifact type, start from it (publish with its `type_url` and a `title` such as "Portfolio tracker") and follow the instructions that come back with it. They are the source of truth for how this type stores its page and its datasets. The steps below describe how the page in this repo expects to be wired, and match the Data type at the time of writing.
2. Upload the six build files to the artifact's asset store: Artifact tool, `url` = the new artifact, `asset: true`, `file_paths` = the six `build/*.json` files (or one call each). Each result gives a `/_blob/<id>` address. Keep the list.
3. With the ArtifactData tool, create one document per dataset in the collection `datasets`, with the dataset id as `doc_id`. Use a single `batch` write. Each document has this shape:

   ```json
   {
     "title": "Holdings at latest close",
     "description": "Every position in every account, priced at the latest market close.",
     "schedule": "Prices refreshed weekly and on request; holdings updated after each reported trade.",
     "source": {"format": "json", "kind": "file", "name": "positions.json", "url": "/_blob/<id from step 2>"},
     "staleAfterHours": 336,
     "updated": {"at": "<UTC ISO time>", "by": "Claude, from brokerage screenshots and Yahoo Finance prices"}
   }
   ```

   | `doc_id` | File | Title | `staleAfterHours` |
   |---|---|---|---|
   | `positions` | `positions.json` | Holdings at latest close | 336 |
   | `valuations` | `valuations.json` | My values and calls | 336 |
   | `performance` | `performance.json` | Returns against the S&P 500 | 336 |
   | `private` | `private.json` | Private company equity | 2160 |
   | `analyses` | `analyses.json` | Latest analysis reports | 1440 |
   | `meetings` | `meetings.json` | Monthly meeting letters | 1440 |

   Write a one-sentence `description` and `schedule` for each that describe the owner's setup, with no personal figures.
4. Set the page: wrap the text of `page/index.html` as `{"text": "<the whole file>"}` in a local JSON file, and `set` the document `index.html` in the collection `files` (pass `if_version` if the type already created it; read it first to get the version).
5. Optional: change `OWNER_TITLE` near the top of the page's script to a name the owner likes (ask once; "My portfolio" is the default).

### 5. Photos

The page shows a photo on each company tile, a hero photo, and a fallback photo on a fund's page. A tile with no photo is a plain dark tile, so photos are optional.

1. Upload the files in `page/photos/` to the artifact's asset store: Artifact tool, `url`, `asset: true`, `file_paths` = the photos. Each result gives a `/_blob/<id>` address.
2. In `page/index.html`, fill the addresses in: `HERO` gets `HERO.jpg`, `FUND_PHOTO` gets `SKYLINE.jpg`, and each `PHOTOS` entry gets the photo named for its ticker (a class-share dot becomes a dash in the file name: a ticker `ABC.B` uses `ABC-B.jpg`). Remove `PHOTOS` entries for tickers the owner does not hold, or leave them; they do no harm.
3. Publish the page again (step 4.4).

To make photos for more holdings: use any image tool the owner has. For speed, ask for one 2x2 sheet of four company scenes at a time (for example "four photographic scenes, one per quadrant: a warehouse for <company 1>, ..."), then crop it into four files. Use generic scenes, never a company's logo or trademark. Save each as `page/photos/<TICKER>.jpg`, about 1200 px wide and under 300 KB, then upload and add it to `PHOTOS`.

### 6. Verify

1. Open the artifact (Artifact tool, `action: "open"`) and check that the page loads: the total in the hero, one button per account, the company tiles, the returns card, and the Details tables.
2. Read `data/users/me/check` and `data/users/me/runs` with ArtifactData, if the type keeps them, and fix any page error they report.
3. Tell the owner the link, in one or two sentences.

### 7. Offer the next steps

Offer, in one short message:

- To run `analyze-stock` on their largest individual stocks, largest first. Each full analysis uses several subagents and takes a while, so suggest starting with the top three.
- To run `portfolio-review` once a few stocks have values, which writes the first monthly meeting letter.
- The optional schedules below.

## Republish data

After any rebuild (`scripts/build_tracker.py`):

1. Upload each changed build file: Artifact tool, `url` = the tracker, `asset: true`, `file_path` = the file. Note the new `/_blob/<id>`.
2. With ArtifactData, read `datasets/<id>` to get its `version`, then `update` it with `if_version` and `{"source": {"url": "/_blob/<new id>"}, "updated": {"at": "<UTC ISO time>", "by": "<who ran it and from what>"}}`. Keep the other `source` fields.
3. Delete the old asset (Artifact tool, `action: "delete"`, `url`, `path` = the old 32-character id) once nothing points at it.
4. Read `data/users/me/check` and `data/users/me/runs` for page errors.

To change the page: edit `page/index.html`, wrap it as `{"text": ...}`, and `set` `files/index.html` with the current `if_version`.

Page rule: an element with `data-draw` must not sit inside another element with `data-draw`, or the inner drawing never runs. Check `node --check` on the script after any page edit.

The tracker's URL is personal. Store it in `context/tracker.md` (git-ignored), not in this file.

## Refresh prices on request

When the owner says "refresh prices" (or similar): run `scripts/refresh_prices.py` and `scripts/build_tracker.py`, republish `positions`, `valuations`, and `performance`, and report any holding whose call changed or that is flagged `needs_review`. Do not commit.

## Optional schedules

Offer these after first run. Create them only when the owner agrees. In the Claude desktop app, local scheduled tasks run only while the app is open; a missed run starts on the next launch.

- **Weekly prices**: once a week after the US market closes (for example Friday afternoon, local time). It runs the "Refresh prices on request" steps and flags any holding that needs an early review.
- **Monthly review**: once a month on a fixed day. It runs the `portfolio-review` skill and writes the meeting letter. A full re-analysis of each stock happens once a year inside it; after an earnings report or a call-price crossing, it runs a short refresh instead.

## Files

| Path | What it is | In git? |
|---|---|---|
| `page/index.html` | The tracker page | yes |
| `page/photos/` | Source photos for the page | yes |
| `scripts/refresh_prices.py` | Pulls prices from Yahoo Finance into `data/prices.json` | yes |
| `scripts/build_tracker.py` | Builds the six page data files into `build/` | yes |
| `scripts/validate.py` | Checks holdings, trades, and valuation files | yes |
| `examples/` | Fictional samples that show each personal file's shape | yes |
| `data/watchlist.json` | Tickers to price but not owned | yes (template) |
| `data/holdings.json`, `data/trades.jsonl`, `data/prices.json`, `data/investor-profile.json`, `data/targets.json`, `data/valuations/` | The owner's data | no |
| `context/` | Financial picture, settings overrides, tracker URL | no |
| `analyses/`, `reviews/` | Analysis reports and meeting letters | no |
| `build/` | Generated page data | no |

Before any commit, run `python3 scripts/validate.py` and confirm `git status` shows no personal file.
