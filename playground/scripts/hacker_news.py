"""Backward-compatible name for the Hacker News stories example."""

from _runner import run_example
from hacker_news_stories import EXAMPLE


def main() -> int:
    """Run the retained Hacker News entry point."""
    return run_example(EXAMPLE)


if __name__ == "__main__":
    raise SystemExit(main())
