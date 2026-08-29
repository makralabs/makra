# Playground scripts audit

Date: 2026-08-29

## Summary

I ran every executable Python entry point in `playground/scripts/` against the
production Makra API. All 13 runs failed with exit code 1 because the service
sent the terminal event `workflow.run.budget_exhausted`.

The API key in `playground/.env` is valid. When it is loaded, each script gets
past client setup, submits a workflow, and receives `run.started`. This is not
an authentication failure and it is not a Python import failure.

There is a separate configuration gap. The shared runner reads
`MAKRA_API_KEY` only from the process environment. It does not open
`playground/.env` itself. Running a script directly without first exporting the
key exits 2 for every entry point. The documented `uv run --env-file
playground/.env ...` command does load the file correctly, but direct Python
invocations do not.

## Scope and method

The audit covered the 13 runnable example files and the shared `_runner.py`
module.

1. I compiled every file with `python -m compileall -q playground/scripts`.
   It passed.
2. I ran each entry script with `MAKRA_API_KEY` removed. Every one returned
   exit code 2 before contacting the API.
3. I ran each entry script after loading `playground/.env`. Each one submitted
   a production workflow and returned exit code 1 after the API reported
   `budget_exhausted`.
4. I also ran the documented `uv run --env-file` form for
   `hacker_news_posts.py`, with `MAKRA_API_KEY` explicitly removed first. It
   loaded the key and reached the same API budget failure.

The key value was never printed or recorded. `playground/.env` is ignored by
Git, as expected.

## Results by script

| Script | No exported key | With key loaded from `.env` | Notes |
| --- | --- | --- | --- |
| `amazon_india_magnesium_products.py` | Exit 2 | Exit 1, `budget_exhausted` | The workflow started and generated a title before the terminal event. |
| `blog_archive_posts.py` | Exit 2 | Exit 1, `budget_exhausted` | The streaming run reached events 1 through 16. The first three crawl activities also emitted `activity.failed` and `stage.failed` before the budget event. The event payloads shown by the script did not include the crawl error text. |
| `github_repositories.py` | Exit 2 | Exit 1, `budget_exhausted` | Compatibility wrapper for `ritsource_github_repositories.py`. |
| `google_kandahar_giants_results.py` | Exit 2 | Exit 1, `budget_exhausted` | The workflow started and generated a title. |
| `hacker_news.py` | Exit 2 | Exit 1, `budget_exhausted` | Compatibility wrapper for `hacker_news_stories.py`. |
| `hacker_news_posts.py` | Exit 2 | Exit 1, `budget_exhausted` | Also passed the separate documented `uv --env-file` check. |
| `hacker_news_stories.py` | Exit 2 | Exit 1, `budget_exhausted` | The first live run after manually loading `.env` completed the same way. |
| `medicines.py` | Exit 2 | Exit 1, `budget_exhausted` | Compatibility wrapper for `one_mg_medicines.py`. |
| `one_mg_medicines.py` | Exit 2 | Exit 1, `budget_exhausted` | The workflow started and generated a title. |
| `ritsource_github_repositories.py` | Exit 2 | Exit 1, `budget_exhausted` | The workflow started before the budget event. |
| `techcrunch_articles.py` | Exit 2 | Exit 1, `budget_exhausted` | The workflow started before the budget event. |
| `ted_talks.py` | Exit 2 | Exit 1, `budget_exhausted` | The workflow started before the budget event. |
| `y_combinator_companies.py` | Exit 2 | Exit 1, `budget_exhausted` | The workflow started and generated a title. |

`_runner.py` is a library module, not an example entry point. Running it exits
0 and intentionally performs no extraction.

## Why the scripts fail

### 1. Direct execution does not read `.env`

`run_example()` uses `os.getenv("MAKRA_API_KEY")` and returns 2 when that
variable is absent. Nothing in `_runner.py` loads a dotenv file. The
playground dependency group contains `rich` only, so there is no dotenv loader
available either.

This means these direct commands fail even when `playground/.env` exists:

```bash
python playground/scripts/hacker_news_posts.py
uv run --project sdk/python --extra playground python playground/scripts/hacker_news_posts.py
```

The README accurately documents a working workaround:

```bash
uv run --env-file playground/.env --project sdk/python --extra playground python \
  playground/scripts/hacker_news_posts.py
```

That command asks `uv` to populate the process environment before Python
starts. The scripts themselves still do not read the file.

### 2. The production account has no workflow budget available

Once the key is present, the API accepts the requests. Every terminal stream
event reported the `budget_exhausted` status, and `_runner.py` turns that into
`WorkflowResultError: budget_exhausted` and exit code 1. The runner does this
deliberately in `_raise_if_terminal_failed()`.

This prevents validation of the extraction schemas, target-site access, result
formatting, and usage table for the current account. Adding budget or using an
authorized gateway with available budget is required before those parts can be
tested.

The blog archive run exposed a possible second issue. Its first three crawl
activities failed before the budget ended the workflow. Because the streamed
event payload omitted a reason, the audit cannot identify whether the cause is
site access, robots policy, a timeout, or the exhausted budget affecting a
later stage. Retest that script after restoring budget and retain the full
event payload or run ID for diagnosis.

## Recommended changes

If each script must load `playground/.env` by itself, make that behavior
explicit in `_runner.py`.

1. Add `python-dotenv` to the `playground` optional dependency group.
2. Before `os.getenv`, call `load_dotenv()` with the absolute path derived
   from the `_runner.py` location: `Path(__file__).resolve().parents[1] /
   ".env"`.
3. Use `override=False` so an explicitly exported `MAKRA_API_KEY` still wins.
4. Add tests for direct execution with only `playground/.env`, for an exported
   key taking precedence, and for a missing file producing the existing exit-2
   error without exposing secret values.
5. Keep the `uv --env-file` README command. It remains useful for tools that
   are not Python scripts.

The account budget must be restored before a success-path test can establish
whether any of the page-specific schemas or crawls need changes.

## Evidence

The key behavior comes from `playground/scripts/_runner.py` lines 38 through
44. It reads `os.getenv("MAKRA_API_KEY")` and returns 2 when it is missing.
Lines 94 through 106 consume workflow events, raise on an unsuccessful terminal
event, and return 1. The README documents `uv --env-file` at lines 32 through
38. The SDK's `playground` dependency group lists `rich` but no dotenv package.
