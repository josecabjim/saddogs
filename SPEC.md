# Saddogs — Reliability & Consolidation Spec

## 1. Problem statement

Saddogs tracks daily dog counts for ~20 rescues across the Canary Islands plus a government
census figure, scraped by Scrapy spiders running on a GitHub Actions cron, stored in Supabase, and
displayed on a public dashboard at `caballerojose.com/saddogs`.

As of this spec, the pipeline is badly degraded: the most recent daily-summary report shows **21/21
spiders critical** ("no entry recorded for today"), and the `Daily Summary` workflow has failed
every single day for at least the preceding week — this is not a one-off blip, it's a sustained
outage. Investigation during this interview turned up two compounding problems:

1. **The failure is probably not N independent site-specific blocks.** `census` — which scrapes a
   completely unrelated government site (zoocan.net), via a completely different parsing strategy
   than any rescue spider — failed on the same day as every rescue spider. The leading hypothesis
   is that GitHub Actions' shared-runner IP ranges are now broadly blocked by several of these sites
   at once (many small Spanish sites sit behind Cloudflare, which commonly blocks entire
   datacenter/hosting-provider ASNs — including GitHub Actions' Azure ranges — regardless of
   per-domain config). This has not been confirmed yet; confirming it is the first action item
   below.
2. **The monitoring can't be trusted to tell you this is happening.** In `daily_scrape.yml`, the
   actual spider run is `poetry run python run_all.py --spiders "$MISSING" || true` — the `|| true`
   means this workflow shows green in the Actions tab *no matter how badly the spiders fail*. The
   only real signal is the 22:00 UTC `daily_summary.py` email, which does appear to be arriving
   (you shared one), but there is no reason to expect it would be if `EMAIL_*` secrets ever rotate —
   it would then fail silently in both places at once.

This spec covers fixing the pipeline, restructuring how failures are surfaced, and consolidating
the frontend. It does **not** cover turning this into an adopter-facing product (see §9).

## 2. Current-state findings (reference material)

Established during this investigation, worth keeping around so the next person (or future Claude)
doesn't have to re-derive it:

- **Deployment**: `caballerojose.com/saddogs` is served by GitHub Pages configured *directly on this
  repo* (`josecabjim/saddogs`), with a custom domain, deploying root `index.html` on every push to
  `main` via GitHub's automatic `pages-build-deployment` — there is no workflow file for this, it's
  a repo Settings → Pages configuration. It is **not** related to the separate
  `josecabjim.github.io` repo, despite the naming similarity. Confirmed via `curl -IL`: both
  `https://josecabjim.github.io/saddogs/` and `https://www.caballerojose.com/saddogs` redirect to
  `https://caballerojose.com/saddogs/`.
- **Four frontends currently exist, only one is live**: root `index.html` (dark theme, the one
  actually served), root `data.html` and `insights.html` (alternate designs, not linked from
  anywhere live), and `projects/saddogs-dashboard` (a separate multi-file JS build, also not the
  live one).
- **Two FastAPI apps exist and appear to be dead/local-only experiments**: `projects/saddogs-api`
  (its own `scripts/add_census.py` posts to `127.0.0.1:8000` — a local dev script) and
  `packages/saddogs-database/saddogs_database/app.py`. Neither has any hosting config anywhere in
  the repo (no Render/Fly/Procfile/etc.). The live site talks to Supabase directly from the browser
  with the publishable key, bypassing both of these entirely.
- **The live frontend already does client-side gap-filling for chart continuity.** `index.html`'s
  `processCensus`/`processRescues` already forward-fill missing days with the last known value so
  the lines/totals stay continuous — it just does this completely silently, with no indication to a
  viewer that a given number might be weeks stale. This matters a lot for §6 below: most of the
  "carry forward instead of leaving a gap" behavior you asked for already exists; what's missing is
  *staleness visibility*, not the fill logic itself.
- **Anomaly handling is inconsistent today.** `CensusSpider.validate_against_previous_census` (in
  `spiders/census.py`) raises `ValueError` on a >50% drop or >200% jump, which kills the spider run
  and the row is never saved. `validate_against_previous` (in `spiders/services/validation.py`,
  used by the rescue-count flow) only calls `warnings.warn(...)`, which is easy to miss (prints
  once to stderr, not captured anywhere) and doesn't stop the save. Two different anomaly-handling
  behaviors for conceptually the same problem.
