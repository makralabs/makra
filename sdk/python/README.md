# Makra Python SDK

The official Python client for the Makra web extraction API.

## Install

```bash
pip install makra
```

For local development from this repository:

```bash
pip install -e sdk/python
```

## Use

```python
from makra import Makra

with Makra(api_key="your-api-key") as client:
    result = client.extract(
        urls=["https://example.com"],
        output_schema={"title": "The page title"},
    )
    print(result)
```

The production API defaults to `https://api.makralabs.org`. To use the local
server:

```python
from makra import DEVELOPMENT_BASE_URL, Makra

client = Makra(api_key="development-key", base_url=DEVELOPMENT_BASE_URL)
```

`AsyncMakra` exposes the same methods for async applications:

```python
from makra import AsyncMakra

async with AsyncMakra(api_key="your-api-key") as client:
    print(await client.ping())
```

Configuration may also be supplied through `MAKRA_API_KEY` and
`MAKRA_BASE_URL`. See [`../SPEC.md`](../SPEC.md) for the complete contract.
