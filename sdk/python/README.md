# Makra SDK for Python

The official Python SDK for Makra - web scraping and data extraction made simple.

## Installation

```bash
pip install makra
```

## Quick Start

```python
from makra import Makra

makra = Makra(api_key="your-api-key")

# Extract data with a query
result = await makra.extract(
    urls=["https://example.com"],
    query="Get all product titles and prices"
)
```

## Features

-   **Simple API**: Easy-to-use async interface for web scraping
-   **Schema-based Extraction**: Define JSON schemas to extract structured data
-   **Query-based Extraction**: Use natural language to describe what to extract
-   **Multiple Output Formats**: Get content as markdown or plain text
-   **Multiple Providers**: Support for various LLM providers (Groq, Google AI)
-   **Type-safe**: Full type hints and Pydantic models
-   **Crawling**: Discover and extract links from pages
-   **Page Mapping**: Get structured maps of page content

## API Reference

### Initialize Client

```python
from makra import Makra

makra = Makra(api_key="your-api-key")
```

With custom base URL:

```python
makra = Makra(
    api_key="your-api-key",
    base_url="https://custom-api.example.com",
    api_version="v1"
)
```

### Extract Data

**Using a JSON schema:**

```python
schema = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "price": {"type": "number"}
    }
}

result = await makra.extract(
    urls=["https://example.com/products"],
    schema=schema
)
```

**Using a natural language query:**

```python
result = await makra.extract(
    urls=["https://example.com/products"],
    query="Get all product titles and prices"
)
```

**With actions (navigation, pagination):**

```python
from makra import enums

result = await makra.extract(
    urls=["https://example.com"],
    schema=schema,
    actions=[enums.ACTION.NAVIGATION, enums.ACTION.PAGINATION]
)
```

**With extract options:**

```python
from makra import types

options = types.ExtractOptions(
    disable_cache=True,
    disable_pagination=False
)

result = await makra.extract(
    urls=["https://example.com"],
    query="Get products",
    options=options
)
```

### Format Content

**As markdown:**

```python
content = await makra.format(
    urls=["https://example.com"],
    type="markdown"
)
```

**As text:**

```python
content = await makra.format(
    urls=["https://example.com"],
    type="text"
)
```

**Using enum:**

```python
from makra import enums

content = await makra.format(
    urls=["https://example.com"],
    type=enums.FORMAT_TYPE.MARKDOWN
)
```

### Crawl URLs

```python
links = await makra.crawl(urls=["https://example.com"])
```

**With options:**

```python
from makra import types

options = types.CrawlOptions()
links = await makra.crawl(
    urls=["https://example.com"],
    options=options
)
```

### Page Map

```python
page_map = await makra.page_map(urls=["https://example.com"])
```

### Pre-process

```python
result = await makra.pre_process(urls=["https://example.com"])
```

**With options:**

```python
from makra import types

options = types.PreprocessOptions()
result = await makra.pre_process(
    urls=["https://example.com"],
    options=options
)
```

### Ping API

```python
status = await makra.ping()
```

## Using Providers

**With Groq:**

```python
from makra import Makra, providers

groq_provider = providers.Groq(api_key="your-groq-api-key")

makra = Makra(
    api_key="your-makra-api-key",
    provider=groq_provider
)
```

**With Google AI:**

```python
from makra import Makra, providers

google_provider = providers.GoogleAI(api_key="your-google-api-key")

makra = Makra(
    api_key="your-makra-api-key",
    provider=google_provider
)
```

**Custom model:**

```python
groq_provider = providers.Groq(
    api_key="your-groq-api-key",
    model="llama-3-70b-8192"
)
```

## Types and Enums

**Import types:**

```python
from makra import types

options = types.ExtractOptions(disable_cache=True)
```

**Import enums:**

```python
from makra import enums

# Format types
enums.FORMAT_TYPE.MARKDOWN
enums.FORMAT_TYPE.TEXT

# Actions
enums.ACTION.NAVIGATION
enums.ACTION.PAGINATION
```

## Error Handling

```python
from makra.errors import RequestError

try:
    result = await makra.extract(urls=["https://example.com"], query="...")
except RequestError as e:
    print(f"Error {e.status_code}: {e.message}")
```

## Requirements

-   Python 3.12+
-   An active Makra API key

## License

MIT License - see [LICENSE](LICENSE) for details.

## Links

-   [Documentation](https://docs.makralabs.org)
-   [Homepage](https://makralabs.org)
-   [GitHub Repository](https://github.com/makralabs/makra-python)
