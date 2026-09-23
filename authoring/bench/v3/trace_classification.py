"""Trace classification (TC-1, TC-2, TC-3): say what went wrong in a real agent run, and where.

TC-1  What kind of failure happens at this step?   AgentRx benchmark (Microsoft, MIT), human annotators
TC-2  Which agent caused the failure?              Who&When (MIT on GitHub), human annotators
TC-3  Did this coding-agent run fix the issue?     nebius/SWE-agent-trajectories (CC BY 4.0), the repository's tests

Every row is a real record. The state is the record itself, trimmed so a reader can take it in quickly: long
text keeps a head and a tail with an explicit "…[N chars truncated]" marker; nothing is rewritten. Sampling is
deterministic (`rank`) and uses no model output. The written rules for each task are in the docstring of its
builder (_tc1, _tc2, _tc3).

TC-1 source change: TC-1 used to sample TRAIL (Patronus AI). TRAIL's GitHub copy is MIT, but its Hugging Face
release is gated with the request that users "not reshare this dataset outside of a gated or private
repository". To respect that wish, every TRAIL row, file and declaration was removed. TC-1 now uses the AgentRx
benchmark (Barke et al. 2026): failed τ-bench retail runs and Magentic-One runs whose failure steps three
human annotators labelled with a grounded failure taxonomy. Candidates checked and not used are listed in _tc1.

GAIA rule (public repository): GAIA's authors ask that its questions not be reshared in plain, crawlable form.
No row of this module shows a GAIA question: TC-1 uses only AgentRx's Magentic-One runs of AssistantBench tasks
(its runs of GAIA tasks are not fetched) and τ-bench runs; TC-2 uses only Who&When logs of AssistantBench tasks
(Apache-2.0), because in its GAIA logs the agents restate the question throughout. TC-3 has no GAIA data.

Code in the rows: SWE-agent rows (TC-3) show issue text, repository code and patches. Every such row's
repository license was read on GitHub and is recorded in REPO_LICENSES (and in the row's source as code_license);
the build fails on a repository that is not listed, and a repository whose license is not in PERMISSIVE_CODE may not
be listed. All repositories used are MIT, Apache-2.0, BSD-2-Clause or BSD-3-Clause. Licenses and terms of each
dataset, and of the text inside it, are declared in `_datasets`.
"""
from __future__ import annotations

import collections
import json
import re
import urllib.parse

from . import dataset, task, row, rank, ROWS, SOURCES as SOURCE_DIR

MARK = "…[{} chars truncated]"

# ---------------------------------------------------------------- sources

AGENTRX_COMMIT = "7a18c79708e7671be15124460f4f7296107c2a55"
AGENTRX_RAW = f"https://raw.githubusercontent.com/microsoft/AgentRx/{AGENTRX_COMMIT}"
# AgentRx's Magentic-One runs fetched: the ones whose task is an AssistantBench task (trajectory id = the task's
# 64-hex AssistantBench id, all in the AssistantBench dev set, Hugging Face revision 482cbbc0), except the four
# runs that are also TC-2 rows (Who&When Hand-Crafted 4, 6, 48, 57: same logs, checked in define()). The other 22
# annotated Magentic-One runs are of GAIA tasks and are not fetched (see the GAIA rule above).
AGENTRX_MAGENTIC = """
    c7afe00869f98cf363fd83677ac41757ed5e57f03eacc3d1304feb0a92084bd1 52f7224e9c79431e7926afe317782711a0028750693e7456cde22ef6f4bd8bd5
    ccec2229ced20a4b0cb4897e3a99120a3017ea030903e01c9bda6b13d40b0b14 6b06d186921b8b390c65aebd0d16f09f60a47d2f1288ebe36953f734e84c0a3c
    8ad84bd6fe38481ba49e7ad1f6fbd43219a999074e5c6fc940003281f55ec65b 2ddae3b7a208e3c25f14d82d7a1faaaa1832fbf950b4dac345e755c4c361f294
    0ec4371851b96837b0a81b3dd3df401415061bb532fbafeb4609f3337c358508 6e3be83d1949fa52cba03fb1ce4b5b3bf7e37a83fd7d67694b10b2e439d90cf8
    797f7a5b65ca28b7e7156e7db1e9f117bd4a021de0cd512bfdbb0be897d89eab 55f4258484c5b398956133128a50462a767da211f8f72aa5ac5bbffb9bcbba1a
    557e78eceec08ca8b0da5f9fdaca6e1c7ec6140a8ce600983ee716327dab005e 929b45f34805280d77c61d1e093e3d4e551d77ddb6ecd73552b12b1af286388d
    748899d9d70c09beb3bd48ac8a3658bdcfd2f9114fe6dc4c4b8d2f9541ef4607 9baaa267c95f9d8b75741ee9169c50563d297cfa592c20deaffd30dbc5984c74
    b36ef2d8f2643b80e74a44ce3403f674ecb2aed7fd36afeaa289061a59feef92 9e31099fffa6a3891c94934fd4fc2f3f522d51c1904ff3561f3a10e4bf245821
    57d9dc6935e8a40b02e7f8ec81768fe70e68a0c05f6866927c9fda38db38a486 a9074997e698f912b9e751779ea19c1e92fa148404e90e0ae997acea3f9559b0
""".split()


def _q(path):
    return urllib.parse.quote(path)


SOURCES = [
    {"dataset": "AgentRx", "url": f"{AGENTRX_RAW}/LICENSE.txt", "path": "agentrx/LICENSE"},
    {"dataset": "AgentRx, τ-bench labels", "url": f"{AGENTRX_RAW}/data/ground_truth/tau_ground_truth.json",
     "path": "agentrx/tau_ground_truth.json"},
    {"dataset": "AgentRx, τ-bench runs", "url": f"{AGENTRX_RAW}/data/tau_retail/tau_dataset_failed.json",
     "path": "agentrx/tau_dataset_failed.json"},
    {"dataset": "AgentRx, Magentic-One labels", "url": f"{AGENTRX_RAW}/data/ground_truth/magentic_one_ground_truth.json",
     "path": "agentrx/magentic_one_ground_truth.json"},
    *({"dataset": "AgentRx, Magentic-One run", "url": f"{AGENTRX_RAW}/data/magentic_dataset/{t}.json",
       "path": f"agentrx/magentic_dataset/{t}.json"} for t in AGENTRX_MAGENTIC),
]

