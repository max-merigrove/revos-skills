#!/usr/bin/env python3
"""Check which vowel the voice used in a word: "led" (short e) or "leed" (long ee).

For heteronyms that differ by that vowel: lead (the metal, "led") vs lead (to guide,
"leed"); read (past, "red") vs read (now, "reed"). Measures the first two formants of
the loudest frames of each time the word is spoken: short e has F1 above ~480 Hz and F2
around 1,500 to 2,000 Hz; long ee has F1 below ~480 Hz and F2 above ~2,200 Hz (adult
voices; a deep male voice reads lower, so compare words against each other too).

  python3 scripts/check-vowel.py reels/<dir> lead e      # every "lead" should be "led"
  python3 scripts/check-vowel.py reels/<dir> read ee
Needs numpy and scipy; reads assets/vo.wav and assets/transcript.json.
"""
import json, os, subprocess, sys
import numpy as np
from scipy.signal import lfilter

dirpath, word, expect = sys.argv[1], sys.argv[2].lower(), sys.argv[3]
FS = 16000
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(dirpath, "assets/vo.wav"), "-ac", "1", "-ar", str(FS), "-f", "f32le", "-"], capture_output=True).stdout
x = np.frombuffer(raw, dtype=np.float32)
w = json.load(open(os.path.join(dirpath, "assets/transcript.json")))
w = w if isinstance(w, list) else w["words"]
spoken = {word, json.load(open(os.path.join(dirpath, "reel.json"))).get("pronounce", {}).get(word, word).lower()}


def lpc(f, order=16):
    r = np.correlate(f, f, "full")[len(f) - 1 : len(f) + order]
    a = np.zeros(order + 1)
    a[0], e = 1, r[0]
    for i in range(1, order + 1):
        k = -(r[i] + np.dot(a[1:i], r[i - 1 : 0 : -1])) / e
        a[1:i] = a[1:i] + k * a[i - 1 : 0 : -1]
        a[i] = k
        e *= 1 - k * k
    return a


def formants(seg):
    n, h = int(0.025 * FS), int(0.01 * FS)
    got, loud = [], []
    for s in range(0, len(seg) - n, h):
        f = lfilter([1, -0.63], 1, seg[s : s + n] * np.hamming(n))
        e = np.sqrt(np.mean(f**2))
        if e < 0.01:
            continue
        roots = [z for z in np.roots(lpc(f)) if np.imag(z) > 0]
        fr = sorted((np.angle(z) * FS / (2 * np.pi), -FS / np.pi * np.log(abs(z))) for z in roots)
        fr = [f_ for f_, bw in fr if f_ > 200 and bw < 500]
        if len(fr) >= 2:
            got.append(fr[:2])
            loud.append(e)
    if not got:
        return None
    got, loud = np.array(got), np.array(loud)
    return np.median(got[loud >= 0.6 * loud.max()], axis=0)


bad = 0
for i, wd in enumerate(w):
    t = "".join(c for c in wd["text"].lower() if c.isalpha())
    if t not in spoken:
        continue
    st, en = float(wd["start"]), float(wd["end"])
    f = formants(x[int((st - 0.02) * FS) : int((en + 0.08) * FS)])
    ctx = " ".join(v["text"] for v in w[max(0, i - 3) : i + 1])
    if f is None:
        print(f"  {st:6.2f}s  could not measure          ...{ctx}")
        continue
    heard = "e" if f[0] >= 480 else "ee"
    ok = heard == expect
    bad += not ok
    print(f"  {st:6.2f}s  F1 {f[0]:4.0f}  F2 {f[1]:4.0f}  {'short e' if heard == 'e' else 'long ee'}  {'ok' if ok else 'WRONG'}  ...{ctx}")
print("all as expected" if not bad else f"{bad} wrong: respell in reel.json pronounce and regenerate those parts")
sys.exit(1 if bad else 0)
