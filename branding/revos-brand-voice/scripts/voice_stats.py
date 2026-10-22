#!/usr/bin/env python3
"""Merigrove Brand Voice: every count the voice guide rests on.

Claude writes the voice guide. This script splits the founder's writing into
pieces, flags pieces that someone else (or an AI tool) may have written,
measures the founder's own pieces, checks drafts against the measured voice,
reads the difference between a draft and the founder's correction, and checks
the finished guide, voice prompt and cheat sheet. Nothing is counted by eye.

Subcommands
  pieces       list every piece with its words, register, author and status,
               and print the verdict: READY, ASK (authorship to confirm) or
               DECLINE (fewer than five of the founder's own pieces)
  measure      measure the counted pieces and write the profile (JSON) and the
               Measured habits block (markdown); every line ends "(measured)"
  compare      check a draft against the profile: rhythm, contractions,
               punctuation, banned phrases and performative tics
  diff         compare a draft with the founder's corrected version and list
               what the correction changed
  check-guide  check the voice guide (page one included) and the PASTE file
  pack         write the profile, the founder's measured pieces and the guide source
               into the memory file's machine section
  unpack       recover profile.json and the guide source from a memory file

Usage
  python3 scripts/voice_stats.py pieces SAMPLE... [--map M] [--json-out F]
  python3 scripts/voice_stats.py measure SAMPLE... [--map M] [--never WORD ...]
          [--signature PHRASE ...] [--phrasing PHRASE ...] --profile-out profile.json [--md-out measured.md]
          [--profile-in memory-or-profile]   (refresh: adds the pieces measured last time)
  python3 scripts/voice_stats.py compare --profile profile.json DRAFT [--register R] [--never WORD ...]
  python3 scripts/voice_stats.py diff BEFORE AFTER
  python3 scripts/voice_stats.py pack --memory M --profile profile.json --guide guide.md
  python3 scripts/voice_stats.py unpack M --out DIR
  python3 scripts/voice_stats.py check-guide GUIDE --profile profile.json
  (--profile also accepts the memory file: it reads its "## Measured profile" block)
          [--prompt <name>-PASTE-THIS-INTO-YOUR-AI.txt]

SAMPLE is a file or a folder of .md, .txt, .csv, .eml or .docx files. Paste-only
surfaces: save each pasted block to a text file first. PDFs: paste the text.

Authors map (optional JSON; every key optional)
{
  "voice_owner": "Ruth Achebe",
  "aliases": ["Ruth", "R"],
  "people": {"Priya": "va", "Northlight Studio": "agency", "Tom Achebe": "principal"},
  "min_words": 30,
  "spelling": "or-ize",          only when the founder asks for a spelling pattern: or-ize, our-ise or our-ize
  "polish": true,                only when the founder asks for their grammar to be tidied
  "files": {
    "newsletter.md": {"author": "ai", "register": "written public"},
    "emails.txt": {"register": "written one-to-one", "split": "email",
                   "pieces": {"3": {"author": "Priya"}, "5": {"exclude": "founder says a template"}}},
    "posts.csv": {"text_column": "Post", "author_column": "Author"}
  }
}
Roles: founder or principal (counted); team (reference only); agency, va,
ghostwriter, ai, customer, other (excluded). Pieces with no author are taken
as the voice owner's, except pieces the script flags for a question.
Split: rule (lines of ---), heading, email (From: lines), blank2 (two or more
blank lines), paragraph (every blank line), whole; detected per file when not set.
Spoken files follow the same map: file-level "author" or "exclude", "split", and
"pieces.<n>". A voice note with no speaker labels is the founder's, except a
paragraph that reads as a reply to them, which is split off and asked about.
Also optional: "country" (two-letter code, from what the founder says, never from
spelling: paper size, and date order and clock where their writing shows none),
"decimal" ("dot" or "comma", only after asking about a figure that reads two ways),
"clients" (names stored as initials by pack), "keep_names" (places, products and
team members pack may keep), "plausible" (figures measure may accept after a STOP).

The founder's English is measured, never assumed: spelling forms (from written pieces only; a
transcript is spelled by the phone), money and dates as written, English idioms, and any phrasing
passed with --phrasing (constructions a polish would change, kept as written). Nothing here names a
country, and no figure is converted.

Exit codes: 0 done or ready; 1 problems found; 2 usage or file error;
3 decline (below five of the founder's own pieces); 4 authorship to confirm;
5 a headline figure looks wrong (measure stops with a plain question).
Standard library only. No network.
"""

import argparse
import csv
import io
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from locale_numbers import Ambiguous, Unreadable, detect_decimal_style, locale_defaults, parse_number  # noqa: E402

# Working defaults (references/method.md section 3). Not benchmarks.
MIN_PIECES = 5
MIN_WORDS_PIECE = 30
MIN_FOUNDER_WORDS = 400
HIGH_PIECES = 8
HIGH_WORDS = 1000
SHORT_SENTENCE = 7
FRAGMENT = 3
LONG_SENTENCE = 25
RATE_MIN_WORDS = 300
RATE_MAX_TURN_SECONDS = 120
RATE_MIN_TURN_WORDS = 8
PROMPT_MAX_CHARS = 8000
SHORT_PROMPT_MAX_CHARS = 1500
CHEATSHEET_MAX_WORDS = 350

COUNTED_ROLES = {"founder", "principal"}
REFERENCE_ROLES = {"team"}
EXCLUDED_ROLES = {"agency", "va", "ghostwriter", "ai", "customer", "other"}
REGISTERS = ("written public", "written one-to-one", "formal document", "spoken")
READABLE = (".md", ".txt", ".markdown", ".csv", ".eml", ".vtt", ".srt")

DASH = "\u2014\u2013"
# Currency signs a sentence or a number may start with (dollar, pound, euro, yen, rupee, won, peso, dong, baht,
# naira, lira, shekel, hryvnia, rouble, zloty is written as letters). Escaped so no one currency is privileged.
CUR_SIGNS = "$\u00a3\u20ac\u00a5\u20b9\u20a9\u20b1\u20ab\u0e3f\u20a6\u20ba\u20aa\u20b4\u20bd"
WORD_RE = re.compile(r"[A-Za-z0-9À-ɏ]+(?:['’][A-Za-z]+|-[A-Za-z0-9À-ɏ]+)*")
META_RE = re.compile(r"^\s*(author|by|written by|from|date|sent|register|channel|subject|to|title|platform)\s*:\s*(.*)$", re.I)
RULE_RE = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,}|={3,})\s*$")
HEAD_RE = re.compile(r"^(#{1,6})\s+(.*)$")
BULLET_RE = re.compile(r"^\s*[-*•]\s+")
NUMBERED_RE = re.compile(r"^\s*\d{1,2}[.)]\s+")
# Emoji, pictographs, variation selectors (the U+FE0F in 🌧️ and 🗓️), joiners, keycaps and skin tones.
EMOJI_CLASS = "\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u2300-\u23FF\uFE0E\uFE0F\u200D\u20E3\u3030\u303D\u3297\u3299"
EMOJI_RE = re.compile("[" + EMOJI_CLASS + "]")
EMOJI_RUN_RE = re.compile("[" + EMOJI_CLASS + "]+")
HASHTAG_RE = re.compile(r"(?<![\w&])#\w*[A-Za-z]\w*")
TRAIL_TAGS_RE = re.compile(r"(?:\s*(?<![\w&])#\w*[A-Za-z]\w*)+\s*$")
LINK_RE = re.compile(r"https?://\S+|www\.\S+")
BOLD_RE = re.compile(r"\*\*[^*\n]+\*\*|__[^_\n]+__")
CAPS_RE = re.compile(r"\b[A-Z]{3,}\b")
EVIDENCE_RE = re.compile(r'^\s*>\s*"(?P<quote>.+)"\s*\[(?P<tags>[^\]]*)\]\s*$')
SPEAKER_RE = re.compile(
    r"^\s*(?:[\[(]?(?P<t1>\d{1,2}:\d{2}(?::\d{2})?)[\])]?\s*-?\s*)?(?:\*\*)?"
    r"(?P<name>[A-Z][A-Za-z.'’ ]{0,40}?)(?:\*\*)?\s*"
    r"(?:[\[(](?P<t2>\d{1,2}:\d{2}(?::\d{2})?)[\])])?\s*(?:\*\*)?:\s*(?:\*\*)?\s*(?P<text>.*)$")
ABBREVS = ["e.g.", "i.e.", "etc.", "Mr.", "Mrs.", "Ms.", "Dr.", "vs.", "approx.", "St.", "No.", "p.m.", "a.m."]
# Acronyms are never read as capitals for emphasis. Generic business and international ones only;
# any other run of capitals of four letters or fewer is already treated as an acronym by is_emphasis.
ACRONYMS = {"CEO", "CFO", "COO", "CTO", "USA", "FAQ", "PDF", "ROI", "KPI", "SOP", "CRM", "DIY", "SEO", "LLC", "LLP",
            "LTD", "PTE", "GMBH", "ASEAN", "COVID", "NASA", "UNESCO", "HIPAA", "OSHA", "GDPR", "NATO", "SAAS",
            "AI", "TV", "PR", "HR", "IT", "EU", "UN"}

STOPLIST = set("""
a about above after again against all almost also although always am among an and another any anyone anything are aren't around as at
back be became because become been before being below between both but by can can't cannot could couldn't did didn't do does doesn't
doing don't done down during each either else enough even ever every everyone everything few first for from further get gets getting
go goes going gone got had hadn't has hasn't have haven't having he he'd he'll he's her here here's hers herself him himself his how
how's however i i'd i'll i'm i've if in into is isn't it it's its itself just keep kind know last least less let let's like likely
made make makes many may maybe me might more most much must mustn't my myself need needs never new next no nobody none nor not nothing
now of off often oh ok okay on once one only or other others otherwise our ours ourselves out over own per perhaps please put quite
rather re really right said same say says see seem seems several shall shan't she she'd she'll she's should shouldn't since so some
someone something sometimes soon still such sure take than that that's the their theirs them themselves then there there's these they
they'd they'll they're they've thing things think this those though through thus till to today too two under until up upon us use used
using very via want wants was wasn't way we we'd we'll we're we've well were weren't what what's when when's where where's whether which
while who who's whom whose why why's will with within without won't would wouldn't yes yet you you'd you'll you're you've your yours
yourself yourselves year years week weeks day days time times lot lots actually already bit come comes came look looks looked tell told
ask asked every went yeah hi hello thanks thank dear best regards cheers got going gonna
""".split())

FIRST_SING = {"i", "me", "my", "mine", "myself", "i'm", "i've", "i'd", "i'll"}
FIRST_PLUR = {"we", "us", "our", "ours", "ourselves", "we're", "we've", "we'd", "we'll"}
SECOND = {"you", "your", "yours", "yourself", "yourselves", "you're", "you've", "you'd", "you'll"}
S_CONTRACT = {"it's", "that's", "there's", "here's", "what's", "who's", "where's", "he's", "she's", "let's", "how's"}
EXPANDED_RE = re.compile(
    r"\b(do not|does not|did not|is not|are not|was not|were not|have not|has not|had not|will not|would not|should not|"
    r"could not|cannot|must not|i am|we are|you are|they are|it is|that is|there is|i have|we have|you have|"
    r"they have|i will|we will|you will|they will|i would|we would|you would|let us|what is)\b", re.I)
GREETING_RE = re.compile(r"^(hiya|heya|hey there|hi there|hi|hello|hey|dear|morning all|afternoon all|evening all|good morning|good afternoon|morning|afternoon|evening|all)\b(?:[^.?!]|(?<=Mr)\.|(?<=Mrs)\.|(?<=Ms)\.|(?<=Dr)\.|(?<=Mx)\.){0,30}[,!]?\s*$", re.I)
SIGNOFF_RE = re.compile(r"^(best|thanks|thank you|many thanks|cheers|regards|kind regards|best regards|warm regards|all the best|"
                        r"speak soon|talk soon|speak then|see you|yours|ta|x+)\b[ ,.!]*", re.I)
LABEL_RE = re.compile(r"^(?:(?:my |an? |the |old |another |last )?(?:linkedin|instagram|insta|facebook|x|twitter|tiktok|email|e-mail|newsletter|voice ?note|voice memo|transcript|"
                      r"whatsapp|sms|text message|slack|wechat|telegram|viber|imessage|"
                      r"blog|post|caption|dm|message|reply|proposal|letter|website|article)\b[^.?!]{0,60}:?|[^.?!]{0,40}\b(?:post|email|newsletter|caption)s?\s*[,(:]"
                      r"[^.?!]{0,50}:?)$", re.I)
VOICE_LABEL_RE = re.compile(r"voice ?note|transcri(bed|pt)|recorded on|dictat", re.I)
LABEL_NOTE_RE = re.compile(r"agency|freelanc|va\b|assistant|chatgpt|ai\b|wrote (it|this)|did this|ghost", re.I)
CONTRAST_RE = re.compile(
    r"\b(?:(?:it'?s|this is|that'?s|we'?re|i'?m)\s+not\s+(?:just\s+|about\s+)?[^.?!,;]{1,40}[,;.]\s*(?:it'?s|it is|this is|that'?s|we'?re|i'?m|but)\b"
    r"|(?:isn'?t|is not|aren'?t|are not|wasn'?t)\s+(?:just\s+|about\s+)?[^.?!,;]{1,40}[,;.]\s*(?:it'?s|it is|this is|that'?s|they'?re)\b)", re.I)

# Stock phrases readers now read as machine-written or as category filler.
# Each entry: (phrase regex, label). Used for the AI-drafted flag, the absence list,
# the compare gate and the guide check. references/banned-patterns.md explains each.
STOCK_PHRASES = [
    (r"in today'?s (fast[- ]paced|digital|ever[- ]changing|competitive)", "in today's fast-paced"),
    (r"\bdelve\b|\bdelving\b", "delve"),
    (r"\btapestry\b", "tapestry"),
    (r"\btestament to\b", "a testament to"),
    (r"\bnavigat(e|ing) the (complex|ever|world|landscape)", "navigate the landscape"),
    (r"\b(digital|business|evolving|competitive) landscape\b", "the landscape"),
    (r"\bgame[- ]chang(er|ing)\b", "game-changer"),
    (r"\bunlock(s|ing)?\b", "unlock"),
    (r"\belevat(e|es|ed|ing)\b", "elevate"),
    (r"\bseamless(ly)?\b", "seamless"),
    (r"\bleverag(e|es|ed|ing)\b", "leverage"),
    (r"\brobust\b", "robust"),
    (r"\bempower(s|ed|ing|ment)?\b", "empower"),
    (r"\bharness(es|ed|ing)?\b", "harness"),
    (r"\bembark(s|ed|ing)?\b", "embark"),
    (r"\bjourney\b", "journey"),
    (r"\bhere'?s the thing\b", "here's the thing"),
    (r"\blet that sink in\b", "let that sink in"),
    (r"\bexcited to (announce|share)\b", "excited to announce"),
    (r"\bthrilled to\b", "thrilled to"),
    (r"\bi hope this (email )?finds you well\b", "hope this finds you well"),
    (r"\breach(ing)? out\b", "reach out"),
    (r"\bcircle back\b", "circle back"),
    (r"\btouch base\b", "touch base"),
    (r"\bjust (wanted to|following up|checking in)\b", "just following up"),
    (r"\bdon'?t hesitate to\b", "do not hesitate to"),
    (r"\bin conclusion\b", "in conclusion"),
    (r"\bat the end of the day\b", "at the end of the day"),
    (r"\bit'?s worth noting\b", "it is worth noting"),
    (r"\bwhether you'?re a\b", "whether you're a"),
    (r"\bto be honest\b|\bif i'?m (being )?honest\b|\blet'?s be real\b|\bi mean,|\bhonestly\b", "announced honesty"),
    (r"\bthe secret sauce\b", "secret sauce"),
    (r"\bnext level\b", "next level"),
    (r"\bdive (deep|into)\b|\bdeep dive\b", "deep dive"),
    (r"\broot cause\b", "root cause"),
    (r"\bwe would love to\b|\bwe'?d love to\b", "we would love to"),
    (r"\bbuilt around you\b|\btailored to you\b|\btailored (approach|programmes?|plans?|solutions?)\b", "built around you"),
    (r"\bwhether it is\b|\bwhether it'?s\b", "whether it is"),
    (r"\bmove with confidence\b|\bwith confidence\b", "with confidence"),
    (r"\b(here|on hand) to help\b", "here to help"),
    (r"\bget (you )?back on track\b", "get back on track"),
    (r"\bpersonali[sz]ed (approach|plan|care|service|programme|treatment|experience)\b", "personalised approach"),
    (r"\b(take|taking) the first step\b|\bfirst step towards\b", "take the first step"),
    (r"\bevery step of the way\b", "every step of the way"),
    (r"\bwe believe\b", "we believe"),
    (r"\bhold(s|ing)? you back\b", "hold you back"),
    (r"\b(expert|dedicated|friendly|experienced) team\b", "our expert team"),
    (r"\bstate[- ]of[- ]the[- ]art\b", "state of the art"),
    (r"\brest assured\b", "rest assured"),
    (r"\btrusted partner\b", "trusted partner"),
    (r"\bcommitted to (providing|delivering|helping)\b", "committed to providing"),
    (r"\bfull potential\b", "full potential"),
    (r"\bpain[- ]free (future|life)\b|\bstronger than ever\b", "stronger than ever"),
    (r"\blook no further\b", "look no further"),
    (r"\bwhat truly matters\b|\bwhat matters most\b", "what truly matters"),
]
STOCK_RE = [(re.compile(p, re.I), lab) for p, lab in STOCK_PHRASES]

# Words the guide's own prose avoids (references/banned-patterns.md). A founder who
# uses one keeps it only by choice, recorded in the guide.
BANNED_VOCAB = ["unlock", "elevate", "leverage", "seamless", "robust", "game-changer", "delve", "synergy", "holistic",
                "empower", "transformative", "world-class", "cutting-edge", "best-in-class", "journey", "passionate",
                "innovative", "authentic", "genuinely", "straightforward"]

AI_TELL_THRESHOLD = 3
DATE = date.today().isoformat()

NK = "[not known]"



# ---------------------------------------------------------------- the founder's English
# Spelling is measured, never assumed. Each pair is (form A, form B, family). Neither form is "right":
# American, British, Australian, Indian, Singaporean, Canadian, Irish and Oxford writers mix them in
# different ways, and many founders mix them in the same post. The guide copies the founder's own forms
# and never names a country from them. Pairs where both forms are standard in one variety (judgement,
# program, licence and license, practise, tyre, cheque, metre and meter) are left out on purpose.
_ISE_STEMS = ["organ", "real", "recogn", "priorit", "special", "optim", "apolog", "custom", "summar", "emphas",
              "minim", "maxim", "final", "personal", "standard", "categor", "util", "critic", "memor", "author",
              "visual", "modern", "central", "normal", "capital", "character", "digit", "energ", "familiar",
              "global", "harmon", "hospital", "ideal", "item", "local", "mobil", "monet", "neutral", "popular",
              "rational", "stabil", "steril", "subsid", "symbol", "synchron", "theor", "urban", "sympath",
              "jeopard", "fertil", "commercial", "democrat", "industrial", "internal", "legitim", "revital",
              "scrutin", "stigmat", "trivial", "vandal", "vapor"]
_ISE_SUFFIXES = [("ise", "ize"), ("ises", "izes"), ("ised", "ized"), ("ising", "izing"), ("isation", "ization"),
                 ("isations", "izations"), ("iser", "izer"), ("isers", "izers")]
_PAIRS = []
for _st in _ISE_STEMS:
    for _a, _b in _ISE_SUFFIXES:
        _PAIRS.append((_st + _a, _st + _b, "-ise/-ize", _st + "ise"))
