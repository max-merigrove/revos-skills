#!/usr/bin/env python3
"""Build the founder's files: the language bank (.docx plus a CSV twin and the scrubbed sources), or the collection sheet.

Usage:
  python3 scripts/build_docx.py bank  --run <run folder> <bank.json> --out <output folder>
  python3 scripts/build_docx.py sheet --run <run folder> <sheet.json> --out <output folder>

bank: runs check_bank.py first; on any PROBLEM nothing is written and the problems are printed (exit 1).
Otherwise writes <out>/buyer-language-<business>-<date>/ with
  <business>-buyer-language-bank-<date>.docx   (Start here, The phrases to use first, Clusters ranked,
      What stops them and what they use instead, Their vocabulary, What changed since last time (return runs),
      What you did not hear, Sources and checks, All phrases)
  buyer-language-<business>-<date>.csv          one row per phrase
  sources/S-nn-<type>.txt                       the scrubbed text every phrase can be re-checked against
and prints SUMMARY lines for the five-line chat reply.
sheet: checks the sheet, then writes <out>/collection-sheet-<business>-<date>.docx (what was heard so far, if anything,
unranked; where to look; what to copy; how to paste it back).
Paper size follows the founder's country (Letter for the US, Canada and a few others; A4 elsewhere). Design rule:
no rules, no borders, no boxes; structure is carried by space, size and weight. The document property
"Made with Merigrove Buyer Language Miner" is set; nothing is added to the page. Standard library only. No network.
"""
import argparse
import os
import re
import shutil
import signal
import sys
import zipfile
from datetime import date, datetime, timezone
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ledger import stop, load_json, load_ledger, counted, show_date, norm, words, phrase_in, slug  # noqa: E402
from rank import write_csv, ANGLE_TYPES, TAGS  # noqa: E402
from check_bank import check as check_bank, quotes_in, outside_quotes, pii_hits, LONG_DIGITS  # noqa: E402
from check_copy import check_text, DASHES  # noqa: E402

PAPER = {"A4": (11906, 16838), "Letter": (12240, 15840)}
FONT = "Calibri"
INK, SOFT = "111111", "666666"
CREDIT = "Made with Merigrove Buyer Language Miner"
QO, QC = "\u201c", "\u201d"

