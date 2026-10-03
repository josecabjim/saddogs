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

## GitHub Actions IP-block hypothesis: revisited and mostly rejected (2026-10-03)

`SPEC.md` was written on the assumption that GitHub Actions' shared-runner IPs were broadly blocked
by many target sites (21/21 spiders critical on the day that report was pulled). **This was
re-investigated and does not hold up as a steady-state problem**:

- Dispatching `daily_scrape.yml` for real on 2026-10-03 showed GH Actions had already scraped 17-18
  of 21 sources successfully *earlier the same day, before any of this session's fixes landed* — the
  `check_missing` job's own log from the 09:30 UTC run that day only listed 4 spiders as missing, not
  21. The historical "21/21 critical" report was an anomalous bad day (cause unknown — possibly a
  transient network issue, a batch of sites having an unrelated bad day, or something that has since
  resolved itself), not a persistent block.
- The 2-3 sources that *are* chronically broken each have their own specific, unrelated cause (see
  the triage table below) — none of them are "blocked because the request came from Azure." One
  (`tenerife_valle_colino`) looked exactly like an IP-reputation block at first (403 from a WAF) but
  turned out to be a request-fingerprint/bot-mitigation soft-block: the *same residential IP* got a
  403 via `curl`/Scrapy's plain HTTP client but a clean 200 via Playwright's real Chromium, and GH
  Actions got a 202 (not even a 403) on the same URL with the plain client. Switching that one spider
  to render with a real browser (see `PlaywrightRegexSpider`) fixed it on GH Actions directly —
  confirmed via a live dispatched run, no infrastructure change needed.

**Conclusion: a laptop (or any other always-on machine/service) fallback is not needed as a general
safety net.** GitHub Actions alone is the primary and, for all but the sites below, *sufficient*
path. Don't build new infrastructure (self-hosted runners, proxies, alternate cloud cron, etc.) to
solve "GH Actions is blocked" — it mostly isn't. If a specific spider is chronically broken, diagnose
*that spider* (wrong selector, dead domain, real bot-mitigation on that one site) rather than
assuming a runner-topology problem.

If you still want an occasional manual check from elsewhere (e.g. to confirm whether a specific
failure is really the target site's fault), the same check-then-scrape flow works locally:

```bash
cd packages/saddogs-scrape/saddogs_scrape
poetry run python check_missing.py        # prints spider names still missing today, or __none__
poetry run python run_all.py --spiders tenerife_k9,census   # only the ones check_missing.py listed
```

Requires a `.env` in `packages/saddogs-scrape/saddogs_scrape/` (or exported in your shell —
`spider_runner.py` calls `load_dotenv()`, and every entry point imports it) with `SUPABASE_URL` and
`SUPABASE_SERVICE_ROLE_KEY` (same values as the GitHub Actions secrets — easiest to copy from
`packages/saddogs-database/.env`, same Supabase project). But this is a diagnostic tool now, not a
scheduled dependency.

## EMAIL_* secret rotation blind spot

The 22:00 UTC daily-summary email (via `send_failure_email.py`'s Gmail SMTP login) is the main
trustworthy signal once the pipeline email bug is fixed. If `EMAIL_FROM`/`EMAIL_TO`/`EMAIL_PASSWORD`
ever rotate or expire, this fails silently (`send_daily_report`/`send_failure_email` just log a
warning and return `False` — the GH Actions job still exits based on whether there was anything to
report, independent of whether the email actually sent). If the daily email ever just stops arriving
with no explanation, suspect this before assuming the pipeline itself is healthy.

## Triage (2026-10-03, updated after live GH Actions verification)

| Site / spider | Result | Cause | Fix |
|---|---|---|---|
| 18 of 21 rescue spiders + `census` | ✅ work fine, including on GH Actions | N/A | Nothing to do — see the IP-block section above |
| `gran_canaria_telde` | ✅ fixed, confirmed live on GH Actions | DNN module control-id (`ctrNNN`) drifted from `ctr383` to `ctr397` after the site republished — `AspNetAjaxCountSpider` had it hardcoded | Now read from the page itself (`spiders/base/aspnet_ajax_spider.py`), which also hardens `gran_canaria_banaderos` against the same future drift |
| `tenerife_valle_colino` | ✅ fixed, confirmed live on GH Actions | Request-fingerprint/bot-mitigation soft-block, not IP reputation: the same residential IP got a 403 via `curl`/Scrapy but 200 via Playwright's real Chromium; GH Actions got a 202 (not even a 403) with the plain client | Switched to `PlaywrightRegexSpider` (renders with real Chromium, same selector/regex as before) |
| `fuerteventura_dog_rescue` | ❌ disabled | `fuerteventuradogrescue.org` has been squatted by an unrelated gambling site (redirects to `rubyselixirdtsp.com`) — the domain is gone, not just redesigned. No replacement URL found (Facebook page still active) | Disabled in `spiders/fuerteventura.py` with a dated comment; revisit if a new URL turns up |
| `tenerife_adeje_mascotas` | ❌ unresolved, better-understood | Not simply "JS-rendered" as previously assumed. The page embeds the actual pet listing via a third-party municipal-services widget (`insuit.net`) inside a nested iframe setup; the widget's content never materializes at the expected selector even after 20s+ waits with a real browser, and `networkidle` never fires (the widget keeps background network activity alive). This needs reverse-engineering the widget's internal tab/API — not attempted further, consistent with the original spec's call to treat Adeje as its own deprioritized line item | None — matches history of proxy/Playwright attempts not panning out for this one specific site |
| `la_gomera_proanimal` | ❌ unreachable, re-confirmed | TLS handshake hangs on both http/https, confirmed independently via two unrelated networks (this laptop and Anthropic's fetch infrastructure) — the site itself is down, not a scraper or runner problem | No action; will clear on its own if/when the site comes back, otherwise the 7-day stale alert will catch it |
