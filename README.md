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
-   **marcus**: Local text-embedding service used by the development configuration
-   **morpheus_js_build**: One-shot build of the JavaScript bundle that Morpheus injects into browser pages
-   **morpheus**: The primary API and Playwright browser-pool server
-   **telemetry_web_build**: One-shot Vite build of the telemetry web application
-   **telemetry**: Go server that serves telemetry APIs and the built web application

Morpheus owns its Playwright browser pool in-process. There is no separate Moleman container.

## Local environment

Compose uses the existing package-level environment files. It does not forward the entire host environment.

The following files provide service credentials and provider settings:

- `packages/shared/libutils/config/.env` is supplied to Marcus and Morpheus. It holds Morpheus service, provider, proxy, and optional S3 settings.
- `packages/telemetry/.env` is supplied to telemetry after the shared settings. It holds Clerk and telemetry authorization settings and may override a shared value when necessary.

Morpheus receives its Docker-network addresses (`mongodb`, `chromadb`, and `marcus`) directly from Compose. Telemetry receives the private `http://morpheus:6900` bridge address directly from Compose. Those internal coordinates intentionally override any host-local values in the environment files.

MongoDB credentials default to the local-only `admin` / `password` pair. Set `MONGO_USER` and `MONGO_PASSWORD` in the shell to override both Mongo initialization and Morpheus's connection settings.

Validate the Compose syntax before starting:

```sh
make compose-config
```

## How to Start Everything for Local Development

The recommended approach is to spin up **all** services at once:

```sh
make all
```

This builds both frontend artifacts and starts every service in dependency order. MongoDB, ChromaDB, Marcus, Morpheus, and telemetry each have readiness checks; Morpheus waits for its databases, Marcus, and JavaScript bundle, while telemetry waits for Morpheus and its Vite bundle.

For a detached stack:

```sh
make all ARGS=-d
```

Local endpoints are available only on loopback:

- `http://127.0.0.1:6900/ready` — Morpheus readiness
- `http://127.0.0.1:6910/ping` — Marcus health
- `http://127.0.0.1:6940/telemetry` — telemetry UI
- `http://127.0.0.1:6940/telemetry/api/v1/health` — telemetry health
- `127.0.0.1:8000` — ChromaDB diagnostics
- `127.0.0.1:27017` — MongoDB diagnostics

---

## Running Specific Service Groups

### To Run Only the Databases

Launches `chromadb` and `mongodb` containers:

```sh
make databases
```

### To Run Only All Server Backends

Builds the two frontend artifacts and starts Marcus, Morpheus, and telemetry. Compose also starts their database dependencies:

```sh
make servers
```

## Operations

Inspect service state and logs with:

```sh
docker compose ps
docker compose logs -f morpheus telemetry
```

Stop the stack with `docker compose down`. This preserves MongoDB, ChromaDB, and telemetry data in their host-mounted directories. Avoid `docker compose down -v` unless intentionally discarding generated build volumes.

For any custom orchestration, see the `Makefile` and `docker-compose.yaml` for more details.
