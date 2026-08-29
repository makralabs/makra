"""Extract current TechCrunch articles with Rich output."""

from _runner import ExtractExample, run_example

EXAMPLE = ExtractExample(
    title="TechCrunch articles",
    urls=["https://techcrunch.com"],
    schema={
        "articles": [
            {
                "headline": "Article headline",
                "url": "Article URL",
                "summary": "Article excerpt or summary",
                "author": "Author name",
                "published_at": "Displayed publication date and time",
                "category": "Article category",
                "image_url": "Primary article image URL",
            }
        ]
    },
    config={},
)


if __name__ == "__main__":
    raise SystemExit(run_example(EXAMPLE))