L10N = {
    "en": {
        "title": "{b}: what your buyers say", "sub": "Buyer language bank, built {d}",
        "start": "Start here", "built": "Built from {q} quoted across {s} sources ({t}), dated {first} to {last}; {r} read in all. Window: the {w} days to {today}; the last {f} days are marked fresh.",
        "built_nodates": "Built from {q} quoted across {s} sources ({t}); {r} read in all. Window: the {w} days to {today}; the last {f} days are marked fresh.",
        "tier_full": "This is a full bank: {q} quoted across {n} source types, over the floor of 15 voices across two source types. The tier counts only people with at least one exact phrase in this bank.",
        "tier_starter": "This is a starter bank: {q} quoted is over the floor of 5 but under 15 across two source types, so read it as a first look. At most five clusters are ranked. The tier counts only people with at least one exact phrase in this bank.",
        "floors": "The floors (5 and 15 voices, 3 voices to rank a cluster) and the score weights are working defaults, not research findings. People who do this work for a living collect far more before they rely on a pattern.",
        "first3": "Do these three things first", "decide": "Needs your decision", "decide_none": "Nothing.",
        "evidence": "What this is good evidence for: the words buyers use and whether a pain keeps coming up. It is not evidence of how many people in your market feel it, of what they would pay, or of whether what they say is true. A voice is one person, however many times they posted.",
        "rules": "Before you reuse any of these words in public, check the terms of the sites you copied them from and the privacy rules where you and these people are. No quote here is a testimonial: never attribute one to a person or present it as a review of you.",
        "top": "The phrases to use first", "top_cols": ["#", "Phrase, exactly as written", "Tag", "Cluster", "Cluster voices", "Said", "ID"],
        "clusters": "Clusters, ranked", "cl_meta": "Mostly {dom} ({mix}). {v} voices, {st} source types ({types}), {fr} of {v} in the last {f} days, intensity {i} of 3, score {sc} of 100.",
        "means": "What it means", "ad": "Ad angle", "post": "Post idea", "lm": "Lead magnet topic",
        "buying_reason": "Buying reason", "type": "Angle type", "headline": "Headline", "need": "Before you run it",
        "draft": "Ready to run", "d_headline": "Headline", "d_text": "Primary text", "d_cta": "Call to action", "d_facts": "Rests on what you told me",
        "ads": "Ads to run", "ads_intro": "Written in your buyers' words without quoting anyone, and resting only on what you told me. The evidence under each ad comes from this bank; the quoted line is for you, not for the ad.",
        "ad_ev": "Evidence: {v} of the {q} voices quoted, across {t} source types; {f} of them in the last {d} days. Strongest line: ",
        "ad_closed": " (closed group: evidence only)", "ad_sharpen": "To sharpen it", "ad_visual": "What to show",
        "with_ads": "Put with the ads", "with_intro": "Answers to the questions these buyers ask before they book, in your words, for the pinned comment or the page the ads link to.",
        "stops_count": "{name}: {o} of its {v} voices raised an objection or named an alternative",
        "opener": "Opening line", "show": "What to show or tell", "proof": "Proof", "ltitle": "Working title", "format": "Format", "next_q": "The question it leaves for your offer",
        "emerging": "Emerging, not ranked", "emerging_intro": "Two voices each. Watch these; collect more before you build on them.",
        "once": "Heard once", "once_intro": "One voice each. Held back from ranking; useful as wording, not as evidence of a pattern.",
        "held": "Established but over the cap", "stops": "What stops them and what they use instead",
        "stops_intro": "Objections and alternatives, in the order of their clusters, with what each needs and where it belongs.",
        "needs": "Needs", "where": "Where", "none_heard": "No objections or alternatives were heard.", "voc": "Their vocabulary", "voc_intro": "Words buyers use for the category, the job and the alternatives, counted by distinct voices.",
        "voc_cols": ["Their word", "Voices", "Your word, where it differs"], "voc_once": "Also used by one voice each: {t}.",
        "changed": "What changed since last time", "changed_intro": "Compared with your bank from {d}.",
        "ch_cols": ["Cluster", "Change", "Voices before", "Voices now", "New phrases"], "retired": "Now outside the window (kept in the CSV, no longer counted): {ids}.",
        "status": {"new": "new", "rising": "rising", "faded": "faded", "steady": "steady"},
        "not_heard": "What you did not hear", "thin": "Too thin to rank: {names}.", "refused": "Could not read: {u} ({r}).",
        "sampling": "Who is missing from any sample like this: buyers who never post or review, quiet happy clients, and anyone outside the places these came from. Reviews of a competitor describe that competitor's customers, who may not be yours.",
        "next": "Collect next: {s}. Search: {q}",
        "sources": "Sources and checks", "src_cols": ["ID", "Source", "Type", "Origin", "Arrived", "Items", "Voices", "Dates"],
        "bias": {"review": "Reviewers skew to the very pleased and the very annoyed.", "forum": "Forum posters skew vocal and problem focused.",
                 "social": "Comments come from people already following the topic.", "email": "Your own enquiries: closest to the people you sell to.",
                 "call": "Your own calls: closest to the people you sell to.", "survey": "Survey answers: shaped by the questions asked.",
                 "dm": "Your own messages: closest to the people you sell to.", "other": "", "previous": "From your last bank, checked then."},
        "checks": "Checks",
        "c_verified": "Quotes: {n} of {n} phrases found word for word in the saved sources by script; none reworded, joined or shortened past a \"not\".",
        "c_voices": "Voices: {v} read and {q} quoted, counted as people, not mentions ({items} items read); repeat posters counted once{anon}.",
        "c_anon": "; {a} items had no author shown and each counts as its own voice, so two of them could be one person",
        "c_dups": "Suspected duplicates: {d}; each counted once.", "c_dups0": "Suspected duplicates: none found by script (near-identical text, a shared sentence within three days, or a shared phone number, email or link across different voices).",
        "c_shares": "Shares a sentence with another voice, more than three days apart, so both are counted: {d}. Tell me if you know they are one person.",
        "c_closed": "{s} came from a closed group you belong to and pasted yourself. Its words shape your own copy; they are never quoted in public, and nothing here should be screenshotted from it.",
        "c_burst": "Bursts: {s} has {n} of {o} dated items on {d}; read those with care.",
        "c_window": "Window: {o} items fall outside the {w} days; they are listed in the CSV marked outside window and are never ranked. {u} undated items are counted but earn no fresh points.",
        "c_pii": "Personal data: {e}, {p}, {l} and every handle or author name removed before anything was saved; your original paste was not saved.",
        "units": {"email": ["email address", "email addresses"], "phone": ["phone number", "phone numbers"], "link": ["link", "links"]},
        "paste_default": "Paste it as it comes, one source at a time, with a line saying where it came from (for example: Google reviews of a competitor). Names and contact details are fine; I remove them.",
        "c_redact": "Names removed at your request: {n}.", "c_excl": "Excluded: {r} ({n} items).",
        "c_model": "Text addressed to an AI, quoted here as data and not followed or counted:", "c_model0": "No text addressed to an AI was found.",
        "c_lang_en": "Writing checks (no dashes, no filler, no claims about \"the market\", no percentages) ran on everything written for you.",
        "c_lang_other": "The bank is not in English, so the English-only writing checks did not run. Quote verification, voice counts, the window, personal data removal and the dash check did.",
        "all": "All phrases", "all_cols": ["ID", "Phrase", "Cluster", "Voice", "Date", "In window"],
        "tags": {"pain": "pain", "trigger": "trigger", "objection": "objection", "outcome": "outcome", "alternative": "alternative"},
        "tag_heads": {"pain": "Pain", "trigger": "Trigger", "objection": "Objection", "outcome": "Outcome", "alternative": "Alternative"},
        "window_vals": {"yes": "yes", "no": "outside window", "unknown": "undated"}, "undated": "undated",
        "voices_word": "voices", "voice_word": "voice",
        "sheet_title": "{b}: where to find what your buyers say", "sheet_sub": "Collection sheet, {d}",
        "sheet_intro": "Copy what buyers wrote, as it comes, and paste it back into the chat. I clean it, remove names and contact details, and send nothing anywhere.",
        "so_far": "What you have so far", "so_far_intro": "{v} voices so far, under the floor of 5 for a ranked bank. These are verified word for word but not ranked or counted as patterns.",
        "own": "Start with what you already have", "public": "Then these public sources", "s_search": "Search", "s_copy": "Copy", "s_many": "How many", "s_note": "Note",
        "paste": "How to paste it back", "listen": "What to listen for", "listen_note": "Hypotheses, not buyer language. None of these is a quote, and none will be counted until a buyer says it.",
        "floor_line": "With 5 voices I can build a starter bank; with 15 across at least two kinds of source, a full one.",
    },
    "de": {
        "title": "{b}: was deine Kundinnen und Kunden sagen", "sub": "Sprachbank, erstellt am {d}",
        "start": "Hier anfangen", "built": "Aus {q} zitiert in {s} Quellen ({t}), datiert vom {first} bis {last}; insgesamt {r} gelesen. Zeitraum: die {w} Tage bis {today}; die letzten {f} Tage gelten als frisch.",
        "built_nodates": "Aus {q} zitiert in {s} Quellen ({t}); insgesamt {r} gelesen. Zeitraum: die {w} Tage bis {today}; die letzten {f} Tage gelten als frisch.",
        "tier_full": "Das ist eine volle Sprachbank: {q} zitiert aus {n} Quellenarten, über der Schwelle von 15 Stimmen aus zwei Quellenarten. Gezählt werden nur Personen mit mindestens einem wörtlichen Satz in dieser Sprachbank.",
        "tier_starter": "Das ist eine Start-Sprachbank: {q} zitiert liegt über der Schwelle von 5, aber unter 15 aus zwei Quellenarten. Lies sie als ersten Eindruck. Höchstens fünf Gruppen werden gerankt. Gezählt werden nur Personen mit mindestens einem wörtlichen Satz in dieser Sprachbank.",
        "floors": "Die Schwellen (5 und 15 Stimmen, 3 Stimmen für eine gerankte Gruppe) und die Gewichte der Punktzahl sind Arbeitswerte, keine Forschungsergebnisse. Wer das beruflich macht, sammelt deutlich mehr, bevor er sich auf ein Muster verlässt.",
        "first3": "Diese drei Dinge zuerst", "decide": "Braucht deine Entscheidung", "decide_none": "Nichts.",
        "evidence": "Wofür das ein guter Beleg ist: für die Worte, die Kundinnen und Kunden benutzen, und dafür, ob ein Problem immer wieder auftaucht. Es ist kein Beleg dafür, wie viele Menschen in deinem Markt so denken, was sie zahlen würden oder ob stimmt, was sie sagen. Eine Stimme ist eine Person, egal wie oft sie geschrieben hat.",
        "rules": "Bevor du diese Worte öffentlich verwendest, prüfe die Nutzungsbedingungen der Seiten, von denen du sie kopiert hast, und die Datenschutzregeln dort, wo du und diese Menschen seid. Kein Zitat hier ist ein Testimonial: Schreibe es nie einer Person zu und gib es nie als Bewertung von dir aus.",
        "top": "Die Sätze für den Anfang", "top_cols": ["#", "Satz, genau wie geschrieben", "Art", "Gruppe", "Stimmen der Gruppe", "Datum", "ID"],
        "clusters": "Gruppen, gerankt", "cl_meta": "Vor allem {dom} ({mix}). {v} Stimmen, {st} Quellenarten ({types}), {fr} von {v} in den letzten {f} Tagen, Intensität {i} von 3, Punktzahl {sc} von 100.",
        "means": "Was es bedeutet", "ad": "Anzeigen-Ansatz", "post": "Idee für einen Beitrag", "lm": "Thema für einen Lead-Magneten",
        "buying_reason": "Kaufgrund", "type": "Art des Ansatzes", "headline": "Überschrift", "need": "Bevor du es schaltest",
        "draft": "Bereit zum Schalten", "d_headline": "Überschrift", "d_text": "Anzeigentext", "d_cta": "Handlungsaufforderung", "d_facts": "Beruht auf dem, was du mir gesagt hast",
        "ads": "Anzeigen zum Schalten", "ads_intro": "In den Worten deiner Käufer geschrieben, ohne jemanden zu zitieren, und nur auf dem, was du mir gesagt hast. Die Belege unter jeder Anzeige stammen aus dieser Sammlung; das Zitat ist für dich, nicht für die Anzeige.",
        "ad_ev": "Belege: {v} von {q} zitierten Stimmen, aus {t} Quellenarten; {f} davon in den letzten {d} Tagen. Stärkster Satz: ",
        "ad_closed": " (geschlossene Gruppe: nur als Beleg)", "ad_sharpen": "Schärfer wird sie mit", "ad_visual": "Was zu zeigen ist",
        "with_ads": "Neben die Anzeigen", "with_intro": "Antworten auf die Fragen, die diese Käufer vor der Buchung stellen, in deinen Worten, für den angehefteten Kommentar oder die Zielseite.",
        "stops_count": "{name}: {o} von {v} Stimmen nannten einen Einwand oder eine Alternative",
        "opener": "Erster Satz", "show": "Was du zeigst oder erzählst", "proof": "Beleg", "ltitle": "Arbeitstitel", "format": "Format", "next_q": "Die Frage, die er für dein Angebot offen lässt",
        "emerging": "Im Kommen, nicht gerankt", "emerging_intro": "Je zwei Stimmen. Beobachten und mehr sammeln, bevor du darauf baust.",
        "once": "Einmal gehört", "once_intro": "Je eine Stimme. Nicht gerankt; nützlich als Formulierung, nicht als Beleg für ein Muster.",
        "held": "Etabliert, aber über der Obergrenze", "stops": "Was sie zögern lässt und was sie stattdessen nutzen",
        "stops_intro": "Einwände und Alternativen in der Reihenfolge ihrer Gruppen, mit dem, was jeweils gebraucht wird, und wo es hingehört.",
        "needs": "Braucht", "where": "Wo", "none_heard": "Es wurden keine Einwände oder Alternativen gehört.", "voc": "Ihr Wortschatz", "voc_intro": "Worte, die Kundinnen und Kunden für das Thema, die Aufgabe und die Alternativen benutzen, gezählt nach Stimmen.",
        "voc_cols": ["Ihr Wort", "Stimmen", "Dein Wort, wo es anders ist"], "voc_once": "Außerdem von je einer Stimme benutzt: {t}.",
        "changed": "Was sich seit dem letzten Mal geändert hat", "changed_intro": "Im Vergleich mit deiner Sprachbank vom {d}.",
        "ch_cols": ["Gruppe", "Änderung", "Stimmen vorher", "Stimmen jetzt", "Neue Sätze"], "retired": "Jetzt außerhalb des Zeitraums (in der CSV, nicht mehr gezählt): {ids}.",
        "status": {"new": "neu", "rising": "steigend", "faded": "verblasst", "steady": "gleich"},
        "not_heard": "Was du nicht gehört hast", "thin": "Zu dünn zum Ranken: {names}.", "refused": "Nicht lesbar: {u} ({r}).",
        "sampling": "Wer in einer Auswahl wie dieser fehlt: alle, die nie posten oder bewerten, stille zufriedene Kundschaft und alle außerhalb der Orte, aus denen das stammt. Bewertungen eines Mitbewerbers beschreiben dessen Kundschaft, nicht unbedingt deine.",
        "next": "Als Nächstes sammeln: {s}. Suche: {q}",
        "sources": "Quellen und Prüfungen", "src_cols": ["ID", "Quelle", "Art", "Herkunft", "Eingang", "Einträge", "Stimmen", "Daten"],
        "bias": {"review": "Bewertungen kommen vor allem von sehr Zufriedenen und sehr Verärgerten.", "forum": "In Foren schreiben vor allem Lautere mit Problemen.",
                 "social": "Kommentare kommen von Menschen, die dem Thema schon folgen.", "email": "Deine eigenen Anfragen: am nächsten an deiner Kundschaft.",
                 "call": "Deine eigenen Gespräche: am nächsten an deiner Kundschaft.", "survey": "Umfrageantworten: geprägt von den gestellten Fragen.",
                 "dm": "Deine eigenen Nachrichten: am nächsten an deiner Kundschaft.", "other": "", "previous": "Aus deiner letzten Sprachbank, damals geprüft."},
        "checks": "Prüfungen",
        "c_verified": "Zitate: {n} von {n} Sätzen per Skript wörtlich in den gespeicherten Quellen gefunden; nichts umformuliert, zusammengefügt oder um ein „nicht“ gekürzt.",
        "c_voices": "Stimmen: {v} gelesen und {q} zitiert, gezählt als Personen, nicht Erwähnungen ({items} Einträge gelesen); wer mehrfach schrieb, zählt einmal{anon}.",
        "c_anon": "; {a} Einträge ohne sichtbaren Namen zählen jeweils als eigene Stimme, zwei davon könnten also eine Person sein",
        "c_dups": "Vermutete Duplikate: {d}; jeweils einmal gezählt.", "c_dups0": "Vermutete Duplikate: per Skript keine gefunden (fast gleicher Text, ein gleicher Satz innerhalb von drei Tagen oder dieselbe Telefonnummer, E-Mail oder derselbe Link unter verschiedenen Stimmen).",
        "c_shares": "Teilt einen Satz mit einer anderen Stimme, mehr als drei Tage auseinander, daher beide gezählt: {d}. Sag mir, wenn du weißt, dass es eine Person ist.",
        "c_closed": "{s} stammt aus einer geschlossenen Gruppe, in der du Mitglied bist, und wurde von dir eingefügt. Die Worte prägen deine eigenen Texte; öffentlich zitiert werden sie nie, und nichts davon sollte als Screenshot verwendet werden.",
        "c_burst": "Häufung: {s} hat {n} von {o} datierten Einträgen am {d}; diese mit Vorsicht lesen.",
        "c_window": "Zeitraum: {o} Einträge liegen außerhalb der {w} Tage; sie stehen in der CSV als außerhalb des Zeitraums und werden nie gerankt. {u} Einträge ohne Datum werden gezählt, bekommen aber keine Frische-Punkte.",
        "c_pii": "Persönliche Daten: {e}, {p}, {l} und alle Namen und Profilnamen wurden vor dem Speichern entfernt; dein ursprünglicher Text wurde nicht gespeichert.",
        "units": {"email": ["E-Mail-Adresse", "E-Mail-Adressen"], "phone": ["Telefonnummer", "Telefonnummern"], "link": ["Link", "Links"]},
        "paste_default": "Füge es so ein, wie es kommt, eine Quelle nach der anderen, mit einer Zeile, woher es stammt (zum Beispiel: Google-Bewertungen eines Mitbewerbers). Namen und Kontaktdaten sind kein Problem; ich entferne sie.",
        "c_redact": "Auf deinen Wunsch entfernte Namen: {n}.", "c_excl": "Ausgeschlossen: {r} ({n} Einträge).",
        "c_model": "Text, der sich an eine KI richtete, hier als Daten zitiert und weder befolgt noch gezählt:", "c_model0": "Kein Text richtete sich an eine KI.",
        "c_lang_en": "", "c_lang_other": "Die Sprachbank ist auf Deutsch, daher liefen die nur englischen Schreibprüfungen nicht. Zitatprüfung, Stimmenzählung, Zeitraum, Entfernen persönlicher Daten und die Prüfung auf Gedankenstriche liefen.",
        "all": "Alle Sätze", "all_cols": ["ID", "Satz", "Gruppe", "Stimme", "Datum", "Im Zeitraum"],
        "tags": {"pain": "Schmerz", "trigger": "Auslöser", "objection": "Einwand", "outcome": "Ergebnis", "alternative": "Alternative"},
        "tag_heads": {"pain": "Schmerz", "trigger": "Auslöser", "objection": "Einwand", "outcome": "Ergebnis", "alternative": "Alternative"},
        "window_vals": {"yes": "ja", "no": "außerhalb", "unknown": "ohne Datum"}, "undated": "ohne Datum",
        "voices_word": "Stimmen", "voice_word": "Stimme",
        "sheet_title": "{b}: wo du findest, was deine Kundschaft sagt", "sheet_sub": "Sammelbogen, {d}",
        "sheet_intro": "Kopiere, was Kundinnen und Kunden geschrieben haben, so wie es ist, und füge es in den Chat ein. Ich bereinige es, entferne Namen und Kontaktdaten und schicke nichts irgendwohin.",
        "so_far": "Was du bisher hast", "so_far_intro": "Bisher {v} Stimmen, unter der Schwelle von 5 für eine gerankte Sprachbank. Wörtlich geprüft, aber nicht gerankt und nicht als Muster gezählt.",
        "own": "Fang mit dem an, was du schon hast", "public": "Dann diese öffentlichen Quellen", "s_search": "Suche", "s_copy": "Kopieren", "s_many": "Wie viele", "s_note": "Hinweis",
        "paste": "So fügst du es ein", "listen": "Worauf du achten kannst", "listen_note": "Vermutungen, keine Kundensprache. Nichts davon ist ein Zitat, und nichts wird gezählt, bevor jemand es sagt.",
        "floor_line": "Mit 5 Stimmen baue ich eine Start-Sprachbank, mit 15 aus mindestens zwei Quellenarten eine volle.",
    },
}
ANGLE_DE = {"name-the-pain": "Den Schmerz benennen", "cost-of-waiting": "Was Warten kostet (arbeitet mit Angst)", "the-moment": "Der Moment, in dem es kippte",
            "answer-the-doubt": "Den Zweifel beantworten", "the-after": "Das Danach", "switch-story": "Die Wechselgeschichte"}


