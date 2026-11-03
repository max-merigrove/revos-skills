#!/usr/bin/env python3
"""Run every gate on the site files, then write the Quote Kit (.docx, ten fixed sections).

Usage:
  python3 scripts/build_kit.py --kit kit.json --settings settings.json --facts facts.json --panel panel-checked.json
        --robots robots.json --site-dir <out>/site-files --out-dir <out> --source <paste> [--source ...]
        [--audit page-audit.json ...] [--results results.json] [--baseline baseline.json] [--proxy proxy.json]

Nothing is written unless every gate passes: each page fragment (page_check), every figure and name
(claims_check), every JSON-LD file (jsonld_check), the llms.txt (llms_check), the banned patterns on the
pages and on the kit's own words (check_copy), the robots fix file when a search crawler is blocked, at
most five pages on a first run, the three actions in a safe order (the baseline before publishing; a
blocked search crawler among the three), and on a return run a named cause and fix for every failing
question and none for passing ones. The closing line must carry [BUSINESS_AUDIT_URL].
Exit 0 written, 1 with PROBLEM lines (nothing written), 2 with STOP. No network calls.
"""
import argparse
import glob
import json
import os
import re
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MONTHS, fmt_date, load_json, parse_date, read_text, save_json, slug, spell, stop, strip_html  # noqa: E402
import office as O  # noqa: E402
import page_check  # noqa: E402
import claims_check  # noqa: E402
import jsonld_check  # noqa: E402
import llms_check  # noqa: E402
import check_copy  # noqa: E402
from locale_numbers import locale_defaults  # noqa: E402

CAUSES = {"unreachable": "assistants cannot reach or read the page",
          "no page": "no page answers this question",
          "not quotable": "a page exists but gives no direct answer to lift",
          "quoted not recommended": "answers lean on other sites and name others: a presence gap, not a page gap",
          "described wrongly": "assistants describe you wrongly"}
ACTION_KINDS = ["baseline", "reach", "accuracy", "publish", "fix", "presence", "retest"]
LIMITS = [
    "Nobody can make an assistant recommend a business. This kit measures what assistants say and fixes what you own: your pages and your files.",
    "Google says you need no special markup, AI text files or pages written for AI to appear in its AI answers, and that Google Search ignores llms.txt "
    "(Google's AI optimization guide, last updated 10 July 2026).",
    "A study of about 300,000 domains (SE Ranking, November 2025) found no measurable link between having an llms.txt and being cited. It is cheap tidiness, not a lever.",
    "Google retired the FAQ rich result on 7 May 2026, so FAQ markup earns no special listing there. The questions and answers on the page itself still help readers and assistants.",
    "Answers change from run to run: a study by SparkToro and Gumshoe (January 2026) found AI tools gave the same list of brands less than 1 in 100 times. "
    "That is why every rate here is a count over several runs, with its sample size.",
    "The test shows whether rates changed, never why. A page going live and a change in rates can happen together by chance.",
]
JS_NOTE = ("Vercel and MERJ reported in December 2024 that the major AI crawlers they measured did not run scripts, with Google's Gemini "
           "(through Googlebot) and Apple's crawler the exceptions. That finding is nearly two years old; treat it as a reason to check, not a fact about today.")
UNBRANDED = ("This kit is a plain working document for you and whoever edits your site, not a branded one. The page text carries no styling, "
             "so it takes your own site's design when it is pasted in.")
COMPLIANCE = "Check the rules on testimonials, reviews and endorsements where you and your customers are."
PROTOCOL = [
    "Do every run within 72 hours, and before you publish any page from this kit.",
    "Use a private or logged-out browser window, with chat history and memory turned off where the assistant allows it. Turn search on where there is a choice.",
    "Paste each question exactly as written. Never add your business name to a question that does not already carry it.",
    "Start a new chat for every run, so earlier answers do not colour the next one.",
    "For each run, fill one row of the Runs sheet: the date, where you are, Named (is your business named?), Cited (is one of your own pages listed as a source?), "
    "Recommended (are you put forward as an option, or warned against?), Framing (favourable, neutral, hedged or against), the sources it lists, and what it said about you.",
    "Fewer than three runs for a question on an assistant reads UNKNOWN, never a pass or a fail.",
    "Send back the workbook, a CSV of its Runs sheet, or the rows pasted in a message, and say which pages went live and on what date.",
]
LABELS = {}
ENGLISH = {"v": ""}


def T(s):
    """The founder's language: a label file maps each English string to its translation; missing ones stay English,
    in the founder's English (American spelling for an American founder)."""
    return LABELS[s] if s in LABELS else spell(s, ENGLISH["v"])


