# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository structure

Monorepo with no root build tool — three independent Poetry Python projects linked via path
dependencies, plus static HTML/JS frontends. There is no root `pyproject.toml`/`package.json`.

- `packages/saddogs-database` — shared Supabase data-access layer (`DatabaseClient`, repositories
  for `rescues` and `census` tables). Also contains a small standalone FastAPI app (`app.py`) that
  serves chart/table views of the same data.
- `packages/saddogs-scrape` — Scrapy spiders that scrape rescue-org and government census websites
  and write counts into Supabase via `saddogs-database`. Depends on `saddogs-database` as a local
  path dependency (`../saddogs-database`).
- `projects/saddogs-api` — a second, separate FastAPI app (`main.py`) exposing `/census` endpoints.
  It talks to Supabase directly with its own client and does **not** use the `saddogs-database`
  repositories. Depends on `saddogs-database` as a local path dependency.
- `projects/saddogs-dashboard` — static multi-file JS dashboard (`js/api.js`, `dataProcessing.js`,
  `ui.js`, `charts.js`, `main.js`) that queries Supabase directly from the browser with the public
  key in `js/config.js`.
- Root-level `index.html`, `data.html`, `insights.html` — separate, self-contained single-file
  dashboards (inline Chart.js + Supabase JS client), independent of `projects/saddogs-dashboard`.

## Commands

Each Python project has its own Poetry environment; run these from inside the respective directory.

```bash
# Install deps (repeat inside each project directory as needed)
cd packages/saddogs-database && poetry install
cd packages/saddogs-scrape && poetry install
cd projects/saddogs-api && poetry install

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

Serving the FastAPI apps:

```bash
# saddogs-database's chart/table server (/, /graph, /graph-rescues)
cd packages/saddogs-database && poetry run uvicorn saddogs_database.app:app --reload

# saddogs-api's /census endpoints
cd projects/saddogs-api && poetry run uvicorn main:app --reload
```

There is currently no automated test suite (`packages/saddogs-database/tests/` only contains an
empty `__init__.py`), and no lint/format command is configured in any project.

Required environment variables (loaded via `.env` / `python-dotenv` in most entry points):
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` — everywhere the database is read or written.
- `SUPABASE_PUBLISHABLE_KEY` — `projects/saddogs-api/main.py` and `scripts/fetch_census.py`.
- `EMAIL_FROM`, `EMAIL_TO`, `EMAIL_PASSWORD` — Gmail SMTP creds used by `send_failure_email.py`
  (health-check and daily-summary failure emails).
- `ADEJE_PROXY_URL` — optional; when set, `spider_runner.run_all_spiders` applies it as a global
  `HTTP_PROXY`/`HTTPS_PROXY` for the entire run. It is not actually scoped per-spider — the
  `use_proxy = True` flag on `TenerifeAdejeMascotas` in `spiders/tenerife.py` is unused/dead.

## Architecture

**Data flow:** spiders in `packages/saddogs-scrape/saddogs_scrape/spiders/*.py` scrape rescue sites
and one government census page, go through `saddogs_database.client.DatabaseClient` into the
Supabase `rescues` and `census` tables, which are then read back by `saddogs-database`'s `app.py`,
`projects/saddogs-api`, and the two dashboard frontends.

**Spider base-class hierarchy** (`spiders/base/`): `BaseSpider` (wires up `DatabaseClient` unless
`dry_run`) → `BaseRescueSpider` (adds `rescue_name`/`island`, `get_previous_count`, `save_result`
with count-sanity validation) → concrete strategies: `CountSpider` (counts CSS matches, with
optional pagination), `RegexSpider` (extracts a number from text via regex), `PlaywrightCountSpider`
(JS-rendered pages, clicks a "next" button in a loop), `AspNetAjaxCountSpider` (drives an ASP.NET
WebForms postback). `CensusSpider` (in `spiders/census.py`) extends `BaseSpider` directly and parses
a single HTML table into per-island counts, with anomaly checks against the previous census row.
Spiders are grouped one file per island (`tenerife.py`, `lanzarote.py`, etc.), each class just
setting `rescue_name`, `island`, `start_urls`, and the selector(s) for its chosen base class.
Note: there are two identical `CountSpider` definitions — one inline in `base_spider.py` and one in
`count_spider.py` — the latter is the one actually imported by spiders.

**Monitoring:** `spider_runner.SpiderMonitor` listens to the `spider_closed` signal and derives a
severity (`success`/`warning`/`high`/`critical`) from Scrapy stats (items scraped, response counts,
retries, dupes, etc.), downgrading spiders listed in `KNOWN_FLAKY_SPIDERS`. `run_all.py` writes this
to a timestamped JSON file under `reports/`.

**Scheduled automation** is entirely GitHub Actions (`.github/workflows/`), not app code:
- `daily_scrape.yml` — every 4h; first runs `check_missing.py` to find rescues with no row for
  today, then only crawls those spiders.
- `spider_health_check.yml` — every 4h; runs `run_all.py --dry-run` and uploads the JSON report as a
  build artifact.
- `daily_summary.yml` — 22:00 UTC; runs `daily_summary.py`, which emails (via
  `spiders/services/send_failure_email.py`) if any rescue still has no entry for the day, and exits
  non-zero so the workflow run is flagged red.