- **Known dead/duplicate code**: `CountSpider` is defined identically twice (inline in
  `base_spider.py`, and again in `count_spider.py` — the latter is the one actually imported).
  `TenerifeAdejeMascotas.use_proxy = True` is never read anywhere — the actual proxy mechanism is a
  single global `HTTP_PROXY`/`HTTPS_PROXY` set for the *entire* run when `ADEJE_PROXY_URL` is
  present, applied to every spider, not scoped per-site.
- **Adeje specifically has a longer-standing, separate problem**: it's been blocked for a while, and
  proxy attempts to fix it specifically have already failed. Treat it as its own line item, not
  assumed to be fixed by whatever fixes the rest.

## 3. Goals

- Get back to one real scrape per day for every rescue + census, as reliably as free tooling allows.
- When a real scrape genuinely can't happen, degrade gracefully (keep showing the last known value,
  visibly marked as stale) rather than showing a gap or a misleadingly "fresh" number.
- Make the monitoring trustworthy: a human glancing at GitHub's Actions tab, or the daily email,
  should get an accurate picture without needing to cross-reference both.
- Collapse to one frontend, one data path, no dead experimental services.
- Do all of this for $0/month.

## 4. Non-goals (for this spec)

- No paid proxies, browser-farm APIs, or hosting. Free tier or self-hosted-on-what-you-already-have
  only.
- No adopter-facing features (per-dog listings, adoption CTAs, etc.) — noted as future work in §9
  only; current schema/architecture is not being bent to accommodate it yet.
- No redesign of the visual language of `index.html` — it keeps its current look; this spec adds
  staleness/review indicators to it, not a new design.

## 5. Phase 0 — Confirm the root cause before building around a guess

Before investing in any resilience architecture, **run one spider from a non-GitHub-Actions IP
(your laptop) and diff the result against the same spider run on GitHub Actions on the same day**:

```bash
cd packages/saddogs-scrape/saddogs_scrape
poetry run python run_all.py --dry-run -v --spiders tenerife_k9,census
```

- If it **succeeds locally but fails on GH Actions** for sites that aren't Adeje → this confirms the
  datacenter-IP-block hypothesis. The fix is primarily about *where the request comes from*
  (§6.1), not rewriting individual spiders.
- If it **fails locally too**, for a given site → that site has a different, genuine problem
  (selector drift from a redesign, markup change, rate limiting unrelated to IP reputation, etc.)
  and needs its own fix, independent of any runner-topology change.

Do this triage **per currently-critical spider** (all 21, from the report in §1) before deciding
which ones need a runner change vs. a selector/logic fix vs. are genuinely dead ends. Keep a simple
running list (even just a GitHub issue or a markdown table) of: site → suspected cause → fix
attempted → result. This replaces guessing with evidence, and tells you which spiders are worth a
retry-hardening investment (§6.2) vs. which should just be accepted as flaky and rely on
stale-but-visible carry-forward (§7).

## 6. Phase 1 — Pipeline resilience

### 6.1 Runner topology: GitHub Actions primary, laptop fallback

- GitHub Actions keeps running on its existing `daily_scrape.yml` schedule as the primary attempt.
- Your laptop runs a local cron job (or similar) later in the day that:
  1. Calls `check_missing.py` (already exists, no changes needed) to get the list of rescues still
     without a row for today.
  2. If the list is non-empty, runs `run_all.py --spiders <missing>` locally, so the request comes
     from your home IP instead of GitHub's.
  3. If the laptop happens to be off that day, nothing runs — this is accepted as fine per your
     answer; a day of true staleness is handled by the carry-forward-with-visible-staleness UX in
     §7, not treated as an incident on its own (only the 7-day escalation in §8.2 is).
- This needs a `.env` on the laptop with `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY` (same values as
  the GitHub secrets) and the laptop's cron/launchd job pointed at
  `packages/saddogs-scrape/saddogs_scrape`.
