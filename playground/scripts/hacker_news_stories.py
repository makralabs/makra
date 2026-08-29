"""Extract Hacker News stories with Rich output."""

from _runner import ExtractExample, run_example

EXAMPLE = ExtractExample(
    title="Hacker News stories",
    urls=["https://news.ycombinator.com"],
    schema={
        "news": [
            {
                "title": "Title of the news/story",
                "link": "Link to the source",
                "comments_count": "Number of comments in the news/story",
                "upvotes_count": "Number of upvotes in the news/story",
            }
        ]
    },
    config={},
)


if __name__ == "__main__":
    raise SystemExit(run_example(EXAMPLE))
