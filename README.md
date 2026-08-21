<p align="center">
  <img src="assets/makralabs-lockup.svg" alt="Makralabs" width="360" />
</p>

<p align="center">
  Structured web data for software that needs an answer, not a browser tab.
</p>

Makra is a client library for the Makra web extraction API. Give it a URL and a description of the data you need. Makra fetches the page, finds the relevant content, and returns the API response as structured JSON.

This repository contains the official Python and JavaScript SDKs, their shared contract, and small scripts for trying the API against a local gateway.

## What you can do

- Extract a known shape from one page or many pages.
- Ask Makra to describe a page before you write an extraction shape.
- Stream run progress to a user interface or log.
- Submit work that outlives the current process, then retrieve it by run ID.

Makra handles page access remotely. The SDK validates your request, sends it to the Makra API, and returns successful response bodies without reshaping them.

## Install an SDK

Python requires Python 3.9 or later:

```bash
pip install makra
```

JavaScript requires Node.js 18 or later and uses ESM:

```bash
npm install makra
```

Set your API key before you run either example:

```bash
export MAKRA_API_KEY="your-api-key"
```

## Extract data

The `schema` is a JSON object or array that describes the data you want. Its strings tell Makra what each field means on the page.

### Python

```python
from makra import Makra

product = {
    "name": "Product name",
    "price": "Current displayed price",
    "in_stock": "Whether the product can be purchased",
}

with Makra() as makra:
    response = makra.extract(
        ["https://example.com/products/widget"],
        product,
    )

print(response)
```

### JavaScript

```js
import { Makra } from "makra";

const makra = new Makra();
const response = await makra.extract({
  urls: ["https://example.com/products/widget"],
  schema: {
    name: "Product name",
    price: "Current displayed price",
    in_stock: "Whether the product can be purchased",
  },
});

console.log(response);
```

Use a list with one object template for repeated data:

```json
{
  "products": [
    {
      "name": "Product title",
      "price": "Current displayed price",
      "url": "Absolute product URL"
    }
  ]
}
```

## Choose how a workflow returns

| Need | Use | Python | JavaScript |
| --- | --- | --- | --- |
| The result in the current request | Blocking | `extract`, `schema` | `extract`, `schema` |
| Live progress | Streaming | `extract_stream`, `schema_stream` | `extractStream`, `schemaStream` |
| Work that may outlive this process | Deferred | `submit_extract`, `submit_schema` | `submitExtract`, `submitSchema` |

Streams report lifecycle and progress events. They do not contain the final result. Read the run ID from an event and retrieve the stored result after the run reaches a terminal event.

```python
with Makra() as makra:
    run = makra.submit_extract(
        ["https://example.com/products"],
        {"products": [{"name": "Product name", "price": "Current price"}]},
    )

    run.wait()
    result = run.result()
```

Run IDs are durable. Store one with your own job record, then resume it later with `get_run`, `wait_for_run`, `stream_run_events`, or `get_run_result`.

## Repository layout

| Path | Purpose |
| --- | --- |
| [`sdk/python`](sdk/python) | Python package, synchronous and `asyncio` clients, type hints, and tests. |
| [`sdk/javascript`](sdk/javascript) | ESM JavaScript package with TypeScript declarations and tests. |
| [`sdk/SPEC.md`](sdk/SPEC.md) | Language-neutral SDK contract. |
| [`playground`](playground) | Small Python and Node.js scripts for a local API gateway. |

## Work on the SDK locally

Install the Python package in editable mode from this repository:

```bash
python -m pip install -e sdk/python
python playground/python.py https://example.com
```

The Node.js playground imports the local SDK source directly:

```bash
node playground/node.mjs https://example.com
```

Without a URL, either playground script calls `ping` only. Both default to `http://localhost:8080` and the development API key. Override either value with `MAKRA_BASE_URL` or `MAKRA_API_KEY`.

Run package checks from their package directories:

```bash
cd sdk/python && uv run pytest
cd sdk/javascript && npm test && npm run typecheck
```

## Documentation

Read the [Makra SDK documentation](https://docs.makralabs.org/makra-sdk/v0.0.3-beta/getting-started/introduction) for setup, workflow guidance, run management, configuration, and the complete Python and JavaScript references.

Each SDK package also has its own focused README: [Python](sdk/python/README.md) and [JavaScript](sdk/javascript/README.md).

## License

The Python and JavaScript SDK packages are released under the MIT License. See [the Python license](sdk/python/LICENSE) and [the JavaScript license](sdk/javascript/LICENSE).
