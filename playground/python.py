"""Small local playground for the Makra Python SDK."""

import argparse
import json
import os

from makra import DEVELOPMENT_BASE_URL, DUMMY_API_KEY, Makra


def main() -> None:
    parser = argparse.ArgumentParser(description="Try the Makra Python SDK")
    parser.add_argument(
        "url",
        nargs="?",
        help="Optional URL to extract. Without it, the script only pings Makra.",
    )
    args = parser.parse_args()

    base_url = os.getenv("MAKRA_BASE_URL", DEVELOPMENT_BASE_URL)
    api_key = os.getenv("MAKRA_API_KEY", DUMMY_API_KEY)

    with Makra(api_key=api_key, base_url=base_url) as client:
        print("ping:", json.dumps(client.ping(), indent=2))
        if args.url:
            result = client.extract(
                urls=[args.url],
                schema={
                    "title": "The page title",
                    "description": "A short description of the page",
                },
                config={
                    "validation_mode": "repair",
                    "memory": {"enabled": True, "selector_chain_version": "v2"},
                },
            )
            print("extract:", json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