for _st in ("anal", "paral", "catal", "dial"):
    for _a, _b in (("yse", "yze"), ("ysed", "yzed"), ("ysing", "yzing"), ("yses", "yzes"), ("yser", "yzer")):
        _PAIRS.append((_st + _a, _st + _b, "-yse/-yze", _st + "yse"))
_OUR = {"colour": ["", "s", "ed", "ing", "ful", "less", "way", "ways"], "favour": ["", "s", "ed", "ing", "ite", "ites", "able", "ably"],
        "behaviour": ["", "s", "al", "ally"], "honour": ["", "s", "ed", "ing", "able"], "labour": ["", "s", "ed", "ing", "er", "ers"],
        "neighbour": ["", "s", "hood", "hoods", "ing", "ly"], "flavour": ["", "s", "ed", "ing", "ful"], "humour": ["", "ed"],
        "rumour": ["", "s", "ed"], "harbour": ["", "s", "ed"], "endeavour": ["", "s", "ed", "ing"], "odour": ["", "s", "less"],
        "vapour": ["", "s"], "armour": ["", "ed"], "rigour": [""], "saviour": [""], "parlour": [""], "valour": [""],
        "candour": [""], "clamour": [""], "splendour": [""], "savour": ["", "s", "ed", "y", "ing"], "tumour": ["", "s"]}
for _st, _sfx in _OUR.items():
    for _x in _sfx:
        _PAIRS.append((_st + _x, _st[:-2] + "r" + _x, "-our/-or", _st))
_RE = ["centre", "centres", "centred", "theatre", "theatres", "fibre", "fibres", "litre", "litres", "calibre",
       "sombre", "spectre", "lustre", "meagre", "sabre", "sceptre", "kilometre", "kilometres", "centimetre",
       "centimetres", "millimetre", "millimetres"]
for _w in _RE:
    _b = re.sub(r"re(s|d)?$", lambda m: "er" + (m.group(1) or ""), _w)
    _PAIRS.append((_w, _b, "-re/-er", re.sub(r"(s|d)$", "", _w)))
_LL = [("travelled", "traveled"), ("travelling", "traveling"), ("traveller", "traveler"), ("travellers", "travelers"),
       ("cancelled", "canceled"), ("cancelling", "canceling"), ("labelled", "labeled"), ("labelling", "labeling"),
       ("modelled", "modeled"), ("modelling", "modeling"), ("signalled", "signaled"), ("fuelled", "fueled"),
       ("fuelling", "fueling"), ("levelled", "leveled"), ("counselling", "counseling"), ("counsellor", "counselor"),
       ("jewellery", "jewelry"), ("marvellous", "marvelous"), ("woollen", "woolen"), ("totalled", "totaled"),
       ("channelled", "channeled"), ("enrolment", "enrollment"), ("enrol", "enroll"), ("enrols", "enrolls"),
       ("fulfil", "fulfill"), ("fulfils", "fulfills"), ("fulfilment", "fulfillment"), ("skilful", "skillful"),
       ("wilful", "willful"), ("instalment", "installment"), ("instalments", "installments"), ("distil", "distill")]
for _a, _b in _LL:
    _h = re.sub(r"(?<=l)l(ed|ing|er|ers|or)$", "", _a)
    _PAIRS.append((_a, _b, "doubled l", re.sub(r"(ments|ment|s)$", "", _h) if _h.endswith(("ment", "ments", "ls")) else _h))
for _a, _b, _f in [("defence", "defense", "-ence/-ense"), ("defences", "defenses", "-ence/-ense"),
                   ("offence", "offense", "-ence/-ense"), ("offences", "offenses", "-ence/-ense"),
                   ("pretence", "pretense", "-ence/-ense"),
                   ("catalogue", "catalog", "-ogue/-og"), ("catalogues", "catalogs", "-ogue/-og"),
                   ("analogue", "analog", "-ogue/-og"),
                   ("paediatric", "pediatric", "ae, oe/e"), ("paediatrics", "pediatrics", "ae, oe/e"),
                   ("paediatrician", "pediatrician", "ae, oe/e"), ("orthopaedic", "orthopedic", "ae, oe/e"),
                   ("orthopaedics", "orthopedics", "ae, oe/e"), ("anaesthetic", "anesthetic", "ae, oe/e"),
                   ("anaesthesia", "anesthesia", "ae, oe/e"), ("encyclopaedia", "encyclopedia", "ae, oe/e"),
                   ("oestrogen", "estrogen", "ae, oe/e"), ("foetus", "fetus", "ae, oe/e"),
                   ("diarrhoea", "diarrhea", "ae, oe/e"), ("manoeuvre", "maneuver", "ae, oe/e"),
                   ("haemorrhage", "hemorrhage", "ae, oe/e"), ("leukaemia", "leukemia", "ae, oe/e"),
                   ("grey", "gray", "other"), ("greys", "grays", "other"), ("aluminium", "aluminum", "other"),
                   ("plough", "plow", "other"), ("pyjamas", "pajamas", "other"), ("mould", "mold", "other"),
                   ("mouldy", "moldy", "other"), ("moustache", "mustache", "other"), ("sceptical", "skeptical", "other"),
                   ("sceptic", "skeptic", "other"), ("artefact", "artifact", "other"), ("artefacts", "artifacts", "other"),
                   ("cosy", "cozy", "other"), ("sulphur", "sulfur", "other"), ("aeroplane", "airplane", "other"),
                   ("ageing", "aging", "other"), ("mum", "mom", "other"), ("mums", "moms", "other"),
                   ("smoulder", "smolder", "other"), ("kerbside", "curbside", "other")]:
    _PAIRS.append((_a, _b, _f, re.sub(r"(s|es)$", "", _a) if _f == "other" else _a))
# word -> (head, variant "a" or "b", family). A is the first form of each pair, B the second.
SPELL = {}
for _a, _b, _f, _h in _PAIRS:
    SPELL.setdefault(_a, (_h, "a", _f))
    SPELL.setdefault(_b, (_h, "b", _f))
FAMILY_LABELS = {"-ise/-ize": ("-ise", "-ize"), "-yse/-yze": ("-yse", "-yze"), "-our/-or": ("-our", "-or"),
                 "-re/-er": ("-re", "-er"), "doubled l": ("doubled l", "single l"), "-ence/-ense": ("-ence", "-ense"),
                 "-ogue/-og": ("-ogue", "-og"), "ae, oe/e": ("ae or oe", "e"), "other": ("other pairs as grey, mum", "other pairs as gray, mom")}
# A spelling the founder states ("use American spelling for my US clients") is recorded as a system and
# overrides the measured forms. Named by pattern, never by country.
SPELLING_SYSTEMS = {"or-ize": {"-ise/-ize": "b", "-yse/-yze": "b", "-our/-or": "b", "-re/-er": "b", "doubled l": "b",
                               "-ence/-ense": "b", "-ogue/-og": "b", "ae, oe/e": "b", "other": "b"},
                    "our-ise": {"-ise/-ize": "a", "-yse/-yze": "a", "-our/-or": "a", "-re/-er": "a", "doubled l": "a",
                                "-ence/-ense": "a", "-ogue/-og": "a", "ae, oe/e": "a", "other": "a"},
                    "our-ize": {"-ise/-ize": "b", "-yse/-yze": "a", "-our/-or": "a", "-re/-er": "a", "doubled l": "a",
                                "-ence/-ense": "a", "-ogue/-og": "a", "ae, oe/e": "a", "other": "a"}}
SPELL_WORD_RE = re.compile(r"[A-Za-z]+")


def spelling_hits(text):
    """Every word in text with two common spellings, as (word as written, lower form, head, variant, family)."""
    out = []
    for w in SPELL_WORD_RE.findall(text or ""):
        low = w.lower()
        if low in SPELL:
            h, v, f = SPELL[low]
            out.append((w, low, h, v, f))
    return out


def spelling_profile(pieces):
    forms, heads, fams = Counter(), defaultdict(set), defaultdict(Counter)
    for p in pieces:
        for w, low, h, v, f in spelling_hits(p["text"]):
            forms[low] += 1
            heads[h].add(v)
            fams[f][v] += 1
    return {"forms": dict(forms), "heads": {h: sorted(v) for h, v in heads.items()},
            "families": {f: {"a": c.get("a", 0), "b": c.get("b", 0)} for f, c in fams.items()}}


def spelling_line(sp):
    if not sp["forms"]:
        return (f"Spelling: none of the {len(SPELL)} words with two common spellings appear in your pieces; "
                f"no spelling is assumed (measured)")
    forms = "; ".join(f"{w} ({c})" for w, c in sorted(sp["forms"].items(), key=lambda t: (-t[1], t[0]))[:12])
    pats = []
    mixed = []
    for f, c in sorted(sp["families"].items()):
        la, lb = FAMILY_LABELS[f]
        pats.append(f"{la} {c['a']}, {lb} {c['b']}")
        if c["a"] and c["b"]:
            mixed.append(f)
    both = []
    for h, v in sorted(sp["heads"].items()):
        if len(v) == 2:
            fs = sorted((w for w in sp["forms"] if SPELL[w][0] == h), key=lambda w: SPELL[w][1])
            both.append(" and ".join(fs))
    tail = ""
    if mixed:
        tail = "; both spellings used in: " + ", ".join(mixed) + (f" (same word both ways: {'; '.join(both)})" if both else "")
    return f"Spelling, your forms as written: {forms}; patterns: {'; '.join(pats)}{tail} (measured)"


def spelling_drift(text, sp, system=None):
    """(problems, warnings) for a draft's spellings against the founder's measured or stated forms."""
    probs, warns, seen = [], [], set()
    for w, low, h, v, f in spelling_hits(text):
        if low in seen:
            continue
        seen.add(low)
        if system:
            want = SPELLING_SYSTEMS.get(system, {}).get(f)
            if want and v != want:
                probs.append(f"'{w}': you asked for the {system} spelling pattern")
            continue
        used = set((sp or {}).get("heads", {}).get(h, []))
        if used and v not in used:
            theirs = [x for x, c in (sp or {}).get("forms", {}).items() if SPELL[x][0] == h]
            probs.append(f"'{w}': you write {', '.join(repr(x) for x in theirs)}")
            continue
        fam = (sp or {}).get("families", {}).get(f)
        if not used and fam and fam.get("a" if v == "b" else "b", 0) >= 2 and not fam.get(v, 0):
            la, lb = FAMILY_LABELS[f]
            warns.append(f"'{w}': your pieces use {la if v == 'b' else lb} forms for this pattern")
    return probs, warns


# Money and dates are copied as the founder writes them. Nothing is converted, and no currency or date
# order is assumed when the pieces hold none.
CUR_CODES = ("USD|GBP|EUR|SGD|AUD|NZD|CAD|HKD|INR|MYR|PHP|IDR|JPY|CNY|RMB|AED|SAR|ZAR|PLN|CHF|SEK|NOK|DKK|"
             "BRL|MXN|THB|VND|KRW|NGN|KES|TWD|ILS|TRY|CZK|HUF")
MONEY_RES = [
    re.compile(r"(?<![A-Za-z])((?:US|S|A|NZ|HK|C|NT|R)\$|[" + CUR_SIGNS + r"])\s?\d"),
    re.compile(r"\b(" + CUR_CODES + r"|Rs\.?|RM|Rp)\s?\d"),
    re.compile(r"\d(?:[\d,.]*\d)?\s?(k\s?)?(" + CUR_CODES + r"|zł|zl|Kč|kr|dollars|euros|pounds|rupees|ringgit|pesos|rand|francs|yen)\b"),
    re.compile(r"\d(?:[\d,.\u00a0\u202f ]*\d)?\s?([" + CUR_SIGNS + r"])(?!\s?\d)"),   # 1.200,50 € and 450 € (sign after)
]
MONTHS = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
DATE_DAY_FIRST_WORD = re.compile(r"\b\d{1,2}(?:st|nd|rd|th)?(?: of)? " + MONTHS + r"\b")
DATE_MONTH_FIRST_WORD = re.compile(r"\b" + MONTHS + r"\.? \d{1,2}(?:st|nd|rd|th)?\b(?!:)")
DATE_NUM = re.compile(r"(?<![\d/.])(\d{1,2})([/.])(\d{1,2})(?:\2(\d{2}|\d{4}))?(?![\d/])")
DATE_ISO = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


# Indian and South Asian magnitude words are money as written ("18 lakh", "2.4L", "3 crore"); kept as the founder writes them.
MONEY_UNIT_RES = [re.compile(r"(?<![\w.,])\d+(?:[.,]\d+)?\s?(lakhs?|lacs?|crores?|cr)\b", re.I),
                  re.compile(r"(?<![\w.,])\d+(?:[.,]\d+)?(L)\b")]
TIME_12_RE = re.compile(r"(?<![\d:.])(\d{1,2})(?:[:.](\d{2}))?\s?(am|pm|a\.m\.|p\.m\.)(?![a-z])", re.I)
TIME_24_RE = re.compile(r"(?<![\d:.$])(1[3-9]|2[0-3]|00)(?::|h)([0-5]\d)(?![\d])")


def unit_key(u):
    low = u.lower()
    return "L" if u == "L" else re.sub(r"s$", "", low)


def money_dates(text, ex=None):
    """Currency as written (signs, codes, words and lakh or crore) and the order of any date that can be read.
    ex, if given, collects the first real example of each date order and clock as written."""
    t = text or ""
    cur = Counter()
    for rx in MONEY_RES:
        for m in rx.finditer(t):
            g = [x for x in m.groups() if x and x.strip() and x.strip() != "k"]
            if g:
                cur[g[-1].strip()] += 1
    for rx in MONEY_UNIT_RES:
        for m in rx.finditer(t):
            cur[unit_key(m.group(1))] += 1
    order = Counter()
    ex = ex if ex is not None else {}

    def hit(label, sample):
        order[label] += 1
        ex.setdefault(label, sample)
    for m in DATE_DAY_FIRST_WORD.finditer(t):
        hit("day first", m.group(0))
    for m in DATE_MONTH_FIRST_WORD.finditer(t):
        hit("month first", m.group(0))
    for m in DATE_ISO.finditer(t):
        hit("year first", m.group(0))
    for m in DATE_NUM.finditer(t):
        a_, sep, b_, y = int(m.group(1)), m.group(2), int(m.group(3)), m.group(4)
        if sep == "." and not y:
            continue  # 7.40 or 2.5: a time or a decimal, not a date
        if f"{a_}/{b_}" in ("24/7", "50/50") or not (1 <= a_ <= 31 and 1 <= b_ <= 31):
            continue
        if a_ > 12 and b_ <= 12:
            hit("day first", m.group(0))
        elif b_ > 12 and a_ <= 12:
            hit("month first", m.group(0))
    return cur, order


def clock_of(text, ex=None):
    """12-hour times with am or pm, and 24-hour times past noon; '4:45' alone cannot be read either way."""
    c = Counter()
    ex = ex if ex is not None else {}
    for m in TIME_12_RE.finditer(text or ""):
        if 1 <= int(m.group(1)) <= 12:
            c["12-hour"] += 1
            ex.setdefault("12-hour", m.group(0))
    for m in TIME_24_RE.finditer(text or ""):
        c["24-hour"] += 1
        ex.setdefault("24-hour", m.group(0))
    return c


def date_orders(order):
    return {k.split(" (")[0] for k in order}


def money_dates_line(cur, order, ex=None, clock=None, country=None):
    ex = ex or {}
    c = "; ".join(f"\"{k}\" ({v})" for k, v in cur.most_common(6)) or "none in your pieces"
    d = "; ".join(f"{k} (e.g. {ex[k]}) {v}" if k in ex else f"{k} {v}" for k, v in order.most_common()) or "none whose order can be read"
    tl = ""
    if clock:
        tl = "; times " + "; ".join(f"{k} (e.g. {ex[k]}) {v}" if k in ex else f"{k} {v}" for k, v in clock.most_common())
    loc = ""
    if country:
        ld = locale_defaults(country)
        gaps = []
        if not order:
            gaps.append("date order " + {"DMY": "day first", "MDY": "month first", "YMD": "year first"}[ld["date_order"]])
        if not clock:
            gaps.append(("12-hour" if ld["clock"] == "12h" else "24-hour") + " clock")
        if gaps:
            loc = f"; from your country ({country.upper()}), not your writing: " + ", ".join(gaps)
    return f"Money and dates as you write them: currency {c}; dates {d}{tl}{loc} (measured)"


# Numbers are written back in the founder's own style: thousands separator, decimal mark, and units such as k or lakh.
_GROUPED = r"\d{1,3}(?:(?:,\d{2})+,\d{3}|(?:[,.'\u2019\u00a0\u202f]\d{3})+)(?:[.,]\d{1,2})?"
NUM_TOKEN_RES = [
    re.compile(r"(?<![\w/:.,-])" + _GROUPED + r"(?![\w/:]|[.,]\d)"),                               # 14,500  1.200,50  18,00,000
    re.compile(r"(?<![\w/:.,-])\d+[.,]\d{1,2}(?=\s?(?:%|lakhs?|lacs?|crores?|cr\b|k\b|m\b|bn\b|million|L\b))", re.I),  # 2.4 lakh, 1,5%
    re.compile(r"(?:(?<![A-Za-z])(?:US|S|A|NZ|HK|C|R)?\$|[" + CUR_SIGNS[1:] + r"]|\b(?:" + CUR_CODES + r")\s?)\s?(\d{1,3}(?:[ \u00a0\u202f]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)(?!\d|[.,]\d)"),
    re.compile(r"(?<![\w/:.,-])(\d{1,3}(?:[ \u00a0\u202f]\d{3})+(?:[.,]\d{1,2})?)(?=\s?(?:[" + CUR_SIGNS + r"]|zł|zl|Kč|kr|" + CUR_CODES + r")\b|\s?[" + CUR_SIGNS + r"])"),
]
UNIT_AFTER_RE = re.compile(r"(?:\$|[" + CUR_SIGNS[1:] + r"]|\b(?:" + CUR_CODES + r")\s?)\s?\d+(?:[.,]\d+)?\s?(k|m|bn|million|billion)\b", re.I)
GROUP_LABELS = {"comma": "thousands with a comma", "dot": "thousands with a full stop", "space": "thousands with a space",
                "apostrophe": "thousands with an apostrophe", "indian": "lakh grouping", "none": "no thousands separator"}


def number_tokens(text):
    out = []
    for rx in NUM_TOKEN_RES:
        for m in rx.finditer(text or ""):
            tok = (m.group(1) if m.groups() and m.group(1) else m.group(0)).strip()
            if tok and tok not in out:
                out.append(tok)
    return out


def group_kind(tok):
    t = tok.replace("\u2019", "'")
    if re.fullmatch(r"\d{1,2}(?:,\d{2})+,\d{3}(?:\.\d+)?", t):
        return "indian"
    m = re.fullmatch(r"\d{1,3}([,.' \u00a0\u202f])\d{3}(?:\1\d{3})*(?:[.,]\d{1,2})?", t)
    if m:
        sep = m.group(1)
        if sep in ",." and re.fullmatch(r"\d{1,3}[,.]\d{3}", t):
            return None  # 1,340 or 12.500 alone: grouping read only with the decimal style below
        return {",": "comma", ".": "dot", "'": "apostrophe"}.get(sep, "space")
    if re.fullmatch(r"\d{4,}(?:[.,]\d{1,2})?", t):
        return "none"
    return None


