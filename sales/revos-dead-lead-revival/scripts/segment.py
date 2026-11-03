#!/usr/bin/env python3
"""Sort every contact into one of nine groups by why they went quiet, or onto the held-back list with a reason.

Rules (references/segments.md and references/method.md):
- The group comes from the earliest true cause: where the conversation stopped, not the last thing said.
  A recorded reason wins; where none is recorded the furthest stage reached decides, marked "reason inferred".
  Price with no proposal or quote on record is an unfinished conversation, not a price objection.
- Held back before anything is written: asked to stop, unsubscribed, current client or live deal, a dispute,
  bad fit or business gone, bought, scraped or unknown source, no usable contact detail, a date in the future,
  too recent, a duplicate, inside the cooldown, a row whose notes carry an instruction, anyone the founder names.
- Recency only orders and paces. Priority score: warmth of the group, recency band, a come-back date that has
  arrived, past value, their own words on file, minus a shared inbox. Shown on the Rules sheet.
Standard library only. No network calls.
"""
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CONTEXT_KEYS, Stop, add_months, fold, is_english, month_year_in, months_between  # noqa: E402
import ingest as ig  # noqa: E402

SEGMENTS = {
    "parked": {"label": "Parked with a date", "touches": 3, "offsets": [0, 5, 14], "warmth": 30,
               "short": "said a date"},
    "past_client": {"label": "Past client", "touches": 4, "offsets": [0, 4, 11, 18], "warmth": 30,
                    "short": "past client"},
    "quiet_after_proposal": {"label": "Went quiet after a proposal", "touches": 4, "offsets": [0, 4, 11, 18],
                             "warmth": 25, "short": "quiet after proposal"},
    "not_now": {"label": "Said not now", "touches": 4, "offsets": [0, 4, 11, 18], "warmth": 22, "short": "said not now"},
    "unfinished": {"label": "Talked, no proposal followed", "touches": 4, "offsets": [0, 4, 11, 18], "warmth": 20,
                   "short": "talked, no proposal"},
    "price": {"label": "Stopped at the price", "touches": 3, "offsets": [0, 5, 14], "warmth": 18,
              "short": "stopped at price"},
    "no_show": {"label": "Booked a call that didn't happen", "touches": 3, "offsets": [0, 5, 14], "warmth": 15,
                "short": "missed the call"},
    "early": {"label": "Enquired or met, never got to a call", "touches": 3, "offsets": [0, 5, 14], "warmth": 12,
              "short": "enquired, no call"},
    "chose_other": {"label": "Chose someone else", "touches": 3, "offsets": [0, 5, 14], "warmth": 8,
                    "short": "chose someone else"},
}
ANGLE = {
    "parked": ("They told you when to come back. Write on that date, name it in their words, ask if it still stands.",
               "Any reply, or touch 3 (closing the file)."),
    "past_client": ("You already did good work together. Ask how things have gone since; no pitch until they answer.",
                    "Any reply, or touch 4 (closing the file)."),
    "quiet_after_proposal": ("The proposal is still open in their head. Ask one easy question about where it landed; "
                             "from touch 2, give them a one-word way to answer.", "Any reply, or touch 4 (closing the file)."),
    "not_now": ("Timing was the reason. Ask whether the timing has changed, nothing else.",
                "Any reply, or touch 4 (closing the file)."),
    "unfinished": ("You talked but never got to a proposal. Pick the conversation up where it stopped.",
                   "Any reply, or touch 4 (closing the file)."),
    "price": ("They saw a price and stopped. Ask what would have had to be different; never cut the price in writing.",
              "Any reply, or touch 3 (closing the file)."),
    "no_show": ("They booked and missed it. Give them an easy way back, then an honest fork: timing, or something "
                "changed.", "Any reply, or touch 3 (closing the file)."),
    "early": ("They asked or you met, and it never became a conversation. Remind them of the moment and ask if it is "
              "still live.", "Any reply, or touch 3 (closing the file)."),
    "chose_other": ("They chose someone else. Ask, without edge, how it went; the door stays open.",
                    "Any reply, or touch 3 (closing the file)."),
}
ABBR = {"parked": "PK", "past_client": "PC", "quiet_after_proposal": "QP", "not_now": "NN", "unfinished": "UF",
        "price": "PR", "no_show": "NS", "early": "EN", "chose_other": "CO"}
SEGMENT_ORDER = ["parked", "past_client", "quiet_after_proposal", "not_now", "unfinished", "price", "no_show", "early",
                 "chose_other"]
LABEL_TO_KEY = {fold(v["label"]): k for k, v in SEGMENTS.items()}

HOLD = {
    "asked_to_stop": ("Asked to stop", "Nothing. Never message them again."),
    "unsubscribed": ("Unsubscribed", "Nothing, unless they contact you first."),
    "off_limits": ("You said leave them out", "You say so."),
    "current": ("Current client or live deal", "Handle them in your normal client work, not here."),
    "dispute": ("Dispute or complaint on file: a phone call, not a message", "Ring them yourself if you want to; "
                "no sequence is written."),
    "bad_fit": ("Marked as a bad fit or no need", "New information that they now fit."),
    "gone": ("Business closed or person left", "A new contact at the company, added as a new row."),
    "bought_list": ("Bought, scraped or unknown list: no history with you", "Only if they contact you themselves."),
    "source_unknown": ("Source unknown: how they came onto your list is not clear", "Tell me how they came onto "
                       "your list (enquired, past client, met in person, signed up)."),
    "no_contact": ("No email or phone for the channels you use", "Add an email or phone, or allow another channel."),
    "no_channel": ("No usable channel: the channels you chose cannot reach them", "Allow another channel for them, or "
                   "add an address you can use."),
    "check_date": ("Last contact date is in the future", "Correct the date."),
    "too_recent": ("Too recent: this is a live follow-up, not a revival", "Revisit on the date shown."),
    "maybe_current": ("May still be a client", "Confirm they have stopped."),
    "duplicate": ("Duplicate: merged into another row", "Nothing; their details are on the row named."),
    "cooldown": ("Inside the cooldown after your last sequence", "The cooldown date passes, or they write to you."),
    "check_row": ("The notes held an instruction to an AI, which was ignored", "Check the row by hand and confirm "
                  "the contact is real."),
    "replied": ("Replied: answer them yourself", "Already in conversation; log the outcome in Status."),
    "replied_later": ("Replied: asked you to come back later", "Message them on the revisit date."),
    "bounced": ("Bounced", "A working address."),
    "retired": ("Sequence finished with no reply", "A new reason to write, after the cooldown."),
}
HOLD_SHORT = {"asked_to_stop": "asked to stop", "unsubscribed": "unsubscribed", "off_limits": "you said leave out",
              "current": "current client or live deal", "dispute": "dispute on file (ring, don't message)",
              "bad_fit": "bad fit or no need", "gone": "business closed or person left", "bought_list": "bought or scraped list",
              "source_unknown": "source unknown", "no_contact": "no contact detail", "no_channel": "no usable channel", "check_date": "date in the future",
              "too_recent": "too recent", "maybe_current": "may still be a client", "duplicate": "duplicate (merged)",
              "cooldown": "in the cooldown", "check_row": "notes held an instruction (ignored)", "replied": "replied",
              "replied_later": "replied: come back later", "bounced": "bounced", "retired": "sequence finished"}