- No code changes required beyond documenting this setup (README or a short `OPERATIONS.md`) — the
  existing scripts already support this; it's an operational addition, not a new feature.

### 6.2 Per-site retry hardening — decide after Phase 0, not before

You confirmed retry effort should vary by site rather than being a single blanket policy. Once
Phase 0's triage table exists, for sites confirmed to be IP-reputation-sensitive (not selector
breakage), consider cheap, free-tier-compatible hardening *in addition to* the laptop fallback:
rotating the `USER_AGENT` already set per-spider in `custom_settings`, adding jitter to
`DOWNLOAD_DELAY`, and — only for sites where this is proven to matter — retrying once without and
once with any available proxy. Don't apply this uniformly; it's wasted effort on sites whose real
problem is a changed CSS selector, which no amount of retrying fixes.

### 6.3 Dead code cleanup (in scope, done opportunistically)

While touching these files for the above:
- Delete the duplicate inline `CountSpider` in `spiders/base/base_spider.py` (keep the one in
  `spiders/base/count_spider.py`, which is what's actually imported).
- Remove `use_proxy = True` from `TenerifeAdejeMascotas` (dead attribute — the real proxy toggle is
  the global `ADEJE_PROXY_URL` env var in `spider_runner.run_all_spiders`). If per-spider proxy
  scoping is something you want later, that'd be new behavior, not a fix to existing behavior — call
  it out separately if you want it.
- Fix the `|| true` in `daily_scrape.yml`'s `scrape` job step so a genuine pipeline crash (not just
  "some sites had zero items," which is an expected/handled case) actually fails the workflow red.
  Recommended split: `run_all.py` should itself distinguish "ran fine, individual spiders reported
  critical/high severity" (expected, not a workflow failure — that's what the email is for) from
  "the script itself crashed before producing a report" (actual infra failure — this should NOT be
  swallowed by `|| true`). Concretely: keep `|| true` off, and make sure `run_all.py`'s existing
  `except Exception` branch (which already writes a minimal report and calls `sys.exit(1)`) is the
  only path that fails the job — a normal run with critical spiders already exits 0 today, so
  removing `|| true` should not cause new false-positive red workflows.

## 7. Phase 2 — Data model: stop losing anomalies, keep gap-filling at read time

### 7.1 No fake rows for missing days

Confirmed: do **not** write a synthetic "carried forward" row to Supabase for a day with no real
scrape. The frontend already reconstructs a continuous daily series from sparse rows (§2) — this
stays read-time-only logic, not a DB write. This keeps the `rescues`/`census` tables as a ground
truth of *actual* scrape events only, which matters for anything that later needs to reason about
"when did we last really check this."

### 7.2 Add `needs_review` instead of raising on anomalies

Today, `census.py`'s anomaly check raises and the row is silently dropped; the rescue-count path
only `warnings.warn`s (easy to miss, no persistence). Unify both to the same pattern:

- Add a `needs_review boolean not null default false` column to both the `census` and `rescues`
  Supabase tables.
- In both `CensusSpider.validate_against_previous_census` and
  `spiders/services/validation.validate_against_previous`, stop raising/warning-only. Instead,
  compute the same "is this a >50% drop or >200% jump vs. previous" check, and if true, **save the
  row with `needs_review = true`** rather than dropping it. The row still gets written — the data
  isn't lost — but it's flagged.
- The live `index.html`'s `processCensus`/`processRescues` should exclude `needs_review = true` rows
  from the "latest known value" used for totals/charts (treat them like a missing day — carry
  forward the last *clean* value instead) until the flag is cleared.
- Review mechanism (your call, confirmed): no new admin UI. Flagged rows get fixed by hand in
  Supabase's own table editor. The daily email (§8.1) is the thing that tells you a row needs this,
  so you don't have to go looking.

## 8. Phase 3 — Monitoring & alerting restructure

The daily email (`daily_summary.py` → `send_failure_email.py`) currently only reports "missing
today." Extend it to three clearly-separated sections, all in the existing single email (no new
channel):

1. **Missing today** (existing behavior, unchanged) — rescues with no row at all for today's date.
2. **Needs review** (new) — any row saved in the last 24h with `needs_review = true`, so flagged
   anomalies surface here instead of only being discoverable by manually browsing Supabase.
