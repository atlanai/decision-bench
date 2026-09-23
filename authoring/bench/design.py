"""design: icons and screens.

DSN-1  What does this icon mean?   Material Symbols (Google, Apache-2.0), the icon's own name in the repository.
       One icon rendered black-on-white at 256×256 px; four icon names from the same category of the set, exactly
       one of which is the icon shown. Requires vision: the text state carries no description of the glyph.

Dropped tasks (see the design report): "What is this screen for?" (Enrico), "Which element is this?" (Rico view
hierarchies / VINS) and "Does this text pass contrast guidelines?" all rest on Rico screenshots. Rico's terms
(interactionmining.org/archive/rico/copyright.txt) are a research indemnity agreement, not a licence: the
screenshots "may contain copyrighted work" and the downloader indemnifies the university. Redistribution,
including commercial, cannot be established, so no Rico-derived image is in this module.

Written sampling rules for DSN-1
- Source: github.com/google/material-design-icons at commit MDI_COMMIT. The category of an icon is the prefix
  of its key in update/current_versions.json ("action::delete"); the glyph is
  symbols/web/<name>/materialsymbolsoutlined/<name>_24px.svg.
- Pool: POOL below, a hand allowlist of icons whose plain-words name is what a general reader would call the
  picture (a plane, a folder, a padlock). Excluded on purpose: pure abstract shapes (chevrons, dots, toggles),
  jargon names ("wb_sunny", "camera_alt", "insert_drive_file"), style variants ("*_outline", "*_border") and,
  within one category, glyphs a reader could confuse (park vs forest, sailing vs directions_boat, wine_bar vs
  local_bar, undo vs reply). Every pool entry is checked at build time against current_versions.json.
- Rows: every pool icon ordered by rank(name); the first TARGET that pass, with at most CAP per category and only
  if three distractors exist. Distractors: the other pool icons of the same category that share no underscore-
  separated word with the answer (so "cloud_upload" never sits next to "cloud_download"), ordered by
  rank("<answer>:<candidate>"), first three. Option keys are the icon names; descriptions are the names in plain
  words.
- Rendering: the SVG's width/height are set to 256 (and viewBox="0 0 24 24" added to the few icons that lack a
  viewBox) and the file is rasterised black on white by rsvg-convert, headless Chrome or macOS Quick Look,
  whichever is installed. Nothing else in the record is changed.
"""
from __future__ import annotations

import json
import shutil
import struct
import subprocess
from pathlib import Path

from . import dataset, task, row, rank, ROOT, SOURCES as SOURCE_DIR, ASSETS

# ---------------------------------------------------------------- source

MDI_COMMIT = "27e9ef1dbeedc13d682fece4a58e1eda4cb0961a"  # master on 2026-09-18
MDI_REPO = "https://github.com/google/material-design-icons"
MDI_RAW = f"https://raw.githubusercontent.com/google/material-design-icons/{MDI_COMMIT}"
MDI_DIR = "material-symbols"


def _svg_rel(name):
    return f"symbols/web/{name}/materialsymbolsoutlined/{name}_24px.svg"


