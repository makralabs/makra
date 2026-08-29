"""Stream blog archive extraction events and render the final rows."""

from _runner import ExtractExample, run_example

EXAMPLE = ExtractExample(
    title="Blog archive posts",
    urls=[
        "http://paulgraham.com/articles.html",
        "https://www.unqualified-reservations.org/#archive",
        "https://scottaaronson.blog",
        "https://www.astralcodexten.com/archive?sort=new",
    ],
    schema={
        "blogs_posts": [
            {
                "post_id:$anchor": "Unique identifier for the blog post based on date and title",
                "date": "Publication date of the post",
                "title": "Title of the blog post",
                "url:$link": "Link to the individual blog post",
            }
        ]
    },
    config={},
    stream=True,
)


if __name__ == "__main__":
    raise SystemExit(run_example(EXAMPLE))
