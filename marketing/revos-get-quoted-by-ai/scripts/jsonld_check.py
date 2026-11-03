#!/usr/bin/env python3
"""Check JSON-LD structured data before it goes on a site.

Usage:
  python3 scripts/jsonld_check.py <file.json or page.html> [...] [--page site-files/page-x.html] [--facts facts.json]
        [--reviews-shown] [--allow-faq]
      Parses each block (a parse error is reported with its line and column), and fails: a type that is
      not a real schema.org type in the list below, a missing @context, any placeholder ([NEED, TODO,
      example.com, lorem), a rating or review unless --reviews-shown (the page shows those real reviews),
      FAQ markup without --allow-faq (the founder asked for it) or whose questions and answers are not on
      --page word for word, a price written with symbols, a currency that is not a three-letter code, and
      any phone, email or web address that is not in the fact register.
Exit 0 clean, 1 with PROBLEM lines, 2 with STOP. No network calls.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import domain_of, load_json, norm, read_text, stop, strip_html  # noqa: E402

# A vendored subset of schema.org types (schema.org vocabulary, version 29), the ones a service or
# expert-led business plausibly needs. A real type outside this list is reported so it can be checked.
TYPES = set("""
Thing Organization Corporation LocalBusiness ProfessionalService Person Service Offer AggregateOffer OfferCatalog
PriceSpecification UnitPriceSpecification CompoundPriceSpecification MonetaryAmount QuantitativeValue PostalAddress
Place City State Country AdministrativeArea GeoCircle GeoCoordinates ContactPoint OpeningHoursSpecification WebSite
WebPage AboutPage ContactPage FAQPage QAPage Question Answer ItemList ListItem BreadcrumbList Article BlogPosting
ImageObject Brand EducationalOccupationalCredential Occupation DefinedTerm Audience BusinessAudience Rating
AggregateRating Review HowTo HowToStep Course Event VideoObject CreativeWork ServiceChannel
AccountingService FinancialService LegalService Attorney Notary HomeAndConstructionBusiness GeneralContractor
HousePainter Electrician Plumber RoofingContractor HVACBusiness Locksmith MovingCompany LandscapingBusiness
HealthAndBeautyBusiness BeautySalon HairSalon DaySpa MedicalBusiness MedicalClinic Dentist Physician Optician
Pharmacy MedicalOrganization FoodEstablishment Restaurant CafeOrCoffeeShop Bakery EducationalOrganization School
AutomotiveBusiness AutoRepair ChildCare EmploymentAgency EntertainmentBusiness Store RealEstateAgent TravelAgency
SportsActivityLocation ExerciseGym LodgingBusiness Hotel ComputerStore InternetCafe Library RecyclingCenter
SelfStorage ShoppingCenter TouristInformationCenter AnimalShelter ArchiveOrganization DryCleaningOrLaundry
EmergencyService GovernmentOffice RadioStation TelevisionStation NGO SoftwareApplication WebApplication
Product SpeakableSpecification
""".split())
RATING_KEYS = {"aggregateRating", "review", "reviews"}
PLACEHOLDER = re.compile(r"\[NEED|\bTODO\b|\bTBC\b|\bTBD\b|example\.com|yourdomain|your-domain|lorem ipsum|\bXXX\b|\{\{\s*\w+\s*\}\}", re.I)
URL_KEYS = {"url", "sameAs", "@id", "logo", "image", "mainEntityOfPage", "hasMap", "item"}


def nodes(data):
    out = []

    def walk(o):
        if isinstance(o, dict):
            out.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(data)
    return out


def blocks_from(path):
    raw = read_text(path, "the structured data")
    if path.endswith((".html", ".htm")):
        found = re.findall(r'(?is)<script[^>]+application/ld\+json[^>]*>(.*?)</script>', raw)
        if not found:
            return [], [f"{os.path.basename(path)}: no JSON-LD block found"]
        return [(f"{os.path.basename(path)} block {i}", b) for i, b in enumerate(found, 1)], []
    return [(os.path.basename(path), raw)], []


def check_block(label, raw, page_text, facts, reviews_shown, allow_faq):
    probs = []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        hint = ""
        lines = raw.splitlines()
        prev = lines[e.lineno - 2].rstrip() if e.lineno >= 2 and e.lineno - 2 < len(lines) else ""
        if prev.endswith(",") and (lines[e.lineno - 1].strip()[:1] in "}]" if e.lineno - 1 < len(lines) else False):
            hint = " (a trailing comma before a closing bracket)"
        return [f"{label}: does not parse, line {e.lineno}, column {e.colno}: {e.msg}{hint}. Engines ignore a block that does not parse"]
    ctx = json.dumps(data.get("@context", "") if isinstance(data, dict) else [d.get("@context", "") for d in data if isinstance(d, dict)])
    if "schema.org" not in ctx:
        probs.append(f"{label}: no @context of https://schema.org")
    if PLACEHOLDER.search(raw):
        probs.append(f"{label}: holds a placeholder ('{PLACEHOLDER.search(raw).group(0)}'); leave the field out until the fact is confirmed")
    reg = " ".join(f"{f.get('value', '')}" for f in (facts or {}).get("facts", []) if f.get("status") == "confirmed").lower()
    reg_digits = re.sub(r"\D", "", reg)
    sites = {domain_of(u) for u in re.findall(r"[a-z0-9.-]+\.[a-z]{2,}(?:/\S*)?", reg)}
    for n in nodes(data):
        t = n.get("@type")
        for tt in (t if isinstance(t, list) else [t] if t else []):
            if tt not in TYPES:
                probs.append(f"{label}: @type '{tt}' is not in the checked list of schema.org types; use a listed type or check it on schema.org")
            if tt in ("AggregateRating", "Review") and not reviews_shown:
                probs.append(f"{label}: {tt} is only allowed when the page itself shows those real reviews")
            if tt == "FAQPage" and not allow_faq:
                probs.append(f"{label}: FAQ markup is added only when the founder asks for it (Google retired the FAQ rich result on 7 May 2026)")
        for k in RATING_KEYS & set(n):
            if not reviews_shown:
                probs.append(f"{label}: '{k}' removed: ratings and reviews are marked up only when the page shows them")
        if n.get("@type") == "Question":
            q = n.get("name") or ""
            ans = n.get("acceptedAnswer") or {}
            a = ans.get("text") if isinstance(ans, dict) else ""
            if page_text is None:
                probs.append(f"{label}: FAQ markup needs --page, the page whose questions it describes")
            else:
                if norm(q) not in norm(page_text):
                    probs.append(f"{label}: FAQ question '{q[:50]}' is not on the page word for word")
                if norm(strip_html(a or "")) not in norm(page_text):
                    probs.append(f"{label}: the answer to '{q[:40]}' is not on the page word for word")
        if "priceCurrency" in n and not re.fullmatch(r"[A-Z]{3}", str(n["priceCurrency"])):
            probs.append(f"{label}: priceCurrency '{n['priceCurrency']}' must be a three-letter code such as USD or EUR")
        for pk in ("price", "minPrice", "maxPrice"):
            if pk in n and not re.fullmatch(r"\d+(\.\d+)?", str(n[pk])):
                probs.append(f"{label}: {pk} '{n[pk]}' must be a plain number such as 4800 or 1850.00 (no symbols or separators)")
        if facts:
            tel = n.get("telephone")
            if tel and re.sub(r"\D", "", str(tel)) not in reg_digits:
                probs.append(f"{label}: telephone '{tel}' is not in the fact register")
            em = n.get("email")
            if em and str(em).lower().replace("mailto:", "") not in reg:
                probs.append(f"{label}: email '{em}' is not in the fact register")
            for k in URL_KEYS & set(n):
                vals = n[k] if isinstance(n[k], list) else [n[k]]
                for v in vals:
                    if isinstance(v, str) and v.startswith("http"):
                        if domain_of(v) not in sites and not any(domain_of(v).endswith("." + s) for s in sites):
                            probs.append(f"{label}: {k} '{v}' is not an address in the fact register")
        if isinstance(t, str) and t in ("Organization", "LocalBusiness", "ProfessionalService", "Person", "Service") and not (n.get("name") or n.get("serviceType")):
            probs.append(f"{label}: a {t} needs a name")
    return probs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--page")
    ap.add_argument("--facts")
    ap.add_argument("--reviews-shown", action="store_true")
    ap.add_argument("--allow-faq", action="store_true")
    a = ap.parse_args()
    page_text = strip_html(read_text(a.page, "the page")) if a.page else None
    facts = load_json(a.facts, "the fact register") if a.facts else None
    probs, n = [], 0
    for f in a.files:
        blocks, p = blocks_from(f)
        probs += p
        for label, raw in blocks:
            n += 1
            probs += check_block(label, raw, page_text, facts, a.reviews_shown, a.allow_faq)
    for p in probs:
        print("PROBLEM:", p)
    print(f"JSON-LD: {n} block(s) checked")
    print(f"{len(probs)} problems")
    return 1 if probs else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main())
