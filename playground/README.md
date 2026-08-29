# Makra SDK playground

`python.py` and `node.mjs` are small local-gateway demos. They default to
`http://localhost:8080` and a documented dummy API key. The Python extraction
examples in `scripts/` call the production gateway and use `MAKRA_API_KEY`.

Install the local SDK with the playground dependencies:

```bash
python -m pip install -e "sdk/python[playground]"
```

Create `playground/.env`:

```dotenv
MAKRA_API_KEY=mk_live_...
```

Each script loads that file automatically. An exported `MAKRA_API_KEY` takes
precedence. Run an example directly:

```bash
python playground/scripts/hacker_news_posts.py
python playground/scripts/github_repositories.py
```

With uv, use the checked-out SDK and its playground dependencies:

```bash
uv run --project sdk/python --extra playground python \
  playground/scripts/hacker_news_posts.py
```

Scripts default to `https://api.makralabs.org`. Pass `--base-url` or set
`MAKRA_BASE_URL` only when you need another gateway. Every example uses the
Python SDK, streams workflow activity, then prints extracted data and a compact
usage summary.
