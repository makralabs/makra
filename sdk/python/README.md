# Makra SDK for Python

The official Python SDK for Makra - web scraping and data extraction made simple.

## Installation

```bash
pip install makra
```

## Quick Start

```python
from makra import Makra

# Initialize the client
client = Makra(api_key="your-api-key")

# Extract structured data from URLs
result = await client.extract(
    urls=["https://example.com"],
    query="Extract all product information"
)
```

## Features

- **Simple API**: Easy-to-use async interface for web scraping
- **Schema-based Extraction**: Define schemas to extract structured data
- **Multiple Providers**: Support for various LLM providers (Groq, etc.)
- **Type-safe**: Full type hints and Pydantic models

## Schema-based Extraction

```python
from makra import Makra, SchemaDefinition

client = Makra(api_key="your-api-key")

schema = SchemaDefinition(
    fields={
        "title": {"type": "string", "description": "Product title"},
        "price": {"type": "number", "description": "Product price"},
        "description": {"type": "string", "description": "Product description"},
    }
)

result = await client.extract(
    urls=["https://example.com/products"],
    schema=schema
)
```

## Requirements

- Python 3.12+
- An active Makra API key

## License

MIT License - see [LICENSE](LICENSE) for details.

## Links

- [Documentation](https://docs.makralabs.org)
- [Homepage](https://makralabs.org)
- [GitHub Repository](https://github.com/makralabs/makra-python)
