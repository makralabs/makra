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

# Running the Project in Development Mode

## Prerequisites

-   **Docker** and **Docker Compose** installed ([see Docker docs](https://docs.docker.com/get-docker/))
-   **Make** utility (usually available by default on Unix-like systems)
-   Clone this repository and navigate to its root in your terminal

## Available Services

This project is composed of several services managed via `docker-compose.yaml` and invoked conveniently using the provided `Makefile`:

-   **chromadb**: Vector database for embeddings
-   **mongodb**: Document database used for persistent storage
-   **marcus**: One of the server backend services (development mode)
-   **moleman**: Another backend service (development mode, manages browsers)
-   **morpheus**: The primary server (development mode, depends on others)

## How to Start Everything for Local Development

The recommended approach is to spin up **all** services at once:

```sh
make all
```

This command will start every service defined in the Docker Compose file, including databases and app servers, enabling a complete development environment.

---

## Running Specific Service Groups

### To Run Only the Databases

Launches `chromadb` and `mongodb` containers:

```sh
make databases
```

### To Run Only All Server Backends

Starts all backend app services (`marcus`, `moleman`, and `morpheus`):

```sh
make servers
```

### To Start All Morpheus Dependencies

If you want to locally run **morpheus** on your host (not in Docker) but need its required databases and service dependencies:

```sh
make dependencies-for-morpheus
```

This will spin up all the required dependencies for morpheus except the morpheus server itself (so you can run or hot-reload it locally).

---

### Notes

-   All containers run in development mode by default.
-   Hot reloading is enabled for server services.
-   If you need to customize environment variables, check `.env` or the `environment:` sections in `docker-compose.yaml`.

For any custom orchestration, see the `Makefile` and `docker-compose.yaml` for more details.
