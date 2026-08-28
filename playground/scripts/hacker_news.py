#!/usr/bin/env python3
"""Extract Hacker News story details with the Makra Python SDK.

Run with:
    uv run --project sdk/python python playground/scripts/hacker_news.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

try:
    from makra import PRODUCTION_BASE_URL, Makra
except ModuleNotFoundError as error:
    if error.name == "makra":
        raise SystemExit(
            "The local Makra SDK is not installed for this Python interpreter.\n"
            "Run: uv run --project sdk/python python "
            "playground/scripts/hacker_news.py\n"
            "Or install this checkout into the active environment: "
            "python -m pip install -e sdk/python"
        ) from None
    raise

DEFAULT_URL = "https://news.ycombinator.com"
DOTENV_PATH = Path(__file__).resolve().parents[1] / ".env"
NEWS_SCHEMA = {
    "news_posts": [
        {
            "title": "The title of the news story.",
            "link": "The link to the story source.",
            "comments_count": "The number of comments on the story.",
            "upvotes_count": "The number of upvotes on the story.",
        }
    ]
}


def load_dotenv(path: Path = DOTENV_PATH) -> None:
    """Load simple KEY=VALUE entries without overwriting the shell environment."""
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key.startswith("export "):
            key = key.removeprefix("export ").strip()
        if not key.isidentifier():
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


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
        return (
            "│"
            + "│".join(
                " " + value.ljust(widths[index]) + " "
                for index, value in enumerate(values)
            )
            + "│"
        )

    print(border("┌", "┬", "┐"))
    print(line(headers))
    print(border("├", "┼", "┤"))
    for row in rendered_rows:
        print(line(row))
    print(border("└", "┴", "┘"))


def news_posts_from(data: Any, url: str) -> list[Mapping[str, Any]]:
    """Handle direct and URL-keyed result payloads returned by the API."""
    candidates: list[Any] = []
    if isinstance(data, Mapping):
        candidates.append(data.get("news_posts"))
        page_data = data.get(url)
        if isinstance(page_data, Mapping):
            candidates.append(page_data.get("news_posts"))
        for value in data.values():
            if isinstance(value, Mapping):
                candidates.append(value.get("news_posts"))

    for candidate in candidates:
        if isinstance(candidate, list):
            return [post for post in candidate if isinstance(post, Mapping)]
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
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Extract news posts and usage from Hacker News."
    )
    parser.add_argument("url", nargs="?", default=DEFAULT_URL, help="Hacker News URL")
    parser.add_argument(
        "--base-url",
        default=os.getenv("MAKRA_BASE_URL", PRODUCTION_BASE_URL),
        help="Makra API base URL. Defaults to https://api.makralabs.org.",
    )
    args = parser.parse_args()

    api_key = os.getenv("MAKRA_API_KEY")
    if not api_key:
        print(
            "MAKRA_API_KEY is required. Add it to playground/.env or run: "
            "MAKRA_API_KEY='your-api-key' "
            "python playground/scripts/hacker_news.py",
            file=sys.stderr,
        )
        return 2

    with Makra(api_key=api_key, base_url=args.base_url) as client:
        response = client.extract([args.url], NEWS_SCHEMA)

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

    posts = news_posts_from(response.get("data"), args.url)
    print(f"News posts from {args.url} ({len(posts)} found)")
    if posts:
        print_table(
            ["Title", "Link", "Comments", "Upvotes"],
            [
                [
                    post.get("title"),
                    post.get("link"),
                    post.get("comments_count"),
                    post.get("upvotes_count"),
                ]
                for post in posts
            ],
        )
    else:
        print("No news posts were returned.")

    print("\nUsage")
    print_table(["Metric", "Value"], usage_rows(response.get("usage")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
