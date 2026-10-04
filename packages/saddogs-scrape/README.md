# saddogs-scrape

Scrapy spiders that scrape rescue-org and government census websites and write counts into
Supabase via `saddogs-database` (a local path dependency).

```bash
poetry install
# one-time, for the Playwright-based spiders
poetry run playwright install chromium
```

Scripts use bare imports, so they must be run with the working directory set to
`saddogs_scrape/` (not the Poetry project root):

```bash
cd saddogs_scrape

poetry run python run_all.py                       # run every spider
poetry run python run_all.py --spiders tenerife_k9  # run one or more by name
poetry run python check_missing.py                  # list spiders missing today's data
poetry run python daily_summary.py                  # email a summary if any rescue needs attention

poetry run scrapy crawl <spider_name>                # run a single spider directly
```

See the root [`CLAUDE.md`](../../CLAUDE.md) and [`OPERATIONS.md`](../../OPERATIONS.md) for the
full picture.
