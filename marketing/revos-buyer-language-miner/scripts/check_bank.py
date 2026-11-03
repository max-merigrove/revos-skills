#!/usr/bin/env python3
"""Check a whole language bank before it is built: every quote, every count, every angle, nothing personal.

Usage:
  python3 scripts/check_bank.py --run <run folder> <bank.json>

Runs rank.py's counting and verification first, then checks what Claude wrote:
  - an ad angle, a post idea and a lead magnet topic for every ranked cluster, and none for a cluster too thin to rank;
  - every fragment in quotation marks is found word for word in what that cluster's buyers said (negations kept);
  - public copy (ad headlines, ready-to-run ads, post openers, lead magnet titles) uses the buyers' words without
    quotation marks, as the reader's own situation, and never repeats a buyer's sentence word for word (a run of eight
    words from one item, five from a closed group); verbatim quotes live in the bank, never in public copy;
  - two or three ready-to-run ads (ad_draft) on ranked clusters, each resting on facts the founder stated, no [NEED]
    inside, nothing on the founder's never-say list, headline length against the common 40-character feed limit;
  - the headline is eight words or fewer and built mostly from the buyers' words; the lead magnet title uses them;
  - the angle type fits the cluster's main tag and is not one the founder ruled out;
  - any result, speed or price promise carries [NEED: ...]; no percentage of anyone, no "customers love";
  - a competitor is named only where at least two voices mentioned it;
  - no email, phone number, handle, author name or profile link anywhere (handles are matched by one-way code);
  - the house writing rules (scripts/check_copy.py) on everything outside quotation marks, in English;
  - any count written in free text matches the scripts: "N voices", "N of M voices", "N voices have no date",
    "N items are undated", "N outside the window", in digits or words.
  --chat FILE also checks a chat reply drafted in FILE (counts, quotes, writing rules, personal data).
On 0 problems it prints AD and EVIDENCE lines: each ready-to-run ad with its character counts and the evidence
behind it (voices out of voices quoted, source types, one verbatim quote), for the first reply.
Prints PROBLEM and WARN lines; exit 1 on any PROBLEM, 2 on bad input. Standard library only. No network.
"""
import argparse
import os
import re
import signal
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ledger import stop, load_json, load_ledger, counted, norm, words, phrase_in, handle_key, voice_hash, name_candidates, EMAIL, PROFILE_URL, MENTION  # noqa: E402
from rank import compute, ALLOWED, ANGLE_TYPES  # noqa: E402
from check_copy import check_text, DASHES  # noqa: E402

QUOTED = re.compile(r'"([^"\n]{2,300})"|“([^”\n]{2,300})”|„([^“”\n]{2,300})[“”]|«\s?([^»\n]{2,300}?)\s?»')
PROMISE = re.compile(r"\d+(?:[.,]\d+)?\s*(?:%|per ?cent|prozent|x\b|times\b|days?\b|weeks?\b|hours?\b|hrs?\b|months?\b|minutes?\b|mins?\b|tage?n?\b|wochen?\b|stunden?\b|monate?n?\b|minuten\b)"
                     r"|[$€£¥₹]\s?\d|\d\s?(?:€|euro|dollars?|pounds?|aud|usd|cad|sgd|eur)\b|\b(?:S|A|C|NZ|HK|US)\$\s?\d|\bguarantee|\bgarant|\bwithin\b|\binnerhalb\b|\bin (a|one|two|three) (day|week|hour|month)s?\b"
                     r"|\bno (surprises|hidden|extra)\b|\bnever\b|\balways\b|\bnie\b|\bimmer\b|\bfaster\b|\bschneller\b|\bsave[sd]?\b|\bsparen\b|\bfixed (fee|price)\b|\bflat fee\b|\bfestpreis\b", re.I)
PHONE_LIKE = re.compile(r"(?<![\w$£€])\+?\d[\d ()-]{6,}\d(?![\w%])")
LONG_DIGITS = re.compile(r"(?<![\w.,/-])\d{9,13}(?![\w.,/-])")
STOP = {"the", "a", "an", "and", "or", "but", "to", "of", "in", "on", "for", "with", "at", "by", "is", "are", "was", "it", "i", "you", "your", "my",
        "we", "our", "they", "their", "this", "that", "be", "not", "no", "do", "does", "did", "so", "if", "as", "from", "who", "what", "when", "how",
        "der", "die", "das", "und", "oder", "ein", "eine", "zu", "mit", "für", "ist", "sind", "nicht", "ich", "du", "dein", "deine", "wir", "sie",
        "es", "im", "am", "an", "auf", "von", "wie", "was", "wenn", "dass", "den", "dem", "des"}


def quotes_in(text):
    return [next(g for g in m.groups() if g) for m in QUOTED.finditer(text or "")]


def outside_quotes(text):
    return QUOTED.sub(" ", text or "")


def content(ws):
    return [w for w in ws if w not in STOP and len(w) >= 3]


