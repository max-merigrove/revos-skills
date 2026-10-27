#!/usr/bin/env python3
"""Prove every quote in the scan is the founder's own words, word for word.

Usage:
  python3 scripts/verify_quotes.py <extraction.json>

Checks every answer in the five-question table, every fact quote, every "also worth fixing" quote and every "current" line in the edits against
the clean text of the asset it is attributed to. Case, curly quotes and line breaks are ignored, and so is a
word a PDF split across two lines with a hyphen; nothing else is. A quote may skip words with "..." if each piece appears, in order. A quote must
be 2 to 45 words: a cell holds the line that answers the question, not the paragraph around it.
Prints OK or one PROBLEM line per quote, with the nearest real sentence to copy from.
Exit 0 all found; exit 1 problems; exit 2 with one STOP line if the input cannot be used.
Standard library only.
"""
import difflib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scan_common as C  # noqa: E402

MAX_QUOTE_WORDS = 45


def found(quote, source_norm):
    q = C.norm_text(quote).strip(" \"'")
    q = re.sub(r"[.,;:!?]+$", "", q)
    pieces = [p.strip(" ,;:") for p in re.split(r"\s*\.\.\.\s*", q) if p.strip(" ,;:")]
    if not pieces:
        return False
    pos = 0
    for p in pieces:
        i = source_norm.find(p, pos)
        if i < 0:
            return False
        pos = i + len(p)
    return True


def nearest(quote, source):
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", source) if len(C.words(s)) >= 2]
    best = difflib.get_close_matches(C.norm_text(quote), [C.norm_text(s) for s in sents], n=1, cutoff=0.3)
    if not best:
        return None
    for s in sents:
        if C.norm_text(s) == best[0]:
            return s[:160]
    return None


def asset_texts(ext, base):
    texts = {}
    for a in ext.get("assets", []):
        f = Path(a.get("file") or "")
        if not f.is_absolute():
            f = base / f
        texts[a["id"]] = C.read_text(f, f"text of asset '{a['id']}'")
    return texts


def check(ext, base):
    """Return (problems, count_ok). Problems are plain sentences."""
    problems, ok = [], 0
    texts = asset_texts(ext, base)
    norms = {k: C.norm_text(v) for k, v in texts.items()}
    unwrapped = {k: C.norm_text(C.unwrap(v)) for k, v in texts.items()}  # "peo-\nple" read as "people" too
    labels = {a["id"]: a.get("label", a["id"]) for a in ext.get("assets", [])}

    def one(where, aid, quote):
        nonlocal ok
        if aid not in texts:
            problems.append(f"{where}: no asset with id '{aid}'.")
            return
        n = len(C.words(quote))
        if n < 2:
            problems.append(f"{where}: quote '{quote}' is under two words; quote the line that answers.")
            return
        if n > MAX_QUOTE_WORDS:
            problems.append(f"{where}: quote is {n} words; keep it to the line that answers ({MAX_QUOTE_WORDS} at most).")
            return
        if found(quote, norms[aid]) or found(quote, unwrapped[aid]):
            ok += 1
            return
        near = nearest(quote, texts[aid])
        hint = f" Nearest line in {labels[aid]}: \"{near}\"" if near else ""
        problems.append(f"{where}: not found word for word in {labels[aid]}: \"{quote[:120]}\".{hint}")

    for q in C.QKEYS:
        row = (ext.get("answers") or {}).get(q) or {}
        for aid, cell in row.items():
            if cell is None:
                continue
            quote = cell.get("quote") if isinstance(cell, dict) else cell
            if not quote:
                continue
            one(f"{C.QLABEL[q]} / {labels.get(aid, aid)}", aid, quote)
    for k, f in enumerate(ext.get("facts") or [], 1):
        for c in (f.get("cells") or []) if isinstance(f, dict) else []:
            if isinstance(c, dict) and c.get("quote"):
                one(f"Fact {k} ({f.get('what', '')} / {labels.get(c.get('asset'), c.get('asset'))})", c.get("asset"), c["quote"])
    for k, x in enumerate(ext.get("also") or [], 1):
        if isinstance(x, dict) and x.get("quote"):
            one(f"Also worth fixing {k} ({x.get('what', '')})", x.get("asset"), x["quote"])
    for k, e in enumerate(ext.get("edits") or [], 1):
        aid = e.get("asset")
        if e.get("current"):
            one(f"Edit {k} ({labels.get(aid, aid)}), current line", aid, e["current"])
        elif e.get("after"):
            one(f"Edit {k} ({labels.get(aid, aid)}), insert after", aid, e["after"])
    return problems, ok


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    path = Path(sys.argv[1])
    ext = C.load_json(path, "extraction file")
    if not isinstance(ext, dict) or not isinstance(ext.get("assets"), list):
        C.stop("the extraction file has no asset list. Start from assets/extraction-template.json.")
    problems, ok = check(ext, path.resolve().parent)
    for p in problems:
        print("PROBLEM:", p)
    print(f"{ok} quotes found word for word, {len(problems)} problems.")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"STOP: the quote check could not finish ({type(e).__name__}: {e}). Check the extraction file's shape.")
        sys.exit(2)
