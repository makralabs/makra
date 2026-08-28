# Makra SDK playground

These scripts use `http://localhost:8080` (local public API gateway) and the
documented dummy API key by default. Override either with `MAKRA_BASE_URL` or
`MAKRA_API_KEY`.

Install the local Python package once:

```bash
python -m pip install -e sdk/python
python playground/python.py
python playground/python.py https://example.com
python playground/scripts/github_repositories.py
```

If you use `uv`, it creates and manages a local environment with the checked-out
SDK. It builds and imports Makra from this repository, not PyPI:

```bash
uv run --project sdk/python python playground/scripts/github_repositories.py
```

The Node.js playground imports the local package source directly:

```bash
node playground/node.mjs
node playground/node.mjs https://example.com
```

With no URL argument, each script only calls `ping`. With a URL, it also runs a
small structured extraction.

The scripts automatically load `playground/.env` without replacing variables
already set in the shell.

`scripts/github_repositories.py` runs the GitHub repositories extraction from
the README example and prints repository data plus API usage as terminal
tables. It reads `MAKRA_API_KEY` and defaults to `https://api.makralabs.org`.
Use `MAKRA_BASE_URL` or `--base-url` to choose another gateway, such as a local
development server.
