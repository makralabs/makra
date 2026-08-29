"""Extract 1mg medicine listings with Rich output."""

from _runner import ExtractExample, run_example

EXAMPLE = ExtractExample(
    title="1mg medicines",
    urls=["https://www.1mg.com/drugs-all-medicines?page=1&label=a"],
    schema={
        "medicines": [
            {
                "name": "The name of the medicine",
                "manufacturer": "The name of the medicine manufacturer",
                "composition": "Salt composition of the medicine",
                "price": "MRP/Price for the medicine",
                "prescription_required": "Describes of prescription is required or not",
            }
        ]
    },
    config={},
)


if __name__ == "__main__":
    raise SystemExit(run_example(EXAMPLE))
