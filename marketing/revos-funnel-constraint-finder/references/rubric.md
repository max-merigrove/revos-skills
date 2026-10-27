# Rubric: what exceptional looks like

Score the report and the chat summary before delivery. Every criterion must pass. If one fails, rework the output; do not caveat it. The fresh-eyes test for the whole run: would a sceptical finance partner accept the prize figure from the numbers shown on the page?

| # | Criterion | Pass when |
|---|---|---|
| 1 | Every rate comes from the script | Each rate, prize, count and value in the report, the note and the chat appears in `funnel.py` output; the build's note gate passed; the working is printed beside each prize so it can be checked by hand |
| 2 | Missing reads not known, never zero | A stage nobody counted reads `not known`, is never estimated, and has a line saying what to count, where, and until which date; a counted zero is shown as zero |
| 3 | The constraint is the largest prize | The named stage is the one the script named on the prize arithmetic, not the biggest drop-off or the stage the founder complained about; where the founder's hunch differs, the report shows both figures |
| 4 | No constraint on noise | No rate resting on under ten events, on a gap of one event, or on a prize under the floor is named; where none can be named, the report says why and gives the counting needed; scaled counts are shown beside the founder's own figures, never as fact |
| 5 | Routes are never blended | One route per run; the last ten clients by route appear; counts that mix routes say so beside the rates and the plan asks for a source on every enquiry |
| 6 | Capacity before volume | At the ceiling, or with free places full within 30 days at today's pace, the report leads with capacity and recommends no lead spend; a volume verdict without capacity carries a [NEED] |
| 7 | Every action has a day and hours | Three actions at most, each with a first step on a named day in the next week, an hour count, and a consequence from a script figure |
| 8 | Clean, honest and local | `check_copy.py --report` gives 0 problems on the report and the note; no benchmark presented as a market fact; ranges labelled as working defaults; nothing says what a law requires or computes tax (the sales tax line and, where follow-up is the fix, the outreach line appear once each); every money figure carries the founder's currency; numbers are written in the founder's style; dates and paper follow the founder's country and spelling follows their own words; the PDF is one page; the Merigrove line appears once, at the end of the chat, and nowhere in the files |