def r(text, bold=False, italic=False, size=None, colour=None):
    p = []
    if bold:
        p.append("<w:b/>")
    if italic:
        p.append("<w:i/>")
    if colour:
        p.append(f'<w:color w:val="{colour}"/>')
    if size:
        p.append(f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>')
    rpr = f"<w:rPr>{''.join(p)}</w:rPr>" if p else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{escape(str(text))}</w:t></w:r>'


def para(runs, before=0, after=120, keep=False, indent=0, page_break=False):
    ppr = []
    if page_break:
        ppr.append("<w:pageBreakBefore/>")
    if keep:
        ppr.append("<w:keepNext/>")
    ppr.append(f'<w:spacing w:before="{before}" w:after="{after}"/>')
    if indent:
        ppr.append(f'<w:ind w:left="{indent}"/>')
    return f"<w:p><w:pPr>{''.join(ppr)}</w:pPr>{runs}</w:p>"


def h1(text, page_break=True):
    return para(r(text, bold=True, size=34, colour=INK), after=260, keep=True, page_break=page_break)


def h2(text, before=340):
    return para(r(text, bold=True, size=25, colour=INK), before=before, after=100, keep=True)


def h3(text, before=220):
    return para(r(text, bold=True, size=21, colour=INK), before=before, after=60, keep=True)


def body(text, size=21, colour=None, italic=False, after=120, indent=0, keep=False):
    return para(r(text, size=size, colour=colour, italic=italic), after=after, indent=indent, keep=keep)


def labelled(label, text, indent=0):
    return para(r(label + ": ", bold=True, size=20) + r(text, size=20), after=60, indent=indent)


def bullet(text, indent=360):
    return para(r("•  ", colour=SOFT) + r(text), after=80, indent=indent)


def table(rows, widths, size=18):
    nb = "".join(f'<w:{s} w:val="nil"/>' for s in ("top", "left", "bottom", "right", "insideH", "insideV"))
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    out = [f'<w:tbl><w:tblPr><w:tblW w:w="{sum(widths)}" w:type="dxa"/><w:tblBorders>{nb}</w:tblBorders>'
           '<w:tblLayout w:type="fixed"/><w:tblCellMar><w:top w:w="50" w:type="dxa"/><w:left w:w="0" w:type="dxa"/>'
           '<w:bottom w:w="50" w:type="dxa"/><w:right w:w="160" w:type="dxa"/></w:tblCellMar><w:tblLook w:val="0000"/></w:tblPr>'
           f"<w:tblGrid>{grid}</w:tblGrid>"]
    for i, row in enumerate(rows):
        cells = []
        for c, w in zip(row, widths):
            txt = r(c, bold=(i == 0), size=size, colour=(SOFT if i == 0 else INK))
            cells.append(f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/></w:tcPr>{para(txt, after=0)}</w:tc>')
        hdr = "<w:trPr><w:tblHeader/><w:cantSplit/></w:trPr>" if i == 0 else "<w:trPr><w:cantSplit/></w:trPr>"
        out.append(f"<w:tr>{hdr}{''.join(cells)}</w:tr>")
    out.append("</w:tbl>")
    return "".join(out) + para("", after=120)


def write_docx(path, body_xml, paper, title, lang):
    w, h = PAPER[paper]
    langtag = {"de": "de-DE", "fr": "fr-FR", "es": "es-ES"}.get(lang, "en-US" if paper == "Letter" else "en-GB")
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
           'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
           f'<w:body>{body_xml}<w:sectPr><w:pgSz w:w="{w}" w:h="{h}"/>'
           '<w:pgMar w:top="1250" w:right="1200" w:bottom="1250" w:left="1200" w:header="500" w:footer="500" w:gutter="0"/>'
           '</w:sectPr></w:body></w:document>')
    styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
              f'<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:cs="{FONT}" w:eastAsia="{FONT}"/>'
              f'<w:sz w:val="21"/><w:szCs w:val="21"/><w:lang w:val="{langtag}"/></w:rPr></w:rPrDefault>'
              '<w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>'
              f'<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:color w:val="{INK}"/></w:rPr></w:style>'
              '</w:styles>')
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'<dc:title>{escape(title)}</dc:title><dc:creator>{CREDIT}</dc:creator>'
            f'<dc:description>{CREDIT}</dc:description><cp:keywords>buyer language</cp:keywords>'
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
            f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified></cp:coreProperties>')
    app = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
           f'<Application>{CREDIT}</Application></Properties>')
    ctypes = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
              '<Default Extension="xml" ContentType="application/xml"/>'
              '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
              '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
              '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
              '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
              '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
            '</Relationships>')
    doc_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
                '</Relationships>')
    tmp = path + ".part"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ctypes)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        z.writestr("docProps/core.xml", core)
        z.writestr("docProps/app.xml", app)
    os.replace(tmp, path)