WW_COMMIT = "b2bae5c5b06d681d04ea5e9b63b7a30525c04925"
WW_RAW = f"https://raw.githubusercontent.com/mingyin1/Agents_Failure_Attribution/{WW_COMMIT}"
# Who&When logs fetched: the AssistantBench-task logs (question_ID of 64 hex digits) of at most 40,000
# bytes at WW_COMMIT (sizes from the GitHub tree listing), so that turns need little trimming. GAIA-task
# logs are not used: GAIA's authors ask that its questions not be reshared in plain text, and in these
# logs every agent restates the question, so no redaction of the question alone would hide it.
WW_FILES = {
    "Algorithm-Generated": [99, 100, 101, 102, 103, 104, 105, 106, 107, 109, 111, 112, 113, 114, 115, 116, 117,
                            118, 119, 120, 121, 122, 123, 124, 125, 126],
    "Hand-Crafted": [1, 4, 6, 16, 28, 31, 32, 40, 48, 52, 57],
}
SOURCES += [
    {"dataset": "Who&When", "url": f"{WW_RAW}/LICENSE", "path": "whoandwhen/LICENSE"},
    *({"dataset": f"Who&When, {sub}", "url": f"{WW_RAW}/{_q(f'Who&When/{sub}/{n}.json')}",
       "path": f"whoandwhen/{sub}/{n}.json"} for sub, ns in WW_FILES.items() for n in ns),
]

# nebius/SWE-agent-trajectories (80,036 rows, 5.3 GB): only TC3_WINDOWS small windows of TC3_WINDOW
# consecutive rows, at offsets spread evenly over the dataset, are fetched through the datasets-server rows
# API (dataset revision 68195a1450865274106246d0d0296a1d6807b88e at the time of fetching).
SWE_ROWS = ("https://datasets-server.huggingface.co/rows?dataset=nebius/SWE-agent-trajectories&config=default"
            "&split=train&offset={offset}&length={length}")
SWE_TOTAL, TC3_WINDOWS, TC3_WINDOW = 80036, 64, 2
SWE_OFFSETS = [k * SWE_TOTAL // TC3_WINDOWS for k in range(TC3_WINDOWS)]
SOURCES += [{"dataset": "nebius/SWE-agent-trajectories, rows API window",
             "url": SWE_ROWS.format(offset=o, length=TC3_WINDOW), "path": f"swe-agent-trajectories/rows-{o:05d}.json"}
            for o in SWE_OFFSETS]


# Repository -> license (SPDX) of the GitHub repositories whose issues, code or patches appear in TC-3 rows, read
# from each repository's license file on GitHub (github.com/<repo>/blob/HEAD/LICENSE*).
REPO_LICENSES = {
    "pvlib/pvlib-python": "BSD-3-Clause", "mlrun/mlrun": "Apache-2.0",
    "mkaz/termgraph": "MIT", "iterative/dvc": "Apache-2.0", "Parquery/icontract": "MIT",
    "zalando-stups/senza": "Apache-2.0", "fetzerch/kasserver": "MIT", "e2nIEE/pandapipes": "BSD-3-Clause",
    "AmiiThinks/driving_gridworld": "MIT", "pydantic/pydantic": "MIT", "lidatong/dataclasses-json": "MIT",
    "asottile/yesqa": "MIT", "snowblink14/smatch": "MIT", "level12/morphi": "BSD-3-Clause",
    "yukinarit/pyserde": "MIT", "haddocking/arctic3d": "Apache-2.0", "kytos/python-openflow": "MIT",
    "praw-dev/prawcore": "BSD-2-Clause", "docker/docker-py": "Apache-2.0", "scikit-hep/cabinetry": "BSD-3-Clause",
    "andialbrecht/sqlparse": "BSD-3-Clause", "asottile/babi": "MIT", "globocom/m3u8": "MIT",
    "scrapy/w3lib": "BSD-3-Clause",
}
PERMISSIVE_CODE = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "CC0-1.0"}
assert set(REPO_LICENSES.values()) <= PERMISSIVE_CODE


def _code_license(repo, where):
    if repo not in REPO_LICENSES:
        raise KeyError(f"{where}: read and record the license of {repo} in REPO_LICENSES")
    return REPO_LICENSES[repo]


