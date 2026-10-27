# The verdicts file

Write this JSON in your scratch folder after reading the whole transcript and the measure output. `score_call.py score` checks every field against the transcript and the method, then works out the numbers. Positions are copied exactly as the measure output prints them (`16:32`, `1:02:03` or `T14`). Every `quote` is word for word from the turn at that position (cut with `...` if long). Everything you write yourself uses the prospect's initials, never their name.

```json
{
  "mode": "transcript",                       // or "recall"
  "business": "Okafor Studio",
  "seller": "Dan Okafor",                     // as the transcript labels them
  "seller_is": "founder",                     // or "closer"
  "prospect": "SM",                           // initials from the measure output
  "prospect_name": null,                      // recall only: the name the founder used, or "not given"; checked for, never printed
  "third_parties": [],                        // optional: names the prospect mentioned that the measure did not list
  "call_date": "2026-10-07",
  "date_style": "day month year",             // the founder's: "day month year", "month day year" or "year month day"
  "country": "GB",                            // the founder's country (ISO code) from read_founder.py, or null; sets the paper size
  "spelling": "British",                      // from the founder's own messages: American, British, Indian ...; sets the proofing language
  "sources": {"business": "call", "offer": "founder said"},   // optional: where business and offer came from, for memory
  "call_type": "first call",                  // "first call", "second call" or "proposal review"
  "offer": "website design and build, £6,500",  // price exactly as said, in the currency said; never converted or taxed
  "structure": "default",                     // or the founder's stages: [{"name": "...", "maps_to": 1}, ...]
  "length_minutes": null,                     // recall only: the founder's estimate
  "headline": "One sentence: the moment that cost the most, where it was created, what it caused.",
  "what_happened": "Three to six sentences of diagnosis, not summary.",

  "stages": [                                 // one per stage, the founder's or the five standard ones
    {"n": 1, "name": "Opening and Frame", "verdict": "partial", "at": "00:16", "quote": "...",
     "note": "what the transcript shows", "say_instead": "the words to use next time"}
  ],                                          // missed stages need no "at"; partial and missed need "say_instead"

  "dimensions": {                             // all five; the rung (method section 3) sets the score, before caps
    "Intro and Frame":         {"rung": "one_element", "at": "00:16", "quote": "...", "why": "one line"},
    "Discovery and Gap Build": {"rung": "layers_no_gap", "at": "...", "quote": "...", "why": "..."},
    "Cost of Inaction":        {"rung": "seller_supplied", "at": "...", "quote": "...", "why": "..."},
    "Objection Handling":      {"rung": "acknowledged", "at": "...", "quote": "...", "why": "..."},
    "Close Attempt":           {"rung": "price_answered_or_cut", "at": "...", "quote": "...", "why": "..."}
  },                                          // leave "score" out; if given it must equal the rung's

  "flags": [                                  // confirmed failures only (method section 4)
    {"flag": "frame_no_control", "at": "00:16", "quote": "...", "note": "..."}
  ],                                          // pitched_before_pain, frame_no_control, coi_missing_then_stall, folded
  "dismissed_flags": [                        // every candidate the measure printed and you did not confirm
    {"flag": "pitched_before_pain", "at": "02:41", "why": "she had named the problem at 00:58"}
  ],                                          // also used for a deadline, promise or untrusted line that is not one

  "coi_at": "16:55",                          // first question about what the problem costs, or null
  "offer_made": {"made": true, "amount": "£6,500", "at": "16:32"},
  "price_before_cost": false,                 // recall only: the founder's account of the order

  "objections": [
    {"at": "24:05", "quote": "...", "belief": "the belief underneath",
     "loop": {"isolated": false, "belief_named": false, "validated": true,
              "cost_exposed": false, "reframed": false, "shift_confirmed": false},
     "folded": false, "note": "...", "say_instead": "..."}
  ],

  "next_step": {
    "grade": "prospect_in_control",           // "closed", "decision_call_booked" or "prospect_in_control"
    "date": null, "agenda": null,             // for a booked decision call
    "exchange": [{"at": "40:18", "quote": "..."}, {"at": "40:25", "quote": "..."}],
    "note": "..."
  },

  "creation_points": [                        // one per confirmed flag ("for": the flag) and one for a failed next step
    {"for": "next_step", "failure": "She left to think it over",
     "appeared_at": "40:18", "appeared_quote": "...", "created_at": "16:32", "created_quote": "...",
     "what_happened": "..."}
  ],

  "coaching": [                               // exactly two
    {"title": "Ask what the drop costs before you say the price", "at": "16:32", "quote": "...",
     "cause_effect": "Because ..., the prospect ...", "fix": "one tangible change",
     "say": "the full line to say next time"}
  ],                                          // recall: "described" in place of "at" and "quote"

  "drill": {"behaviour": "...", "reps": "five times", "by": "before your next sales call",
            "dimension": "Cost of Inaction"}, // dimension: the one it trains; must match a pattern if one fires

  "worked": {"at": "02:14", "quote": "...", "why": "..."},

  "red_lines": [                              // price_before_cost is added by the script when it applies
    {"kind": "price_asked_early", "at": "16:20", "quote": "...", "note": "..."}
  ],                                          // kinds: price_asked_early, deadline, promise, untrusted

  "way_back_in": {                            // open deal left with the prospect: required (method section 9)
    "why": "one or two sentences: what is pending and why this message gets the next step back",
    "message": "Hi [name], ... one question that isolates what is in the way, and a call on two named days"
  },                                          // under 120 words; names of people she mentioned allowed; nothing the founder has not stated

  "outcome": "lost",                          // "won", "lost", "open" or "not a fit"
  "stated_reason": "what the prospect said, or 'not given'",
  "real_reason": {"reason": "Price or value belief unresolved", "at": "16:32", "note": "..."},

  "defaults": ["each default you used, in one line, so the founder can correct it"]
}
```