def has_run(text, pool, n=3):
    """True if text shares a run of n or more words with any string in pool."""
    tw = words(text)
    grams = {tuple(tw[i:i + n]) for i in range(len(tw) - n + 1)}
    for p in pool:
        pw = words(p)
        if grams & {tuple(pw[i:i + n]) for i in range(len(pw) - n + 1)}:
            return True
    return False


GENERIC_FIRST = {"hundeschule", "school", "studio", "salon", "garden", "gardens", "mobile", "grooming", "catering", "cleaning", "fitness",
                 "pilates", "bookkeeping", "accounting", "dental", "clinic", "kitchen", "coffee", "bakery", "agency", "digital", "global",
                 "london", "denver", "sydney", "brisbane", "berlin", "cape", "smart", "simple", "happy", "little", "north", "south", "east", "west"}
NUMW = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
        "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
        "ein": 1, "eine": 1, "zwei": 2, "drei": 3, "vier": 4, "fünf": 5, "sechs": 6, "sieben": 7, "acht": 8, "neun": 9, "zehn": 10}
NUM = r"(\d+|" + "|".join(sorted(NUMW, key=len, reverse=True)) + r")"
PEOPLE = r"(?:voices|voice|stimmen|people|personen|buyers|homeowners|customers|owners|parents|people's)"
ITEMS = r"(?:items?|phrases?|posts?|reviews?|comments?|answers?|eintr\w*|bewertungen)"
PUBLIC = ("ad_angle.headline", "post_idea.opener", "lead_magnet.title", "ad_draft.headline", "ad_draft.primary_text", "ad_draft.cta")


def num(x):
    return int(x) if x.isdigit() else NUMW[x.lower()]


def runs_from(text, pool, n):
    """Runs of n or more consecutive words shared by text and any one string in pool (longest first, with a content word)."""
    tw = words(text)
    out = []
    for p in pool:
        pw = words(p)
        pg = {tuple(pw[i:i + n]) for i in range(len(pw) - n + 1)}
        i = 0
        while i <= len(tw) - n:
            if tuple(tw[i:i + n]) in pg:
                j = i + n
                while j < len(tw) and any(tuple(tw[i:j + 1]) == tuple(pw[k:k + j + 1 - i]) for k in range(len(pw))):
                    j += 1
                run = tw[i:j]
                if content(run):
                    out.append(" ".join(run))
                i = j
            else:
                i += 1
    return sorted(set(out), key=lambda r: -len(r.split()))


PRON = {"i", "me", "my", "mine", "myself", "we", "us", "our", "ours", "you", "your", "yours", "yourself", "he", "she", "him", "her", "his",
        "hers", "they", "them", "their", "theirs", "it", "its", "i'm", "you're", "we're", "they're", "i've", "you've", "i'd", "you'd",
        "ich", "mir", "mich", "mein", "meine", "du", "dir", "dich", "dein", "deine", "wir", "uns", "unser", "ihr", "euch", "euer"}
BE = {"is", "was", "am", "are", "were", "be", "been", "ist", "war", "bin", "bist", "sind", "seid"}


def pnorm(text):
    """Words with pronouns and forms of 'be' folded, so 'nobody wants to show me a plan' and '...show you a plan' match."""
    return " ".join("~p" if w in PRON else "~b" if w in BE else w for w in words(text))


def echoes(text, pool, n, exempt="", min_content=2):
    """Runs of n or more words (pronouns folded) shared with any one buyer's text, leaving out runs the founder wrote themselves."""
    ex = pnorm(exempt)
    out = []
    for r_ in runs_from(pnorm(text), [pnorm(p) for p in pool], 2):
        real = [w for w in r_.split() if w not in ("p", "b")]
        if r_ in ex or len(real) < n or len(content(real)) < min_content:
            continue
        out.append(" ".join("..." if w in ("p", "b") else w for w in r_.split()))
    return out


NUMTOK = re.compile(r"^(?:\d+(?:[.,]\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|twelve|twenty|zwei|drei|vier|fünf|sechs)$")


def story_numbers(text, closed_pool, exempt=""):
    """A number with the word after it ('three quotes', '9 Hunden') taken from a closed-group post and not from the founder."""
    tw, ex = words(text), " ".join(words(exempt))
    grams = {" ".join(tw[i:i + 2]) for i in range(len(tw) - 1) if NUMTOK.match(tw[i])}
    hits = []
    for p in closed_pool:
        pw = words(p)
        for i in range(len(pw) - 1):
            g = " ".join(pw[i:i + 2])
            if NUMTOK.match(pw[i]) and g in grams and g not in ex:
                hits.append(g)
    return sorted(set(hits))


