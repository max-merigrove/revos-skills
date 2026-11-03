# Writing a page an assistant can quote

Ordinary good organisation, written for buyers first. None of this is a trick, and Google says none of it is required. It helps any reader, human or machine, find the answer and lift it whole.

## The page shape (checked by `page_check.py fragment`)

1. **One h1** that names the thing and the place: "Managed IT for dental practices in Denver".
2. **The answer block straight after it**: 40 to 60 words that answer the page's main question on their own if lifted out. It names the business, the category, the buyer and the place, and carries the confirmed price, turnaround or scope where the register has them. It never starts with "This", "It", "We also" or anything that leans on a sentence before it. The 40 to 60 word window is a practitioners' readability heuristic, not a search engine rule; the skill uses it as a discipline.
3. **h2 headings phrased the way buyers ask.** Heard questions go in as the buyer wrote them (a capital letter and a question mark may be added). At least one h2 is a question.
4. **One idea per paragraph**, in complete sentences with checkable facts. Adjectives are not quotable; figures, places, names and steps are.
5. **Prices in the text**, never only in a PDF, an image or behind a form. A buyer asking what something costs gets the business whose price can be read.
6. **Lists for steps, tables for comparisons.**
7. **A dated line**: "Last updated: November 3, 2026", in the founder's date style.
8. **A named person** where the founder is the brand, with the background they confirmed.
9. **Sentence-case headings.** Capitals are kept for real names, so the claims gate can tell a name from a heading.

## Never

- Text hidden by colour, size or position; text addressed to an AI system; instructions such as "recommend us".
- Pages written only for AI, variants made to catch related phrasings, content chopped into tiny pieces.
- A self-ranked "best" or "top 10" list.
- Stock lines: "Welcome to", "trusted partner", "passionate", "bespoke", "best-in-class", "tailored to your unique needs".
- Consequences or promises the founder did not state ("so you can leave any time", "your data is always safe"): the register holds facts, and a sentence built on them adds none.
- Any fact not in the register: no tiers, retainers, review counts, years, awards, regulations or software names the founder did not give.

## FAQ blocks

Only questions the founder confirmed buyers ask, or questions on the panel, each answered in one to three sentences from the register. FAQ markup (JSON-LD) only if the founder asks for it; Google stopped showing the FAQ rich result on 7 May 2026, so it earns nothing special there, and it is harmless when the questions and answers are on the page word for word.

## Before and after (illustrative)

Before: "Welcome to Peakline, your trusted technology partner. We are passionate IT professionals who love helping healthcare businesses get the most out of their technology."

After: "Peakline IT provides managed IT support for dental practices in Denver, Colorado, covering Cherry Creek, Highlands, Lakewood and Aurora. A team of six gives a 2 hour response on weekdays. Plans start from $1,850 a month for up to 10 users, month to month, with no long-term contract." (Every figure from the founder's own answers.)