PERMANENT = {"asked_to_stop", "unsubscribed", "bought_list", "dispute", "gone", "bad_fit"}

KW = {
    "asked_to_stop": r"(do not (contact|email|call|message)|don'?t (contact|email|call)|asked (us |me )?not to be contacted|"
                     r"asked (us |me )?to stop|remove (me|them|from)|take (me|them) off|stop (emailing|messaging|contacting)|"
                     r"\bdnc\b|nicht (mehr )?kontaktieren|keinen kontakt|ne (pas|plus) (le |la |les )?contacter|"
                     r"keine (e-?mails?|mails|nachrichten|anrufe) mehr|no contactar|hostile|abusive|rude reply|told (us|me) to go away)",
    "unsubscribed": r"(unsubscrib|opted out|opt-out|abgemeldet|desabonne|desinscri|baja)",
    "current": r"(closed ?won|\bwon\b|current client|active client|now a client|became a client|is a client now|"
               r"signed (up|the contract)|onboarding|live deal|"
               r"in negotiation|open deal|gewonnen|aktiver kunde|kunde aktuell|aktuell(er)? kunde|projekt (lauft|laeuft)|"
               r"laufendes projekt|client actuel|projet en cours|mission en cours|cliente actual|proyecto en curso|"
               r"still a client|currently working (with|for)|ongoing (project|work|contract))",
    "maybe_current": r"(maybe (still )?(a )?current|might (still )?be (a )?(current|client)|still books|possibly (still )?"
                     r"(a )?(current|client)|not sure if (she|he|they)('?s| is| are) still|vielleicht noch kunde)",
    "dispute": r"(dispute|disputed|complain|chargeback|refund|angry|threat|late payment|unpaid|owes (us|me)|still owes|"
               r"\bowed\b|outstanding (invoice|balance|amount|payment|bill)|overdue (invoice|payment|bill)|never paid|"
               r"didn'?t pay|offene rechnung|rechnung (noch |ist )?offen|mahnung|inkasso|nicht bezahlt|streit|beschwerde|"
               r"litige|impaye|facture impayee|reclamacion|factura pendiente|no (ha )?pagado)",
    "bad_fit": r"(not a fit|wrong fit|bad fit|no need|not qualified|unqualified|disqualif|student|spam|job seeker|"
               r"is a competitor|we don'?t (do|offer) (that|those|it|this)|we don'?t\W*$|not something we do|"
               r"kein bedarf|pas de besoin|sin necesidad)",
    "gone": r"(closed down|went bust|out of business|ceased trading|left the company|no longer at|retired|"
            r"insolven|liquidat|geschlossen|ferme|cerrado)",
    "bought": r"(bought (a |the )?list|purchased (a |the )?list|scraped|apollo|zoominfo|lusha|list (from|vendor)|"
              r"data ?broker|cold list|lead list|purchased (data|contacts|leads)|bought (data|contacts|leads)|"
              r"adressliste|gekaufte? (adress)?liste|liste gekauft|gekauft\W{1,3}(\w+\W{1,3}){0,2}liste|"
              r"liste\W{1,3}(\w+\W{1,3}){0,2}gekauft|liste achetee|lista comprada|base de datos comprada)",
    "signed_up": r"(newsletter|subscriber|signed up|sign-up|download(ed)?|webinar|lead magnet|opt-?in)",
    "met": r"(met (at|in|him|her|them|on)|\bevent\b|conference|networking|meetup|trade ?show|expo|introduced|"
           r"\bintro\b|referr|recommended|empfehlung|empfohlen|recommand|recomendad|visitenkarte|business card|chamber|"
           r"messe|salon|kongress|konferenz)",
    "past_client": r"(past client|former client|ex-?client|was a client|was our client|\bclient (in |since |from )?(19|20)\d{2}\b|"
                   r"\bclient (from|since|for|until) |customer (from|for|since) |bought from (us|me)|war (unser |mein )?kunde|"
                   r"ehemalige[rn]? kunde|altkunde|ex-?kunde|stammkunde|kunde (von|seit|bis) |ancien(ne)? client|ex-?cliente|"
                   r"^client\b|lapsed|used to (work|buy)|previous client|"
                   r"customer since|ehemaliger kunde|ancien client|antiguo cliente|stopped (working|buying|using))",
    "no_show": r"(no[- ]?show|didn'?t show|did not show|missed (the |our )?(call|meeting)|stood (me|us) up|"
               r"cancel+ed|rescheduled|reschedule|verschoben|abgesagt|nicht erschienen|absent|annule)",
    "offer": r"(proposal|quote|quoted|pricing sent|price sent|sent (the |a |our )?(price|pricing|figures|offer)|contract sent|"
             r"(replied|came back|answered|got back) with [^.;]{0,20}(\d|price|pricing|quote|package)|"
             r"sent (him|her|them) (the |a |our )?(price|pricing|quote|figures|package)|"
             r"estimate|angebot|offerte|devis|presupuesto|cotizacion|sow\b|statement of work|sent terms)",
    "price": r"(price|pricing|too expensive|expensive|cost|budget too|cheaper|pricey|afford|\bfee\b|too much|too steep|"
             r"out of (our|my|their) budget|teuer|preis|kosten|"
             r"prix|cher|caro|precio)",
    "chose_other": r"(went with|chose|another (agency|firm|provider|consultant|supplier)|competitor|someone else|in-?house|"
                   r"\bdiy\b|do(ing)? it (themselves|ourselves|himself|herself|myself|in-?house)|their nephew|wettbewerber|"
                   r"bei .{0,30}geblieben|anderen anbieter|macht es (intern|selbst)|intern mit|concurrent|competencia|otro proveedor|hired (someone|a)|"
                   r"cheaper outfit|cheaper (one|option)|konkurren|mitbewerber|ging zu|geht zu|gegangen zu|zu \w+( \w+)? gegangen|"
                   r"went elsewhere|went to [^.;]{0,30}instead|gone with|signed with|switched to|eigenleistung|"
                   r"macht (es|das) selb|selbst gemacht|selber machen|a choisi|autre prestataire|fue con|eligio|otra empresa)",
    "not_now": r"(not now|not right now|timing|bad time|not the right time|later|on hold|paused|pause|busy|budget|"
               r"no budget|maybe next|next year|partner|wife|husband|needs? to (talk|check|ask|run it)|board|think about it|"
               r"spater|zeitpunkt|kein budget|abwarten|erst mal|erstmal|nicht jetzt|keine zeit|im moment nicht|"
               r"derzeit nicht|zurzeit nicht|pas maintenant|plus tard|mas adelante|ahora no)",
    "silence": r"(ghost|went (dark|quiet|silent)|no (response|reply|answer)|never (replied|heard|came back)|silence|"
               r"keine antwort|pas de reponse|sin respuesta)",
    "call": r"(had a call|\bcall\b|spoke|chatted|meeting|met with|discovery|consult|zoom|teams|termin|gesprach|"
            r"said yes|agreed|verbal|zugesagt|trial|rendez-vous|reunion|llamada|coffee)",
    "enquired": r"(enquir|inquir|contact form|web form|form fill|asked (about|for)|requested|wanted (a |some )?(quote|price|"
                r"pricing|info)|anfrage|angefragt|kontaktformular|hatte (eine )?frage|demande|consulta|never booked|"
                r"didn'?t book|lead\b)",
    "come_back": r"\b(till|until|untill|til|after (the )?(summer|holidays?|christmas|new year|break|q[1-4]|launch|"
                 r"jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{1,2}(st|nd|rd|th))|"
                 r"back in|ask in|ring (me )?(in|after)|call (me )?(in|after)|in q[1-4]|by q[1-4]|from q[1-4]|"
                 r"try again (in|after|next)|again in (the )?|harvest|busy season|year[- ]end|financial year|"
                 r"chat again in|in the new year|erst (nachstes|im|ab|nach|20\d\d)|not (until|before) (20\d\d|next)|"
                 r"see (the )?q[1-4]|q[1-4] (numbers|results|figures|budget)|"
                 r"next (year|quarter|month|spring|summer|autumn|fall)|new year|nach der|nach dem|bis|ab (januar|februar|"
                 r"marz|april|mai|juni|juli|august|september|oktober|november|dezember)|melden|apres|jusqu|despues|hasta)\b",
    "texted": r"(\btext(ed)?\b|\bsms\b|whatsapp|imessage|replied by text|on whatsapp)",
    "no_contact_words": r"(no (email|address|number|contact details)|lost (their|his|her) (email|number))",
    "dm": r"(linkedin|insta(gram)?\b|\big\b|\bdm\b|direct message|messenger|facebook|tiktok|twitter|\bx\.com)",
    # any sign of a real exchange with the founder: enough to count as "enquired or spoke with you"
    "history": r"(asked|enquir|inquir|request|said|told|agreed|keen|interested|wanted|wants|replied|respond|wrote|emailed|"
               r"messaged|texted|rang|called|phoned|spoke|talked|chatted|\bmet\b|trial|class|booked|quote|proposal|"
               r"pricing|price|sent|\bcall\b|meeting|zoom|coffee|visit|demo|ring me|call me|no[- ]?show|ghost|"
               r"gesprochen|geschrieben|angerufen|gefragt|wollte|termin|gesprach|angebot|anfrage|interessiert|"
               r"parle|ecrit|appele|demande|rendez-vous|hablamos|escribio|llamo|pidio)",
    "unknown_history": r"(don'?t remember|do not remember|can'?t remember|cannot remember|no idea|not sure who|who is this|"
                       r"keine ahnung|weiss nicht mehr|wei. nicht mehr|aucune idee|ni idea)",
}
HANDLE_RX = r"(?<![\w.@])@[a-z0-9_][a-z0-9_.]{1,29}[a-z0-9_]"
PRICE_OBJECTION = (r"(too expensive|expensive|too much|too high|too steep|pricey|afford|cheaper|budget too|out of (our|my|their) "
                   r"budget|zu teuer|teuer|zu (viel|hoch)|preis zu hoch|trop cher|\bcher\b|caro|demasiado|price too|"
                   r"cost too|\bfee\b)")
