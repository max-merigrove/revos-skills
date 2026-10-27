# Who sells, and "I" or "we"

Merigrove's founder-led brand ladder has three rungs:

1. **Founder-fronted.** The founder is the brand. Buyers choose a person they have come to trust. Most businesses of one to five people sit here, and should.
2. **Founder-endorsed.** The founder vouches; the business carries its own proof (a named method, case studies, a second person who delivers).
3. **Firm-fronted.** The business is the authority. Rarely right while the founder still sells, because the business has no proof of its own to stand on.

The move up a rung is earned by proof the business owns, not declared by a rebrand. The commonest mistake the scan finds is a website rewritten in a corporate "we" while the LinkedIn, the calls and the proposal are still one person. Buyers then meet the founder and wonder who "we" was.

## How the scan uses it

- **Intake question 1** sets `founder_sells`: me, me and others, a team.
- **Voice drift** counts "I" and "we" per asset and flags the split. When the founder sells personally, any asset that speaks mainly as "we" is flagged: "Buyers meet you, so 'we' here describes a team they may never speak to."
- **The recommended line**, when the founder sells personally, keeps them visible: "I", their name, or no pronoun. `build_report.py` refuses a recommended line that says "we" without "I" in that case.
- **Me and others:** "we" is fine where others deliver, but the line should still name what the founder personally does if they are the one buyers meet.
- **A team sells:** "we" is right. Flag "I" only where it promises the founder's personal time the team will deliver.

This is a reading of the assets, not a verdict on the founder's ambition. If the founder says they are deliberately moving to founder-endorsed, keep "we" in the line and record it as a learning for the Make step.
