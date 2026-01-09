# Makra - Quick Usage

Makra lets you extract structured data from any website with just a few lines of Python. You can extract links, content, run natural language queries, or provide example data or schemas.

First, install the Python SDK (see SDK README for details).

## Basic Usage

```python
from makra import Makra
import asyncio

makra = Makra(api_key="YOUR_API_KEY")

async def main():
    # Crawl a page for links
    links = await makra.crawl(urls=["https://example.com"])

    # Convert a web page to markdown or text
    content = await makra.format(
        urls=["https://example.com"],
        type="markdown/text"
    )

    # Get all repositories with selected fields using a natural language query
    repos = await makra.extract(
        urls=["https://github.com/ritsource"],
        query="Get all the title, link, and language for all repositories."
    )

    # Map a page's structure
    page_map = await makra.page_map(urls=["https://example.com"])

    # Pre-process and annotate a page (extracts content and saves annotations)
    result = await makra.pre_process(
        urls=["https://example.com"]
    )

asyncio.run(main())
```

## Advanced: Use Namespaces & Providers

If you need to specify a custom LLM provider or manage multi-user data separation:

```python
from makra import Makra
import os

makra = Makra(api_key=os.getenv("MAKRA_API_KEY"))
provider = Makra.providers.Groq(api_key="YOUR_GROQ_API_KEY")

ns = makra.namespace(key="user-namespace-123", provider=provider)
result = await ns.extract(
    urls=["https://github.com/ritsource"],
    query="List repository titles and languages."
)
```

> See the SDK examples for more advanced scenarios and options.
