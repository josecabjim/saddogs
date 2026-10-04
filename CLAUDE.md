# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository structure

Monorepo with no root build tool — two independent Poetry Python projects linked via a path
dependency, plus one static HTML frontend. There is no root `pyproject.toml`/`package.json`.

- `packages/saddogs-database` — shared Supabase data-access layer (`DatabaseClient`, repositories
  for `rescues` and `census` tables). No app code of its own; just the client + repositories.
- `packages/saddogs-scrape` — Scrapy spiders that scrape rescue-org and government census websites
  and write counts into Supabase via `saddogs-database`. Depends on `saddogs-database` as a local
  path dependency (`../saddogs-database`).
- Root-level `index.html` — the single live dashboard (inline Chart.js + Supabase JS client),
  served by GitHub Pages and talking to Supabase directly from the browser with the publishable
  key. There used to be more frontends and two standalone FastAPI apps (`projects/saddogs-api`,
  `packages/saddogs-database/saddogs_database/app.py`) and alternate dashboards (`data.html`,
  `insights.html`, `projects/saddogs-dashboard`) — all deleted as dead/experimental; `index.html` is
  now the only consumer of the data.

## Commands

Each Python project has its own Poetry environment; run these from inside the respective directory.

```bash
# Install deps (repeat inside each project directory as needed)
cd packages/saddogs-database && poetry install
cd packages/saddogs-scrape && poetry install

# Playwright-based spiders need the browser installed once
cd packages/saddogs-scrape && poetry run playwright install chromium
```

Scraper scripts (`run_all.py`, `check_missing.py`, `daily_summary.py`) use bare imports
(`import spiders`, `from spider_runner import ...`), so they must be run with the working directory
set to `packages/saddogs-scrape/saddogs_scrape/` (not the Poetry project root):

```bash
cd packages/saddogs-scrape/saddogs_scrape

# Run every spider
poetry run python run_all.py

# Run one or more spiders by exact name (comma-separated)
poetry run python run_all.py --spiders tenerife_k9,census

# Dry run — no DB writes, used by the health-check workflow
poetry run python run_all.py --dry-run

# Verbose (DEBUG) logging
poetry run python run_all.py -v

# List spiders missing today's data (prints spider names, one per line, or "__none__")
poetry run python check_missing.py

# Email a summary if any rescue is still missing data (run at end of day)
poetry run python daily_summary.py
```

A single spider can also be run with plain Scrapy from the same directory:
`poetry run scrapy crawl <spider_name>`.

There's no backend service to serve — `index.html` reads Supabase directly from the browser with
the publishable key hardcoded in the file itself (not an env var).

There is currently no automated test suite (`packages/saddogs-database/tests/` only contains an
empty `__init__.py`), and no lint/format command is configured in either project.

Required environment variables (loaded via `.env` / `python-dotenv` in most entry points):
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` — everywhere the database is read or written.
- `EMAIL_FROM`, `EMAIL_TO`, `EMAIL_PASSWORD` — Gmail SMTP creds used by `send_failure_email.py`
  (health-check and daily-summary failure emails).

## Architecture

**Data flow:** spiders in `packages/saddogs-scrape/saddogs_scrape/spiders/*.py` scrape rescue sites
and one government census page, go through `saddogs_database.client.DatabaseClient` into the
Supabase `rescues` and `census` tables, which `index.html` then reads back directly from the
browser via the Supabase JS client (publishable key, read-only) — no backend in that path.

**Spider base-class hierarchy** (`spiders/base/`): `BaseSpider` (wires up `DatabaseClient` unless
`dry_run`) → `BaseRescueSpider` (adds `rescue_name`/`island`, `get_previous_count`, `save_result`
with count-sanity validation) → concrete strategies: `CountSpider` (counts CSS matches, with
optional pagination), `RegexSpider` (extracts a number from text via regex), `PlaywrightCountSpider`
(JS-rendered pages, clicks a "next" button in a loop), `AspNetAjaxCountSpider` (drives an ASP.NET
WebForms postback). `CensusSpider` (in `spiders/census.py`) extends `BaseSpider` directly and parses
a single HTML table into per-island counts, with anomaly checks against the previous census row.
Spiders are grouped one file per island (`tenerife.py`, `lanzarote.py`, etc.), each class just
setting `rescue_name`, `island`, `start_urls`, and the selector(s) for its chosen base class.
Anomaly checks (`spiders/services/validation.py`) and the census path's own check
(`spiders/census.py`) flag — rather than drop — a count that looks like a >50% drop or >200% jump
vs. the previous value, by saving the row with `needs_review = true`.

**Monitoring:** `spider_runner.SpiderMonitor` listens to the `spider_closed` signal and derives a
severity (`success`/`warning`/`high`/`critical`) from Scrapy stats (items scraped, response counts,
retries, dupes, etc.), downgrading spiders listed in `KNOWN_FLAKY_SPIDERS`. `run_all.py` writes this
to a timestamped JSON file under `reports/`.

**Scheduled automation** is entirely GitHub Actions (`.github/workflows/`), not app code:
- `daily_scrape.yml` — every 8h (00:13/08:13/16:13 UTC); first runs `check_missing.py` to find
  rescues with no row for today, then only crawls those spiders.
- `spider_health_check.yml` — every 8h (00:41/08:41/16:41 UTC); runs `run_all.py --dry-run` and
  uploads the JSON report as a build artifact.
- `daily_summary.yml` — 21:11 UTC (deliberately not 22:00 — see OPERATIONS.md); runs
  `daily_summary.py`, which emails (via
  `spiders/services/send_failure_email.py`) a two-section report — needs review (last 24h), stale
  7+ days — if either section is non-empty, and exits non-zero so the workflow run is flagged red.
  A same-day "missing" miss deliberately does not trigger this email; see OPERATIONS.md.
