# Design category (authoring/bench/design.py) — report

Module: /Users/rohan/GitHub/decision-bench/authoring/bench/design.py
Assets: /Users/rohan/GitHub/decision-bench/data/assets/design/dsn-1-<name>.png (30 files, 256×256, 0.9–9 KB each, 180 KB total)
Sources: data/sources/material-symbols/ (LICENSE, current_versions.json, svg/<name>.svg for the 30 chosen icons, render/ scratch copies)

`python3 scripts/fetch_sources.py --only design` and `python3 scripts/build_bench.py --dry-run --only design` both pass, "problems": [].

## Tasks built

### DSN-1 "What does this icon mean?" — 30 rows, image modality, per-row options

One Material Symbols icon (outlined style, 24 px grid) rasterised black on white at 256×256, plus four icon names from the
same category of the set (option keys = the icon names, descriptions = the names in plain words). Gold = the icon's own
name in the repository. label_origin "objective record", expertise "none", contamination "high" (Material icons are
everywhere in training data).

Answer balance: every row has a different answer (30 distinct icons), so no option is the answer more than once.
Category spread (cap 3 per category): content 3, action 3, image 3, places 3, maps 3, social 3, av 3, search 3, device 2,
file 1, notification 1, home 1, navigation 1 (13 of the 16 pooled categories; communication, editor, hardware simply did
not reach the top 30 by rank).

Rows (answer): mail, work, brush, storefront, folder, flight, usb, iron, volcano, factory, play_arrow, shield, traffic,
push_pin, power, skip_next, door_front, rotate_left, lock, stairs, podcasts, sports_tennis, help, flashlight_on, palette,
piano, propane_tank, check, garage, mic. I rendered a labelled contact sheet of all 30 with their distractors and checked
each glyph is the plain thing its name says and none of its three distractors could be argued for.

Rendering: headless Google Chrome 153 (`--headless=new --screenshot`) on this Mac; rsvg-convert and cairosvg are not
installed, PIL is not installed. The module prefers rsvg-convert if present, then Chrome/Chromium, then macOS `qlmanage`.
The only edits to the SVG are width/height 24 → 256 and, for the few legacy icons with no viewBox (push_pin was one),
adding viewBox="0 0 24 24". PNG dimensions are read from the IHDR header, no image library needed. Rendering happens in
define() only when a PNG is missing, so the build is reproducible from the sources.

Text track: the state carries only "an icon from a standard icon set (Material Symbols, outlined style, 24 px design
grid), drawn black on white at 256×256 px", the four candidate names, and an explicit "text_rendering: none … cannot be
decided without the image". The task instruction says the task requires vision. Alt text is generic ("A single black
glyph from the Material Symbols outlined icon set, centred on a white square") because any faithful description of the
glyph would be the answer.

## Licence evidence