def count_checks(where, o, R, cid=None):
    """Counts written in free text against the scripts' numbers."""
    probs = []
    S, Q = R["stats"], R["quoted"]
    by_id = {c["id"]: c for c in R["clusters"]}
    totals = {S["voices"], Q["voices"]}
    sub = {S.get("undated_voices"), S.get("outside_voices"), Q.get("undated_voices")} | set((S.get("voices_by_type") or {}).values())
    for c in R["clusters"]:
        sub |= {c["voices"], c.get("fresh_voices"), c.get("dated_voices"), c.get("undated_voices"), c.get("objection_voices")}
    sub.discard(None)
    clv = {by_id[cid]["voices"]} if cid and cid in by_id else {c["voices"] for c in R["clusters"]}
    spans = []
    for m in re.finditer(r"\b" + NUM + r"\s+(?:of|out of|von|aus)\s+(?:the\s+|its\s+|their\s+)?" + NUM + r"\s+(?:\w+\s+){0,2}?" + PEOPLE + r"\b", o, re.I):
        n, mm = num(m.group(1)), num(m.group(2))
        spans.append(m.span())
        if mm not in totals | clv:
            probs.append(f"{where}: says {m.group(0)!r}, but no count is {mm}: voices read {S['voices']}, quoted {Q['voices']}"
                         + (f", this theme {by_id[cid]['voices']}" if cid and cid in by_id else "") + "; never count by eye")
        elif n > mm or n not in sub | totals | clv:
            probs.append(f"{where}: says {m.group(0)!r}, but {n} is not a count the scripts gave; never count by eye")
    for m in re.finditer(r"\b" + NUM + r"\s+(?:\w+\s+){0,2}?(" + PEOPLE + r"|" + ITEMS + r")?\s*(?:have no date|with no date|are undated|undated|carry no date|ohne datum)", o, re.I):
        if any(a <= m.start() < b for a, b in spans):
            continue
        noun = (m.group(2) or "").lower()
        n = num(m.group(1))
        if noun and re.fullmatch(PEOPLE, noun, re.I):
            want, what = (S.get("undated_voices"), "voices with no date")
            ok = {S.get("undated_voices"), Q.get("undated_voices")} | ({by_id[cid].get("undated_voices")} if cid and cid in by_id else set())
        else:
            want, what = (S["undated"], "undated items")
            ok = {S["undated"]}
        if n not in ok:
            probs.append(f"{where}: says {m.group(0).strip()!r}, but the scripts count {want} {what}; never count by eye")
    for m in re.finditer(r"\b" + NUM + r"\s+(?:\w+\s+){0,2}?(" + PEOPLE + r"|" + ITEMS + r")?\s*(?:\w+\s+){0,2}?(?:fall |are |were |sit )?(?:outside the window|outside the \d+|außerhalb)", o, re.I):
        if any(a <= m.start() < b for a, b in spans):
            continue
        noun = (m.group(2) or "").lower()
        n = num(m.group(1))
        want = S.get("outside_voices") if noun and re.fullmatch(PEOPLE, noun, re.I) else S["outside"]
        if n != want:
            probs.append(f"{where}: says {m.group(0).strip()!r}, but the scripts count {want}; never count by eye")
    for m in re.finditer(r"\b" + NUM + r"\s+(?:\w+\s+){0,2}?" + PEOPLE + r"\b", o, re.I):
        if any(a <= m.start() < b for a, b in spans) or re.match(r"(?:of|out of)\b", o[m.end():].strip()):
            continue
        if re.search(r"\b(?:of|out of)\s*$", o[:m.start()]):
            continue
        n = num(m.group(1))
        if not m.group(1).isdigit() and n == 1:
            continue
        allowed = totals | clv | sub
        if n not in allowed:
            probs.append(f"{where}: says {m.group(0)!r}, but the counts are {sorted(totals | clv)}; never count by eye")
    return probs


