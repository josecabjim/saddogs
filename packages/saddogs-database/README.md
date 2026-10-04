# saddogs-database

Shared Supabase data-access layer for the saddogs monorepo: `DatabaseClient` plus repositories for
the `rescues` and `census` tables. No standalone app — it exists only to be depended on by
`saddogs-scrape`.

```bash
poetry install
```

See the root [`CLAUDE.md`](../../CLAUDE.md) for the full monorepo picture.
