#!/usr/bin/env python3
"""Merigrove Thumbnail Builder: inspect, check, render and readability-test video thumbnails.

Everything with one right answer is done here, so the model never judges a size,
a contrast ratio or a word count by eye.

Subcommands
  fonts                     list the safe, open-licence bold fonts installed here
  inspect PHOTO [--out D]   size, photo or illustration, transparency; writes a grid
                            overlay (PHOTO-grid.png) so the face box can be read off
  colours IMAGE [--out D]   the main colours in a screenshot of a logo, site or brand sheet
  swatches NAME... [--out D] two or three candidate colours for a colour given by name
  check SPEC                validate a spec against the composition and honesty rules
  render SPEC [--svg]       draw every style at every size in the spec, run the
                            readability test, write the comparison sheet and notes
  test IMAGE [--out D]      readability test for a thumbnail the founder already has

Styles: panel (dark, slanted photo panel, oversized key word), poster (light background,
dark words, circular photo, boxed key word), cinema (full photo, words low in the shade),
cutout (person in front of the words), type (words only). Old names split, card and bleed
still work.

Spec (JSON; assets/spec-template.json has every field with comments)
  slug, title, hook, highlight, focal, focal_scale, photo, photo_kind, face_box, cutout,
  subject_side, brand {mode, colours, ground, accent, font, logo, named}, case,
  directions, sizes, promise, payoff, payoff_time, reasons {style: one line}, out_dir

Languages: the words may be in any script. Every character is looked up in the font's own character
map; if the founder's font lacks one, the best open-licence face that has them all is used and check
says so; if no installed font has them, check refuses rather than draw empty boxes. Scripts that join
or reorder letters (Arabic, Hebrew, the Indic scripts, Thai and others) need Pillow's raqm layout;
without it check refuses. Right-to-left words are set right to left; in Chinese, Japanese and Thai a
space in the hook marks a line break point and is not drawn. Optional spec field: lang (for example
ja, ko, zh-Hans, zh-Hant, tr) picks the regional letterforms and casing.

Exit codes: 0 clean; 1 problems found (or a readability FAIL); 2 bad input.
Pillow (PIL) is used when present. Without it, render writes editable SVG files
with geometric checks only, and says so. No network calls. Nothing is uploaded.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import math
import os
import re
import struct
import sys
import unicodedata

try:
    from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
    from PIL.PngImagePlugin import PngInfo
    HAVE_PIL = True
except Exception:  # Pillow missing: SVG fallback
    HAVE_PIL = False

CREDIT = "Made with Merigrove Thumbnail Builder"

# ---------------------------------------------------------------- sizes and rules

SIZES = {
    # name: (width, height, label, test widths for the readability sheet)
    "youtube": (1280, 720, "YouTube thumbnail 16:9", [360, 246, 168]),
    "widescreen": (1920, 1080, "16:9 at 1920 (LinkedIn, Vimeo, course platforms)", [360, 246, 168]),
    "square": (1080, 1080, "Square 1:1 (podcast episode, LinkedIn, X)", [300, 160, 110]),
    "vertical": (1080, 1920, "Vertical 9:16 cover (Shorts, Reels, TikTok)", [270, 180, 120]),
    "podcast": (3000, 3000, "Podcast show art 1:1 at 3000", [300, 160, 110]),
}
RULES = {
    "words_best": 3, "words_good": 5, "words_max": 6,
    "cap_px_pass": 8.0, "cap_px_warn": 6.0,          # cap height at the smallest test width
    "contrast_pass": 4.5, "contrast_warn": 3.0,       # text against what is behind it
    "squint_pass": 3.0, "squint_warn": 2.0,           # spread inside the hook box, blurred, at the smallest width
    "face_h_min": 0.35, "face_h_max": 0.75,           # face height as a share of frame height (16:9)
    "upscale_warn": 1.6,                              # output pixels per source pixel
    "youtube_max_bytes": 2 * 1024 * 1024,
    "short_side_min": 600,
}
# Where platform furniture sits, as fractions (x0, y0, x1, y1). Nothing essential goes here.
KEEP_CLEAR = {
    "16:9": [(0.80, 0.80, 1.0, 1.0)],                         # duration badge
    "1:1": [],
    "9:16": [(0.0, 0.80, 1.0, 1.0), (0.85, 0.45, 1.0, 1.0)],  # caption and action buttons
}
DIRECTIONS = {
    "panel": "Bold panel",
    "poster": "Poster",
    "cinema": "Cinematic",
    "cutout": "Cut-out",
    "type": "Words only",
}
ALIASES = {"split": "panel", "card": "poster", "bleed": "cinema"}
DEFAULT_REASONS = {
    "panel": "Dark and direct: your face on a slanted panel and the key word set larger, so it reads like a statement. Suits a method or a strong claim.",
    "poster": "Light and calm: your words in your darkest shade on your lightest, you in a framed circle. Stands apart in a dark feed and suits an explainer or a series.",
    "cinema": "The most personal: the photo fills the frame and the words sit low in the shade, like a film still. Suits a story or behind the scenes.",
    "cutout": "The loudest: you stand in front of the words on a flat background. Suits a reaction, a warning or a surprising result.",
    "type": "No face needed: the words and one number carry it, centred and large. Suits a list or a number-led video.",
}
PLAIN = {"ink": "#111111", "paper": "#FFFFFF", "accent": None}
OUTPUTS_DIR = "/mnt/user-data/outputs/thumbnails"
# Currency signs a hook may carry; none is a default. The founder's own currency comes from what they
# write. (Pound, dollar, euro, yen and yuan, rupee, won, peso, naira, lira, dong, baht, shekel, rouble,
# hryvnia, tenge, colon, guarani, cedi, kip, tugrik, manat, lari, rial, cent.)
CURRENCY = ("\u00a3$\u20ac\u00a5\u20b9\u20a9\u20b1\u20a6\u20ba\u20ab\u0e3f\u20aa\u20bd\u20b4\u20b8\u20a1\u20b2"
            "\u20b5\u20ad\u20ae\u20bc\u20be\ufdfc\u00a2")
DASHES = re.compile("[\u2013\u2014]")
ABSOLUTES = re.compile(r"\b(never|always|everyone|nobody|guaranteed?|secret|overnight|instantly|"
                       r"forever|best|worst|only|100%|zero|free)\b", re.I)

# ---------------------------------------------------------------- small helpers


def hex_rgb(h):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", h):
        raise ValueError(f"not a hex colour: {h!r}")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lum_rgb(rgb):
    r, g, b = rgb[:3]
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def ratio(l1, l2):
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def contrast_hex(a, b):
    return ratio(lum_rgb(hex_rgb(a)), lum_rgb(hex_rgb(b)))


def words(s):
    return [t for t in re.findall(r"\S+", s or "") if re.search(r"[\w%" + CURRENCY + r"]", t)]


def aspect_of(w, h):
    r = w / h
    if r > 1.2:
        return "16:9"
    if r < 0.8:
        return "9:16"
    return "1:1"


def numbers_in(text):
    return [x.replace(",", "") for x in re.findall(r"\d[\d,]*(?:\.\d+)?", text or "")]


# Short forms founders put on thumbnails: $10k, 2.5m, 3bn, 5 lakh, 2 crore, 10\u4e07. Attached letters
# (k, m, bn) must touch the number; words (lakh, crore, million) may follow a space.
MULTIPLIERS = {"k": 1e3, "m": 1e6, "mn": 1e6, "bn": 1e9, "b": 1e9, "thousand": 1e3, "million": 1e6,
               "billion": 1e9, "lakh": 1e5, "lakhs": 1e5, "lac": 1e5, "lacs": 1e5, "crore": 1e7, "crores": 1e7,
               "cr": 1e7, "\u0932\u093e\u0916": 1e5, "\u0915\u0930\u094b\u0921": 1e7, "\u0915\u0930\u094b\u0921\u093c": 1e7,
               "\u4e07": 1e4, "\u842c": 1e4, "\u5104": 1e8, "\u4ebf": 1e8, "\u5343": 1e3, "\ub9cc": 1e4,
               "\uc5b5": 1e8}
_NUM_FULL = re.compile(r"(\d[\d,]*(?:\.\d+)?)(?:(k|K|m|M|mn|bn|b|B|\u4e07|\u842c|\u5104|\u4ebf|\u5343|\ub9cc|\uc5b5)(?![A-Za-z])"
                       r"|\s?(thousand|million|billion|lakhs?|lacs?|crores?|cr)\b|\s?(\u0932\u093e\u0916|\u0915\u0930\u094b\u0921\u093c?))?",
                       re.I)


def number_claims(text):
    """Every number in the text with its value: (as written, value, abbreviated). '$10k' gives
    ('10k', 10000.0, True); '5,00,000' gives ('500000', 500000.0, False)."""
    out = []
    for m in _NUM_FULL.finditer(text or ""):
        raw = m.group(1).replace(",", "")
        try:
            v = float(raw)
        except ValueError:
            continue
        suf = (m.group(2) or m.group(3) or m.group(4) or "").lower()
        mult = MULTIPLIERS.get(suf, 1.0)
        out.append((raw + suf, v * mult, mult != 1.0))
    return out


def number_backed(claim, source):
    """Is a number on the thumbnail shown in the source text? Exact match, the same value written
    another way (10k and 10,000), or a short form rounded down from the real figure (10k for 10,400,
    never 10k for 9,600)."""
    raw, value, abbreviated = claim
    for r2, v2, _a in number_claims(source):
        if raw.lower() == r2.lower() or abs(v2 - value) < 1e-9:
            return True
        if abbreviated and value <= v2 < value * 1.10:
            return True
    return False


def image_size_noPIL(path):
    """(width, height) from a PNG or JPEG header, standard library only."""
    with open(path, "rb") as fh:
        head = fh.read(26)
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", head[16:24])
        fh.seek(0)
        if fh.read(2) != b"\xff\xd8":
            raise ValueError("not a PNG or JPEG")
        while True:
            b = fh.read(1)
            while b and b != b"\xff":
                b = fh.read(1)
            while b == b"\xff":
                b = fh.read(1)
            if not b:
                raise ValueError("no size marker found")
            marker = b[0]
            seglen = struct.unpack(">H", fh.read(2))[0]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                fh.read(1)
                h, w = struct.unpack(">HH", fh.read(4))
                return w, h
            fh.seek(seglen - 2, 1)


def image_size(path):
    if HAVE_PIL:
        with Image.open(path) as im:
            return im.size
    return image_size_noPIL(path)


# ---------------------------------------------------------------- fonts

FONT_DIRS = ["/usr/share/fonts", "/usr/local/share/fonts", "~/.fonts", "~/.local/share/fonts",
             "~/Library/Fonts", "/Library/Fonts", "/System/Library/Fonts/Supplemental", "C:/Windows/Fonts",
             "/usr/share/texmf/fonts/opentype/public"]
# Open-licence families only, best thumbnail faces first. Rendering text into an image does not
# distribute the font; the list exists so the skill never reaches for a font whose licence limits
# use (for example a platform's own UI font). A founder's own font file always comes first.
# The Latin faces come first; the script families after them are used only when the words need
# letters the Latin faces do not have (see pick_font).
SAFE_FAMILIES = [
    ("anton", "Anton", "OFL"), ("bebasneue", "Bebas Neue", "OFL"), ("archivoblack", "Archivo Black", "OFL"),
    ("montserrat", "Montserrat", "OFL"), ("inter", "Inter", "OFL"), ("poppins", "Poppins", "OFL"),
    ("oswald", "Oswald", "OFL"), ("worksans", "Work Sans", "OFL"), ("roboto", "Roboto", "Apache 2.0"),
    ("opensans", "Open Sans", "OFL"), ("lato", "Lato", "OFL"), ("sourcesans", "Source Sans", "OFL"),
    ("notosanscjk", "Noto Sans CJK", "OFL"), ("notosansjp", "Noto Sans JP", "OFL"),
    ("notosanskr", "Noto Sans KR", "OFL"), ("notosanssc", "Noto Sans SC", "OFL"), ("notosanstc", "Noto Sans TC", "OFL"),
    ("notosansdevanagari", "Noto Sans Devanagari", "OFL"), ("notosansbengali", "Noto Sans Bengali", "OFL"),
    ("notosanstamil", "Noto Sans Tamil", "OFL"), ("notosanstelugu", "Noto Sans Telugu", "OFL"),
    ("notosanskannada", "Noto Sans Kannada", "OFL"), ("notosansmalayalam", "Noto Sans Malayalam", "OFL"),
    ("notosansgujarati", "Noto Sans Gujarati", "OFL"), ("notosansgurmukhi", "Noto Sans Gurmukhi", "OFL"),
    ("notosansarabic", "Noto Sans Arabic", "OFL"), ("notokufiarabic", "Noto Kufi Arabic", "OFL"),
    ("notosanshebrew", "Noto Sans Hebrew", "OFL"), ("notosansthai", "Noto Sans Thai", "OFL"),
    ("notosanssinhala", "Noto Sans Sinhala", "OFL"), ("notosanskhmer", "Noto Sans Khmer", "OFL"),
    ("notosansmyanmar", "Noto Sans Myanmar", "OFL"), ("notosans", "Noto Sans", "OFL"),
    ("liberationsans", "Liberation Sans", "OFL"), ("texgyreheros", "TeX Gyre Heros", "GUST"),
    ("dejavusans", "DejaVu Sans", "Bitstream Vera (free)"), ("carlito", "Carlito", "OFL"),
    ("freesans", "FreeSans", "GPL with font exception"), ("loma", "Loma", "GPL with font exception"),
    ("wqyzenhei", "WenQuanYi Zen Hei", "GPL with font exception"),
]
WEIGHTS = [("black", 900), ("heavy", 900), ("extrabold", 800), ("ultrabold", 800), ("bold", 700)]
EXCLUDE = re.compile(r"italic|oblique|mono|condensed|display-?thin|light|thin|medium|semibold|"
                     r"extralight|serif|ui-", re.I)
SINGLE_WEIGHT = ("anton", "bebasneue", "archivoblack", "wqyzenhei")


def find_fonts():
    found = []
    for d in FONT_DIRS:
        d = os.path.expanduser(d)
        if not os.path.isdir(d):
            continue
        for root, _dirs, files in os.walk(d):
            for f in files:
                if not f.lower().endswith((".ttf", ".otf", ".ttc")):
                    continue
                key = re.sub(r"[^a-z]", "", f.lower())
                for i, (fam_key, fam, lic) in enumerate(SAFE_FAMILIES):
                    if not key.startswith(fam_key):
                        continue
                    base = f.lower()
                    if "display" in base and fam_key == "inter":
                        continue
                    weight = 0
                    for wname, wv in WEIGHTS:
                        if wname in key[len(fam_key):]:
                            weight = wv
                            break
                    variable = "variable" in base or "[" in base
                    if variable:
                        weight = 900
                    if fam_key in SINGLE_WEIGHT and weight == 0:
                        weight = 900 if fam_key != "wqyzenhei" else 600  # single-weight faces
                    if weight == 0 or (EXCLUDE.search(f) and not variable):
                        continue
                    found.append({"family": fam, "licence": lic, "weight": weight, "file": os.path.join(root, f),
                                  "rank": i, "variable": variable})
                    break
    found.sort(key=lambda x: (x["rank"], -x["weight"]))
    return found


# ---------------------------------------------------------------- scripts, glyphs and shaping
# A thumbnail must never show an empty box where a letter should be. Every character in the words is
# looked up in the font's own character map (read here with the standard library), and a font that
# lacks one is never used for those words.

SCRIPT_RANGES = [
    ("Latin", ((0x0041, 0x005A), (0x0061, 0x007A), (0x00C0, 0x024F), (0x1E00, 0x1EFF))),
    ("Greek", ((0x0370, 0x03FF),)), ("Cyrillic", ((0x0400, 0x052F),)),
    ("Hebrew", ((0x0590, 0x05FF), (0xFB1D, 0xFB4F))),
    ("Arabic", ((0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF), (0xFB50, 0xFDFF), (0xFE70, 0xFEFF))),
    ("Devanagari", ((0x0900, 0x097F),)), ("Bengali", ((0x0980, 0x09FF),)), ("Gurmukhi", ((0x0A00, 0x0A7F),)),
    ("Gujarati", ((0x0A80, 0x0AFF),)), ("Tamil", ((0x0B80, 0x0BFF),)), ("Telugu", ((0x0C00, 0x0C7F),)),
    ("Kannada", ((0x0C80, 0x0CFF),)), ("Malayalam", ((0x0D00, 0x0D7F),)), ("Sinhala", ((0x0D80, 0x0DFF),)),
    ("Thai", ((0x0E00, 0x0E7F),)), ("Lao", ((0x0E80, 0x0EFF),)), ("Myanmar", ((0x1000, 0x109F),)),
    ("Khmer", ((0x1780, 0x17FF),)), ("Hangul", ((0x1100, 0x11FF), (0x3130, 0x318F), (0xAC00, 0xD7AF))),
    ("Kana", ((0x3040, 0x30FF), (0x31F0, 0x31FF))),
    ("Han", ((0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xF900, 0xFAFF), (0x3000, 0x303F), (0xFF01, 0xFF60))),
    ("Emoji", ((0x1F000, 0x1FAFF), (0x2600, 0x27BF), (0xFE0F, 0xFE0F))),
]
RTL_SCRIPTS = {"Hebrew", "Arabic"}
# Scripts whose letters join, reorder or stack: drawn correctly only with a text shaping library
# (Pillow's raqm layout). Without it the letters come out unjoined or in the wrong order.
SHAPED_SCRIPTS = {"Arabic", "Hebrew", "Devanagari", "Bengali", "Gurmukhi", "Gujarati", "Tamil", "Telugu",
                  "Kannada", "Malayalam", "Sinhala", "Thai", "Lao", "Myanmar", "Khmer"}
# Scripts written without spaces between words: a space in the hook marks where a line may break and
# is not drawn between two such characters.
NO_SPACE_SCRIPTS = {"Han", "Kana", "Thai", "Lao", "Khmer", "Myanmar"}
# Scripts with marks above and below the letters need looser leading than Latin capitals.
TALL_SCRIPTS = {"Arabic", "Devanagari", "Bengali", "Gurmukhi", "Gujarati", "Tamil", "Telugu", "Kannada",
                "Malayalam", "Sinhala", "Thai", "Lao", "Myanmar", "Khmer"}
SQUARE_SCRIPTS = {"Han", "Kana", "Hangul"}
# The letter whose height stands in for "capital height" in each script, for the size check.
SIZE_GLYPH = {"Latin": "H", "Greek": "\u0397", "Cyrillic": "\u041d", "Hebrew": "\u05e9", "Arabic": "\u0643",
              "Devanagari": "\u0915", "Bengali": "\u0995", "Gurmukhi": "\u0a15", "Gujarati": "\u0a95",
              "Tamil": "\u0b95", "Telugu": "\u0c15", "Kannada": "\u0c95", "Malayalam": "\u0d15",
              "Sinhala": "\u0d9a", "Thai": "\u0e01", "Lao": "\u0e81", "Myanmar": "\u1000", "Khmer": "\u1780",
              "Hangul": "\ud55c", "Kana": "\u3042", "Han": "\u56fd"}
CJK_FACE = {"ja": "JP", "ko": "KR", "zh-hans": "SC", "zh-cn": "SC", "zh-sg": "SC", "zh": "SC",
            "zh-hant": "TC", "zh-tw": "TC", "zh-hk": "HK"}


def script_of(ch):
    o = ord(ch)
    for name, ranges in SCRIPT_RANGES:
        for a, b in ranges:
            if a <= o <= b:
                return name
    return None


def scripts_in(text):
    """The scripts in the text, most used first (digits, spaces and punctuation are neutral)."""
    counts = {}
    for ch in text or "":
        s = script_of(ch)
        if s:
            counts[s] = counts.get(s, 0) + 1
    return [s for s, _ in sorted(counts.items(), key=lambda kv: -kv[1])]


def main_script(text):
    """The script the hook is mostly written in; Latin when there is none (numbers only)."""
    ss = [s for s in scripts_in(text) if s != "Emoji"]
    non_latin = [s for s in ss if s != "Latin"]
    return non_latin[0] if non_latin else "Latin"


def is_rtl(text):
    return main_script(text) in RTL_SCRIPTS


def has_raqm():
    if not HAVE_PIL:
        return False
    try:
        from PIL import features
        return bool(features.check("raqm"))
    except Exception:
        return False


def hook_units(text):
    """How many words a hook reads as. Space-separated words count one each; in scripts written
    without spaces, about two characters (Chinese, Japanese) or three (Thai, Lao, Khmer, Burmese) make
    one word. A house working rule, so the three-to-five-word rule applies in every language."""
    n = 0
    for tok in (text or "").replace("|", " ").split():
        if not re.search(r"[\w%" + CURRENCY + r"]", tok):
            continue
        cjk = sum(1 for ch in tok if script_of(ch) in ("Han", "Kana"))
        sea = sum(1 for ch in tok if script_of(ch) in ("Thai", "Lao", "Khmer", "Myanmar")
                  and not unicodedata.category(ch).startswith("M"))
        n += max(1, math.ceil(cjk / 2) + math.ceil(sea / 3)) if (cjk or sea) else 1
    return n


_CMAP_CACHE = {}


def _sfnt_offsets(data):
    if data[:4] == b"ttcf":
        n = struct.unpack(">I", data[8:12])[0]
        return [struct.unpack(">I", data[12 + 4 * i:16 + 4 * i])[0] for i in range(n)]
    return [0]


def font_faces(path):
    try:
        with open(path, "rb") as fh:
            return len(_sfnt_offsets(fh.read(4096)))
    except Exception:
        return 1


def font_cmap(path, index=0):
    """The set of characters a font file can draw, read from its cmap table (formats 4 and 12, which
    every modern TrueType and OpenType font carries). Standard library only."""
    key = (path, index)
    if key in _CMAP_CACHE:
        return _CMAP_CACHE[key]
    cps = set()
    try:
        with open(path, "rb") as fh:
            data = fh.read()
        offs = _sfnt_offsets(data)
        off = offs[min(index, len(offs) - 1)]
        ntab = struct.unpack(">H", data[off + 4:off + 6])[0]
        cmap = None
        for i in range(ntab):
            rec = off + 12 + 16 * i
            if data[rec:rec + 4] == b"cmap":
                cmap = struct.unpack(">I", data[rec + 8:rec + 12])[0]
        if cmap is not None:
            nsub = struct.unpack(">H", data[cmap + 2:cmap + 4])[0]
            for i in range(nsub):
                pid, eid, so = struct.unpack(">HHI", data[cmap + 4 + 8 * i:cmap + 12 + 8 * i])
                if pid not in (0, 3) or (pid == 3 and eid not in (0, 1, 10)):
                    continue
                so += cmap
                fmt = struct.unpack(">H", data[so:so + 2])[0]
                if fmt == 4:
                    seg = struct.unpack(">H", data[so + 6:so + 8])[0] // 2
                    ends = struct.unpack(f">{seg}H", data[so + 14:so + 14 + 2 * seg])
                    p = so + 16 + 2 * seg
                    starts = struct.unpack(f">{seg}H", data[p:p + 2 * seg])
                    deltas = struct.unpack(f">{seg}h", data[p + 2 * seg:p + 4 * seg])
                    rop = p + 4 * seg
                    ros = struct.unpack(f">{seg}H", data[rop:rop + 2 * seg])
                    for k in range(seg):
                        s, e, dl, ro = starts[k], ends[k], deltas[k], ros[k]
                        if s == 0xFFFF:
                            continue
                        if ro == 0:
                            cps.update(c for c in range(s, e + 1) if (c + dl) & 0xFFFF)
                        else:
                            base = rop + 2 * k + ro
                            for c in range(s, e + 1):
                                a = base + 2 * (c - s)
                                gid = struct.unpack(">H", data[a:a + 2])[0] if a + 2 <= len(data) else 0
                                if gid and (gid + dl) & 0xFFFF:
                                    cps.add(c)
                elif fmt == 12:
                    ng = struct.unpack(">I", data[so + 12:so + 16])[0]
                    for g in range(ng):
                        s, e, sg = struct.unpack(">III", data[so + 16 + 12 * g:so + 28 + 12 * g])
                        cps.update(range(s if sg else s + 1, e + 1))
    except Exception:
        cps = set()
    _CMAP_CACHE[key] = cps
    return cps


BUNDLED_COVERAGE = set(range(0x20, 0x7F)) | set(range(0xA0, 0x100)) | {0x20AC}


def needed_chars(text):
    return sorted({ch for ch in (text or "") if not ch.isspace() and ch not in "|\u200c\u200d"})


def missing_in(path, text, index=0):
    cov = font_cmap(path, index) if path else BUNDLED_COVERAGE
    return [ch for ch in needed_chars(text) if ord(ch) not in cov]


_FACE_INDEX = {}


def _cjk_face(path, text, lang):
    """In a font collection (.ttc) of Chinese, Japanese and Korean faces, the face for this language.
    Without a language, kana means Japanese, hangul Korean, and Chinese characters alone Simplified."""
    n = font_faces(path)
    if n <= 1 or not HAVE_PIL:
        return 0
    want = CJK_FACE.get((lang or "").lower())
    if not want:
        ss = scripts_in(text)
        want = "JP" if "Kana" in ss else "KR" if "Hangul" in ss else "SC" if "Han" in ss else None
    if not want:
        return 0
    for i in range(n):
        try:
            fam = ImageFont.truetype(path, 20, index=i).getname()[0] or ""
        except Exception:
            continue
        if fam.endswith(" " + want) or (" " + want + " ") in fam:
            return i
    return 0


def pick_font(spec_font, text="", lang=None):
    """Choose the typeface for these words. Returns a dict: path (None means Pillow's bundled sans),
    desc, missing (characters no available font can draw) and swapped (the founder's font, when it
    lacked letters the words need and another face was used instead).

    Order: the founder's own file; an installed family they name; the best open-licence bold font
    installed here that has every character in the words; Pillow's bundled sans for plain Latin only."""
    fonts = find_fonts()
    swapped = None
    own = None
    if spec_font and os.path.isfile(spec_font):
        own = (spec_font, f"{os.path.basename(spec_font)} (the founder's own file)")
    elif spec_font:
        want = re.sub(r"[^a-z]", "", spec_font.lower())
        for f in fonts:
            if re.sub(r"[^a-z]", "", f["family"].lower()) == want:
                own = (f["file"], f"{f['family']} ({f['licence']}, installed here)")
                break
    if own:
        idx = _cjk_face(own[0], text, lang)
        if not missing_in(own[0], text, idx):
            _FACE_INDEX[own[0]] = idx
            return {"path": own[0], "desc": own[1], "missing": [], "swapped": None, "family": own[1]}
        swapped = own[1].split(" (")[0]
    for f in fonts:
        idx = _cjk_face(f["file"], text, lang)
        if not missing_in(f["file"], text, idx):
            _FACE_INDEX[f["file"]] = idx
            desc = f"{f['family']} ({f['licence']}, installed here)"
            if swapped:
                desc += f"; your font {swapped} has no glyphs for some of these letters"
            return {"path": f["file"], "desc": desc, "missing": [], "swapped": swapped, "family": f["family"]}
    if not missing_in(None, text):
        return {"path": None, "desc": "Pillow's bundled sans (no open-licence bold font found; emboldened with a stroke)",
                "missing": [], "swapped": swapped, "family": "sans-serif"}
    # Nothing here can draw every character: report what is missing against the best candidate.
    cand = own[0] if own else (fonts[0]["file"] if fonts else None)
    return {"path": cand, "desc": "no installed font covers these words", "missing": missing_in(cand, text),
            "swapped": swapped, "family": "sans-serif"}


_FONT_CACHE = {}


def load_font(path, size):
    key = (path, int(size))
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    if path:
        f = ImageFont.truetype(path, int(size), index=_FACE_INDEX.get(path, 0))
        try:
            names = [n.decode() if isinstance(n, bytes) else n for n in f.get_variation_names()]
            for want in ("Black", "ExtraBold", "Bold"):
                if want in names:
                    f.set_variation_by_name(want)
                    break
        except Exception:
            pass
    else:
        try:
            f = ImageFont.load_default(size=int(size))
        except TypeError:
            f = ImageFont.load_default()
    _FONT_CACHE[key] = f
    return f


def cap_height(font, script="Latin"):
    """Height of a capital H, or of the letter that plays that part in the hook's script."""
    g = SIZE_GLYPH.get(script, "H")
    try:
        b = font.getbbox(g)
        if b[3] - b[1] <= 0:
            b = font.getbbox("H")
        return b[3] - b[1]
    except Exception:
        return font.size * 0.72 if hasattr(font, "size") else 10


def text_w(font, s, stroke=0):
    if HAVE_PIL:
        b = font.getbbox(s, stroke_width=stroke)
        return b[2] - b[0]
    return len(s) * font * 0.58  # font is a size in the SVG path


# ---------------------------------------------------------------- colour roles




# ---------------------------------------------------------------- colour roles


def _sat(c):
    r, g, b = hex_rgb(c)
    return (max(r, g, b) - min(r, g, b)) / 255.0


def _norm(c):
    c = c.strip()
    return ("#" + c.lstrip("#")).upper()


def palette(spec):
    """Sort the founder's colours into dark, light and accent. Black and white are neutrals and are
    always available; no other colour is ever added."""
    b = spec.get("brand") or {}
    if (b.get("mode") or "plain").lower() != "brand" or not b.get("colours"):
        return {"mode": "plain", "dark": PLAIN["ink"], "light": PLAIN["paper"], "accents": [], "given": [],
                "poster_ground": PLAIN["paper"]}
    cols = []
    for c in b["colours"]:
        hex_rgb(c)
        cols.append(_norm(c))
    by_lum = sorted(cols, key=lambda c: lum_rgb(hex_rgb(c)))
    dark = _norm(b["ground"]) if b.get("ground") else by_lum[0]
    if contrast_hex(dark, PLAIN["paper"]) < 3.0 and contrast_hex(dark, PLAIN["ink"]) < 3.0:
        dark = PLAIN["ink"]
    if lum_rgb(hex_rgb(dark)) > 0.35:          # the founder only gave light colours
        dark = PLAIN["ink"]
    # A light colour carries words only if it is quiet (cream, sand, pale grey); a bright light colour
    # such as gold or yellow is an accent.
    light_cands = [c for c in by_lum[::-1] if lum_rgb(hex_rgb(c)) > 0.45 and c != dark and _sat(c) < 0.35]
    light = light_cands[0] if light_cands and contrast_hex(light_cands[0], dark) >= 4.5 else PLAIN["paper"]
    accents = [c for c in cols if c not in (dark, light) and _sat(c) >= 0.2]
    # The light background for the poster style: the quiet light colour, else a bright brand colour the dark
    # colour reads on, else white.
    poster_ground = light
    if light == PLAIN["paper"]:
        bright = [c for c in accents if lum_rgb(hex_rgb(c)) > 0.30 and contrast_hex(c, dark) >= 4.5]
        if bright:
            poster_ground = max(bright, key=lambda c: lum_rgb(hex_rgb(c)))
    if b.get("accent"):
        accents = [_norm(b["accent"])] + [c for c in accents if c != _norm(b["accent"])]
    return {"mode": "brand", "dark": dark, "light": light, "accents": accents, "given": cols,
            "poster_ground": poster_ground}


def scheme(pal, ground_kind):
    """Colour roles for one direction. ground_kind 'dark' or 'light'.

    Words take the opposite of the ground (the founder's light colour on dark, their dark colour on
    light). The highlight is an accent colour only when it stands 3:1 off the ground and 1.5:1 off the
    words; otherwise it becomes a box in the words' colour with the ground's colour inside it, which
    always stands out."""
    ground = pal["dark"] if ground_kind == "dark" else pal["poster_ground"]
    text = pal["light"] if ground_kind == "dark" else pal["dark"]
    if contrast_hex(text, ground) < 4.5:
        text = PLAIN["paper"] if contrast_hex(PLAIN["paper"], ground) >= contrast_hex(PLAIN["ink"], ground) else PLAIN["ink"]
    accent = None
    for c in pal["accents"]:
        if c == ground:
            continue
        if contrast_hex(c, ground) >= 3.0 and contrast_hex(c, text) >= 1.5:
            accent = c
            break
    hl = {"mode": "colour", "colour": accent} if accent else {"mode": "box", "colour": text, "ink": ground}
    return {"ground": ground, "text": text, "accent": accent, "hl": hl, "kind": ground_kind, "mode": pal["mode"]}


def roles(spec):
    """Kept for the checks: the dark scheme."""
    s = scheme(palette(spec), "dark")
    return {"mode": s["mode"], "ground": s["ground"], "text": s["text"], "accent": s["accent"]}


# ---------------------------------------------------------------- directions


def resolve_direction(d):
    return ALIASES.get(d, d)


def ground_kind_for(direction):
    return "light" if direction == "poster" else "dark"


def layout(direction, W, H, side, text_width=None):
    """Regions for one direction at one size, in pixels. Each direction differs in composition,
    hierarchy, alignment and colour logic, not only in how the photo is framed."""
    a = aspect_of(W, H)
    right = side != "left"
    g = {"aspect": a, "photo": None, "shape": "rect", "face": None, "scrim": None, "feather": None,
         "text": None, "align": "left", "valign": "center", "hl_style": "colour", "stripe": None,
         "ring": False, "cutout": False, "ground": ground_kind_for(direction), "text_first": False}
    if a == "16:9":
        m = 0.05 * W
        # text_width: how much of the frame the words' side takes (0.40 to 0.70); 0.50 is the default
        tw = max(0.40, min(0.70, float(text_width))) if text_width else 0.50
        sh = (tw - 0.50) * W
        if direction == "panel":
            # Bold panel: a slanted photo panel with an accent edge; words huge, highlight oversized.
            x_top, x_bot = (0.60 * W + sh, 0.54 * W + sh) if right else (0.40 * W - sh, 0.46 * W - sh)
            if right:
                g["photo"] = (min(x_top, x_bot), 0, W, H)
                g["poly"] = [(x_top, 0), (W, 0), (W, H), (x_bot, H)]
                g["text"] = (m, 0.12 * H, min(x_top, x_bot) - 0.04 * W, 0.92 * H)
            else:
                g["photo"] = (0, 0, max(x_top, x_bot), H)
                g["poly"] = [(0, 0), (x_top, 0), (x_bot, H), (0, H)]
                g["text"] = (max(x_top, x_bot) + 0.04 * W, 0.10 * H, W - m, 0.78 * H)
            g["shape"] = "poly"
            g["stripe"] = g["poly"]
            g["face"] = ((0.785 * W + sh / 2) if right else (0.215 * W - sh / 2), 0.47 * H, 0.58 * H)
            g["hl_style"] = "big"
        elif direction == "poster":
            # Poster: light ground, dark words, the founder in a large circle with an offset disc.
            d = 0.80 * H
            cx = 0.76 * W if right else 0.24 * W
            if text_width:
                edge = (tw + 0.035) * W
                d = min(0.80 * H, 0.985 * W - edge)
                cx = edge + d / 2 if right else W - edge - d / 2
            cy = 0.50 * H
            g["photo"] = (cx - d / 2, cy - d / 2, cx + d / 2, cy + d / 2)
            g["shape"] = "circle"
            g["ring"] = True
            g["face"] = (cx, cy - 0.02 * H, 0.50 * H)
            g["text"] = (m, 0.10 * H, cx - d / 2 - 0.035 * W, 0.86 * H) if right else \
                (cx + d / 2 + 0.035 * W, 0.10 * H, W - m, 0.78 * H)
            g["hl_style"] = "box"
        elif direction == "cinema":
            # Cinema: the photo fills the frame; words sit low across a shaded corner.
            g["photo"] = (0, 0, W, H)
            g["face"] = (0.70 * W + sh / 2 if right else 0.30 * W - sh / 2, 0.40 * H, 0.60 * H)
            g["scrim"] = "low-left" if right else "low-right"
            g["text"] = (m, 0.30 * H, 0.56 * W + sh, 0.90 * H) if right else (0.44 * W - sh, 0.30 * H, W - m, 0.78 * H)
            g["valign"] = "bottom"
            g["hl_style"] = "big"
        elif direction == "cutout":
            g["photo"] = (W * 0.46, 0, W, H) if right else (0, 0, W * 0.54, H)
            g["face"] = (0.73 * W if right else 0.27 * W, 0.36 * H, 0.54 * H)
            g["cutout"] = True
            g["text"] = (m, 0.10 * H, 0.56 * W, 0.86 * H) if right else (0.44 * W, 0.10 * H, W - m, 0.78 * H)
            g["text_first"] = True
            g["hl_style"] = "big"
        elif direction == "type":
            g["text"] = (0.08 * W, 0.12 * H, 0.92 * W, 0.80 * H)
            g["align"] = "center"
            g["hl_style"] = "big"
    else:
        sq = a == "1:1"
        m = 0.06 * W
        top = 0.06 * H if sq else 0.15 * H
        split_y = 0.44 * H if sq else 0.42 * H
        right_limit = W - m if sq else 0.84 * W
        g["align"] = "center"
        fh = 0.34 * H if sq else 0.22 * H
        if direction == "panel":
            g["text"] = (m, top, right_limit if sq else W - m, split_y - 0.05 * H)
            if not sq:
                g["text"] = (0.08 * W, top, 0.92 * W, split_y - 0.04 * H)
            g["photo"] = (0, split_y - 0.03 * H, W, H)
            g["poly"] = [(0, split_y + 0.02 * H), (W, split_y - 0.03 * H), (W, H), (0, H)]
            g["shape"] = "poly"
            g["stripe"] = g["poly"]
            g["face"] = (W / 2, split_y + (H - split_y) * 0.44, fh)
            g["hl_style"] = "big"
        elif direction == "poster":
            g["text"] = (m, top, W - m, split_y - 0.03 * H) if sq else (0.08 * W, top, 0.92 * W, split_y - 0.02 * H)
            d = min(0.80 * W, (H - split_y) * 0.92) if sq else min(0.86 * W, (0.90 * H - split_y) * 0.95)
            cy = split_y + d / 2 + 0.01 * H
            g["photo"] = (W / 2 - d / 2, cy - d / 2, W / 2 + d / 2, cy + d / 2)
            g["shape"] = "circle"
            g["ring"] = True
            g["face"] = (W / 2, cy - 0.02 * d, 0.55 * d)
            g["hl_style"] = "box"
        elif direction == "cinema":
            g["photo"] = (0, 0, W, H)
            g["face"] = (W / 2, 0.27 * H if sq else 0.30 * H, 0.30 * H if sq else fh)
            g["scrim"] = "bottom"
            g["text"] = (m, 0.60 * H, W - m, 0.94 * H) if sq else (0.08 * W, 0.50 * H, 0.84 * W, 0.78 * H)
            g["valign"] = "bottom"
            g["hl_style"] = "big"
        elif direction == "cutout":
            g["text"] = (m, top, W - m, split_y - 0.03 * H) if sq else (0.08 * W, top, 0.92 * W, split_y - 0.02 * H)
            g["photo"] = (0, split_y, W, H)
            g["face"] = (W / 2, split_y + (H - split_y) * 0.36, fh)
            g["cutout"] = True
            g["text_first"] = True
            g["hl_style"] = "big"
        elif direction == "type":
            g["text"] = (0.08 * W, 0.16 * H, 0.92 * W, 0.80 * H) if sq else (0.12 * W, 0.16 * H, 0.84 * W, 0.70 * H)
            g["hl_style"] = "big"
    return g


def photo_fit(img_w, img_h, face_box, region, face_target, face_scale=1.0, offset=(0.0, 0.0)):
    """Scale and offset so the face reaches its target height and sits where the direction wants it,
    while the photograph still covers the whole region. face_scale (0.6 to 1.4) and offset (pixels)
    are the founder's own adjustments: they may move the photo past its edge, and the gap is then
    filled with a soft, blurred extension of the same photo (fit["gaps"] is True)."""
    rx0, ry0, rx1, ry1 = region
    rw, rh = rx1 - rx0, ry1 - ry0
    l, t, r, b = face_box
    fcx, fcy, fh_target = face_target
    face_h_px = max(1.0, (b - t) * img_h)
    fs = max(0.6, min(1.4, float(face_scale or 1.0)))
    s = fh_target * fs / face_h_px
    if fs >= 1.0:
        s = max(s, rw / img_w, rh / img_h)
    sw, sh = img_w * s, img_h * s
    x = fcx - (l + r) / 2 * sw
    y = fcy - (t + b) / 2 * sh
    x = min(rx0, max(rx1 - sw, x)) if sw >= rw else x
    y = min(ry0, max(ry1 - sh, y)) if sh >= rh else y
    x += offset[0]
    y += offset[1]
    fx0, fy0, fx1, fy1 = l * sw + x, t * sh + y, r * sw + x, b * sh + y
    vis = (max(fx0, rx0), max(fy0, ry0), min(fx1, rx1), min(fy1, ry1))
    vis_area = max(0, vis[2] - vis[0]) * max(0, vis[3] - vis[1])
    full_area = max(1e-6, (fx1 - fx0) * (fy1 - fy0))
    gaps = x > rx0 + 0.5 or y > ry0 + 0.5 or x + sw < rx1 - 0.5 or y + sh < ry1 - 0.5
    return {"scale": s, "x": x, "y": y, "face": (fx0, fy0, fx1, fy1), "visible": vis_area / full_area,
            "upscale": s, "sw": sw, "sh": sh, "face_visible_box": vis, "gaps": gaps}


# ---------------------------------------------------------------- type setting

NUM_RE = re.compile(r"^(?:[A-Z]{0,3}[" + CURRENCY + r"]|Rs\.?|RM|Rp|CHF|AED|SAR|kr)?\d[\d.,]*"
                    r"(?:%|k|K|m|M|bn|p|x|\u4e07|\u842c|\u5104|\u4ebf)?[" + CURRENCY + r"]?[,.]?$")
HL_SCALE = 1.32
NUM_SCALE = 1.6
SMALL_SCALE = 0.68
FUNCTION_WORDS = {"to", "of", "in", "a", "an", "the", "and", "for", "on", "at", "by", "from", "vs", "with", "is"}
DESCENDERS = set("gjpqy,")


def _clean(w):
    return re.sub(r"[^\w%" + CURRENCY + r"]", "", w.lower())


def partitions(tokens, max_lines):
    n = len(tokens)
    out = []
    for lines in range(1, min(max_lines, n) + 1):
        def rec(start, left):
            if left == 1:
                yield [tokens[start:]]
                return
            for cut in range(start + 1, n - left + 2):
                for rest in rec(cut, left - 1):
                    yield [tokens[start:cut]] + rest
        out.extend(rec(0, lines))
    return out


class Setter:
    """Measures and draws a hook as lines of words, each word with its own size and treatment."""

    def __init__(self, font_path, hl_word, hl_style, upper, script="Latin", lang=None, hl_boost=1.0):
        self.font_path, self.hl, self.style, self.upper = font_path, _clean(hl_word or ""), hl_style, upper
        self.hl_boost = max(0.8, min(2.2, float(hl_boost or 1.0)))
        self.bold = 0.0
        self.small_words = False
        self.script = script
        self.rtl = script in RTL_SCRIPTS
        self.lang = (lang or "").lower()
        self.direction = "rtl" if self.rtl else None

    def leading(self, base):
        """Latin capitals sit tight; scripts with marks above and below need room, and square
        Chinese, Japanese and Korean characters fill their whole em."""
        if self.script in TALL_SCRIPTS:
            return max(base, 1.22)
        if self.script in SQUARE_SCRIPTS:
            return max(base, 1.06)
        return base

    def case(self, s):
        if not self.upper:
            return s
        if self.lang.startswith(("tr", "az")):
            s = s.replace("i", "\u0130")          # Turkish and Azeri dotted capital I
        return s.upper()

    @staticmethod
    def disp(w):
        """A highlighted phrase travels as one token joined by no-break spaces; it is drawn with plain ones."""
        return w.replace(NBSP, " ")

    def _len(self, font, w):
        w = self.disp(w)
        if self.direction and HAVE_PIL and has_raqm():
            return font.getlength(w, direction=self.direction)
        return font.getlength(w)

    def gap(self, a, b, size):
        """The space drawn between two words. Between two characters of a script written without
        spaces, the space in the hook only marks a line break point, so nothing is drawn."""
        if a and b and script_of(a.rstrip(",.")[-1:] or " ") in NO_SPACE_SCRIPTS \
                and script_of(b[:1]) in NO_SPACE_SCRIPTS:
            return 0.0
        return self.space(size)

    def is_hl(self, w):
        return bool(self.hl) and _clean(w) == self.hl

    def scale(self, w):
        if self.is_hl(w) and self.style == "big":
            if NUM_RE.match(w.split(NBSP)[0]):
                return (NUM_SCALE if NBSP not in w else 1.42) * self.hl_boost
            return HL_SCALE * self.hl_boost
        if self.is_hl(w) and self.style == "box":
            return (1.12 if NUM_RE.match(w.split(NBSP)[0]) else 1.0) * self.hl_boost
        if self.small_words and w.lower().strip(",.") in FUNCTION_WORDS and not self.is_hl(w):
            return SMALL_SCALE
        return 1.0

    def boxed(self, w):
        return self.is_hl(w) and self.style == "box"

    def word_w(self, w, size):
        s = size * self.scale(w)
        if HAVE_PIL:
            wd = self._len(load_font(self.font_path, s), w)
        else:
            wd = len(w) * s * 0.60
        if self.boxed(w):
            wd += 2 * BOX_PAD * s
        return wd + 2 * int(s * self.bold)

    def space(self, size):
        if HAVE_PIL:
            return load_font(self.font_path, size).getlength(" ") * 0.95
        return size * 0.26

    def line_w(self, line, size):
        return sum(self.word_w(w, size) for w in line) + sum(self.gap(line[i], line[i + 1], size)
                                                               for i in range(len(line) - 1))

    def line_h(self, line, size, leading):
        top = max(self.scale(w) for w in line)
        extra = BOX_PAD * 1.6 if any(self.boxed(w) for w in line) else 0
        # room for descenders (g, j, p, y) so they never touch the line below
        desc = max((self.scale(w) * 0.12 for w in line if set(w) & DESCENDERS and not self.upper), default=0)
        return size * (top * self.leading(leading) + extra + desc)

    def fit(self, text, box, max_lines, leading):
        s = self.case(text)
        forced = None
        if "|" in s:
            forced = [_toks(seg) for seg in s.split("|") if _toks(seg)]
            s = " ".join(" ".join(x) for x in forced)
        tokens = _toks(s)
        # Hierarchy: in a hook of three or more words, little linking words are set smaller so the
        # words that carry the idea dominate.
        content = [t for t in tokens if t.lower().strip(",.") not in FUNCTION_WORDS]
        self.small_words = len(tokens) >= 3 and len(content) >= 2
        x0, y0, x1, y1 = box
        bw, bh = x1 - x0, y1 - y0
        best = None
        cands = [forced] if forced else (partitions(tokens, max_lines) if len(tokens) <= 8 else [[tokens]])
        for parts in cands:
            lo, hi, fit = 10, int(bh), None
            while lo <= hi:
                mid = (lo + hi) // 2
                widest = max(self.line_w(p, mid) for p in parts)
                total = sum(self.line_h(p, mid, leading) for p in parts)
                if widest <= bw and total <= bh:
                    fit, lo = mid, mid + 1
                else:
                    hi = mid - 1
            if not fit:
                continue
            score = fit * (1 if forced else self.sense(parts))
            if best is None or score > best[2] * 1.03 or (score >= best[2] * 0.97 and len(parts) < len(best[1])):
                best = (fit, parts, score)
        if best is None:
            best = (10, [tokens], 10)
        return {"size": best[0], "lines": best[1], "line_scale": self.stack(best[1], best[0], bw, bh, leading)}

    def stack(self, parts, size, bw, bh, leading):
        """Stacked type: a line narrower than the column is set larger until it fills the width, so the
        block reads as one designed shape instead of a ragged paragraph with empty space beside it. A
        line without the highlight never grows past 0.75 of the highlight's size, so the key word or
        figure stays the largest thing on the thumbnail."""
        if len(parts) < 2:
            return [1.0] * len(parts)
        hl_px = max([size * self.scale(w) for p in parts for w in p if self.is_hl(w)] or [0])
        f = []
        for p in parts:
            k = min(1.55, bw / max(1.0, self.line_w(p, size)))
            if hl_px and not any(self.is_hl(w) for w in p):
                k = min(k, 0.75 * hl_px / (size * max(self.scale(w) for w in p)))
            f.append(max(1.0, k))
        for _ in range(12):
            total = sum(self.line_h(p, size * k, leading) for p, k in zip(parts, f))
            if total <= bh:
                break
            f = [1.0 + (k - 1.0) * 0.8 for k in f]
        return [round(k, 3) for k in f]

    def sense(self, parts):
        """Line breaks that read as phrases score higher than ones that only make the type bigger."""
        k = 1.0
        for i, p in enumerate(parts):
            last = p[-1]
            if i < len(parts) - 1:
                nxt = parts[i + 1][0]
                if last.endswith(","):
                    k *= 1.12
                if len(last.strip(",.")) <= 2 and not NUM_RE.match(last):
                    k *= 0.90
                if NUM_RE.match(last) and not last.endswith(","):
                    k *= 0.72          # a number split from its unit ("10 / hours")
                if last.lower().strip(",.") in FUNCTION_WORDS | {"my", "your", "our"}:
                    k *= 0.75          # a line never ends on a linking word ("TIERS FROM / $450")
            for t in p[:-1]:
                if t.endswith(","):
                    k *= 0.88
            if len(p) == 1 and len(p[0].strip(",.")) <= 3 and not self.is_hl(p[0]):
                k *= 0.82
        return k


BOX_PAD = 0.14
NBSP = "\u00a0"


def _toks(text):
    """Split on ordinary spaces only: a no-break space keeps a number and its unit together."""
    return [t for t in re.split(r"[ \t\r\n]+", text) if t]


def join_highlight(hook, hl):
    """A highlight of two or three words (a number and its unit: "\u20b95.2 lakh", "10 hours") is joined
    into one token, so it is sized, coloured or boxed as one and never split across lines."""
    hl = (hl or "").strip()
    if not hl or " " not in hl:
        return hook
    pat = r"\s+".join(re.escape(p) for p in hl.split())
    m = re.search(pat, hook, re.I)
    if not m:
        return hook
    return hook[:m.start()] + NBSP.join(m.group(0).split()) + hook[m.end():]


def draw_words(canvas, setter, fitd, box, colours, align="left", valign="center", leading=0.9, stroke=None,
               below=0):
    """Draw the hook. Returns the box round all words, the cap height at body size and the y below the
    last line. Highlight: colour, big (bigger and coloured) or box (filled in the words' colour)."""
    d = ImageDraw.Draw(canvas)
    base_size = fitd["size"]
    lscale = fitd.get("line_scale") or [1.0] * len(fitd["lines"])
    x0, y0, x1, y1 = box
    kw = {"direction": setter.direction} if setter.direction and has_raqm() else {}
    # Lines are spaced by their ink: the space between the lowest mark of one line and the highest of the
    # next is the same for every script and every size, so no line floats loose.
    tops, bots = [], []
    for p, k in zip(fitd["lines"], lscale):
        t_, b_ = 0.0, 0.0
        for w in p:
            ws = base_size * k * setter.scale(w)
            f = load_font(setter.font_path, ws)
            bb = f.getbbox(setter.disp(w), anchor="ls", **kw)
            tt = max(-bb[1], cap_height(f, setter.script) if setter.script == "Latin" else 0)
            bt = max(0, bb[3])
            if setter.boxed(w):
                tt, bt = max(cap_height(f, setter.script), -bb[1]) + BOX_PAD * ws * 0.8, bt + BOX_PAD * ws * 0.8
            t_, b_ = max(t_, tt), max(b_, bt)
        tops.append(t_)
        bots.append(b_)
    sizes_ = [base_size * k for k in lscale]
    gap_k = 0.20 if setter.script in TALL_SCRIPTS else (0.14 if setter.script in SQUARE_SCRIPTS else 0.13)
    gaps = [gap_k * min(sizes_[i], sizes_[i + 1]) for i in range(len(sizes_) - 1)]
    heights = [t_ + b_ + (gaps[i] if i < len(gaps) else 0) for i, (t_, b_) in enumerate(zip(tops, bots))]
    total = sum(heights)
    if valign == "center":
        y = y0 + ((y1 - y0) - total - below) / 2
    elif valign == "bottom":
        y = y1 - total - below
    else:
        y = y0
    y = max(y0, y)
    rects, word_rects = [], []
    for li, (p, lh, lk) in enumerate(zip(fitd["lines"], heights, lscale)):
        size = base_size * lk
        sw = max(2, int(size * 0.045)) if stroke else 0
        emb = int(size * (0.025 if setter.font_path is None else 0) + size * setter.bold)
        lw = setter.line_w(p, size)
        # Right-to-left words are placed from the right: the line is laid out in visual order, and a
        # block that would sit flush left sits flush right instead.
        if align == "left":
            x = x1 - lw if setter.rtl else x0
        else:
            x = x0 + ((x1 - x0) - lw) / 2
        line_x0 = x
        order = list(reversed(p)) if setter.rtl else list(p)
        baseline = y + tops[li]
        for i, w in enumerate(order):
            ws = size * setter.scale(w)
            f = load_font(setter.font_path, ws)
            fill = colours["text"]
            e = int(ws * setter.bold)          # extra weight, drawn as a stroke in the letter's own colour
            wemb = emb + e
            ww = setter._len(f, w) + 2 * e
            if setter.boxed(w):
                pad = BOX_PAD * ws
                cap = cap_height(f, setter.script)
                bb = f.getbbox(setter.disp(w), anchor="ls", **kw)
                d.rectangle([x, baseline + min(-cap, bb[1]) - pad * 0.8, x + ww + 2 * pad,
                             baseline + max(0, bb[3]) + pad * 0.8], fill=hex_rgb(colours["hl"]["colour"]))
                fill = colours["hl"]["ink"]
                d.text((x + pad + e, baseline), setter.disp(w), font=f, fill=hex_rgb(fill), anchor="ls",
                       stroke_width=wemb, stroke_fill=hex_rgb(fill), **kw)
                word_rects.append((x, baseline + min(-cap, bb[1]) - pad, x + ww + 2 * pad, baseline + pad))
                x += ww + 2 * pad
            else:
                if setter.is_hl(w) and colours["hl"]["mode"] == "colour":
                    fill = colours["hl"]["colour"]
                elif setter.is_hl(w) and setter.style == "big" and colours["hl"]["mode"] == "box":
                    # no usable accent: the oversized word carries the emphasis on its own
                    fill = colours["text"]
                if stroke:
                    if e:
                        d.text((x + e, baseline), setter.disp(w), font=f, fill=hex_rgb(fill), anchor="ls",
                               stroke_width=sw + e, stroke_fill=hex_rgb(stroke), **kw)
                    d.text((x + e, baseline), setter.disp(w), font=f, fill=hex_rgb(fill), anchor="ls",
                           stroke_width=e if e else sw, stroke_fill=hex_rgb(fill if e else stroke), **kw)
                else:
                    d.text((x + e, baseline), setter.disp(w), font=f, fill=hex_rgb(fill), anchor="ls", stroke_width=wemb,
                           stroke_fill=hex_rgb(fill), **kw)
                bb = f.getbbox(setter.disp(w), anchor="ls", **kw)
                word_rects.append((x + bb[0], baseline + bb[1] - e, x + bb[2] + 2 * e, baseline + bb[3] + e))
                x += ww
            if i < len(order) - 1:
                a_, b_ = (order[i + 1], w) if setter.rtl else (w, order[i + 1])
                x += setter.gap(a_, b_, size)
        rects.append((line_x0, y, x, y + lh))
        y += lh
    tb = (min(r[0] for r in word_rects), min(r[1] for r in word_rects),
          max(r[2] for r in word_rects), max(r[3] for r in word_rects))
    return tb, cap_height(load_font(setter.font_path, base_size), setter.script), y


def draw_focal(canvas, text, x, y, size, font_path, colours):
    """The focal chip: a filled shape in the accent (or the words' colour) with the ground's colour inside."""
    d = ImageDraw.Draw(canvas)
    f = load_font(font_path, size)
    fill_bg = colours["accent"] or colours["text"]
    ink = colours["ground"]
    if contrast_hex(fill_bg, ink) < 4.5:
        ink = PLAIN["ink"] if contrast_hex(PLAIN["ink"], fill_bg) > contrast_hex(PLAIN["paper"], fill_bg) else PLAIN["paper"]
    w = f.getlength(text)
    bb = f.getbbox(text, anchor="ls")
    cap = cap_height(f, main_script(text))
    top, bottom = max(cap, -bb[1]), max(0, bb[3]) if main_script(text) != "Latin" else 0
    padx, pady = size * 0.32, size * 0.24
    rect = [x, y, x + w + 2 * padx, y + top + bottom + 2 * pady]
    d.rounded_rectangle(rect, radius=int(size * 0.12), fill=hex_rgb(fill_bg))
    d.text((x + padx, y + pady + top), text, font=f, fill=hex_rgb(ink), anchor="ls")
    return tuple(rect), cap, fill_bg, ink


# ---------------------------------------------------------------- PIL rendering


def _poly_mask(size, poly, offset):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).polygon([(px - offset[0], py - offset[1]) for px, py in poly], fill=255)
    return m


