# Tutorial: make your first structured web extraction

You will send one product page to Makra and get structured product data back. The API receives a target shape, rather than a strict JSON Schema: strings such as `"Product name"` tell the extraction workflow what each field means.

For the broader map of the package, see the [reading guide](112137-python-sdk-reading-guide.md). For every configurable field, see the [reference](112137-python-sdk-reference.md).

## What you need

- Python 3.9 or later.
- A Makra API key for the environment you intend to call.
- The `makra` package installed with `pip install makra`.

Set the key in your shell so it is not hard-coded in source:

```bash
export MAKRA_API_KEY="your-api-key"
```

## Step 1: submit a blocking extraction

Create `extract_product.py`:

```python
from makra import Makra

url = "https://example.com/products/widget"
schema = {
    "name": "Product name",
    "price": "Current displayed price",
    "in_stock": "Whether the item can be purchased",
}

with Makra() as client:
    response = client.extract([url], schema)

print(response)
```

Run it:

```bash
python extract_product.py
```

`response` is the complete successful API body. For example, if the API returns an envelope, access its fields as returned rather than assuming the SDK has unwrapped it:

```python
if isinstance(response, dict) and response.get("success"):
    extracted = response.get("data")
    print(extracted)
```

That is a working result in one request. The connection remains open until the workflow reaches its terminal response, so blocking mode is the simplest choice only when the caller can wait.

## Step 2: extract a list of repeated objects

Use a list containing one object template when the page has a repeated collection:

```python
from makra import Makra

schema = {
    "products": [
        {
            "name": "Product title",
            "price": "Price as displayed",
            "url": "Absolute product URL",
        }
    ]
}

with Makra() as client:
    response = client.extract(
        ["https://example.com/category/widgets"],
        schema,
        config={"validation_mode": "repair"},
    )

print(response)
```

Use `ValidationModes.REPAIR` rather than the literal if you want the value to be self-documenting. `repair` asks the workflow to repair output that fails validation; `observe` is the other accepted mode.

## Step 3: discover a schema before writing one

Use schema discovery when you are exploring a new page or want a candidate extraction shape:

```python
from makra import Makra

with Makra() as client:
    page_schema = client.schema("https://example.com/category/widgets")

print(page_schema)
```

Pass `only_memoized=True` when you specifically want a schema built from Makra's memoized knowledge for that page:

```python
page_schema = client.schema(
    "https://example.com/category/widgets",
    only_memoized=True,
)
```

## What you built

You can now make a synchronous extraction, shape repeated records, and ask the service to discover a page schema. Move to the [workflow guide](112137-python-sdk-workflows.md) when a run needs live progress or must continue after the current process exits. For production configuration, timeouts, pagination, and proxy targeting, use the [reference](112137-python-sdk-reference.md).

## Async equivalent

In an `asyncio` application, make the same calls with `AsyncMakra`:

```python
import asyncio
from makra import AsyncMakra

async def main() -> None:
    async with AsyncMakra() as client:
        response = await client.extract(
            ["https://example.com/products/widget"],
            {"name": "Product name", "price": "Current price"},
        )
        print(response)

asyncio.run(main())
```

Do not use `await` with `Makra`, and do not call blocking `Makra` methods from an async event loop if that would block other application work.