PRICE_WORD = r"(\bprice|\bpricing\b|\bpreis|\bprix\b|\bprecio\b|\bcost\b|\bkosten\b|\bteuer)"
NEG_OFFER = (r"(never|didn'?t|did not|not yet|haven'?t|hadn'?t|wasn'?t|was not)( \w+){0,2} (sent|send|got to|get to|gave|give|"
             r"given|quoted)( \w+){0,3} (figures|price|prices|pricing|proposal|quote|numbers)|"
             r"no (proposal|quote|price|pricing|figures) (was |were )?(sent|given)|"
             r"(proposal|quote|price|pricing|figures)( \w+){0,2} (never|not|wasn'?t)( yet)? (sent|given|done)|"
             r"send (me |them |him |her )?(the |a )?(proposal|quote|figures)[^.;]{0,50}\b(i )?never (did|sent)|"
             r"(angebot|preis|kostenvoranschlag)( \w+){0,2} (nie|nicht|noch nicht|niemals)( \w+)? (geschickt|gesendet|"
             r"geschrieben|raus|erstellt|gemacht)|(nie|kein|noch kein) angebot|(devis|offre)( \w+){0,2} (jamais|pas) "
             r"(envoye|fait)|(presupuesto|propuesta)( \w+){0,2} (nunca|no) (enviad|mandad)|nunca (envie|mande)")
AMOUNT = r"([$£€¥₹]\s?\d[\d.,]*|\b\d{1,3}([.,' ]\d{3})+([.,]\d{1,2})?\b|\b\d[\d.,]*\s?(€|eur\b|euro|k\b|usd|aud|gbp|dollars?))"
AMOUNT_OBJECTION = (AMOUNT + r"[^.;]{0,25}(zu (viel|hoch|teuer)|too (much|high|steep)|trop|demasiado)|"
                    r"(too (much|high|steep)|zu (viel|hoch|teuer))[^.;]{0,25}" + AMOUNT)
EXPLICIT_TIMING = (r"(not now|not right now|timing|bad time|not the right time|later|on hold|pause|busy|budget|next year|"
                   r"spater|zeitpunkt|abwarten|erst mal|erstmal|nicht jetzt|keine zeit|pas maintenant|plus tard|"
                   r"mas adelante|ahora no)")
STAGE_CLIENT = r"^(ex-?|alt|ehemalige[rn]? )?(kunde|client|customer|cliente|klant|kund)( \(?(ehemalig|former|past|alt)\)?)?$"
STAGE_OFFER = r"(proposal|quote|contract|negotiat|decision|angebot|offer|devis|presentation sent|pricing)"
STAGE_CALL = r"(appointment|meeting|qualified|presentation|demo|discovery|call|termin|gesprach|sql)"
STAGE_EARLY = r"(lead|new|subscriber|mql|contacted|open|enquiry|inquiry|attempted|anfrage|nouveau|nuevo)"


def rx(key, text):
    return re.search(KW[key], text, re.I)


def text_of(c):
    t = " ".join(str(c.get(k, "")) for k in ("reason", "stage", "notes", "raw", "deal", "status", "reply_notes"))
    for k in ("email", "name", "company"):
        v = str(c.get(k) or "").strip()
        if len(v) > 2:
            t = re.sub(re.escape(v), " ", t, flags=re.I)
    return fold(t)


