# Dataset and privacy review — 2026-09-23

**Outcome:** the source and privacy review is complete as a release assessment, with the decisions below still open. It is not a blanket legal clearance. No benchmark row or answer was silently changed.

## Scope and evidence

- Screened all **1,071 active v4 rows** and **359 archived v3 rows** for email, telephone and US SSN patterns. The [machine-readable evidence](data-release-review.json) contains corpus hashes, row IDs and match counts, never matched contact values.
- Retrieved and inspected the license evidence for all **36 active sources**. One SEC endpoint rejected the script; its official policy was inspected through the web reader. Fixed the Congress license link: the data lives on a generated branch that has no LICENSE; the license now points to a verified main-branch commit.
- Rechecked underlying license metadata for **all 16 OWID charts**: observed CC BY 4.0 and CC BY 3.0 IGO declarations. Preserve the data-provider attribution already present in the chart images and rows. Auxiliary geographic/annotation columns are not separately licensed evidence for the numerical series.
- Visually inspected contact sheets covering **106 unique corpus images**: 30 receipts, 30 document pages, 30 icons and 16 charts, referenced by 122 rows. Receipt identifiers are visibly blurred; document pages contain public publication material and attribution. This was not forensic OCR or a pixel-by-pixel search.
- Inspected image metadata. The 30 receipt images' EXIF contains color space and dimensions, with no GPS/camera/author fields observed. No attempt was made to recover redacted content.

## Decisions before publication

| Item | Evidence and affected scope | Recommended resolution |
| --- | --- | --- |
| Archived SWE-agent output terms | 24 rows in `bench-v3`; the [publisher's license section](https://huggingface.co/datasets/nebius/SWE-agent-trajectories#license) requires compliance with Llama 3.1 terms in addition to dataset and source-code terms | Exclude archived v3 from the public snapshot, or explicitly document and satisfy those additional requirements. Do not describe the entire repository as unrestricted MIT/CC-BY data. |
| deepset license declarations | The [pinned card](https://huggingface.co/datasets/deepset/prompt-injections/blob/4f61ecb038e9c3fb77e21034b22511b523772cdd/README.md) has top-level Apache-2.0 and nested CC-BY-4.0 declarations; 16 active and 16 archived rows | Preserve both declarations and attribution; obtain clarification or choose exclusion in a new corpus version before representing the data as unambiguously Apache-only. Both named licenses are permissive; no noncommercial restriction was found. |
| Public history | Local history includes archived data, personal commit identity and old home paths; GitHub currently has only the organization starter commit | Prepare an intentional release snapshot. Do not merge unrelated histories or force-push the old history as an incidental setup step. |
| Notice packaging | Code excerpts have per-repository license references; Wikipedia-derived rows include share-alike material | Retain original notices and all applicable dataset/content licenses in any redistributed package. A dataset-level MIT label cannot replace the original code license; a CC-BY-SA-3.0 table cannot relabel CC-BY-SA-4.0 questions. |

The active corpus is frozen and may already have local runs. Excluding or redacting rows requires a new corpus version and hash, not an in-place edit that invalidates comparisons. Deleting archived files from the tip would not remove them from published Git history.

## Privacy dispositions

| Area | Review result |
| --- | --- |
| Active email-like strings | 34 rows flagged. Contexts are AgentDojo/tau-bench benchmark environment contacts, a CredData example-domain placeholder, and code instance-name syntax. No private operator contact was established. Benchmark identities can resemble real addresses; do not treat them as actual customer records or contact them. |
| Active telephone-like strings | Two rows flagged: a product's public customer-service number and a company's public filing contact. They are business contact details, not evidence of a private individual's phone. |
| SSN patterns | No matches in active or archived state fields. This is a pattern result, not proof that no personal identifiers exist. |
| Contract text | Existing authoring redaction removes email and phone/fax details. No active email/phone-pattern hits in the contract rows. Names and organization names can still appear in public contracts. |
| Consumer complaints | Public CFPB narratives retain upstream masking. Their public origin does not remove the possibility of contextual identification; preserve the removal-request route. |
| Meeting transcripts | AMI speakers are represented by role/channel. The publisher documents [ethics and participant consent procedures](https://groups.inf.ed.ac.uk/ami/corpus/ethicsandconsent.shtml). |
| Archived corpus | 28 email-like and 7 phone-like rows flagged. Includes simulated agent environments and public web observations. These are separate from active-v4 clearance; excluding the archive is the simpler release boundary. |
| Vendor marks | Logos identify vendors in the viewer. They remain vendor property and must not imply endorsement; they are not covered by the code's MIT license. |

## License interpretation corrections

The [SEC FAQ](https://www.sec.gov/about/webmaster-frequently-asked-questions) and [dissemination policy](https://www.sec.gov/about/privacy-information#dissemination) support reuse of public filing content. That is more precise evidence than claiming every privately authored filing is a US-government work in the public domain. Existing frozen metadata uses the older shorthand; downstream distributors should cite the actual reuse policy and retain the corpus/annotation terms.

For charts, [OWID's reuse guidance](https://ourworldindata.org/faqs) distinguishes its work from third-party data. The recorded indicator licenses support the selected charts; do not extend that result to other OWID charts automatically.

The repository's build checks a license allowlist and attribution fields. It cannot establish third-party ownership, consent or legal rights. The README now makes that limit explicit. Dataset source links, code-repository license labels, embedded notices and attribution must travel with exports.

## Release recommendation

Keep the repository private until the source-term and history decisions above are resolved. Publish a reviewed v4 snapshot through the protected PR path; keep archived v3 out unless its additional terms are deliberately accepted and documented. The previously exposed local provider key still needs rotation. No raw downloaded dataset, local run, credential or public release was uploaded during this follow-up.
