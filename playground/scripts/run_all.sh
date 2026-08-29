#!/usr/bin/env bash

# Run every production playground example sequentially. Each Python script loads
# MAKRA_API_KEY from playground/.env itself; an exported value takes precedence.

set -uo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/../.." && pwd)"

examples=(
  amazon_india_magnesium_products.py
  blog_archive_posts.py
  github_repositories.py
  google_kandahar_giants_results.py
  hacker_news.py
  hacker_news_posts.py
  hacker_news_stories.py
  medicines.py
  one_mg_medicines.py
  ritsource_github_repositories.py
  techcrunch_articles.py
  ted_talks.py
  y_combinator_companies.py
)

if [[ -z "${MAKRA_API_KEY:-}" && ! -f "$repo_root/playground/.env" ]]; then
  echo "MAKRA_API_KEY is not set and $repo_root/playground/.env does not exist." >&2
  exit 2
fi

runner=(uv run --project "$repo_root/sdk/python" --extra playground python)
failed=()

for example in "${examples[@]}"; do
  echo
  echo "===== Running $example ====="
  if "${runner[@]}" "$script_dir/$example" "$@"; then
    echo "===== Completed $example ====="
  else
    status=$?
    echo "===== Failed $example (exit $status) =====" >&2
    failed+=("$example")
  fi
done

if ((${#failed[@]})); then
  echo >&2
  echo "Failed examples: ${failed[*]}" >&2
  exit 1
fi

echo
echo "All ${#examples[@]} examples completed successfully."
