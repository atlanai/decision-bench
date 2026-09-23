"""bench-v3 category: Sensitive data (PII).

PII-2  Samsung CredData: a secret scanner flagged a line in a real, permissively licensed GitHub repository. Is the
       flagged value a real credential, a placeholder or test value, or not a secret? Answers come from CredData's
       manual review. No real secret is published: every credential-shaped value in the shown lines was replaced by
       a random same-shape fake (AWS keys by AWS's documented example pair; provider prefixes broken with EXAMPLE).
       Every excerpt comes from a repository whose license file was read and is MIT, Apache-2.0 or BSD-3-Clause.

       Pointer rule. CredData hides where its lines come from (directory and file names are replaced by hashes) so
       that a reader cannot go from a row to a live secret. This benchmark follows the same rule, and goes one step
       further: the scrubbed excerpts are committed in creddata_excerpts.json, and neither this module nor the
       source manifest records the commit, directory path or line number of any excerpt. A row names the repository
       (URL and license, for attribution), the CredData metadata file and Id (record_id), and the file's base name
       (shown to the model, because "devise.rb" or "index.test.ts" is part of the evidence). The same fields are
       kept for every label, so a row's shape never hints at the answer. To trace a row to its file, use CredData's
       own tooling: its meta file gives the FileID and its download script maps it to the file.

       How the excerpts were chosen (deterministic, from all 60,227 labelled lines of the 305 CredData repositories
       whose GitHub license is MIT, Apache-2.0, BSD-2/3-Clause, ISC, CC0-1.0 or Unlicense; 32 repositories with GPL,
       LGPL, MPL, EPL, OSL, UPL, no or unknown license were skipped):
         - every labelled line ordered by sha256("pii-2/<Id>"); per label, the first 8 that pass the rules below,
           at most one line per repository across the whole task;
         - common rules: a single-line value; category not UUID, nonce, salt, PEM/private key, IP, certificate, CMD,
           multi or "Other"; a source/config/doc file type (no .xml, bundles, storyboards, ndjson); file <= 1.5 MB;
           the flagged line and the +-2 lines shown are each 8-180 characters; the flagged value is set and at least
           4 characters; no other CredData label with a different answer on the same line;
         - real_credential (CredData T): not in a test/example/docs scope, and the original path does not contain
           example, sample, template, dist, test, spec, fixture, mock, demo, doc, tutorial, quickstart, readme,
           guide, tmpl, cassette or vcr; not a .md/.rst/.txt/.adoc/.html file; the shown lines contain no placeholder
           wording (<...>, your_, example, xxx, changeme, dummy, fake, sample, placeholder, ***, replace, insert,
           todo, redacted, "...", ">>>", "e.g.", demo); the flagged line is not a comment; the value is >= 10
           characters, mixes at least two of lower case / upper case / digits, has no spaces, has more than 5
           distinct characters and no run like abcdef or 123456; the category is not an "ID";
         - placeholder_or_test (CredData X): common rules only;
         - not_a_secret (CredData F): no placeholder wording in the shown lines and a flagged value of at least 6
           characters;
         - real-credential lines dropped after reading them are listed in CRED_EXCLUDED.
       Each excerpt shows the flagged line (marked ">") and up to two lines either side, without line numbers.

PII-1 (masking a highlighted mention: direct identifier / quasi-identifier / no need to mask) has been withdrawn.
It used TAB (ECHR judgments): TAB's annotations are MIT, but the Court's terms
(https://www.echr.coe.int/copyright-and-disclaimer) allow reproduction only "for private use or for the purposes of
information and education" and require "prior written permission" for commercial use, so the text fails the
benchmark's license policy. No replacement meets the policy (real or objectively labelled text, human span-level
masking labels, a permissive license for both dataset and text, no text centred on private individuals):
  - Wikipedia biographies annotated with the TAB scheme (Papadopoulou et al., LREC 2022; 553 summaries, 11,141
    DIRECT/QUASI/NO_MASK decisions; github.com/anthipapa/bootstrapping-anonymization): the ideal source (CC BY-SA
    text about public figures, same scheme), but the repository has no license file or license statement; the
    paper says only that it is "publically available". Unlicensed annotations cannot be redistributed. If the
    authors add a permissive license (TAB itself is MIT), PII-1 can be rebuilt on it: the file uses TAB's JSON
    format, so the TAB loader removed from this module applies almost unchanged.
  - MAPA EUR-Lex annotations (joelniklaus/mapa, CC BY 4.0): only 12 English documents; entity types, not masking
    decisions; visible label errors (a date and the word "Appellant" tagged PERSON); private parties named in CJEU
    cases (e.g. a divorce).
  - CRAPII student essays (Kaggle, human double-annotated direct/indirect identifiers): CC BY-NC 4.0.
  - SynthPAI (human-verified personal-attribute labels): CC BY-NC-SA 4.0.
  - Nemotron-PII (CC BY 4.0) and Gretel pii-masking-en-v1 (Apache-2.0): synthetic text whose spans were tagged by
    the generating model ("produced during generation"; "automated validation"), neither human-verified nor
    objectively defined; ai4privacy's CC BY 4.0 previews have their text redacted; Presidio's synth_dataset_v2 and
    Privy are template fills whose labels restate the template slot (no masking judgement to test).
  - WNUT-17, Few-NERD and other permissive NER sets: entity types, not privacy decisions (WNUT-17's tweets and
    Reddit posts also carry platform terms); a masking answer would be this benchmark's rule, not a human label.
"""
import json

