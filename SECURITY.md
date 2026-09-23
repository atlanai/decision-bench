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

The harness reads API keys and endpoints only from environment variables or an untracked `.env` file (see `.env.example`). Configured harness keys and endpoint URLs are redacted before writing run records and again when exporting predictions. Raw local responses can retain provider request ids and other debugging metadata: keep `runs/` private. Redaction is not a guarantee against encoded, transformed, or unknown secrets; inspect output before publication, especially older runs created before a key was rotated.

CI and the Pages build scan tracked and nonignored text files for known credential formats. Third-party data is exempt from hostname, home-path and generic entropy rules, but not recognized provider-key rules. Binary files and files over 20 MB are outside the scanner's coverage. The scanner never prints matched credential values. Review images, new datasets, and Git history separately; a clean heuristic scan is not proof that no secret exists.

The benchmark rows include code excerpts where the answer is "real credential". Those secrets are replaced with fake values of the same shape before they enter the corpus. None of them works.
