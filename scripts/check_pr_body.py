"""Fail a PR that changes a results/<suite>/<model-id>/ folder without the Results fields of the PR template.

CI runs this on the PR merge commit, so HEAD^1..HEAD is exactly the PR's change. The description is read from the
GitHub event file, never from the command line, so its text never reaches a shell.
"""
import json
import os
import re
import subprocess
import sys

RESULTS_FIELDS = ("Model id", "Endpoint type", "Run dates", "Client location", "Full runs made", "Key type",
                  "Affiliation")
MODEL_FOLDER = re.compile(r"^results/[^/]+/[^/]+/")
HINT = re.compile(r"<!--.*?-->", re.DOTALL)
FIELD = re.compile(r"^[ \t]*-[ \t]*([^:\n]+):[ \t]*(.*)$", re.MULTILINE)


def missing_fields(body, changed_files):
    if not any(MODEL_FOLDER.match(f) for f in changed_files):
        return []
    values = {name.strip(): value.strip() for name, value in FIELD.findall(HINT.sub("", body or ""))}
    return [f for f in RESULTS_FIELDS if not values.get(f)]


def main():
    with open(os.environ["GITHUB_EVENT_PATH"]) as f:
        body = json.load(f)["pull_request"]["body"]
    changed = subprocess.run(["git", "diff", "--name-only", "HEAD^1", "HEAD"], capture_output=True, text=True,
                             check=True).stdout.splitlines()
    missing = missing_fields(body, changed)
    if missing:
        print("This PR changes a results/<suite>/<model-id>/ folder, so fill in these fields under Results in the "
              "PR description: " + ", ".join(missing) + ". See .github/PULL_REQUEST_TEMPLATE.md.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
