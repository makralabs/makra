"""Extract Y Combinator company directory listings with Rich output."""

from _runner import ExtractExample, run_example

EXAMPLE = ExtractExample(
    title="Y Combinator companies",
    urls=["https://www.ycombinator.com/companies"],
    schema={
        "companies": [
            {
                "company_name": "The display name of the company",
                "company_url": "Link to the company's detail page in the YC directory",
                "location": "The city, state, and country where the company is headquartered",
                "description": "A brief description of what the company does",
                "batch": "The Y Combinator batch the company participated in",
            }
        ]
    },
    config={"crawler": {"post_ready_wait_ms": 8000}},
)


if __name__ == "__main__":
    raise SystemExit(run_example(EXAMPLE))
