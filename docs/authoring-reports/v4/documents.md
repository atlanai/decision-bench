# documents module report (Decision Bench v4)

Module: `authoring/bench/documents.py`. Assets: `data/assets/documents/` (30 JPEGs, 3.9 MB). Sources:
`data/sources/doclaynet/` (18 rows-API windows, 47 MB) and `data/sources/ami/ami_public_manual_1.6.2.zip` (23 MB).
`python3 scripts/fetch_sources.py --only documents` and `python3 scripts/build_bench.py --dry-run --only documents`
both pass; the dry run ends with `"problems": []`. Nothing outside the module, its assets and its source folders
was edited. No commit made.

## Tasks built

| Task | Name | Rows | Answer balance | Source |
| --- | --- | --- | --- | --- |
| DOC-1 | Where is this page from? (text+image) | 30 | 5 each: financial_report, scientific_article, law_or_regulation, government_tender, manual, patent | DocLayNet v1.2 |
| DOC-2 | Decision, action item, or neither? | 30 | decision 10, action_item 10, neither 10 | AMI manual annotations |
| DOC-3 | Which summary is this meeting's? | 27 | a 6, b 9, c 6, d 6 | AMI abstractive summaries |

State sizes (chars, min/median/max): DOC-1 908/2,850/5,354; DOC-2 1,127/1,325/2,227; DOC-3 6,120/7,936/9,964.
DOC-3 is over the 5,000-character median because a row must carry four whole annotator summaries plus a
transcript excerpt long enough to identify the meeting stage; the excerpt is capped at 3,500 characters.

Task ids were renumbered after the RVL-CDIP task was dropped (see below): the brief's DOC-2/3/4 are DOC-1/2/3 here.

## Licence evidence

**DocLayNet v1.2** (DOC-1)
- Dataset card, licence "CDLA-Permissive-1.0": https://huggingface.co/datasets/docling-project/DocLayNet-v1.2
- Repository LICENSE (full CDLA-Permissive-1.0 text): https://raw.githubusercontent.com/DS4SD/DocLayNet/main/LICENSE
- Content: the paper (arXiv 2206.01062, section 3) says documents were chosen under "open intellectual property
  constraints" and that "a large effort went into ensuring that all documents are free to use"; sources named are
  SEC filings and annual reports, arXiv, government websites, patent offices, IBM manuals and EU tenders. I treat
  IBM's CDLA-Permissive release as covering the page images and text cells (content_license = CDLA-Permissive-1.0).
  Maintainer judgement call: arXiv authors keep copyright in their papers; DocLayNet's assertion that the documents
  are free to use is what we rely on for the five scientific_article rows.

**AMI Meeting Corpus, manual annotations 1.6.2** (DOC-2, DOC-3)
- Licence page: https://groups.inf.ed.ac.uk/ami/corpus/license.shtml (CC BY 4.0)
- LICENCE.txt inside the annotation zip: "The AMI corpus and its annotations are released under the Creative Commons
  Attribution 4.0 International Public License".
- Download page: https://groups.inf.ed.ac.uk/ami/download/ (ami_public_manual_1.6.2.zip, 22.9 MB)
- Consent: https://groups.inf.ed.ac.uk/ami/corpus/ethicsandconsent.shtml. Speakers appear only as role plus channel
  letter (e.g. "Project Manager (A)"); first names spoken inside utterances are left as the corpus publishes them.

## Dropped

