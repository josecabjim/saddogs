# Operations

Operational notes that aren't discoverable from the code itself. See `SPEC.md` for the reliability
work these came out of.

## `saddogs-database` path-dependency goes stale silently

`packages/saddogs-scrape` (and the now-deleted `projects/saddogs-api`, if this pattern is ever
reused elsewhere) depends on `saddogs-database` via a local path dependency. `poetry install` in
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
trustworthy signal, now that it reports three clearly-separated sections (missing today, needs
review, stale 7+ days) instead of just "missing today". If `EMAIL_FROM`/`EMAIL_TO`/`EMAIL_PASSWORD`
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
| `tenerife_adeje_mascotas` | ❌ retired 2026-10-03 | Not simply "JS-rendered" as previously assumed — the page embeds the actual pet listing via a third-party municipal-services widget (`insuit.net`) inside a nested iframe setup that never materializes at the expected selector even after 20s+ waits with a real browser. But separately, and more decisively: the live page now shows zero animals listed (confirmed by eye on adeje.es directly, 2026-10-03), and the last *successful* scrape before that was 2026-06-27 — over three months with no true read. Treated as abandoned rather than worth continuing to chase the widget | Spider commented out in `spiders/tenerife.py`; see "Retired rescues" below for how the historical data was closed out |
| `la_gomera_proanimal` | ❌ unreachable, re-confirmed | TLS handshake hangs on both http/https, confirmed independently via two unrelated networks (this laptop and Anthropic's fetch infrastructure) — the site itself is down, not a scraper or runner problem | No action; will clear on its own if/when the site comes back, otherwise the 7-day stale alert will catch it |

## Retired rescues: Adeje Mascotas and Fuerteventura Dog Rescue (2026-10-03)

Both rescues' source sites are gone, and both spiders are now disabled (commented out, not deleted,
in `spiders/tenerife.py` and `spiders/fuerteventura.py`) rather than left to retry forever. Disabling
the spider is enough to drop a retired rescue out of `check_missing.py`'s "missing today" and
`get_stale_spider_names`'s "stale 7+ days" monitoring — both derive their "known rescues" list from
`load_spiders()`, so a commented-out spider simply stops being tracked (same mechanism already used
for `fuerteventura_dog_rescue`). The two historical data series were closed out differently, because
the evidence available for each was different:

- **Adeje Mascotas**: the current true count is actually known — browsing `adeje.es` directly on
  2026-10-03 shows zero animals listed. That's a real, confirmed observation, just not one the
  spider produced. A single row (`total_dogs=0`, `needs_review=false`, dated 2026-10-03) was
  inserted by hand to close the series honestly. It is **not** backdated to 2026-06-27 (the last
  successful scrape) or to any point in between — we have no evidence of exactly when the count
  actually dropped to zero over those three-plus months, so the chart will show a flat line at the
  last real scraped value (14) through 2026-06-27, then a gap, then a single-day drop to 0 on
  2026-10-03. That discontinuity is the honest shape of what we actually know, not a bug.
- **Fuerteventura Dog Rescue**: no current read is possible at all — the domain is squatted by an
  unrelated site, not merely redesigned, so there's no page left to even eyeball. Forcing this one to
  0 would be a guess dressed up as data. Its last real row (`total_dogs=6`, 2026-08-05) stands as the
  final data point; no synthetic row was added.

**Known limitation, accepted for now**: `index.html`'s forward-fill (per SPEC.md §7/§9) carries the
last real value forward indefinitely for *any* stale rescue, and retired rescues are no exception —
Fuerteventura Dog Rescue's "6" (and Adeje's new "0") will keep counting toward island/total figures
forever, not just until some cutoff. The per-rescue "last real update: N days ago" card already
exposes the staleness honestly, and SPEC.md §9 already accepted silent carry-forward as the intended
behavior for ordinary staleness — this just means that policy now also applies, indefinitely, to
rescues that are never coming back, which SPEC.md didn't anticipate. No dashboard change was made for
this; if the growing list of retired-but-still-counted rescues becomes noticeable, a future pass
should give retired rescues a real end date and have `processRescues` stop counting them after it,
rather than forward-filling forever.