def number_style(texts, decimal=None):
    """The founder's number style, read with locale_numbers: decimal mark, thousands separator, units.
    Returns a dict; 'ambiguous' lists figures that read two ways (12.500 with no other clue)."""
    toks, units = [], Counter()
    for t in texts:
        toks.extend(number_tokens(t))
        for m in UNIT_AFTER_RE.finditer(t or ""):
            units[m.group(1).lower()] += 1
        for rx in MONEY_UNIT_RES:
            for m in rx.finditer(t or ""):
                units[unit_key(m.group(1))] += 1
    style = decimal or detect_decimal_style(toks)
    groups, ex, amb = Counter(), {}, []
    for tok in toks:
        try:
            parse_number(tok, style)
        except Ambiguous:
            amb.append(tok)
            continue
        except Unreadable:
            continue
        k = group_kind(tok)
        if k is None and re.fullmatch(r"\d{1,3}[,.]\d{3}", tok):
            k = ("comma" if "," in tok else "dot") if style in (None, "dot") and "," in tok or style == "comma" and "." in tok else None
        if k:
            groups[k] += 1
            ex.setdefault(k, tok)
    dec_ex = next((tk for tk in toks if re.search(r"[.,]\d{1,2}$", tk) and not re.fullmatch(r"\d{1,3}[,.]\d{3}", tk)), None)
    return {"decimal": style, "decimal_example": dec_ex, "grouping": dict(groups), "examples": ex, "units": dict(units), "ambiguous": amb}


def numbers_line(ns):
    parts = []
    for k, v in sorted(ns["grouping"].items(), key=lambda kv: -kv[1]):
        parts.append(f"{GROUP_LABELS[k]} (e.g. {ns['examples'][k]}) {v}")
    if ns.get("decimal"):
        parts.append(f"decimals with a {'full stop' if ns['decimal'] == 'dot' else 'comma'}" +
                     (f" (e.g. {ns['decimal_example']})" if ns.get("decimal_example") else ""))
    if ns["units"]:
        parts.append("amounts in " + ", ".join(f"{u} ({n})" for u, n in sorted(ns["units"].items(), key=lambda kv: -kv[1])))
    if ns.get("ambiguous"):
        parts.append("not readable one way: " + ", ".join(ns["ambiguous"][:3]))
    return "Numbers as you write them: " + ("; ".join(parts) or "no amounts with thousands or decimals") + " (measured)"


# English idioms. A founder who uses none (often, but not only, a founder writing in a second language)
# reads wrong when a draft adds them. Used for the drift check and the authorship style check.
IDIOMS = [
    "hit the ground running", "low-hanging fruit", "low hanging fruit", "move the needle", "ball is in your court",
    "on the same page", "think outside the box", "no-brainer", "bang for your buck", "back to the drawing board",
    "go the extra mile", "raise the bar", "hit it out of the park", "win-win", "perfect storm", "elephant in the room",
    "cut corners", "boil the ocean", "drop the ball", "in a nutshell", "the bottom line", "piece of cake",
    "kill two birds", "under the hood", "double-edged sword", "tip of the iceberg", "food for thought",
    "rule of thumb", "ballpark", "up to speed", "the whole nine yards", "from the get-go", "zero in on",
    "hop on a call", "jump on a call", "keep you in the loop", "loop you in", "pick your brain", "get the ball rolling",
    "on the radar", "bring to the table", "icing on the cake", "nail down", "go-to", "level up", "a cut above",
    "second to none", "hands down", "over the moon", "best of both worlds", "worth its weight in gold",
    "take it to the next level", "speaks for itself", "the real deal", "labour of love", "labor of love",
    "under one roof", "peace of mind", "made with love", "heart and soul", "good things take time",
    "worth the wait", "stand the test of time", "built to last", "no exception",
]
IDIOM_RES = [(i, re.compile(r"(?<![\w-])" + re.escape(i) + r"(?![\w-])", re.I)) for i in IDIOMS]


def idioms_in(text):
    t = norm_quotes(text or "")
    return sorted({i for i, rx in IDIOM_RES if rx.search(t)})

# ---------------------------------------------------------------- helpers

def words(text):
    return WORD_RE.findall(text or "")


def norm_quotes(s):
    return (s or "").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')


def norm_space(s):
    s = norm_quotes(s)
    s = re.sub(r"\*\*|__", "", s)
    return re.sub(r"\s+", " ", s).strip()


def pct(n, d):
    return "0%" if not d else f"{round(100.0 * n / d)}%"


def pctv(n, d):
    return 0.0 if not d else 100.0 * n / d


def rate(n, d, per=100):
    return 0.0 if not d else per * n / d


