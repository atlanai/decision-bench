# Security and data removal

## Report privately

Use GitHub's **Report a vulnerability** button on the Security tab of this repository. It opens a private advisory that only the maintainers can see. Please report there, not in a public issue, if you find:

- a real credential, API key or token anywhere in the repository or its history;
- personal data about a private individual in a row;
- a way for the harness to leak an API key, send it to the wrong host, or write it to a results file.

We aim to acknowledge within 3 working days. Leaked secrets are removed from the tree and, where needed, from history, and we tell you when that's done.

## Data removal requests

Every real row names the public dataset it came from, the record id and the license (see [data/SOURCES.md](data/SOURCES.md)). If you are a rights holder or the subject of a row and want it removed, open an issue with the **Data removal request** template, or report privately as above if the request itself is sensitive. We remove the row in the next corpus version and note the removal in [CHANGELOG.md](CHANGELOG.md). You don't need to prove a legal claim first.

## Secrets in this repository

The harness reads API keys and endpoints only from environment variables or an untracked `.env` file (see `.env.example`). Run records never store keys, endpoint URLs or provider request ids. CI fails if a tracked file contains a key-shaped string, a private hostname or a local home-directory path.

The benchmark rows include code excerpts where the answer is "real credential". Those secrets are replaced with fake values of the same shape before they enter the corpus. None of them works.
