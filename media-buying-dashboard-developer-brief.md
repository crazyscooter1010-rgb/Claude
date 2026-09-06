# Media Buying Dashboard — Developer Brief

**Goal:** Give the media buyer (David) a way to glance at every ad account in the morning and instantly see which accounts are outside KPI — without exporting spreadsheets into an AI tool once a week. Catch problems same-day, not 5 days later.

**The core bottleneck we're fixing:** Right now analysis happens ~once/week (export sheet → paste into Claude with a prompt → read reply → go fix the ad account). It takes ~1.5 days. If something breaks Friday and we don't look until Wednesday, we burn 4–5 days of budget (at $300/day that's $1,200–$1,500 wasted per account per incident). We need at-a-glance, near-real-time KPI monitoring.

---

## 1. What we have today (so you don't rebuild it)

The current system is a Google Sheet **per ad account** (mine + one per client), each with a bound Apps Script that:
- Pulls **Meta Ads** daily, per-ad rows → `Meta Raw` (impressions, clicks, link clicks, CTR all/link, CPC, CPM, spend, campaign/adset/ad IDs + names, created time)
- Pulls **GHL leads** → `GHL Raw` (lead ID, contact name, lead color = green/yellow/red quality, date added, UTM campaign/ad/content)
- Cross-references Meta ↔ GHL by **UTM Ad ID**
- Produces derived tabs: `Campaign Analytics (Lifetime)`, `7 Day Stats` (+ prior 7), `30 Day Stats` (+ prior 30), `Account Overview` (lead/green summary), `Change Log` (manual optimization journal)
- Refreshes via a manual **"Refresh Analytics"** button

**The ingestion pipeline (Meta API + GHL API + UTM cross-referencing) is good and we want to keep it.** The problems are the data model, the missing metrics, the lack of a unified view, and the manual/weekly cadence — not the data collection itself.

---

## 2. Problems to solve (all confirmed against the current sheets)

1. **No booked-call / appointment / show data at all.** `GHL Raw` only pulls *leads*. It never fetches GHL calendar appointments or opportunity stages, so **cost per booked call and cost per show cannot be calculated today.** This is the #1 gap.
2. **No ad-set-level rollup.** Everything is per *ad creative*. Now that we run multiple ads per ad set, we need metrics aggregated at the **ad-set level** (Ad Set ID already exists in `Meta Raw`, so it's a group-by — just not built).
3. **No "last 3 days (including today)" window.** We only have 7d/30d + prior periods. Media-buying decisions are made off the last ~72 hours; this window's absence is *why* problems get caught late.
4. **No KPI baseline/target, and no at-a-glance status.** "Green lead %" is *lead quality* coloring — it is NOT a cost-efficiency flag. There's no per-account target CPL / target cost-per-booked-call, and nothing turns yellow/red when we breach it. We cannot glance and see "who's out of KPI."
5. **No unified cross-account view.** One spreadsheet per account = no 30,000-ft scroll across all clients + my account in one place.
6. **Not timely / no alerting.** Manual button, run weekly. Need scheduled refresh (daily or 2–3×/day) + an alert when an account breaches KPI.
7. **Raw-spreadsheet UX + scaling ceiling.** Dense and hard to read. The `7 Day Stats` tab is already ~62,000 rows (it appends a weekly snapshot per ad every refresh) — it will keep bloating and eventually break, which is exactly why we don't want to keep piling everything into Sheets long-term.
8. **Security:** Meta access tokens + GHL bearer/PIT tokens are stored in plaintext in the `Config` tab of shareable spreadsheets. Move these to Script Properties / a secrets store; never in a shared sheet.
9. **No top-of-funnel vs. bottom-of-funnel visibility on client accounts.** Client leads are now tagged in GHL as Top of Funnel or Bottom of Funnel, but `GHL Raw` only pulls Lead ID/Contact Name/Ad Campaign/Ad Creative/Lead Color/Date Added/UTMs — no tag field. So today we can't see the TOF/BOF mix or how lead quality breaks down by funnel stage. Client-only; not applicable to Logan's B2B account.

---

## 3. Metrics the dashboard must show

Per **ad set** (and roll up to account + agency-wide), for each time window:

**Spend & delivery**
- Ad spend
- Link CTR (link click-through rate)
- Cost per link click (CPC link)
- CPM (secondary)

**Funnel & cost efficiency**
- Leads + CPL (cost per lead)
- Green leads + Green % + Cost per green lead (keep our lead-quality scoring)
- **Booked calls + Cost per booked call** ← new, my B2B account especially
- **Shows + Cost per show** ← new
- (Clients don't have booked calls yet — build the columns but they can be blank/N/A per account. My account is B2B and needs booked-call metrics at the ad-set level.)

**Time windows (toggle-able):** Last 3 days (incl. today), Last 7, Last 14, Last 30, Previous 30 (for comparison).

**Status logic (the "glance" feature):** Each account/ad set carries a per-account KPI target (baseline CPL, target cost-per-booked-call, etc.). Cell/tile turns **green within target, yellow approaching, red over target**. Baseline is set per account per offer and can be reset when the offer changes or for seasonality.

**Client-side only: Funnel Stage Mix.** Client leads are tagged in GHL as Top of Funnel (TOF) or Bottom of Funnel (BOF). Per ad set, per time window:
- **TOF %** and **BOF %** — the split of leads by funnel stage
- **Green / Yellow / Red lead counts** (raw counts, not just green — we already capture Lead Color in `GHL Raw`, just not broken out by all three colors today)
- **Green Lead %**
- **BOF % is the metric we're optimizing for** — flag it distinctly (bold, starred, or its own mini-indicator) since it's the one David/the client team should watch trend upward, not just a pass/fail KPI threshold like the cost metrics above.

Not applicable to Logan's own B2B account — client-only, same blank/N/A pattern as booked calls being blank for clients.

---

## 4. The actual glanceable view — "Ad Set Overview"

This is the specific screen David opens every morning. **One row per ad set** (not per ad, not per account), for whichever time window is selected:

| Client | Ad Set Name | Status | Days Running | Spend | Link CTR | CPC (Link) | Leads | CPL | Booked Calls | Cost/Booked Call | Shows | Cost/Show | TOF % | BOF % | Green/Yellow/Red | Green % | KPI Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

Note: Booked Calls / Cost/Booked Call / Shows / Cost/Show are B2B-only (Logan's account); TOF % / BOF % / Green-Yellow-Red / Green % are client-only. Neither set applies to both — expect real blanks either direction depending on account type. If this makes the table too wide to actually glance at, the developer's call whether Funnel Stage Mix ships as extra columns here or as a secondary panel/tab per ad set — the data and grouping are the same either way.

- **Time window is a single toggle at the top** (3d incl. today / 7d / 14d / 30d / prior 30d) that re-renders every row — not five separate tabs to flip between.
- **Rollup rows above the ad-set rows:** an agency-wide total row, then one subtotal row per client/account — so David scrolls agency → account → ad set without leaving the page.
- **KPI Status column** is the whole point: colored green/yellow/red per row based on that ad set's worst-breaching metric against its account's KPI targets (baseline CPL, target cost/booked call, target cost/show from section 3). Sort or filter by this column to jump straight to what's broken — that's the "quick glance, who's outside KPI" you asked for.
- **Visually distinct from the existing lead-quality colors.** `GHL Raw` already colors leads green/yellow/red for *lead quality* — a different meaning. Don't reuse plain cell-background green/yellow/red for KPI Status too, or David will misread one for the other at a glance. Use a distinct treatment (icon/badge, or a clearly separate "KPI Status" column with its own legend) so the two systems never visually collide.
- **Drill-down:** clicking/expanding a flagged ad set row should jump to that ad set's underlying ad-level detail (the existing `Campaign Analytics` / `7 Day Stats` / `30 Day Stats` data) — so the next step after "this is red" is "here's why," not a manual lookup back in the raw tabs.

**Where this lives:** in Phase 1, this is literally a dedicated tab — call it `Ad Set Overview` — in the consolidated data store, and it becomes the **default landing page** in the Looker Studio dashboard (section 6 below) once that's built. Same spec, two implementations; the Sheets tab can exist as an interim/manual-check view before Looker Studio is live.

---

## 5. KPI breach alerts (Slack → David)

This is the piece that actually kills the "burned budget until next Wednesday" problem — the dashboard only helps if someone's told to look at it. Alerting runs off the same KPI Status logic driving the Ad Set Overview column above, not a separate system.

- **Trigger:** after every scheduled data refresh (section 6), re-evaluate KPI Status for every ad set/account on the **3-day window** specifically — that's the window meant to catch problems fast, so it's the one that should page someone.
- **Fires on transition, not on every refresh:** alert when a row flips from green/yellow **into red**. Don't re-alert every 4 hours while it's already sitting red and David's presumably working it — that trains people to ignore the channel.
- **Destination:** Slack, via an incoming webhook, into a dedicated channel (e.g. `#kpi-alerts`) so both David and Logan see it — not a DM to David alone, so nothing gets missed if he's off that day.
- **Message content:** client name, ad set name, which metric breached (CPL / cost-per-booked-call / cost-per-show), target vs. actual, and a deep link straight to that account's row in Ad Set Overview / Looker Studio.
- **Re-alert / escalation:** if a row is still red after a cooldown (say 24–48h) with no corresponding entry in `Change Log`, send a follow-up nudge — surfaces the ones David hasn't gotten to yet without spamming the ones he already fixed.
- **Suppress once actioned:** since `Change Log` already exists as the manual optimization journal, the developer can suppress re-alerts for an ad set once a same-day Change Log entry exists for it.

---

## 6. Recommended approach (phased)

Phase 1 is split into **1a** (stops the budget-burn problem, ships in days, built on the existing per-account sheets — no rebuild needed) and **1b** (the full unified dashboard). Don't wait for 1b to get value — 1a alone fixes "we don't find out until Wednesday."

### Phase 1a — Stop the bleeding (fast, on the existing sheets)
No new ingestion required — this only uses data we already pull.

1. **Add a 3-day-incl.-today CPL window** to each account's `Account Overview` tab (same shape as the existing 7-day/30-day rows).
2. **Add a per-account `KPI Target`** (baseline CPL) — a manual config value, same place as the existing `Config` tab.
3. **Switch refresh from the manual button to a scheduled trigger** (daily, ideally 2–3×/day) so the 3-day number is always current.
4. **Build the Slack alert** from section 5 — for now, scoped to account-level CPL vs. target (not yet ad-set-level, not yet booked-call/show — those need 1b's ingestion work first). Green/yellow→red transition, `#kpi-alerts` channel, escalation + Change-Log suppression as described.
5. **Validation spike, done in parallel:** before pricing 1b, have the developer prove the GHL appointment→UTM attribution join (section 7, Q1) actually works on a real data sample. This is the biggest unknown in the whole plan and 1b's scope/cost depends on the answer.

### Phase 1b — The unified dashboard (the bigger rebuild)
Once 1a is live and the attribution spike is validated:

1. **Extend GHL ingestion** to pull **calendar appointments (booked calls)** and **appointment/opportunity outcomes (shows)**, attributed back to the originating ad via the contact's stored UTMs. Join path: `appointment → contact → contact attribution (UTM Ad ID) → Meta ad → Ad Set ID`. Unlocks cost-per-booked-call and cost-per-show.
2. **Extend GHL ingestion (client accounts)** to also pull the contact's **Top of Funnel / Bottom of Funnel tag** into `GHL Raw`, and break the existing Lead Color field out into explicit Green/Yellow/Red counts (not just Green/Green %). Unlocks the Funnel Stage Mix section from section 3.
3. **Add an ad-set-level aggregation** (group by Ad Set ID) alongside the existing ad-level data.
4. **Add the 14-day window** (3/7/30 already exist by this point).
5. **Extend `KPI Targets`** to ad-set granularity plus cost-per-booked-call and cost-per-show targets.
6. **Build the `Ad Set Overview` view described in section 4** — rollup rows + ad-set rows + KPI Status coloring + drill-down + Funnel Stage Mix (client accounts) + the single time-window toggle.
7. **Consolidate all accounts into ONE data store** instead of N separate spreadsheets — one row per ad-set per account per day.
8. **Put a real BI front-end on it: Google Looker Studio** (free, Google-native). Scorecards with conditional color formatting, date-range toggles, a multi-account overview page — the clean "software" UI feel from the reference video, without a custom app build. `Ad Set Overview` becomes the default landing page.
9. **Extend the Slack alert** from account-level CPL to ad-set-level, and to cost-per-booked-call / cost-per-show once that data exists.

**Storage note:** If we stay at a handful of accounts, a single consolidated Google Sheet feeding Looker Studio is fine. As we add clients, move the consolidated store to **BigQuery** (cheap at this volume, native Looker Studio connector, won't break like Sheets does at scale). Looker Studio reads either, so we can start on Sheets and swap to BigQuery later without redoing the front-end.

### Phase 2 — Custom embedded dashboard (only when client count / client-facing need justifies it)
When we want clients to see their own real-time dashboard *inside their GHL sub-account* (iframe embed) and/or we're pushing toward many accounts: BigQuery as the warehouse + a custom UI (Next.js on Vercel). This is the end-state from the reference video; we don't need it to fix the current bottleneck.

---

## 7. Questions for the developer
1. **Can you pull GHL calendar appointments + opportunity/appointment status via API and reliably attribute them to the originating ad through the contact's stored UTMs?** Before quoting Phase 1b, please validate this against a real sample of our data (reschedules and repeat visits are the likely failure modes for UTM persistence) rather than assuming it'll work — this is the single biggest unknown in the whole plan and Phase 1b's scope depends on the answer.
2. Rough effort/cost, quoted **separately** for Phase 1a and Phase 1b as described.
3. Any concern moving the consolidated store to BigQuery now vs. starting on a consolidated Sheet and migrating later?
4. Recommendation on scheduled refresh frequency given Meta/GHL API rate limits (target: at least daily, ideally 2–3×/day).
5. Do we already have a Slack workspace/webhook set up for this, or does one need to be created? (Logan to confirm — see note below.)
6. Can GHL's API return a contact's tags (specifically Top of Funnel / Bottom of Funnel) reliably, including cases where a contact has both, neither, or the tag changes after the lead comes in? Lower-risk than Q1, but confirm before building the Funnel Stage Mix section.