def labels(B):
    lang = B.get("lang", "en")
    lab = dict(L10N["en"])
    lab.update(L10N.get(lang, {}))
    lab.update(B.get("labels") or {})
    return lang, lab


def nw(n, lab, key=None, one=None, many=None):
    """'1 voice', '3 voices' in the document's language."""
    if key:
        one, many = lab["units"][key] if key in lab.get("units", {}) else L10N["en"]["units"][key]
    one = one or lab["voice_word"]
    many = many or lab["voices_word"]
    return f"{n} {one if n == 1 else many}"


def angle_name(t, lang):
    return ANGLE_DE.get(t, t) if lang == "de" else ANGLE_TYPES.get(t, t)


def build_bank(L, B, R, out_root):
    global QO, QC
    lang, lab = labels(B)
    QO, QC = ("\u201e", "\u201c") if lang == "de" else ("\u201c", "\u201d")
    order = L["date_order"]
    sd = lambda d: show_date(d, order, lang)  # noqa: E731
    S = R["stats"]
    Q = R["quoted"]
    pm = R["phrases"]
    cl = {c["id"]: c for c in R["clusters"]}
    bcl = {c["id"]: c for c in B.get("clusters", [])}
    today = L["today"]
    counted_items = [i for i in L["items"] if counted(i)]
    q_items = [p["_item"] for p in pm.values() if "_item" in p and counted(p["_item"])]
    dates = sorted(i["date"] for i in q_items if i["date"])
    tlabel = lambda t: lab["tags"].get(t, t)  # noqa: E731
    srcs = [s for s in L["sources"]]
    used_src = {i["source"] for i in counted_items}
    x = []
    x.append(para(r(lab["title"].format(b=L["business"]), bold=True, size=40), after=80))
    x.append(body(lab["sub"].format(d=sd(today)), colour=SOFT, after=360))
    ads = [cid for cid in R["ranked"] if (bcl.get(cid) or {}).get("ad_draft")]
    if ads:
        x.append(h1(lab["ads"], page_break=False))
        x.append(body(lab["ads_intro"], colour=SOFT, size=19))
        closed = {s_["id"] for s_ in L["sources"] if s_.get("closed")}
        for n, cid in enumerate(ads, 1):
            c, bc = cl[cid], bcl[cid]
            dr = bc["ad_draft"]
            x.append(h2(f"{n}. {bc.get('name', cid)}", before=200 if n == 1 else 360))
            x.append(labelled(lab["d_headline"], dr.get("headline", ""), 360))
            x.append(labelled(lab["d_text"], dr.get("primary_text", ""), 360))
            x.append(labelled(lab["d_cta"], dr.get("cta", ""), 360))
            if dr.get("facts"):
                x.append(labelled(lab["d_facts"], "; ".join(dr["facts"]), 360))
            if dr.get("visual"):
                x.append(labelled(lab["ad_visual"], dr["visual"], 360))
            if dr.get("sharpen"):
                x.append(labelled(lab["ad_sharpen"], dr["sharpen"], 360))
            ps = sorted([pm[q] for q in c["counted_phrases"]], key=lambda p: (p["_item"]["source"] in closed, -p["intensity"], p["id"]))
            ev = lab["ad_ev"].format(v=c["voices"], q=Q["voices"], t=len(c["source_types"]), f=c["fresh_voices"], d=L["fresh_days"])
            if ps:
                p0 = ps[0]
                x.append(para(r(ev, size=19, colour=SOFT) + r(QO + p0["text"] + QC, italic=True, size=19)
                              + r(f"   {p0['id']}, {p0['_item']['source_type']}" + (lab["ad_closed"] if p0["_item"]["source"] in closed else ""), size=17, colour=SOFT),
                              after=80, indent=360))
        wl = [w_ for w_ in (B.get("with_ads") or []) if isinstance(w_, dict) and w_.get("line")]
        if wl:
            x.append(h2(lab["with_ads"], before=360))
            x.append(body(lab["with_intro"], colour=SOFT, size=19))
            for w_ in wl:
                x.append(bullet(f"{w_['line']} ({w_.get('where', '')})"))
    x.append(h2(lab["start"], before=0 if not ads else 420))
    types_txt = ", ".join(Q["source_types"])
    if dates:
        x.append(body(lab["built"].format(q=nw(Q["voices"], lab), r=nw(S["voices"], lab), s=Q["sources"], t=types_txt, first=sd(dates[0]), last=sd(dates[-1]),
                                          w=L["window_days"], today=sd(today), f=L["fresh_days"])))
    else:
        x.append(body(lab["built_nodates"].format(q=nw(Q["voices"], lab), r=nw(S["voices"], lab), s=Q["sources"], t=types_txt, w=L["window_days"],
                                                  today=sd(today), f=L["fresh_days"])))
    x.append(body(lab["tier_full" if R["bank_tier"] == "full" else "tier_starter"].format(q=nw(Q["voices"], lab), n=len(Q["source_types"]))))
    x.append(body(lab["floors"], colour=SOFT, size=19))
    x.append(h3(lab["first3"]))
    for i, t in enumerate(B.get("first_three", []), 1):
        x.append(para(r(f"{i}.  ", bold=True) + r(t), after=80, indent=360))
    x.append(h3(lab["decide"]))
    dec = list(B.get("decisions") or [])
    if dec:
        for t in dec:
            x.append(bullet(t))
    else:
        x.append(body(lab["decide_none"]))
    x.append(body(lab["evidence"], size=19, colour=SOFT))
    x.append(body(lab["rules"], size=19, colour=SOFT))
    # twelve phrases
    x.append(h1(lab["top"]))
    rows = [lab["top_cols"]]
    for n, t in enumerate(R["top12"], 1):
        p = pm[t["id"]]
        c = cl[t["cluster"]]
        it = p["_item"]
        rows.append([str(n), p["text"], tlabel(p["tag"]), bcl.get(c["id"], c).get("name", c["id"]), str(c["voices"]), sd(it["date"]) if it["date"] else lab["undated"], p["id"]])
    x.append(table(rows, [380, 4100, 1050, 1900, 750, 1200, 700]))
    # clusters
    x.append(h1(lab["clusters"]))
    for rank, cid in enumerate(R["ranked"], 1):
        c, bc = cl[cid], bcl.get(cid, {})
        x.append(h2(f"{rank}. {bc.get('name', cid)}", before=200 if rank == 1 else 420))
        mix = ", ".join(f"{n} {tlabel(t)}" for t, n in c["tag_mix"].items())
        x.append(body(lab["cl_meta"].format(dom=tlabel(c["dominant_tag"]), mix=mix, v=c["voices"], st=len(c["source_types"]), types=", ".join(c["source_types"]),
                                            fr=c["fresh_voices"], f=L["fresh_days"], i=f"{c['mean_intensity']:.1f}".replace(".", "," if lang == "de" else "."), sc=c["score"]),
                      colour=SOFT, size=19))
        # quotes: highest intensity, one per voice first
        cps = sorted([pm[q] for q in c["counted_phrases"]], key=lambda p: (-p["intensity"], p["id"]))
        chosen, seen_v = [], set()
        for p in cps:
            if p["_item"]["voice"] not in seen_v and len(chosen) < 5:
                chosen.append(p)
                seen_v.add(p["_item"]["voice"])
        for p in cps:
            if len(chosen) < 3 and p not in chosen:
                chosen.append(p)
        for p in chosen:
            it = p["_item"]
            x.append(para(r(QO + p["text"]+ QC, italic=True) + r(f"   {p['id']}, {it['voice']}, {it['source_type']}, {sd(it['date']) if it['date'] else lab['undated']}", size=17, colour=SOFT),
                          after=60, indent=360))
        x.append(labelled(lab["means"], bc.get("means", "")))
        aa, pi, lm = bc.get("ad_angle", {}), bc.get("post_idea", {}), bc.get("lead_magnet", {})
        x.append(h3(lab["ad"]))
        x.append(labelled(lab["headline"], aa.get("headline", ""), 360))
        x.append(labelled(lab["buying_reason"], aa.get("buying_reason", ""), 360))
        x.append(labelled(lab["type"], angle_name(aa.get("type", ""), lang), 360))
        if aa.get("need"):
            x.append(labelled(lab["need"], " ".join(aa["need"]), 360))
        dr = bc.get("ad_draft") or {}
        if dr:
            x.append(h3(lab["draft"]))
            x.append(labelled(lab["d_headline"], dr.get("headline", ""), 360))
            x.append(labelled(lab["d_text"], dr.get("primary_text", ""), 360))
            x.append(labelled(lab["d_cta"], dr.get("cta", ""), 360))
            if dr.get("facts"):
                x.append(labelled(lab["d_facts"], "; ".join(dr["facts"]), 360))
        x.append(h3(lab["post"]))
        x.append(labelled(lab["opener"], pi.get("opener", ""), 360))
        x.append(labelled(lab["show"], pi.get("show", ""), 360))
        x.append(labelled(lab["proof"], pi.get("proof", ""), 360))
        x.append(h3(lab["lm"]))
        x.append(labelled(lab["ltitle"], lm.get("title", ""), 360))
        x.append(labelled(lab["format"], lm.get("format", ""), 360))
        x.append(labelled(lab["next_q"], lm.get("next_question", ""), 360))
    held = [c for c in R["clusters"] if c["tier"] == "established" and c["id"] not in R["ranked"]]
    if held:
        x.append(h2(lab["held"]))
        for c in held:
            x.append(bullet(f"{bcl.get(c['id'], c).get('name', c['id'])}: {nw(c['voices'], lab)} ({c.get('held_reason', '')})"))
    em = [c for c in R["clusters"] if c["tier"] == "emerging"]
    if em:
        x.append(h2(lab["emerging"]))
        x.append(body(lab["emerging_intro"], colour=SOFT, size=19))
        for c in em:
            x.append(h3(f"{bcl.get(c['id'], c).get('name', c['id'])}: {nw(2, lab)}"))
            for q in c["counted_phrases"]:
                x.append(para(r(QO + pm[q]["text"]+ QC, italic=True) + r(f"   {q}, {pm[q]['_item']['voice']}", size=17, colour=SOFT), after=50, indent=360))
    once = [c for c in R["clusters"] if c["tier"] == "single"]
    if once:
        x.append(h2(lab["once"]))
        x.append(body(lab["once_intro"], colour=SOFT, size=19))
        for c in once:
            for q in c["counted_phrases"]:
                x.append(para(r(QO + pm[q]["text"]+ QC, italic=True) + r(f"   {q}, {tlabel(pm[q]['tag'])}", size=17, colour=SOFT), after=50, indent=360))
    # stops
    x.append(h1(lab["stops"]))
    x.append(body(lab["stops_intro"], colour=SOFT, size=19))
    order_ids = R["ranked"] + [c["id"] for c in R["clusters"] if c["id"] not in R["ranked"]]
    any_stop = False
    for cid in order_ids:
        c, bc = cl[cid], bcl.get(cid, {})
        obs = [pm[q] for q in c["counted_phrases"] if pm[q]["tag"] in ("objection", "alternative")]
        if not obs:
            continue
        any_stop = True
        x.append(h3(lab["stops_count"].format(name=bc.get("name", cid), o=len({p["_item"]["voice"] for p in obs}), v=c["voices"])))
        for p in obs:
            x.append(para(r(QO + p["text"]+ QC, italic=True) + r(f"   {tlabel(p['tag'])}, {p['id']}", size=17, colour=SOFT), after=50, indent=360))
        st = bc.get("stops") or {}
        if st:
            x.append(labelled(lab["needs"], st.get("answer", ""), 360))
            x.append(labelled(lab["where"], st.get("where", ""), 360))
    if not any_stop:
        x.append(body(lab["none_heard"]))
    # vocabulary
    x.append(h1(lab["voc"]))
    x.append(body(lab["voc_intro"], colour=SOFT, size=19))
    rows = [lab["voc_cols"]]
    vocab = sorted(B.get("vocabulary") or [], key=lambda v: -v.get("_voices", 0))
    for v in vocab:
        if v.get("_voices", 0) >= 2 or v.get("founder_term"):
            rows.append([v["term"], str(v.get("_voices", 0)), v.get("founder_term", "") if norm(v.get("founder_term", "")) != norm(v["term"]) else ""])
    if len(rows) > 1:
        x.append(table(rows, [3200, 1200, 5600]))
    once_terms = [v["term"] for v in vocab if v.get("_voices", 0) < 2 and not v.get("founder_term")]
    if once_terms:
        x.append(body(lab["voc_once"].format(t=", ".join(once_terms)), size=19, colour=SOFT))
    # changes
    if R["delta"]:
        x.append(h1(lab["changed"]))
        x.append(body(lab["changed_intro"].format(d=sd(L["previous_run"]) if L.get("previous_run") else "")))
        rows = [lab["ch_cols"]]
        for d in sorted(R["delta"], key=lambda d: ["rising", "new", "steady", "faded"].index(d["status"])):
            rows.append([f"{bcl.get(d['cluster'], {}).get('name') or d['name'] or d['cluster']} ({d['cluster']})", lab["status"][d["status"]], str(d["voices_before"]), str(d["voices_now"]), str(d["new_phrases"])])
        x.append(table(rows, [3800, 1400, 1500, 1500, 1500]))
        ret = [q for d in R["delta"] for q in d["retired_outside_window"]]
        if ret:
            x.append(body(lab["retired"].format(ids=", ".join(ret))))
    # not heard
    x.append(h1(lab["not_heard"]))
    for t in B.get("not_heard") or []:
        x.append(bullet(t))
    thin = [bcl.get(c["id"], c).get("name", c["id"]) for c in R["clusters"] if c["tier"] in ("emerging", "single")]
    if thin:
        x.append(bullet(lab["thin"].format(names="; ".join(thin))))
    for w in L.get("web", []):
        if w["result"] != "ok":
            x.append(bullet(lab["refused"].format(u=w["url"], r=w["result"] + (": " + w["reason"] if w.get("reason") else ""))))
    x.append(bullet(lab["sampling"]))
    nc = B.get("next_collect") or {}
    if nc:
        x.append(para(r(lab["next"].format(s=nc.get("source", ""), q=nc.get("search", "")), bold=True), before=120))
    # sources and checks
    x.append(h1(lab["sources"]))
    rows = [lab["src_cols"]]
    for s in srcs:
        its = [i for i in L["items"] if i["source"] == s["id"]]
        ds = sorted(i["date"] for i in its if i["date"])
        dr = f"{sd(ds[0])} to {sd(ds[-1])}" if len(ds) > 1 and ds[0] != ds[-1] else (sd(ds[0]) if ds else lab["undated"])
        if lang == "de" and len(ds) > 1 and ds[0] != ds[-1]:
            dr = f"{sd(ds[0])} bis {sd(ds[-1])}"
        rows.append([s["id"], s["label"] + ("  " + s["url"] if s.get("url") else ""), s["type"], s["origin"], s["arrived"], str(len(its)), str(len({i['voice'] for i in its})), dr])
    x.append(table(rows, [520, 3300, 900, 1100, 900, 700, 750, 1830], size=16))
    for t in sorted({s["type"] for s in srcs}):
        if lab["bias"].get(t):
            x.append(body(f"{t}: {lab['bias'][t]}", size=18, colour=SOFT, after=40))
    x.append(h3(lab["checks"]))
    n_ph = len([p for p in pm.values()])
    x.append(bullet(lab["c_verified"].format(n=n_ph)))
    anon = lab["c_anon"].format(a=S["anon"]) if S["anon"] else ""
    x.append(bullet(lab["c_voices"].format(v=S["voices"], q=Q["voices"], items=S["items"], anon=anon)))
    dups = [i for i in L["items"] if i.get("dup_of")]
    shares = [(i["id"], f.split()[-1]) for i in L["items"] if not i.get("dup_of") for f in i["flags"] if f.startswith("shares a sentence with")]
    if dups:
        x.append(bullet(lab["c_dups"].format(d="; ".join(f"{i['id']} matches {i['dup_of']}" if lang == "en" else f"{i['id']} gleicht {i['dup_of']}" for i in dups))))
    if shares:
        x.append(bullet(lab["c_shares"].format(d="; ".join(f"{a_} and {b_}" if lang == "en" else f"{a_} und {b_}" for a_, b_ in shares))))
    if not dups and not shares:
        x.append(bullet(lab["c_dups0"]))
    for b in L.get("bursts", []):
        x.append(bullet(lab["c_burst"].format(s=b["source"], n=b["items"], o=b["of"], d=sd(b["date"]))))
    x.append(bullet(lab["c_window"].format(o=S["outside"], w=L["window_days"], u=S["undated"])))
    sc = L["scrub"]
    x.append(bullet(lab["c_pii"].format(e=nw(sc["emails"], lab, "email"), p=nw(sc["phones"], lab, "phone"), l=nw(sc["links"], lab, "link"))))
    for s_ in srcs:
        if s_.get("closed"):
            short = re.split(r"\s+\(|\s+[-\u2013]\s+", s_["label"])[0].strip()
            short = short if len(short) <= 60 else short[:60].rsplit(" ", 1)[0]
            x.append(bullet(lab["c_closed"].format(s=f"{s_['id']} ({short})")))
    if L.get("redactions"):
        x.append(bullet(lab["c_redact"].format(n=L["redactions"])))
    for e in L.get("exclusions", []):
        x.append(bullet(lab["c_excl"].format(r=e["reason"], n=e["items"])))
    sus = [i for i in L["items"] if i.get("suspicious")]
    if sus:
        x.append(bullet(lab["c_model"]))
        for i in sus:
            x.append(para(r(QO + i["text"]+ QC, italic=True, size=18) + r(f"   {i['id']}", size=17, colour=SOFT), after=50, indent=720))
    else:
        x.append(bullet(lab["c_model0"]))
    x.append(bullet(lab["c_lang_en"] if lang == "en" else lab["c_lang_other"]))
    for t in B.get("checks_notes") or []:
        x.append(bullet(t))
    # all phrases
    x.append(h1(lab["all"]))
    clmap = {q: c["id"] for c in R["clusters"] for q in c["all_phrases"]}
    for t in TAGS:
        ps = [p for p in pm.values() if p["tag"] == t and "_item" in p]
        if not ps:
            continue
        x.append(h3(lab["tag_heads"][t]))
        rows = [lab["all_cols"]]
        for p in sorted(ps, key=lambda p: p["id"]):
            it = p["_item"]
            rows.append([p["id"], p["text"], clmap.get(p["id"], ""), it["voice"], sd(it["date"]) if it["date"] else lab["undated"], lab["window_vals"][it["in_window"]]])
        x.append(table(rows, [700, 5000, 650, 700, 1500, 1450], size=17))
    biz = slug(L["business"])
    folder = os.path.join(out_root, f"buyer-language-{biz}-{today}")
    os.makedirs(folder, exist_ok=True)
    docx = os.path.join(folder, f"{biz}-buyer-language-bank-{today}.docx")
    write_docx(docx, "".join(x), L["paper"], lab["title"].format(b=L["business"]), lang)
    csvp = os.path.join(folder, f"buyer-language-{biz}-{today}.csv")
    write_csv(L, R, csvp)
    return folder, docx, csvp


