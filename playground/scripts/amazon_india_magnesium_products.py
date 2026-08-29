"""Extract Amazon India magnesium supplement listings with Rich output."""

from _runner import ExtractExample, run_example

EXAMPLE = ExtractExample(
    title="Amazon India magnesium products",
    urls=["https://www.amazon.in/s?k=magnesium+supplement"],
    schema={
        "products": [
            {
                "name": "Product name",
                "price": "Listed product price",
                "rating": "Customer rating",
                "review_count": "Number of customer reviews",
                "prime_eligible": "Whether the listing is Prime eligible",
                "product_url": "Amazon product detail page URL",
            }
        ]
    },
    config={},
)


if __name__ == "__main__":
    raise SystemExit(run_example(EXAMPLE))
