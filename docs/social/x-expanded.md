Can a small model make the decisions inside your AI agent?

I built Decision Bench to find out.

1,071 real-world cases. 35 tasks. 11 use cases. 12 models.

The decisions software keeps asking LLMs to make:

→ Tool calling: which function should the agent use?
→ Routing: which team owns this support ticket?
→ Grounding: does the cited evidence actually support the answer?
→ Security: is this a prompt injection or a normal request?
→ Code: is this diff a fix, feature, or refactor?
→ Documents: which receipt number is the total? Does this contract contain the clause?
→ Data: which SQL query answers the question? Does this chart support the claim?

Measured across accuracy, confidence calibration, latency, and cost.

The interesting part is where models stumble:

1. Predicting the winning headline
All 12 chose B in one historical A/B test. A actually earned 1.52% CTR vs B’s 0.71%. Models saw the content, not the click counts. A reminder to test audience behavior.

2. Checking citations
11 of 12 accepted an answer HAGRID annotators marked unsupported. The issue was a claim its cited passage didn’t establish. Plausible isn’t the same as grounded.

3. Extracting action items
All 12 disagreed with one AMI action-item label: 11 said “neither,” one said “decision.” The wording is ambiguous. Shared misses can expose problems in the evaluation too.

These are individual examples, not task-wide failure rates.

The question I care about: how much model does each decision actually need?

An open benchmark for practical LLM evals, small models, and AI agents.

[launch link]

---
Attachment order: accuracy-latency.png, failure-examples.png.

Evidence: local results/bench-v4/*/predictions.jsonl and scores.json; frozen data/corpus/bench-v4/cases.jsonl. Snapshot 2026-09-23. Graph generation: build_graphs.py. Input modalities and provider setups differ; overlapping accuracy intervals do not establish a winner. Replace the launch-link placeholder before posting.