# category -> icon names (see the module docstring for the allowlist rule). Categories are the classic Material
# Icons categories, which the repository keeps for the 2,209 icons that predate Material Symbols.
POOL = {
    "action": ["delete", "search", "home", "settings", "favorite", "lock", "visibility", "print", "shopping_cart",
               "alarm", "thumb_up", "calendar_today", "schedule", "bug_report", "pets", "work", "bookmark", "zoom_in",
               "credit_card", "account_balance", "fingerprint", "lightbulb", "savings", "receipt", "rocket_launch",
               "anchor", "shopping_bag", "help", "shopping_basket"],
    "image": ["photo_camera", "edit", "palette", "brush", "crop", "flash_on", "image", "landscape", "timer",
              "music_note", "bedtime", "rotate_left"],
    "device": ["bluetooth", "battery_full", "light_mode", "dark_mode", "flashlight_on", "usb", "thermostat",
               "medication", "cable"],
    "maps": ["flight", "restaurant", "hotel", "local_hospital", "directions_car", "directions_bike", "directions_boat",
             "directions_bus", "train", "map", "local_cafe", "local_pizza", "local_gas_station", "local_taxi",
             "local_bar", "two_wheeler", "museum", "forest", "castle", "factory", "fire_truck", "local_shipping",
             "traffic", "lunch_dining", "icecream", "ramen_dining", "bakery_dining", "medical_services",
             "local_fire_department", "pedal_bike", "electric_car", "agriculture", "local_police", "theater_comedy",
             "diamond", "egg"],
    "social": ["share", "person", "group", "notifications", "cake", "school", "sports_soccer", "sports_basketball",
               "sports_tennis", "mood", "public", "luggage", "science", "piano", "recycling", "cookie", "surfing",
               "hiking", "water_drop", "thunderstorm", "volcano", "waving_hand"],
    "av": ["videocam", "mic", "volume_up", "volume_off", "play_arrow", "pause", "stop", "skip_next", "fast_forward",
           "radio", "hearing", "movie", "album", "speed"],
    "editor": ["attach_file", "format_bold", "format_italic", "format_underlined", "pie_chart", "bar_chart",
               "format_list_bulleted", "checklist", "format_quote", "table_chart", "scatter_plot", "draw"],
    "communication": ["call", "chat", "qr_code", "dialpad", "location_on", "cell_tower", "rss_feed", "contacts", "key",
                      "voicemail"],
    "hardware": ["keyboard", "mouse", "headphones", "smartphone", "watch", "router", "speaker", "sim_card", "earbuds",
                 "scanner"],
    "places": ["umbrella", "fitness_center", "casino", "kitchen", "golf_course", "room_service", "apartment", "bathtub",
               "stairs", "elevator", "microwave", "iron", "stroller", "storefront", "fire_extinguisher", "pool", "house",
               "grass", "fence", "balcony", "crib", "soap"],
    "content": ["mail", "link", "save", "shield", "flag", "undo", "redo", "block", "archive", "calculate", "push_pin",
                "bolt", "backspace", "tag", "send", "add"],
    "notification": ["wifi", "power", "live_tv", "support_agent"],
    "navigation": ["refresh", "fullscreen", "menu", "close", "check", "arrow_back", "arrow_upward", "apps", "campaign"],
    "file": ["cloud_upload", "cloud_download", "folder", "download", "upload", "cloud", "newspaper", "attachment"],
    "home": ["sunny", "snowing", "foggy", "shelves", "curtains", "solar_power", "wind_power", "oil_barrel",
             "propane_tank"],
    "search": ["bed", "chair", "coffee", "door_front", "doorbell", "garage", "light", "shower", "window", "blender",
               "podcasts", "flatware"],
}
CAP, TARGET = 3, 30


def _words(name):
    return set(name.split("_"))


def _plain(name):
    return name.replace("_", " ")


def _distractors(category, name):
    others = [n for n in POOL[category] if n != name and not (_words(n) & _words(name))]
    others.sort(key=lambda n: rank(f"{name}:{n}"))
    return others[:3]


def _select():
    """The DSN-1 rows: (name, category, distractors), by the written rule; static, so SOURCES can list the SVGs."""
    candidates = sorted(((n, c) for c, names in POOL.items() for n in names), key=lambda t: rank(t[0]))
    per_category, chosen = {}, []
    for name, category in candidates:
        if per_category.get(category, 0) >= CAP:
            continue
        distractors = _distractors(category, name)
        if len(distractors) < 3:
            continue
        chosen.append((name, category, distractors))
        per_category[category] = per_category.get(category, 0) + 1
        if len(chosen) == TARGET:
            break
    return chosen


CHOSEN = _select()

SOURCES = [
    {"dataset": "Material Symbols", "url": f"{MDI_RAW}/LICENSE", "path": f"{MDI_DIR}/LICENSE"},
    {"dataset": "Material Symbols, icon list with categories", "url": f"{MDI_RAW}/update/current_versions.json",
     "path": f"{MDI_DIR}/current_versions.json"},
    *({"dataset": "Material Symbols, icon", "url": f"{MDI_RAW}/{_svg_rel(name)}", "path": f"{MDI_DIR}/svg/{name}.svg"}
      for name, _, _ in CHOSEN),
]