def classify(c, s, ann):
    """Return (segment or None, hold code or None, why, inferred flag, extra notes)."""
    t = text_of(c)
    rs = fold(c.get("reason", ""))
    stage = fold(c.get("stage", ""))
    notes = []
    if c.get("instruction_text"):
        return None, "check_row", "", False, notes
    if c.get("duplicate_of"):
        return None, "duplicate", "", False, notes
    if ann.get("hold"):
        if ann["hold"] not in HOLD:
            raise Stop(f"annotation for {c['ref']} has hold '{ann['hold']}', which is not one of: {', '.join(HOLD)}")
        return None, ann["hold"], ann.get("why", ""), False, notes
    if rx("asked_to_stop", t):
        return None, "asked_to_stop", "", False, notes
    if rx("unsubscribed", t):
        return None, "unsubscribed", "", False, notes
    xnotes = s.get("exclude_notes") or {}
    for x in s.get("exclude", []):
        xf = fold(x)
        if xf and (xf == fold(c.get("name")) or xf == fold(c.get("first")) or xf == fold(c.get("company"))
                   or xf == fold(c.get("email")) or (len(xf.split()) > 1 and xf in fold(c.get("name")))):
            return None, "off_limits", xnotes.get(x, ""), False, notes
    if rx("current", rs + " " + stage + " " + fold(c.get("notes")) + " " + fold(c.get("raw"))) and \
            not re.search(r"lost|verloren|perdu", stage + rs):
        return None, "current", "", False, notes
    if rx("dispute", t):
        return None, "dispute", "", False, notes
    if rx("gone", t):
        return None, "gone", "", False, notes
    if rx("bad_fit", rs + " " + fold(c.get("notes"))):
        return None, "bad_fit", "", False, notes
    if rx("maybe_current", t):
        return None, "maybe_current", "their notes say they may still be a client", False, notes
    if ann.get("segment"):
        if ann["segment"] not in SEGMENTS:
            raise Stop(f"annotation for {c['ref']} has segment '{ann['segment']}', not one of: {', '.join(SEGMENTS)}")
        return ann["segment"], None, ann.get("why", ""), False, notes
    if rs and rx("chose_other", rs) and not rx("not_now", rs):
        return "chose_other", None, "", False, notes
    has_offer = bool(rx("offer", t) or re.search(STAGE_OFFER, stage))
    if re.search(NEG_OFFER, t):
        has_offer = bool(re.search(STAGE_OFFER, stage))
        notes.append("no figures were sent, so this is treated as an unfinished conversation")
    price_ok = bool(re.search(r"price (was|is|seemed) (fine|ok|okay|not the (issue|problem))|not (about|the) price", t))
    # a price word in the recorded reason is an objection; in the notes it takes an objection word ("asked for pricing" is not)
    objected = bool(re.search(PRICE_OBJECTION, rs) or re.search(PRICE_WORD, rs) or re.search(PRICE_OBJECTION, t))
    if objected and not has_offer and re.search(AMOUNT_OBJECTION, t) and not re.search(NEG_OFFER, t):
        has_offer = True
        notes.append("an amount is named beside the objection, so they saw a price")
    is_client = bool(rx("past_client", t) or re.search(STAGE_CLIENT, stage) or c.get("invoices") not in (None, "")
                     or c.get("came_onto_list") == "past_client")
    if is_client and not re.search(r"never (a |been a )?client|nie kunde", t):
        return "past_client", None, "", False, notes
    if rx("no_show", t):
        return "no_show", None, "", False, notes
    if c.get("parked_until") or rx("come_back", t):
        return "parked", None, "", False, notes
    if objected and not price_ok:
        if has_offer:
            return "price", None, "", False, notes
        if rx("chose_other", t):
            notes.append("they mentioned price, but no proposal or quote from you is on record")
            return "chose_other", None, "", False, notes
        if re.search(r"\bbudget\b", rs) and not re.search(r"price|cost|expensive|teuer|prix|preis", rs):
            return "not_now", None, "", False, notes
        if rx("call", t) and not re.search(r"never booked|didn'?t book", t):
            notes.append("price mentioned, but no proposal or quote on record, so treated as an unfinished conversation")
            return "unfinished", None, "", False, notes
        notes.append("price mentioned, but no call or proposal on record, so treated as an early enquiry")
        return "early", None, "", False, notes
    if rx("chose_other", t):
        return "chose_other", None, "", False, notes
    if rx("not_now", t):
        if re.search(r"think about it", t) and not has_offer:
            notes.append("'think about it' with no offer made is an unfinished conversation, not timing")
            return "unfinished", None, "", False, notes
        if has_offer and not re.search(EXPLICIT_TIMING, t):
            return "quiet_after_proposal", None, "", False, notes
        return "not_now", None, "", False, notes
    if has_offer:
        return "quiet_after_proposal", None, "", not rx("silence", t) and not rx("offer", rs + fold(c.get("notes"))), notes
    if re.search(r"never booked|didn'?t book|did not book|no call (booked|yet)|never (had|got to) (a|the) call|"
                 r"nie (einen )?termin|keinen termin|jamais (pris|reserve)|nunca reservo", t):
        return "early", None, "", False, notes
    if rx("call", t):
        said = re.search(r"went (quiet|dark|silent)|then nothing|nothing (since|back|after)|ghost|didn'?t follow|never did|"
                         r"no reply|no response|silence|i was slow|dropped|dann nichts|funkstille|keine antwort|"
                         r"nicht mehr gemeldet|pas de (suite|reponse)|sin respuesta", t)
        return "unfinished", None, "", not (rs or said), notes
    if rx("enquired", t) or rx("met", t) or rx("signed_up", t):
        return "early", None, "", False, notes
    if re.search(STAGE_CALL, stage):
        return "unfinished", None, "", True, notes
    return "early", None, "", True, notes


def came_from(c, seg, s, ann):
    """How they came onto the list: enquired, past_client, met, signed_up, bought, unknown.
    Any sign of a real exchange with the founder counts as enquired; only rows with no history at all, or notes
    saying the founder does not remember them, are held as unknown."""
    if ann.get("came_from"):
        return ann["came_from"]
    if c.get("came_onto_list"):
        return c["came_onto_list"]
    t = text_of(c) + " " + fold(c.get("source"))
    for rule in s.get("source_rules", []):
        if fold(rule.get("match")) and fold(rule.get("match")) in t:
            return rule.get("source", "unknown")
    if rx("bought", t):
        return "bought"
    if seg == "past_client":
        return "past_client"
    strong = any(rx(k, t) for k in ("enquired", "no_show", "offer", "call", "met", "signed_up", "chose_other"))
    if rx("unknown_history", t) and not strong:
        return s.get("source_default") or "unknown"
    if rx("met", t):
        return "met"
    if rx("signed_up", t) and not (rx("call", t) or rx("offer", t)):
        return "signed_up"
    if re.search(r"website|web ?site|homepage|kontaktformular|contact form|google|inbound|webseite|site web|pagina web", t):
        return "enquired"
    if seg != "early" or c.get("stage") or c.get("reason") or c.get("deal") or rx("history", t) or rx("come_back", t) \
            or c.get("value") not in (None, "") or c.get("parked_until"):
        return "enquired"
    return s.get("source_default") or "unknown"