def _datasets():
    dataset(id="agentrx", name="AgentRx benchmark", tasks=["TC-1"],
            homepage="https://github.com/microsoft/AgentRx", license="MIT",
            license_url=f"https://github.com/microsoft/AgentRx/blob/{AGENTRX_COMMIT}/LICENSE.txt",
            content="Failed agent runs with the failure steps marked: τ-bench retail customer-service chats (a "
                    "gpt-4o agent with the store's tools, a simulated customer, the store policy and the customer's "
                    "hidden instructions) and Magentic-One multi-agent runs on AssistantBench web tasks (the same "
                    "logs as Who&When's Hand-Crafted set), with the text the agents read from web pages and tools.",
            content_license="MIT",
            content_terms="The GitHub repository (the copy used) is MIT (\"Copyright (c) Microsoft Corporation\"). "
                          "The Hugging Face copy (microsoft/AgentRx) is CC BY 4.0 and asks visitors to share contact "
                          "details before downloading; it states no other condition, and it was not used (its terms "
                          "were not accepted). τ-bench (sierra-research/tau-bench) is MIT; its retail customers, "
                          "orders and products are synthetic. The Magentic-One logs come from Who&When (MIT) and "
                          "their tasks from AssistantBench (Apache-2.0, "
                          "https://huggingface.co/datasets/AssistantBench/AssistantBench); they quote short snippets "
                          "of third-party web pages (search results, business listings) that the agents retrieved. "
                          "The agent turns are gpt-4o outputs.",
            labelled_by="AgentRx's human annotators (three annotators, grounded-theory coding; mean pairwise Cohen's "
                        "kappa 0.89 reported in the paper)",
            changes="Categories are mapped to six options (TC1_CATEGORY). The transcript runs up to one turn after "
                    "the reviewed step; long turns are cut to a head and a tail with \"…[N chars truncated]\" "
                    "marked (the same cap for every turn but the reviewed one), and long Magentic-One runs show the "
                    "task, the plan and the turns just before the step, with the omitted turns marked. Nothing is "
                    "rewritten.",
            selection="Failure steps whose category maps to an option and whose label passes the re-checks in _tc1 "
                      "(right speaker, visible evidence, read by hand), in sha256 order, scarcest option first, at "
                      "most 5 per option, one row per run and per τ-bench customer (two for the scarcest option).",
            citation="Barke et al., AgentRx: Diagnosing AI Agent Failures from Execution Trajectories, "
                     "arXiv:2602.02475, 2026. Runs from τ-bench (Yao et al., 2024) and Who&When (Zhang et al., 2025).",
            bibtex="""@article{barke2026agentrx,
  title   = {{AgentRx}: Diagnosing {AI} Agent Failures from Execution Trajectories},
  author  = {Barke, Shraddha and Goyal, Arnav and Khare, Alind and Singh, Avaljot and Nath, Suman and Bansal, Chetan},
  journal = {arXiv preprint arXiv:2602.02475},
  year    = {2026},
  url     = {https://arxiv.org/abs/2602.02475}
}""")

    dataset(id="whoandwhen", name="Who&When", tasks=["TC-2"],
            homepage="https://github.com/mingyin1/Agents_Failure_Attribution", license="MIT",
            license_url=f"https://github.com/mingyin1/Agents_Failure_Attribution/blob/{WW_COMMIT}/LICENSE",
            content="Logs of failed runs of LLM multi-agent teams (CaptainAgent-built AutoGen groups and "
                    "Magentic-One) on AssistantBench web tasks, with the task, its correct answer and the text the "
                    "agents read from web pages and tools.",
            content_license="MIT",
            content_terms="The logs are MIT on GitHub; the Hugging Face copy (Kevin355/Who_and_When) states no "
                          "license. The task and answer come from AssistantBench, whose Hugging Face dataset is "
                          "apache-2.0 (https://huggingface.co/datasets/AssistantBench/AssistantBench); its GitHub "
                          "code repository is under the AI Pubs OpenRAIL-S license, which covers its source code, "
                          "not the task data. Logs quote short snippets of third-party web pages (business listings, "
                          "search results) that the agents retrieved. GAIA-task logs are not used.",
            labelled_by="Who&When's human annotators",
            changes="Every turn is cut to the same cap (head and tail kept, \"…[N chars truncated]\" marked) so "
                    "the transcript fits 12,000 characters; turns are numbered; nothing is rewritten.",
            selection="AssistantBench logs of at most 40 KB whose labelled agent speaks the labelled step, in sha256 "
                      "order, one per question, at most 4 rows with the same answer, 24 rows at most.",
            citation="Zhang et al., Which Agent Causes Task Failures and When? On Automated Failure Attribution of "
                     "LLM Multi-Agent Systems, ICML 2025. Tasks from AssistantBench (Yoran et al., 2024).",
            bibtex="""@inproceedings{zhang2025which,
  title     = {Which Agent Causes Task Failures and When? On Automated Failure Attribution of {LLM} Multi-Agent Systems},
  author    = {Shaokun Zhang and Ming Yin and Jieyu Zhang and Jiale Liu and Zhiguang Han and Jingyang Zhang and Beibin Li and Chi Wang and Huazheng Wang and Yiran Chen and Qingyun Wu},
  booktitle = {Proceedings of the 42nd International Conference on Machine Learning},
  series    = {Proceedings of Machine Learning Research},
  volume    = {267},
  pages     = {76583--76599},
  publisher = {PMLR},
  year      = {2025},
  url       = {https://proceedings.mlr.press/v267/zhang25cq.html}
}""")
    dataset(id="swe-agent-trajectories", name="nebius/SWE-agent-trajectories", tasks=["TC-3"],
            homepage="https://huggingface.co/datasets/nebius/SWE-agent-trajectories", license="CC-BY-4.0",
            license_url="https://huggingface.co/datasets/nebius/SWE-agent-trajectories/blob/"
                        "68195a1450865274106246d0d0296a1d6807b88e/README.md",
            content="Runs of a SWE-agent coding agent (driven by fine-tuned open-weight models) on real GitHub "
                    "issues from SWE-bench-extra and SWE-bench: the issue text, the agent's actions, what the "
                    "environment returned (often repository code) and the final patch.",
            content_license="CC-BY-4.0",
            content_terms="The card: \"licensed under the Creative Commons Attribution 4.0 license. However, please "
                          "respect the license of each specific repository on which a particular instance is "
                          "based.\" Each row's repository license was read and is recorded as code_license (all MIT, "
                          "Apache-2.0, BSD-2-Clause or BSD-3-Clause). Issue text was posted by GitHub users. The card "
                          "also says users of the model outputs \"must comply with the Llama 3.1 License\" "
                          "(https://www.llama.com/llama3_1/license/); that license's conditions apply to using the "
                          "agents' outputs to train or improve a model.",
            labelled_by="the repository's own tests (not a human): the dataset's target field",
            changes="Only the issue, the last 6 actions with their observations and the final patch are shown; "
                    "long text keeps a head and tail with \"…[N chars truncated]\" marked. The hidden tests' "
                    "logs are never shown.",
            selection="Submitted runs with a patch of at most 5,000 characters from 64 evenly spaced 2-row windows "
                      "of the dataset, in sha256 order, 12 per outcome, every row from a different repository.",
            citation="Golubev et al., Leveraging training and search for better software engineering agents, "
                     "Nebius blog, 2024 (Hugging Face dataset nebius/SWE-agent-trajectories).",
            bibtex="""@article{golubev2024search,
  title   = {Leveraging training and search for better software engineering agents},
  author  = {Golubev, Alexander and Polezhaev, Sergey and Zainullina, Karina and Trofimova, Maria and Badertdinov, Ibragim and Anapolskiy, Yury and Litvintseva, Daria and Karasik, Simon and Fisin, Filipp and Skvortsov, Sergey and Nekrashevich, Maxim and Shevtsov, Anton and Abramov, Sergey and Yangel, Boris},
  year    = {2024},
  journal = {Nebius blog},
  note    = {https://nebius.com/blog/posts/training-and-search-for-software-engineering-agents}
}""")


def _clip(text, n):
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[:n - 1].rsplit(" ", 1)[0] + "…"


def _cut(text, keep):
    """Keep the [a, b) windows of text; mark every removed stretch with its length."""
    merged = []
    for a, b in sorted(keep):
        a, b = max(0, a), min(len(text), b)
        if a >= b:
            continue
        if merged and a <= merged[-1][1] + len(MARK) + 6:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    out, last = [], 0
    for a, b in merged:
        if a > last:
            out.append(MARK.format(a - last))
        out.append(text[a:b])
        last = b
    if last < len(text):
        out.append(MARK.format(len(text) - last))
    return "".join(out)


def _headtail(text, n, head=0.6):
    text = str(text)
    if len(text) <= n:
        return text
    return _cut(text, [(0, int(n * head)), (len(text) - int(n * (1 - head)), len(text))])


def _size(obj):
    return len(json.dumps(obj, ensure_ascii=False))


def _first_sentence(text, n=220):
    text = " ".join(str(text).split())
    m = re.match(r"(.+?[.!?])(\s|$)", text)
    s = m.group(1) if m and len(m.group(1)) >= 40 else text
    return _clip(s, n)



# ================================================================ TC-1 (AgentRx)

