#!/usr/bin/env python3
"""Extract GitHub repository details with the Makra Python SDK.

Run with:
    API_KEY="your-api-key" uv run --project sdk/python python playground/scripts/github_repositories.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping, Sequence
from typing import Any

try:
    from makra import DEVELOPMENT_BASE_URL, Makra
except ModuleNotFoundError as error:
    if error.name == "makra":
        raise SystemExit(
            "The local Makra SDK is not installed for this Python interpreter.\n"
            "Run: API_KEY='your-api-key' uv run --project sdk/python python "
            "playground/scripts/github_repositories.py\n"
            "Or install this checkout into the active environment: "
            "python -m pip install -e sdk/python"
        ) from None
    raise


# DEFAULT_URL = "https://github.com/karpathy?tab=repositories"
# REPOSITORY_SCHEMA = {
#     "repositories": [
#         {
#             "title": "The name of the repository.",
#             "repository_url:$link": "The URL of the repository.",
#             "description": "The repository description.",
#             "language": "The primary programming language used in the repository.",
#             "forks": "The number of repository forks.",
#             "stars": "The number of repository stars.",
#             "license": "The license for the open-source repository.",
#             "last_updated": "The date the repository was last updated.",
#         }
#     ]
# }

DEFAULT_URL = "https://hn.algolia.com/?dateRange=all&page=0&prefix=true&query=crispr&sort=byPopularity&type=story"
REPOSITORY_SCHEMA = {
    "news_article": [
      {
        "title": "The title of the news story.",
        "link": "The link to the story source.",
        "comments_count": "The number of comments on the story.",
        "upvotes_count": "The number of upvotes on the story."
      }
    ]
  }

def text(value: Any, limit: int = 48) -> str:
    """Render a cell value in one terminal-friendly line."""
    if value is None:
        rendered = ""
    elif isinstance(value, (dict, list)):
        rendered = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    else:
        rendered = str(value)
    rendered = " ".join(rendered.split())
    return rendered if len(rendered) <= limit else rendered[: limit - 1] + "…"


def print_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> None:
    """Print a compact Unicode table without third-party dependencies."""
    rendered_rows = [[text(value) for value in row] for row in rows]
    widths = [len(header) for header in headers]
    for row in rendered_rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))

    def border(left: str, join: str, right: str, fill: str = "─") -> str:
        return left + join.join(fill * (width + 2) for width in widths) + right

    def line(values: Sequence[str]) -> str:
        return "│" + "│".join(
            " " + value.ljust(widths[index]) + " "
            for index, value in enumerate(values)
        ) + "│"

    print(border("┌", "┬", "┐"))
    print(line(headers))
    print(border("├", "┼", "┤"))
    for row in rendered_rows:
        print(line(row))
    print(border("└", "┴", "┘"))


def repositories_from(data: Any, url: str) -> list[Mapping[str, Any]]:
    """Handle direct and URL-keyed result payloads returned by the API."""
    candidates: list[Any] = []
    if isinstance(data, Mapping):
        candidates.append(data.get("repositories"))
        page_data = data.get(url)
        if isinstance(page_data, Mapping):
            candidates.append(page_data.get("repositories"))
        for value in data.values():
            if isinstance(value, Mapping):
                candidates.append(value.get("repositories"))

    for candidate in candidates:
        if isinstance(candidate, list):
            return [repository for repository in candidate if isinstance(repository, Mapping)]
    return []


def usage_rows(usage: Any) -> list[list[str]]:
    """Flatten nested usage data into key/value rows."""
    if usage is None:
        return [["usage", "No usage details returned"]]
    if not isinstance(usage, Mapping):
        return [["usage", text(usage)]]

    rows: list[list[str]] = []

    def visit(value: Any, path: str) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                visit(child, f"{path}.{key}" if path else str(key))
        else:
            rows.append([path, text(value)])

    visit(usage, "")
    return rows or [["usage", "No usage fields returned"]]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract repository details and usage from a GitHub profile."
    )
    parser.add_argument(
        "url", nargs="?", default=DEFAULT_URL, help="GitHub repositories URL"
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("MAKRA_BASE_URL", DEVELOPMENT_BASE_URL),
        help="Makra API base URL. Defaults to http://localhost:8080.",
    )
    args = parser.parse_args()

    api_key = os.getenv("API_KEY")
    if not api_key:
        print(
            "API_KEY is required. Example: API_KEY='your-api-key' "
            "python playground/scripts/github_repositories.py",
            file=sys.stderr,
        )
        return 2

    with Makra(api_key=api_key, base_url=args.base_url) as client:
        response = client.extract([args.url], REPOSITORY_SCHEMA)

    if not isinstance(response, Mapping):
        print(f"Unexpected API response: {response!r}", file=sys.stderr)
        return 1

    status = response.get("status", "unknown")
    if response.get("success") is False or status not in {"succeeded", "partial"}:
        print(
            f"Extraction failed ({status}): "
            f"{response.get('message', 'No message returned')}",
            file=sys.stderr,
        )
        return 1

    repositories = repositories_from(response.get("data"), args.url)
    print(f"Repositories from {args.url} ({len(repositories)} found)")
    if repositories:
        print_table(
            [
                "Title",
                "Description",
                "Language",
                "Stars",
                "Forks",
                "License",
                "Last updated",
                "Repository URL",
            ],
            [
                [
                    repository.get("title"),
                    repository.get("description"),
                    repository.get("language"),
                    repository.get("stars"),
                    repository.get("forks"),
                    repository.get("license"),
                    repository.get("last_updated"),
                    repository.get("repository_url:$link")
                    or repository.get("repository_url"),
                ]
                for repository in repositories
            ],
        )
    else:
        print("No repositories were returned.")

    print("\nUsage")
    print_table(["Metric", "Value"], usage_rows(response.get("usage")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
