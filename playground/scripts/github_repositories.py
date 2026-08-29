"""Backward-compatible name for the ritSource GitHub example."""

from _runner import run_example
from ritsource_github_repositories import EXAMPLE


def main() -> int:
    """Run the retained GitHub repositories entry point."""
    return run_example(EXAMPLE)


if __name__ == "__main__":
    raise SystemExit(main())