def check(L, B):
    R = compute(L, B)
    problems = list(R["problems"])
    warns = list(R["warns"])
    lang = B.get("lang", "en")
    items = {i["id"]: i for i in L["items"]}
    counted_items = [i for i in L["items"] if counted(i)]
    salt = L["salt"]
    vhashes = {v["hash"] for v in L["voices"].values() if not v.get("anon")} | {h for v in L["voices"].values() for h in v.get("alias", [])}
    pmap = R["phrases"]
    tier = R["bank_tier"]
    texts = []  # (where, text, cluster or None)

    if tier == "none":
        if any(c.get(k) for c in B.get("clusters", []) for k in ("ad_angle", "post_idea", "lead_magnet")):
            problems.append(f"only {R['quoted']['voices']} voices quoted: under the floor of 5 nothing is ranked and no angle is written; quote more of the voices read or build the collection sheet instead")
    by_id = {c["id"]: c for c in R["clusters"]}
    for c in B.get("clusters", []):
        cid = c.get("id")
        rc = by_id.get(cid, {})
        ranked = cid in R["ranked"]
        pool = [items[pmap[x]["item"]]["text"] for x in rc.get("counted_phrases", []) if x in pmap]
        closed_src = {s_["id"] for s_ in L["sources"] if s_.get("closed")}
        pool_open = [items[pmap[x]["item"]]["text"] for x in rc.get("counted_phrases", []) if x in pmap and items[pmap[x]["item"]]["source"] not in closed_src]
        blocks = {k: c.get(k) for k in ("ad_angle", "post_idea", "lead_magnet", "ad_draft")}
        if not c.get("name"):
            problems.append(f"{cid}: give the cluster a plain name")
        if c.get("means"):
            texts.append((f"{cid} means", c["means"], cid))
        if not ranked:
            if any(blocks.values()):
                problems.append(f"{cid}: has {rc.get('voices', 0)} voices ({rc.get('tier')}{', ' + rc['held_reason'] if rc.get('held_reason') else ''}); "
                                "angles, posts and lead magnet topics are written only for ranked clusters. Remove them")
            continue
        if not c.get("means"):
            problems.append(f"{cid}: add 'means', one line on what this cluster tells the founder")
        aa, pi, lm, dr = blocks["ad_angle"] or {}, blocks["post_idea"] or {}, blocks["lead_magnet"] or {}, blocks["ad_draft"] or {}
        facts = [f for f in (dr.get("facts") or []) if str(f).strip()] if isinstance(dr.get("facts", []), list) else []
        if dr:
            for f in ("headline", "primary_text", "cta"):
                if not str(dr.get(f, "")).strip():
                    problems.append(f"{cid}: ad_draft.{f} is missing; a ready-to-run ad has a headline, primary text and a call to action")
            for f in ("headline", "primary_text", "cta"):
                if "[NEED" in str(dr.get(f, "")):
                    problems.append(f"{cid}: ad_draft.{f} holds a [NEED]; a ready-to-run ad says only what the founder stated. "
                                    "Word it to what they stated and put the fact that would sharpen it in ad_draft.sharpen")
            if not str(dr.get("visual", "")).strip():
                warns.append(f"{cid}: ad_draft.visual is empty; say in a line what the image or video shows, from the founder's own photos or footage")
            hlen = len(str(dr.get("headline", "")))
            if hlen > 40:
                warns.append(f"{cid}: ad_draft.headline is {hlen} characters; feed placements commonly cut headlines past about 40")
            if not buyer_runs_ok(" ".join(str(dr.get(f, "")) for f in ("headline", "primary_text")), pool):
                problems.append(f"{cid}: the ready-to-run ad does not use this theme's words; build it from what these buyers said, unquoted")
            if not facts and any(PROMISE.search(outside_quotes(str(dr.get(f, "")))) for f in ("headline", "primary_text", "cta")):
                problems.append(f"{cid}: ad_draft makes a promise; list in ad_draft.facts the founder's own confirmed facts it rests on")
        for k, need in (("ad_angle", ["buying_reason", "type", "headline"]), ("post_idea", ["opener", "show", "proof"]),
                        ("lead_magnet", ["title", "format", "next_question"])):
            b = blocks[k] or {}
            for f in need:
                if not str(b.get(f, "")).strip():
                    problems.append(f"{cid}: {k}.{f} is missing; every ranked cluster gets an ad angle, a post idea and a lead magnet topic")
        t = aa.get("type")
        if t and t not in ANGLE_TYPES:
            problems.append(f"{cid}: angle type '{t}' is not one of {', '.join(ANGLE_TYPES)}")
        elif t:
            mix = rc.get("tag_mix", {})
            tot = sum(mix.values()) or 1
            fits = set(ALLOWED.get(rc.get("dominant_tag"), set()))
            for tg, n in mix.items():
                if n / tot >= 1 / 3 or (tg == "trigger" and n >= 1 and t == "the-moment"):
                    fits |= ALLOWED.get(tg, set())
            if t not in fits:
                problems.append(f"{cid}: a '{t}' angle does not fit this cluster's tags ({', '.join(f'{k} {v}' for k, v in mix.items())}); use one of {', '.join(sorted(fits))}")
        if t and t in (B.get("avoid_angle_types") or []):
            problems.append(f"{cid}: the founder ruled out '{t}' angles (saved learning); choose another type")
        hl = aa.get("headline", "")
        if hl:
            hw = words(outside_quotes(hl)) + [w for q in quotes_in(hl) for w in words(q)]
            if len(words(hl)) > 14:
                problems.append(f"{cid}: headline has {len(words(hl))} words; fourteen at most even in the founder's own wording")
            elif len(words(hl)) > 8:
                warns.append(f"{cid}: headline has {len(words(hl))} words; eight or fewer reads fastest, but the founder's own wording wins")
            cw = content(words(hl))
            pool_words = {w for p in pool for w in words(p)}
            if cw and sum(1 for w in cw if w in pool_words) / len(cw) < 0.5 and not quotes_in(hl):
                problems.append(f"{cid}: headline '{hl}' is mostly not the buyers' words; build it from what this cluster said")
        op = pi.get("opener", "")
        for f, v in (("post_idea.opener", op), ("means", c.get("means", "")), ("ad_angle.buying_reason", aa.get("buying_reason", ""))):
            g = re.search(r"\b(she|he|her|his|him|herself|himself)\b", outside_quotes(v), re.I) if lang == "en" else None
            if g:
                problems.append(f"{cid} {f}: '{g.group(0)}' gives a buyer a gender nobody stated; use 'they' or 'one buyer'")
        if op and not runs_from(outside_quotes(op), pool, 3):
            problems.append(f"{cid}: the post opener needs a run of three or more of the buyers' words, written as the reader's situation, without quotation marks")
        if ranked and not pool_open:
            warns.append(f"{cid}: every quote in this cluster comes from a closed group, so its headline, opener and title use your own words, not quotes")
        quote_ok = str(c.get("quote_ok") or dr.get("quote_ok") or "").strip()
        founder_facts = [str(x) for c_ in B.get("clusters", []) for x in ((c_.get("ad_draft") or {}).get("facts") or [])] + \
                        [str(x) for w_ in (B.get("with_ads") or []) for x in (w_.get("facts") or [])]
        all_counted = [i["text"] for i in counted_items]
        closed_pool = [i["text"] for i in counted_items if i["source"] in closed_src]
        for f, v in (("ad_angle.headline", aa.get("headline", "")), ("post_idea.opener", op), ("lead_magnet.title", lm.get("title", "")),
                     ("ad_draft.headline", dr.get("headline", "")), ("ad_draft.primary_text", dr.get("primary_text", "")), ("ad_draft.cta", dr.get("cta", ""))):
            for q in quotes_in(v):
                if len(words(q)) < 2 or not any(phrase_in(q, p)[0] for p in all_counted):
                    continue
                if any(phrase_in(q, p)[0] for p in closed_pool) and not any(phrase_in(q, p)[0] for p in pool_open):
                    problems.append(f"{cid} {f}: \"{q[:50]}\" comes from a closed group; public copy never quotes a closed group. "
                                    "Say it as the reader's situation, without quotation marks")
                elif not quote_ok:
                    problems.append(f"{cid} {f}: \"{q[:50]}\" quotes a buyer in public copy. Write their words as the reader's own situation, "
                                    "without quotation marks (keep the quote in the bank); only the founder's own customer, with permission, is quoted (set quote_ok)")
            plain = outside_quotes(v)
            exempt = " ".join([str(B.get("offer", "")), str(B.get("buyer", ""))] + [str(x) for x in (dr.get("facts") or [])] + founder_facts)
            long_runs = echoes(plain, all_counted, 5 if f.startswith(("ad_draft", "ad_angle")) else 6, exempt, 4)
            closed_runs = echoes(plain, closed_pool, 4, exempt) if closed_pool else []
            nums = story_numbers(plain, closed_pool, exempt) if closed_pool else []
            if long_runs:
                problems.append(f"{cid} {f}: echoes a buyer's sentence ('{long_runs[0][:70]}', {'five' if f.startswith(('ad_draft', 'ad_angle')) else 'six'} words or more in a row, pronouns aside); public copy carries "
                                "their words, not their sentences: keep their two or three most telling words and say the rest plainly")
            elif closed_runs:
                problems.append(f"{cid} {f}: echoes a closed-group member's words ('{closed_runs[0][:60]}'); say it in plain words of your own")
            elif nums:
                problems.append(f"{cid} {f}: retells a closed-group member's story ('{nums[0]}'); speak to the general situation, not their details")
            elif f.startswith("ad_draft"):
                mid = echoes(plain, all_counted, 4, exempt, 3)
                if mid:
                    warns.append(f"{cid} {f}: carries four of one buyer's words in a row ('{mid[0][:60]}'); fine as vocabulary, but cut it if it reads as their sentence")
            if f.startswith("ad_draft") and not B.get("name_competitors"):
                for comp in L.get("competitors", []):
                    first = comp.split()[0] if len(comp.split()) > 1 else ""
                    toks = [comp] + ([first] if len(first) >= 5 and norm(first) not in GENERIC_FIRST else [])
                    if any(re.search(r"(?<!\w)" + re.escape(norm(t_)) + r"(?!\w)", norm(v)) for t_ in toks):
                        problems.append(f"{cid} {f}: names {comp}; a ready-to-run ad never names a competitor unless the founder asks (set name_competitors)")
            for term in B.get("never_say") or []:
                if term and re.search(r"(?<!\w)" + re.escape(norm(term)) + r"(?!\w)", norm(v)):
                    problems.append(f"{cid} {f}: says '{term}', which the founder does not want said")
        tl = lm.get("title", "")
        if tl and not quotes_in(tl) and not has_run(tl, pool, 2 if lang == "en" else 2):
            problems.append(f"{cid}: lead magnet title '{tl}' does not use the buyers' words")
        for k, b in blocks.items():
            for f, v in (b or {}).items():
                if f in ("type",) or not isinstance(v, str):
                    continue
                texts.append((f"{cid} {k}.{f}", v, cid))
        for i, f in enumerate(facts):
            texts.append((f"{cid} ad_draft.facts[{i}]", str(f), cid))
        needs = (aa.get("need") or [])
        need_txt = " ".join(needs) if isinstance(needs, list) else str(needs)
        for k, b in blocks.items():
            for f, v in (b or {}).items():
                if not isinstance(v, str) or f in ("type", "format"):
                    continue
                o = outside_quotes(v)
                pm_ = PROMISE.search(o)
                stated = pm_ and norm(pm_.group(0)).strip() in norm(" ".join(str(f_) for c_ in B.get("clusters", []) for f_ in ((c_.get("ad_draft") or {}).get("facts") or [])))
                if pm_ and "[NEED:" not in v and "[NEED:" not in need_txt and "[NEED:" not in (pi.get("proof") or "") and not (facts and k == "ad_draft") and not stated:
                    problems.append(f"{cid} {k}.{f}: '{v[:70]}' implies a figure, speed or promise; add [NEED: what would prove it]")
        for comp in L.get("competitors", []):
            for k, b in blocks.items():
                for f, v in (b or {}).items():
                    if isinstance(v, str) and norm(comp) in norm(outside_quotes(v)):
                        n = len({i["voice"] for i in counted_items if norm(comp) in norm(i["text"])})
                        if n < 2:
                            problems.append(f"{cid} {k}.{f}: names {comp}, which only {n} voice mentioned; a claim about a competitor needs two or more")
        if rc.get("dominant_tag") in ("objection", "alternative"):
            st = c.get("stops") or {}
            if not st.get("answer") or not st.get("where"):
                problems.append(f"{cid}: mostly {rc['dominant_tag']}; add 'stops' with the answer or proof it needs and where it goes (ad, page, call)")
        if c.get("stops"):
            texts.append((f"{cid} stops.answer", c["stops"].get("answer", ""), cid))
    closed_ids = {s_["id"] for s_ in L["sources"] if s_.get("closed")}
    all_counted_t = [i["text"] for i in counted_items]
    closed_t = [i["text"] for i in counted_items if i["source"] in closed_ids]
    for n_, w_ in enumerate(B.get("with_ads") or []):
        if not isinstance(w_, dict) or not str(w_.get("line", "")).strip() or not str(w_.get("where", "")).strip():
            problems.append(f"with_ads[{n_}] needs 'line' (what to say) and 'where' (pinned comment, booking page or both)")
            continue
        v, wf = str(w_["line"]), [str(x) for x in (w_.get("facts") or [])]
        texts.append((f"with_ads[{n_}]", v, None))
        if quotes_in(v):
            problems.append(f"with_ads[{n_}]: a line that runs beside the ads carries no quotation marks; say it plainly")
        if PROMISE.search(v) and not wf:
            problems.append(f"with_ads[{n_}]: '{v[:60]}' states a figure or promise; list in facts what the founder told you it rests on")
        ex_ = " ".join(wf + [str(B.get("offer", ""))])
        if echoes(v, all_counted_t, 5, ex_, 4) or (closed_t and echoes(v, closed_t, 4, ex_)):
            problems.append(f"with_ads[{n_}]: echoes a buyer's sentence; answer the question in the founder's words")
        for term in B.get("never_say") or []:
            if term and re.search(r"(?<!\w)" + re.escape(norm(term)) + r"(?!\w)", norm(v)):
                problems.append(f"with_ads[{n_}]: says '{term}', which the founder does not want said")
    drafts = [c.get("id") for c in B.get("clusters", []) if c.get("ad_draft") and c.get("id") in R["ranked"]]
    if tier != "none":
        if not drafts:
            problems.append("no ready-to-run ad: the first reply leads with two or three ads (ad_draft) on the top ranked themes, "
                            "written on what the founder stated; see references/angles.md")
        elif len(drafts) == 1 and len(R["ranked"]) >= 2:
            warns.append("only one ready-to-run ad; write two or three so the founder can test them against each other")
        elif len(drafts) > 3:
            problems.append(f"{len(drafts)} ready-to-run ads; lead with two or three, and keep the rest as angles")
    for k in ("first_three", "decisions", "not_heard", "checks_notes"):
        v = B.get(k) or []
        if not isinstance(v, list):
            problems.append(f"'{k}' must be a list of lines")
            continue
        for i, line in enumerate(v):
            texts.append((f"{k}[{i}]", str(line), None))
    if tier != "none":
        if len(B.get("first_three") or []) != 3:
            problems.append("first_three needs exactly three things to do first")
        if not B.get("not_heard"):
            problems.append("not_heard is empty: name who and what is missing (segments, countries, stages, source types)")
        nc = B.get("next_collect") or {}
        if not nc.get("source") or not nc.get("search"):
            problems.append("next_collect needs the one source to collect next and its exact search string")
        else:
            texts.append(("next_collect", nc["source"], None))
    for v in B.get("vocabulary") or []:
        term = v.get("term", "")
        n = len({i["voice"] for i in counted_items if re.search(r"(?<!\w)" + re.escape(norm(term)) + r"(?!\w)", norm(i["text"]))})
        if n == 0:
            problems.append(f"vocabulary '{term}': no counted voice used it; vocabulary comes from what buyers wrote")
        v["_voices"] = n
    B_names = {c.get("id"): c.get("name", "") for c in B.get("clusters", [])}
    # per-text checks
    all_pool = [i["text"] for i in counted_items]
    total = R["stats"]["voices"]
    quoted_total = R["quoted"]["voices"]
    for where, t, cid in texts:
        if not t:
            continue
        pool = [items[pmap[x]["item"]]["text"] for x in by_id.get(cid, {}).get("counted_phrases", []) if x in pmap] if cid else all_pool
        for q in quotes_in(t):
            if len(words(q)) < 2:
                continue
            if not any(phrase_in(q, p)[0] for p in pool):
                if any(phrase_in(q, i["text"])[0] for i in L["items"] if not counted(i)):
                    problems.append(f"{where}: \"{q[:60]}\" comes from an item that is not counted (outside the window, excluded or a duplicate); quote a counted voice")
                    continue
                why = next((phrase_in(q, p)[1] for p in pool if norm(q).strip(" .,;:!?") in norm(p)), "is not word for word in what " + ("this cluster's buyers" if cid else "any counted buyer") + " said")
                problems.append(f"{where}: \"{q[:60]}\" {why}")
        o = outside_quotes(t)
        if DASHES.search(o):
            problems.append(f"{where}: dash in '{o[:60]}'; use a full stop, comma, colon or brackets")
        if re.search(r"\d\s?%|\bper ?cent\b|\bprozent\b|\bpercent\b", o, re.I):
            problems.append(f"{where}: a percentage; say how many voices instead ('6 of 14 voices')")
        problems.extend(count_checks(where, o, R, cid))
        rank_of = {(B_names.get(x) or ""): i for i, x in enumerate(R["ranked"], 1)}
        for m in re.finditer(r"\b(?:cluster|gruppe|grupo|groupe)\s+(\d+)\b", o, re.I):
            n = int(m.group(1))
            if n > len(R["ranked"]):
                problems.append(f"{where}: refers to {m.group(0)}, but only {len(R['ranked'])} clusters are ranked")
                continue
            sent = next((x for x in re.split(r"(?<=[.!?:;])\s+", o) if m.group(0) in x), o)
            for nm, rk in rank_of.items():
                if nm and norm(nm) in norm(sent) and rk != n:
                    problems.append(f"{where}: calls '{nm}' {m.group(0)}, but it ranks {rk}; clusters are numbered by rank in the document")
        if lang == "en":
            ps, ws_, _ = check_text(o, "en")
            for p in ps:
                if p.startswith("dash"):
                    continue
                problems.append(f"{where}: {p}")
            warns.extend(f"{where}: {w}" for w in ws_ if "three-item" not in w)
        pii = pii_hits(t, salt, vhashes)
        for h in pii:
            problems.append(f"{where}: {h}")
    # personal data anywhere in the bank file text
    for p in B.get("phrases", []):
        for h in pii_hits(p.get("text", ""), salt, vhashes):
            problems.append(f"{p.get('id')}: {h}")
    # what ships in sources/: no unsettled possible names, no long digit runs
    left = name_candidates(L, None)
    if left:
        problems.append("possible private names still in the saved sources: " + ", ".join(n for n, _ in left)
                        + ". For each private person run ledger.py redact --run <run> --text \"<name>\"; for brands, places and ordinary words run "
                        "ledger.py keep --run <run> " + " ".join(f'--text "{n}"' for n, _ in left))
    for it in L["items"]:
        if it["source"] != "P" and LONG_DIGITS.search(it["text"]):
            problems.append(f"{it['id']}: '{LONG_DIGITS.search(it['text']).group(0)}' looks like a phone number and is still in the saved text; "
                            f"run ledger.py redact --run <run> --text \"{LONG_DIGITS.search(it['text']).group(0)}\"")
    return problems, warns, R


