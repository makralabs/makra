# Makra SDK playground

These scripts use `http://localhost:6900` and the documented dummy API key by
default. Override either with `MAKRA_BASE_URL` or `MAKRA_API_KEY`.

Install the local Python package once:

```bash
python -m pip install -e sdk/python
python playground/python.py
python playground/python.py https://example.com
```

The Node.js playground imports the local package source directly:

```bash
node playground/node.mjs
node playground/node.mjs https://example.com
```

With no URL argument, each script only calls `ping`. With a URL, it also runs a
small structured extraction.
