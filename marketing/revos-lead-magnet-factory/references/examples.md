# Worked examples

Two illustrative businesses, invented for this file. Both were built and checked with the scripts; the figures below are what the scripts printed.

## 1. A scorecard: Lindqvist Brand Studio, Gothenburg

**What the founder pasted:** "We're a two-person brand studio in Gothenburg. Clients are B2B software companies, usually 15 to 60 people. Almost every first call starts with "our brand doesn't match what we've become". ... Our main offer is a brand foundation sprint, 85 000 kr, six weeks. Under 10 people we're too early for them. We sign off "Anna & Erik"."

**First reply, in short.** Read back: a brand foundation sprint at 85 000 kr for B2B software companies of 15 to 60 people; under 10 is too early; signs "Anna & Erik". Three problems, each with its line: the brand no longer matches the company (quoted, most repeated); the look dates from the founders' first weekend; a sales team that has grown past the brand. Recommended: a scorecard, because founders arrive with a feeling and want to know where they stand, and one fit question on headcount separates a sprint client from a company that is too early. Draft questions on five areas: the one-line description, the website, the sales deck, the look, hiring. Then three questions: confirm the five areas, the booking link, and Swedish or English for the page. Number style read as comma decimals with space grouping ("85 000 kr"); every figure written back that way.

**The spec** is `assets/spec-template.json` in full. Its shape:

| Part | Content |
|---|---|
| Title | Has your company outgrown its brand? |
| Questions | The one-line description; the website; the sales deck; the look; hiring. Four options each, 0 to 3 points, options describing behaviour ("Each seller has their own version") |
| Fit | How many people work at your company? Fewer than 10 (not a fit) / 10 to 60 / More than 60 |
| Tiers | Still the launch brand (0 to 5); Partly caught up (6 to 9); Matches the company (10 to 15) |
| Door | You can see where your brand lags behind. What should it become? |
| Not a fit | Under 10 people it is too early for a brand sprint. The fixes above are the right start. |

**Simulation output:**

```
Answer sets walked: 1024. Scores run 0 to 15.
  Still the launch brand (0 to 5): 222 sets, 21.7%
  Partly caught up (6 to 9): 580 sets, 56.6%
  Matches the company (10 to 15): 222 sets, 21.7%
Middle pattern: 7.5 points, lands in 'Partly caught up'.
```

A first draft banded the middle tier 6 to 10; the simulation put 66.5 per cent of answer sets there and blocked the build. Moving one point to the top tier fixed it.

**The emails** (signed "Anna & Erik"): 1 "Your brand scorecard" delivers the link and says to read what works first; 2 "What your score is telling you" has one paragraph per tier and asks for a reply with the score; 3 "One sales deck, before and after" is an illustration, labelled as one; 4 "What the scorecard cannot decide" is the door (what the brand should become); 5 "Who our brand sprint is for" names the price, who it is for and who it is not for, and carries the only booking link.

Email two in full:

> Hi {{first_name}},
>
> The scorecard puts you in one of three places.
>
> Still the launch brand: start with the one sentence. Until the team describes the company the same way, a new logo will not help, because the words around it will still disagree.
>
> Partly caught up: look at the sales deck. It is where the old story and the new one meet a buyer at the same time, and your sellers have probably already rewritten it for you.
>
> Matches the company: your work is keeping it there as you hire. Give every new person the one sentence in their first week.
>
> Reply with your score and the gap you want to close first. It helps us write the next emails for the people actually reading them.
>
> Anna & Erik
>
> P.S. In two days: an example of one deck, before and after.

**Why it passes the rubric:** the topic is the founders' quoted line; the scorecard never promises a new brand (criterion 2); headcount and the "not for" line are two fit signals (3); the simulation passes (4); the claim scan finds nothing, and the price appears only as the founder wrote it (5); about two minutes by estimate (6); the page audit passes (7); comma-decimal numbers, their sign-off, their English (8).

## 2. A checklist: Pine Row Freight Advisory, Toronto

**What the founder pasted:** notes listing what he tells every client "roughly in order", the opening line of every call ("my container is stuck and nobody can tell me why"), a shipment review at CAD 2,400, and "Not a fit: people shipping one parcel by courier."

**Diagnose:** the value is an order of steps, so a checklist. It also works as a download for a founder who would rather not host a page.

**The checklist:** "The 12-point pre-shipment checklist for small importers", for Canadian importers bringing in full containers. Every item is one of his notes, in his order, with the note quoted as its `source_quote`:

| Section | Items |
|---|---|
| Before it ships | Get the commercial invoice right before it ships; match the HS code on the invoice to your broker's; confirm you are the importer of record; check the packing list against the invoice, line by line; have the bill of lading checked before the ship leaves; know your Incoterm and who pays for what; book your customs broker before the goods ship |
| Before it arrives | Send your broker the documents five days before arrival; plan for an inspection; budget for storage if the container is held |
| After | Keep one folder per shipment; debrief after every shipment |

Each item carries one or two sentences ("Five days gives your broker time to find problems while the ship is still at sea."). Nothing about duty rates, regulations or what any authority requires: those are his clients' questions for their broker, and the checklist says nothing a rule book would have to settle. What it does not cover (the door): why their last shipment was held, and what to change for their products. That is the shipment review.

**The emails:** 1 delivers the checklist and says to start with the invoice; 2 the step his clients most often get wrong, from his notes (documents to the broker five days before arrival), asking them to reply with the step that caught them last time; 3 an illustration of a held container, labelled; 4 the door; 5 who a shipment review is for and not for (not for one parcel by courier), with the only booking link. Result map keyed by reply: "Their shipment is held right now" and "They have never been held".

**Checks:** `validate` 0 problems; the claim scan 0; Canadian spelling, CAD, Letter paper from the country code.