TC1_OPTIONS = {
    "ignored_instruction": "Ignored an instruction: the agent breaks a rule or direction it was given (the operating "
                           "policy, the orchestrator's instruction, or the agreed plan), for example acting without a "
                           "required confirmation, or doing something other than the step it was told to do.",
    "wrong_plan": "Wrong plan for the goal: the agent misunderstands what the user wants or the task's constraints, "
                  "and plans or orders its actions so that the intended outcome cannot be reached (a wrong "
                  "objective, a dropped requirement, or steps in an order that rules out part of the goal).",
    "misread_output": "Misread a result: the agent draws a wrong conclusion from what a tool or another agent "
                      "returned, for example miscounting, picking the wrong record, or treating partial results as "
                      "complete.",
    "bad_call": "Invalid tool call: the agent calls a tool with arguments the tool does not accept (missing, "
                "malformed or inconsistent values), so the call is rejected.",
    "user_info": "The user's information: the simulated customer gives the agent wrong, incomplete or ambiguous "
                 "information (it departs from, or is not settled by, their hidden instructions), so the agent "
                 "cannot reach the intended outcome.",
    "blocked": "Blocked from outside: a content-safety filter or a website's access control stops the step; the "
               "agent's reasoning is not what failed.",
}
TC1_INSTRUCTION = (
    "You review failed runs of AI agents: either a retail customer-service agent chatting with a simulated "
    "customer (τ-bench), or a Magentic-One team whose Orchestrator directs a WebSurfer and other agents on a web "
    "task. Each record gives the setting, the task (for customer service: the agent's policy and the customer's "
    "hidden instructions, which the agent never saw), the numbered transcript up to one turn after the step "
    "under review, and the number of that step. Long turns are cut and marked \"…[N chars truncated]\"; omitted "
    "turns are marked too. Human annotators found a failure at step_to_review. Classify what went wrong at that "
    "step, using the definitions in the options. Judge the step itself, not whether the run failed later.")
# AgentRx category (normalised) -> option. Definitions follow AgentRx's taxonomy (Barke et al. 2026, sec. 3).
# Not used (10 labelled steps): Invention of New Information (one step among the runs fetched), Intent Not
# Supported (six steps of one run asking WebSurfer to send an email, and two τ-bench steps whose notes describe a
# policy violation or a premature hand-off), System Failure (one τ-bench step; the log shows no failure).
TC1_CATEGORY = {
    "instruction adherence failure": "ignored_instruction", "instruction/plan adherence failure": "ignored_instruction",
    "intent plan misalignment": "wrong_plan", "misinterpretation of tool output": "misread_output",
    "invalid invocation": "bad_call", "underspecified user intent": "user_info", "guardrails triggered": "blocked",
}
TC1_PLAIN = {"ignored_instruction": "an instruction the agent ignored", "wrong_plan": "a plan aimed at the wrong outcome",
             "misread_output": "a misread tool or agent result", "bad_call": "an invalid tool call",
             "user_info": "wrong or incomplete information from the simulated customer",
             "blocked": "a step blocked from outside the agent"}
# A "blocked" step must show the block itself (AgentRx also files run-length limits such as "Max rounds (30)
# reached" under Guardrails Triggered; those are skipped).
TC1_BLOCKED = re.compile(r"ResponsibleAIPolicyViolation|content management policy|Access to this page has been "
                         r"denied|Pardon Our Interruption", re.I)
# Label re-check (read by hand; each entry says why). Failure steps whose label a careful reader can dispute
# against another option from what the row shows.
TC1_SKIP = {
    "tau/34/step 30": "user_info label, but the agent had just claimed the order would ship to the new address "
                      "without changing it; the customer's closing turn reads as reasonable",
    "tau/74/step 21": "ignored_instruction label on a call the tool rejects (\"non-delivered order cannot be "
                      "exchanged\"), which reads as an invalid call",
    "tau/39/step 17": "wrong_plan label; the step is the agent wrongly saying a lookup is impossible, not a plan",
    "tau/38/step 37": "misread_output label; the product listing that shows the unavailable item is cut from the row",
    "tau/31/step 31": "wrong_plan label; the agent cancels a whole order believing it cancels one item, which reads "
                      "equally as a misread of the order's contents",
    "tau/28/step 33": "wrong_plan label; as tau/31/step 31 (a whole order cancelled for one item)",
    "m1/ccec2229ced2/step 10": "misread_output label; checking the hours of the five eateries the search returned is "
                               "a reasonable use of the result",
    "m1/929b45f34805/step 7": "misread_output label; the step sends WebSurfer to check the page for the May 2020 "
                              "files and does not yet rely on the result",
    "m1/ccec2229ced2/step 7": "wrong_plan label; the instruction asks for eateries near the park open at 11pm, "
                              "which covers the request",
    "m1/797f7a5b65ca/step 109": "wrong_plan label; the instruction asks to confirm vegan mains under $15, as the "
                                "task requires",
    "m1/a9074997e698/step 4": "wrong_plan label; the step carries out the first item of the plan, whose next item "
                              "is the TripAdvisor check the note says was skipped",
}
# Magentic-One: AgentRx files 87 WebSurfer steps of these runs as Instruction/Plan Adherence Failure. Most are an
# ordinary browsing move (a search, a click on the page it was sent to) that a reader cannot tell apart from
# following the instruction, so a WebSurfer step is used only if listed here: read by hand, the step visibly does
# something other than the Orchestrator's instruction just before it.
TC1_CONFIRMED = {
    "m1/748899d9d70c/step 95": "told to use the USPS calculator; clicks 'Get a Quote' on the DHL site",
    "m1/6e3be83d1949/step 25": "told to gather addresses and schedules of martial arts schools; opens an ad for "
                               "3D measuring equipment",
    "m1/9e31099fffa6/step 113": "told to open the monday.com press release result; lands on the NoCamels home page",
    "m1/9e31099fffa6/step 117": "told to open the monday.com press release; opens a NoCamels 'favourite articles' "
                                "post",
}
# Recurring mistakes (matched in the annotators' step_reason): at most TC1_MAX_PATTERN rows of one option share one,
# so an option is not filled by near-copies of one mistake.
TC1_PATTERNS = {"partial results treated as complete": r"incomplete|partial|whatever (?:the )?list|18%|comprehensive",
                "items modified before the address": r"before modifying|lock|prematurely called modify"}
TC1_MAX_PATTERN = 2
TC1_PER_LABEL = 5
TC1_STATE_CHARS = 15000
TC1_STEP_CHARS = 6000       # the reviewed step: longer text keeps a head and a tail
TC1_TURN_CAPS = (None, 3000, 2000, 1500, 1200, 900, 700, 500, 400)   # tried in order; one cap for every other turn
TC1_WINDOW = 10             # Magentic-One: turns shown just before the reviewed step (besides the task and plan)
TAU_SETTING = ("Customer-service chat. The agent (gpt-4o) serves a customer of an online retail store and can "
               "call the store's tools; it must follow agent_policy. The customer is played by another model "
               "following customer_hidden_instructions, which the agent cannot see. Step 1 is the policy.")
MAGENTIC_SETTING = ("Magentic-One multi-agent team (gpt-4o). The Orchestrator plans, keeps a progress ledger and "
                    "tells the other agents what to do; WebSurfer browses the web and reports what it sees; "
                    "FileSurfer reads files; Assistant writes code; ComputerTerminal runs it.")
TC1_USED_RUNS = set()       # Magentic-One run ids used by TC-1 (checked against TC-2 in define())


def _tau_turn(m):
    role = m["role"]
    if role == "tool":
        return f"tool result ({m.get('name', '?')})", m.get("content") or ""
    calls = [f"[tool call] {c['function']['name']}({c['function']['arguments']})" for c in m.get("tool_calls") or []]
    text = "\n".join(t for t in [m.get("content") or ""] + calls if t)
    return {"user": "customer", "assistant": "agent"}.get(role, role), text


