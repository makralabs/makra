"""Extract current Hacker News posts with live Rich output."""

from _runner import ExtractExample, run_example

EXAMPLE = ExtractExample(
    title="Hacker News posts",
    urls=["https://news.ycombinator.com"],
    schema={
        "news_posts": [
            {
                "title": "The title of the news story.",
                "link": "The link to the story source.",
                "comments_count": "The number of comments on the story.",
                "upvotes_count": "The number of upvotes on the story.",
            }
        ]
    },
    config={
        "validation_mode": "observe",
        "pagination": {"enabled": False, "additional_pages": 0},
        "title": {"enabled": True},
    },
)


if __name__ == "__main__":
    raise SystemExit(run_example(EXAMPLE))
