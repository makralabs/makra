"""Extract Google results for Kandahar Giants with Rich output."""

from _runner import ExtractExample, run_example

EXAMPLE = ExtractExample(
    title="Google Kandahar Giants results",
    urls=["https://www.google.com/search?q=kandahar+giants"],
    schema={
        "search_results": [
            {
                "page_title": "Title of the result page",
                "page_url": "Link for the result page",
            }
        ]
    },
    config={},
)


if __name__ == "__main__":
    raise SystemExit(run_example(EXAMPLE))