def quantile(vals, q):
    if not vals:
        return 0
    s = sorted(vals)
    k = (len(s) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return s[int(k)]
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def median(vals):
    return quantile(vals, 0.5)


def r0(v):
    return int(round(v))


def r1(v):
    return f"{v:.1f}"


def read_text(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read().replace("\r\n", "\n").replace("\r", "\n")


def read_docx(path):
    """Text of a .docx, one line per paragraph, using only zipfile and the XML parser."""
    import zipfile
    from xml.etree import ElementTree as ET
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    try:
        with zipfile.ZipFile(path) as z:
            root = ET.fromstring(z.read("word/document.xml"))
    except (zipfile.BadZipFile, KeyError, ET.ParseError, OSError):
        return None
    lines = []
    for para in root.iter(ns + "p"):
        parts = []
        for node in para.iter():
            if node.tag == ns + "t" and node.text:
                parts.append(node.text)
            elif node.tag in (ns + "tab",):
                parts.append(" ")
            elif node.tag in (ns + "br", ns + "cr"):
                parts.append("\n")
        lines.append("".join(parts))
    return "\n".join(lines)


def die(msg, code=2):
    print(msg)
    sys.exit(code)


def load_map(path):
    if not path:
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError) as e:
        die(f"Cannot read the authors map {path}: {e}")


def expand_paths(paths):
    out = []
    for p in paths:
        if os.path.isdir(p):
            for name in sorted(os.listdir(p)):
                full = os.path.join(p, name)
                if os.path.isfile(full) and not name.startswith((".", "_")) and name.lower() != "readme.md":
                    out.append(full)
        elif os.path.isfile(p):
            out.append(p)
        else:
            die(f"Not found: {p}")
    return out


class People:
    def __init__(self, amap):
        self.owner = amap.get("voice_owner") or "the founder"
        self.aliases = {a.lower() for a in amap.get("aliases", []) or []}
        self.aliases.add(self.owner.lower())
        if " " in self.owner:
            self.aliases.add(self.owner.split()[0].lower())
        self.people = {k: (v if isinstance(v, str) else (v or {}).get("role", "other")).lower()
                       for k, v in (amap.get("people") or {}).items()}

    def resolve(self, raw):
        """Return (name, role) for an author string, or (raw, None) when unknown."""
        if not raw:
            return None, None
        s = norm_space(raw).strip().strip(",.")
        s = re.sub(r"<[^>]*>", "", s).strip()
        low = s.lower()
        if low in ("me", "founder", "myself", "mine"):
            return self.owner, "founder"
        if low in ("ai", "chatgpt", "claude", "gpt", "an ai tool", "copilot", "gemini"):
            return s, "ai"
        if low in self.aliases or any(a and (low == a or low.startswith(a + " ")) for a in self.aliases):
            return self.owner, "founder"
        for name, role in self.people.items():
            n = name.lower()
            if low == n or low.split()[0] == n.split()[0] or n in low:
                return name, role
        if low in COUNTED_ROLES | REFERENCE_ROLES | EXCLUDED_ROLES:
            return s, low
        return s, None


def norm_register(raw, filename=""):
    s = (raw or "").lower()
    if s:
        if s in REGISTERS:
            return s
        if re.search(r"spoken|transcript|call|podcast|video|voice ?note", s):
            return "spoken"
        if re.search(r"formal|proposal|contract|report|terms|policy|\bletter\b", s):
            return "formal document"
        if re.search(r"one-to-one|1:1|email|e-mail|\bdm\b|direct message|message|whatsapp|slack|text|reply", s):
            return "written one-to-one"
        if re.search(r"public|post|linkedin|instagram|newsletter|blog|article|website|twitter|substack|caption|thread", s):
            return "written public"
    f = os.path.basename(filename).lower()
    if re.search(r"transcript|voice[-_ ]?note|call|podcast", f):
        return "spoken"
    if re.search(r"email|e-mail|\bdm|dms|message|whatsapp|slack|inbox|repl", f):
        return "written one-to-one"
    if re.search(r"proposal|contract|report|(?<!news)letter", f):
        return "formal document"
    if re.search(r"post|linkedin|instagram|newsletter|blog|article|website|substack|caption|thread", f):
        return "written public"
    return None


# ---------------------------------------------------------------- splitting

def strip_front_matter(text):
    lines = text.split("\n")
    meta = {}
    if lines and lines[0].strip() == "---":
        for j in range(1, min(len(lines), 20)):
            if lines[j].strip() == "---":
                block = lines[1:j]
                if all(META_RE.match(b) or not b.strip() for b in block):
                    for b in block:
                        m = META_RE.match(b)
                        if m:
                            meta[m.group(1).lower()] = m.group(2).strip()
                    return meta, "\n".join(lines[j + 1:])
                break
    return meta, text


def take_meta(lines, allow_from=True):
    meta, i, seen = {}, 0, 0
    while i < len(lines) and seen < 8:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        m = META_RE.match(line)
        if not m or (m.group(1).lower() == "from" and not allow_from):
            break
        meta.setdefault(m.group(1).lower(), m.group(2).strip())
        seen += 1
        i += 1
    return meta, lines[i:]


def detect_split(lines):
    heads = [HEAD_RE.match(x) for x in lines]
    levels = [len(m.group(1)) for m in heads if m]
    if any(RULE_RE.match(x) for x in lines):
        return "rule"
    if sum(1 for x in lines if re.match(r"^\s*From:\s", x)) >= 2:
        return "email"
    if levels and levels.count(min(levels)) >= 2:
        return "heading"
    if re.search(r"\n\s*\n\s*\n", "\n".join(lines)):
        return "blank2"
    return "whole"


def split_lines(lines, mode):
    chunks, cur, titles, title = [], [], [], None
    if mode == "rule":
        for x in lines:
            if RULE_RE.match(x):
                chunks.append(cur); titles.append(None); cur = []
            else:
                cur.append(x)
        chunks.append(cur); titles.append(None)
    elif mode == "heading":
        levels = [len(HEAD_RE.match(x).group(1)) for x in lines if HEAD_RE.match(x)]
        top = min(levels) if levels else 1
        for x in lines:
            m = HEAD_RE.match(x)
            if m and len(m.group(1)) == top:
                chunks.append(cur); titles.append(title); cur = []; title = m.group(2).strip()
            else:
                cur.append(x)
        chunks.append(cur); titles.append(title)
    elif mode == "email":
        for x in lines:
            if re.match(r"^\s*From:\s", x) and cur and any(y.strip() for y in cur):
                chunks.append(cur); titles.append(None); cur = []
            cur.append(x)
        chunks.append(cur); titles.append(None)
    elif mode == "paragraph":
        for x in lines:
            if not x.strip():
                if any(y.strip() for y in cur):
                    chunks.append(cur); titles.append(None); cur = []
                continue
            cur.append(x)
        chunks.append(cur); titles.append(None)
    elif mode == "blank2":
        blank = 0
        for x in lines:
            if not x.strip():
                blank += 1
                cur.append(x)
                continue
            if blank >= 2 and any(y.strip() for y in cur):
                chunks.append(cur); titles.append(None); cur = []
            blank = 0
            cur.append(x)
        chunks.append(cur); titles.append(None)
    else:
        chunks, titles = [lines], [None]
    return [(c, t) for c, t in zip(chunks, titles) if any(x.strip() for x in c)]


def clean_email_body(lines):
    out = []
    for x in lines:
        if re.match(r"^\s*On .+wrote:\s*$", x) or re.match(r"^\s*-{2,}\s*(Original|Forwarded) Message", x, re.I):
            break
        if x.lstrip().startswith(">") or RULE_RE.match(x):
            continue
        out.append(x)
    return out


def split_signoff(lines):
    body = list(lines)
    while body and not body[-1].strip():
        body.pop()
    tail = []
    while body and len(tail) < 3:
        s = body[-1].strip()
        if not s or RULE_RE.match(s):
            body.pop()
            continue
        if len(words(s)) <= 4 and (SIGNOFF_RE.match(s) or s.endswith(",") or not re.search(r"[.?!:]$", s)) and not BULLET_RE.match(s):
            tail.insert(0, s)
            body.pop()
        else:
            break
    return body, " / ".join(tail)


def is_transcript(text, filename, reg):
    if reg == "spoken":
        return True
    hits = sum(1 for x in text.split("\n") if SPEAKER_RE.match(x) and (re.search(r"\d{1,2}:\d{2}", x[:20]) or ":" in x[:45]))
    timed = sum(1 for x in text.split("\n") if re.match(r"^\s*[\[(]?\d{1,2}:\d{2}", x))
    return timed >= 3 or (hits >= 4 and re.search(r"transcript|call|voice|note", os.path.basename(filename).lower()))


def parse_turns(text):
    turns, cur = [], None
    for line in text.split("\n"):
        if HEAD_RE.match(line.strip()):
            continue
        m = SPEAKER_RE.match(line)
        if m and m.group("name").strip().lower() not in ("note", "source", "date", "tags", "http", "https", "subject"):
            t = m.group("t1") or m.group("t2") or ""
            cur = {"speaker": m.group("name").strip(), "text": m.group("text").strip(), "time": t}
            turns.append(cur)
        elif cur is not None and line.strip():
            if re.match(r"^\s*[\[(]?\d{1,2}:\d{2}", line):
                cur = {"speaker": cur["speaker"], "text": re.sub(r"^\s*[\[(]?\d{1,2}:\d{2}(:\d{2})?[\])]?\s*", "", line).strip(),
                       "time": re.match(r"^\s*[\[(]?(\d{1,2}:\d{2}(?::\d{2})?)", line).group(1)}
                turns.append(cur)
            else:
                cur["text"] += " " + line.strip()
    return turns


REPLY_ACK_RE = re.compile(r"^\W*(ya|yaa|yeah|yes|yep|ok|okay|okk|noted|sure|done|got it|will do|understood|right)\b", re.I)
REPLY_ADDRESS_RE = re.compile(r"\b(ma'?am|madam|sir|boss|ji|mam)\b", re.I)
REPLY_BACK_RE = re.compile(r"\b(one doubt|should i|shall i|do you want me|let me know|can you confirm|please confirm|i will send|will do)\b", re.I)


def reply_signs(text):
    """Signs that a paragraph of a voice note is someone answering the founder, not the founder speaking."""
    t = norm_quotes(text or "")
    why = []
    if REPLY_ACK_RE.search(t):
        why.append(f"opens '{REPLY_ACK_RE.search(t).group(0).strip()}'")
    if REPLY_ADDRESS_RE.search(t):
        why.append(f"says '{REPLY_ADDRESS_RE.search(t).group(0)}'")
    if REPLY_BACK_RE.search(t) or "?" in t:
        why.append("asks a question back" if "?" in t else f"'{REPLY_BACK_RE.search(t).group(0)}'")
    return why if len(why) >= 2 else []


def ai_tells(text):
    """Return (score, reasons) for signs that a piece was machine-drafted."""
    t = norm_quotes(text)
    reasons, score = [], 0
    d = sum(t.count(c) for c in DASH)
    if d >= 2:
        score += 2; reasons.append(f"{d} long dashes")
    elif d == 1:
        score += 1; reasons.append("1 long dash")
    found = sorted({lab for rx, lab in STOCK_RE if rx.search(t)})
    if found:
        score += len(found); reasons.append("stock phrases: " + ", ".join(found))
    if CONTRAST_RE.search(t):
        score += 1; reasons.append("'not X, it's Y' contrast")
    triplets = len(re.findall(r"\b\w+, \w+,? and \w+\b", t))
    if triplets >= 2:
        score += 1; reasons.append(f"{triplets} triplet lists")
    emo = len(EMOJI_RE.findall(t))
    if emo >= 3 and re.search(r"^\s*\S*[\U0001F300-\U0001FAFF✅➡]", t, re.M):
        score += 1; reasons.append("emoji bullets")
    return score, reasons


def piece_status(pm, role, author, wc, min_words, extra_ask=None):
    """Status of a piece from the map's answers, its author's role and its length."""
    if pm.get("exclude"):
        return "excluded: " + str(pm.get("exclude"))
    if role is None:
        return f"ask: unknown author '{author}'"
    if role in EXCLUDED_ROLES:
        return f"excluded ({role})"
    if role in REFERENCE_ROLES:
        return "reference only (team)"
    if wc < min_words:
        return f"short (under {min_words} words)"
    if extra_ask and not pm.get("confirmed"):
        return extra_ask
    return "counted"


def load_transcript(name, text2, fmap, file_meta, people, min_words):
    """Pieces from a spoken file. The map's file-level author and exclude, split and pieces.<n> all apply.
    Labelled transcripts keep only the founder's turns. A phone voice note with no speaker labels is the
    founder's speech, except a paragraph that reads as a reply to them (ma'am, noted, a question back),
    which becomes its own piece and is asked about."""
    out = []
    file_pm = {k: fmap[k] for k in ("exclude", "confirmed") if fmap.get(k)}
    raw_file_author = fmap.get("author") or file_meta.get("author") or file_meta.get("by")
    turns = parse_turns(text2)
    spk = Counter(t["speaker"] for t in turns)
    if turns and not any(t["time"] for t in turns) and max(spk.values()) < 2 and len(spk) < 2:
        turns = []  # a stray colon in prose, not a speaker label
    if turns:
        owner_turns = [t for t in turns if people.resolve(t["speaker"])[1] in COUNTED_ROLES]
        speakers = sorted({t["speaker"] for t in turns})
        body = " ".join(t["text"] for t in owner_turns)
        wc = len(words(body))
        if file_pm.get("exclude"):
            status = "excluded: " + str(file_pm["exclude"])
        elif not owner_turns:
            status = "speaker not found: the transcript has speaker labels; add the founder's name as written to aliases"
        else:
            status = f"short (under {min_words} words)" if wc < min_words else "counted"
        out.append({"file": name, "piece": 1, "words": wc, "author": people.owner if owner_turns else NK,
                    "role": "founder" if owner_turns else NK, "register": "spoken", "status": status,
                    "signoff": "", "greeting": "", "text": body, "turns": owner_turns, "all_turns": turns,
                    "speakers": speakers, "first_words": " ".join(words(body)[:8]), "ai": (0, []), "split": "transcript"})
        return out
    # A phone voice note with no speaker labels.
    lines_ = text2.split("\n")
    lead = next((i for i, x in enumerate(lines_) if x.strip()), None)
    if lead is not None and (LABEL_RE.match(lines_[lead].strip()) or VOICE_LABEL_RE.search(lines_[lead])
                             or (lines_[lead].strip().endswith(":") and len(words(lines_[lead])) <= 14)):
        lines_ = lines_[lead + 1:]
    mode = fmap.get("split")
    if not mode:
        d = detect_split(lines_)
        mode = d if d in ("rule", "blank2", "heading") else None
    chunks = [c for c, _ in split_lines(lines_, mode)] if mode else [lines_]
    flags = {}
    if not fmap.get("split") and len(chunks) == 1:
        paras = [c for c, _ in split_lines(lines_, "paragraph")]
        signs = [reply_signs(" ".join(p)) if i else [] for i, p in enumerate(paras)]
        if any(signs):
            # Keep the founder's paragraphs together; each paragraph that reads as a reply is its own piece.
            chunks, cur = [], []
            for p_, sg in zip(paras, signs):
                if sg:
                    if cur:
                        chunks.append(cur); cur = []
                    chunks.append(p_)
                    flags[len(chunks)] = sg
                else:
                    cur = cur + [""] + p_ if cur else list(p_)
            if cur:
                chunks.append(cur)
    elif fmap.get("split"):
        for i, c in enumerate(chunks, 1):
            if i > 1 and reply_signs(" ".join(c)):
                flags[i] = reply_signs(" ".join(c))
    for n, chunk in enumerate(chunks, 1):
        pm = dict(file_pm, **((fmap.get("pieces", {}) or {}).get(str(n), {}) or {}))
        body = " ".join(x.strip() for x in chunk if x.strip())
        wc = len(words(body))
        raw_author = pm.get("author") or raw_file_author
        author, role = people.resolve(raw_author) if raw_author else (people.owner, "founder")
        ask = None
        if n in flags and not pm.get("author"):
            ask = f"ask: reads as a reply to you, not your own speech ({'; '.join(flags[n])})"
        status = piece_status(pm, role, author, wc, min_words, ask)
        if status == "counted" and len(chunks) == 1:
            print(f"NOTE: {name} has no speaker labels; read as a solo voice note by {people.owner}")
        if n in flags and status.startswith("ask"):
            print(f"NOTE: {name} piece {n} reads as someone replying to {people.owner} ({'; '.join(flags[n])}); "
                  f"ask in question 1, then set files.{name}.pieces.{n}.author to their name or exclude")
        is_owner = role in COUNTED_ROLES
        turn = [{"speaker": people.owner if is_owner else (author or NK), "text": body, "time": ""}]
        out.append({"file": name, "piece": n, "words": wc, "author": author or NK, "role": role or NK,
                    "register": "spoken", "status": status, "signoff": "", "greeting": "", "text": body,
                    "turns": turn if is_owner else [], "all_turns": turn, "speakers": [],
                    "first_words": " ".join(words(body)[:8]), "ai": (0, []), "split": "transcript"})
    return out


def load_samples(paths, amap):
    people = People(amap)
    fmaps = amap.get("files", {}) or {}
    min_words = int(amap.get("min_words", MIN_WORDS_PIECE))
    pieces, unreadable = [], []
    for path in expand_paths(paths):
        name = os.path.basename(path)
        fmap = fmaps.get(name, {}) or {}
        ext = os.path.splitext(name)[1].lower()
        if ext == ".docx":
            text = read_docx(path)
            if text is None:
                unreadable.append(name)
                continue
        elif ext not in READABLE:
            unreadable.append(name)
            continue
        else:
            text = read_text(path)
        raw_units = []
        if ext == ".csv":
            rows = list(csv.DictReader(io.StringIO(text)))
            if rows:
                cols = list(rows[0].keys())
                col = fmap.get("text_column") or max(cols, key=lambda c: sum(len(r.get(c) or "") for r in rows))
                acol = fmap.get("author_column") or next((c for c in cols if (c or "").strip().lower() in
                                                          ("author", "by", "written by", "from", "posted by")), None)
                for r in rows:
                    meta = {"author": r.get(acol)} if acol and r.get(acol) else {}
                    raw_units.append(((r.get(col) or "").split("\n"), None, meta))
            mode, file_meta = "csv", {}
        else:
            fm, text2 = strip_front_matter(text)
            file_meta = dict(fm)
            reg_hint = norm_register(fmap.get("register") or fm.get("register") or fm.get("channel"), name)
            if is_transcript(text2, name, reg_hint):
                pieces.extend(load_transcript(name, text2, fmap, file_meta, people, min_words))
                continue
            lines = text2.split("\n")
            mode = fmap.get("split") or detect_split(lines)
            top_meta, rest = take_meta(lines, allow_from=(mode != "email"))
            if top_meta:
                file_meta.update({k: v for k, v in top_meta.items() if k not in file_meta})
                lines = rest
            for chunk, title in split_lines(lines, mode):
                meta, body = take_meta(chunk, allow_from=True)
                if mode == "email":
                    body = clean_email_body(body)
                if words("\n".join(body)):
                    raw_units.append((body, title, meta))
        for n, (body, title, meta) in enumerate(raw_units, 1):
            pm = (fmap.get("pieces", {}) or {}).get(str(n), {}) or {}
            label = None
            lead_i = next((i for i, x in enumerate(body) if x.strip()), None)
            if lead_i is not None and LABEL_RE.match(body[lead_i].strip()):
                label = body[lead_i].strip()
                body = body[lead_i + 1:]
                if LABEL_NOTE_RE.search(label):
                    meta.setdefault("note", label)
            raw_author = (pm.get("author") or meta.get("author") or meta.get("written by") or meta.get("by")
                          or meta.get("from") or fmap.get("author") or file_meta.get("author") or file_meta.get("by"))
            explicit = bool(raw_author)
            author, role = people.resolve(raw_author) if raw_author else (people.owner, "founder")
            reg = norm_register(pm.get("register") or meta.get("register") or meta.get("channel") or meta.get("platform")
                                or fmap.get("register") or norm_register(label or "") or file_meta.get("register")
                                or file_meta.get("channel"), name)
            first_line = next((x.strip() for x in body if x.strip()), "")
            if pm.get("register") is None and meta.get("register") is None and (
                    mode == "email" or (GREETING_RE.match(first_line) and len(words(first_line)) <= 4)):
                reg = "written one-to-one"
            signoff, greeting, frame_marks, frame_lines = "", "", 0, 0
            if mode == "email" or reg == "written one-to-one":
                body, signoff = split_signoff(body)
                frame_marks += signoff.count("!")
                frame_lines = int("!" in signoff)
                lead = next((i for i, x in enumerate(body) if x.strip()), None)
                if lead is not None and len(words(body[lead])) <= 4 and GREETING_RE.match(body[lead].strip()):
                    # The greeting's own punctuation ("Hey Katie!") still counts toward exclamations.
                    frame_marks += body[lead].count("!")
                    frame_lines += int("!" in body[lead])
                    greeting = GREETING_RE.match(body[lead].strip()).group(1)
                    greeting = greeting[0].upper() + greeting[1:]
                    body = body[lead + 1:]
            else:
                tail = [x for x in body if x.strip()]
                if tail and len(words(tail[-1])) <= 3 and not re.search(r"[.?!]$", tail[-1].strip()) \
                        and not HASHTAG_RE.search(tail[-1]):
                    signoff = tail[-1].strip()
                    idx = max(i for i, x in enumerate(body) if x.strip())
                    body = body[:idx]
            joined = "\n".join(strip_hashtags(x) for x in body if not HASHTAG_RE.fullmatch(x.strip() or "x"))
            wc = len(words(joined))
            score, reasons = ai_tells("\n".join(body))
            signer = None
            if signoff and not explicit:
                for part in [x.strip() for x in signoff.split("/")]:
                    part = SIGNOFF_RE.sub("", part).strip(" ,.")
                    ws = words(part)
                    if not ws or len(ws) > 2 or not ws[0][0].isupper() or ws[0].lower() in ("x", "xx"):
                        continue
                    who, wrole = people.resolve(part)
                    if who != people.owner:
                        signer = (who, wrole)
                    break
            if pm.get("exclude"):
                status = "excluded: " + str(pm.get("exclude"))
            elif signer and signer[1] is None:
                status = f"ask: signed '{signer[0]}', not the voice owner"
            elif signer and signer[1] in EXCLUDED_ROLES | REFERENCE_ROLES:
                author, role = signer
                status = f"excluded ({role})" if role in EXCLUDED_ROLES else "reference only (team)"
            elif role is None:
                status = f"ask: unknown author '{author}'"
            elif role in EXCLUDED_ROLES:
                status = f"excluded ({role})"
            elif role in REFERENCE_ROLES:
                status = "reference only (team)"
            elif wc < min_words:
                status = f"short (under {min_words} words)"
            elif meta.get("note") and not pm.get("confirmed"):
                status = f"ask: your note says \"{meta['note']}\"" + (f"; also {'; '.join(reasons)}" if score >= AI_TELL_THRESHOLD else "")
            elif score >= AI_TELL_THRESHOLD and not pm.get("confirmed"):
                status = "ask: possible AI or ghostwritten draft (" + "; ".join(reasons) + ")"
            else:
                status = "counted"
            pieces.append({"file": name, "piece": n, "title": title, "words": wc, "author": author or NK,
                           "role": role or NK, "register": reg or "written public", "register_guessed": reg is None,
                           "status": status, "signoff": signoff, "greeting": greeting, "frame_marks": frame_marks, "frame_lines": frame_lines,
                           "text": "\n".join(body),
                           "first_words": " ".join(words(" ".join(body))[:8]), "ai": (score, reasons), "split": mode})
    return pieces, unreadable


WRITER_PATTERNS = [
    re.compile(r"\b([A-Z][a-z]+)\s*\(\s*(?:she|he|they)\s+(?:does|do|writes|write|runs|run|handles|handle|manages|manage|looks after|look after|posts|post)\s+(?:our|my|the|all our)\s+([a-z ]{3,30}?)\s*\)"),
    re.compile(r"\b([A-Z][a-z]+)\s+(?:does|writes|runs|handles|manages|looks after|posts|drafts|sorts)\s+(?:our|my|the|all our|all my)\s+(socials|social media|social|posts|instagram|linkedin|facebook|content|newsletters?|emails|marketing|blog|captions|copy|website)\b"),
    re.compile(r"\b(?:our|my)\s+(va|virtual assistant|assistant|agency|freelancer|copywriter|ghostwriter|intern|team member|"
               r"social media (?:person|manager|lady|guy|girl|bloke|intern)|marketing (?:person|agency|assistant|manager|intern)|"
               r"content (?:person|intern|writer|team|manager|creator))\b(?:,?\s+([A-Z][a-z]+))?", re.I),
    re.compile(r"\b([A-Z][a-z]+),?\s+(?:our|my)\s+(va|virtual assistant|assistant|copywriter|ghostwriter|intern|team member|"
               r"social media manager|social media intern|marketing assistant|marketing manager|content (?:intern|writer|person))\b"),
    re.compile(r"\b([A-Z][a-z]+)\s+(?:also\s+|sometimes\s+|usually\s+|often\s+)?(?:posts on|posts for|writes for|writes on|handles|drafts)\s+"
               r"(?:our|my|the|all our|all my)\s+([A-Za-z][A-Za-z ]{2,30}?)\b"),
]
# Capitalised words that start a sentence and are never a person's name.
NOT_NAMES = {"the", "she", "he", "they", "it", "we", "i", "our", "my", "this", "that", "also", "sometimes", "who", "which",
             "everyone", "someone", "nobody", "and", "but", "so", "then", "now", "usually", "often"}


def find_writers(text, people):
    """People the founder names as writing for them ('Bethan (she does our socials)', 'our VA, Priya')."""
    found = {}
    for rx in WRITER_PATTERNS:
        for m in rx.finditer(text or ""):
            g = [x for x in m.groups() if x]
            name = next((x for x in g if re.fullmatch(r"[A-Z][a-z]+", x) and x.lower() not in ("our", "my")), None)
            if name and name.lower() in NOT_NAMES:
                continue
            role_words = next((x for x in g if x != name), "")
            key = name or role_words
            if not key:
                continue
            if name and (people.resolve(name)[1] is not None and name.lower() not in people.aliases):
                continue
            if name and name.lower() in people.aliases:
                continue
            found.setdefault(key, m.group(0).strip())
    return found


def read_note(paths):
    """The founder's covering note, saved as _note.txt beside the samples; never measured."""
    texts = []
    for p in paths:
        cand = os.path.join(p, "_note.txt") if os.path.isdir(p) else None
        if cand and os.path.isfile(cand):
            texts.append(read_text(cand))
    return "\n".join(texts)


def style_outliers(pieces, amap):
    """Leave-one-out: flag written pieces whose habits sit far from the founder's other pieces.
    Polished AI copy usually drops every contraction, evens out sentence length and uses
    punctuation the founder never does. Adds reasons to the piece and returns nothing."""
    min_words = int(amap.get("min_words", MIN_WORDS_PIECE))
    pool = [p for p in pieces if p["register"] != "spoken" and p["words"] >= min_words
            and (p["status"] == "counted" or p["status"].startswith("ask: possible"))]
    if len(pool) < 4:
        return
    stats = {id(p): measure([p]) for p in pool}
    for p in pool:
        rest = [q for q in pool if q is not p]
        rs = measure(rest)
        f, fr = figures(stats[id(p)]), figures(rs)
        score, why = 0, []
        if f["contractible"] >= 4 and fr["contractible"] >= 8 and f["contraction_share"] < 50 and fr["contraction_share"] >= 85:
            score += 2; why.append(f"contractions {f['contraction_share']}% against {fr['contraction_share']}% in your other pieces")
        if f["contractible"] >= 4 and fr["contractible"] >= 8 and f["contraction_share"] >= 70 and fr["contraction_share"] <= 25:
            score += 2; why.append(f"contractions {f['contraction_share']}% against {fr['contraction_share']}% in your other pieces")
        own_idioms = idioms_in(p["text"])
        rest_idioms = set(i for q in rest for i in idioms_in(q["text"]))
        if len(own_idioms) >= 2 and not rest_idioms:
            score += 1; why.append(f"{len(own_idioms)} English idioms ({', '.join(own_idioms)}), which your other pieces never use")
        if f["sentence_median"] and fr["sentence_median"] and f["sentence_median"] > 2 * fr["sentence_median"]:
            score += 1; why.append(f"sentence median {f['sentence_median']} against {fr['sentence_median']}")
        s_p, s_r = stats[id(p)]["sentences"], rs["sentences"]
        if len(s_p) >= 5 and len(s_r) >= 10:
            def cv(v):
                m_ = sum(v) / len(v)
                return (sum((x - m_) ** 2 for x in v) / len(v)) ** 0.5 / m_ if m_ else 0
            if cv(s_p) < 0.5 * cv(s_r):
                score += 1; why.append("sentence lengths unusually even")
        pp, pr = stats[id(p)]["punct"], rs["punct"]
        odd = [k for k in ("semicolons", "colons", "exclamation marks", "dashes") if pp[k] >= 2 and pr[k] == 0]
        if odd:
            score += 1; why.append("uses " + " and ".join(odd) + ", which your other pieces never do")
        phrase_score, phrase_why = p["ai"]
        total = score + phrase_score
        p["style"] = (score, why)
        if amap_confirmed(amap, p):
            continue
        if p["status"].startswith("ask: possible") and why:
            p["status"] = p["status"][:-1] + "; " + "; ".join(why) + ")"
            continue
        if p["status"] != "counted":
            continue
        if p["words"] < 100:
            # A short chatty piece with "honestly" and one contrast line is often the founder's own: ask only on
            # three phrase tells, or one tell with a style outlier, or two style outliers.
            flag = score >= 2 or phrase_score >= AI_TELL_THRESHOLD or (phrase_score >= 1 and score >= 1)
        else:
            flag = score >= 2 or total >= AI_TELL_THRESHOLD or (total >= 2 and phrase_score >= 1)
        if flag:
            p["status"] = "ask: possible AI or ghostwritten draft (" + "; ".join(why + phrase_why) + ")"


def amap_confirmed(amap, p):
    pm = ((amap.get("files", {}) or {}).get(p["file"], {}) or {}).get("pieces", {}) or {}
    return bool((pm.get(str(p["piece"])) or {}).get("confirmed"))


def load_with_owner(paths, amap):
    """Load pieces; with no voice_owner set and exactly one unknown author named, take that author as the owner."""
    pieces, unreadable = load_samples(paths, amap)
    if not amap.get("voice_owner"):
        unknown = {p["author"] for p in pieces if p["status"].startswith("ask: unknown author")}
        signers = Counter(re.match(r"ask: signed '([^']+)'", p["status"]).group(1)
                          for p in pieces if p["status"].startswith("ask: signed '"))
        if not unknown and len(signers) == 1 and max(signers.values()) >= 2:
            unknown = set(signers)
        if len(unknown) == 1:
            name = unknown.pop()
            amap = dict(amap, voice_owner=name)
            print(f"NOTE: taking {name} as the voice owner (the only author or sign-off named); set voice_owner in the map if that is wrong")
            pieces, unreadable = load_samples(paths, amap)
    style_outliers(pieces, amap)
    note = read_note(paths)
    people = People(amap)
    writers = find_writers(note, people)
    for p in pieces:
        for k, v in find_writers(p["text"], people).items():
            writers.setdefault(k, v)
    amap["_writers"] = writers
    for k, v in writers.items():
        print(f"NOTE: you named {k} as writing for you (\"{v}\"); ask whether {k} wrote or edited any of these pieces, then add {k} to people in the map")
    return pieces, unreadable, amap


def verdict(pieces, amap):
    counted = [p for p in pieces if p["status"] == "counted"]
    asks = [p for p in pieces if p["status"].startswith("ask")]
    fw = sum(p["words"] for p in counted)
    potential = len(counted) + sum(1 for p in asks if p["words"] >= int(amap.get("min_words", MIN_WORDS_PIECE)))
    potential_words = fw + sum(p["words"] for p in asks)
    if potential < MIN_PIECES or potential_words < MIN_FOUNDER_WORDS:
        return "DECLINE", (f"{len(counted)} of your own pieces found ({fw} words); {MIN_PIECES} pieces and "
                           f"{MIN_FOUNDER_WORDS} words are needed")
    writers = amap.get("_writers") or {}
    if asks or writers:
        parts = []
        if asks:
            parts.append(f"{len(asks)} pieces need a quick authorship answer")
        if writers:
            parts.append("ask about " + ", ".join(writers) + " (named as writing for you)")
        return "ASK", "; ".join(parts) + " before measuring"
    if len(counted) < MIN_PIECES or fw < MIN_FOUNDER_WORDS:
        return "DECLINE", (f"{len(counted)} of your own pieces found ({fw} words); {MIN_PIECES} pieces and "
                           f"{MIN_FOUNDER_WORDS} words are needed")
    return "READY", f"{len(counted)} pieces, {fw} words"


# ---------------------------------------------------------------- measuring

EMPHASIS_WORDS = {"never", "not", "stop", "must", "every", "always", "free", "only", "huge", "really", "massive", "now", "need"}


def is_emphasis(m):
    """Capitals for emphasis, not an acronym: a long word, or a common word set in capitals."""
    if m in ACRONYMS:
        return False
    low = m.lower()
    return len(m) >= 5 or low in STOPLIST or low in EMPHASIS_WORDS


SENT_MARK = "\u241e"  # a sentence boundary set by an emoji run


def strip_hashtags(line):
    """Drop a run of hashtags at the end of a line; keep a mid-sentence hashtag as its word."""
    line = TRAIL_TAGS_RE.sub("", line)
    return HASHTAG_RE.sub(lambda m: m.group(0)[1:], line)


def protect_abbrevs(t):
    for a in ABBREVS:
        t = t.replace(a, a.replace(".", "․"))
    # A chain of initials ("S. L. said") is a name, never a sentence end. "Menu B. It is" still splits.
    t = re.sub(r"(?<![A-Za-z])([A-Z])\.(?=\s+[A-Z]\.)", "\\1․", t)
    t = re.sub(r"(?<=[A-Z]․\s)([A-Z])\.(?=\s)", "\\1․", t)
    return t


def text_units(text):
    """Return paragraphs, each a list of sentences."""
    paras, cur = [], []
    for line in text.split("\n") + [""]:
        s = line.strip()
        if not s or HEAD_RE.match(s):
            if cur:
                paras.append(cur)
            cur = []
            continue
        if HASHTAG_RE.sub("", s).strip() == "" and HASHTAG_RE.search(s):
            continue
        cur.append(line)
    out = []
    for para in paras:
        units, buf = [], ""
        for line in para:
            s = line.strip()
            is_item = bool(BULLET_RE.match(s) or NUMBERED_RE.match(s))
            s2 = NUMBERED_RE.sub("", BULLET_RE.sub("", s))
            s2 = BOLD_RE.sub(lambda m: m.group(0)[2:-2], s2)
            s2 = LINK_RE.sub("link", s2)
            s2 = strip_hashtags(s2)
            # An emoji run followed by a capital ends a sentence ("are OUT 🌸🌸 We walked"); elsewhere it is dropped.
            s2 = re.sub("(?<=\\S)\\s*[" + EMOJI_CLASS + "]+\\s*(?=[\"'(\u201c]?[A-Z0-9" + CUR_SIGNS + "])", SENT_MARK, s2)
            s2 = EMOJI_RUN_RE.sub(" ", s2)
            s2 = re.sub(r"[ \t]{2,}", " ", s2).strip()
            s2 = strip_hashtags(s2)
            if not s2:
                continue
            if is_item:
                if buf:
                    units.append(buf); buf = ""
                units.append(s2)
                continue
            if buf and not re.search(r"[.!?:\"')”]$", buf) and s2[:1].islower():
                buf += " " + s2
            else:
                if buf:
                    units.append(buf)
                buf = s2
        if buf:
            units.append(buf)
        sents = []
        for u in units:
            for sp in re.split(SENT_MARK + r"|(?<=[.!?…])[\"')\]”]*\s+(?=[\"'(\[“]?[A-Z0-9" + CUR_SIGNS + "])", protect_abbrevs(u)):
                sp = sp.replace("․", ".").strip()
                if words(sp):
                    sents.append(sp)
        if sents:
            out.append(sents)
    return out


def piece_format(text):
    lines = text.split("\n")
    return {
        "bullets": int(any(BULLET_RE.match(x) for x in lines)),
        "numbered": int(any(NUMBERED_RE.match(x) for x in lines)),
        "headings": int(any(HEAD_RE.match(x.strip()) for x in lines)),
        "bold": int(bool(BOLD_RE.search(text))),
        "emoji": int(bool(EMOJI_RE.search(text))),
        "hashtags": int(bool(HASHTAG_RE.search(text))),
        "links": int(bool(LINK_RE.search(text))),
    }


def tokens_of(sent):
    return [norm_quotes(w).lower() for w in words(sent)]


def new_stats():
    return {"pieces": 0, "words": 0, "sentences": [], "para_sents": [], "para_words": [], "questions": 0, "exclaims": 0,
            "fs": 0, "fp": 0, "sp": 0, "contr": 0, "expanded": 0, "punct": Counter(), "format": Counter(),
            "open_short": 0, "open_question": 0, "open_number": 0, "open_i": 0, "open_greeting": 0, "close_question": 0,
            "signoffs": Counter(), "greetings": Counter(), "caps": Counter(), "word_count": Counter(),
            "word_pieces": Counter(), "phrase_pieces": Counter(), "phrase_count": Counter(), "contrast": 0,
            "stock": Counter(), "stock_where": defaultdict(list), "piece_words": [], "frame_units": 0}


def measure(units, kind="written"):
    st = new_stats()
    for u in units:
        text = u["text"]
        paras = text_units(text)
        flat = [s for p in paras for s in p]
        if not flat:
            continue
        st["pieces"] += 1
        st["piece_words"].append(sum(len(words(s)) for s in flat))
        if kind == "written":
            for k, v in piece_format(text).items():
                st["format"][k] += v
            for p in paras:
                st["para_sents"].append(len(p))
                st["para_words"].append(sum(len(words(s)) for s in p))
            first, last = flat[0], flat[-1]
            if len(words(first)) <= SHORT_SENTENCE:
                st["open_short"] += 1
            if first.rstrip("\"')” ").endswith("?"):
                st["open_question"] += 1
            if re.match(r"^[\"'“(]?(?:[A-Z]{0,3}[" + CUR_SIGNS + "])?\\d", first):
                st["open_number"] += 1
            if re.match(r"^[\"'“]?I\b", first):
                st["open_i"] += 1
            if last.rstrip("\"')” ").endswith("?"):
                st["close_question"] += 1
            if u.get("signoff"):
                st["signoffs"][u["signoff"]] += 1
            if u.get("greeting"):
                st["greetings"][u["greeting"]] += 1
                st["open_greeting"] += 1
        seen_w, seen_p = set(), set()
        clean = " ".join(flat)
        for s in flat:
            toks = tokens_of(s)
            st["words"] += len(toks)
            st["sentences"].append(len(toks))
            end = s.rstrip("\"')”] ")
            if end.endswith("?"):
                st["questions"] += 1
            if end.endswith("!"):
                st["exclaims"] += 1
            for t in toks:
                if t in FIRST_SING:
                    st["fs"] += 1
                elif t in FIRST_PLUR:
                    st["fp"] += 1
                elif t in SECOND:
                    st["sp"] += 1
                if "'" in t and (t.endswith("n't") or re.search(r"'(re|ve|ll|d|m)$", t) or t in S_CONTRACT):
                    st["contr"] += 1
                if len(t) >= 3 and not t.isdigit() and t not in STOPLIST and "'" not in t:
                    st["word_count"][t] += 1
                    seen_w.add(t)
            for k in (2, 3, 4):
                for i in range(len(toks) - k + 1):
                    g = toks[i:i + k]
                    if g[0] in STOPLIST or g[-1] in STOPLIST or any(x.isdigit() for x in g):
                        continue
                    if sum(1 for x in g if x not in STOPLIST) < 2:
                        continue
                    ph = " ".join(g)
                    st["phrase_count"][ph] += 1
                    seen_p.add(ph)
            for m in CAPS_RE.findall(s):
                if is_emphasis(m):
                    st["caps"][m] += 1
        st["word_pieces"].update(seen_w)
        st["phrase_pieces"].update(seen_p)
        st["expanded"] += len(EXPANDED_RE.findall(clean))
        nclean = norm_quotes(clean)
        if CONTRAST_RE.search(nclean):
            st["contrast"] += 1
        for rx, lab in STOCK_RE:
            if rx.search(nclean):
                st["stock"][lab] += 1
                st["stock_where"][lab].append(f"{u.get('file', 'draft')} piece {u.get('piece', 1)}")
        c = st["punct"]
        if kind == "written" and u.get("frame_lines"):
            # "Hey Katie!" was cut as the greeting; its exclamation still counts, as a sentence of its own.
            st["exclaims"] += u["frame_lines"]
            st["frame_units"] += u["frame_lines"]
            c["exclamation marks"] += u.get("frame_marks", 0)
        c["commas"] += clean.count(",")
        c["full stops"] += len(re.findall(r"(?<!\.)\.(?!\.)(?=\s|$|[\"')”])", clean))
        c["semicolons"] += clean.count(";")
        c["colons"] += len(re.findall(r"(?<!\d):(?!\d)", clean))
        c["brackets"] += clean.count("(")
        c["dashes"] += sum(clean.count(ch) for ch in DASH) + len(re.findall(r"\s-\s", clean))
        c["ellipses"] += clean.count("…") + len(re.findall(r"\.\.\.", clean))
        c["exclamation marks"] += clean.count("!")
        c["question marks"] += clean.count("?")
        c["ampersands"] += clean.count("&")
    return st


SKIP_WORDS = set()   # names from the authors map; set by cmd_measure


def distinctive(st, limit=15):
    need = 2 if st["pieces"] >= 2 else 1
    items = [(w, st["word_pieces"][w], c) for w, c in st["word_count"].items()
             if st["word_pieces"][w] >= need and w not in SKIP_WORDS and not w.isdigit()
             and (len(w) >= 5 or st["word_pieces"][w] >= 3)]
    items.sort(key=lambda t: (-t[1], -t[2], t[0]))
    return items[:limit]


def repeated_phrases(st, limit=10):
    items = [(p, st["phrase_pieces"][p], st["phrase_count"][p]) for p in st["phrase_pieces"] if st["phrase_pieces"][p] >= 2
             and not any(w in SKIP_WORDS for w in p.split())]
    items.sort(key=lambda t: (-len(t[0].split()), -t[1]))
    kept = []
    for p, k, c in items:
        if any(p in q and k <= kq for q, kq, _ in kept):
            continue
        kept.append((p, k, c))
    kept.sort(key=lambda t: (-t[1], -t[2], t[0]))
    return kept[:limit]


def figures(st):
    """Plain numbers used by compare and stored in the profile."""
    s = st["sentences"]
    n = len(s)
    ps = st["para_sents"]
    return {
        "pieces": st["pieces"], "words": st["words"], "sentences": n,
        "sentence_median": r0(median(s)) if s else 0, "sentence_p10": r0(quantile(s, 0.1)) if s else 0,
        "sentence_p90": r0(quantile(s, 0.9)) if s else 0, "sentence_max": max(s) if s else 0,
        "sentence_mean": round(sum(s) / n, 1) if n else 0,
        "short_share": round(pctv(sum(1 for x in s if x <= SHORT_SENTENCE), n)),
        "fragment_share": round(pctv(sum(1 for x in s if x <= FRAGMENT), n)),
        "long_share": round(pctv(sum(1 for x in s if x >= LONG_SENTENCE), n)),
        "para_median_sents": r0(median(ps)) if ps else 0, "para_max_sents": max(ps) if ps else 0,
        "one_sentence_para_share": round(pctv(sum(1 for x in ps if x == 1), len(ps))) if ps else 0,
        "paragraphs": len(ps),
        "question_share": round(pctv(st["questions"], n)), "exclaim_share": round(pctv(st["exclaims"], n + st.get("frame_units", 0))),
        "i_per_100": round(rate(st["fs"], st["words"]), 1), "we_per_100": round(rate(st["fp"], st["words"]), 1),
        "you_per_100": round(rate(st["sp"], st["words"]), 1),
        "contraction_per_100": round(rate(st["contr"], st["words"]), 1),
        "contraction_share": round(pctv(st["contr"], st["contr"] + st["expanded"])),
        "contractible": st["contr"] + st["expanded"],
        "punct_per_1000": {k: round(rate(v, st["words"], 1000), 1) for k, v in st["punct"].items()},
        "format_pieces": dict(st["format"]), "open_question": st["open_question"], "open_short": st["open_short"],
        "open_greeting": st["open_greeting"], "close_question": st["close_question"], "contrast_pieces": st["contrast"],
        "piece_words_median": r0(median(st["piece_words"])) if st["piece_words"] else 0,
        "piece_words_max": max(st["piece_words"]) if st["piece_words"] else 0,
    }


CEILING_POINTS = 15


def ceilings(f):
    """Ceilings for a draft: the founder's measured rate plus 15 points. compare uses the same figures."""
    c = {"fragments": f["fragment_share"] + CEILING_POINTS, "questions": f["question_share"] + CEILING_POINTS,
         "exclamations": f["exclaim_share"] + CEILING_POINTS}
    if f.get("paragraphs"):
        c["one-sentence paragraphs"] = f["one_sentence_para_share"] + CEILING_POINTS
    return {k: min(v, 100) for k, v in c.items()}


def ceilings_line(f):
    c = ceilings(f)
    order = ["fragments", "one-sentence paragraphs", "questions", "exclamations"]
    return (f"Ceilings for a draft (your rate plus {CEILING_POINTS} points): " +
            "; ".join(f"{k} {c[k]}%" for k in order if k in c) + " (measured)")


def block_lines(st, label=None):
    T = "(measured)"
    f = figures(st)
    s = st["sentences"]
    L = []
    if not s:
        return [f"Nothing to measure {T}"]
    L.append(f"Written words: {st['words']} across {st['pieces']} pieces; piece length median {f['piece_words_median']} words, longest {f['piece_words_max']} {T}")
    L.append(f"Sentence length: median {f['sentence_median']} words; middle 80% {f['sentence_p10']} to {f['sentence_p90']}; longest {f['sentence_max']} ({len(s)} sentences) {T}")
    L.append(f"Short sentences ({SHORT_SENTENCE} words or fewer): {f['short_share']}%; fragments ({FRAGMENT} words or fewer): {f['fragment_share']}%; long ({LONG_SENTENCE} words or more): {f['long_share']}% {T}")
    if st["para_sents"]:
        L.append(f"Paragraphs: median {f['para_median_sents']} sentences; longest {f['para_max_sents']}; one-sentence paragraphs {f['one_sentence_para_share']}% {T}")
    L.append(f"Questions: {f['question_share']}% of sentences; exclamations: {f['exclaim_share']}% of sentences {T}")
    L.append(ceilings_line(f))
    L.append(f"Person: I {r1(f['i_per_100'])}, we {r1(f['we_per_100'])}, you {r1(f['you_per_100'])} per 100 words {T}")
    L.append(f"Contractions: {r1(f['contraction_per_100'])} per 100 words; {f['contraction_share']}% of contractible forms contracted ({f['contractible']} found) {T}")
    order = ["commas", "full stops", "question marks", "exclamation marks", "colons", "semicolons", "brackets", "dashes", "ellipses", "ampersands"]
    L.append("Punctuation per 1,000 words: " + "; ".join(f"{k} {r1(f['punct_per_1000'].get(k, 0.0))}" for k in order) + f" {T}")
    p = st["pieces"]
    fm = st["format"]
    L.append(f"Openings: {st['open_short']} of {p} open with a sentence of {SHORT_SENTENCE} words or fewer; {st['open_question']} with a question; {st['open_number']} with a number; {st['open_i']} with \"I\"; {st['open_greeting']} with a greeting {T}")
    L.append(f"Closings: {st['close_question']} of {p} close with a question {T}")
    L.append(f"Formatting: bullet lists in {fm['bullets']} of {p} pieces; numbered lists {fm['numbered']}; headings {fm['headings']}; bold {fm['bold']}; emoji {fm['emoji']}; hashtags {fm['hashtags']}; links {fm['links']} {T}")
    caps = ", ".join(f"{w} ({c})" for w, c in st["caps"].most_common(5)) or "none"
    L.append(f"Capitals for emphasis: {caps} {T}")
    if st["greetings"] or st["signoffs"]:
        L.append("Greetings: " + ("; ".join(f"\"{k}\" ({v})" for k, v in st["greetings"].most_common(5)) or "none found") + f" {T}")
        L.append("Sign-offs: " + ("; ".join(f"\"{k}\" ({v})" for k, v in st["signoffs"].most_common(5)) or "none found") + f" {T}")
    dw = "; ".join(f"{w} ({c} in {k} pieces)" for w, k, c in distinctive(st)) or "none"
    L.append(f"Distinctive words: {dw} {T}")
    rp = "; ".join(f"\"{ph}\" ({k} pieces)" for ph, k, c in repeated_phrases(st)) or "none"
    L.append(f"Repeated phrases: {rp} {T}")
    return L


def absence_lines(written, st):
    """What the founder never or rarely does, with counts (provisional until the founder confirms)."""
    n = len(written)
    checks = []
    def count(fn):
        return sum(1 for u in written if fn(u))
    checks.append(("long dashes (em or en)", count(lambda u: any(c in u["text"] for c in DASH))))
    checks.append(("exclamation marks", count(lambda u: "!" in u["text"] or u.get("frame_marks", 0) > 0)))
    checks.append(("emoji", count(lambda u: bool(EMOJI_RE.search(u["text"])))))
    checks.append(("hashtags", count(lambda u: bool(HASHTAG_RE.search(u["text"])))))
    checks.append(("bullet or numbered lists", count(lambda u: any(BULLET_RE.match(x) or NUMBERED_RE.match(x) for x in u["text"].split("\n")))))
    checks.append(("bold", count(lambda u: bool(BOLD_RE.search(u["text"])))))
    checks.append(("semicolons", count(lambda u: ";" in u["text"])))
    checks.append(("ellipses", count(lambda u: "..." in u["text"] or "…" in u["text"])))
    checks.append(("opening with a question", count(lambda u: bool(text_units(u["text"])) and text_units(u["text"])[0][0].rstrip("\"') ").endswith("?"))))
    checks.append(("closing with a question", count(lambda u: bool(text_units(u["text"])) and text_units(u["text"])[-1][-1].rstrip("\"') ").endswith("?"))))
    checks.append(("the 'not X, it's Y' contrast", count(lambda u: bool(CONTRAST_RE.search(norm_quotes(u["text"]))))))
    checks.append(("capitals for emphasis", count(lambda u: any(is_emphasis(m) for m in CAPS_RE.findall(u["text"])))))
    never = [lab for lab, c in checks if c == 0]
    rare = [f"{lab} ({c} of {n})" for lab, c in checks if c == 1 and n >= 4]
    stock_hits = defaultdict(list)
    for u in written:
        t = norm_quotes(u["text"])
        for rx, lab in STOCK_RE:
            if rx.search(t):
                stock_hits[lab].append(f"{u['file']} piece {u['piece']}")
    L = [f"Absent from all {n} written pieces (provisional until you confirm): " + ("; ".join(never) or "none of the moves checked") + " (measured)"]
    if rare:
        L.append("Rare, in 1 piece only: " + "; ".join(rare) + " (measured)")
    if stock_hits:
        L.append("Stock phrases found in your pieces: " + "; ".join(f"\"{k}\" ({', '.join(v)})" for k, v in sorted(stock_hits.items())) + " (measured)")
    else:
        L.append(f"Stock phrases: none of the {len(STOCK_PHRASES)} checked appear in any of your pieces (measured)")
    return L, {"never": never, "rare": rare, "stock_hits": {k: v for k, v in stock_hits.items()}}


def register_line(reg, st):
    f = figures(st)
    if not st["pieces"]:
        return f"{reg}: 0 pieces (measured)"
    unit = "piece" if st["pieces"] == 1 else "pieces"
    extra = f"; one-sentence paragraphs {f['one_sentence_para_share']}%" if reg != "spoken" and st["para_sents"] else ""
    return (f"{reg[0].upper() + reg[1:]}: {st['pieces']} {unit}, {st['words']} words; sentence median {f['sentence_median']}, "
            f"middle 80% {f['sentence_p10']} to {f['sentence_p90']}; questions {f['question_share']}%; "
            f"I {r1(f['i_per_100'])} and we {r1(f['we_per_100'])} per 100 words; "
            f"contractions {f['contraction_share']}% of contractible forms{extra} (measured)")


def _secs(t):
    parts = [int(x) for x in t.split(":")]
    return parts[0] * 60 + parts[1] if len(parts) == 2 else parts[0] * 3600 + parts[1] * 60 + parts[2]


def speaking_rate(spoken, people):
    words_n, files, turns_n, rates = 0, set(), 0, []
    for piece in spoken:
        turns = piece.get("all_turns", [])
        for i, t in enumerate(turns):
            if people.resolve(t["speaker"])[1] not in COUNTED_ROLES:
                continue
            nxt = next((u["time"] for u in turns[i + 1:] if u["time"]), None)
            if not t["time"] or not nxt:
                continue
            d = _secs(nxt) - _secs(t["time"])
            n = len(words(t["text"]))
            if d <= 0 or d > RATE_MAX_TURN_SECONDS or n < RATE_MIN_TURN_WORDS:
                continue
            words_n += n
            rates.append(n * 60.0 / d)
            turns_n += 1
            files.add(piece["file"])
    if rates and words_n >= RATE_MIN_WORDS:
        return round(median(rates)), (f"Speaking rate: {round(median(rates))} words a minute (median of {turns_n} timed turns, "
                                      f"{words_n} words, {len(files)} recording{'s' if len(files) != 1 else ''}) (measured)")
    return None, (f"Speaking rate: {NK} ({words_n} words in timed turns, under the {RATE_MIN_WORDS} needed; "
                  f"a timestamped transcript of five minutes or more gives it) (measured)")


def support(counted, fw, asks):
    regs = Counter(p["register"] for p in counted)
    written_regs = [r for r in ("written public", "written one-to-one") if regs.get(r, 0) >= 2]
    reasons = []
    if len(counted) < HIGH_PIECES:
        reasons.append(f"{len(counted)} pieces, {HIGH_PIECES} or more for high")
    if fw < HIGH_WORDS:
        reasons.append(f"{fw} words, {HIGH_WORDS} or more for high")
    if len(written_regs) < 2:
        reasons.append("2 or more pieces each of public and one-to-one writing needed for high")
    if asks:
        reasons.append(f"{asks} pieces with authorship unconfirmed")
    level = "high" if not reasons else "medium"
    return level, f"Samples support: {level} ({'; '.join(reasons) if reasons else f'{len(counted)} pieces, {fw} words, both written registers'}) (measured)"


def find_terms(pieces, terms):
    hits = {}
    for term in terms:
        rx = re.compile(r"(?<![\w-])" + re.escape(norm_quotes(term).lower()) + r"(?![\w-])", re.I)
        where = [f"{p['file']} piece {p['piece']}" for p in pieces if rx.search(norm_quotes(p["text"]))]
        hits[term] = where
    return hits


# ---------------------------------------------------------------- commands

def money_summary(written, spoken, amap):
    """Currency, units, date order, clock and number style from the founder's pieces (written; units also spoken)."""
    cur, order, clock, ex = Counter(), Counter(), Counter(), {}
    for p in written:
        c_, o_ = money_dates(p["text"], ex)
        cur.update(c_)
        order.update(o_)
        clock.update(clock_of(p["text"], ex))
    spoken_units = Counter()
    for p in spoken:
        for rx in MONEY_UNIT_RES:
            for m in rx.finditer(p["text"]):
                spoken_units[unit_key(m.group(1))] += 1
    cur.update(spoken_units)
    country = (amap.get("country") or "").strip().upper() or None
    if amap.get("decimal") not in (None, "dot", "comma"):
        die("decimal in the map must be \"dot\" or \"comma\"")
    ns = number_style([p["text"] for p in written], amap.get("decimal"))
    for k, v in spoken_units.items():
        ns["units"][k] = ns["units"].get(k, 0) + v
    return {"cur": cur, "order": order, "clock": clock, "ex": ex, "country": country, "numbers": ns,
            "line": money_dates_line(cur, order, ex, clock, country)}


def cmd_pieces(a):
    amap = load_map(a.map)
    pieces, unreadable, amap = load_with_owner(a.samples, amap)
    print(f"Voice owner: {People(amap).owner}")
    for p in pieces:
        flag = " (register guessed)" if p.get("register_guessed") else ""
        extra = f" | speakers: {', '.join(p['speakers'])}" if p.get("speakers") else ""
        print(f"{p['file']} piece {p['piece']} | {p['words']} words | {p['register']}{flag} | {p['author']} | {p['status']} | \"{p['first_words']}\"{extra}")
    for u in unreadable:
        print(f"NOT READ {u}: paste its text, or save it as .txt or .docx")
    # A preview for the defaults line, from pieces counted so far (written only); measure gives the final figures.
    so_far = [p for p in pieces if p["status"] == "counted" and p["register"] != "spoken"]
    print("Spelling so far: " + spelling_line(spelling_profile(so_far)).split(": ", 1)[1].replace(" (measured)", ""))
    md = money_summary(so_far, [p for p in pieces if p["status"] == "counted" and p["register"] == "spoken"], amap)
    print("Money and dates so far: " + md["line"].split(": ", 1)[1].replace(" (measured)", ""))
    print("Numbers so far: " + numbers_line(md["numbers"]).split(": ", 1)[1].replace(" (measured)", ""))
    for tok in md["numbers"]["ambiguous"][:1]:
        alt = tok.replace(".", "\u0000").replace(",", ".").replace("\u0000", ",")
        print(f"ASK NUMBER: '{tok}' reads two ways ({alt} or {tok} as a decimal). Ask once, inside the defaults line, "
              f"then set \"decimal\": \"comma\" or \"dot\" in the map")
    if not amap.get("country"):
        print("COUNTRY: not set. Set \"country\" (a two-letter code) in the map from what the founder says (their note, "
              "signature or business address), never from spelling; if nothing says, ask once inside the defaults line. "
              "It sets the Word file's paper size, and the date order and clock only where their writing shows none.")
    v, why = verdict(pieces, amap)
    print(f"{v}: {why}")
    if a.json_out:
        with open(a.json_out, "w", encoding="utf-8") as fh:
            json.dump([{k: v for k, v in p.items() if k not in ("all_turns", "turns")} for p in pieces], fh, indent=1)
    sys.exit({"READY": 0, "ASK": 4, "DECLINE": 3}[v])


def stored_pieces(path):
    """Pieces kept in an earlier profile (profile.json or the memory file), for a refresh."""
    prof = load_profile(path)
    out = []
    for sp in prof.get("samples", []):
        if sp.get("status") != "counted":
            continue
        piece = {"file": sp["file"], "piece": sp["piece"], "words": sp["words"], "author": prof.get("voice_owner", NK),
                 "role": "founder", "register": sp["register"], "status": "counted", "signoff": sp.get("signoff", ""),
                 "greeting": sp.get("greeting", ""), "frame_marks": sp.get("frame_marks", 0), "frame_lines": sp.get("frame_lines", 0),
                 "text": sp["text"], "first_words": " ".join(words(sp["text"])[:8]),
                 "ai": (0, []), "split": "stored"}
        if sp.get("turns"):
            piece["all_turns"] = sp["turns"]
        out.append(piece)
    return out


PLAUSIBLE_MAX_SENTENCE = 60
PLAUSIBLE_MAX_PIECE = 2500


def plausibility(written, spoken, wst, reg_stats, amap):
    """Headline figures that are almost always a misread paste. Each stops the build with a plain question."""
    ok_ = set(amap.get("plausible") or [])
    out = []
    if written:
        f = figures(wst)
        if f["sentence_max"] > PLAUSIBLE_MAX_SENTENCE and "longest sentence" not in ok_:
            out.append(("longest sentence", f"your longest written sentence measures {f['sentence_max']} words. That usually means "
                        "missing full stops, or two pieces run together. Check the piece, separate pieces with a line of ---, "
                        "or ask the founder whether they really write sentences that long."))
        if f["sentence_median"] < 3 and "sentence median" not in ok_:
            out.append(("sentence median", f"the typical sentence measures {f['sentence_median']} words, which usually means a list "
                        "or a table was measured as prose. Check the paste."))
    for p in written + spoken:
        if p["words"] > PLAUSIBLE_MAX_PIECE and "piece length" not in ok_:
            out.append(("piece length", f"{p['file']} piece {p['piece']} is {p['words']} words as one piece. If it holds several "
                        "posts or emails, separate them with a line of --- and run again."))
    sp = reg_stats.get("spoken")
    if sp and sp["sentences"] and figures(sp)["sentence_median"] > PLAUSIBLE_MAX_SENTENCE and "spoken sentences" not in ok_:
        out.append(("spoken sentences", "the transcript has almost no full stops, so the spoken rhythm cannot be read. Ask the "
                    "founder for the phone's transcript with punctuation, or leave the voice note out of the rhythm figures."))
    return out


def cmd_measure(a):
    amap = load_map(a.map)
    if a.profile_in:
        # A refresh keeps what the map said last time unless this map says otherwise: who is who, the country,
        # the decimal style the founder confirmed and any figure they confirmed.
        prev_ = load_profile(a.profile_in)
        for k in ("voice_owner", "aliases", "people", "country", "decimal", "plausible"):
            src = prev_.get("map", {}).get(k) if k not in ("voice_owner", "country") else prev_.get(k)
            if src and not amap.get(k):
                amap[k] = src
    if a.profile_in and not a.samples:
        pieces, unreadable = [], []
    else:
        pieces, unreadable, amap = load_with_owner(a.samples, amap)
    if a.profile_in:
        prev = load_profile(a.profile_in)
        # A refresh or a version 1 upgrade keeps what the founder already settled.
        a.never = a.never or list(prev.get("nevers") or [])
        a.signature = a.signature or list((prev.get("signature") or {}).keys())
        a.phrasing = a.phrasing or list((prev.get("phrasing") or {}).keys())
        if prev.get("spelling_system") and "spelling" not in amap:
            amap["spelling"] = prev["spelling_system"]
        if prev.get("polish") and "polish" not in amap:
            amap["polish"] = True
        seen = {norm_space(p["text"]).lower() for p in pieces}
        for sp in stored_pieces(a.profile_in):
            if norm_space(sp["text"]).lower() not in seen:
                pieces.append(sp)
        amap.pop("_writers", None)
    people = People(amap)
    SKIP_WORDS.clear()
    for name in list(people.people) + [people.owner] + list(people.aliases) + list(amap.get("clients") or []):
        for w in words(name.lower()):
            SKIP_WORDS.add(w)
    v, why = verdict(pieces, amap)
    provisional = False
    if v == "ASK" and getattr(a, "provisional", False):
        # First reply: a read from the pieces nobody has questioned, so the founder sees value before answering.
        n_ok = sum(1 for p in pieces if p["status"] == "counted")
        if n_ok >= 2:
            provisional = True
            print(f"PROVISIONAL: {why}; those pieces are left out of this read. Show it labelled provisional; "
                  "re-run without --provisional once the founder answers. Never pack or check-guide this profile.")
        else:
            print(f"{v}: {why}. Fewer than 2 unquestioned pieces, so no provisional read. Not measured.")
            sys.exit(4)
    elif v != "READY":
        print(f"{v}: {why}. Not measured.")
        sys.exit(3 if v == "DECLINE" else 4)
    counted = [p for p in pieces if p["status"] == "counted"]
    written = [p for p in counted if p["register"] != "spoken"]
    spoken = [p for p in counted if p["register"] == "spoken"]
    fw = sum(p["words"] for p in counted)
    L = []
    by_reg = Counter(p["register"] for p in counted)
    L.append(f"Voice owner: {people.owner} (measured)")
    L.append(f"Pieces counted: {len(counted)} of {len(pieces)}; by register: " + "; ".join(f"{r} {by_reg[r]}" for r in REGISTERS if by_reg.get(r)) + " (measured)")
    excl = Counter()
    for p in pieces:
        if p["status"] != "counted":
            excl[re.sub(r" \(.*$", "", p["status"]) if p["status"].startswith("ask") else p["status"]] += 1
    L.append("Pieces not counted: " + ("; ".join(f"{n} {k}" for k, n in sorted(excl.items())) or "none") + " (measured)")
    wst = measure(written) if written else new_stats()
    if written:
        L.extend(block_lines(wst))
        ab_lines, ab = absence_lines(written, wst)
        L.extend(ab_lines)
    else:
        ab = {"never": [], "rare": [], "stock_hits": {}}
        L.append("Written pieces: none; the written rules are drawn from speech and are provisional (measured)")
    reg_stats = {}
    for reg in REGISTERS:
        group = [p for p in counted if p["register"] == reg]
        if group:
            reg_stats[reg] = measure(group, "spoken" if reg == "spoken" else "written")
            L.append(register_line(reg, reg_stats[reg]))
    rate_val = None
    if spoken:
        sst = reg_stats["spoken"]
        dw = "; ".join(f"{w} ({c})" for w, k, c in distinctive(sst, 10)) or "none"
        L.append(f"Spoken distinctive words: {dw} (measured)")
        rate_val, line = speaking_rate(spoken, people)
        L.append(line)
    sig_hits = find_terms(counted, a.signature or [])
    if a.signature:
        L.append("Signature phrases: " + "; ".join(f"\"{t}\" in {len(w)} of {len(counted)} pieces" for t, w in sig_hits.items()) + " (measured)")
    never_hits = find_terms(counted, a.never or [])
    if a.never:
        found = {t: w for t, w in never_hits.items() if w}
        L.append("Your nevers found in your own pieces: " + ("; ".join(f"\"{t}\" ({', '.join(w)})" for t, w in found.items()) or "none") + " (measured)")
    banned_hits = {t: w for t, w in find_terms(counted, BANNED_VOCAB).items() if w}
    if banned_hits:
        L.append("Filler words found in your pieces: " + "; ".join(f"\"{t}\" ({', '.join(w)})" for t, w in banned_hits.items()) + " (measured)")
    # The founder's English: spelling, money, dates and idioms come from written pieces only, because a
    # phone or meeting transcript is spelled by the transcription tool, not by the founder.
    sp = spelling_profile(written)
    system = amap.get("spelling")
    if system and system not in SPELLING_SYSTEMS:
        die(f"spelling in the map must be one of {', '.join(SPELLING_SYSTEMS)} (only when the founder asks for it)")
    L.append(spelling_line(sp))
    if system:
        L.append(f"Spelling you asked for: the {system} pattern, stated by you; it overrides the forms above (measured)")
    md = money_summary(written, spoken, amap)
    cur, order = md["cur"], md["order"]
    L.append(md["line"])
    L.append(numbers_line(md["numbers"]))
    idiom_where = defaultdict(list)
    for p in written:
        for i_ in idioms_in(p["text"]):
            idiom_where[i_].append(f"{p['file']} piece {p['piece']}")
    if idiom_where:
        L.append("English idioms in your pieces: " + "; ".join(f"\"{k}\" ({', '.join(v)})" for k, v in sorted(idiom_where.items())) + " (measured)")
    else:
        L.append(f"English idioms: none of the {len(IDIOMS)} checked appear in your {len(written)} written pieces (measured)")
    # Phrasing is counted in every counted piece, spoken included: "do the needful" said on a voice note is the founder's.
    phr_hits = find_terms(counted, a.phrasing or [])
    spoken_ids = {f"{p['file']} piece {p['piece']}" for p in spoken}

    def phr_count(t, w):
        if not w:
            return f"\"{t}\" not found (copy it exactly from a piece)"
        ns_ = sum(1 for x in w if x in spoken_ids)
        reg_ = "" if not ns_ else f" ({ns_} spoken)" if ns_ < len(w) else " (spoken only)"
        return f"\"{t}\" in {len(w)} of {len(counted)} pieces{reg_}"
    if a.phrasing:
        L.append("Your phrasing, kept as written: " + "; ".join(phr_count(t, w) for t, w in phr_hits.items()) + " (measured)")
    polish = bool(amap.get("polish"))
    if polish:
        L.append("Polish: on, at your request; grammar is tidied, your words, rhythm and spelling are kept (measured)")
    asks = sum(1 for p in pieces if p["status"].startswith("ask"))
    level, sline = support(counted, fw, asks)
    L.append(sline)
    if provisional:
        L.insert(0, f"PROVISIONAL read: {asks} piece(s) awaiting an authorship answer are left out (measured)")
    stops = plausibility(written, spoken, wst, reg_stats, amap)
    if stops:
        for code_, msg in stops:
            print(f"STOP ({code_}): {msg}")
        print(f"{len(stops)} figure(s) look wrong. Not measured: ask the founder, fix the paste or the map, and run again. "
              "If the figure is right, add its name to \"plausible\" in the map.")
        sys.exit(5)
    profile = {
        "built": DATE, "provisional": provisional, "voice_owner": people.owner, "pieces_counted": len(counted), "founder_words": fw,
        "registers": dict(by_reg), "support": level, "written": figures(wst) if written else None,
        "by_register": {r: figures(s) for r, s in reg_stats.items()}, "absences": ab,
        "distinctive": [w for w, k, c in distinctive(wst)] if written else [],
        "repeated": [ph for ph, k, c in repeated_phrases(wst)] if written else [],
        "signature": {t: len(w) for t, w in sig_hits.items()}, "nevers": list(a.never or []),
        "never_found": {t: w for t, w in never_hits.items() if w}, "banned_found": banned_hits,
        "speaking_rate": rate_val, "measured_block": L,
        "spelling": sp, "spelling_system": system or None, "currency": dict(cur), "date_orders": sorted(date_orders(order)),
        "date_examples": md["ex"], "clock": dict(md["clock"]), "numbers": md["numbers"], "country": md["country"],
        "locale": locale_defaults(md["country"]) if md["country"] else None,
        "phrasing_where": {t: w for t, w in phr_hits.items()},
        "map": {k: amap[k] for k in ("aliases", "people", "decimal", "plausible") if amap.get(k)},
        "idioms": sorted(idiom_where), "phrasing": {t: len(w) for t, w in phr_hits.items()}, "polish": polish,
        "samples": [dict({"file": p["file"], "piece": p["piece"], "status": p["status"], "register": p["register"],
                          "words": p["words"], "text": p["text"], "greeting": p.get("greeting", ""), "signoff": p.get("signoff", ""),
                          "frame_marks": p.get("frame_marks", 0), "frame_lines": p.get("frame_lines", 0)},
                         **({"turns": [{"speaker": t["speaker"], "time": t["time"],
                                        "text": t["text"] if people.resolve(t["speaker"])[1] in COUNTED_ROLES or t["speaker"] == people.owner else ""}
                                       for t in p.get("all_turns", [])]} if p.get("all_turns") else {}))
                    for p in pieces],
    }
    if a.profile_out:
        with open(a.profile_out, "w", encoding="utf-8") as fh:
            json.dump(profile, fh, indent=1)
    md = "\n".join(L) + "\n"
    if a.md_out:
        with open(a.md_out, "w", encoding="utf-8") as fh:
            fh.write(md)
    print(md, end="")
    for u in unreadable:
        print(f"NOT READ {u}")


def strip_email_frame(text):
    """Remove a greeting line and a sign-off, as load_samples does for one-to-one pieces."""
    body, signoff = split_signoff(text.split("\n"))
    lead = next((i for i, x in enumerate(body) if x.strip()), None)
    if lead is not None and len(words(body[lead])) <= 6 and (GREETING_RE.match(body[lead].strip()) or
                                                            re.match(r"^(hi|hello|dear)\b", body[lead].strip(), re.I)):
        body = body[lead + 1:]
    return "\n".join(body)


def load_profile(path):
    """Read profile.json, or the compact profile kept in the memory file's '## Measured profile' json block."""
    text = read_text(path)
    if path.lower().endswith(".md"):
        m = re.search(r"(?:## Machine section|## Measured profile).*?```json\n(.*?)\n```", text, re.S)
        if not m:
            die(f"No measured profile block in {path}")
        text = m.group(1)
    try:
        return json.loads(text)
    except ValueError as e:
        die(f"Cannot read the profile in {path}: {e}")


def compact_profile(profile):
    """The profile for the memory file: figures plus the founder's own counted pieces (never excluded pieces),
    so a refresh on a surface with no saved files can re-measure old and new together."""
    out = {k: v for k, v in profile.items() if k != "samples"}
    out["samples"] = [sp for sp in profile.get("samples", []) if sp.get("status") == "counted"]
    return out


def draft_figures(text, one_to_one=False):
    if one_to_one or re.match(r"^\s*(hi|hello|dear)\b", text, re.I):
        text = strip_email_frame(text)
    unit = [{"text": text, "file": "draft", "piece": 1}]
    st = measure(unit)
    return st, figures(st)


MACHINE_HEAD = ("## Machine section\n\nDo not edit below this line. The skill reads it to pick up where you left off: "
                "your measured figures, the pieces of your own writing it measured, and the source of your voice guide.\n")


DAYS_MONTHS = set("""monday tuesday wednesday thursday friday saturday sunday mondays tuesdays wednesdays thursdays fridays
saturdays sundays january february march april may june july august september october november december jan feb mar apr
jun jul aug sep sept oct nov dec mon tue tues wed thu thur thurs fri sat sun christmas easter diwali eid ramadan
thanksgiving hanukkah passover holi""".split())


def initials(text, names):
    """Reduce each client name to initials ("Jess + Marco" to "J. + M.", "Sharma Logistics" to "S. L.")."""
    for name in sorted({n.strip() for n in names if n and n.strip()}, key=len, reverse=True):
        short = " ".join(w[0].upper() + "." for w in name.split())
        text = re.sub(r"(?<![\w])" + re.escape(name) + r"(?![\w])", short, text)
    return text


PHONE_RE = re.compile(r"(?<![\w$€£₹.,/])(?:\+\d{1,3}[\s.-]?)?(?:\(\d{2,5}\)[\s.-]?)?\d{2,5}(?:[\s.-]\d{2,5}){1,4}(?![\w%$€£₹/:])")
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")


def redact_contacts(text):
    """Phone numbers and email addresses never go into the memory file. A run of digits counts as a phone number
    only with at least 9 digits split by spaces, dots or hyphens (so 14,500, 10/17, 2027 and 10am to 11pm stay)."""
    n = 0

    def ph(m):
        nonlocal n
        if sum(c.isdigit() for c in m.group(0)) < 9 or re.match(r"(?:19|20)\d\d-\d\d-\d\d", m.group(0)):
            return m.group(0)
        n += 1
        return "[phone]"
    text = PHONE_RE.sub(ph, text)
    text, k = EMAIL_RE.subn("[email]", text)
    return text, n + k


def name_candidates(texts, keep):
    """Capitalised words mid-sentence that may be a person's or a business's name: never a sentence opener, a
    day or month, a common word, or a word the founder also writes in lower case."""
    lower_seen = set()
    for t in texts:
        lower_seen.update(w for w in re.findall(r"\b[a-z][a-z'’]+\b", t))
    keep_l = {w.lower() for k in keep for w in re.findall(r"[A-Za-z]+", k or "")}
    found = defaultdict(set)
    for i, t in enumerate(texts):
        for line in t.split("\n"):
            for m in re.finditer(r"(?<![\w#@])[A-Z][a-z]+", line):
                w, low = m.group(0), m.group(0).lower()
                prev = line[:m.start()].rstrip()
                if not prev or prev[-1] in ".!?:\"“(\u241e" or EMOJI_RE.search(prev[-1:]) or re.fullmatch(r"\s*(?:[-*•>]|\d{1,2}[.)])", prev):
                    continue
                if low in STOPLIST or low in DAYS_MONTHS or low in keep_l or low in lower_seen or len(w) < 3:
                    continue
                found[w].add(i)
    return found


def cmd_pack(a):
    """Write the measured profile and the guide source into the memory file's machine section. Client names are
    reduced to initials everywhere in the memory (stored pieces, guide source and the top part)."""
    mem = read_text(a.memory) if os.path.isfile(a.memory) else ""
    with open(a.profile, encoding="utf-8") as fh:
        prof = json.load(fh)
    amap = load_map(a.map) if a.map else {}
    clients = list(amap.get("clients") or []) + list(a.client or [])
    people = People(amap) if amap else None
    keep = list(amap.get("keep_names") or []) + list(a.keep or []) + [prof.get("voice_owner") or ""]
    if people:
        keep += list(people.aliases) + list(people.people)
    guide = read_text(a.guide) if a.guide else ""
    if "````" in guide:
        die("The guide contains four backticks in a row; remove them before packing.")
    if prof.get("provisional"):
        die("This profile is provisional (authorship answers pending). Re-run measure without --provisional, then pack.")
    comp = compact_profile(prof)
    n_contacts = 0
    for sp in comp["samples"]:
        sp["text"], k = redact_contacts(initials(sp["text"], clients))
        n_contacts += k
        for t in sp.get("turns") or []:
            t["text"], k = redact_contacts(initials(t.get("text", ""), clients))
            n_contacts += k
    comp["measured_block"] = [initials(x, clients) for x in comp.get("measured_block", [])]
    comp["names_reduced"] = True
    left = name_candidates([sp["text"] for sp in comp["samples"]], keep)
    if left and not a.names_checked:
        for w, where in sorted(left.items()):
            print(f"NAME?: '{w}' in {len(where)} stored piece(s). A client or patient goes in \"clients\" in the map "
                  "(stored as initials); a place, product or team member goes in \"keep_names\".")
        print("Not packed: the memory keeps clients by initials only. Sort each name above, then run pack again "
              "(or pass --names-checked once every name left is not a client).")
        sys.exit(1)
    head = mem.split("## Machine section")[0].split("## Measured profile")[0].rstrip() + "\n\n"
    block = MACHINE_HEAD + "\n```json\n" + json.dumps(comp, separators=(",", ":")) + "\n```\n"
    if guide:
        g, k = redact_contacts(initials(guide.rstrip(), clients))
        n_contacts += k
        block += "\n````markdown\n" + g + "\n````\n"
    with open(a.memory, "w", encoding="utf-8") as fh:
        fh.write(initials(head, clients) + block)
    print(f"Packed into {a.memory}: profile ({len(comp['samples'])} pieces of your writing)"
          + (", guide source" if guide else "") + (f"; {len(set(clients))} client name(s) reduced to initials" if clients else "")
          + (f"; {n_contacts} phone number(s) or email address(es) replaced" if n_contacts else ""))


def cmd_unpack(a):
    """Recover profile.json and the guide source from a memory file."""
    text = read_text(a.memory)
    prof = load_profile(a.memory)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "profile.json"), "w", encoding="utf-8") as fh:
        json.dump(prof, fh, indent=1)
    m = re.search(r"````markdown\n(.*?)\n````", text, re.S)
    if m:
        with open(os.path.join(a.out, "guide.md"), "w", encoding="utf-8") as fh:
            fh.write(m.group(1) + "\n")
    print(f"Unpacked to {a.out}: profile.json" + (", guide.md" if m else " (no guide source in this memory file)"))
    if "spelling" not in prof:
        print(f"NOTE: this memory predates spelling and phrasing; run: measure --profile-in {a.memory} --profile-out "
              f"{os.path.join(a.out, 'profile.json')} (re-measures the stored pieces, keeps the nevers and signatures)")