CAME_LABEL = {"enquired": "enquired or spoke with you", "past_client": "past client", "met": "met in person or introduced",
              "signed_up": "signed up to something of yours", "bought": "bought or scraped list", "unknown": "not known"}


def band_of(months):
    if months is None:
        return "date unknown", 3
    if months < 3:
        return "1 to 3 months", 8
    if months < 6:
        return "3 to 6 months", 12
    if months < 18:
        return "6 to 18 months", 15
    if months < 36:
        return "18 to 36 months", 6
    return "over 36 months", 0


def label_their_date(phrase, d, s=None):
    s = s or {}
    if not is_english(s):
        return month_year_in(d, s) if d else ""
    p = fold(phrase)
    m = re.search(r"\bq([1-4])\b", p)
    if m:
        return f"Q{m.group(1)} {d.year}" if d else f"Q{m.group(1)}"
    if re.search(r"christmas|xmas|weihnacht", p):
        return "after Christmas" if re.search(r"after|nach", p) else "Christmas"
    if re.search(r"next year|new year|neujahr|neuen jahr|nachstes jahr", p):
        return "the new year"
    if re.search(r"harvest|ernte|vendange", p):
        return "after harvest"
    if re.search(r"after (the )?summer|summer ?(break|holiday)|sommerpause|nach dem sommer", p):
        return "after the summer"
    if re.search(r"summer|sommer|ete\b", p):
        return "the summer"
    m = re.search(r"\b(\d{1,2})(st|nd|rd|th)\b", p)
    if m:
        return f"the {m.group(1)}{m.group(2)}"
    return month_year_in(d, s) if d else "then"


def previous_index(prev_data, s):
    """From an earlier tracker: who must stay out of a new list (asked to stop, inside the cooldown, replied)."""
    idx = {}
    if not prev_data:
        return idx
    today = s["today"]
    for c in prev_data["contacts"]:
        code = fold(c.get("held_code") or "").replace(" ", "_")
        status = fold(c.get("status") or "")
        hold = None
        if code in PERMANENT or code in ("off_limits",) or status == "stopped":
            hold = ("asked_to_stop" if code in ("asked_to_stop", "") or status == "stopped" else code,
                    "from your last tracker")
        elif status in ("replied", "call booked", "won"):
            hold = ("replied", "in conversation on your last tracker")
        else:
            cd = c.get("cooldown_until") or c.get("revisit")
            cdd = cd if isinstance(cd, date) else (ig.parse_when(cd, "dmy", "", today)[0] if cd else None)
            if status in ("sent", "no reply") and cdd and cdd > today:
                hold = ("cooldown", f"messaged on your last run; rests until {cdd.isoformat()}")
        if not hold:
            continue
        for k in keys_of(c):
            idx[k] = hold
    return idx


def keys_of(c):
    ks = []
    if c.get("email"):
        ks.append("e:" + fold(c["email"]))
    if c.get("phone_digits"):
        ks.append("p:" + c["phone_digits"][-9:])
    if c.get("name") and c.get("company"):
        ks.append("n:" + fold(c["name"]) + "|" + fold(c["company"]))
    return ks


def previous_match(c, idx):
    for k in keys_of(c):
        if k in idx:
            return idx[k]
    return None


