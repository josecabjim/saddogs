# Operations

Operational notes that aren't discoverable from the code itself. See `SPEC.md` for the reliability
work these came out of.

## `saddogs-database` path-dependency goes stale silently

`packages/saddogs-scrape` and `packages/saddogs-api` (deleted, but if this pattern is reused
elsewhere) depend on `saddogs-database` via a local path dependency. `poetry install` in
`saddogs-scrape` does **not** reliably pick up source changes made in `saddogs-database` — it's
installed as a built, non-editable copy, and `poetry install`/`poetry install --sync` often report
"nothing to do" even after `saddogs-database`'s code has changed. If `saddogs-scrape` seems to be
running old `saddogs-database` behavior (missing methods, old signatures), force a reinstall from
inside `packages/saddogs-scrape`:

```bash
poetry run pip install --force-reinstall --no-deps ../saddogs-database
```

## GitHub Pages deployment

`caballerojose.com/saddogs` is served by GitHub Pages configured directly on this repo
(`josecabjim/saddogs`), with a custom domain, deploying root `index.html` on every push to `main` via
GitHub's automatic `pages-build-deployment`. **There is no workflow file for this** — it's a repo
Settings → Pages configuration, which is easy to forget since nothing in `.github/workflows/`
mentions it. It is unrelated to the separate `josecabjim.github.io` repo despite the naming
similarity.

## Laptop fallback for scrapes GitHub Actions can't complete

`daily_scrape.yml` runs every 4h from GitHub Actions' shared-runner IPs, which several target sites
block at the datacenter/ASN level (confirmed via the Phase 0 triage below — most spiders that show
critical on GH Actions run clean from a residential IP). As a free second attempt, run the same
check-then-scrape flow from your own laptop later in the day:

```bash
cd packages/saddogs-scrape/saddogs_scrape
poetry run python check_missing.py        # prints spider names still missing today, or __none__
poetry run python run_all.py --spiders tenerife_k9,census   # only the ones check_missing.py listed
```

Requires a `.env` in `packages/saddogs-scrape/saddogs_scrape/` (or exported in your shell —
`spider_runner.py` calls `load_dotenv()`, and every entry point imports it) with:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY` (same values as the GitHub Actions secrets)

The easiest way to get these locally is to copy them from `packages/saddogs-database/.env`, which
already has them (same Supabase project).

To verify it ran: `check_missing.py` should print `__none__` afterward, or check the newest
`reports/*.json` file's timestamp/summary. If the laptop is off that day, nothing runs — accepted as
fine; a day of staleness is handled by the carry-forward-with-visible-staleness UX in `index.html`,
not treated as its own incident (only the 7-day stale escalation in the daily email is).

Point a `cron`/`launchd` job at the two commands above, run once in the evening after the last
GitHub Actions attempt (GH Actions runs every 4h at :00).

## EMAIL_* secret rotation blind spot

The 22:00 UTC daily-summary email (via `send_failure_email.py`'s Gmail SMTP login) is the main
trustworthy signal once the pipeline email bug is fixed. If `EMAIL_FROM`/`EMAIL_TO`/`EMAIL_PASSWORD`
ever rotate or expire, this fails silently (`send_daily_report`/`send_failure_email` just log a
warning and return `False` — the GH Actions job still exits based on whether there was anything to
report, independent of whether the email actually sent). If the daily email ever just stops arriving
with no explanation, suspect this before assuming the pipeline itself is healthy.

## Phase 0 triage (2026-10-03)

Run from a laptop (non-GitHub-Actions IP) via `poetry run python run_all.py --dry-run -v`, to
separate "blocked by GH Actions' IP range" from "genuinely broken," per `SPEC.md` §5.

| Site / spider | Result | Cause | Fix |
|---|---|---|---|
| 16 other rescue spiders + `census` | ✅ succeed locally | N/A | Confirms the GH Actions datacenter-IP-block hypothesis — no code fix, rely on the laptop fallback above |
| `gran_canaria_telde` | ✅ fixed | DNN module control-id (`ctrNNN`) drifted from `ctr383` to `ctr397` after the site republished — `AspNetAjaxCountSpider` had it hardcoded | Now read from the page itself (`spiders/base/aspnet_ajax_spider.py`), which also hardens `gran_canaria_banaderos` against the same future drift |
| `fuerteventura_dog_rescue` | ❌ disabled | `fuerteventuradogrescue.org` has been squatted by an unrelated gambling site (redirects to `rubyselixirdtsp.com`) — the domain is gone, not just redesigned. No replacement URL found (Facebook page still active) | Disabled in `spiders/fuerteventura.py` with a dated comment; revisit if a new URL turns up |
| `tenerife_adeje_mascotas` | ❌ known issue, unchanged | 200 OK but 0 items — content is JS-rendered/Cloudflare-gated. A Playwright-based rewrite was already tried previously and reverted (didn't help) | None attempted this round — matches the spec's existing call to treat Adeje as its own unresolved line item |
| `tenerife_valle_colino` | ❌ blocked | 403 from a WAF (not Cloudflare) even on a residential IP with full browser headers — not simple IP-reputation | Left as accepted-flaky; a Playwright rewrite is the next thing to try if this is worth more investment, but untried so far |
| `la_gomera_proanimal` | ❌ unreachable at triage time | TLS handshake hung on both http/https directly via `curl`, independent of the scraper — looks like the site itself was down | No action; re-check if it recurs |