def cmd_compare(a):
    prof = load_profile(a.profile)
    text = read_text(a.draft)
    st, d = draft_figures(text, one_to_one=(a.register == "written one-to-one"))
    base = prof["by_register"].get(a.register) if a.register else None
    note, small_reg = "", None
    if base and base.get("pieces", 0) < 4:
        note = (f"(only {base['pieces']} {a.register} pieces measured, so compared with all your writing; "
                f"the sentence median may sit near either)")
        small_reg, base = base, None
    base = base or prof.get("written") or next(iter(prof["by_register"].values()))
    problems, warns, passed = [], [], []
    def ok(label):
        passed.append(label)
    tol = max(2, round(base["sentence_median"] * (0.35 if prof.get("support") == "high" else 0.25)))
    near_reg = small_reg is not None and abs(d["sentence_median"] - small_reg["sentence_median"]) <= tol
    if abs(d["sentence_median"] - base["sentence_median"]) > tol and not near_reg:
        msg = f"sentence median {d['sentence_median']} words; yours is {base['sentence_median']} (allowed {tol} either side)"
        if d["sentences"] < 6:
            # A two-line correction or a short reply has no stable median; never let it overrule the founder's own edit.
            warns.append(msg + f"; only {d['sentences']} sentences, too few to judge")
        else:
            problems.append(msg)
    else:
        ok("sentence median")
    if d["sentence_max"] > base["sentence_max"] + 5:
        problems.append(f"longest sentence {d['sentence_max']} words; your longest is {base['sentence_max']}")
    else:
        ok("longest sentence")
    if d["long_share"] > base["long_share"] + 15:
        warns.append(f"long sentences {d['long_share']}%; yours {base['long_share']}%")
    else:
        ok("long sentences")
    if d["contractible"] >= 4 and base["contractible"] >= 4:
        if abs(d["contraction_share"] - base["contraction_share"]) > 30:
            problems.append(f"contractions {d['contraction_share']}% of contractible forms; yours {base['contraction_share']}%")
        else:
            ok("contractions")
    ceil = ceilings(base)
    if base["exclaim_share"] == 0 and d["exclaim_share"] > 0:
        problems.append("exclamation marks used; you use none")
    elif st["exclaims"] >= 2 and d["exclaim_share"] > ceil["exclamations"]:
        problems.append(f"performative: exclamations {d['exclaim_share']}% of sentences; yours {base['exclaim_share']}%, "
                        f"ceiling {ceil['exclamations']}%")
    else:
        ok("exclamation marks")
    if any(c in text for c in DASH):
        problems.append("long dash used (house rule: none, and readers now read it as machine-written)")
    else:
        ok("dashes")
    fmt = base.get("format_pieces", {})
    dfmt = piece_format(text)
    for key, label in (("emoji", "emoji"), ("hashtags", "hashtags"), ("bullets", "bullet lists"), ("bold", "bold")):
        if dfmt.get(key) and not fmt.get(key):
            problems.append(f"{label} used; none in your pieces")
    stock = sorted({lab for rx, lab in STOCK_RE if rx.search(norm_quotes(text))})
    allowed = set(prof.get("banned_found", {}).keys())
    stock = [s for s in stock if s not in allowed]
    if stock:
        problems.append("stock phrases: " + ", ".join(stock))
    else:
        ok("stock phrases")
    banned = [t for t, w in find_terms([{"text": text, "file": "draft", "piece": 1}], BANNED_VOCAB).items()
              if w and t not in prof.get("banned_found", {})]
    if banned:
        problems.append("filler words: " + ", ".join(banned))
    else:
        ok("filler words")
    nevers = [t for t, w in find_terms([{"text": text, "file": "draft", "piece": 1}], list(prof.get("nevers", [])) + list(a.never or [])).items() if w]
    if nevers:
        problems.append("your nevers: " + ", ".join(nevers))
    else:
        ok("your nevers")
    # The founder's English: their spellings, their money and date style, and no idioms they never use.
    if "spelling" in prof:
        sp_probs, sp_warns = spelling_drift(text, prof.get("spelling"), prof.get("spelling_system"))
        if sp_probs:
            problems.append("spelling changed from yours: " + "; ".join(sp_probs))
        else:
            ok("spelling")
        warns.extend("spelling: " + w for w in sp_warns)
        cur_d, ord_d = money_dates(text)
        cur_f = set(prof.get("currency") or {})
        if cur_d and cur_f and not (set(cur_d) & cur_f):
            problems.append(f"money written as {', '.join(repr(k) for k in cur_d)}; your pieces write {', '.join(repr(k) for k in sorted(cur_f))}")
        elif cur_d and cur_f:
            ok("money")
            new_c = sorted(set(cur_d) - cur_f)
            if new_c:
                warns.append(f"money: {', '.join(repr(k) for k in new_c)} added; your pieces only write {', '.join(repr(k) for k in sorted(cur_f))}")
        elif cur_d and "numbers" in prof:
            warns.append(f"money: {', '.join(repr(k) for k in cur_d)} added; your pieces write no currency, so check the brief gave it")
        nf = prof.get("numbers")
        if nf:
            nd = number_style([text])
            g_f, g_d = set(nf.get("grouping") or {}), set(nd["grouping"])
            if g_d and g_f and not g_d <= g_f:
                theirs = ", ".join(nf["examples"][k] for k in sorted(g_f) if k in nf.get("examples", {}))
                mine = ", ".join(nd["examples"][k] for k in sorted(g_d - g_f))
                lakh_ = sorted({"lakh", "crore", "lac", "L", "cr"} & set(nf.get("units") or {}))
                if "indian" in g_d - g_f and lakh_:
                    problems.append(f"numbers written {mine}; you write amounts in {', '.join(lakh_)}")
                else:
                    problems.append(f"numbers written {mine}; you write them like {theirs}")
            elif "indian" in g_d and not g_f and ({"lakh", "crore", "lac", "L", "cr"} & set(nf.get("units") or {})):
                problems.append(f"numbers written {nd['examples']['indian']}; you write amounts in " + ", ".join(sorted(nf["units"])))
            if nd.get("decimal") and nf.get("decimal") and nd["decimal"] != nf["decimal"]:
                problems.append(f"decimals written with a {'comma' if nd['decimal'] == 'comma' else 'full stop'}; you use a "
                                f"{'comma' if nf['decimal'] == 'comma' else 'full stop'}")
        ord_f = set(prof.get("date_orders") or [])
        od = date_orders(ord_d)
        if od and ord_f and not (od & ord_f):
            problems.append(f"dates written {', '.join(sorted(od))}; yours are {', '.join(sorted(ord_f))}")
        elif od and ord_f:
            ok("dates")
        new_idioms = [i for i in idioms_in(text) if i not in set(prof.get("idioms") or [])]
        if new_idioms and not prof.get("idioms"):
            problems.append("English idioms you never use: " + ", ".join(new_idioms))
        elif new_idioms:
            warns.append("idioms not in your pieces: " + ", ".join(new_idioms))
        else:
            ok("idioms")
    if CONTRAST_RE.search(norm_quotes(text)) and prof.get("written") and not prof["written"].get("contrast_pieces", 0):
        problems.append("'not X, it's Y' contrast; you never write it")
    # Performative tics: habits pushed past the founder's own rate.
    words_n = max(1, d["words"])
    for phrase, n_pieces in (prof.get("signature") or {}).items():
        c = len(re.findall(r"(?<![\w-])" + re.escape(phrase.lower()) + r"(?![\w-])", norm_quotes(text).lower()))
        if c > 1:
            problems.append(f"performative: signature phrase \"{phrase}\" used {c} times (once a piece at most)")
    for phrase in (prof.get("phrasing") or {}):
        c = len(re.findall(r"(?<![\w-])" + re.escape(norm_quotes(phrase).lower()) + r"(?![\w-])", norm_quotes(text).lower()))
        if c > 1:
            problems.append(f"performative: your phrasing \"{phrase}\" used {c} times (once a piece at most)")
    for rep in prof.get("repeated", [])[:10]:
        c = norm_quotes(text).lower().count(rep)
        if c > 1:
            warns.append(f"performative: your phrase \"{rep}\" used {c} times in one piece")
    if d["fragment_share"] > ceil["fragments"]:
        problems.append(f"performative: fragments {d['fragment_share']}% of sentences; yours {base['fragment_share']}%")
    else:
        ok("fragments")
    if d.get("paragraphs", 0) >= 4 and base.get("one_sentence_para_share") is not None and d["one_sentence_para_share"] > base["one_sentence_para_share"] + CEILING_POINTS:
        warns.append(f"performative: one-sentence paragraphs {d['one_sentence_para_share']}%; yours {base['one_sentence_para_share']}%")
    nq = st["questions"]
    if base["question_share"] == 0:
        if nq >= 2:
            problems.append(f"{nq} questions; you ask none in writing")
        elif nq == 1:
            warns.append("1 question; you ask none in writing")
        else:
            ok("questions")
    elif nq >= 2 and d["question_share"] > ceil["questions"]:
        problems.append(f"performative: questions {d['question_share']}% of sentences; yours {base['question_share']}%, "
                        f"ceiling {ceil['questions']}%")
    elif d["question_share"] > ceil["questions"]:
        warns.append(f"questions {d['question_share']}% of sentences; yours {base['question_share']}%")
    else:
        ok("questions")
    own = [w for w in prof.get("distinctive", [])] + list((prof.get("signature") or {}).keys())
    if d["words"] > 100 and own:
        low = norm_quotes(text).lower()
        if not any(re.search(r"(?<![\w-])" + re.escape(w.lower()) + r"(?![\w-])", low) for w in own):
            warns.append("none of your own distinctive words or phrases appear")
    if base.get("open_question", 0) == 0 and d["open_question"]:
        warns.append("opens with a question; none of your pieces do")
    for p in problems:
        print("PROBLEM:", p)
    for w in warns:
        print("WARN:", w)
    total = len(passed) + len(problems)
    if note:
        print("NOTE:", note)
    print(f"Drift checks: {len(passed)} of {total} in range; {len(problems)} problems, {len(warns)} warnings "
          f"(draft: {d['words']} words, sentence median {d['sentence_median']})")
    sys.exit(1 if problems else 0)