def founder_words(facts, panel, audits):
    """The founder's and buyers' own words in the kit: never scored by the banned-pattern check (claims_check guards them)."""
    out = []
    for f in facts.get("facts", []):
        out += [str(f.get("value") or ""), str(f.get("need") or ""), str(f.get("label") or ""), str(f.get("source") or "")]
    for q in panel.get("questions", []) + panel.get("branded", []):
        if isinstance(q, dict):
            out += [str(q.get("text") or ""), str(q.get("quote") or ""), str(q.get("source") or ""), str(q.get("cut_reason") or "")]
    for au in audits or []:
        for c in au.get("checks", []):
            out += re.findall(r"'([^']{3,})'", str(c.get("detail") or ""))
    return [x for x in out if x.strip()]


def page_label(au):
    """'Your home page', not a scratch file name such as home.txt."""
    if au.get("label"):
        return au["label"]
    stem = re.sub(r"\.(txt|html?|md)$", "", os.path.basename(str(au.get("file") or "")), flags=re.I)
    stem = re.sub(r"^(audit|page|saved|fetched|paste)[-_]?", "", stem, flags=re.I)
    stem = re.sub(r"[-_]+", " ", stem).strip()
    if not stem or stem.lower() in ("home", "homepage", "index", "start", "startseite", "home page"):
        return T("Your home page")
    return T("Your {name} page").format(name=stem)


def label_keys():
    """Every English string the kit can print, for translation into the founder's language."""
    import ast
    keys = []
    tree = ast.parse(open(os.path.abspath(__file__), encoding="utf-8").read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "T" and node.args and isinstance(node.args[0], ast.Constant) \
                and isinstance(node.args[0].value, str):
            keys.append(node.args[0].value)
    keys += MONTHS + LIMITS + [JS_NOTE, COMPLIANCE, UNBRANDED] + PROTOCOL + list(CAUSES.values())
    keys += ["Crawlers that feed answers and search results", "Fetchers that open a page when a person asks", "Crawlers that collect pages for training"]
    keys += ["category", "choosing", "problem", "objection", "cost", "heard", "derived", "allowed", "blocked", "partly blocked", "unknown",
             "raw text", "noindex", "one h1", "question headings", "direct answer first", "dated", "price in text", "structured data",
             "text in images", "nothing gated", "hidden text", "text aimed at AI", "own", "competitor", "directory or review site", "media",
             "forum", "video", "other", "favourable", "neutral", "hedged", "against", "moved up", "moved down", "no clear change",
             "not comparable", "seen in some runs"]
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "agents.json"), encoding="utf-8") as fh:
            ag = json.load(fh)["agents"]
            keys += [a["if_blocked"] for a in ag] + [a["product"] for a in ag]
    except (OSError, ValueError):
        pass
    out = []
    for k in keys:
        if k not in out:
            out.append(k)
    return out