def plan_contacts(data, s, ann_all=None, prev_data=None):
    """data: ingest result. Returns dict with contacts (eligible, ranked) and held (with reasons)."""
    today = s["today"]
    prev_index = previous_index(prev_data, s) if data["kind"] != "tracker" else {}
    ann_all = ann_all or {}
    order = data["date_order"]
    contacts, held = [], []
    values = sorted([c["value"] for c in data["contacts"] if isinstance(c.get("value"), (int, float)) and c["value"] > 0])
    q1 = values[int(len(values) * 0.75)] if len(values) >= 4 else None
    q2 = values[int(len(values) * 0.5)] if len(values) >= 4 else None
    for c in data["contacts"]:
        ann = dict(ann_all.get(c["ref"], {}) or ann_all.get(str(c["row"]), {}) or {})
        bad = set(ann) - ANN_KEYS
        if bad:
            raise Stop(f"annotation for {c['ref']} has unknown keys {', '.join(sorted(bad))}; use: {', '.join(sorted(ANN_KEYS))}")
        if data["kind"] == "tracker" and c.get("personal") and not str(c["personal"]).startswith("[") \
                and not ann.get("context"):
            c["context"] = c["personal"]
        for k in ("parked_until", "parked_phrase", "context", "channel", "detail", "handle", "greeting"):
            if ann.get(k):
                c[k] = ann[k]
        c["why_inferred"] = False
        c["notes_flags"] = list(c.get("flags", []))
        c["corrections"] = []
        apply_contact_fixes(c, ann, s, order)
        prev = None
        if data["kind"] == "tracker":
            seg, hold, why, inferred, extra = tracker_state(c, s, ann)
            prev = True
        else:
            seg, hold, why, inferred, extra = classify(c, s, ann)
        if any(x.startswith("no figures were sent") for x in extra):
            extra = [x for x in extra if not x.startswith("price mentioned")]
        c["notes_flags"] += extra
        pk = previous_match(c, prev_index)
        if pk and not hold:
            hold, why = pk
        if hold == "replied_later" and c.get("parked_until"):
            d, _a, _n = ig.parse_future(str(c["parked_until"]), today, order, s.get("country"))
            if d is None:
                d = ig.parse_when(c["parked_until"], order, s.get("country"), today)[0]
            if d:
                add_hold(held, c, hold, why, s, order, revisit=d)
                continue
        if hold:
            add_hold(held, c, hold, why, s, order)
            if c.get("held_reason_in") and data["kind"] == "tracker" and not ann.get("hold"):
                c["held_reason"] = str(c["held_reason_in"])
            continue
        cf = came_from(c, seg, s, ann)
        c["came_from"] = cf
        if cf == "bought":
            add_hold(held, c, "bought_list", "", s, order)
            continue
        if cf == "unknown":
            add_hold(held, c, "source_unknown", "", s, order)
            continue
        # parked date
        last = date.fromisoformat(c["last_contact"]) if c.get("last_contact") else None
        if c.get("future_date"):
            add_hold(held, c, "check_date", "", s, order)
            continue
        if seg == "parked":
            phrase = c.get("parked_phrase") or c.get("parked_until") or extract_come_back(text_of(c), c)
            anchor = last or today
            if not last and phrase and re.search(re.escape(fold(phrase)) + r"\W{0,4}(\(\W*)?(last year|letztes jahr|"
                                                 r"l'annee derniere|el ano pasado)", text_of(c)):
                anchor = date(today.year - 1, today.month, min(today.day, 28))
                c["notes_flags"].append("they said that last year, so their date has passed: first message now")
            when = None
            if c.get("parked_until"):
                d, _ap, note = ig.parse_when(c["parked_until"], order, s.get("country"), today)
                if d is None or re.search(r"^(q[1-4]|[a-z]+)$", fold(c["parked_until"])):
                    d, _ap, note = ig.parse_future(c["parked_until"], anchor, order, s.get("country"))
                when = d
            else:
                when, _ap, _n = ig.parse_future(phrase or "", anchor, order, s.get("country"))
            if when is None:
                c["notes_flags"].append("they named a time to come back, but no date could be read: check it")
                seg = "not_now"
            else:
                c["parked_date"] = when.isoformat()
                c["their_date"] = c.get("their_date") or label_their_date(phrase or "", when, s)
                c["parked_phrase"] = phrase
        if seg != "parked" and last and (today - last).days < s["too_recent_days"] and seg != "past_client":
            add_hold(held, c, "too_recent", "", s, order, revisit=last + timedelta(days=s["too_recent_days"]))
            continue
        if seg == "past_client" and last and (today - last).days < 90:
            add_hold(held, c, "maybe_current", "invoiced or in touch in the last three months", s, order)
            continue
        if c.get("parked_date") and date.fromisoformat(c["parked_date"]) > today and \
                (date.fromisoformat(c["parked_date"]) - today).days > 0:
            pass
        ch, no_reason = pick_channel(c, s)
        pasted = data["kind"] in ("lines", "json") or (data["kind"] == "tracker" and c.get("sheet") == "Contacts")
        if not ch and no_reason.startswith("no email, number") and pasted and not rx("no_contact_words", text_of(c)):
            # a pasted note with no address at all: the founder usually has it in their phone or inbox. Plan them on
            # the first channel they chose that the rules allow, and say plainly what is missing.
            texted = reach_of(c, s)[1]
            ok = [x for x in s["channels"] if x != "text" or texted or not s.get("text_only_if_texted", True)]
            if ok:
                ch = ok[0]
                c["address_needed"] = True
                what = {"email": "email address", "text": "mobile number", "dm": "DM handle"}[ch]
                c["notes_flags"].append(f"no {what} in your notes: add it before sending")
        if not ch:
            add_hold(held, c, "no_channel" if pasted or no_reason[:4] in ("has ", "has a")
                     else "no_contact", no_reason, s, order)
            continue
        c["channel"] = ch
        c["segment"] = seg
        c["why"] = (why if data["kind"] == "tracker" and why else why_line(c, seg))
        if why and data["kind"] != "tracker":
            c["why_note"] = why
        c["why_inferred"] = inferred
        months = months_between(last, today) if last else None
        c["months_since"] = months
        band, band_pts = band_of(months)
        c["band"] = band
        pts = {"group": SEGMENTS[seg]["warmth"], "recency": band_pts}
        if c.get("parked_date") and date.fromisoformat(c["parked_date"]) <= today + timedelta(days=14):
            pts["date arrived"] = 15
        if q1 is not None and isinstance(c.get("value"), (int, float)):
            pts["past value"] = 10 if c["value"] >= q1 else 5 if c["value"] >= q2 else 0
        if (c.get("notes") or c.get("raw") or c.get("context")) and len(str(c.get("notes") or c.get("raw") or "")) > 12:
            pts["their words on file"] = 5
        if "shared inbox address" in c.get("flags", []):
            pts["shared inbox"] = -5
        if ann.get("priority_points") not in (None, ""):
            try:
                pts["you moved them"] = int(float(str(ann["priority_points"])))
            except ValueError as e:
                raise Stop(f"annotation for {c['ref']}: priority_points must be a whole number") from e
        c["score_parts"] = pts
        c["score"] = sum(pts.values())
        touches = SEGMENTS[seg]["touches"]
        offsets = list(SEGMENTS[seg]["offsets"])
        c["template_nums"] = list(range(1, touches + 1))
        if band == "over 36 months" and touches > 3:
            c["template_nums"] = [1, 2, touches]
            touches, offsets = 3, [0, 5, 14]
            c["notes_flags"].append("over three years since you spoke: three touches, not four")
        c["touch_count"] = touches
        c["offsets"] = offsets
        c["context_default"] = not c.get("context")
        c["context"] = c.get("context") or default_context(c, seg, s)
        c["rich_notes"] = rich_notes(c)
        c["when"] = when_text(c, s)
        if prev and c.get("resume_from"):
            c["start_touch"] = c["resume_from"]
        contacts.append(c)
    cross_check(contacts + held)
    dup_rows = {h["row"] for h in held if h.get("held_code") == "duplicate"}
    for c in contacts + held:
        if c.get("same_name_as") and (c["row"] in dup_rows or set(c["same_name_as"]) & dup_rows):
            c["notes_flags"] = [f for f in c["notes_flags"] if not f.startswith("same name as")]
    contacts.sort(key=lambda x: (-x["score"], -(x.get("value") or 0) if isinstance(x.get("value"), (int, float)) else 0,
                                 x.get("months_since") if x.get("months_since") is not None else 999, x["row"]))
    for i, c in enumerate(contacts, 1):
        c["rank"] = i
        c["tier"] = "A" if i <= s["tier_a"] else "B"
    return {"contacts": contacts, "held": held}


ANN_KEYS = {"segment", "hold", "why", "context", "parked_until", "parked_phrase", "came_from", "channel", "detail",
            "last_contact", "email", "phone", "handle", "priority_points", "greeting"}


