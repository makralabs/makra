<p align="center">
  <img src="assets/makralabs-lockup.png" alt="Makralabs" width="360" />
</p>

Makra is the official client for the Makra web extraction API. Pass a URL and a small description of the data you need. Makra reads the page remotely and returns the API response as structured JSON.

This repository contains the Python and JavaScript SDKs, their shared contract, and a Python playground for a local gateway. Python is used in the examples below.

## Install

Python 3.9 or later:

```bash
pip install makra
```

JavaScript, Node.js 18 or later:

```bash
npm install makra
```

Set an API key before making requests:

```bash
export MAKRA_API_KEY="your-api-key"
```

## Extract data

`schema` describes the values Makra should find. The strings say what each field means on the page. Use a list with one object template for repeated content.

```python
from makra import Makra

schema = {
    "products": [
        {
            "name": "Product title",
            "price": "Current displayed price",
            "url": "Absolute product URL",
        }
    ]
}

with Makra() as makra:
    response = makra.extract(
        ["https://example.com/category/widgets"],
        schema,
    )

print(response)
```

The SDK returns the full successful API body. It does not unwrap `data` or impose a response model.

## Workflows

| Need | Python method | Result |
| --- | --- | --- |
| A response in the current request | `extract`, `schema` | The successful API body. |
| Progress while work runs | `extract_stream`, `schema_stream` | Server-sent lifecycle events. Retrieve the result by run ID after a terminal event. |
| Work that outlives this process | `submit_extract`, `submit_schema` | A `RunHandle` with `wait`, `stream`, `result`, and `cancel`. |

Use `schema` to inspect a page before designing an extraction shape. Store a deferred run ID with your own job record. You can later call `get_run`, `wait_for_run`, `stream_run_events`, or `get_run_result` from another process.

## Repository layout

| Path | Contents |
| --- | --- |
| [`sdk/python`](sdk/python) | Python package, synchronous and `asyncio` clients, type hints, and tests. |
| [`sdk/javascript`](sdk/javascript) | ESM JavaScript package with TypeScript declarations and tests. |
| [`sdk/SPEC.md`](sdk/SPEC.md) | Language-neutral API and SDK contract. |
| [`playground`](playground) | Python script for trying a local API gateway. |

## Local development

```bash
python -m pip install -e sdk/python
python playground/python.py https://example.com

cd sdk/python && uv run pytest
```

The playground defaults to `http://localhost:8080` and the development API key. Override either with `MAKRA_BASE_URL` or `MAKRA_API_KEY`.

## Documentation

Read the [Makra documentation](https://docs.makralabs.org/) for setup, workflow guides, configuration, and API references. Package-specific details live in the [Python README](sdk/python/README.md), [JavaScript README](sdk/javascript/README.md), and [SDK specification](sdk/SPEC.md).

## License

Both SDK packages use the MIT License. See [Python](sdk/python/LICENSE) and [JavaScript](sdk/javascript/LICENSE).