from . import dataset, task, row, ROOT, SOURCES as SOURCE_DIR

CRED_COMMIT = "c09c0c52fc6dae4ae5438ae69ba486f9f8059f0d"
CRED_REPO = "https://github.com/Samsung/CredData"
CRED_RAW = f"https://raw.githubusercontent.com/Samsung/CredData/{CRED_COMMIT}"
CRED_CITATION = "Yun et al., Project CredData: A Dataset of Credentials for Research, Samsung, 2021."
# The 24 scrubbed excerpts (see "Pointer rule" above): state, CredData label and repository license per row.
EXCERPTS = ROOT / "authoring/bench/creddata_excerpts.json"
PERMISSIVE_CODE = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "CC0-1.0"}
CRED_LABELS = {"T": "real_credential", "X": "placeholder_or_test", "F": "not_a_secret"}

# CredData's license and the metadata files that hold each row's label (FileID hashes only, no paths).
SOURCES = [{"dataset": "Samsung CredData", "url": f"{CRED_RAW}/LICENSE", "path": "creddata/LICENSE"}] + [
    {"dataset": "Samsung CredData (metadata)", "url": f"{CRED_RAW}/meta/{m}.csv", "path": f"creddata/meta/{m}.csv"}
    for m in sorted({e["meta"] for e in json.loads(EXCERPTS.read_text())})]

# Lines that passed the written rules but that a careful reader could not defend as "real_credential".
CRED_EXCLUDED = {
    1494346: "a NATS user nkey (starts with U), which is a public key, in a server test config",
    32721: "an Algolia DocSearch key, which is a search-only key published for website search",
    41430: "a seeded user password in OWASP Juice Shop, a deliberately insecure training app",
    37415: "an AWS key pair; publishing it safely needs AWS's documented example values, which read as placeholders",
    136872: "a Firebase database URL, which is not a secret",
    35042: "a session token in a fake transport used to simulate server faults in tests",
}

# One plain sentence per row, written after reading the line and its CredData label.
CRED_REASONS = {
    1494695: "A RabbitMQ password is hard-coded in the application's console config.",
    34244: "A Coveralls repository token is committed in the project's CI config.",
    42432: "A GitHub API token is committed in the CI workflow, split into two halves.",
    32268: "Devise's secret key, used to sign tokens, is hard-coded in the initializer.",
    34770: "A long random session-signing secret is hard-coded in a config file.",
    29500: "A fixed AES encryption key is hard-coded in the class that decrypts stored database passwords.",
    1493488: "A fixed Shiro remember-me cipher key is hard-coded in the Java configuration.",
    11536976: "A JWT signing secret is hard-coded as the default in the Helm chart's values file.",
    31185: "The value is a “<your key>” placeholder in documentation.",
    33539: "“admin” is the password of a throwaway database in a CI test workflow.",
    29475: "MY_OAUTH_TOKEN is a placeholder in the README's example code.",
    110520: "“foo2” is a dummy value in documentation that shows the config file format.",
    23505: "“my_secret” is a dummy option value inside a test spec.",
    35067: "The password is a fixed value in a test configuration file.",
    32498: "“pass” is a dummy credential in a test spec.",
    61652: "“test” is the default password in the sample docker-compose file generated for new projects.",
    11526114: "The flagged text is the name of a test key pair, not key material.",
    11528189: "RSA_2048 names a key type; it is a setting, not a secret.",
    11532785: "The flagged word is part of an error message in generated code.",
    11527047: "typing.Any is the type annotation of a method parameter.",
    11529947: "The value is a translation placeholder that refers to another label.",
    11531540: "o.AuthURL reads a URL from configuration; no secret is written here.",
    27607: "“secret” is the name of a database column.",
    37179: "“Invalid Password” is an error message in a test.",
}