def check_sheet(L, Sh):
    problems = []
    lang = Sh.get("lang", "en")
    own = Sh.get("own_material") or []
    pub = Sh.get("sources") or []
    if not own:
        problems.append("own_material is empty: lead with the founder's own enquiries, call notes, review replies and comments on their posts")
    if len(own) + len(pub) < 6:
        problems.append(f"{len(own) + len(pub)} sources; a collection sheet names at least six")
    for i, s in enumerate(own + pub):
        for f in ("name", "search", "copy", "how_many"):
            if not str(s.get(f, "")).strip():
                problems.append(f"source {i + 1} ({s.get('name', '?')}): '{f}' is missing")
    for t in Sh.get("listen_for") or []:
        if quotes_in(t) or re.search(r"[\"“”„]", t):
            problems.append(f"listen_for '{t[:50]}' uses quotation marks; hypotheses are never written as quotes")
    items = {i["id"]: i for i in L["items"]} if L else {}
    for p in Sh.get("heard") or []:
        it = items.get(p.get("item"))
        if not it:
            problems.append(f"heard phrase '{p.get('text', '')[:40]}' cites an item not in the ledger")
            continue
        ok, why = phrase_in(p.get("text", ""), it["text"])
        if not ok:
            problems.append(f"heard phrase '{p.get('text', '')[:40]}' {why}")
    texts = [Sh.get("intro", ""), Sh.get("paste_format", "")] + [str(s.get(f, "")) for s in own + pub for f in ("name", "copy", "note", "how_many")] + list(Sh.get("listen_for") or [])
    for t in texts:
        if DASHES.search(outside_quotes(t)):
            problems.append(f"dash in '{t[:60]}'")
        if lang == "en":
            ps, _, _ = check_text(outside_quotes(t), "en")
            problems.extend(f"'{t[:40]}': {p}" for p in ps if not p.startswith("dash"))
    if L:
        vh = {v["hash"] for v in L["voices"].values() if not v.get("anon")} | {h for v in L["voices"].values() for h in v.get("alias", [])}
        for t in texts + [p.get("text", "") for p in Sh.get("heard") or []]:
            problems.extend(f"'{t[:40]}': {h}" for h in pii_hits(t, L["salt"], vh))
    return problems