def cmd_diff(a):
    before, after = read_text(a.before), read_text(a.after)
    sb, fb = draft_figures(before)
    sa, fa = draft_figures(after)
    import difflib
    sb_ = [x for para in text_units(before) for x in para]
    sa_ = [x for para in text_units(after) for x in para]
    nb, na = [norm_space(x).lower() for x in sb_], [norm_space(x).lower() for x in sa_]
    kept_a = set(nb) & set(na)
    cut_s = [sb_[i] for i, x in enumerate(nb) if x not in kept_a]
    new_s = [sa_[i] for i, x in enumerate(na) if x not in kept_a]
    replaced, used = [], set()
    for c in list(cut_s):
        best, score = None, 0.0
        for n in new_s:
            if n in used:
                continue
            r_ = difflib.SequenceMatcher(None, c.lower(), n.lower()).ratio()
            if r_ > score:
                best, score = n, r_
        if best is not None and score >= 0.45:
            replaced.append(f"\"{c}\" became \"{best}\"")
            used.add(best)
            cut_s.remove(c)
    removed = cut_s
    added = [n for n in new_s if n not in used]
    stock_before = sorted({lab for rx, lab in STOCK_RE if rx.search(norm_quotes(before))})
    stock_after = sorted({lab for rx, lab in STOCK_RE if rx.search(norm_quotes(after))})
    print(f"Words: {fb['words']} to {fa['words']}")
    print(f"Sentence median: {fb['sentence_median']} to {fa['sentence_median']}; longest {fb['sentence_max']} to {fa['sentence_max']}")
    print(f"Contractions: {fb['contraction_share']}% to {fa['contraction_share']}% of contractible forms")
    print(f"Exclamations: {fb['exclaim_share']}% to {fa['exclaim_share']}%; questions {fb['question_share']}% to {fa['question_share']}%")
    print(f"Dashes: {fb['punct_per_1000'].get('dashes', 0)} to {fa['punct_per_1000'].get('dashes', 0)} per 1,000 words")
    pf_b, pf_a = piece_format(before), piece_format(after)
    for k in ("emoji", "hashtags", "bullets", "bold"):
        if pf_b[k] != pf_a[k]:
            print(f"Formatting: {k} {'removed' if pf_b[k] else 'added'}")
    ub, ua = text_units(before), text_units(after)
    if ub and ua and norm_space(ub[0][0]) != norm_space(ua[0][0]):
        print(f"Opening changed: \"{ub[0][0]}\" to \"{ua[0][0]}\"")
    if ub and ua and norm_space(ub[-1][-1]) != norm_space(ua[-1][-1]):
        print(f"Closing changed: \"{ub[-1][-1]}\" to \"{ua[-1][-1]}\"")
    if stock_before != stock_after:
        print("Stock phrases cut: " + (", ".join(s for s in stock_before if s not in stock_after) or "none"))
    sb_sp = {low: w for w, low, h, v, f in spelling_hits(before)}
    sa_sp = {h: w for w, low, h, v, f in spelling_hits(after)}
    sp_changes = sorted({f"{w} to {sa_sp[SPELL[low][0]]}" for low, w in sb_sp.items()
                         if SPELL[low][0] in sa_sp and sa_sp[SPELL[low][0]].lower() != low})
    if sp_changes:
        print("Spelling changed: " + "; ".join(sp_changes))
    id_b, id_a = set(idioms_in(before)), set(idioms_in(after))
    if id_b - id_a:
        print("Idioms cut: " + ", ".join(sorted(id_b - id_a)))
    print("Sentences cut: " + ("; ".join(f"\"{g}\"" for g in removed[:15]) or "none"))
    print("Sentences reworded: " + ("; ".join(replaced[:15]) or "none"))
    print("Sentences added: " + ("; ".join(f"\"{g}\"" for g in added[:15]) or "none"))