3. **Stale 7+ days** (new) — any rescue/census whose most recent *real* row (ignore
   `needs_review = true` rows for this purpose too) is 7 or more days old. This is deliberately a
   different bar than "missing today": a rescue that fails once is routine; a rescue that hasn't
   produced a real number in a week is a distinct, worse problem and should visually stand out in
   the email (its own heading, e.g. with a different emoji/marker) rather than blending into
   ordinary daily noise.

This requires `check_missing.py` (or a new small sibling script) to also compute "most recent real
row per known rescue," not just "missing today," since that data isn't currently queried anywhere.

## 9. Phase 4 — Frontend consolidation

- **Keep**: root `index.html`, as-is design-wise, served by the existing GitHub Pages setup.
- **Delete**: `data.html`, `insights.html`, `projects/saddogs-dashboard/`, `projects/saddogs-api/`,
  and `packages/saddogs-database/saddogs_database/app.py`. None of these are the live path; keeping
  them around is pure maintenance burden and a trap for a future "wait, which of these is actually
  live?" moment. (`packages/saddogs-database`'s repository classes — `client.py`,
  `repositories/`  — stay; only its embedded FastAPI app goes.)
- **No backend service.** Confirmed: stay fully static. `index.html` keeps talking to Supabase
  directly from the browser with the publishable key, as it does today. This avoids introducing any
  hosting dependency (which would also need to be free and would add a cold-start/uptime concern for
  no real benefit now that there's only one consumer).
- **Add to `index.html`**:
  - A per-rescue/per-island staleness indicator wherever the current per-island cards/legend already
    render (e.g. the existing `.island-card` / `ic-*` elements in `updateCensusCards`, and the
    equivalent for the rescue side) — something like a small "last real update: N days ago" note,
    derived from the true (non-forward-filled) last-row date per rescue, not the synthetic daily
    series used for the chart line itself.
  - Exclude `needs_review = true` rows from the series the same way a missing day is excluded (§7.2).
  - No change to how the aggregate "Total" figures treat ordinary staleness — carried-forward values
    keep counting toward totals silently, per your answer in the interview; only `needs_review` rows
    are excluded, since those are suspected-wrong, not just old.

## 10. Operational notes to write down somewhere (README or OPERATIONS.md)

- How to set up the laptop fallback cron (§6.1): required env vars, exact command, how to verify it
  ran (check the `reports/` JSON or just that today's `check_missing.py` comes back empty).
- The GitHub Pages deployment mechanism (§2) — it's configured via repo Settings, not a workflow
  file, which is easy to forget and hard to rediscover later.
- The Phase 0 triage table (site → cause → fix → result) as a living reference for which spiders are
  known-fragile and why.

## 11. Open risks

- The datacenter-IP-block hypothesis, even if confirmed, may not be something a free laptop-fallback
  fully solves forever — home IP reputation can also degrade over time with heavy automated traffic
  to the same handful of sites. No paid fallback exists in this plan if that happens; it would need
  revisiting (currently out of budget scope, per your "free only" answer).
- `EMAIL_*` (Gmail SMTP) secrets silently expiring would currently break your only reliable failure
  signal with no secondary alert. Not fixed by this spec (no budget for a second channel), but worth
  knowing: if the daily email ever just stops arriving with no explanation, suspect this before
  assuming the pipeline itself is healthy.
- Adeje remains unresolved; nothing in this plan guarantees a fix for it specifically, since
  proxy-based attempts already failed. It gets the same Phase 0 triage treatment as everything else,
  with no higher expectation of success given the history.

## 12. Future work (explicitly out of scope now)

You mentioned wanting this to eventually be useful for potential adopters, not just stats. Noted as
a direction, not a constraint on today's design: this would likely require per-dog records (photo,
breed, status) rather than the current daily-aggregate-count model, which is a substantially
different and harder scraping problem (per-animal listings change structure far more often and vary
more per site than a single "total" number does). Worth a fresh, separate spec when you're ready to
pursue it — don't let it influence schema or architecture decisions made here.