def build_sheet(L, Sh, out_root):
    global QO, QC
    lang, lab = labels(Sh)
    QO, QC = ("\u201e", "\u201c") if lang == "de" else ("\u201c", "\u201d")
    order = (L or {}).get("date_order") or "DMY"
    today = (L or {}).get("today") or Sh.get("today") or date.today().isoformat()
    sd = lambda d: show_date(d, order, lang)  # noqa: E731
    biz = Sh.get("business") or (L or {}).get("business") or "business"
    x = [para(r(lab["sheet_title"].format(b=biz), bold=True, size=40), after=80), body(lab["sheet_sub"].format(d=sd(today)), colour=SOFT, after=300),
         body(Sh.get("intro") or lab["sheet_intro"]), body(lab["floor_line"], colour=SOFT, size=19)]
    heard = Sh.get("heard") or []
    if heard and L:
        from ledger import stats
        v = stats(L)["voices"]
        x.append(h2(lab["so_far"]))
        x.append(body(lab["so_far_intro"].format(v=v), colour=SOFT, size=19))
        items = {i["id"]: i for i in L["items"]}
        for p in heard:
            it = items[p["item"]]
            x.append(para(r(QO + p["text"]+ QC, italic=True) + r(f"   {it['voice']}, {it['source_type']}, {sd(it['date']) if it['date'] else lab['undated']}", size=17, colour=SOFT), after=50, indent=360))

    def src_block(s):
        out = [h3(s["name"])]
        out.append(labelled(lab["s_search"], s["search"], 360))
        out.append(labelled(lab["s_copy"], s["copy"], 360))
        out.append(labelled(lab["s_many"], s["how_many"], 360))
        if s.get("note"):
            out.append(labelled(lab["s_note"], s["note"], 360))
        return out
    x.append(h2(lab["own"]))
    for s in Sh.get("own_material") or []:
        x.extend(src_block(s))
    x.append(h2(lab["public"]))
    for s in Sh.get("sources") or []:
        x.extend(src_block(s))
    x.append(h2(lab["paste"]))
    x.append(body(Sh.get("paste_format") or lab["paste_default"]))
    if Sh.get("listen_for"):
        x.append(h2(lab["listen"]))
        x.append(body(lab["listen_note"], colour=SOFT, size=19))
        for t in Sh["listen_for"]:
            x.append(bullet(t))
    x.append(body(lab["rules"], size=19, colour=SOFT))
    os.makedirs(out_root, exist_ok=True)
    path = os.path.join(out_root, f"collection-sheet-{slug(biz)}-{today}.docx")
    paper = (L or {}).get("paper") or Sh.get("paper") or "A4"
    write_docx(path, "".join(x), paper, lab["sheet_title"].format(b=biz), lang)
    return path