REQUIRED_HEADINGS = [
    "## On one page", "## Never write", "## The rules that never bend", "## How you sound, measured", "## Traits", "## Tone",
    "## Do and don't", "## By register", "## Spelling and phrasing", "## Signature moves", "## Keep it natural", "## Before and after",
    "## Calibration", "## Evidence", "## Corrections log", "## Where this came from",
]


# The founder's English is their voice. The skill never calls it wrong and never names a country for it.
CORRECTION_RE = re.compile(
    r"\b(spelling|grammar|grammatical|english|phrasing|wording)\b[^.\n]{0,40}\b(mistakes?|errors?|incorrect|broken|poor|bad|"
    r"non-?native|unidiomatic|unnatural|awkward)\b|\b(mistakes?|errors?|incorrect|broken|poor|bad|non-?native|unidiomatic|"
    r"unnatural|awkward)\b[^.\n]{0,40}\b(spelling|grammar|english|phrasing|wording)\b", re.I)
COUNTRY_ENGLISH_RE = re.compile(
    r"\b(american|british|uk|us|australian|indian|singapore|singaporean|canadian|irish|new zealand|south african|"
    r"international|standard|proper|correct)\s+(english|spelling)\b", re.I)


def name_norm(s):
    """Lower case, with every capitalised word reduced to its initial, so 'Jess + Marco' matches 'J. + M.'."""
    return re.sub(r"\b([A-Z])(?:[a-z]+|\.)", r"\1.", s).lower()


