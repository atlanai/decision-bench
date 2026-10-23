"""The PR description check the way CI runs it: a checkout whose HEAD is the PR merge commit and the GitHub event file."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts/check_pr_body.py"
TEMPLATE = (ROOT / ".github/PULL_REQUEST_TEMPLATE.md").read_text()
FILLED = {
    "Model id": "example-model",
    "Endpoint type": "hosted API, called directly",
    "Run dates": "20 Oct",
    "Client location": "us-east-1",
    "Full runs made": "1 (1,003 correct), published",
    "Key type": "normal customer key",
    "Affiliation": "none",
}


def git(repo, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false",
                    "-c", "core.hooksPath=/dev/null", *args], cwd=repo, check=True, capture_output=True)


def check(changed_file, body):
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        git(repo, "init", "-q")
        (repo / "README.md").write_text("base\n")
        git(repo, "add", ".")
        git(repo, "commit", "-qm", "base")
        (repo / changed_file).parent.mkdir(parents=True, exist_ok=True)
        (repo / changed_file).write_text("change\n")
        git(repo, "add", ".")
        git(repo, "commit", "-qm", "pr")
        event = repo / "event.json"
        event.write_text(json.dumps({"pull_request": {"body": body}}))
        return subprocess.run([sys.executable, str(SCRIPT)], cwd=repo, capture_output=True, text=True,
                              env={**os.environ, "GITHUB_EVENT_PATH": str(event)})


def filled_template(**overrides):
    """The template with every Results field filled in front of its hint, the way a contributor usually types it."""
    body = TEMPLATE
    for field, value in {**FILLED, **overrides}.items():
        body = body.replace(f"- {field}:", f"- {field}: {value}", 1)
    return body


class PullRequestBody(unittest.TestCase):
    def test_results_pr_with_the_template_unfilled_names_every_missing_field(self):
        out = check("results/bench-v4/example-model/metadata.json", TEMPLATE)
        self.assertEqual(out.returncode, 1)
        for field in FILLED:
            self.assertIn(field, out.stdout)

    def test_results_pr_with_the_fields_filled_passes(self):
        out = check("results/bench-v4/example-model/metadata.json", filled_template())
        self.assertEqual(out.returncode, 0, out.stdout)

    def test_a_value_typed_after_the_hint_counts(self):
        hint = next(line for line in TEMPLATE.splitlines() if line.startswith("- Endpoint type:"))
        lines = [hint + " OpenRouter" if line.startswith("- Endpoint type:") else line
                 for line in filled_template().splitlines()]
        body = "\n".join(lines)
        out = check("results/bench-v4/example-model/metadata.json", body)
        self.assertEqual(out.returncode, 0, out.stdout)

    def test_results_pr_with_one_field_left_as_its_hint_fails_on_that_field(self):
        out = check("results/bench-v4/example-model/metadata.json", filled_template(**{"Client location": ""}))
        self.assertEqual(out.returncode, 1)
        self.assertIn("Client location", out.stdout)
        self.assertNotIn("Affiliation", out.stdout)

    def test_results_pr_with_no_description_fails_and_names_the_fields(self):
        out = check("results/bench-v4/example-model/predictions.jsonl", None)
        self.assertEqual(out.returncode, 1)
        self.assertIn("Model id", out.stdout)

    def test_pr_that_does_not_touch_results_needs_no_results_fields(self):
        out = check("decision_bench/runner.py", None)
        self.assertEqual(out.returncode, 0, out.stdout)

    def test_pr_that_only_edits_the_results_guide_needs_no_results_fields(self):
        out = check("results/README.md", None)
        self.assertEqual(out.returncode, 0, out.stdout)


if __name__ == "__main__":
    unittest.main()