Comments above are for reading only; the file itself is plain JSON with no comments.

## What the scorer refuses

- A dimension with no rung, a score that differs from its rung, an Objection Handling rung the six-step record does not support, a Close Attempt rung that does not fit the next step or the offer, a Cost of Inaction rung that disagrees with `coi_at`, or `not_recalled` in a transcript review.
- An open deal left with the prospect and no `way_back_in.message`, or one over 120 words.
- A `say` or `say_instead` holding its own double quotation marks (it is printed inside a pair): single quotation marks for the prospect's words, square brackets for a direction.
- In a recall review, a moment placed by the clock ("at about 40 minutes", "40 mins in").
- A position that is not the start of a turn, or a quote not found word for word in that turn.
- An objection quote that is the seller's, not the prospect's.
- A measure candidate (failure, deadline, promise, untrusted line) neither confirmed nor dismissed with a reason.
- More or fewer than two coaching points; a cause and effect that does not start "Because"; no line to say; a framework named at the seller.
- A drill that asks the founder to read or watch anything.
- A confirmed failure, or a failed next step, with no creation point; a creation point created after it appeared.
- Close Attempt above 4 when the prospect was left in control.
- A lost deal without a stated reason and a real reason from the nine; timing as the real reason when the cost was never made real.
- The prospect's name, blame, banned or held-out wording in anything you wrote.
- When the pattern check fires, a drill aimed at a different dimension.
- A call date with no `date_style`: the founder's date order comes from their country or a date they wrote, never assumed.
- A recall review with no `prospect_name` ("not given" is an answer), or that name anywhere in what you wrote.
- A person the prospect named (listed by the measure as "People the prospect named", or in `third_parties`) outside a quote, a `say` or a `say_instead`.
- In anything you wrote: a statement of what a law requires, a named law or regulator, a lawyer by a country's title, or tax worked out on a price.