def check_style(text, rel, problems, allowed_line):
    for i, line in enumerate(text.split("\n"), 1):
        if any(c in line for c in DASH):
            problems.append(f"{rel} line {i}: long dash")
        if allowed_line(line):
            continue
        low = re.sub(r'"[^"]{1,200}"', '""', norm_quotes(line)).lower()  # quoted words are cited, not written
        if CORRECTION_RE.search(low):
            problems.append(f"{rel} line {i}: describes the founder's English as wrong ('{CORRECTION_RE.search(low).group(0)}'); "
                            "their spelling and phrasing are their voice")
        if COUNTRY_ENGLISH_RE.search(low):
            problems.append(f"{rel} line {i}: names a variety of English ('{COUNTRY_ENGLISH_RE.search(low).group(0)}'); "
                            "describe the founder's own forms instead and never assume a country")
        for term in BANNED_VOCAB:
            if re.search(r"(?<![\w-])" + re.escape(term) + r"(?![\w-])", low):
                problems.append(f"{rel} line {i}: '{term}' in prose (allowed only in Never, Don't, Before and evidence lines)")


def cmd_check_guide(a):
    problems, warns = [], []
    prof = load_profile(a.profile)
    guide = read_text(a.guide)
    if prof.get("provisional"):
        problems.append("profile: provisional (authorship answers pending); re-run measure without --provisional first")
    samples = [s for s in prof.get("samples", []) if s["status"] == "counted"]
    all_samples = prof.get("samples", [])
    corpus = norm_space("\n".join(s["text"] for s in samples)).lower()
    full_corpus = norm_space("\n".join(s["text"] for s in all_samples)).lower()
    # Clients appear by initials in the guide and in the memory; a quote matches with any name reduced to its initial.
    n_corpus = name_norm(norm_space("\n".join(s["text"] for s in samples)))
    n_full = name_norm(norm_space("\n".join(s["text"] for s in all_samples)))

    def in_counted(q):
        return norm_space(q).lower() in corpus or name_norm(norm_space(q)) in n_corpus

    def in_any(q):
        return norm_space(q).lower() in full_corpus or name_norm(norm_space(q)) in n_full
    for h in REQUIRED_HEADINGS:
        if not re.search(r"^" + re.escape(h) + r"\b", guide, re.M):
            problems.append(f"guide: heading '{h}' missing")
    heads = re.findall(r"^## (.+)$", guide, re.M)
    if len(heads) < 2 or not heads[0].lower().startswith("on one page") or not heads[1].lower().startswith("never write"):
        problems.append("guide: the first sections must be 'On one page' then 'Never write' (banned phrases first)")
    op = re.search(r"^## On one page\s*\n(.*?)(?=^## )", guide, re.M | re.S)
    if op:
        opw = len(words(re.sub(r"<!--.*?-->", "", op.group(1))))
        print(f"On one page: {opw} words (limit {CHEATSHEET_MAX_WORDS})")
        if opw > CHEATSHEET_MAX_WORDS:
            problems.append(f"guide: 'On one page' is {opw} words, limit {CHEATSHEET_MAX_WORDS}")
        first_bold = re.search(r"\*\*([^*]+)\*\*", op.group(1))
        if not first_bold or not first_bold.group(1).lower().startswith("never"):
            problems.append("guide: 'On one page' must open with the never list")
    have_samples = bool(all_samples)
    if not have_samples:
        warns.append("samples not supplied (compact profile): quotes not re-verified; they were verified when the guide was built")
    m = re.search(r'^Sounds like: "(.+)"\s*$', guide, re.M)
    if not m:
        problems.append("guide: 'Sounds like: \"...\"' line missing under the title")
    elif have_samples and not in_counted(m.group(1)):
        problems.append("guide: the Sounds like sentence is not verbatim from a counted piece")
    hm = re.search(r"^Version .+$", guide, re.M)
    if not hm:
        problems.append("guide: the 'Version ... | From <n> pieces' header line is missing")
    else:
        head = hm.group(0)
        if f"{prof['pieces_counted']} pieces" not in head:
            problems.append(f"guide header: piece count does not match the measured {prof['pieces_counted']} pieces")
        for wn in re.findall(r"\b(\d[\d,]*) words\b", head):
            n = int(wn.replace(",", ""))
            if n not in (prof["founder_words"], HIGH_WORDS, MIN_FOUNDER_WORDS):
                problems.append(f"guide header: '{wn} words' does not match the measured {prof['founder_words']} words")
    if not re.search(r"^Unlike the usual: .+", guide, re.M):
        problems.append("guide: 'Unlike the usual:' line missing under the title")
    block = prof.get("measured_block", [])
    for line in block:
        if line not in guide:
            problems.append(f"guide: measured line missing or altered: {line[:70]}")
    for i, line in enumerate(guide.split("\n"), 1):
        em = EVIDENCE_RE.match(line)
        if em and have_samples:
            q = em.group("quote")
            tags = em.group("tags").lower()
            only_counted = all(sp.get("status") == "counted" for sp in all_samples)
            if not in_any(q) and "not yours" in tags and only_counted:
                warns.append(f"guide line {i}: 'not yours' quote not re-verified (the memory keeps only your own pieces)")
            elif not in_any(q):
                problems.append(f"guide line {i}: quote not found verbatim in the samples: \"{em.group('quote')[:50]}\"")
            elif not in_counted(q) and "not yours" not in tags:
                problems.append(f"guide line {i}: quote is from a piece that was not counted; tag it 'not yours'")
    do_lines = []
    for i, line in enumerate(guide.split("\n"), 1):
        dm = re.match(r"^Do: (.+?)\s*\(([^()]*)\)\s*$", line)
        if line.startswith("Do: "):
            src = dm.group(2).lower() if dm else ""
            text_ = dm.group(1) if dm else line[4:]
            do_lines.append(norm_space(text_).lower())
            if re.search(r"piece \d+|\.txt|\.md|\.docx|transcript", src):
                if have_samples and not in_counted(text_):
                    problems.append(f"guide line {i}: Do line is not verbatim from the piece it cites: \"{text_[:50]}\"")
            elif not re.search(r"not yet approved|approved \d{4}-\d{2}-\d{2}|calibration, approved", src):
                problems.append(f"guide line {i}: Do line has no source; cite '(<file> piece <n>)' or label it '(written in your voice, not yet approved)'")
    def count(rx):
        return len(re.findall(rx, guide, re.M))
    n_never = count(r"^- Never: ")
    n_rules = count(r"^Rule \d+: ")
    n_dont = count(r"^Don't: ")
    for dl in re.findall(r"^Don't: (.+)$", guide, re.M):
        if not re.search(r"\((?:generic|from [^)]*not yours|not yours)[^)]*\)\s*$", dl, re.I):
            problems.append(f"guide: Don't line not tagged '(generic example, not yours)' or '(from <piece>, not yours)': \"{dl[:50]}\"")
    n_ceiling = count(r"^(?:- )?Ceiling: ")
    if n_ceiling < 4:
        problems.append(f"guide: {n_ceiling} 'Ceiling:' lines; at least four, each with its measured rate")
    n_do = count(r"^Do: ")
    n_traits = count(r"^Trait \d: .+ \| means: .+ \| does not mean: .+")
    n_axes = count(r"^Tone axis \d: .+ \| [1-5] \| reason: .+")
    n_ceiling = count(r"^Ceiling: ")
    n_rewrites = count(r"^### Rewrite \d")
    n_befores = count(r"^Before \(")
    n_afters = count(r"^After \(")
    checks = [(n_never, 8, 30, "'- Never: ' lines"), (n_rules, 5, 7, "'Rule n:' lines (rules that never bend)"),
              (n_dont, 6, 12, "'Don't:' lines"), (n_do, 6, 12, "'Do:' lines"), (n_traits, 3, 3, "Trait lines"),
              (n_axes, 4, 4, "Tone axis lines"), (n_ceiling, 4, 10, "'Ceiling:' lines"), (n_rewrites, 3, 3, "rewrites"),
              (n_befores, 3, 3, "Before lines"), (n_afters, 3, 3, "After lines")]
    for n, lo, hi, label in checks:
        if n < lo or n > hi:
            problems.append(f"guide: {n} {label}; need {lo}" + (f" to {hi}" if hi != lo else ""))
    if n_do != n_dont:
        problems.append(f"guide: {n_do} Do lines and {n_dont} Don't lines; they come in pairs")
    if re.search(r"^## Calibration\s*\n+\s*\[", guide, re.M):
        warns.append("guide: Calibration section still holds a placeholder")
    def allowed(line):
        s = line.strip()
        return (s.startswith("- Never:") or s.startswith("**Never") or s.startswith("Don't:") or s.startswith("Before (") or s.startswith(">")
                or s.startswith("What changed:") or "(measured)" in s or s.startswith("|") or s.startswith("Edge case:"))
    check_style(guide, "guide", problems, allowed)
    block_text = "\n".join(block)
    section = ""
    for i, line in enumerate(guide.split("\n"), 1):
        if line.startswith("## "):
            section = line[3:].strip().lower()
        s_ = line.strip()
        if section.startswith("calibration") or "(measured)" in s_ or s_.startswith((">", "Do:", "Don't:", "Before (", "After (")):
            continue
        for pc in re.findall(r"\b\d+%", s_):
            if pc not in block_text:
                problems.append(f"guide line {i}: '{pc}' is not in the measured block; copy figures, never compute them")
    v11 = "spelling" in prof
    top_forms = [w for w, c in sorted((prof.get("spelling") or {}).get("forms", {}).items(), key=lambda t: (-t[1], t[0]))][:8]
    phrasing = [t for t, n in (prof.get("phrasing") or {}).items() if n]
    sec = re.search(r"^## Spelling and phrasing\s*\n(.*?)(?=^## )", guide, re.M | re.S)
    if v11 and sec:
        body = norm_quotes(sec.group(1)).lower()
        for w in top_forms:
            if not re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", body):
                problems.append(f"guide: 'Spelling and phrasing' does not list your form '{w}'")
        for t in phrasing:
            if norm_quotes(t).lower() not in body:
                problems.append(f"guide: 'Spelling and phrasing' does not keep your phrasing \"{t}\"")
        for t, n in (prof.get("phrasing") or {}).items():
            if not n and norm_quotes(t).lower() in body:
                problems.append(f"guide: \"{t}\" is kept as the founder's phrasing but is in none of their pieces; "
                                "never name phrasing they did not write")
        if prof.get("polish"):
            if "polish" not in body:
                problems.append("guide: polish is on, so 'Spelling and phrasing' must say what polish changes and what it keeps")
        elif not re.search(r"\bkept as (you|they|he|she) wr", body) and "as written" not in body:
            problems.append("guide: 'Spelling and phrasing' must say the founder's spelling and phrasing are kept as written")
    if a.prompt:
        pt = read_text(a.prompt)
        fm_ = re.search(r"=+ START OF FULL PROMPT[^\n]*\n(.*?)\n=+ END OF FULL PROMPT", pt, re.S)
        sm_ = re.search(r"=+ START OF SHORT VERSION[^\n]*\n(.*?)\n=+ END OF SHORT VERSION", pt, re.S)
        blocks = [fm_.group(1), sm_.group(1)] if fm_ and sm_ else re.findall(r"```(?:text)?\n(.*?)```", pt, re.S)
        if len(blocks) < 2:
            problems.append("prompt: needs the full prompt and the short version between their START and END markers")
        else:
            full, short = blocks[0], blocks[1]
            if not short.strip().lower().startswith("when i ask you to write"):
                problems.append("prompt: the short version must start 'When I ask you to write...' so it only applies to writing for the business")
            if "project" not in pt.lower():
                problems.append("prompt: placement must recommend a Project (ChatGPT Project or Claude Project) first")
            if "[NEED: a real" not in full:
                problems.append("prompt: must say to open on a real case only when the brief gives one, else [NEED: a real ...]")
            unit = r"(?:post|piece|email|caption|newsletter|video|update)s?"
            for rate_rx in (r"\bone " + unit + r" in (?:two|three|four|five|six|ten|\d+)\b",
                            r"\b(?:in|at most) (?:about )?one " + unit + r" in\b",
                            r"\bevery (?:other|second|third) " + unit + r"\b",
                            r"\b\d+ (?:of|in) (?:every )?\d+ " + unit + r"\b",
                            r"\bin about one in\b", r"\bone in (?:two|three|four|five|six|ten) " + unit + r"\b"):
                for rm in re.finditer(rate_rx, full, re.I):
                    problems.append(f"prompt: rate-based habit '{rm.group(0)}'; a single draft cannot keep a rate, so write it default-off ('do not ... unless I ask')")
            for dl in re.findall(r"^Do: (.+)$", full, re.M):
                if norm_space(dl).lower().rstrip(".") not in " ".join(do_lines) and do_lines:
                    problems.append(f"prompt: example Do line is not one of the guide's Do lines: \"{dl[:50]}\"")
            seen_l = Counter(norm_space(x).lower() for x in full.split("\n") if len(norm_space(x)) >= 25)
            for ln, k in seen_l.items():
                if k > 1:
                    problems.append(f"prompt: line repeated {k} times in the full prompt: \"{ln[:60]}\"")
            for dl in re.findall(r"^Don't: (.+)$", full, re.M):
                if not re.search(r"\((?:generic|from [^)]*not yours|not yours)[^)]*\)\s*$", dl, re.I):
                    problems.append(f"prompt: Don't line not tagged '(generic example, not yours)' or '(from <piece>, not yours)': \"{dl[:50]}\"")
            if len(full) > PROMPT_MAX_CHARS:
                problems.append(f"prompt: full block {len(full)} characters, limit {PROMPT_MAX_CHARS}")
            if len(short) > SHORT_PROMPT_MAX_CHARS:
                problems.append(f"prompt: short block {len(short)} characters, limit {SHORT_PROMPT_MAX_CHARS}")
            if "never" not in full[:600].lower():
                problems.append("prompt: the never list must come first")
            if prof.get("voice_owner", "").split()[0].lower() not in full.lower():
                problems.append("prompt: does not name whose voice it is")
            for rx_label in ("sentence", "contraction"):
                if rx_label not in full.lower():
                    problems.append(f"prompt: no measured {rx_label} target")
            if v11:
                fl = norm_quotes(full).lower()
                sl = re.search(r"^- spell[^\n]*$", fl, re.M)
                if not sl:
                    problems.append("prompt: needs a '- Spell ...' line with the founder's own forms")
                for w in top_forms:
                    if not re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", fl):
                        problems.append(f"prompt: your spelling '{w}' is not in the prompt")
                if prof.get("polish"):
                    if "polish" not in fl and "tidy" not in fl:
                        problems.append("prompt: polish is on; say what to tidy and what to keep")
                else:
                    if not re.search(r"do not (change|correct)[^.\n]*(spelling|phrasing)", fl):
                        problems.append("prompt: must say not to change the founder's spelling or phrasing")
                    for t in phrasing:
                        if norm_quotes(t).lower() not in fl:
                            problems.append(f"prompt: your phrasing \"{t}\" is not kept in the prompt")
                if (prof.get("currency") or prof.get("date_orders")) and "- money and dates:" not in fl:
                    problems.append("prompt: needs a '- Money and dates:' line copying how the founder writes them")
                for k in sorted(prof.get("currency") or {}, key=lambda k: -prof["currency"][k])[:1]:
                    if k.lower() not in fl:
                        problems.append(f"prompt: currency '{k}' as the founder writes it is missing")
                for o in prof.get("date_orders") or []:
                    if o not in fl:
                        problems.append(f"prompt: date order '{o}' is missing")
                # Numbers written back in the founder's style: units such as lakh, and any style a model would not default to.
                nf = prof.get("numbers") or {}
                mm_ = re.search(r"^- money and dates:[^\n]*$", fl, re.M)
                mline = mm_.group(0) if mm_ else ""
                for u in sorted(nf.get("units") or {}):
                    if u in ("lakh", "lac", "crore", "cr", "L") and u.lower() not in mline:
                        problems.append(f"prompt: the '- Money and dates:' line must say you write amounts in {u}")
                for k, ex_ in sorted((nf.get("examples") or {}).items()):
                    if k != "comma" and ex_.lower() not in fl:
                        problems.append(f"prompt: write numbers as the founder does; their form '{ex_}' ({GROUP_LABELS[k]}) is missing")
                if nf.get("decimal") == "comma" and nf.get("decimal_example") and nf["decimal_example"].lower() not in fl:
                    problems.append(f"prompt: the founder writes decimals with a comma ('{nf['decimal_example']}'); show that form")
            print(f"Prompt: full block {len(full)} characters (limit {PROMPT_MAX_CHARS}); short block {len(short)} characters (limit {SHORT_PROMPT_MAX_CHARS})")
        scan, in_never = [], False
        for line in pt.split("\n"):
            st_ = line.strip()
            if re.fullmatch(r"[A-Z][A-Z ,'()]{3,}", st_):
                in_never = st_.startswith("NEVER")
            line_ = re.sub(r"\bNever:[^.]*\.", "", line)
            scan.append("" if in_never or st_.startswith("Don't:") or st_.lower().startswith("instead of") else line_)
        check_style("\n".join(scan), "prompt", problems, lambda l: False)
        if any(c in pt for c in DASH):
            problems.append("prompt: contains a long dash")
    if a.cheatsheet:
        cs = read_text(a.cheatsheet)
        wc = len(words(cs))
        if wc > CHEATSHEET_MAX_WORDS:
            problems.append(f"cheat sheet: {wc} words, limit {CHEATSHEET_MAX_WORDS} (one page)")
        print(f"Cheat sheet: {wc} words (limit {CHEATSHEET_MAX_WORDS})")
        check_style(cs, "cheat sheet", problems, lambda l: "never" in l.lower()[:40] or l.strip().startswith("Don't"))
    for p in problems:
        print("PROBLEM:", p)
    for w in warns:
        print("WARN:", w)
    print(f"{len(problems)} problems, {len(warns)} warnings")
    sys.exit(1 if problems else 0)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    pc = sub.add_parser("pieces"); pc.add_argument("samples", nargs="+"); pc.add_argument("--map"); pc.add_argument("--json-out")
    ms = sub.add_parser("measure"); ms.add_argument("samples", nargs="*"); ms.add_argument("--map"); ms.add_argument("--profile-in")
    ms.add_argument("--never", action="append"); ms.add_argument("--signature", action="append")
    ms.add_argument("--phrasing", action="append")
    ms.add_argument("--profile-out"); ms.add_argument("--md-out")
    ms.add_argument("--provisional", action="store_true",
                    help="first reply only: measure the unquestioned pieces while authorship answers are pending")
    cp = sub.add_parser("compare"); cp.add_argument("draft"); cp.add_argument("--profile", required=True); cp.add_argument("--register"); cp.add_argument("--never", action="append")
    df = sub.add_parser("diff"); df.add_argument("before"); df.add_argument("after")
    pk = sub.add_parser("pack"); pk.add_argument("--memory", required=True); pk.add_argument("--profile", required=True); pk.add_argument("--guide")
    pk.add_argument("--map"); pk.add_argument("--client", action="append"); pk.add_argument("--keep", action="append")
    pk.add_argument("--names-checked", action="store_true")
    up = sub.add_parser("unpack"); up.add_argument("memory"); up.add_argument("--out", required=True)
    cg = sub.add_parser("check-guide"); cg.add_argument("guide"); cg.add_argument("--profile", required=True)
    cg.add_argument("--prompt"); cg.add_argument("--cheatsheet")
    a = p.parse_args()
    {"pieces": cmd_pieces, "measure": cmd_measure, "compare": cmd_compare, "diff": cmd_diff, "check-guide": cmd_check_guide, "pack": cmd_pack, "unpack": cmd_unpack}[a.cmd](a)


if __name__ == "__main__":
    main()