def _numbered(turns, shown, step, cap, head_lines=()):
    """Numbered transcript lines of turns[i] for i in `shown` (0-based; turn i is step i + 1), with omitted
    stretches marked. The reviewed step is cut to TC1_STEP_CHARS, every other turn to `cap`."""
    lines, last = list(head_lines), (min(shown) - 1 if head_lines else -1)
    for i in shown:
        if i > last + 1:
            lines.append(f"…[turns {last + 2}–{i} not shown]" if i > last + 2 else f"…[turn {i} not shown]")
        who, text = turns[i]
        limit = TC1_STEP_CHARS if i == step - 1 else cap
        lines.append(f"{i + 1}. {who}: {text if limit is None else _headtail(text, limit, 0.6)}")
        last = i
    return lines


def _fit(make):
    """The first state make(cap) that fits TC1_STATE_CHARS, trying TC1_TURN_CAPS in order; None if none does."""
    for cap in TC1_TURN_CAPS:
        state = make(cap)
        if _size(state) <= TC1_STATE_CHARS:
            return state
    return None


def _tc1_candidates(skipped):
    src = SOURCE_DIR / "agentrx"
    runs = {x["task_id"]: x for x in json.loads((src / "tau_dataset_failed.json").read_text())}
    for t in json.loads((src / "tau_ground_truth.json").read_text()):
        x = runs[t["trajectory_id"]]
        yield "tau", str(t["trajectory_id"]), t, [_tau_turn(m) for m in x["traj"]], x
    for t in json.loads((src / "magentic_one_ground_truth.json").read_text()):
        path = src / "magentic_dataset" / f"{t['trajectory_id']}.json"
        if not path.exists():
            skipped["Magentic-One run not fetched (GAIA task, or a TC-2 row)"] += len(t["failures"])
            continue
        log = json.loads(path.read_text())
        yield "magentic", t["trajectory_id"], t, [(h.get("role") or "?", h.get("content") or "") for h in log], log


def _tc1():
    """TC-1 rows from AgentRx (Barke et al. 2026): failed agent runs whose failure steps human annotators marked,
    each with a category of AgentRx's taxonomy, the agent at fault and a reason. One annotated failure step = one
    candidate row; its answer is the category, mapped by TC1_CATEGORY.

    Source choice (checked September 2026; licenses read in each repository or card):
    - AgentRx (github.com/microsoft/AgentRx): MIT; labels by three human annotators. Used.
    - TRAIL (Patronus AI): MIT on GitHub, but the Hugging Face release asks users not to reshare it outside a
      gated or private repository. Removed to respect that wish.
    - MAST / MAD (Cemri et al. 2025, mcemri/MAST-Data): CC BY 4.0, but its card says the 1,642 traces are
      annotated "by an LLM judge, not by human labelling"; the human-labelled file holds 19 traces from an
      agreement study whose codes follow a different taxonomy revision each round. The GitHub repository has
      no license. Not used.
    - AgentErrorBench (Zhu et al. 2025, AgentDebug): human-annotated, but the data is on Google Drive with no
      license (the code repository is MIT; the paper is CC BY-NC-SA 4.0) and a third of it is GAIA runs. The
      Hugging Face mirror (davide221/agenterrorbench) is a third party's copy with no license. Not used.
    - Who&When: human labels name the agent and step, not a failure category (it is TC-2's source).
    Rules, applied in order before sampling:

    1. Runs: all 29 annotated τ-bench runs, and the AGENTRX_MAGENTIC runs (AssistantBench tasks only).
    2. The category must map to an option (see TC1_CATEGORY for the three not used).
    3. The labelled step must be spoken by the agent at fault: a user_info step is a customer turn and any other
       τ-bench step an agent turn; a Magentic-One step's speaker is the annotators' failed_agent.
    4. blocked: the step must show the block (TC1_BLOCKED); run-length limits filed as guardrails are skipped.
    5. Label re-check (read by hand): the step must not be in TC1_SKIP, and a Magentic-One WebSurfer step
       labelled Instruction/Plan Adherence must be in TC1_CONFIRMED (reasons given there).
    6. The row must fit TC1_STATE_CHARS with one of TC1_TURN_CAPS; otherwise it is skipped.
    Sampling: candidates ordered by rank(run + step); options filled scarcest first, TC1_PER_LABEL each; one row
    per run and per τ-bench customer (several τ-bench tasks share a customer and their early turns), except that
    an option with fewer than 2 rows may take a second step of a run it already uses; at most TC1_MAX_PATTERN
    rows of one option share a recurring mistake (TC1_PATTERNS).
    """
    skipped, pool = collections.Counter(), collections.defaultdict(list)
    TC1_USED_RUNS.clear()
    for system, run, t, turns, raw in _tc1_candidates(skipped):
        root = (t.get("root_cause") or {}).get("failure_id")
        for f in t["failures"]:
            n = int(f["step_number"])
            gold = TC1_CATEGORY.get(" ".join(f["failure_category"].lower().split()))
            key = f"{'tau/' + run if system == 'tau' else 'm1/' + run[:12]}/step {n}"
            if gold is None:
                skipped["category not used (see TC1_CATEGORY)"] += 1
                continue
            if not 1 <= n <= len(turns):
                skipped["step outside the log"] += 1
                continue
            who = turns[n - 1][0]
            if system == "tau":
                right = who == ("customer" if gold == "user_info" else "agent")
            else:
                right = re.sub(r"\s*\(.*\)$", "", who).lower() == f["failed_agent"].strip().lower()
            if not right:
                skipped["the labelled step is not spoken by the agent at fault"] += 1
                continue
            if gold == "blocked" and not TC1_BLOCKED.search(turns[n - 1][1]):
                skipped["blocked: the step does not show a block (e.g. a run-length limit)"] += 1
                continue
            if key in TC1_SKIP:
                skipped["label disputed (hand-reviewed list)"] += 1
                continue
            if system == "magentic" and gold == "ignored_instruction" and who == "WebSurfer" \
                    and key not in TC1_CONFIRMED:
                skipped["WebSurfer adherence label not confirmed on reading (see TC1_CONFIRMED)"] += 1
                continue
            end = min(len(turns), n + 1)
            if system == "tau":
                instr = raw["info"]["task"]["instruction"]
                first = next((x for w, x in turns if w == "customer"), "")
                make = lambda cap, turns=turns, n=n, end=end, instr=instr: {
                    "setting": TAU_SETTING, "agent_policy": turns[0][1], "customer_hidden_instructions": instr,
                    "transcript": _numbered(turns, range(1, end), n, cap,
                                            head_lines=["1. system: (the agent policy, shown in agent_policy)"]),
                    "step_to_review": n}
                title = f"τ-bench retail chat, task {run} · step {n} · “{_clip(first, 50)}”"
                group, tags = f"tau-customer/{raw['info']['task']['user_id']}", ("τ-bench retail",)
            else:
                shown = sorted({0, 1} | set(range(max(2, n - 1 - TC1_WINDOW), end)))
                question = turns[0][1].strip()
                make = lambda cap, turns=turns, n=n, shown=shown, question=question: {
                    "setting": MAGENTIC_SETTING, "task": question,
                    "transcript": _numbered(turns, shown, n, cap)
                    + ([f"…[turns {shown[-1] + 2}–{len(turns)} not shown]"] if shown[-1] + 1 < len(turns) else []),
                    "step_to_review": n}
                title = f"Magentic-One web team · step {n} · AssistantBench task: “{_clip(question, 60)}”"
                group, tags = f"magentic/{run}", ("Magentic-One", "AssistantBench")
            state = _fit(make)
            if state is None:
                skipped["too long to show"] += 1
                continue
            if gold == "blocked" and not TC1_BLOCKED.search(state["transcript"][[
                    i for i, x in enumerate(state["transcript"]) if x.startswith(f"{n}. ")][0]]):
                skipped["blocked: the block is cut from the shown step"] += 1
                continue
            pool[gold].append(dict(system=system, run=run, n=n, f=f, root=f["failure_id"] == root, gold=gold,
                                   state=state, title=title, group=group, tags=tags, key=key, turns=len(turns)))
    def pattern(c):
        return next((p for p, rx in TC1_PATTERNS.items() if re.search(rx, c["f"]["step_reason"], re.I)), None)
    chosen, groups = [], collections.Counter()
    for gold in sorted(TC1_OPTIONS, key=lambda g: (len(pool[g]), g)):
        taken = []
        for second in (False, True):   # a second row from one run only while the option has fewer than 2
            for c in sorted(pool[gold], key=lambda c: rank(c["key"])):
                pat = pattern(c)
                if len(taken) >= (2 if second else TC1_PER_LABEL) or c in taken \
                        or groups[c["group"]] >= (2 if second else 1) \
                        or (second and not any(x["group"] == c["group"] for x in taken)) \
                        or (pat and sum(pattern(x) == pat for x in taken) >= TC1_MAX_PATTERN):
                    continue
                taken.append(c)
                groups[c["group"]] += 1
        chosen += taken
    chosen.sort(key=lambda c: rank(c["key"]))
    for c in chosen:
        f, tau = c["f"], c["system"] == "tau"
        if not tau:
            TC1_USED_RUNS.add(c["run"])
        row("TC-1", f"{'tau-' + c['run'] if tau else 'm1-' + c['run'][:12]}-s{c['n']}", title=c["title"],
            state=c["state"], gold=c["gold"],
            rationale=f"AgentRx's annotators labelled step {c['n']} {f['failure_category'].strip()} "
                      f"({'the critical failure of the run' if c['root'] else 'not the critical failure'}): "
                      f"{_first_sentence(f['step_reason'], 260)}",
            note=f"The annotators found {TC1_PLAIN[c['gold']]} here; agent at fault: {f['failed_agent'].strip()}.",
            source={"dataset_id": "agentrx", "dataset": "AgentRx benchmark", "license": "MIT",
                    "url": "https://github.com/microsoft/AgentRx",
                    "citation": "Barke et al., AgentRx: Diagnosing AI Agent Failures from Execution Trajectories, "
                                "arXiv:2602.02475, 2026." + (" Run of a τ-bench retail task (Yao et al., 2024; MIT)."
                                if tau else " Magentic-One run from Who&When (Zhang et al., 2025; MIT) of an "
                                "AssistantBench task (Yoran et al., 2024; Apache-2.0)."),
                    "record_id": (f"data/tau_retail/tau_dataset_failed.json task_id {c['run']}, step {c['n']}" if tau
                                  else f"data/magentic_dataset/{c['run']}.json, step {c['n']}"),
                    "original_label": {"failure_category": f["failure_category"].strip(), "step_number": c["n"],
                                       "failed_agent": f["failed_agent"].strip(), "step_reason": f["step_reason"],
                                       "category_reason": f["category_reason"], "critical_failure": c["root"]},
                    "labelled_by": "AgentRx's human annotators"},
            tags=c["tags"])
    return skipped, pool


