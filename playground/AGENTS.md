# SDK playground

Local scripts against the public API gateway. Defaults are
`http://localhost:8080` and the documented dummy API key. Override with
`MAKRA_BASE_URL` or `MAKRA_API_KEY`.

## Commands

```bash
python -m pip install -e sdk/python
python playground/python.py
python playground/python.py https://example.com
node playground/node.mjs
node playground/node.mjs https://example.com
```

No URL argument calls `ping` only. A URL runs a small extraction.

Public examples remain Python-only. Prefer `sdk/python/examples/golden_quickstart.py`
when documenting a first extraction.