def _datasets():
    dataset(id="creddata", name="Samsung CredData", tasks=["PII-2"], homepage=CRED_REPO,
            license="Apache-2.0", license_url=f"{CRED_REPO}/blob/{CRED_COMMIT}/LICENSE",
            content="One to five lines of source, config or documentation files from public GitHub repositories, "
                    "around a line that secret scanners flagged; CredData supplies the labels and line positions.",
            content_license="Apache-2.0",
            content_terms="CredData's labels and metadata are Apache-2.0; its README says \"Each file is under the "
                          "existing project's license\". Each excerpt here keeps its repository's license, read "
                          "from its license file and recorded per row (source.code_license and code_license_file): "
                          "MIT, Apache-2.0 or BSD-3-Clause for all 24 rows. The repository and the file's base name "
                          "are shown (CredData hides both behind ids; the repository is kept for attribution and the "
                          "base name because it is part of the evidence); nothing that locates the file is.",
            labelled_by="CredData's reviewers, who manually checked every scanner hit against written ground rules",
            changes="Every value CredData judged a real credential, and any other credential-shaped string in the "
                    "shown lines, is replaced with a random fake of the same length and shape (AWS keys with AWS's "
                    "documented example pair; provider prefixes broken with EXAMPLE). Only the flagged line and up "
                    "to two lines either side are shown. So that no row leads a reader to a live secret, every row "
                    "(whatever its label, so the shape never hints at the answer) keeps only the repository URL and "
                    "license, the CredData metadata file and Id, and the file's base name. The scrubbed excerpts are "
                    "committed; the commit, directory path and line number of the originals are recorded nowhere "
                    "in this repository.",
            selection="Labelled lines from the 305 CredData repositories with a permissive GitHub license, in "
                      "sha256 order, 8 per label, at most one per repository, filtered by the written rules in "
                      "authoring/bench/pii.py; six real-credential lines were dropped after reading (CRED_EXCLUDED).",
            citation=CRED_CITATION,
            bibtex="""@misc{sr-cred21,
  author       = {JaeKu Yun and ShinHyung Choi and YuJeong Lee and Oleksandra Sokol and WooChul Shim and Arkadiy Melkonyan and Dmytro Kuzmenko},
  title        = {Project {CredData}: A Dataset of Credentials for Research},
  howpublished = {\\url{https://github.com/Samsung/CredData}},
  year         = {2021}
}""")


def define():
    _datasets()
    task("PII-2", category="pii", name="Triage a secret-scanner hit",
         ask="Is this a real secret committed in code?",
         instruction=("A secret scanner flagged a value (flagged_value) on one line of a file from a public GitHub "
                      "repository; the flagged line is marked with > among its neighbouring lines. Decide what the "
                      "flagged value is. Credential-shaped values in the excerpt may have been replaced by random "
                      "stand-ins of the same shape, so judge by the code and its context, not by testing the value."),
         options={"real_credential": "Looks like a real, usable credential hard-coded in code or config.",
                  "placeholder_or_test": "A placeholder, an example or a value only used in tests.",
                  "not_a_secret": "Not a credential at all, e.g. a variable, function call, type, message or "
                                  "setting."})
    _pii2()


def _pii2():
    excerpts = json.loads(EXCERPTS.read_text())
    for e in excerpts:
        assert e["code_license"] in PERMISSIVE_CODE, f"PII-2 {e['id']}: {e['repo']} is {e['code_license']}"
        assert e["id"] not in CRED_EXCLUDED
        assert CRED_LABELS[e["original_label"].split()[1].rstrip(",")] == e["label"], f"PII-2 {e['id']}: label"
        row("PII-2", f"creddata-{e['id']}", title=e["title"], state=e["state"], gold=e["label"],
            rationale=CRED_REASONS[e["id"]], note=e["note"], tags=e["tags"],
            source={"dataset_id": "creddata", "dataset": "Samsung CredData",
                    "license": "Apache-2.0 (labels and metadata); the code excerpt "
                               f"keeps its repository's license, {e['code_license']}",
                    "url": f"{CRED_REPO}/blob/{CRED_COMMIT}/meta/{e['meta']}.csv", "citation": CRED_CITATION,
                    "record_id": f"CredData Id {e['id']} (meta/{e['meta']}.csv)",
                    "original_label": e["original_label"],
                    "labelled_by": "CredData's reviewers, who manually checked every scanner hit against written "
                                   "ground rules",
                    "code_repo": f"https://github.com/{e['repo']}", "code_license": e["code_license"],
                    "code_license_file": e["license_file"]})
