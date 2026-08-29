"""Backward-compatible name for the 1mg medicines example."""

from _runner import run_example
from one_mg_medicines import EXAMPLE


def main() -> int:
    """Run the retained medicines entry point."""
    return run_example(EXAMPLE)


if __name__ == "__main__":
    raise SystemExit(main())