def _extension(src, size, ground_hex, blur):
    """The founder's own photo, scaled to cover, blurred and drawn a third of the way towards the
    background colour: it fills any strip the photo no longer covers after it is moved or shrunk."""
    w, h = size
    s = max(w / src.width, h / src.height)
    big = src.convert("RGB").resize((max(1, int(src.width * s) + 1), max(1, int(src.height * s) + 1)), Image.LANCZOS)
    big = big.crop(((big.width - w) // 2, (big.height - h) // 2, (big.width - w) // 2 + w, (big.height - h) // 2 + h))
    big = big.filter(ImageFilter.GaussianBlur(blur))
    tint = Image.new("RGB", big.size, hex_rgb(ground_hex))
    return Image.blend(big, tint, 0.35).convert("RGBA")


def _feathered(img, inner_edges, width):
    """Soft edges on the sides of the photo that fall inside the frame."""
    if width < 2:
        return img
    a = img.split()[3]
    m = Image.new("L", img.size, 255)
    md = ImageDraw.Draw(m)
    for i in range(width):
        v = int(255 * (i / width) ** 1.3)
        if "l" in inner_edges:
            md.line([(i, 0), (i, img.height)], fill=v)
        if "r" in inner_edges:
            md.line([(img.width - 1 - i, 0), (img.width - 1 - i, img.height)], fill=v)
    if "t" in inner_edges or "b" in inner_edges:
        m2 = Image.new("L", img.size, 255)
        md2 = ImageDraw.Draw(m2)
        for i in range(width):
            v = int(255 * (i / width) ** 1.3)
            if "t" in inner_edges:
                md2.line([(0, i), (img.width, i)], fill=v)
            if "b" in inner_edges:
                md2.line([(0, img.height - 1 - i), (img.width, img.height - 1 - i)], fill=v)
        m = ImageChops.multiply(m, m2)
    out = img.copy()
    out.putalpha(ImageChops.multiply(a, m))
    return out


def place_photo(canvas, photo_path, face_box, g, colours, adjust=None):
    region = g["photo"]
    W, H = canvas.size
    adjust = adjust or {}
    fsc = adjust.get("face_scale", 1.0)
    off = (adjust.get("dx", 0.0) * W, adjust.get("dy", 0.0) * H)
    with Image.open(photo_path) as src:
        src = src.convert("RGBA")
        if g["cutout"]:
            bbox = src.getbbox() or (0, 0, src.width, src.height)
            fit = photo_fit(src.width, src.height, face_box, (0, 0, 1, 1), g["face"], fsc)
            s = fit["scale"]
            sw, sh = max(1, int(src.width * s)), max(1, int(src.height * s))
            img = src.resize((sw, sh), Image.LANCZOS)
            l, t, r, b = face_box
            x = int(g["face"][0] - (l + r) / 2 * sw)
            y = int(region[3] - bbox[3] * s)
            y = max(y, int(g["face"][1] - (t + b) / 2 * sh))
            x, y = int(x + off[0]), int(y + off[1])
            alpha = img.split()[3]
            halo = alpha.filter(ImageFilter.MaxFilter(max(3, (int(min(W, H) * 0.014) | 1))))
            ring = Image.new("RGBA", img.size, hex_rgb(colours["text"]) + (255,))
            layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            layer.paste(ring, (x, y), halo)
            layer.paste(img, (x, y), img)
            canvas.alpha_composite(layer)
            fx0, fy0, fx1, fy1 = l * sw + x, t * sh + y, r * sw + x, b * sh + y
            vis = (max(fx0, 0), max(fy0, 0), min(fx1, W), min(fy1, H))
            fit.update({"x": x, "y": y, "face": (fx0, fy0, fx1, fy1), "upscale": s, "face_visible_box": vis,
                        "visible": max(0, vis[2] - vis[0]) * max(0, vis[3] - vis[1]) /
                        max(1e-6, (fx1 - fx0) * (fy1 - fy0))})
            return fit
        fit = photo_fit(src.width, src.height, face_box, region, g["face"], fsc, off)
        sw, sh = max(1, int(round(fit["sw"]))), max(1, int(round(fit["sh"])))
        img = src.resize((sw, sh), Image.LANCZOS)
        rx0, ry0, rx1, ry1 = [int(round(v)) for v in region]
        if fit["gaps"]:
            inner = ""
            inner += "l" if fit["x"] > rx0 else ""
            inner += "r" if fit["x"] + sw < rx1 else ""
            inner += "t" if fit["y"] > ry0 else ""
            inner += "b" if fit["y"] + sh < ry1 else ""
            img = _feathered(img, inner, int(min(W, H) * 0.12))
        crop = img.crop((int(rx0 - fit["x"]), int(ry0 - fit["y"]), int(rx0 - fit["x"]) + (rx1 - rx0),
                         int(ry0 - fit["y"]) + (ry1 - ry0)))
        if fit["gaps"]:
            ext = _extension(src, crop.size, colours["ground"], max(8, int(min(W, H) * 0.035)))
            ext.alpha_composite(crop)
            crop = ext
        mask = crop.split()[3]
        d = ImageDraw.Draw(canvas)
        if g["shape"] == "circle":
            # offset disc in the accent (only if the founder has one), then a ring in the words' colour
            dia = rx1 - rx0
            if colours["accent"]:
                off = int(dia * 0.06)
                ox = -off if g["photo"][0] > W / 3 else off
                d.ellipse([rx0 + ox, ry0 + off, rx1 + ox, ry1 + off], fill=hex_rgb(colours["accent"]))
            ring = max(4, int(dia * 0.018))
            d.ellipse([rx0 - ring, ry0 - ring, rx1 + ring, ry1 + ring], fill=hex_rgb(colours["text"]))
            cm = Image.new("L", crop.size, 0)
            ImageDraw.Draw(cm).ellipse([0, 0, crop.width - 1, crop.height - 1], fill=255)
            mask = ImageChops.multiply(mask, cm)
        elif g["shape"] == "poly":
            pm = _poly_mask(crop.size, g["poly"], (rx0, ry0))
            mask = ImageChops.multiply(mask, pm)
        if g.get("feather"):
            fw = int(crop.width * 0.35)
            grad = Image.new("L", crop.size, 255)
            gd = ImageDraw.Draw(grad)
            for i in range(fw):
                a_ = int(255 * (i / fw) ** 1.5)
                x_ = i if g["feather"] == "left" else crop.width - 1 - i
                gd.line([(x_, 0), (x_, crop.height)], fill=a_)
            mask = ImageChops.multiply(mask, grad)
        canvas.paste(crop, (rx0, ry0), mask)
        if g.get("stripe") and g["shape"] == "poly":
            # an accent edge along the slant; with no accent, the words' colour
            col = colours["accent"] or colours["text"]
            poly = g["poly"]
            edge = [p for p in poly if 0 < p[0] < W] if g["aspect"] == "16:9" else [p for p in poly if 0 < p[1] < H and p[1] < H * 0.9]
            if len(edge) >= 2:
                wdt = max(6, int(min(W, H) * 0.016))
                d.line(edge[:2], fill=hex_rgb(col), width=wdt)
        return fit


def draw_scrim(canvas, where, colour, strength=0.96):
    W, H = canvas.size
    over = Image.new("RGBA", (W, H), hex_rgb(colour) + (0,))
    alpha = Image.new("L", (W, H), 0)
    px = alpha.load()
    small = Image.new("L", (64, 36 if W >= H else 64), 0)
    sp = small.load()
    sw_, sh_ = small.size
    for j in range(sh_):
        for i in range(sw_):
            fx, fy = i / (sw_ - 1), j / (sh_ - 1)
            if where == "low-left":
                v = max(0.0, 1.25 - ((fx / 0.70) ** 2 + ((1 - fy) / 0.85) ** 2) ** 0.5)
                v = max(v, max(0.0, (fy - 0.40) / 0.45) * 0.85 * max(0.0, 1 - fx / 0.80))
            elif where == "low-right":
                v = max(0.0, 1.25 - (((1 - fx) / 0.70) ** 2 + ((1 - fy) / 0.85) ** 2) ** 0.5)
                v = max(v, max(0.0, (fy - 0.40) / 0.45) * 0.85 * max(0.0, 1 - (1 - fx) / 0.80))
            else:  # bottom
                v = max(0.0, (fy - 0.30) / 0.45)
            sp[i, j] = int(255 * strength * min(1.0, v) ** 1.1)
    alpha = small.resize((W, H), Image.BICUBIC)
    del px
    over.putalpha(alpha)
    canvas.alpha_composite(over)


def logo_contrast(logo_path, ground_hex):
    """Contrast between the logo's own colours (opaque pixels) and the background it would sit on."""
    with Image.open(logo_path) as lg:
        lg = lg.convert("RGBA")
        lg.thumbnail((200, 200))
        raw = lg.tobytes()
    lums = [lum_rgb(raw[i:i + 3]) for i in range(0, len(raw), 4) if raw[i + 3] > 128]
    if not lums:
        return 21.0
    lums.sort()
    return ratio(lums[len(lums) // 2], lum_rgb(hex_rgb(ground_hex)))


def place_logo(canvas, logo_path, text_box, aspect):
    with Image.open(logo_path) as lg:
        lg = lg.convert("RGBA")
        W, H = canvas.size
        target_h = int(H * (0.07 if aspect == "16:9" else 0.045))
        s = target_h / lg.height
        lg = lg.resize((max(1, int(lg.width * s)), target_h), Image.LANCZOS)
        x, y = int(text_box[0]), int(H * 0.05)
        canvas.alpha_composite(lg, (x, y))
        return (x, y, x + lg.width, y + lg.height)


def _busiest_contrast(background, box, text_hex):
    W, H = background.size
    x0, y0, x1, y1 = [int(v) for v in box]
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, max(x0 + 1, x1)), min(H, max(y0 + 1, y1))
    vals = _lum_values(background.crop((x0, y0, x1, y1)))
    tl = lum_rgb(hex_rgb(text_hex))
    med = vals[len(vals) // 2]
    worst = vals[int(len(vals) * 0.9)] if tl > med else vals[int(len(vals) * 0.1)]
    return ratio(tl, med), ratio(tl, worst)


def draw_depth(canvas, ground_kind):
    """A quiet edge shade on a flat dark background, in black only, so the frame has depth rather
    than reading as a flat fill. Nothing on a light background."""
    if ground_kind != "dark":
        return
    W, H = canvas.size
    small = Image.new("L", (64, max(2, int(64 * H / W))), 0)
    sp = small.load()
    sw_, sh_ = small.size
    for j in range(sh_):
        for i in range(sw_):
            dx, dy = (i / (sw_ - 1) - 0.42) / 0.75, (j / (sh_ - 1) - 0.45) / 0.80
            sp[i, j] = int(255 * 0.30 * min(1.0, max(0.0, (dx * dx + dy * dy) ** 0.5 - 0.35) / 0.75))
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shade.putalpha(small.resize((W, H), Image.BICUBIC))
    canvas.alpha_composite(shade)


def spec_for(spec, direction):
    """The spec as one style sees it: a style may carry its own words (styles.<name>.hook, highlight,
    focal) and its own adjustments, so the three options show three word options, not one."""
    over = (spec.get("styles") or {}).get(direction) or {}
    if not over:
        return spec
    out = dict(spec)
    for k in STYLE_KEYS:
        if k in over:
            out[k] = over[k]
    return out


STYLE_KEYS = ("hook", "highlight", "focal", "focal_scale", "highlight_scale", "photo_offset", "face_scale",
              "text_width", "text_position", "weight_boost", "case", "subject_side")


def _clear_of_face(box, fv, W, H, aspect, side_right):
    """Pull the words' box back from the face so no letter, dot or mark touches it."""
    x0, y0, x1, y1 = box
    m = 0.03 * W
    if aspect == "16:9":
        if fv[1] < y1 and fv[3] > y0:
            if side_right and x1 > fv[0] - m and fv[0] - m - x0 >= 0.30 * W:
                x1 = fv[0] - m
            elif not side_right and x0 < fv[2] + m and x1 - (fv[2] + m) >= 0.30 * W:
                x0 = fv[2] + m
    else:
        if fv[0] < x1 and fv[2] > x0 and y1 > fv[1] - m and fv[1] - m - y0 >= 0.15 * H:
            y1 = fv[1] - m
    return [x0, y0, x1, y1]


def render_one(spec, direction, size_name, out_dir, font_path, font_desc, pal):
    spec = spec_for(spec, direction)
    W, H, label, tests = SIZES[size_name]
    side = (spec.get("subject_side") or "right").lower()
    g = layout(direction, W, H, side, spec.get("text_width"))
    colours = scheme(pal, g["ground"])
    canvas = Image.new("RGBA", (W, H), hex_rgb(colours["ground"]) + (255,))
    if not (g["photo"] == (0, 0, W, H)):
        draw_depth(canvas, g["ground"])
    if (spec.get("text_position") or "") in ("top", "center", "bottom"):
        g["valign"] = spec["text_position"]
    po = spec.get("photo_offset") or [0, 0]
    adjust = {"face_scale": float(spec.get("face_scale") or 1.0), "dx": float(po[0]), "dy": float(po[1])}
    photo = spec.get("cutout") if direction == "cutout" else spec.get("photo")
    face_box = spec.get("face_box") or [0.3, 0.1, 0.7, 0.55]
    fit = None
    if photo and g["photo"] is not None and not g["text_first"]:
        if direction == "cinema" and g["aspect"] == "16:9":
            iw, ih = image_size(photo)
            trial = photo_fit(iw, ih, face_box, g["photo"], g["face"])
            if (trial["face"][3] - trial["face"][1]) > 0.80 * H:
                # a tall photo cannot fill a wide frame without a giant face: fill the face side and fade
                right = (spec.get("subject_side") or "right").lower() != "left"
                g["photo"] = (0.30 * W, 0, W, H) if right else (0, 0, 0.70 * W, H)
                g["feather"] = "left" if right else "right"
        fit = place_photo(canvas, photo, face_box, g, colours, adjust)
    if g["scrim"]:
        draw_scrim(canvas, g["scrim"], colours["ground"])
    upper = (spec.get("case") or "as-written").lower() == "upper"
    hook = spec["hook"] if g["aspect"] == "16:9" else spec["hook"].replace("|", " ")
    hook = join_highlight(hook, spec.get("highlight"))
    focal = (spec.get("focal") or "").strip()
    box = list(g["text"])
    if fit and not g["text_first"]:
        box = _clear_of_face(box, fit["face_visible_box"], W, H, g["aspect"], side != "left")
    logo = (spec.get("brand") or {}).get("logo")
    logo_note = None
    if logo and os.path.isfile(logo) and logo_contrast(logo, colours["ground"]) < 2.0:
        logo_note = "left off: it would vanish on this background"
        logo = None
    if logo and os.path.isfile(logo):
        box[1] = max(box[1], H * (0.05 + (0.07 if g["aspect"] == "16:9" else 0.045) + 0.04))
    leading = 0.86 if upper else 0.90
    setter = Setter(font_path, spec.get("highlight"), g["hl_style"], upper, main_script(spec["hook"]),
                    spec.get("lang"), spec.get("highlight_scale") or 1.0)
    setter.bold = max(0.0, min(1.0, float(spec.get("weight_boost") or 0))) * 0.035
    fscale = max(0.6, min(2.6, float(spec.get("focal_scale") or 1.0)))
    focal_reserve = (box[3] - box[1]) * min(0.62, 0.24 * fscale) if focal else 0
    fitd = setter.fit(hook, (box[0], box[1], box[2], box[3] - focal_reserve), 3, leading)
    fsize = int(max(fitd["size"] * 0.46, H * 0.055) * fscale) if focal else 0
    if focal:
        # the chip never runs past the words' box: shrink it to fit rather than overflow
        fmax = (box[2] - box[0]) / max(1.0, load_font(font_path, 100).getlength(focal) / 100 + 0.64)
        fsize = int(min(fsize, fmax))
    focal_block = (fsize * 1.25 + fitd["size"] * 0.22) if focal else 0
    background = canvas.copy()
    # Outline only where the words sit on a busy photo and would otherwise fall under 4.5:1
    stroke = None
    if g["scrim"] or g["photo"] == (0, 0, W, H):
        c_med, c_worst = _busiest_contrast(background, box, colours["text"])
        if c_worst < 4.5:
            stroke = colours["ground"]
    hook_rect, cap, ybottom = draw_words(canvas, setter, fitd, box, colours, align=g["align"], valign=g["valign"],
                                         leading=leading, stroke=stroke, below=focal_block)
    rects = {"hook": hook_rect}
    focal_info = None
    if focal:
        fw = load_font(font_path, fsize).getlength(focal) + fsize * 0.64
        if g["align"] == "left":
            fx = hook_rect[2] - fw if setter.rtl else hook_rect[0]
        else:
            fx = (box[0] + box[2]) / 2 - fw / 2
        frect, fcap, fbg, fink = draw_focal(canvas, focal, fx, ybottom + fitd["size"] * 0.20, fsize, font_path, colours)
        rects["focal"] = frect
        focal_info = (fbg, fink, fcap)
    if photo and g["photo"] is not None and g["text_first"]:
        fit = place_photo(canvas, photo, face_box, g, colours, adjust)
    if logo and os.path.isfile(logo):
        rects["logo"] = place_logo(canvas, logo, g["text"], g["aspect"])
    final = canvas.convert("RGB")
    stem = f"{spec.get('date') or dt.date.today().isoformat()}-{spec['slug']}-{direction}-{size_name}"
    path = os.path.join(out_dir, stem + ".png")
    meta = PngInfo()
    meta.add_text("Software", CREDIT)
    meta.add_text("Title", spec.get("title") or spec["slug"])
    final.save(path, pnginfo=meta, optimize=True)
    result = {"direction": direction, "size": size_name, "file": path, "W": W, "H": H, "font": font_desc,
              "font_px": fitd["size"], "lines": [" ".join(p) for p in fitd["lines"]], "cap_px": cap, "rects": rects,
              "fit": fit, "aspect": g["aspect"], "text_colour": colours["text"], "focal_info": focal_info,
              "colours": colours, "highlight": bool(setter.hl), "hl_style": g["hl_style"], "stroke": bool(stroke),
              "object": (spec.get("photo_kind") or "face") == "object", "script": setter.script,
              "hook": " ".join(_toks(spec["hook"].replace("|", " "))), "highlight_word": spec.get("highlight") or "",
              "focal": focal, "extended": bool(fit and fit.get("gaps")),
              "hl_scale": max([setter.scale(w) for p_ in fitd["lines"] for w in p_ if setter.is_hl(w)] or [1.0])}
    result["checks"] = readability(final, background, result, tests)
    if logo_note:
        result["checks"].append(("Logo", "WARN", logo_note))
    result["bytes"] = os.path.getsize(path)
    if size_name == "youtube" and result["bytes"] > RULES["youtube_max_bytes"]:
        jpg = path[:-4] + ".jpg"
        try:
            final.save(jpg, quality=90, optimize=True, comment=CREDIT.encode())
        except TypeError:
            final.save(jpg, quality=90, optimize=True)
        result["jpg"] = jpg
    return result


# ---------------------------------------------------------------- readability


def verdict(value, pass_at, warn_at, higher_is_better=True):
    if higher_is_better:
        return "PASS" if value >= pass_at else ("WARN" if value >= warn_at else "FAIL")
    return "PASS" if value <= pass_at else ("WARN" if value <= warn_at else "FAIL")


def pixels(img):
    raw = img.convert("RGB").tobytes()
    return [raw[i:i + 3] for i in range(0, len(raw), 3)]


def _lum_values(img):
    g = img.convert("RGB").resize((max(1, img.width // 4), max(1, img.height // 4)))
    return sorted(lum_rgb(p) for p in pixels(g))


def readability(final, background, r, tests):
    W, H = final.size
    out = []
    smallest = min(tests)
    scale = smallest / W
    cap_small = r["cap_px"] * scale
    out.append(("Hook size at %d px wide" % smallest, verdict(cap_small, RULES["cap_px_pass"], RULES["cap_px_warn"]),
                (f"capitals {cap_small:.1f} px tall" if r.get("script", "Latin") == "Latin" else
                 f"letters ({SIZE_GLYPH.get(r['script'], 'H')} height) {cap_small:.1f} px tall")
                + f" (pass at {RULES['cap_px_pass']:.0f})"))
    c_med, c_worst = _busiest_contrast(background, r["rects"]["hook"], r["text_colour"])
    if r.get("stroke"):
        c_worst = max(c_worst, contrast_hex(r["text_colour"], r["colours"]["ground"]))
    v = verdict(c_med, RULES["contrast_pass"], RULES["contrast_warn"])
    if v == "PASS" and c_worst < RULES["contrast_warn"]:
        v = "WARN"
    out.append(("Contrast behind the words", v, f"{c_med:.1f}:1 typical, {c_worst:.1f}:1 at the busiest tenth"
                + (" (outlined)" if r.get("stroke") else "")))
    x0, y0, x1, y1 = [int(v) for v in r["rects"]["hook"]]
    small = final.resize((smallest, max(1, int(H * scale))), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.0))
    sb = small.crop((max(0, int(x0 * scale)), max(0, int(y0 * scale)), max(int(x0 * scale) + 1, int(x1 * scale)),
                     max(int(y0 * scale) + 1, int(y1 * scale))))
    vals = sorted(lum_rgb(p) for p in pixels(sb))
    sq = ratio(vals[int(len(vals) * 0.95)], vals[int(len(vals) * 0.05)]) if vals else 1.0
    out.append(("Squint test", verdict(sq, RULES["squint_pass"], RULES["squint_warn"]),
                f"words still separate from their ground at {sq:.1f}:1 when blurred at {smallest} px"))
    if r.get("highlight"):
        c = r["colours"]
        hl = c["hl"]
        if hl["mode"] == "colour" and r["hl_style"] != "box":
            hv = contrast_hex(hl["colour"], c["text"])
            gv = contrast_hex(hl["colour"], c["ground"])
            v = "PASS" if hv >= 1.5 and gv >= 3 else ("WARN" if hv >= 1.2 and gv >= 2 else "FAIL")
            out.append(("Highlight stands out", v, f"highlighted word {hv:.1f}:1 against the other words, "
                                                   f"{gv:.1f}:1 against the background"))
        elif r["hl_style"] == "box" or hl["mode"] == "box" and r["hl_style"] != "big":
            bx = hl["colour"] if hl["mode"] == "box" else c["text"]
            ink = hl.get("ink") or c["ground"]
            bv, iv = contrast_hex(bx, c["ground"]), contrast_hex(bx, ink)
            v = "PASS" if bv >= 3 and iv >= 4.5 else ("WARN" if bv >= 2 and iv >= 3 else "FAIL")
            out.append(("Highlight stands out", v, f"highlight box {bv:.1f}:1 against the background, "
                                                   f"its word {iv:.1f}:1 inside it"))
        else:
            out.append(("Highlight stands out", "PASS", f"highlighted words set {r.get('hl_scale', HL_SCALE):.2f} times larger"))
    clash = []
    for name, rect in r["rects"].items():
        for kc in KEEP_CLEAR[r["aspect"]]:
            kx0, ky0, kx1, ky1 = kc[0] * W, kc[1] * H, kc[2] * W, kc[3] * H
            if rect[0] < kx1 and rect[2] > kx0 and rect[1] < ky1 and rect[3] > ky0:
                clash.append(name)
    if KEEP_CLEAR[r["aspect"]]:
        what = "duration badge" if r["aspect"] == "16:9" else "caption and buttons"
        out.append((f"Clear of the {what}", "FAIL" if clash else "PASS",
                    ("overlaps: " + ", ".join(sorted(set(clash)))) if clash else "nothing essential sits there"))
    if r["aspect"] == "9:16":
        hy0, hy1 = r["rects"]["hook"][1] / H, r["rects"]["hook"][3] / H
        inside = hy0 >= 0.125 and hy1 <= 0.875
        out.append(("Inside the profile-grid crop", "PASS" if inside else "WARN",
                    "the words sit inside the centre 3:4 crop a profile grid shows" if inside else
                    "part of the words falls outside the centre 3:4 crop a profile grid shows"))
    if r["fit"]:
        f = r["fit"]["face"]
        fh = (f[3] - f[1]) / H
        lo, hi = RULES["face_h_min"], RULES["face_h_max"]
        if r["aspect"] != "16:9":
            lo, hi = lo * 0.55, hi * 0.8
        if r.get("object"):
            lo, hi = 0.20, 0.95
        noun = "subject" if r.get("object") else "face"
        v = "PASS" if lo <= fh <= hi else "WARN"
        if r["fit"].get("visible", 1) < 0.85:
            v = "WARN"
        fv = r["fit"].get("face_visible_box", f)
        fa = max(1e-6, (fv[2] - fv[0]) * (fv[3] - fv[1]))
        ix, gap = 0.0, 1e9
        for name in ("hook", "focal"):
            hk = r["rects"].get(name)
            if not hk:
                continue
            ix += max(0, min(hk[2], fv[2]) - max(hk[0], fv[0])) * max(0, min(hk[3], fv[3]) - max(hk[1], fv[1]))
            gx = max(0, max(fv[0] - hk[2], hk[0] - fv[2]))
            gy = max(0, max(fv[1] - hk[3], hk[1] - fv[3]))
            gap = min(gap, max(gx, gy))
        share = ix / fa
        if share >= 0.10:
            v, msg = "FAIL", f"{share * 100:.0f} per cent of the {noun} is under the words"
        elif share > 0:
            v, msg = "WARN", (f"the words touch the {noun} ({share * 100:.1f} per cent overlap); move the photo "
                              f"(photo_offset), shrink it (face_scale) or shorten the words")
        elif gap < 0.012 * W:
            v, msg = "WARN", f"the words come within {gap:.0f} px of the {noun}; give them room"
        else:
            v, msg = "PASS", f"nothing touches the {noun}; nearest letter {gap:.0f} px away"
        out.append((f"Words clear of the {noun}", v, msg))
        out.append((f"{noun.capitalize()} size", v, f"{noun} is {fh * 100:.0f} per cent of the frame height, "
                                                    f"{r['fit'].get('visible', 1) * 100:.0f} per cent of it in frame"))
        up = r["fit"]["upscale"]
        out.append(("Photo sharpness", "PASS" if up <= RULES["upscale_warn"] else "WARN",
                    f"photograph enlarged {up:.2f} times" + ("; it may look soft" if up > RULES["upscale_warn"] else "")))
    if r.get("focal_info"):
        fbg, fink, fcap = r["focal_info"]
        c = contrast_hex(fbg, fink)
        out.append(("Focal element", verdict(c, RULES["contrast_pass"], RULES["contrast_warn"]),
                    f"{c:.1f}:1 inside its chip, capitals {fcap * scale:.1f} px at {smallest} px"))
    return out


# ---------------------------------------------------------------- sheet


def _label_font(px, text=""):
    """A plain face for labels on the sheets that has every character in the label."""
    return load_font(pick_font(None, text)["path"], px)


def _label_text(text, fallback):
    """The label itself, or a stand-in when no installed font can draw it (never a row of boxes)."""
    return text if not pick_font(None, text)["missing"] else fallback


def _badge(img, text="12:34"):
    d = ImageDraw.Draw(img)
    W, H = img.size
    f = load_font(pick_font(None, text)["path"], max(7, int(H * 0.075)))
    b = f.getbbox(text)
    pad = max(2, int(H * 0.025))
    w, h = b[2] - b[0] + 2 * pad, b[3] - b[1] + 2 * pad
    x, y = W - w - pad, H - h - pad
    d.rounded_rectangle([x, y, x + w, y + h], radius=3, fill=(0, 0, 0))
    d.text((x + pad - b[0], y + pad - b[1]), text, font=f, fill=(255, 255, 255))
    return img


def fit_line(text, font, max_w):
    """Cut a title at a word boundary with an ellipsis, as the platforms do."""
    if font.getlength(text) <= max_w:
        return text
    out = ""
    for w in text.split():
        trial = (out + " " + w).strip()
        if font.getlength(trial + "…") > max_w:
            break
        out = trial
    return (out or text[:3]) + "…"


def sheet(spec, results, out_path):
    rows = [r for r in results if r["size"] == (spec.get("sizes") or ["youtube"])[0]]
    if not rows:
        return None
    W, H = rows[0]["W"], rows[0]["H"]
    tests = SIZES[rows[0]["size"]][3]
    prev_w = 560 if rows[0]["aspect"] == "16:9" else 300
    prev_h = int(prev_w * H / W)
    feed_w = sum(tests) + 40 * len(tests) + 40
    th_max = int(max(tests) * H / W)
    row_h = max(prev_h, th_max * 2 + 140) + 200
    sheet_w = 40 + prev_w + 40 + feed_w + 40
    sheet_h = 160 + row_h * len(rows)
    im = Image.new("RGB", (sheet_w, sheet_h), (246, 246, 244))
    d = ImageDraw.Draw(im)
    import textwrap
    title = _label_text(spec.get("title") or spec["slug"], spec["slug"])
    pr_text = (spec.get("promise") or "") + " " + (spec.get("payoff") or "")
    big = _label_font(30, title)
    mid = _label_font(19, "".join((spec.get("reasons") or {}).values()))
    small = _label_font(15, title + pr_text + "".join((spec.get("reasons") or {}).values()))
    d.text((40, 28), fit_line(title, big, sheet_w - 80), font=big, fill=(17, 17, 17))
    pr = (f"Promise: {spec.get('promise') or '[NEED: what the thumbnail promises]'}.  Pays off: "
          f"{spec.get('payoff') or '[NEED: where the video delivers it]'}"
          + (f" at {spec['payoff_time']}" if spec.get("payoff_time") else ""))
    pr = _label_text(pr, "Promise and payoff: see the notes file (no installed font here draws their script).")
    for k, part in enumerate(textwrap.wrap(pr, 160)[:2]):
        d.text((40, 72 + 20 * k), part, font=small, fill=(60, 60, 60))
    d.text((40, 120), "Each row is one style. Right: the same thumbnail at the sizes people see it, in a dark and a "
                      "light feed, with the video length badge in place.", font=small, fill=(110, 110, 110))
    y = 160
    for i, r in enumerate(rows):
        letter = "ABCDE"[i]
        with Image.open(r["file"]) as t:
            t = t.convert("RGB")
            im.paste(t.resize((prev_w, prev_h), Image.LANCZOS), (40, y))
            x = 40 + prev_w + 40
            for mode, (bgc, fg) in enumerate((((15, 15, 15), (241, 241, 241)), ((255, 255, 255), (15, 15, 15)))):
                yy = y + mode * (th_max + 70)
                d.rectangle([x - 12, yy - 10, x + feed_w - 40, yy + th_max + 58], fill=bgc)
                cx = x
                for tw in tests:
                    th = int(tw * H / W)
                    sm = t.resize((tw, th), Image.LANCZOS)
                    if r["aspect"] == "16:9":
                        _badge(sm)
                    im.paste(sm, (cx, yy))
                    d.text((cx, yy + th + 6), fit_line(title, small, tw), font=small, fill=fg)
                    d.text((cx, yy + th + 26), f"{tw} px", font=small, fill=(130, 130, 130))
                    cx += tw + 40
        ty = y + max(prev_h, 2 * (th_max + 70)) + 12
        reason = (spec.get("reasons") or {}).get(r["direction"]) or DEFAULT_REASONS[r["direction"]]
        reason = loc(_label_text(reason, DEFAULT_REASONS[r["direction"]]), spec)
        words_on = r.get("hook") or ""
        head = f"{letter}  {DIRECTIONS[r['direction']]}" + (f":  {words_on}" if words_on else "")
        head = _label_text(head, f"{letter}  {DIRECTIONS[r['direction']]}")
        d.text((40, ty), head, font=_label_font(19, head), fill=(17, 17, 17))
        for k, part in enumerate(textwrap.wrap(reason, 150)[:2]):
            d.text((40, ty + 30 + 20 * k), part, font=small, fill=(60, 60, 60))
        items = [f"{name}: {v}" for name, v, _ in r["checks"]]
        half = (len(items) + 1) // 2
        d.text((40, ty + 76), "   ".join(items[:half]), font=small, fill=(90, 90, 90))
        d.text((40, ty + 96), "   ".join(items[half:]), font=small, fill=(90, 90, 90))
        fails = [n for n, v, _ in r["checks"] if v == "FAIL"]
        d.text((40, ty + 124), ("Reads at feed size" if not fails else "Not ready: " + ", ".join(fails)),
               font=mid, fill=(20, 110, 60) if not fails else (170, 30, 30))
        y += row_h
    meta = PngInfo()
    meta.add_text("Software", CREDIT)
    im.save(out_path, pnginfo=meta, optimize=True)
    return out_path


# ---------------------------------------------------------------- SVG fallback (no Pillow)


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def svg_one(spec, direction, size_name, out_dir, pal, family="sans-serif"):
    spec = spec_for(spec, direction)
    W, H, label, tests = SIZES[size_name]
    side = (spec.get("subject_side") or "right").lower()
    g = layout(direction, W, H, side)
    c = scheme(pal, g["ground"])
    P = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
         f'width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         f'<desc>{CREDIT}</desc><rect width="{W}" height="{H}" fill="{c["ground"]}"/>']
    photo = spec.get("cutout") if direction == "cutout" else spec.get("photo")
    fit = None
    if photo and g["photo"] is not None and os.path.isfile(photo):
        iw, ih = image_size_noPIL(photo)
        fb = spec.get("face_box") or [0.3, 0.1, 0.7, 0.55]
        fit = photo_fit(iw, ih, fb, g["photo"] if not g["cutout"] else (0, 0, 1, 1), g["face"])
        mime = "image/png" if photo.lower().endswith(".png") else "image/jpeg"
        with open(photo, "rb") as fh:
            data = base64.b64encode(fh.read()).decode()
        x0, y0, x1, y1 = g["photo"]
        if g["shape"] == "circle":
            cx, cy, rr = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2
            if c["accent"]:
                off = rr * 0.12
                P.append(f'<circle cx="{cx - off if x0 > W / 3 else cx + off:.0f}" cy="{cy + off:.0f}" r="{rr:.0f}" fill="{c["accent"]}"/>')
            P.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{rr * 1.036:.0f}" fill="{c["text"]}"/>')
            P.append(f'<clipPath id="p"><circle cx="{cx:.0f}" cy="{cy:.0f}" r="{rr:.0f}"/></clipPath>')
        elif g["shape"] == "poly":
            pts = " ".join(f"{px:.0f},{py:.0f}" for px, py in g["poly"])
            P.append(f'<clipPath id="p"><polygon points="{pts}"/></clipPath>')
        else:
            P.append(f'<clipPath id="p"><rect x="{x0:.0f}" y="{y0:.0f}" width="{x1 - x0:.0f}" height="{y1 - y0:.0f}"/></clipPath>')
        P.append(f'<image clip-path="url(#p)" x="{fit["x"]:.0f}" y="{fit["y"]:.0f}" width="{fit["sw"]:.0f}" '
                 f'height="{fit["sh"]:.0f}" xlink:href="data:{mime};base64,{data}"/>')
        if g["shape"] == "poly":
            e = [p for p in g["poly"] if 0 < p[0] < W] if g["aspect"] == "16:9" else g["poly"][:2]
            if len(e) >= 2:
                P.append(f'<line x1="{e[0][0]:.0f}" y1="{e[0][1]:.0f}" x2="{e[1][0]:.0f}" y2="{e[1][1]:.0f}" '
                         f'stroke="{c["accent"] or c["text"]}" stroke-width="{max(6, min(W, H) * 0.016):.0f}"/>')
    if g["scrim"]:
        if g["scrim"] == "bottom":
            grad = 'x1="0" y1="1" x2="0" y2="0.35"'
        elif g["scrim"] == "low-left":
            grad = 'x1="0" y1="1" x2="0.7" y2="0.2"'
        else:
            grad = 'x1="1" y1="1" x2="0.3" y2="0.2"'
        P.append(f'<linearGradient id="s" {grad}><stop offset="0" stop-color="{c["ground"]}" stop-opacity="0.92"/>'
                 f'<stop offset="1" stop-color="{c["ground"]}" stop-opacity="0"/></linearGradient>'
                 f'<rect width="{W}" height="{H}" fill="url(#s)"/>')
    upper = (spec.get("case") or "as-written").lower() == "upper"
    setter = Setter(None, spec.get("highlight"), g["hl_style"], upper, main_script(spec["hook"]), spec.get("lang"))
    hook = spec["hook"] if g["aspect"] == "16:9" else spec["hook"].replace("|", " ")
    hook = join_highlight(hook, spec.get("highlight"))
    box = g["text"]
    fitd = setter.fit(hook, box, 3, 0.9)
    size = fitd["size"]
    total = sum(setter.line_h(p, size, 0.9) for p in fitd["lines"])
    y = box[1] + ((box[3] - box[1]) - total) / 2 if g["valign"] == "center" else box[3] - total
    fam = (f"'{family}', " if family and family != "sans-serif" else "") + \
        "Inter, 'Montserrat', 'Noto Sans', 'Helvetica Neue', Arial, sans-serif"
    # each word is its own text element, so the viewer's bidi algorithm orders its letters; the words
    # themselves are placed right to left here
    for p in fitd["lines"]:
        lh = setter.line_h(p, size, 0.9)
        lw = setter.line_w(p, size)
        if g["align"] == "left":
            x = box[2] - lw if setter.rtl else box[0]
        else:
            x = box[0] + ((box[2] - box[0]) - lw) / 2
        base = y + lh * 0.82
        order = list(reversed(p)) if setter.rtl else list(p)
        for i, w in enumerate(order):
            nxt = order[i + 1] if i + 1 < len(order) else ""
            gap = setter.gap(*((nxt, w) if setter.rtl else (w, nxt)), size) if nxt else 0
            ws = size * setter.scale(w)
            fill = c["text"]
            if setter.boxed(w):
                ww = setter.word_w(w, size)
                P.append(f'<rect x="{x:.0f}" y="{base - ws * 0.86:.0f}" width="{ww:.0f}" height="{ws * 1.0:.0f}" fill="{c["hl"]["colour"]}"/>')
                fill = c["hl"].get("ink") or c["ground"]
                P.append(f'<text x="{x + BOX_PAD * ws:.0f}" y="{base:.0f}" font-family="{fam}" font-weight="900" font-size="{ws:.0f}" fill="{fill}">{_esc(Setter.disp(w))}</text>')
                x += ww + gap
                continue
            if setter.is_hl(w) and c["hl"]["mode"] == "colour":
                fill = c["hl"]["colour"]
            P.append(f'<text x="{x:.0f}" y="{base:.0f}" font-family="{fam}" font-weight="900" font-size="{ws:.0f}" fill="{fill}">{_esc(Setter.disp(w))}</text>')
            x += setter.word_w(w, size) + gap
        y += lh
    focal = (spec.get("focal") or "").strip()
    if focal:
        fs = max(int(size * 0.46), int(H * 0.055))
        fw = len(focal) * fs * 0.6 + fs * 0.64
        bgc = c["accent"] or c["text"]
        P.append(f'<rect x="{box[0]:.0f}" y="{y + size * 0.2:.0f}" width="{fw:.0f}" height="{fs * 1.2:.0f}" rx="{fs * 0.12:.0f}" fill="{bgc}"/>'
                 f'<text x="{box[0] + fs * 0.32:.0f}" y="{y + size * 0.2 + fs * 0.95:.0f}" font-family="{fam}" '
                 f'font-weight="900" font-size="{fs}" fill="{c["ground"]}">{_esc(focal)}</text>')
    P.append("</svg>")
    stem = f"{spec.get('date') or dt.date.today().isoformat()}-{spec['slug']}-{direction}-{size_name}"
    path = os.path.join(out_dir, stem + ".svg")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(P))
    cap_small = size * 0.72 * min(tests) / W
    checks = [("Hook size at %d px wide" % min(tests), verdict(cap_small, RULES["cap_px_pass"], RULES["cap_px_warn"]),
               f"capitals about {cap_small:.1f} px tall (estimated without Pillow)"),
              ("Contrast behind the words", "NOT MEASURED", "open the SVG and squint; Pillow is not available here")]
    return {"direction": direction, "size": size_name, "file": path, "checks": checks, "font_px": size,
            "lines": [" ".join(p) for p in fitd["lines"]], "fit": fit, "font": "browser font stack (SVG)", "W": W, "H": H}


# ---------------------------------------------------------------- checks on the spec


class Findings:
    def __init__(self):
        self.problems, self.warns = [], []

    def p(self, m):
        self.problems.append(m)

    def w(self, m):
        self.warns.append(m)

    def report(self):
        for m in self.problems:
            print("PROBLEM " + m)
        for m in self.warns:
            print("WARN " + m)
        print(f"{len(self.problems)} problem(s), {len(self.warns)} warning(s)")
        return 1 if self.problems else 0


def load_spec(path):
    with open(path, encoding="utf-8") as fh:
        spec = json.load(fh)
    base = os.path.dirname(os.path.abspath(path))
    for k in ("photo", "cutout"):
        if spec.get(k) and not os.path.isabs(spec[k]):
            spec[k] = os.path.normpath(os.path.join(base, spec[k]))
    b = spec.get("brand") or {}
    for k in ("logo", "font"):
        v = b.get(k)
        if v and not os.path.isabs(v) and (os.sep in v or "/" in v or v.lower().endswith((".ttf", ".otf", ".png"))):
            b[k] = os.path.normpath(os.path.join(base, v))
    od = spec.get("out_dir")
    if not od:
        od = OUTPUTS_DIR if os.path.isdir(os.path.dirname(OUTPUTS_DIR)) else "thumbnails"
    spec["out_dir"] = od if os.path.isabs(od) else os.path.normpath(os.path.join(base, od))
    spec["directions"] = [resolve_direction(d) for d in (spec.get("directions") or [])] or None
    return spec


def default_directions(spec):
    if not spec.get("photo"):
        return ["type"]
    return ["panel", "poster", "cinema"]


def hook_text(spec):
    """Every character the thumbnail itself draws, in every style: the hook (in both cases when set in
    upper case) and the focal chip."""
    out = ""
    for sp in [spec] + [dict(spec, **{k: v for k, v in (o or {}).items() if k in STYLE_KEYS})
                        for o in (spec.get("styles") or {}).values()]:
        h = (sp.get("hook") or "").replace("|", " ")
        if (sp.get("case") or "").lower() == "upper":
            h = h + " " + h.upper()
        out += " " + h + " " + (sp.get("focal") or "")
    return out


def check_script(spec, F):
    """Glyphs, shaping and line breaks for the language the words are in. A thumbnail never shows an
    empty box where a letter should be: if no font here has every character, nothing is drawn."""
    text = hook_text(spec)
    ss = scripts_in(text)
    if "Emoji" in ss:
        F.p("an emoji in the words: a thumbnail typeface cannot draw it, so it would print as an empty box. "
            "Remove it or say it in a word")
        return
    fp = pick_font((spec.get("brand") or {}).get("font"), text, spec.get("lang"))
    if fp["missing"]:
        miss = "".join(fp["missing"][:12])
        sc = ", ".join(s for s in ss if s != "Latin") or "these characters"
        F.p(f"no font on this machine can draw {miss!r} ({sc}); it would print as empty boxes. Ask the founder "
            f"for a font file that covers {sc} (for example the free Noto Sans family for that script), or "
            f"write the words in a script an installed font covers")
    elif fp["swapped"]:
        F.w(f"the founder's font {fp['swapped']} has no glyphs for some of these characters; the words are set "
            f"in {fp['desc'].split(';')[0]} instead. Tell the founder, or ask for a version of their font that "
            f"covers them")
    main = main_script(spec.get("hook") or "")
    if not HAVE_PIL and main != "Latin":
        F.w(f"without Pillow the SVG files use the viewer's own fonts for the {main} letters; open each one and "
            f"check every letter shows, not an empty box")
    if HAVE_PIL and any(s in SHAPED_SCRIPTS for s in ss) and not has_raqm():
        F.p(f"{main} letters join, reorder or stack, and this machine's Pillow has no shaping library (raqm), "
            f"so they would be drawn broken. Render where raqm is installed, or deliver the words and a layout "
            f"brief for the founder to set in their own design tool")
    hook = spec.get("hook") or ""
    for tok in hook.replace("|", " ").split():
        n = sum(1 for ch in tok if script_of(ch) in NO_SPACE_SCRIPTS)
        if n > 6:
            F.w(f"{tok!r} has no break point; put a space (or |) where a line may break. Between "
                f"{main} characters the space is not drawn")
            break
    if main in ("Han",) and not spec.get("lang"):
        F.w("Chinese characters with no lang set: drawn in Simplified Chinese letterforms. Set \"lang\": "
            "\"zh-Hant\" (Traditional) or \"zh-HK\" if that is how the founder writes")


def check_spec(spec, F):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,48}", spec.get("slug") or ""):
        F.p("slug must be lower case letters, numbers and hyphens, 2 to 49 characters")
    hook = (spec.get("hook") or "").replace("|", " ").strip()
    n = hook_units(hook)
    if n == 0:
        F.p("no hook: at feed size the thumbnail is its words and its face")
    elif n > RULES["words_max"]:
        F.p(f"hook is {n} words; six is the hard limit, three reads fastest")
    elif n > RULES["words_good"]:
        F.w(f"hook is {n} words; five is the working limit")
    if hook.endswith("."):
        F.w("the hook ends in a full stop; a thumbnail phrase is not a sentence")
    if re.search(r"\bmore\b", hook, re.I):
        F.p("'more' in the hook says nothing a viewer can picture; give the number or the comparison")
    for k in ("hook", "focal", "title", "promise", "payoff"):
        if DASHES.search(spec.get(k) or ""):
            F.p(f"an en or em dash in {k}")
    hl = (spec.get("highlight") or "").strip()
    if hl and len(hl.split()) == 1 and _clean(hl) not in [_clean(w) for w in hook.split()]:
        F.p(f"highlight {hl!r} is not a word in the hook")
    if hl and len(hl.split()) > 1:
        if not re.search(r"\s+".join(re.escape(x) for x in hl.split()), hook, re.I):
            F.p(f"highlight {hl!r} is not a run of words in the hook")
        elif len(hl.split()) > 3:
            F.p("highlight is more than three words; it is the focal point, not a second headline")
        elif not number_claims(hl):
            F.w("highlight is several words with no number; a number and its unit read as one, other phrases compete")
    for k, lo, hi in (("focal_scale", 0.6, 2.6), ("highlight_scale", 0.8, 2.2), ("face_scale", 0.6, 1.4),
                      ("text_width", 0.40, 0.70)):
        v = spec.get(k)
        if v not in (None, "") and not (lo <= float(v) <= hi):
            F.w(f"{k} {v} is outside {lo} to {hi}; it is clamped to that range")
    title = spec.get("title") or ""
    if not title.strip():
        F.w("no title; the title and the thumbnail are read together and should not repeat each other")
    else:
        tw = set(w.lower().strip("?!.,:;") for w in words(title))
        hw = set(w.lower().strip("?!.,:;") for w in words(hook))
        if hw and hw <= tw:
            F.w("every word of the hook is already in the title; the thumbnail adds nothing the title does not say")
        else:
            rep_ = sorted(w for w in hw & tw if len(w) >= 4 and not number_claims(w))
            if rep_:
                F.w(f"the hook repeats {', '.join(repr(w) for w in rep_)} from the title; the thumbnail should say the "
                    f"half the title does not")
    focal = (spec.get("focal") or "").strip()
    if focal and len(words(focal)) > 2:
        F.w("the focal element is more than two words; it is the second thing read, not a second headline")
    if focal and hl:
        F.w("both a highlight word and a focal element: two focal points read as none. Keep one")
    promise, payoff = (spec.get("promise") or "").strip(), (spec.get("payoff") or "").strip()
    if not promise:
        F.p("promise is empty: write what the title and thumbnail together promise the viewer")
    if not payoff or payoff.startswith("[NEED"):
        F.p("payoff is empty: say where the video delivers the promise, or change the hook. A thumbnail "
            "the video does not pay off buys one click and costs the next ten")
    if payoff and not spec.get("payoff_time"):
        F.w("no payoff_time: name roughly when in the video the promise is delivered (for example 3:40)")
    pt = spec.get("payoff_time") or ""
    if pt and not re.fullmatch(r"\d{1,2}:\d{2}(:\d{2})?", pt):
        F.w(f"payoff_time {pt!r} is not in m:ss form")
    for claim in number_claims(hook) + number_claims(focal):
        if not number_backed(claim, payoff + " " + promise + " " + title):
            F.p(f"the number {claim[0]} on the thumbnail does not appear in the payoff or the promise. A number "
                f"on a thumbnail is a claim; the video has to show it (a short form such as 10k may round a "
                f"figure down, never up)")
    for m in ABSOLUTES.finditer(hook + " " + focal):
        F.w(f"{m.group(0)!r} is an absolute; check the payoff really delivers it, or soften the hook")
    if hook:
        check_script(spec, F)
    photo = spec.get("photo")
    dirs = spec.get("directions") or default_directions(spec)
    if (spec.get("photo_kind") or "face") not in ("face", "object"):
        F.p("photo_kind must be face or object")
    if photo:
        if not os.path.isfile(photo):
            F.p(f"photo not found: {photo}")
        else:
            try:
                w, h = image_size(photo)
                if min(w, h) < RULES["short_side_min"]:
                    F.w(f"the photograph is {w}x{h}; under {RULES['short_side_min']} px on its short side it will "
                        f"look soft at 1280x720")
            except Exception as exc:
                F.p(f"photo cannot be read ({exc})")
            if HAVE_PIL:
                try:
                    with Image.open(photo) as im:
                        cols = im.convert("RGB").getcolors(1 << 16)
                    if cols:
                        counts = sorted((c for c, _ in cols), reverse=True)
                        if sum(counts[:8]) / float(sum(counts) or 1) > 0.90:
                            F.w("this image looks like an illustration or a graphic, not a photograph; fine if "
                                "that is the channel's look, but say so")
                except Exception:
                    pass
        fb = spec.get("face_box")
        if not fb or len(fb) != 4:
            F.p("no face_box: give where the face (or the subject) sits as [left, top, right, bottom] fractions")
        else:
            l, t, r, b = [float(x) for x in fb]
            if not (0 <= l < r <= 1 and 0 <= t < b <= 1):
                F.p("face_box must be fractions with left < right and top < bottom")
    elif any(d != "type" for d in dirs):
        F.p("styles other than 'type' need a photo")
    if "cutout" in dirs:
        c = spec.get("cutout")
        if not c or not os.path.isfile(c):
            F.p("the cut-out style needs a transparent PNG of the person (cutout)")
        elif HAVE_PIL:
            with Image.open(c) as im:
                if im.mode not in ("RGBA", "LA") and "transparency" not in im.info:
                    F.p("the cutout file has no transparency; use a PNG with the background removed")
    for d in dirs:
        if d not in DIRECTIONS:
            F.p(f"unknown style {d!r}; use {', '.join(DIRECTIONS)}")
    for s in spec.get("sizes") or ["youtube"]:
        if s not in SIZES:
            F.p(f"unknown size {s!r}; use {', '.join(SIZES)}")
    if (spec.get("subject_side") or "right").lower() not in ("left", "right"):
        F.p("subject_side must be left or right")
    b = spec.get("brand") or {}
    named = [c for c in (b.get("named") or []) if c]
    if named:
        F.p(f"colour given by name only ({', '.join(named)}): ask once for a screenshot to sample (colours "
            f"command) or offer swatches (swatches command); never drop it silently")
    if (b.get("mode") or "plain") == "brand":
        try:
            pal = palette(spec)
            dk = scheme(pal, "dark")
            lt = scheme(pal, "light")
            for nm, s in (("dark", dk), ("light", lt)):
                if contrast_hex(s["text"], s["ground"]) < 4.5:
                    F.p(f"words on the {nm} background read at only {contrast_hex(s['text'], s['ground']):.2f}:1 (4.5:1 needed)")
            if not pal["accents"]:
                F.w("no brand colour works as a highlight colour, so the highlight becomes a filled box or a "
                    "larger word; that is a deliberate choice, not a fault")
            if len(pal["given"]) > 3:
                F.w("more than three brand colours given; a thumbnail uses two dominant colours and one accent")
        except ValueError as exc:
            F.p(str(exc))
        given = [_norm(c) for c in (b.get("colours") or [])] + ["#000000", "#FFFFFF", PLAIN["ink"]]
        for k in ("ground", "accent"):
            if b.get(k) and _norm(b[k]) not in given:
                F.p(f"brand {k} {b[k]} is not one of the founder's colours (or black or white). Never mix a "
                    f"shade or tint of their colour; for 'brighter' use white, a box in their light colour, "
                    f"a larger figure, or a deeper shade on the photo")
        if b.get("logo") and not os.path.isfile(b["logo"]):
            F.p(f"logo not found: {b['logo']}")
        if b.get("font") and (b["font"].lower().endswith((".ttf", ".otf"))) and not os.path.isfile(b["font"]):
            F.p(f"font file not found: {b['font']}")
    return F


# ---------------------------------------------------------------- colours from a screenshot or a name

NAMED = {
    "cream": ["#F3EBD8", "#EFE4C8", "#F7F1E3"], "ivory": ["#FFFFF0", "#F6F1E1", "#FAF6EA"],
    "beige": ["#E8DCC4", "#D9C9A8", "#EFE6D2"], "sand": ["#E3D3B4", "#D8C29A", "#EDE2CC"],
    "navy": ["#14213D", "#1B2A4A", "#0E1F3B"], "royal blue": ["#2448A6", "#1F4FBF", "#2A5AD6"],
    "sky blue": ["#7CC4F0", "#9ED3F2", "#5AB4E6"], "teal": ["#0F6F6F", "#14807A", "#1A8C8C"],
    "forest green": ["#1F3D2B", "#234A33", "#1B3A2A"], "sage": ["#9CAF88", "#A8B89A", "#8FA37C"],
    "olive": ["#6B6B2E", "#7A7A3A", "#5E6128"], "mint": ["#BFE8D2", "#A8E0C4", "#CFF0DD"],
    "green": ["#2E7D4F", "#3A8F5C", "#24693F"], "emerald": ["#0F7A55", "#138A61", "#0C6B4A"],
    "burgundy": ["#6D1A2E", "#7A1F35", "#5E1627"], "red": ["#C8282E", "#D63A33", "#B71F2A"],
    "coral": ["#F07362", "#F4846F", "#E8604F"], "terracotta": ["#C8643B", "#B85A35", "#D4704A"],
    "orange": ["#E8742A", "#F0832F", "#D9652A"], "mustard": ["#D9A82B", "#E3B23C", "#C89A22"],
    "gold": ["#D4A72C", "#E0B43F", "#C49A26"], "yellow": ["#F6D33C", "#FFD84D", "#F2C935"],
    "pink": ["#E88AA8", "#F09BB5", "#DE7898"], "blush": ["#F2C6C2", "#EDB8B3", "#F6D3CF"],
    "purple": ["#5B2A86", "#6A3399", "#4E2475"], "lavender": ["#B9A7D9", "#C7B8E2", "#AA96CF"],
    "charcoal": ["#2B2B2B", "#333333", "#26292C"], "grey": ["#8A8D91", "#9A9DA1", "#7A7D81"],
    "black": ["#111111", "#000000", "#1A1A1A"], "white": ["#FFFFFF", "#FAFAFA", "#F5F5F5"],
    "brown": ["#6B4A2F", "#7A5536", "#5C3F27"], "blue": ["#1F5FBF", "#2A6FD6", "#1A52A6"],
}


def _swatch_sheet(rows, out_path):
    f = _label_font(22, "".join(r[0] for r in rows))
    sw = 180
    im = Image.new("RGB", (60 + sw * 3 + 40 * 2, 40 + len(rows) * (sw + 70)), (250, 250, 248))
    d = ImageDraw.Draw(im)
    y = 30
    for label, cols in rows:
        d.text((30, y), label, font=f, fill=(17, 17, 17))
        x = 30
        for k, c in enumerate(cols):
            d.rounded_rectangle([x, y + 34, x + sw, y + 34 + sw - 40], radius=14, fill=hex_rgb(c))
            d.text((x, y + sw), f"{'ABC'[k] if len(cols) <= 3 else k + 1}  {c}", font=f, fill=(60, 60, 60))
            x += sw + 40
        y += sw + 70
    im.save(out_path)
    return out_path


def cmd_swatches(a):
    rows = []
    for name in a.names:
        key = name.lower().strip()
        cands = NAMED.get(key) or next((v for k, v in NAMED.items() if k in key or key in k), None)
        if not cands:
            print(f"No built-in swatches for {name!r}. Ask for a screenshot of the logo or website instead.")
            continue
        rows.append((name, cands))
        print(f"{name}: " + ", ".join(f"{'ABC'[i]} {c}" for i, c in enumerate(cands)))
    if rows and HAVE_PIL:
        out = a.out or "."
        os.makedirs(out, exist_ok=True)
        p = _swatch_sheet(rows, os.path.join(out, "colour-swatches.png"))
        print(f"Swatch sheet: {p} (show it and let the founder pick; record the pick as their choice)")
    return 0


def cmd_colours(a):
    """The main colours in a screenshot of the founder's logo, website or brand sheet."""
    if not HAVE_PIL:
        print("Pillow is not available: ask the founder for the hex codes instead.")
        return 0
    with Image.open(a.image) as im:
        im = im.convert("RGBA")
        im.thumbnail((400, 400))
        raw = im.tobytes()
        opaque = [raw[i:i + 3] for i in range(0, len(raw), 4) if raw[i + 3] > 200]  # ignore see-through areas
        if not opaque:
            print("The image has no solid colour in it.")
            return 0
        im = Image.frombytes("RGB", (len(opaque), 1), b"".join(opaque))
        q = im.quantize(colors=8, method=Image.Quantize.MEDIANCUT)
        pal = q.getpalette()[:24]
        counts = sorted(q.getcolors(), reverse=True)
    out = []
    total = sum(c for c, _ in counts)
    for cnt, idx in counts:
        r, g, b = pal[idx * 3:idx * 3 + 3]
        c = f"#{r:02X}{g:02X}{b:02X}"
        out.append((c, cnt / total))
    print("Main colours, most used first (share of the image):")
    for c, share in out:
        print(f"  {c}  {share * 100:.0f} per cent")
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        p = _swatch_sheet([("From your screenshot", [c for c, _ in out[:3]]),
                           ("Also in it", [c for c, _ in out[3:6]] or [out[0][0]])],
                          os.path.join(a.out, "colours-from-screenshot.png"))
        print(f"Swatch sheet: {p}")
    print("Confirm with the founder which is which before using them; a background colour in a screenshot is "
          "not always a brand colour.")
    return 0


# ---------------------------------------------------------------- commands


def cmd_fonts(_a):
    fonts = find_fonts()
    if not fonts:
        print("No open-licence bold font found. The render uses Pillow's bundled sans, emboldened, "
              "unless the founder supplies a font file.")
        return 0
    seen = set()
    for f in fonts:
        k = (f["family"], f["weight"])
        if k in seen:
            continue
        seen.add(k)
        print(f"{f['family']} | weight {f['weight']} | licence {f['licence']} | {f['file']}")
    print(f"First choice: {fonts[0]['family']}")
    return 0


def cmd_inspect(a):
    p = a.photo
    if not os.path.isfile(p):
        print(f"PROBLEM photo not found: {p}")
        return 2
    w, h = image_size(p)
    print(f"Size: {w}x{h} ({'portrait' if h > w else 'landscape' if w > h else 'square'})")
    if min(w, h) < RULES["short_side_min"]:
        print(f"WARN under {RULES['short_side_min']} px on the short side; it will look soft at 1280x720")
    if not HAVE_PIL:
        print("Pillow is not available: no grid overlay. Estimate the face box from the photo by eye.")
        return 0
    with Image.open(p) as im:
        alpha = im.mode in ("RGBA", "LA") or "transparency" in im.info
        cols = im.convert("RGB").getcolors(1 << 16)
        kind = "photograph"
        if cols:
            counts = sorted((c for c, _ in cols), reverse=True)
            if sum(counts[:8]) / float(sum(counts) or 1) > 0.90:
                kind = "illustration or graphic"
        print(f"Kind: {kind}")
        print(f"Transparent background: {'yes, usable for the cut-out style' if alpha else 'no'}")
        g = im.convert("RGB").copy()
        g.thumbnail((1000, 1000))
        d = ImageDraw.Draw(g)
        f = _label_font(max(12, g.width // 45))
        for i in range(1, 20):
            x, y = g.width * i / 20, g.height * i / 20
            major = i % 2 == 0
            col = (255, 0, 90) if major else (255, 160, 190)
            d.line([(x, 0), (x, g.height)], fill=col, width=1)
            d.line([(0, y), (g.width, y)], fill=col, width=1)
            if major:
                d.text((x + 3, 3), f"{i / 20:.1f}", font=f, fill=(255, 255, 0), stroke_width=2, stroke_fill=(0, 0, 0))
                d.text((3, y + 3), f"{i / 20:.1f}", font=f, fill=(255, 255, 0), stroke_width=2, stroke_fill=(0, 0, 0))
        out_dir = a.out or os.path.dirname(os.path.abspath(p))
        os.makedirs(out_dir, exist_ok=True)
        gp = os.path.join(out_dir, os.path.splitext(os.path.basename(p))[0] + "-grid.png")
        g.save(gp)
        print(f"Grid overlay: {gp} (lines every 0.05; read the face box as [left, top, right, bottom], "
              f"hair to chin, ear to ear)")
    return 0


def check_all(spec, F):
    """The base spec, then each style's own words, so every word option drawn is checked."""
    check_spec(spec, F)
    dirs = spec.get("directions") or default_directions(spec)
    seen = set(F.problems) | set(F.warns)
    for d in dirs:
        over = (spec.get("styles") or {}).get(d)
        if not over:
            continue
        bad = [k for k in over if k not in STYLE_KEYS and not k.startswith("_")]
        if bad:
            F.w(f"[{d}] ignored fields: {', '.join(bad)} (a style may set {', '.join(STYLE_KEYS)})")
        sub = check_spec(spec_for(spec, d), Findings())
        for m in sub.problems:
            if m not in seen:
                F.p(f"[{d}] {m}")
        for m in sub.warns:
            if m not in seen:
                F.w(f"[{d}] {m}")
    hooks = {(spec_for(spec, d).get("hook") or "").replace("|", " ").strip() for d in dirs}
    hk = [set(w.lower().strip("?!.,:;|") for w in words((spec_for(spec, d).get("hook") or "").replace("|", " "))
              if not number_claims(w))
          for d in dirs]
    for i in range(len(hk)):
        for j in range(i + 1, len(hk)):
            a_, b_ = hk[i], hk[j]
            if a_ and b_ and a_ != b_ and len(a_ & b_) / float(min(len(a_), len(b_))) > 0.5:
                F.w(f"{dirs[i]} and {dirs[j]} carry nearly the same words; give each a different angle "
                    f"(outcome, before and after, named object, mistake)")
    if len(dirs) >= 3 and len(hooks) == 1:
        F.w("every style carries the same words; give at least two styles a different word option "
            "(styles.<name>.hook) so the founder sees the options drawn, not listed")
    return F


def cmd_check(a):
    spec = load_spec(a.spec)
    return check_all(spec, Findings()).report()


def cmd_render(a):
    spec = load_spec(a.spec)
    code = check_all(spec, Findings()).report()
    if code:
        print("Not rendered: fix the problems above.")
        return 1
    os.makedirs(spec["out_dir"], exist_ok=True)
    if a.date:
        spec["date"] = a.date
    moved = None if a.keep else archive_round(spec)
    pal = palette(spec)
    dirs = spec.get("directions") or default_directions(spec)
    sizes = spec.get("sizes") or ["youtube"]
    results = []
    fp = pick_font((spec.get("brand") or {}).get("font"), hook_text(spec), spec.get("lang"))
    font_path, font_desc = fp["path"], fp["desc"]
    if not HAVE_PIL or a.svg:
        for s in sizes:
            for d in dirs:
                results.append(svg_one(spec, d, s, spec["out_dir"], pal, fp["family"]))
        if not HAVE_PIL:
            print("NOTE Pillow is not available, so the thumbnails are SVG files with the photograph embedded. "
                  "Open each in a browser to view it, or in any design tool to export a PNG. Contrast and the "
                  "squint test were not measured.")
    if HAVE_PIL:
        results += [render_one(spec, d, s, spec["out_dir"], font_path, font_desc, pal) for s in sizes for d in dirs]
    print(f"Colours: {pal['mode']} (dark {pal['dark']}, light {pal['light']}, accents {', '.join(pal['accents']) or 'none'})")
    print(f"Typeface: {font_desc if HAVE_PIL else 'browser font stack'}")
    sc = main_script(spec["hook"])
    if sc != "Latin":
        print(f"Script: {sc}" + (", right to left" if sc in RTL_SCRIPTS else "")
              + (", shaped with raqm" if sc in SHAPED_SCRIPTS and has_raqm() else ""))
    any_fail = False
    for r in results:
        print(f"\n{DIRECTIONS[r['direction']]} | {r['size']} {r['W']}x{r['H']} | {r['file']}")
        if r.get("extended"):
            print("  Photo moved or shrunk past its edge: the gap is filled with a soft, blurred extension of the "
                  "same photo. Tell the founder in one line.")
        print(f"  Hook set at {r['font_px']} px in {len(r['lines'])} line(s): " + " / ".join(r["lines"]))
        for name, v, detail in r["checks"]:
            print(f"  {v:<5} {name}: {detail}")
            any_fail = any_fail or v == "FAIL"
        if r.get("bytes"):
            print(f"  File: {r['bytes'] / 1024:.0f} KB" + (" (over YouTube's 2 MB limit; JPEG written: " + r["jpg"] + ")"
                                                         if r.get("jpg") else ""))
    if HAVE_PIL:
        sp = os.path.join(spec["out_dir"], f"{spec.get('date') or dt.date.today().isoformat()}-{spec['slug']}-compare.png")
        sheet(spec, [r for r in results if r["file"].endswith(".png")], sp)
        print(f"\nComparison and readability sheet: {sp}")
    notes = write_notes(spec, results, pal, font_desc)
    print(f"Notes: {notes}")
    if moved:
        print(f"The previous round ({moved[1]} files) was moved to {moved[0]}; this folder holds only this round.")
    if spec.get("photo"):
        print("The photograph was read from this machine and composited here. Nothing was uploaded or sent.")
    else:
        print("No photograph was used. Nothing was uploaded or sent.")
    return 1 if any_fail else 0


def archive_round(spec):
    """Each revision keeps one slug. Before drawing, the files from the last round move to
    earlier/round-N/, so the founder's folder only ever holds the current set."""
    out = spec["out_dir"]
    prefix = f"{spec.get('date') or dt.date.today().isoformat()}-{spec['slug']}-"
    old = [f for f in os.listdir(out) if f.startswith(prefix) and os.path.isfile(os.path.join(out, f))]
    if not old:
        return None
    base = os.path.join(out, "earlier")
    n = 1
    while os.path.isdir(os.path.join(base, f"round-{n}")):
        n += 1
    dest = os.path.join(base, f"round-{n}")
    os.makedirs(dest, exist_ok=True)
    for f in old:
        os.replace(os.path.join(out, f), os.path.join(dest, f))
    return dest, len(old)


US_SPELLING = (("colours", "colors"), ("Colours", "Colors"), ("colour", "color"), ("Colour", "Color"),
               ("per cent", "percent"), ("centre", "center"), ("grey", "gray"), ("recognised", "recognized"))


def loc(text, spec):
    """Founder-facing words in the founder's own spelling (spec "spelling": "us" for American)."""
    if (spec.get("spelling") or "").lower() in ("us", "american", "en-us"):
        for a_, b_ in US_SPELLING:
            text = text.replace(a_, b_)
    return text


def write_notes(spec, results, pal, font_desc):
    date = spec.get("date") or dt.date.today().isoformat()
    path = os.path.join(spec["out_dir"], f"{date}-{spec['slug']}-notes.md")
    first = (spec.get("sizes") or ["youtube"])[0]
    L = [f"# Thumbnail notes: {spec.get('title') or spec['slug']}", "",
         f"Made {date}. {CREDIT}.", "",
         "## What it promises, and where the video delivers it", "",
         f"- Title: {spec.get('title') or '[NEED: title]'}",
         "- Words on the thumbnail: " + "; ".join(dict.fromkeys(
             f"{r.get('hook') or ' '.join(_toks(spec['hook'].replace('|', ' ')))} ({DIRECTIONS[r['direction']]})"
             for r in results if r["size"] == (spec.get("sizes") or ["youtube"])[0])),
         f"- The promise: {spec.get('promise')}",
         f"- Where the video delivers it: {spec.get('payoff')}" + (f" (at {spec['payoff_time']})" if spec.get('payoff_time') else ""), "",
         "## Look", "",
         ("- Palette: black and white with your photo; nothing was invented" if pal["mode"] == "plain" else
          "- Palette: your " + ", ".join(pal["given"]) + " (plus black or white where words need it)"),
         f"- Typeface: {font_desc if HAVE_PIL else 'browser font stack (SVG)'}", "",
         "## The styles", ""]
    firsts = [r for r in results if r["size"] == first and r["file"].endswith(".png")] or \
        [r for r in results if r["size"] == first]
    for i, r in enumerate(firsts):
        reason = (spec.get("reasons") or {}).get(r["direction"]) or DEFAULT_REASONS[r["direction"]]
        fails = [n for n, v, _ in r["checks"] if v == "FAIL"]
        warns = [n for n, v, _ in r["checks"] if v == "WARN"]
        L += [f"### {'ABCDE'[i]}. {DIRECTIONS[r['direction']]}", "", f"File: {os.path.basename(r['file'])}", "",
              f"Words: {r.get('hook') or spec['hook'].replace('|', ' ')}", "",
              f"Why: {reason}", ""] + (["Photo: moved or shrunk at your request; the strip it no longer covers is a "
                                        "soft, blurred extension of the same photo.", ""] if r.get("extended") else []) + [
              "Reads at phone and sidebar size: " + ("yes" if not fails else "not yet (" + ", ".join(fails) + ")")
              + (f". Worth a look: {', '.join(warns).lower()}." if warns else "."), ""]
    L += ["## The checks in full", "", "For the record. Every measure, every style.", ""]
    for r in results:
        L += [f"### {DIRECTIONS[r['direction']]}, {r['size']}", "", "| Check | Result | Detail |", "|---|---|---|"]
        L += [f"| {n} | {v} | {d} |" for n, v, d in r["checks"]]
        L.append("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(loc("\n".join(L), spec))
    return path


def cmd_test(a):
    if not HAVE_PIL:
        print("Pillow is not available: open the thumbnail at about 168 px wide and squint at it.")
        return 0
    with Image.open(a.image) as im:
        im = im.convert("RGB")
        W, H = im.size
        asp = aspect_of(W, H)
        tests = {"16:9": [360, 246, 168], "1:1": [300, 160, 110], "9:16": [270, 180, 120]}[asp]
        print(f"Size: {W}x{H} ({asp})")
        if asp == "16:9" and (W, H) != (1280, 720):
            print(f"WARN YouTube's recommended size is 1280x720; this is {W}x{H}")
        small = im.resize((min(tests), int(H * min(tests) / W)), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.0))
        vals = sorted(lum_rgb(px) for px in pixels(small))
        spread = ratio(vals[int(len(vals) * 0.95)], vals[int(len(vals) * 0.05)])
        print(f"{verdict(spread, 4.5, 3.0)} Overall light to dark spread at {min(tests)} px, blurred: {spread:.1f}:1")
        if a.words:
            n = hook_units(a.words)
            v = "PASS" if n <= RULES["words_good"] else ("WARN" if n <= RULES["words_max"] else "FAIL")
            print(f"{v} Words on the thumbnail: {n} (three reads fastest, five is the working limit, six the most)")
        if a.text_box:
            l, t, r_, b = a.text_box
            lines = max(1, a.lines or 1)
            cap_full = (b - t) * H / lines * 0.70
            c = cap_full * min(tests) / W
            print(f"{verdict(c, RULES['cap_px_pass'], RULES['cap_px_warn'])} Hook size at {min(tests)} px wide: "
                  f"capitals about {c:.1f} px tall (estimated from a text block {b - t:.2f} of the height in {lines} line(s))")
        if asp == "16:9":
            zone = im.crop((int(W * 0.80), int(H * 0.80), W, H)).convert("L").filter(ImageFilter.FIND_EDGES)
            busy = sum(1 for v in zone.tobytes() if v > 60) / float(zone.width * zone.height)
            print(f"{'WARN' if busy > 0.04 else 'PASS'} Video length badge corner: {busy * 100:.0f} per cent edge "
                  f"detail (words or a logo there are covered by the badge)")
        sh_w = sum(tests) + 40 * (len(tests) + 1)
        th = int(max(tests) * H / W)
        sh = Image.new("RGB", (sh_w, th * 2 + 140), (246, 246, 244))
        d = ImageDraw.Draw(sh)
        y = 20
        for bgc in ((15, 15, 15), (255, 255, 255)):
            d.rectangle([0, y - 10, sh_w, y + th + 40], fill=bgc)
            x = 40
            for tw in tests:
                t = im.resize((tw, int(H * tw / W)), Image.LANCZOS)
                if asp == "16:9":
                    _badge(t)
                sh.paste(t, (x, y))
                x += tw + 40
            y += th + 60
        out = a.out or os.path.dirname(os.path.abspath(a.image))
        os.makedirs(out, exist_ok=True)
        op = os.path.join(out, os.path.splitext(os.path.basename(a.image))[0] + "-readability.png")
        sh.save(op)
        print(f"Small-size sheet: {op} (open it: can you read the words at the smallest size, and is the face still a face?)")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fonts")
    i = sub.add_parser("inspect")
    i.add_argument("photo")
    i.add_argument("--out")
    c = sub.add_parser("check")
    c.add_argument("spec")
    r = sub.add_parser("render")
    r.add_argument("spec")
    r.add_argument("--svg", action="store_true", help="also write editable SVG files")
    r.add_argument("--date")
    r.add_argument("--keep", action="store_true", help="do not move the previous round to earlier/")
    t = sub.add_parser("test")
    t.add_argument("image")
    t.add_argument("--out")
    t.add_argument("--words", help="the words on the existing thumbnail, typed out")
    t.add_argument("--text-box", type=float, nargs=4, metavar=("L", "T", "R", "B"),
                   help="the block of words as fractions, read off the inspect grid")
    t.add_argument("--lines", type=int, help="how many lines of words are in that block")
    s = sub.add_parser("swatches")
    s.add_argument("names", nargs="+")
    s.add_argument("--out")
    k = sub.add_parser("colours")
    k.add_argument("image")
    k.add_argument("--out")
    a = ap.parse_args(argv)
    try:
        return {"fonts": cmd_fonts, "inspect": cmd_inspect, "check": cmd_check, "render": cmd_render,
                "test": cmd_test, "swatches": cmd_swatches, "colours": cmd_colours}[a.cmd](a)
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as exc:
        print(f"PROBLEM {exc.__class__.__name__}: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
