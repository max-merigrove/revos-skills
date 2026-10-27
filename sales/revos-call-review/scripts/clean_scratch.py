#!/usr/bin/env python3
"""Delete this skill's working files once the review is finished, so no copy of the transcript is left behind.

Usage:
  python3 scripts/clean_scratch.py <scratch folder>

Removes only the files this skill writes there (the saved transcript, the founder's message, the measure, verdicts,
results, review, previous and founder files), then the folder itself if nothing else is in it. Anything else in the
folder is left alone and listed. The delivered Word file and the memory file live elsewhere and are never touched.
Exit 0 done (or nothing to do); exit 2 STOP when the path is not a folder. Standard library only.
"""
import os
import sys

OURS = {"transcript.txt", "transcript.md", "transcript.vtt", "transcript.srt", "transcript.docx", "founder-message.txt",
        "measure.json", "verdicts.json", "results.json", "review.md", "previous.json", "memory.md", "founder.json"}


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    d = sys.argv[1]
    if not os.path.exists(d):
        print(f"Nothing to clean: {d} is already gone.")
        return 0
    if not os.path.isdir(d):
        print(f"STOP: {d} is not a folder. Nothing was deleted.")
        return 2
    gone, kept = [], []
    for name in sorted(os.listdir(d)):
        p = os.path.join(d, name)
        if name in OURS and os.path.isfile(p):
            os.remove(p)
            gone.append(name)
        else:
            kept.append(name)
    if not kept:
        os.rmdir(d)
    print(f"DELETED: {len(gone)} working files" + (f" and the folder {d}" if not kept else "")
          + (f"; left alone (not this skill's): {', '.join(kept)}" if kept else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
