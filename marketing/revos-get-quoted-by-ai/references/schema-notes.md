# Structured data (JSON-LD): what to write and what never to write

Structured data states who the business is and what it offers in a form engines parse reliably. No well-documented study isolates a lift in AI citations from it, and Google says none is required for its AI answers. The skill ships it as cheap, correct tidiness.

## The default set

- `entity.jsonld.json`: one block for the business. Type `ProfessionalService` for most service firms, or a closer listed type where one fits (`AccountingService`, `LegalService`, `Dentist`, `HomeAndConstructionBusiness`, `LandscapingBusiness`, `Restaurant` and others in `jsonld_check.py`). Fields only from the register: `name`, `url`, `description`, `areaServed`, `address` (town and country only unless the founder gives a street address to publish), `email` or `telephone` only if confirmed, `knowsLanguage`, `founder` as a `Person` where the founder is the brand. Use an `@graph` when there is a Person.
- `service-<slug>.jsonld.json`: one `Service` per distinct service, saved under the slug of the page that describes it (a pricing page for the same service gets no copy; identical files are refused), with `provider` pointing at the entity's `@id`, `areaServed`, and an `Offer` whose `priceSpecification` carries the confirmed price as a plain number (`"1850"`, `"4800"`) and a three-letter currency (`"USD"`). A range uses `minPrice` and `maxPrice`. The Offer's `description` repeats the price as the founder writes it.

## Never

- `AggregateRating` or `Review` unless the page itself shows those reviews. Reviews on a map listing or another site do not count. Marking up reviews a page does not show is fabrication.
- `FAQPage` unless the founder asks for it; then only questions and answers that are on the page word for word (checked with `--page`).
- Placeholders: `[NEED]`, TODO, example.com, empty strings. Leave a field out until the fact is confirmed.
- Phone numbers, emails, street addresses or links not in the register.
- Prices with symbols or separators in `price` fields.

## Where it goes

Inside `<script type="application/ld+json">` and `</script>` in the page's custom code or header setting. Website builders call this code injection, custom code or header scripts. The entity block goes on the home page (or every page); each service block goes on its own page only.

## Checking

`jsonld_check.py` parses each block (a parse error is reported with its line and column, often a trailing comma), checks types against a vendored list of schema.org types, and applies the rules above. A real schema.org type outside the list is reported so it can be checked by hand rather than guessed.
