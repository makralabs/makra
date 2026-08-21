# Python SDK

Package `makra`, source in `src/makra`. Python 3.9+. Public examples are
Python-only until the JavaScript documentation returns.

## Commands

From `sdk/python`:

```bash
uv sync --extra dev
uv run ruff check src tests examples
uv run pytest
uv run pyright
```

Without uv:

```bash
python -m pip install -e ".[dev]"
ruff check src tests examples
pytest
pyright
```

The golden program is `examples/golden_quickstart.py`. The local contract test
runs it against an in-process HTTP server with `MAKRA_BASE_URL` and no real
credentials. The optional public job is:

```bash
MAKRA_INTEGRATION=1 MAKRA_API_KEY=mk_live_... pytest -m integration
```

Skip that job for untrusted pull requests.

## Notes

- `extract(urls, schema)` requires a sequence of URLs, not a string.
- Blocking methods return the API envelope. Do not unwrap `data` inside the SDK.
- Keep reserved headers out of `default_headers`.