**"What kind of document is this page?" on RVL-CDIP** — dropped for licence. The Hugging Face card
(https://huggingface.co/datasets/aharley/rvl_cdip) marks the licence "other" and points to the UCSF Industry
Documents Library. Its copyright page (https://www.industrydocuments.ucsf.edu/help/copyright/, rendered in a
browser because the site is a JavaScript app) says the companies or individuals who created the documents "may
still hold the rights", that material "cannot be 'substantially' reproduced in books or other media without the
copyright holder's permission", and that use is governed by fair use. That is not a redistribution licence, so no
RVL-CDIP row, image or OCR text was built. (Separately, the dataset viewer is disabled on aharley/rvl_cdip, and the
mirrors with a viewer inherit the same terms.) No tesseract or PIL was present on this machine, which did not matter
in the end: DocLayNet ships its own text cells and its images are already within the size limits.

**Presentations (item 5)** — nothing built. Candidates checked:
- SlideAudit (arXiv 2508.03630, CC BY 4.0 labels): slides come from a US government slide-deck set (likely public
  domain), publicly shared Google Slides decks (no licence from the deck authors) and Gemini-synthesised slides (not
  real records). Only the government subset could qualify, and the labels are design-flaw categories, not document
  decisions. Worth a look if a "which slide design flaw" task is wanted; the licence of the government subset would
  need checking deck by deck.
- SPaSe (slide segmentation, CC BY 4.0 labels) uses Slideshare-1M images, whose decks are not openly licensed.
- SlideTailor-PSP and Datacluster Labs samples: annotations CC BY 4.0, underlying decks not open or a commercial
  sample. No open-licence dataset of real slide decks with usable labels was found.

## Judgement calls to review

1. **DOC-1 law rows avoid the FAA collection.** DocLayNet files FAA orders and handbooks under laws_and_regulations,
   but those pages read as manuals as much as regulations. Law rows come from the German (gesetze-im-internet),
   Botswana, Chinese and Japanese statute collections; a script filter (60% Latin letters) removed Russian pages so a
   generalist can read them. Three German pages remain (headed "...verordnung", "...gesetz", with the federal
   ministry banner); a reader who cannot read German still sees a statute layout, but flag if you disagree.
2. **DOC-1 rationale** quotes DocLayNet's doc_category and collection name plus the page's first heading; file
   names, collection names and page numbers are kept out of the state and only appear in `source` and `note`.
3. **DOC-2 rules were tightened after review** (all written in the module docstring): three-word stemmed overlap
   between the utterance and the linked summary sentence; action sentences must name who will act ("The industrial
   designer will ..."); decision utterances may not be hedged ("maybe", "I think", "could") and may not be the
   project brief's money constraints (price, cost, profit, Euro), because annotators filed the PM's kick-off
   announcement of those constraints inconsistently as decisions or as background; "neither" utterances exclude
   commitment, planning and constraint words. Two rows a maintainer may still want to eyeball: the Marketing
   Expert's list "Yeah a audio settings, mono, stereo, pitch, bass, treble. Screen settings, brightness and colour."
   (linked to the decision that advanced functions go on the screen) and "which you can recharge through the
   docking station." (a clause the annotators linked to the rechargeable-battery decision).
4. **DOC-3 distractors are the same team's other three meetings.** A first build used other teams' meetings; since
   every AMI scenario team follows the same script, same-stage summaries from different teams were near-identical
   and not one defensible answer. Using the same series (kick-off, functional, conceptual, detailed design) makes
   the reader identify the meeting stage from the excerpt. Meeting ids are kept out of DOC-3 titles and states
   because the trailing letter encodes the stage. 27 rows passed the overlap filter (true summary shares at least 4
   distinctive words with the excerpt and beats every distractor by 2); relaxing the margin would add rows at the
   cost of defensibility.
5. **Contamination**: AMI transcripts and summaries are widely published, so DOC-3 is marked high and DOC-2 medium
   (the utterance-to-summary links are not a published task). DocLayNet is medium.
6. **Fetching**: the datasets-server rows API returned HTTP 429 several times under `fetch_sources.py`'s eight
   parallel downloads, so I pre-downloaded the 18 windows with backoff into the exact `SOURCES` paths and let the
   script verify them. A maintainer re-fetching from scratch should use `--jobs 1` or expect retries. The signed
   image URLs in the windows expire after about an hour; `python3 -m authoring.bench.documents` (prepare_assets)
   must run soon after a fresh fetch, or re-request the single row for a fresh URL as I did for three replacements.
   Images are stored unmodified (dataset JPEGs, 1025x1025, 40–240 KB).
7. **Hashes are not pinned** (as instructed); `data/sources/manifest.json` was not touched.