def gates(kit, settings, facts, panel, robots, site_dir, sources, return_run, results, audits=None):
    probs = []
    pages = sorted(glob.glob(os.path.join(site_dir, "page-*.html")))
    jsons = sorted(glob.glob(os.path.join(site_dir, "*.json")))
    llms = os.path.join(site_dir, "llms.txt")
    if not return_run and len(pages) > 5:
        probs.append(f"{len(pages)} pages; a first run rewrites at most five")
    if not pages and not kit.get("no_pages_reason"):
        probs.append("no page-*.html in site-files and no no_pages_reason in kit.json")
    price_ok = any(f.get("kind") == "price" and f.get("status") == "confirmed" for f in facts["facts"])
    statuses = {}
    for p in pages:
        html = read_text(p)
        spec = next((x for x in kit.get("pages", []) if f"page-{x.get('slug')}.html" == os.path.basename(p)), None)
        if spec is None:
            probs.append(f"{os.path.basename(p)} has no entry in kit.json pages")
            continue
        must = spec.get("must") or settings.get("must") or []
        pr, _w, info = page_check.fragment(html, must, price_ok and spec.get("price", True))
        probs += [f"{os.path.basename(p)}: {x}" for x in pr]
        statuses[spec["slug"]] = "finished" if info["finished"] else "not finished"
        cp, _cw, _n = check_copy.check(strip_html(html))
        probs += [f"{os.path.basename(p)}: {x}" for x in cp]
    files = pages + jsons + ([llms] if os.path.exists(llms) else [])
    qtext = " ".join(q.get("text", "") for q in panel.get("questions", []) if not q.get("cut"))
    probs += claims_check.check(facts, sources, files, entities=not settings.get("no_entities"), questions=qtext)
    seen_json = {}
    for j in jsons:
        body = re.sub(r"\s+", "", read_text(j))
        if body in seen_json:
            probs.append(f"{os.path.basename(j)} is identical to {seen_json[body]}: write one Service block per service, on the page that describes it")
        seen_json.setdefault(body, os.path.basename(j))
    allow_faq = bool(settings.get("faq_markup"))
    for j in jsons:
        raw = read_text(j)
        page_for = None
        m = re.match(r"service-(.+)\.jsonld\.json$", os.path.basename(j))
        if m and os.path.exists(os.path.join(site_dir, f"page-{m.group(1)}.html")):
            page_for = strip_html(read_text(os.path.join(site_dir, f"page-{m.group(1)}.html")))
        elif "FAQPage" in raw:
            page_for = " ".join(strip_html(read_text(p)) for p in pages)
        probs += jsonld_check.check_block(os.path.basename(j), raw, page_for, facts, bool(settings.get("reviews_shown")), allow_faq)
    if not jsons and not kit.get("no_pages_reason"):
        probs.append("no JSON-LD file in site-files (entity.jsonld.json at least)")
    if os.path.exists(llms):
        lp, _lw = llms_check.check(read_text(llms), facts)
        probs += [f"llms.txt: {x}" for x in lp]
    elif not kit.get("no_pages_reason"):
        probs.append("no llms.txt in site-files")
    blocked = [r["token"] for r in robots.get("rows", []) if r.get("verdict") == "FAIL"]
    rl = os.path.join(site_dir, "robots-lines.txt")
    if blocked and not os.path.exists(rl):
        probs.append(f"{', '.join(blocked)} blocked but no robots-lines.txt: run robots_check.py with --fix-out")
    if not blocked and os.path.exists(rl):
        probs.append("robots-lines.txt present though no search crawler is blocked")
    acts = (kit.get("read_first") or {}).get("actions") or []
    if len(acts) != 3:
        probs.append(f"read_first has {len(acts)} actions; it carries exactly three")
    kinds = [x.get("kind") for x in acts]
    for k in kinds:
        if k not in ACTION_KINDS:
            probs.append(f"action kind '{k}' must be one of {', '.join(ACTION_KINDS)}")
    if blocked and "reach" not in kinds:
        probs.append("a search crawler is blocked, so a reach action is one of the three")
    if not return_run:
        if "baseline" not in kinds:
            probs.append("a first run's actions include running the baseline")
        elif "publish" in kinds and kinds.index("publish") < kinds.index("baseline"):
            probs.append("the baseline comes before publishing")
    if return_run and results:
        failing = set(results.get("failing", []))
        fixes = (kit.get("next") or {}).get("fixes", [])
        fixed = {f.get("q") for f in fixes}
        for q in failing - fixed:
            probs.append(f"{q} failed and has no diagnosis and fix in kit.next.fixes")
        for f in fixes:
            if f.get("q") not in failing and not str(f.get("q", "")).startswith("B"):
                probs.append(f"{f.get('q')} has a fix but did not fail; fix only what failed")
            if f.get("cause") not in CAUSES:
                probs.append(f"{f.get('q')}: cause must be one of {', '.join(CAUSES)}")
    for x in (kit.get("next") or {}).get("accuracy_ignore", []):
        if not str(x.get("reason") or "").strip():
            probs.append(f"accuracy_ignore for {x.get('q')} run {x.get('run')} has no reason: say why the flagged line is not a wrong description")
    closing = kit.get("closing", "")
    if "[BUSINESS_AUDIT_URL]" not in closing:
        probs.append("the closing line must carry [BUSINESS_AUDIT_URL]")
    narrative = []
    rf = kit.get("read_first") or {}
    narrative += [rf.get("read", "")] + [x.get("text", "") for x in acts]
    narrative += kit.get("reach_notes", []) + kit.get("not_checked", [])
    narrative += (kit.get("beyond") or {}).get("actions", []) + (kit.get("beyond") or {}).get("notes", [])
    narrative += [f.get("fix", "") for f in (kit.get("next") or {}).get("fixes", [])]
    narrative += list((kit.get("next") or {}).get("accuracy", []))
    narrative += [x.get("where", "") for x in kit.get("pages", [])]
    cp, _w, _n = check_copy.check("\n".join(narrative), allow_quotes=True, exempt=founder_words(facts, panel, audits))
    probs += [f"kit text: {x}" for x in cp]
    if not return_run and re.search(r"(?i)\byou know which questions\b|\bwhich questions name you and which do not\b|\bje weet nu welke vragen\b|"
                                         r"\bsie wissen (jetzt|nun),? welche fragen\b|\bvous savez (maintenant )?quelles questions\b|"
                                         r"\bya sabes qué preguntas\b", closing):
        probs.append("the closing line says the founder knows which questions name them, but nothing has been run yet: "
                     "use the first-visit line (\"Once your baseline is in you will know which questions name you. ...\")")
    return probs, statuses, pages, jsons, llms, blocked


def html_to_doc(doc, html):
    for m in re.finditer(r"(?is)<(h1|h2|h3|p|ul|ol)\b[^>]*>(.*?)</\1>", html):
        tag, inner = m.group(1).lower(), m.group(2)
        if tag in ("ul", "ol"):
            for k, li in enumerate(re.findall(r"(?is)<li\b[^>]*>(.*?)</li>", inner), 1):
                doc.para(("• " if tag == "ul" else f"{k}. ") + strip_html(li), indent=520, after=40)
            continue
        text = strip_html(inner)
        if tag == "h1":
            doc.para(text, size=13, bold=True, before=120, after=80, indent=360, keep=True)
        elif tag in ("h2", "h3"):
            doc.para(text, bold=True, before=100, after=40, indent=360, keep=True)
        else:
            doc.para(text, indent=360, after=80)