def buyer_runs_ok(text, pool):
    """The copy carries at least one run of two or more of these buyers' words with a content word in it."""
    return bool(runs_from(outside_quotes(text), pool, 2))


def ad_lines(L, B, R):
    """AD and EVIDENCE lines for each ready-to-run ad, in rank order: what the first reply shows."""
    out = []
    by_id = {c["id"]: c for c in R["clusters"]}
    bcl = {c.get("id"): c for c in B.get("clusters", [])}
    items = {i["id"]: i for i in L["items"]}
    closed = {s_["id"] for s_ in L["sources"] if s_.get("closed")}
    n = 0
    for cid in R["ranked"]:
        dr = (bcl.get(cid) or {}).get("ad_draft")
        if not dr:
            continue
        n += 1
        rc = by_id[cid]
        hl, pt, cta = str(dr.get("headline", "")), str(dr.get("primary_text", "")), str(dr.get("cta", ""))
        out.append(f"AD {n} ({bcl[cid].get('name', cid)}): headline '{hl}' ({len(hl)} characters) | text '{pt}' ({len(pt)} characters) | button '{cta}'"
                   + (f" | show: {dr['visual']}" if dr.get("visual") else ""))
        ps = sorted([R["phrases"][x] for x in rc["counted_phrases"]], key=lambda p: (items[p["item"]]["source"] in closed, -p["intensity"], p["id"]))
        q = ps[0] if ps else None
        qtxt = (f"\"{q['text']}\" ({q['id']}, {items[q['item']]['source_type']}" + (", closed group: evidence only" if items[q['item']]['source'] in closed else "") + ")") if q else "none"
        out.append(f"EVIDENCE {n}: {rc['voices']} of {R['quoted']['voices']} voices quoted, {len(rc['source_types'])} source types ({', '.join(rc['source_types'])}), "
                   f"{rc['fresh_voices']} in the last {L.get('fresh_days') or 30} days; strongest quote {qtxt}; rests on: {'; '.join(dr.get('facts') or []) or 'the buyers words only'}"
                   + (f"; sharpen with: {dr['sharpen']}" if dr.get("sharpen") else ""))
    for k, w_ in enumerate(B.get("with_ads") or [], 1):
        if isinstance(w_, dict):
            out.append(f"WITH {k} ({w_.get('where', '')}): {w_.get('line', '')}")
    return out


