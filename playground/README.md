# Makra SDK playground

These scripts use `http://localhost:8080` (local public API gateway) and the
documented dummy API key by default. Override either with `MAKRA_BASE_URL` or
`MAKRA_API_KEY`.

Install the local Python package once:

```bash
python -m pip install -e sdk/python
python playground/python.py
python playground/python.py https://example.com
API_KEY="your-api-key" python playground/scripts/github_repositories.py
```

If you use `uv`, it creates and manages a local environment with the checked-out
SDK. It builds and imports Makra from this repository, not PyPI:

```bash
API_KEY="your-api-key" uv run --project sdk/python python playground/scripts/github_repositories.py
```

The Node.js playground imports the local package source directly:

```bash
node playground/node.mjs
node playground/node.mjs https://example.com
```

With no URL argument, each script only calls `ping`. With a URL, it also runs a
small structured extraction.

`scripts/github_repositories.py` runs the GitHub repositories extraction from
the README example and prints repository data plus API usage as terminal
tables. It reads `API_KEY` and defaults to `http://localhost:8080`. Use
`MAKRA_BASE_URL` or `--base-url` to choose another gateway.