# ---------------------------------------------------------------- rendering

SIZE = 256


def _renderer():
    if shutil.which("rsvg-convert"):
        return "rsvg-convert"
    for chrome in (shutil.which("google-chrome"), shutil.which("chromium"), shutil.which("chromium-browser"),
                   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"):
        if chrome and Path(chrome).exists():
            return chrome
    if shutil.which("qlmanage"):
        return "qlmanage"
    raise RuntimeError("DSN-1 needs rsvg-convert, Chrome/Chromium or macOS qlmanage to rasterise the icon SVGs")


def _render(svg_path: Path, png_path: Path):
    """Rasterise one Material Symbols SVG to a SIZE×SIZE black-on-white PNG. Only the width/height change."""
    svg = svg_path.read_text()
    assert 'height="24"' in svg and 'width="24"' in svg, f"{svg_path}: unexpected SVG size"
    scaled = svg.replace('height="24"', f'height="{SIZE}"', 1).replace('width="24"', f'width="{SIZE}"', 1)
    if "viewBox=" not in scaled:  # a few older icons have no viewBox; their path is on the 24-unit grid
        scaled = scaled.replace("<svg ", '<svg viewBox="0 0 24 24" ', 1)
    work = svg_path.parent.parent / "render"
    work.mkdir(parents=True, exist_ok=True)
    tmp_svg = work / svg_path.name
    tmp_svg.write_text(scaled)
    png_path.parent.mkdir(parents=True, exist_ok=True)
    tool = _renderer()
    if tool == "rsvg-convert":
        subprocess.run(["rsvg-convert", "-w", str(SIZE), "-h", str(SIZE), "-b", "white", "-o", str(png_path),
                        str(tmp_svg)], check=True)
    elif tool == "qlmanage":
        subprocess.run(["qlmanage", "-t", "-s", str(SIZE), "-o", str(work), str(tmp_svg)], check=True,
                       capture_output=True)
        (work / (tmp_svg.name + ".png")).replace(png_path)
    else:
        subprocess.run([tool, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                        f"--window-size={SIZE},{SIZE}", "--default-background-color=ffffffff",
                        f"--screenshot={png_path}", tmp_svg.as_uri()], check=True, capture_output=True)
    assert png_path.is_file(), f"render failed for {svg_path.name}"


def _png_size(path: Path):
    head = path.read_bytes()[:24]
    assert head[:8] == b"\x89PNG\r\n\x1a\n" and head[12:16] == b"IHDR", f"{path}: not a PNG"
    return struct.unpack(">II", head[16:24])


# ---------------------------------------------------------------- datasets

def _datasets():
    dataset(
        id="material-symbols",
        name="Material Symbols (google/material-design-icons)",
        tasks=["DSN-1"],
        homepage=MDI_REPO,
        license="Apache-2.0",
        license_url=f"{MDI_REPO}/blob/{MDI_COMMIT}/LICENSE",
        content=("One icon of Google's Material Symbols set, the outlined-style 24 px SVG from symbols/web/<name>/ at the "
                 "pinned commit, rasterised black on white at 256×256 px."),
        content_license="Apache-2.0",
        content_terms=(f"The icons are Google's own designs, released with the repository under the Apache License 2.0 "
                       f"({MDI_REPO}/blob/{MDI_COMMIT}/LICENSE); the same set is served by Google Fonts "
                       "(fonts.google.com/icons) under Apache-2.0. No third-party logos are in the set."),
        labelled_by=("the icon's own name and category in the repository: the folder symbols/web/<name>/ and the key "
                     "'<category>::<name>' in update/current_versions.json"),
        changes=("The SVG's width and height attributes were set from 24 to 256 (viewBox='0 0 24 24' added where the "
                 "file had none) and the file rasterised black on white "
                 "(headless Chrome on the authoring machine; rsvg-convert or Quick Look otherwise). Nothing else was "
                 "changed; distractor names are other icons of the same category."),
        selection=("A hand allowlist of icons whose plain-words name is what a general reader would call the picture "
                   "(no abstract shapes, jargon names or style variants; no two confusable glyphs in one category), "
                   "ordered by sha256 of the icon name, at most three per category, first 30. Distractors are the "
                   "first three same-category pool icons by sha256 of 'answer:candidate' sharing no word with the answer."),
        citation=f"Google. Material Symbols. github.com/google/material-design-icons, commit {MDI_COMMIT[:7]} (2026-09-18).",
        bibtex=f"""@misc{{material_symbols,
  title        = {{Material Symbols}},
  author       = {{{{Google}}}},
  howpublished = {{\\url{{https://github.com/google/material-design-icons}}}},
  year         = {{2026}},
  note         = {{Commit {MDI_COMMIT}, Apache License 2.0}}
}}""",
    )


# ---------------------------------------------------------------- DSN-1

def _categories():
    """name -> set of categories, from the repository's own listing at the pinned commit."""
    versions = json.loads((SOURCE_DIR / MDI_DIR / "current_versions.json").read_text())
    out = {}
    for key in versions:
        category, name = key.split("::", 1)
        out.setdefault(name, set()).add(category)
    return out


def _dsn1():
    categories = _categories()
    for category, names in POOL.items():
        for n in names:
            assert category in categories.get(n, ()), f"DSN-1 pool: {n!r} is not in category {category!r} upstream"
    assets_dir = ASSETS / "design"
    for i, (name, category, distractors) in enumerate(CHOSEN, 1):
        svg_path = SOURCE_DIR / MDI_DIR / "svg" / f"{name}.svg"
        png_path = assets_dir / f"dsn-1-{name}.png"
        if not png_path.is_file():
            _render(svg_path, png_path)
        width, height = _png_size(png_path)
        options = {n: _plain(n) for n in sorted([name, *distractors], key=rank)}
        row(
            "DSN-1", name,
            title=f"Icon · Material Symbols outlined · 24 px grid · #{i:02d}",
            state={
                "image": "an icon from a standard icon set (Material Symbols, outlined style, 24 px design grid), "
                         f"drawn black on white at {width}×{height} px",
                "candidate_names": [_plain(n) for n in options],
                "text_rendering": "none: the glyph carries no text, so this row cannot be decided without the image",
            },
            gold=name,
            options=options,
            rationale=(f"The record is the Material Symbols icon whose official name is “{_plain(name)}” "
                       f"(key {category}::{name} in the repository's update/current_versions.json); the other three "
                       f"names are other icons of the {category} category."),
            source={
                "dataset_id": "material-symbols",
                "dataset": "Material Symbols (google/material-design-icons)",
                "license": "Apache-2.0",
                "url": f"{MDI_REPO}/blob/{MDI_COMMIT}/{_svg_rel(name)}",
                "citation": f"Google, Material Symbols, commit {MDI_COMMIT[:7]}",
                "record_id": name,
                "original_label": f"{category}::{name}",
                "labelled_by": "the icon's own name in the repository",
                "category": category,
            },
            assets=[{
                "path": str(png_path.relative_to(ROOT)),
                "mime_type": "image/png",
                "alt_text": "A single black glyph from the Material Symbols outlined icon set, centred on a white square.",
                "width": width, "height": height,
            }],
            note=f"Rendered from {_svg_rel(name)} at commit {MDI_COMMIT[:7]}; the name is Google's own.",
            tags=["icon", "vision-required", category],
        )


def define():
    _datasets()
    task("DSN-1", category="design", name="What does this icon mean?",
         ask="Which of these names is this icon's official name?",
         instruction=("The image is one icon from Google's Material Symbols set, drawn in the outlined style, black on a "
                      "white square. Four icon names from the same category of the set are offered; exactly one is the "
                      "official name of the icon shown. Decide from what the glyph depicts. This task requires vision: "
                      "the text state describes the format only, not the glyph."),
         options={}, per_row_options=True,
         shape="classify", input_type="icon image", modality="image", expertise="none",
         contamination="high", label_origin="objective record")
    _dsn1()