# ================================================================ TC-2 (Who&When)

TC2_INSTRUCTION = (
    "You review logs of multi-agent teams that failed a task: each final answer was wrong. Each record gives "
    "the task, the correct answer when it may be shown, and the numbered transcript of the run (who spoke, "
    "and what they said; long turns are cut and marked \"…[N chars truncated]\"). Human annotators traced "
    "the failure back to the one agent whose mistake caused it. Pick that agent from the options, which are "
    "the agents that speak in this log. An agent that only repeats or accepts an earlier mistake is not the "
    "cause; the first decisive mistake is.")
TC2_SCHEME = {"agent": "One of the agents that speak in the row's log (the options differ per row)."}
TC2_CHARS = 12000         # transcript budget (sum of the numbered turns)
TC2_TURN_CAPS = (None, 3000, 2000, 1500, 1200, 1000, 800)   # tried in order; the same cap applies to every turn
TC2_ROWS = 24
TC2_MAX_AGENT = 4         # rows whose answer is the same agent name
MAGENTIC = {
    "Orchestrator": "Orchestrator: plans the work, keeps a progress ledger and tells the other agents what to do.",
    "WebSurfer": "WebSurfer: browses the web (searches, opens pages, clicks, reads, summarises).",
    "FileSurfer": "FileSurfer: opens and reads local files.",
    "Assistant": "Assistant: a general-purpose model that reasons and writes code.",
    "ComputerTerminal": "ComputerTerminal: runs the code the Assistant writes and returns the output.",
}
COMPUTER_TERMINAL = "Computer_terminal: runs the code the experts write and returns its output."


def _ww_role(system_prompt, name):
    text = (system_prompt or {}).get(name, "")
    m = re.search(r"## Your role\s*(.+?)(?:\n\n|\n##|$)", text, re.S)
    role = " ".join((m.group(1) if m else "").split())
    if role and not role.startswith(name):
        role = f"{name}: {role}"
    return _first_sentence(role, 160) if role else f"{name}: an expert agent in the group chat."