Material Symbols / Material Design Icons (google/material-design-icons), pinned commit 27e9ef1dbeedc13d682fece4a58e1eda4cb0961a
(master on 2026-09-18).
- Repository licence: Apache License 2.0 — https://github.com/google/material-design-icons/blob/27e9ef1dbeedc13d682fece4a58e1eda4cb0961a/LICENSE
  (fetched into data/sources/material-symbols/LICENSE; GitHub's licence API also reports spdx Apache-2.0).
- Content: the icons are Google's own designs released with the repository; the README states third-party logos are
  excluded from the set for legal reasons, so no trademarked glyph is in the pool. Google Fonts serves the same set as
  Apache-2.0 (https://fonts.google.com/icons).
- Categories come from the repository's own file update/current_versions.json (keys like "maps::flight"); the build
  asserts every pool icon really is in the category the pool claims.

## Dropped tasks and why

DSN-2 "What is this screen for?" (Enrico), DSN-3 "Which element is this?" (Rico view hierarchies / VINS), DSN-4 contrast:
all rest on Rico screenshots. Evidence read:
- https://interactionmining.org/rico links a "Copyright Notice": https://interactionmining.org/archive/rico/copyright.txt.
  It is a download agreement, not a licence. It opens "The screenshots contained in the Rico dataset may contain
  copyrighted work", disclaims non-infringement, makes the "Researcher" indemnify the Rico team and the University of
  Illinois for "use of any copies of copyrighted images", and lets the Researcher share only with colleagues who first
  agree to the same terms. Nothing grants redistribution, let alone commercial redistribution.
- Enrico (https://github.com/luileito/enrico) is MIT for its own files (design_topics.csv, code), but its screenshots.zip
  is Rico imagery of third-party Android apps and the README says nothing about the images' terms.
- Hugging Face re-hosts (creative-graphic-design/Rico, Voxel51/rico) state "The dataset license is not specified …
  verify the upstream terms before redistribution or commercial use" — re-hoster caveats, not a grant.
- VINS (sbunian/VINS) mixes Rico screenshots with other sources; same problem, and I could not read a licence file
  (GitHub API rate-limited; not pursued further since the Rico part already fails).
Beyond Rico's own terms, the screenshots depict copyrighted third-party app UIs, so the "content licence" test fails
regardless. No Rico-derived image, text or hierarchy is in the module.

## Judgement calls for a maintainer

1. Pool is a hand allowlist (POOL in the module), not the whole set. The brief asked for icons a general reader would
   know and no abstract shapes; that is inherently a curation step. The rule written in the docstring: plain-words name
   is what a reader would call the picture; no abstract shapes (chevrons, dots, toggles), no jargon names (wb_sunny,
   camera_alt, insert_drive_file), no style variants (*_outline, *_border), and within one category no two glyphs a
   reader could confuse (I excluded e.g. park vs forest, sailing vs directions_boat, wine_bar vs local_bar, undo vs reply,
   chat vs comment/forum, headset vs headphones, tablet vs smartphone, escalator vs stairs, beach_access vs umbrella).
   Within the pool, selection and distractors are purely by rank(); I never picked rows by hand.
2. Distractor rule: same category, no shared underscore-word with the answer (so cloud_upload never sits beside
   cloud_download, sports_tennis never beside sports_soccer), first three by rank("answer:candidate"). Cross-category
   look-alikes (e.g. "home" in action and "house" in places) never co-occur because options come from one category.
3. Categories are the classic Material Icons categories the repository keeps for the 2,209 pre-Symbols icons; the 4,403
   "symbols::" entries have no category and are not pooled. Four categories (toggle, alert, plus thin ones) have fewer
   than 4 plain-named icons and cannot yield rows; the rule "only if three distractors exist" handles this.
4. Titles are "Icon · Material Symbols outlined · 24 px grid · #NN" — the running number is there only because titles
   must be unique per task; it carries no information.
5. State per row differs only in "candidate_names" (the option list) — needed to satisfy the identical-state check; it
   leaks nothing beyond the options already shown.
6. The rows' `source` dict has an extra "category" key beyond the required fields; harmless, but remove if the schema is
   meant to be closed.
7. data/sources/material-symbols/render/ holds the scaled SVG copies used for rasterising; it is scratch and can be
   ignored or gitignored like the rest of data/sources.

## Other open-licence design datasets found (for future tasks)

Icon sets with a clear licence covering the glyphs themselves (licence file read from each repository's default branch):
- Font Awesome Free — icons CC BY 4.0 (LICENSE.txt: "Icons: CC BY 4.0"), fonts OFL, code MIT. Has categories/search
  terms in metadata; good second icon source.
- Tabler Icons — MIT. Lucide — ISC. Phosphor — MIT. Bootstrap Icons — MIT. Heroicons — MIT. Octicons — MIT.
  Fluent UI System Icons (Microsoft) — MIT. Ionicons — MIT. Feather — MIT. Iconoir — MIT.
- Remix Icon — Apache-2.0 (per its License file).
- Twemoji — graphics CC BY 4.0; OpenMoji — CC BY-SA 4.0; Noto Emoji — fonts OFL 1.1 (not in PERMISSIVE), artwork Apache-2.0.
  These could support "which emoji/icon is this" or "same concept, different set" comparisons.

UI-screenshot datasets: none cleared both tests.
- WebUI (Wu et al., CHI 2023; biglab/webui-7k on HF) — the project says CC BY 4.0 for the dataset, but the rows are
  screenshots of arbitrary crawled websites whose content is the sites' copyright; fails the content test.
- Google Screen Annotation (ScreenAI) — annotations CC BY 4.0, but the screenshots are Rico; fails.
- "Annotated UI Element Dataset for Desktop Environments" (Zenodo 10822752, CC BY 4.0) — 100+ desktop screenshots of
  PDF readers, Windows Explorer, email clients, a CRM and an LMS with element boxes; the depicted software UIs are
  third-party (Microsoft etc.), so the content test is doubtful; worth a maintainer's look only if the depicted apps
  turn out to be open-source.
- ShowUI-desktop / OmniAct / ScreenSpot / Aria-UI / Wave-UI — Apache/MIT dataset licences over screenshots of
  commercial apps and websites; same content problem.
- A promising route not yet explored: screenshots of open-source software with permissive licences (e.g. self-hosted
  WebArena sites, or apps whose own licence is MIT/Apache/BSD and whose sample screenshots ship in the repo), where the
  depicted UI is itself openly licensed. GPL-licensed app screenshots (most of F-Droid) would not fit PERMISSIVE.
