# Makra

Makra is an AI-powered web scraping and data extraction platform that simplifies extracting structured data from websites using natural language queries or JSON schemas. The platform consists of multiple microservices including browser automation, embedding services, and intelligent data extraction powered by LLMs.

## Architecture

- **Morpheus**: Main AI-powered extraction service with agents, workflows, and API endpoints
- **Marcus**: FastAPI service providing text embeddings using sentence-transformers
- **Moleman**: Browser automation service using Playwright for web scraping
- **SDK**: Python SDK for easy integration and usage
- **Clients**: JavaScript/Node.js client-side components

## Quick Start

See individual service READMEs for setup instructions. Use `uv` for fast Python dependency management and virtual environments.