def _tc2():
    """TC-2 rows from Who&When (Zhang et al., ICML 2025): failed runs of real multi-agent systems, with the
    agent annotators hold responsible (`mistake_agent`), the step (`mistake_step`) and a reason. The
    Hugging Face copy of the dataset states no license; the GitHub repository (the source used) is MIT.
    Rules:

    1. Logs are the WW_FILES (AssistantBench tasks, at most 40 KB each). The options are the agents that speak in the log, with
       "Orchestrator (thought)", "Orchestrator (-> WebSurfer)" etc. counted as one Orchestrator; the person who
       asks the question ("human") is not an option.
    2. Skipped: fewer than two agents besides Computer_terminal; mistake_agent not among the speakers, or not
       the speaker of turn mistake_step (the label contradicts the log); the first two turns do not contain
       at least half of the question's 4-word sequences (some logs carry an error message, e.g. "exitcode: 1
       … unknown language json", where the task should be, and annotators then blame whoever answered it).
    3. Trimming, identical for every turn so it never points at the answer: each turn is cut to the largest
       cap in TC2_TURN_CAPS (head and tail kept, "…[N chars truncated]" marked) that brings the transcript
       within TC2_CHARS; if even the smallest cap does not, the log is skipped.
    4. Only AssistantBench tasks (64-hex question_ID; AssistantBench is Apache-2.0): they keep their
       question and correct answer. GAIA-task logs are skipped (see WW_FILES).
    Sampling: rank(log id) order; one row per question; at most TC2_MAX_AGENT rows with the same answer;
    TC2_ROWS rows.
    """
    src = SOURCE_DIR / "whoandwhen"
    skipped, cands = collections.Counter(), []
    for sub, ns in WW_FILES.items():
        for n in ns:
            path = src / sub / f"{n}.json"
            if not path.exists():
                skipped["log not downloaded"] += 1
                continue
            d = json.loads(path.read_text())
            hist = d["history"]
            speaker = [(h.get("name") or h.get("role") or "?").strip() for h in hist]
            base = [re.sub(r"\s*\(.*\)$", "", x) for x in speaker]
            agents = sorted(set(base) - {"human"})
            gold, at = d["mistake_agent"], int(d["mistake_step"])
            if len(set(agents) - {"Computer_terminal", "ComputerTerminal"}) < 2:
                skipped["only one agent in the log"] += 1
                continue
            if gold not in agents or at >= len(hist) or base[at] != gold:
                skipped["mistake agent is not the speaker of the mistake step"] += 1
                continue
            if not re.fullmatch(r"[0-9a-f]{64}", str(d["question_ID"])):
                skipped["GAIA task (not used, see WW_FILES)"] += 1
                continue
            qw = re.findall(r"\w+", d["question"].lower())
            grams = {tuple(qw[i:i + 4]) for i in range(len(qw) - 3)}
            opening = re.findall(r"\w+", " ".join(h["content"] or "" for h in hist[:2]).lower())
            seen = {tuple(opening[i:i + 4]) for i in range(len(opening) - 3)}
            if grams and len(grams & seen) < 0.5 * len(grams):
                skipped["the log's own task text is not the question (corrupted log)"] += 1
                continue
            turns = [(speaker[i], h["content"] or "") for i, h in enumerate(hist)]
            for cap in TC2_TURN_CAPS:
                lines = [f"{i + 1}. {who}: {text if cap is None else _headtail(text, cap, 0.65)}"
                         for i, (who, text) in enumerate(turns)]
                if sum(len(x) for x in lines) <= TC2_CHARS:
                    break
            else:
                skipped["transcript longer than 12,000 characters after trimming"] += 1
                continue
            hand = sub == "Hand-Crafted"
            options = {a: (MAGENTIC.get(a, f"{a}: an agent of the team.") if hand else
                           COMPUTER_TERMINAL if a == "Computer_terminal" else _ww_role(d.get("system_prompt"), a))
                       for a in agents}
            state = {"team": ("Magentic-One: an Orchestrator directs specialist agents (web, files, code)."
                              if hand else "AutoGen group chat of experts; Computer_terminal runs their code."),
                     "task": d["question"].strip(), "correct_answer": str(d["ground_truth"]),
                     "outcome": "The team's final answer was wrong.",
                     "transcript": lines}
            cands.append(dict(sub=sub, n=n, d=d, gold=gold, at=at, state=state, options=options,
                              agents=agents, turns=len(hist)))
    cands.sort(key=lambda c: rank(f"{c['sub']}/{c['n']}"))
    chosen, questions, per_gold = [], set(), collections.Counter()
    for c in cands:
        if len(chosen) == TC2_ROWS:
            break
        if c["d"]["question_ID"] in questions:
            skipped["another log of the same question already sampled"] += 1
            continue
        if per_gold[c["gold"]] >= TC2_MAX_AGENT:
            continue
        questions.add(c["d"]["question_ID"])
        per_gold[c["gold"]] += 1
        chosen.append(c)
    for c in chosen:
        d, hand = c["d"], c["sub"] == "Hand-Crafted"
        title = (f"{'Magentic-One' if hand else 'AutoGen expert'} team, {len(c['agents'])} agents, "
                 f"{c['turns']} turns · AssistantBench task: “{_clip(d['question'], 60)}”")
        reason = d["mistake_reason"]
        row("TC-2", f"{'hc' if hand else 'ag'}-{c['n']}", title=title, state=c["state"], gold=c["gold"],
            options=c["options"],
            rationale=f"Who&When's annotators blame {c['gold']} at turn {c['at'] + 1}: {_first_sentence(reason, 240)}",
            note=f"Decisive mistake at turn {c['at'] + 1} of {c['turns']}.",
            source={"dataset_id": "whoandwhen", "dataset": "Who&When",
                    "license": "MIT (GitHub repository; the Hugging Face card states none)",
                    "url": "https://github.com/mingyin1/Agents_Failure_Attribution",
                    "citation": "Zhang et al., Which Agent Causes Task Failures and When? On Automated Failure "
                                "Attribution of LLM Multi-Agent Systems, ICML 2025. Task from AssistantBench (Yoran et "
                                "al., 2024; Apache-2.0).",
                    "record_id": f"Who&When/{c['sub']}/{c['n']}.json (question {d['question_ID']})",
                    "original_label": {"mistake_agent": c["gold"], "mistake_step": str(d["mistake_step"]),
                                       "mistake_reason": reason},
                    "labelled_by": "Who&When's human annotators"},
            tags=("AssistantBench", "Magentic-One" if hand else "AutoGen"))
    return skipped, cands


# ================================================================ TC-3 (SWE-agent trajectories)

TC3_OPTIONS = {
    "fixed": "Fixed: with this patch applied, the repository's hidden tests for the issue pass.",
    "not_fixed": "Not fixed: with this patch applied, the repository's hidden tests for the issue still fail.",
}
TC3_INSTRUCTION = (
    "You review runs of a coding agent (SWE-agent) that tried to fix a GitHub issue in a Python repository. "
    "Each record gives the issue, the agent's last actions with what it saw after each (long text is cut and "
    "marked \"…[N chars truncated]\"), and the final patch it submitted. The repository has hidden tests for "
    "the issue that the agent never saw. Decide whether this patch makes them pass. Judge the patch against "
    "the issue; the agent's own claims of success are not evidence.")
TC3_PER_LABEL = 12
TC3_ISSUE_CHARS = 2500
TC3_LAST_ACTIONS = 6
TC3_ACTION_CHARS, TC3_OBS_CHARS = 900, 900
TC3_PATCH_CHARS = 5000    # longer patches are skipped: a diff cut in the middle cannot be judged
TC3_STATE_CHARS = 14000