def main():
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["bank", "sheet"])
    ap.add_argument("--run")
    ap.add_argument("file")
    ap.add_argument("--out", required=True)
    try:
        a = ap.parse_args()
    except SystemExit as e:
        if e.code not in (0, None):
            stop("the command was not understood; see the usage at the top of scripts/build_docx.py")
        raise
    if a.what == "sheet":
        Sh = load_json(a.file, "sheet")
        L = load_ledger(a.run) if a.run and os.path.exists(os.path.join(a.run, "ledger.json")) else None
        probs = check_sheet(L, Sh)
        for p in probs:
            print("PROBLEM:", p)
        if probs:
            print(f"{len(probs)} problems; nothing written")
            sys.exit(1)
        path = build_sheet(L, Sh, a.out)
        print(f"WROTE {path}")
        return
    if not a.run:
        stop("give --run with the run folder")
    L = load_ledger(a.run)
    B = load_json(a.file, "bank")
    problems, warns, R = check_bank(L, B)
    if R["bank_tier"] == "none":
        problems.append(f"only {R['quoted']['voices']} voices quoted ({R['stats']['voices']} read): under 5 there is no ranked bank. Quote phrases from more of the voices read, "
                        "or build the collection sheet (build_docx.py sheet) with what was heard so far")
    for p in problems:
        print("PROBLEM:", p)
    if problems:
        print(f"{len(problems)} problems; nothing written")
        sys.exit(1)
    folder, docx, csvp = build_bank(L, B, R, a.out)
    dst = os.path.join(folder, "sources")
    shutil.rmtree(dst, ignore_errors=True)
    os.makedirs(dst, exist_ok=True)
    for s in L["sources"]:
        if s["type"] != "previous" and s.get("file"):
            shutil.copy2(os.path.join(a.run, "sources", s["file"]), os.path.join(dst, s["file"]))
    S = R["stats"]
    Q = R["quoted"]
    top = R["ranked"][0] if R["ranked"] else None
    shipped = [os.path.join(dst, f) for f in os.listdir(dst)] + [csvp]
    for f in shipped:
        hit = LONG_DIGITS.search(open(f, encoding="utf-8-sig").read())
        if hit:
            shutil.rmtree(folder, ignore_errors=True)
            print(f"PROBLEM: {os.path.basename(f)} holds '{hit.group(0)}', which looks like a phone number; nothing written. Run ledger.py redact --run <run> --text \"{hit.group(0)}\" and build again")
            sys.exit(1)
    bcl = {c["id"]: c for c in B["clusters"]}
    cl = {c["id"]: c for c in R["clusters"]}
    print(f"WROTE {docx}")
    print(f"WROTE {csvp}")
    print(f"WROTE {dst}/ ({len([s for s in L['sources'] if s['type'] != 'previous'])} files)")
    dates = sorted(p["_item"]["date"] for p in R["phrases"].values() if "_item" in p and counted(p["_item"]) and p["_item"]["date"])
    lang = B.get("lang", "en")
    sd = lambda d: show_date(d, L["date_order"], lang)  # noqa: E731
    span = f", dated {sd(dates[0])} to {sd(dates[-1])}" if dates else ""
    print(f"SUMMARY 1: {'Full' if R['bank_tier'] == 'full' else 'Starter'} bank from {Q['voices']} voices quoted ({S['voices']} read) across {Q['sources']} sources "
          f"({', '.join(Q['source_types'])}){span}; {len(R['ranked'])} clusters ranked.")
    if top:
        q = next((R["phrases"][x] for x in cl[top]["counted_phrases"]), None)
        print(f"SUMMARY 2: Lead with '{bcl[top]['name']}' ({cl[top]['voices']} voices, {len(cl[top]['source_types'])} source types)"
              + (f": \"{q['text']}\"" if q else ""))
        def needs(cid):
            n = (bcl.get(cid, {}).get("ad_angle") or {}).get("need") or []
            return [x for x in (n if isinstance(n, list) else [n]) if "[NEED" in str(x)]
        ready = [c for c in R["ranked"] if bcl.get(c, {}).get("ad_draft")]
        for c in ready:
            print(f"SUMMARY 2c: Ready to run: '{bcl[c]['ad_draft'].get('headline', '')}' ({bcl[c]['name']}, {cl[c]['voices']} of {Q['voices']} voices quoted), resting on: {'; '.join(bcl[c]['ad_draft'].get('facts') or [])}")
        quick = min(R["ranked"], key=lambda c: (len(needs(c)), R["ranked"].index(c)))
        nq = needs(quick)
        if not ready:
            print(f"SUMMARY 2b: Quickest to run: '{(bcl[quick].get('ad_angle') or {}).get('headline', '')}' ({bcl[quick]['name']}); "
                  + (f"clear first: {nq[0]}" + (f" and {len(nq) - 1} more" if len(nq) > 1 else "") if nq else "nothing to prove first beyond the buyers' own words"))
    em = [c for c in R["clusters"] if c["tier"] == "emerging"]
    one = [c for c in R["clusters"] if c["tier"] == "single"]
    flags = [f"{len(em)} emerging and {len(one)} single-voice cluster{'s' if len(em) + len(one) != 1 else ''} held back" if em or one else "",
             f"{S['outside']} outside the window" if S["outside"] else "", f"{S['undated']} undated" if S["undated"] else "",
             (f"{S['dups']} suspected duplicate" + ("s" if S["dups"] != 1 else "")) if S["dups"] else "", f"{S['excluded']} excluded ({'; '.join(e['reason'] for e in L.get('exclusions', []))})" if S["excluded"] else "", (f"{S['suspicious']} item" + ("s" if S["suspicious"] != 1 else "") + " addressed to a model") if S["suspicious"] else "",
             f"{sum(1 for w in L.get('web', []) if w['result'] != 'ok')} sources could not be read" if any(w["result"] != "ok" for w in L.get("web", [])) else ""]
    print("SUMMARY 3: Flagged: " + ("; ".join(f for f in flags if f) or "nothing"))
    nc = B.get("next_collect") or {}
    print(f"SUMMARY 5: Collect next: {nc.get('source', '')}. Search: {nc.get('search', '')}")


if __name__ == "__main__":
    main()
