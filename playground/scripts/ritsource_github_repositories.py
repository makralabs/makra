"""Extract ritSource GitHub repositories with Rich output."""

from _runner import ExtractExample, run_example

EXAMPLE = ExtractExample(
    title="ritsource GitHub repositories",
    urls=["https://github.com/ritsource?tab=repositories"],
    schema={
        "repositories": [
            {
                "title": "Name of the repository",
                "repository_url": "link to the repository",
                "description": "Description about the repository",
                "language": "Primary programming language used in the repository",
                "forks": "Number of forks in the repository",
                "stars": "Number of starts in the repository",
                "license": "License for the open-source repository",
                "last_updated": "Last update date for the repository",
            }
        ]
    },
    config={},
)


if __name__ == "__main__":
    raise SystemExit(run_example(EXAMPLE))