def _tc3():
    """TC-3 rows from nebius/SWE-agent-trajectories (CC BY 4.0): SWE-agent runs (fine-tuned Llama models) on
    real GitHub issues. The answer is the dataset's `target`: whether the repository's hidden tests passed
    once the run's patch was applied. Nobody labelled these by hand; the tests did. Rules:

    1. Rows are the ones in the fetched windows (SWE_OFFSETS). Skipped: the run did not end by submitting
       (exit_status not starting with "submitted"), or its patch is empty or longer than TC3_PATCH_CHARS.
    2. State: the issue text (from the first user message, cut to TC3_ISSUE_CHARS), the run's last
       TC3_LAST_ACTIONS actions with the observation after each (cut to TC3_ACTION_CHARS / TC3_OBS_CHARS),
       and the full final patch. The dataset's eval_logs (the hidden tests' output) are never shown.
    3. Rows over TC3_STATE_CHARS are skipped.
    Sampling: candidates in rank(instance_id/row index) order; the scarcer label (fixed) is filled first,
    then the other; TC3_PER_LABEL per label; every row from a different repository.
    """
    skipped, cands = collections.Counter(), []
    for o in SWE_OFFSETS:
        path = SOURCE_DIR / f"swe-agent-trajectories/rows-{o:05d}.json"
        data = json.loads(path.read_text()) if path.exists() else {}
        for item in data.get("rows", []):
            x, idx = item["row"], item["row_idx"]
            patch = (x.get("generated_patch") or "").strip("\n")
            if not str(x.get("exit_status", "")).startswith("submitted"):
                skipped["run did not end by submitting a patch"] += 1
                continue
            if len(patch) < 20 or len(patch) > TC3_PATCH_CHARS:
                skipped["patch empty or longer than 5,000 characters"] += 1
                continue
            traj = x["trajectory"]
            first = next((m["text"] for m in traj if m["role"] == "user"), "") or ""
            m = re.search(r"ISSUE:\n(.*?)\n+INSTRUCTIONS:", first, re.S)
            issue = (m.group(1) if m else first).strip()
            acts = [i for i, t in enumerate(traj) if t["role"] == "ai"]
            last = []
            for k, i in enumerate(acts[-TC3_LAST_ACTIONS:], start=len(acts[-TC3_LAST_ACTIONS:]) and
                                  len(acts) - len(acts[-TC3_LAST_ACTIONS:]) + 1):
                obs = traj[i + 1]["text"] if i + 1 < len(traj) and traj[i + 1]["role"] == "user" else None
                step = {"action_no": k, "action": _headtail(traj[i]["text"] or "", TC3_ACTION_CHARS, 0.5)}
                if obs is not None:
                    step["observation"] = _headtail(obs, TC3_OBS_CHARS, 0.6)
                last.append(step)
            repo = x["instance_id"].rsplit("-", 1)[0].replace("__", "/")
            state = {"repository": repo, "issue": _headtail(issue, TC3_ISSUE_CHARS, 0.8),
                     "actions_in_run": len(acts),
                     "last_actions": ([f"…[actions 1–{len(acts) - len(last)} not shown]"]
                                      if len(acts) > len(last) else []) + last,
                     "final_patch": patch}
            if _size(state) > TC3_STATE_CHARS:
                skipped["too long to show"] += 1
                continue
            gold = "fixed" if x["target"] in (True, "True", "true") else "not_fixed"
            title_line = _clip(next((ln.strip() for ln in issue.splitlines() if ln.strip()), ""), 60)
            number = x["instance_id"].rsplit("-", 1)[1]
            gist = "" if re.search(r"fix", title_line, re.I) else f": “{title_line}”"  # never echo an option word
            cands.append(dict(idx=idx, x=x, repo=repo, gold=gold, state=state,
                              title=f"SWE-agent run on {repo} · issue {number}{gist}"))
    cands.sort(key=lambda c: rank(f"{c['x']['instance_id']}/{c['idx']}"))
    counts = collections.Counter(c["gold"] for c in cands)
    used, chosen = set(), []
    for gold in sorted(TC3_OPTIONS, key=lambda g: (counts[g], g)):
        n = 0
        for c in cands:
            if n == TC3_PER_LABEL:
                break
            if c["gold"] != gold or c["repo"] in used:
                continue
            used.add(c["repo"])
            chosen.append(c)
            n += 1
    chosen.sort(key=lambda c: rank(f"{c['x']['instance_id']}/{c['idx']}"))
    for c in chosen:
        x = c["x"]
        row("TC-3", f"{x['instance_id']}-r{c['idx']}", title=c["title"], state=c["state"], gold=c["gold"],
            rationale=("The repository's hidden tests for this issue passed with the patch applied."
                       if c["gold"] == "fixed" else
                       "The repository's hidden tests for this issue did not pass with the patch applied."),
            note=f"Run by {x['model_name']}; exit status: {x['exit_status']}.",
            source={"dataset_id": "swe-agent-trajectories", "dataset": "nebius/SWE-agent-trajectories",
                    "license": "CC BY 4.0",
                    "url": "https://huggingface.co/datasets/nebius/SWE-agent-trajectories",
                    "citation": "Nebius AI, SWE-agent trajectories (Golubev et al., 2024), Hugging Face dataset "
                                "nebius/SWE-agent-trajectories.",
                    "record_id": f"train row {c['idx']} ({x['instance_id']}, {x['model_name']})",
                    "original_label": {"target": c["gold"] == "fixed", "exit_status": x["exit_status"]},
                    "labelled_by": "the repository's own tests (not a human)",
                    "code_repo": f"https://github.com/{c['repo']}",
                    "code_license": _code_license(c["repo"], f"TC-3 {x['instance_id']}")},
            tags=("SWE-agent", x["model_name"]))
    return skipped, cands


def define():
    _datasets()
    task("TC-1", category="trace-classification", name="Agent failure type at a step",
         ask="What kind of failure happens at this step?", instruction=TC1_INSTRUCTION, options=TC1_OPTIONS)
    _tc1()
    task("TC-2", category="trace-classification", name="Failure attribution in a multi-agent run",
         ask="Which agent caused the failure?", instruction=TC2_INSTRUCTION, options=TC2_SCHEME,
         per_row_options=True)
    _tc2()
    # TC-1 and TC-2 may not show the same Magentic-One log (AgentRx's Magentic-One runs are Who&When logs).
    shared = {r["source"]["record_id"].rsplit("question ", 1)[-1].rstrip(")") for r in ROWS if r["task"] == "TC-2"
              and "Hand-Crafted" in r["source"]["record_id"]} & TC1_USED_RUNS
    assert not shared, f"TC-1 and TC-2 rows share Magentic-One logs: {sorted(shared)}"
    task("TC-3", category="trace-classification", name="Coding-agent outcome",
         ask="Did this coding-agent run fix the issue?", instruction=TC3_INSTRUCTION, options=TC3_OPTIONS)
    _tc3()