def apply_contact_fixes(c, ann, s, order):
    """Founder corrections from annotations: a date, an address or a handle the script misread or the notes lacked.
    Each becomes a correction line the founder sees and can veto."""
    today = s["today"]
    if ann.get("last_contact"):
        d, approx, note = ig.parse_when(str(ann["last_contact"]), order, s.get("country"), today)
        if d is None:
            raise Stop(f"annotation for {c['ref']}: last_contact '{ann['last_contact']}' is not a date ({note})")
        c["last_contact"] = d.isoformat()
        c["date_as_given"] = str(ann["last_contact"])
        c.pop("future_date", None)
        c.pop("bulk_date", None)
        c["notes_flags"] = [f for f in c["notes_flags"] if not f.startswith(("date ", "last contact date is in the future",
                                                                              "this date is shared"))]
        if approx:
            c["date_approx"] = note
        else:
            c.pop("date_approx", None)
        if d > today:
            c["future_date"] = True
        c["corrections"].append(f"last contact set to {ann['last_contact']}")
    if ann.get("email"):
        e = str(ann["email"]).strip().lower()
        if not ig.EMAIL_RX.match(e):
            raise Stop(f"annotation for {c['ref']}: '{ann['email']}' is not an email address")
        c["email"] = e
        c["corrections"].append("email added")
    if ann.get("phone"):
        ph = ig.clean_phone(ann["phone"])
        if not ph:
            raise Stop(f"annotation for {c['ref']}: '{ann['phone']}' is not a phone number")
        c["phone"], c["phone_digits"] = str(ann["phone"]), ph
        c["corrections"].append("number added")
    if ann.get("handle"):
        c["corrections"].append(f"DM handle {ann['handle']}")
    if ann.get("priority_points") not in (None, ""):
        c["corrections"].append(f"order changed as you asked ({ann['priority_points']} points)")
    if ann.get("greeting"):
        c["corrections"].append(f"greeting: {ann['greeting']}")
    for k, label in (("segment", "group set to"), ("hold", "held back as"), ("came_from", "came onto the list as"),
                     ("context", "personal field"), ("parked_until", "come-back date")):
        if ann.get(k):
            v = ann[k]
            v = SEGMENTS[v]["label"] if k == "segment" and v in SEGMENTS else HOLD[v][0] if k == "hold" and v in HOLD else v
            c["corrections"].append(f"{label} {v}" + (f" ({ann['why']})" if ann.get("why") and k in ("segment", "hold") else ""))


def rich_notes(c):
    """Their notes hold a specific fact beyond a date and a status: worth a sentence of detail in the messages."""
    t = text_of(c)
    t = re.sub(r"\b\d{1,4}([/.\-]\d{1,4}){0,2}\b", " ", t)
    t = re.sub(r"\b(" + "|".join(ig.MONTH_WORD) + r")\b", " ", t)
    t = re.sub(r"\b(enquired|enquiry|inquired|call|had|a|the|and|then|nothing|since|sent|proposal|no|show|reply|"
               r"response|via|website|form|lastmail|said|went|quiet|ghosted|after|never|booked|client|lapsed|to|of|"
               r"in|on|at|re|it|for|with)\b", " ", t)
    return len(re.findall(r"[a-z]{3,}", t)) >= 4


def cross_check(people):
    """A company one row works at that another row says they chose instead: the first may be a competitor."""
    by_co = {}
    for c in people:
        co = fold(c.get("company"))
        if len(co) > 3:
            by_co.setdefault(co, []).append(c)
    for c in people:
        note = fold(" ".join(str(c.get(k) or "") for k in ("notes", "reason", "raw")))
        for co, owners in by_co.items():
            if c in owners or co not in note:
                continue
            if re.search(r"(went with|chose|stayed with|hired|moved to|signed with|switched to|bei)\W+(\w+\W+){0,3}"
                         + re.escape(co), note):
                for o in owners:
                    o.setdefault("notes_flags", []).append(
                        f"{c.get('name') or c['ref']} chose {o.get('company')} over you, and {o.get('name') or o['ref']} "
                        f"works there: are they a competitor? Check before sending")


def extract_come_back(t, c):
    """The come-back phrase from one field at a time, so a phrase never runs into another field's words."""
    for k in ("reply_notes", "reason", "notes", "raw"):
        v = fold(c.get(k) or "")
        m = re.search(KW["come_back"] + r"[^.;,/\"()\-]{0,40}", v, re.I)
        if m:
            return m.group(0).strip()
    return ""


def add_hold(held, c, code, why, s, order, revisit=None):
    c["held_code"] = code
    c["held_reason"], c["release"] = HOLD[code]
    if why:
        c["held_reason"] = f"{c['held_reason']} ({why})"
    if code == "duplicate" and c.get("duplicate_of"):
        c["held_reason"] = f"Duplicate: merged into C{c['duplicate_of']:03d}"
        c["release"] = f"Nothing; their details are on row C{c['duplicate_of']:03d}."
    if revisit:
        c["revisit"] = revisit.isoformat()
    if code == "check_row":
        c["notes"] = "[notes withheld: they contained an instruction to an AI]"
        c.pop("raw", None)
    held.append(c)


def reach_of(c, s):
    """What this contact can be reached on, from their row: {'email','text','dm'} -> bool, plus texted and handle."""
    t = text_of(c)
    raw = " ".join(str(c.get(k) or "") for k in ("notes", "raw", "handle"))
    texted = bool(rx("texted", t)) or bool(c.get("texted_before"))
    handle = c.get("handle") or (re.search(HANDLE_RX, re.sub(r"\S+@\S+\.\S+", " ", raw.lower())) or [None])[0]
    if handle:
        c["handle"] = handle
    has = {"email": bool(c.get("email")), "text": bool(c.get("phone_digits")), "dm": bool(handle or rx("dm", t))}
    return has, texted


def pick_channel(c, s):
    """The first of the founder's channels, in their order, that this contact can be reached on.
    Texts go only to people who texted before unless the founder allows texts to everyone with a mobile.
    Returns (channel, None) or (None, the plain reason nobody can be messaged)."""
    chans = s["channels"]
    only_texted = s.get("text_only_if_texted", True)
    has, texted = reach_of(c, s)
    can = {"email": has["email"], "text": has["text"] and (texted or not only_texted), "dm": has["dm"]}
    want = fold(c.get("channel") or "")
    want = {"sms": "text", "whatsapp": "text", "instagram": "dm", "linkedin": "dm"}.get(want, want)
    if want in can and want in chans and can[want]:
        return want, None
    if texted and can["text"] and "text" in chans:
        return "text", None
    for ch in chans:
        if can.get(ch):
            return ch, None
    words = {"email": "an email", "text": "a number", "dm": "a DM handle"}
    names = {"email": "email", "text": "texts", "dm": "DMs"}
    chosen = " and ".join(names[x] for x in chans)
    other = [x for x in ("email", "text", "dm") if has[x] and x not in chans]
    if has["text"] and "text" in chans and not texted:
        return None, "has a number but has never texted you, and texts go only to people who texted you first"
    if other:
        return None, f"has {' and '.join(words[x] for x in other)} only, and you chose {chosen}"
    return None, "no email, number or DM handle in your notes"


