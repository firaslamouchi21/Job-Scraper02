# Contributing

## Development

- Use Docker Compose for local development.
- Keep changes minimal and production-minded.

## Style rules

- No comments or docstrings in source code.
- Prefer clear naming and small functions.

## Pull requests

- Ensure CI passes. It runs the test suite, builds the package and checks it didn't leak flat modules, installs and runs the `job-scraper` console script, and boots the actual Docker images (scraper, UI, and the combined one) and drives a real scrape against them — a green check means the whole thing works, not just that it compiles.
- Include a clear description of the change and why it is needed.
- Small, focused PRs get reviewed faster than one PR doing five things.
