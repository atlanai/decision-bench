# Dataset and privacy review — 2026-09-23

**Outcome:** the source and privacy review of the published v4 corpus is complete, with the notes below still open. It is not a blanket legal clearance. No benchmark row or answer was silently changed.

## Scope and evidence

- Screened all **1,071 v4 rows** for email, telephone and US SSN patterns. The [machine-readable evidence](data-release-review.json) contains corpus hashes, row IDs and match counts, never matched contact values.
- Retrieved and inspected the license evidence for all **36 active sources**. One SEC endpoint rejected the script; its official policy was inspected through the web reader. Fixed the Congress license link: the data lives on a generated branch that has no LICENSE; the license now points to a verified main-branch commit.
- Rechecked underlying license metadata for **all 16 OWID charts**: observed CC BY 4.0 and CC BY 3.0 IGO declarations. Preserve the data-provider attribution already present in the chart images and rows. Auxiliary geographic/annotation columns are not separately licensed evidence for the numerical series.
- Visually inspected contact sheets covering **106 unique corpus images**: 30 receipts, 30 document pages, 30 icons and 16 charts, referenced by 122 rows. Receipt identifiers are visibly blurred; document pages contain public publication material and attribution. This was not forensic OCR or a pixel-by-pixel search.
- Inspected image metadata. The 30 receipt images' EXIF contains color space and dimensions, with no GPS/camera/author fields observed. No attempt was made to recover redacted content.

## Open notes

| Item | Evidence and affected scope | Handling |
| --- | --- | --- |
| deepset license declarations | The [pinned card](https://huggingface.co/datasets/deepset/prompt-injections/blob/4f61ecb038e9c3fb77e21034b22511b523772cdd/README.md) has top-level Apache-2.0 and nested CC-BY-4.0 declarations; 16 rows | Both declarations and the attribution are preserved. Both licenses are permissive and no noncommercial restriction was found; a clarification, or an exclusion in a new corpus version, is needed before describing the data as Apache-only. |
| Notice packaging | Code excerpts have per-repository license references; Wikipedia-derived rows include share-alike material | Retain original notices and all applicable dataset/content licenses in any redistributed package. A dataset-level MIT label cannot replace the original code license; a CC-BY-SA-3.0 table cannot relabel CC-BY-SA-4.0 questions. |

The corpus is frozen. Excluding or redacting rows requires a new corpus version and hash, not an in-place edit that invalidates comparisons.

## Privacy dispositions

| Area | Review result |
| --- | --- |
| Active email-like strings | 34 rows flagged. Contexts are AgentDojo/tau-bench benchmark environment contacts, a CredData example-domain placeholder, and code instance-name syntax. No private operator contact was established. Benchmark identities can resemble real addresses; do not treat them as actual customer records or contact them. |
| Active telephone-like strings | Two rows flagged: a product's public customer-service number and a company's public filing contact. They are business contact details, not evidence of a private individual's phone. |
| SSN patterns | No matches in any state field. This is a pattern result, not proof that no personal identifiers exist. |
| Contract text | Existing authoring redaction removes email and phone/fax details. No active email/phone-pattern hits in the contract rows. Names and organization names can still appear in public contracts. |
| Consumer complaints | Public CFPB narratives retain upstream masking. Their public origin does not remove the possibility of contextual identification; preserve the removal-request route. |
| Meeting transcripts | AMI speakers are represented by role/channel. The publisher documents [ethics and participant consent procedures](https://groups.inf.ed.ac.uk/ami/corpus/ethicsandconsent.shtml). |
| Vendor marks | Logos identify vendors in the viewer. They remain vendor property and must not imply endorsement; they are not covered by the code's MIT license. |

## License interpretation corrections

The [SEC FAQ](https://www.sec.gov/about/webmaster-frequently-asked-questions) and [dissemination policy](https://www.sec.gov/about/privacy-information#dissemination) support reuse of public filing content. That is more precise evidence than claiming every privately authored filing is a US-government work in the public domain. Existing frozen metadata uses the older shorthand; downstream distributors should cite the actual reuse policy and retain the corpus/annotation terms.

For charts, [OWID's reuse guidance](https://ourworldindata.org/faqs) distinguishes its work from third-party data. The recorded indicator licenses support the selected charts; do not extend that result to other OWID charts automatically.

The repository's build checks a license allowlist and attribution fields. It cannot establish third-party ownership, consent or legal rights. The README now makes that limit explicit. Dataset source links, code-repository license labels, embedded notices and attribution must travel with exports.