def why_line(c, seg):
    bits = []
    if c.get("reason"):
        bits.append(str(c["reason"]))
    note = str(c.get("notes") or c.get("raw") or "").strip()
    for k in ("email", "name", "company", "phone"):
        v = str(c.get(k) or "")
        if v and len(v) > 1:
            note = re.sub(r"\(?\s*" + re.escape(v) + r"\s*\)?", " ", note, flags=re.I)
    note = re.sub(r"\s+", " ", note)
    note = re.sub(r"^[\s,;:\-]+|(\s*[,;]\s*)+(?=-)|\s+([,;])", lambda m: "" if m.group(0).strip(" ,;:-") == "" else m.group(0), note)
    note = re.sub(r"\s*,\s*-\s*", ", ", note).strip(" ,;:-")
    if note:
        bits.append(note)
    line = " / ".join(bits)
    if len(line) > 110:
        line = line[:107].rsplit(" ", 1)[0] + "..."
    if not line:
        line = "reason not recorded"
        if c.get("stage"):
            line += f"; furthest stage: {c['stage']}"
        if seg == "past_client":
            bits = []
            if c.get("invoices") not in (None, ""):
                bits.append(f"{c['invoices']} invoices")
            if c.get("value_as_given"):
                bits.append(f"{c['value_as_given']} invoiced")
            if c.get("date_as_given"):
                bits.append(f"last {c['date_as_given']}")
            line = (", ".join(bits) + "; " if bits else "") + "why they stopped: not recorded"
    return line


def when_text(c, s=None):
    s = s or {}
    if not c.get("last_contact"):
        return ""
    d = date.fromisoformat(c["last_contact"])
    note = c.get("date_approx", "") or ""
    given = str(c.get("date_as_given", ""))
    if note.startswith("year only"):
        return str(d.year)
    if not is_english(s):
        return month_year_in(d, s)
    if note.startswith("quarter"):
        m = re.search(r"q([1-4])", fold(given))
        return f"Q{m.group(1)} {d.year}" if m else month_year_in(d, s)
    m = re.match(r"(spring|summer|autumn|fall|winter) \d{4}", fold(given))
    if m:
        return f"{m.group(1)} {d.year}"
    return month_year_in(d, s)


def phrase_for(key, s, when, deal=""):
    """The personal-field phrase in the message language: the founder's own (context_phrases) or the English default."""
    own = (s.get("context_phrases") or {})
    if key in own and own[key]:
        p = own[key]
    elif is_english(s):
        p = CONTEXT_KEYS[key]
    else:
        return ""
    return p.replace("{when}", when).replace("{deal}", deal)


def default_context(c, seg, s=None):
    s = s or {}
    w = when_text(c, s)
    if not w:
        return ""
    deal = str(c.get("deal") or "").strip()
    t = text_of(c)
    met = rx("met", t) is not None
    if seg == "price" and not rx("offer", t) and not re.search(STAGE_OFFER, fold(c.get("stage"))):
        return phrase_for("price_talk", s, w)
    if seg in ("quiet_after_proposal", "price"):
        if deal and len(deal) < 40 and is_english(s):
            d2 = " ".join(x if (x.isupper() and len(x) > 1) else x.lower() for x in deal.split())
            return phrase_for("proposal_deal", s, w, d2)
        return phrase_for("proposal", s, w)
    if seg == "early":
        if met:
            return phrase_for("met", s, w)
        if re.search(r"enquir|inquir|contact form|web form|form fill|asked (about|for)|requested|anfrage|angefragt|"
                     r"kontaktformular|demande|consulta|signed up|newsletter|anmeldung", t):
            return phrase_for("enquiry", s, w)
        c.setdefault("notes_flags", []).append(
            "your notes do not say who wrote first, so the message says 'our last exchange', not 'your enquiry': "
            "change it if they enquired")
        return phrase_for("exchange", s, w)
    if seg == "no_show":
        return phrase_for("booked_call", s, w)
    if seg == "past_client":
        y = str(date.fromisoformat(c["last_contact"]).year)
        if deal and len(deal) < 30 and is_english(s):
            return phrase_for("work_deal", s, y, deal)
        return phrase_for("work", s, y)
    if seg == "unfinished":
        return phrase_for("conversation" if rx("call", t) else "exchange", s, w)
    return phrase_for("exchange", s, w)


def tracker_state(c, s, ann):
    """Return run: read the status the founder set and decide what happens next."""
    today = s["today"]
    status = fold(c.get("status") or "not started")
    if c.get("sheet") == "Held back":
        code = fold(c.get("held_code") or "")
        code = code.replace(" ", "_")
        if code in PERMANENT or code in ("off_limits", "check_row", "duplicate", "current", "replied"):
            return None, code if code in HOLD else "off_limits", "", False, []
        if code == "too_recent" and c.get("revisit"):
            rv = c["revisit"] if isinstance(c["revisit"], date) else ig.parse_when(c["revisit"], "dmy", "", today)[0]
            if rv and rv > today:
                return None, "too_recent", "", False, []
        if code in ("cooldown", "retired", "replied_later", "bounced") and c.get("revisit"):
            rv = c["revisit"] if isinstance(c["revisit"], date) else None
            if rv and rv > today:
                return None, code, "", False, []
        if code in ("bounced",) and not ann.get("segment"):
            return None, "bounced", "", False, []
        timed = code in ("too_recent", "cooldown", "retired", "replied_later")
        reachable = code in ("no_contact", "no_channel")
        if ann.get("segment") or ann.get("came_from") or ann.get("hold") or ann.get("last_contact") or timed or reachable:
            return classify(c, s, ann)
        # everything else stays held as the founder left it (source unknown, bought, a date to check, may still be a
        # client...) until they say otherwise in this run
        return None, code if code in HOLD else "off_limits", "", False, []
    if ann.get("hold"):
        return None, ann["hold"], ann.get("why", ""), False, []
    seg_key = LABEL_TO_KEY.get(fold(c.get("group")))
    if ann.get("segment"):
        seg_key = ann["segment"]
    if status in ("replied", "call booked", "won"):
        return None, "replied" if status != "won" else "current", c.get("reply_notes", ""), False, []
    if status in ("stopped",):
        return None, "asked_to_stop", c.get("reply_notes", ""), False, []
    if status == "bounced":
        return None, "bounced", "", False, []
    cd = c.get("cooldown_until")
    cdd = cd if isinstance(cd, date) else (ig.parse_when(cd, "dmy", "", today)[0] if cd else None)
    dates = touch_dates_of(c, today)
    sent = [d for d in dates if d < today]
    if status == "no reply" or (status == "sent" and dates and len(sent) >= len(dates)):
        last_sent = max(sent) if sent else today
        until = cdd or add_months(last_sent, s["cooldown_months"])
        c["revisit"] = until.isoformat()
        if until > today:
            return None, "cooldown", "", False, []
        return seg_key or "not_now", None, "", False, []
    if status == "sent" and dates:
        c["resume_from"] = len(sent) + 1
        c["notes_flags"] = c.get("notes_flags", []) + [f"touches 1 to {len(sent)} already sent; resuming at {len(sent) + 1}"]
    if not seg_key:
        return classify(c, s, ann)
    return seg_key, None, str(c.get("why") or ""), False, []


def touch_dates_of(c, today):
    raw = c.get("touch_dates")
    if not raw:
        return []
    out = []
    for part in re.split(r"[;,]\s*", str(raw)):
        d = ig.parse_when(part.strip(), "ymd" if re.match(r"\d{4}-", part.strip()) else "dmy", "", today)[0]
        if d:
            out.append(d)
    return out