def pii_hits(text, salt, vhashes):
    out = []
    if EMAIL.search(text):
        out.append("contains an email address")
    if PROFILE_URL.search(text):
        out.append("contains a profile link")
    if MENTION.search(text):
        out.append(f"contains a handle ({MENTION.search(text).group(0)})")
    m = PHONE_LIKE.search(text)
    if m and len(re.sub(r"\D", "", m.group(0))) >= 7 and re.search(r"[ -]", m.group(0)) and not re.search(r"\d{4}-\d{2}-\d{2}", m.group(0)):
        out.append("contains what looks like a phone number")
    elif LONG_DIGITS.search(text):
        out.append("contains what looks like a phone number")
    ws = re.findall(r"[\w.'’-]+", text)
    for n in (1, 2, 3):
        for i in range(len(ws) - n + 1):
            cand = handle_key(" ".join(ws[i:i + n]))
            if len(cand) >= 3 and voice_hash(salt, cand) in vhashes:
                out.append(f"contains a buyer's handle or name ('{' '.join(ws[i:i + n])}'); use the voice ID or leave it out")
    return sorted(set(out))


def main():
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("bank")
    ap.add_argument("--chat", help="a chat reply drafted in a file, checked for counts, quotes, writing rules and personal data")
    try:
        a = ap.parse_args()
    except SystemExit as e:
        if e.code not in (0, None):
            stop("the command was not understood; see the usage at the top of scripts/check_bank.py")
        raise
    L = load_ledger(a.run)
    B = load_json(a.bank, "bank")
    if not isinstance(B, dict):
        stop("bank.json must be an object; see references/bank-format.md")
    problems, warns, R = check(L, B)
    if a.chat:
        try:
            chat = open(a.chat, encoding="utf-8").read()
        except OSError:
            stop(f"cannot read {a.chat}; write the drafted reply to that file first")
        chat_body = re.sub(r"\[BUSINESS_AUDIT_URL\]", "", chat)
        problems.extend(count_checks("chat", outside_quotes(chat_body), R))
        all_pool = [i["text"] for i in L["items"] if counted(i)]
        for q in quotes_in(chat_body):
            if len(words(q)) >= 2 and not any(phrase_in(q, p)[0] for p in all_pool) and not any(phrase_in(q, i["text"])[0] for i in L["items"]):
                problems.append(f"chat: \"{q[:60]}\" is in quotation marks but no buyer said it word for word; quote exactly or drop the marks")
        if DASHES.search(outside_quotes(chat_body)):
            problems.append("chat: a dash; use a full stop, comma, colon or brackets")
        vh = {v["hash"] for v in L["voices"].values() if not v.get("anon")} | {h for v in L["voices"].values() for h in v.get("alias", [])}
        for h in pii_hits(chat_body, L["salt"], vh):
            problems.append(f"chat: {h}")
    for p in problems:
        print("PROBLEM:", p)
    for w in warns:
        print("WARN:", w)
    if not problems:
        for line in ad_lines(L, B, R):
            print(line)
    print(f"{len(problems)} problems, {len(warns)} warnings; bank {R['bank_tier']}, {R['quoted']['voices']} voices quoted of {R['stats']['voices']} read, {len(R['ranked'])} clusters ranked")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