def main():
    ap = argparse.ArgumentParser()
    for k in ("kit", "settings", "facts", "panel", "robots", "site-dir", "out-dir"):
        ap.add_argument("--" + k, required=False)
    ap.add_argument("--source", action="append", default=[])
    ap.add_argument("--audit", action="append", default=[])
    ap.add_argument("--results")
    ap.add_argument("--baseline")
    ap.add_argument("--proxy")
    ap.add_argument("--labels", help="the kit's fixed text in the founder's language (from --labels-template)")
    ap.add_argument("--labels-template", help="write every English string to this JSON file, to translate, and stop")
    a = ap.parse_args()
    if a.labels_template:
        save_json(a.labels_template, {k: k for k in label_keys()})
        print(f"WROTE {a.labels_template}: {len(label_keys())} strings. Translate the values (keep the keys and every {{placeholder}}), then pass --labels.")
        return 0
    if a.labels:
        lab = load_json(a.labels, "the labels file")
        bad = [k for k, v in lab.items() if set(re.findall(r"\{\w+\}", k)) != set(re.findall(r"\{\w+\}", str(v)))]
        if bad:
            stop(f"{len(bad)} translated label(s) lost or added a {{placeholder}}, for example '{bad[0][:60]}'. Keep every {{name}} exactly.")
        LABELS.update({k: str(v) for k, v in lab.items() if v})
    for k in ("kit", "settings", "facts", "panel", "robots", "site_dir", "out_dir"):
        if not getattr(a, k):
            stop(f"--{k.replace('_', '-')} is needed. See the usage at the top of scripts/build_kit.py.")
    kit = load_json(a.kit, "kit.json")
    settings = load_json(a.settings, "the settings file")
    facts = load_json(a.facts, "the fact register")
    panel = load_json(a.panel, "the checked panel")
    robots = load_json(a.robots, "the robots report")
    results = load_json(a.results, "the results") if a.results else None
    baseline = load_json(a.baseline, "the baseline") if a.baseline else None
    proxy = load_json(a.proxy, "the proxy read") if a.proxy else None
    audits = [load_json(p, "a page audit") for p in a.audit]
    sources = [read_text(s, "a source file") for s in a.source]
    if not os.path.isdir(a.site_dir):
        stop(f"{a.site_dir} is not a folder. Save the pages, JSON-LD and llms.txt into <out>/site-files first.")
    reg_probs = claims_check.validate_register(facts)
    return_run = bool(results and results.get("headline", {}).get("n"))
    ENGLISH["v"] = settings.get("english") or ""
    probs, statuses, pages, jsons, llms, blocked = gates(kit, settings, facts, panel, robots, a.site_dir, sources, return_run, results, audits)
    probs = reg_probs + probs
    if probs:
        for p in probs:
            print("PROBLEM:", p)
        print(f"{len(probs)} problems. Nothing was written: fix the source files (not the kit) and run again.")
        return 1

    country = settings.get("country", "")
    loc = locale_defaults(country)
    order = settings.get("date_order") or loc["date_order"]
    today = parse_date(kit.get("date") or settings.get("today")) or date.today()
    weeks = int(settings.get("cadence_weeks") or 4)
    retest = parse_date(kit.get("retest_date")) if kit.get("retest_date") else today + timedelta(weeks=weeks)
    biz = settings.get("business") or facts.get("business") or "Your business"
    d = O.Doc(paper=(settings.get("paper") or loc["paper"]))
    F = lambda x: fmt_date(x, order, [T(m) for m in MONTHS])  # noqa: E731

    # 1 Read first
    d.para(T("{biz}: Quote Kit").format(biz=biz), size=20, bold=True, after=40)
    d.para(T("{date}. What AI assistants can read about you, the questions your buyers ask them, and the pages that answer those questions.").format(date=F(today)),
           color="555555", after=280)
    d.h1(T("1. Read first"))
    d.para(kit["read_first"]["read"], size=12, after=200)
    d.para(T("This week, in this order:"), bold=True, after=60)
    for i, act in enumerate(kit["read_first"]["actions"], 1):
        d.para(f"{i}. {act['text']}", indent=300, after=80)
    if not return_run:
        d.para(T("Run the baseline before you publish anything. Without it you will not be able to tell whether anything changed."), bold=True, before=160)
    d.para(T(LIMITS[0]), before=120)
    if return_run:
        d.para(T("Next test: on or after {date}.").format(date=F(retest)), before=80)
    else:
        d.para(T("Next test: on or after {date}, four weeks after this kit (if your pages go live later, retest {weeks} weeks after they do).").format(date=F(retest), weeks=weeks),
               before=80)
    d.page_break()

    # 2 Reach
    d.h1(T("2. Can assistants reach you?"))
    seen = robots.get("seen", True)
    if kit.get("reach_from_memory"):
        d.para(T("Not re-checked on this visit. Last time: {finding}").format(finding=kit["reach_from_memory"]), after=120)
        robots = {"rows": [], "seen": True}
    elif not seen:
        d.para(T("Your robots.txt was not seen, so every crawler line below is UNKNOWN, not a fail. To settle it, open your web address followed by /robots.txt and paste what it shows."),
               after=120)
    for note in kit.get("reach_notes", []):
        d.para(note, after=80)
    shell = any(c.get("check") == "raw text" and c.get("verdict") == "FAIL" for au in audits for c in au.get("checks", []))
    if shell:
        d.para(T(JS_NOTE), color="555555", after=120)
    for purpose, title in (("search", "Crawlers that feed answers and search results"), ("user", "Fetchers that open a page when a person asks"),
                           ("training", "Crawlers that collect pages for training")):
        rows = [r for r in robots.get("rows", []) if r["purpose"] == purpose]
        if not rows or (not seen and purpose != "search"):
            continue
        d.h3(T(title))
        tbl = [[T("Crawler"), T("Operator"), T("What it feeds"), T("Your file says"), T("Verdict")]]
        for r in rows:
            v = {"PASS": "PASS", "FAIL": "FAIL", "WARN": T("check"), "UNKNOWN": "UNKNOWN", "training only": T("your choice")}[r["verdict"]]
            tbl.append([r["token"], r["operator"], T(r["product"]), T(r["status"]) + (f" ({'; '.join(r['deciding_rules'])})" if r["deciding_rules"] else ""), v])
        d.table(tbl, [1900, 1300, 3000, 2300, 1100], size=8)
    for r in [r for r in robots.get("rows", []) if r["verdict"] == "FAIL"]:
        d.para(T("{token} is blocked.").format(token=r["token"]) + " " + T(r["if_blocked"]), bold=True, after=60)
    train = [r for r in robots.get("rows", []) if r["verdict"] == "training only"]
    if train:
        d.para(T("Blocked for training only: {tokens}. That is an opt-out from AI training, and it does not keep you out of answers. Keep it or remove it as you prefer.").format(
            tokens=", ".join(r["token"] for r in train)), after=100)
    rl = os.path.join(a.site_dir, "robots-lines.txt")
    if os.path.exists(rl):
        owner = settings.get("robots_owner") or T("whoever looks after your site")
        d.para(T("The change, for {owner} (also saved as site-files/robots-lines.txt). If a plugin wrote the file, make the change in the plugin's settings, or it may write the old lines back:").format(owner=owner),
               bold=True, before=80)
        d.code(read_text(rl))
    if audits:
        d.h3(T("What the page itself shows"))
        tbl = [[T("Page"), T("Check"), T("Verdict"), T("Detail")]]
        for au in audits:
            for c in au.get("checks", []):
                tbl.append([page_label(au), T(c["check"]), c["verdict"], c["detail"]])
        d.table(tbl, [1800, 1700, 1000, 5100], size=8)
    dates = sorted({r["checked_on"] for r in robots.get("rows", []) if re.match(r"\d{4}-", r["checked_on"])})
    if dates:
        d.para(T("Crawler names and purposes checked on {date} against each operator's own page. They change; check again if this kit is old.").format(date=F(parse_date(dates[0]))),
               color="555555", before=120)
    d.page_break()

    # 3 Questions
    d.h1(T("3. Your buyer questions"))
    qs = [q for q in panel["questions"] if not q.get("cut")]
    heard = sum(q["tag"] == "heard" for q in qs)
    d.para(T("{n} questions, {heard} heard from your buyers and {derived} derived from your own offer words. Heard questions keep the buyer's words exactly. "
             "None includes your business name, because buyers who do not know you would not type it.").format(n=len(qs), heard=heard, derived=len(qs) - heard), after=60)
    if any(q.get("reworded") for q in qs):
        d.para(T("Where a buyer wrote to you rather than to an assistant (for example \"can you come to us?\"), the question is asked the way they would ask an assistant, with their own words beside it."),
               after=120)
    tbl = [["#", T("Question"), T("Family"), T("Source"), T("Came from"), T("Page that should answer it"), T("Run")]]
    for q in qs:
        run = (T("first") + (", " + T("quick") if q.get("quick") else "")) if q.get("priority") == "run first" else T("spare")
        text = q["text"] + ((" (" + T("heard as") + f": \"{q.get('quote', '')}\")") if q.get("reworded") else "")
        tbl.append([q["id"], text, T(q["family"]), T(q["tag"]), q.get("source", ""), q.get("page") or T("no page yet"), run])
    d.table(tbl, [450, 3000, 900, 750, 1900, 1700, 800], size=8)
    d.para(T("Three branded questions check what assistants say about you, against your fact register:"), bold=True, before=80)
    for b in panel.get("branded", []):
        d.para(f"{b['id']}. {b['text']}", indent=300, after=40)
    cuts = [q for q in panel["questions"] if q.get("cut")]
    if cuts:
        d.para(T("Cut by you:"), bold=True, before=120)
        for q in cuts:
            d.para(f"{q['text']} ({q.get('cut_reason', '')})", indent=300, after=40)
    d.page_break()

    # 4 Protocol
    engines = settings.get("engines") or ["ChatGPT"]
    nruns = int(settings.get("runs", 3))
    first = [q for q in qs if q.get("priority") == "run first"]
    full = len(first) * len(engines) * nruns
    quick = min(5, len(first)) * nruns
    d.h1(T("4. How to run the test"))
    d.para(T("The full panel: {q} questions on {engines}, {runs} runs each, {full} runs in all, plus the three branded questions once on each assistant. "
             "About {minutes} minutes, at a minute a run. The quick panel: the 5 questions marked quick, on {first} only, {runs} runs each, {quick} runs plus the three branded questions once, about {qmin} minutes.").format(
        q=len(first), engines=T(" and ").join(engines), runs=nruns, full=full, minutes=full + 3 * len(engines), first=engines[0], quick=quick, qmin=quick + 3), after=120)
    for i, s in enumerate(PROTOCOL, 1):
        d.para(f"{i}. {T(s)}", indent=300, after=70)
    d.page_break()

    # 5 Pages
    d.h1(T("5. What to publish"))
    if kit.get("no_pages_reason"):
        d.para(kit["no_pages_reason"], after=120)
    for spec in kit.get("pages", []):
        p = os.path.join(a.site_dir, f"page-{spec['slug']}.html")
        if not os.path.exists(p):
            continue
        st = statuses.get(spec["slug"], "")
        owned = [q for q in qs if q["id"] in spec.get("question_ids", [])]
        d.h2(spec.get("title") or spec["slug"])
        d.para(T("Answers:") + " " + "; ".join(f"{q['id']} {q['text']}" for q in owned), after=40)
        d.para(T("Where it goes:") + " " + spec.get("where", ""), after=40)
        svc = os.path.exists(os.path.join(a.site_dir, f"service-{spec['slug']}.jsonld.json"))
        d.para(T("File:") + f" site-files/page-{spec['slug']}.html" + (f" + site-files/service-{spec['slug']}.jsonld.json" if svc else ""), after=40)
        d.para(T("Ready to publish after your baseline.") if st == "finished" else T("Not finished: fill the [NEED] items first, then publish after your baseline."),
               bold=True, after=100)
        html_to_doc(d, read_text(p))
        labs = []
        for u in spec.get("facts_used", []):
            f = next((x for x in facts["facts"] if x.get("label") == u or x.get("kind") == u), None)
            if f:
                labs.append(f"{f.get('label') or f['kind']} ({f.get('source', '')})")
        if labs:
            d.para(T("Facts used:") + " " + "; ".join(labs), color="555555", before=80, after=40)
        for n in spec.get("needs", []):
            d.para(f"[NEED: {n}]", color="555555", after=40)
    d.page_break()

    # 6 Facts
    d.h1(T("6. Fact register"))
    d.para(T("Every page and file in this kit draws only on the facts below. Anything not here is not written. Change a fact here and the pages change with it."), after=120)
    tbl = [[T("Fact"), T("As you wrote it"), T("Status"), T("Source"), T("Confirmed")]]
    for f in facts["facts"]:
        val = f.get("value") if f.get("status") != "NEED" else f"[NEED: {f.get('need', '')}]"
        st = {"confirmed": T("confirmed"), "NEED": T("needed"), "declined": T("you chose to leave it out")}[f["status"]]
        tbl.append([f.get("label") or f["kind"], val, st, f.get("source", ""), F(parse_date(f.get("confirmed_on"))) if f.get("confirmed_on") else ""])
    d.table(tbl, [1800, 3300, 1500, 1800, 1200], size=8)
    d.page_break()

    # 7 Machine-readable
    d.h1(T("7. Machine-readable files"))
    d.para(T("Structured data (JSON-LD) states who you are and what you offer in a form engines parse reliably. It helps them read you correctly; no study isolates a lift in citations from it. "
             "Google says none is required for its AI answers."), after=100)
    plat = settings.get("platform")
    d.para(T("Where it goes: paste each block into the page's custom code or header code setting ({platform}), inside <script type=\"application/ld+json\"> and </script>. "
             "The entity block goes on every page (or the home page); each service block goes on its own page only.").format(platform=plat or T("your site builder")), after=100)
    for j in jsons:
        d.para(os.path.basename(j), bold=True, before=80, after=20)
        d.code(read_text(j))
    if any("FAQPage" in read_text(j) for j in jsons):
        d.para(T(LIMITS[3]), after=100)
    if os.path.exists(llms):
        d.para(T("llms.txt is a plain summary of your site for AI tools, in the format at llmstxt.org. It is optional, has no demonstrated effect on citations, and Google ignores it. "
                 "Upload it so it opens at your address followed by /llms.txt; if your site builder does not allow files at that address, skip it."), before=120, after=60)
        d.code(read_text(llms))
    d.page_break()

    # 8 Beyond
    d.h1(T("8. Beyond your own pages"))
    d.para(T("Assistants also draw on what other sites say about you. Being cited (your page used as a source) is not the same as being recommended: "
             "recommendations follow what reviews, directories, press and forums say across the web."), after=120)
    srcs = (results or {}).get("sources") or []
    if srcs:
        tbl = [[T("Domain"), T("Group"), T("Times listed"), T("For questions")]]
        for s in srcs[:15]:
            tbl.append([s["domain"], T(s["group"]), str(s["count"]), ", ".join(s["questions"])])
        d.table(tbl, [3200, 2400, 1300, 2700], size=8)
    elif proxy:
        d.para(T("A web search of each question without your name, run on {date}. This is a search, not an assistant's answer, and it is never scored:").format(date=F(parse_date(proxy.get("date")))),
               after=60)
        tbl = [["#", T("Domains that came up"), T("Businesses named")]]
        for r in proxy.get("rows", []):
            tbl.append([r.get("q", ""), ", ".join(r.get("domains", [])), ", ".join(r.get("named", []))])
        d.table(tbl, [600, 5000, 4000], size=8)
    else:
        d.para(T("No sources recorded yet. Your runs will list them; the Sources sheet counts them."), after=80)
    for n in (kit.get("beyond") or {}).get("notes", []):
        d.para(n, after=60)
    acts = (kit.get("beyond") or {}).get("actions", [])[:3]
    if acts:
        d.para(T("Honest actions, in order:"), bold=True, before=80)
        for i, x in enumerate(acts, 1):
            d.para(f"{i}. {x}", indent=300, after=60)
    d.para(T("Never buy, write or plant reviews or mentions, and never publish a list that ranks yourself first: assistants and buyers read those as what they are."),
           color="555555", before=80)
    d.page_break()

    # 9 Results
    d.h1(T("9. Results and what to do next"))
    pc = lambda v: f"{round(v * 100)}%"  # noqa: E731
    if not return_run:
        d.para(T("No runs yet, so there is no rate and no score. Run the baseline (section 4) before you publish anything."), after=80)
        d.para(T("Retest on or after {date}. Send the workbook back and say which pages went live and on what date.").format(date=F(retest)), after=80)
    else:
        h = results["headline"]
        lo, hi = h["range"]
        d.para(T("Panel headline: named in {x} of {n} runs, n equals {n} (range {lo} to {hi}). Cited in {c} of {n}; recommended in {r} of {n}.").format(
            x=h["named"], n=h["n"], lo=pc(lo), hi=pc(hi), c=h["cited"], r=h["recommended"]), size=12, bold=True, after=80)
        if baseline:
            from runlog import wilson
            bl, bh = wilson(baseline["named"], baseline["n"])
            d.para(T("Baseline, {date}: named in {x} of {n} runs, n equals {n} (range {lo} to {hi}).").format(
                date=F(parse_date(baseline.get("date"))), x=baseline["named"], n=baseline["n"], lo=pc(bl), hi=pc(bh)), after=60)
            mv = results.get("movement")
            d.para(T("Against the baseline: {mv}.").format(mv=T(mv)) + " " + (T("The two ranges do not overlap.") if mv.startswith("moved") else T("The ranges overlap, so this could be chance."))
                   + " " + T("The test cannot show what caused it."), bold=True, after=100)
        tbl = [[T("Engine"), T("Named"), T("Range"), T("Cited")]]
        for e, pe in results.get("per_engine", {}).items():
            tbl.append([e, T("{x} of {n}, n equals {n}").format(x=pe["named"], n=pe["n"]), f"{pc(pe['range'][0])} - {pc(pe['range'][1])}".replace(" - ", " " + T("to") + " "), str(pe["cited"])])
        d.table(tbl, [2400, 2800, 2400, 1200], size=8)
        tbl = [["#", T("Engine"), T("Named"), T("Verdict"), T("Note")]]
        for c in results["cells"]:
            tbl.append([c["q"], c["engine"], T("{x} of {n}, n equals {n}").format(x=c["named"], n=c["n"]) if c["n"] else T("no runs"), c["verdict"], T(c["flag"]) if c["flag"] == "seen in some runs" else c["flag"]])
        d.table(tbl, [600, 2000, 2600, 1300, 3100], size=8)
        frames = {}
        for c in results["cells"]:
            for k, v in c.get("framing", {}).items():
                frames[k] = frames.get(k, 0) + v
        if frames:
            d.para(T("How mentions were framed:") + " " + ", ".join(f"{T(k)} {v}" for k, v in sorted(frames.items(), key=lambda x: -x[1])) + ".", after=80)
        ignore = {(x.get("q"), str(x.get("run")), x.get("engine")) for x in (kit.get("next") or {}).get("accuracy_ignore", [])}
        for acc in results.get("accuracy", []):
            if (acc["q"], str(acc["run"]), acc["engine"]) in ignore:
                continue
            if acc.get("kind") == "missing":
                d.para(T("Not stated: {q} on {engine}, run {run}: the answer names no place; your register says {register}.").format(**acc), after=40)
            else:
                d.para(T("Described wrongly: {q} on {engine}, run {run}: {problem}; your register says {register}.").format(**acc), after=40)
        for note in (kit.get("next") or {}).get("accuracy", []):
            d.para(T("Described wrongly:") + " " + note, after=40)
        for n in results.get("notes", []):
            d.para(T("Note:") + f" {n}.", color="555555", after=40)
        fixes = (kit.get("next") or {}).get("fixes", [])
        if fixes:
            d.h3(T("What failed, why, and the fix"))
            for f in fixes:
                d.para(f"{f['q']}: {T(CAUSES[f['cause']])}. {f['fix']}", indent=300, after=60)
        d.para(T("Next retest: on or after {date}, the same questions, engines and run count.").format(date=F(retest)), bold=True, before=100)
    d.page_break()

    # 10 Limits
    d.h1(T("10. What this did not check"))
    items = list(kit.get("not_checked", []))
    all_eng = ["ChatGPT", "Perplexity", "Gemini", "Google AI answers", "Copilot", "Claude"]
    notrun = [e for e in all_eng if e not in engines]
    if notrun:
        items.append(T("Assistants not tested: {engines}. Rates for one assistant say nothing about another.").format(engines=", ".join(notrun)))
    if results and results.get("unknown_cells"):
        items.append(T("Too few runs to call: {cells}.").format(cells=", ".join(results["unknown_cells"])))
    items += [T(x) for x in LIMITS[1:3] + LIMITS[4:6] + [COMPLIANCE, UNBRANDED]]
    for x in items:
        d.bullet(x)
    d.para(kit["closing"], before=240)

    os.makedirs(a.out_dir, exist_ok=True)
    name = f"get-quoted-by-ai_{slug(biz)}_{today.isoformat()}.docx"
    path = os.path.join(a.out_dir, name)
    d.save(path, footer=f"{biz} | Quote Kit | {F(today)}", title=f"{biz}: Quote Kit", lang=settings.get("kit_language") or settings.get("language") or "en-GB")
    text = "\n".join(d.texts)
    cp, _w, _n = check_copy.check(text, allow_quotes=True, exempt=founder_words(facts, panel, audits)
                                  + [strip_html(x) for p in pages for x in re.findall(r"(?is)<(?:h[1-6]|p|li)\b[^>]*>(.*?)</(?:h[1-6]|p|li)>", read_text(p))]
                                  + [read_text(j) for j in jsons]
                                  + ([read_text(llms)] if os.path.exists(llms) else []))
    if cp:
        os.remove(path)
        for x in cp:
            print("PROBLEM: kit:", x)
        print("Nothing was written.")
        return 1
    n_pages = len(pages)
    fin = sum(1 for s in statuses.values() if s == "finished")
    print(f"WROTE {path}")
    print(f"SLUG: {slug(biz)} (name the workbook ai-query-test_{slug(biz)}_<date>.xlsx)")
    for i, act in enumerate(kit["read_first"]["actions"], 1):
        print(f"ACTION {i}: {act['text']}")
    print(f"SUMMARY 1: {biz}; {len(qs)} questions ({heard} heard); {n_pages} page(s) ({fin} finished); "
          f"{len(jsons)} JSON-LD file(s){', llms.txt' if os.path.exists(llms) else ''}{', robots-lines.txt' if os.path.exists(rl) else ''}")
    reach = (f"reach not re-checked (last time: {kit['reach_from_memory'].rstrip('.')})" if kit.get("reach_from_memory") else
             f"search crawler blocked: {', '.join(blocked)}" if blocked else
             "robots.txt not seen: reach UNKNOWN" if not robots.get("seen", True) else "no search crawler blocked")
    if shell:
        reach += "; the page as served is almost empty without scripts"
    if return_run:
        h = results["headline"]
        print(f"SUMMARY 2: {reach}; {h['text']}" + (f"; against the baseline: {results.get('movement')}" if baseline else ""))
    else:
        print(f"SUMMARY 2: {reach}; no runs yet: run the baseline before you publish")
    needs = [f for f in facts["facts"] if f["status"] == "NEED"]
    dec = [f for f in facts["facts"] if f["status"] == "declined"]
    page_needs = [n for spec in kit.get("pages", []) for n in spec.get("needs", [])]
    all_needs = [f.get("need", "") for f in needs] + page_needs
    print(f"SUMMARY 3: {len(all_needs)} NEED item(s){': ' + '; '.join(all_needs) if all_needs else ''}; {len(dec)} declined")
    print(f"SUMMARY 5: next test on or after {F(retest)}")
    print("SECTIONS: 1 Read first, 2 Can assistants reach you?, 3 Your buyer questions, 4 How to run the test, 5 What to publish, 6 Fact register, "
          "7 Machine-readable files, 8 Beyond your own pages, 9 Results and what to do next, 10 What this did not check")
    return 0


if __name__ == "__main__":
    sys.exit(main())
