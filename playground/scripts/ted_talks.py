"""Extract TED talk metadata with Rich output."""

from _runner import ExtractExample, run_example

EXAMPLE = ExtractExample(
    title="TED talks",
    urls=["https://www.ted.com/talks"],
    schema={
        "speaker": "Speaker name",
        "talk_title": "Talk title",
        "topic": "Talk topic or subject",
        "published_date": "Published date if shown",
        "duration": "Talk duration if shown",
        "description": "Published talk summary",
        "talk_url": "Canonical talk URL",
    },
    config={
        "validation_mode": "observe",
        "pagination": {"enabled": False, "additional_pages": 0},
        "title": {"enabled": True},
    },
)


if __name__ == "__main__":
    raise SystemExit(run_example(EXAMPLE))
