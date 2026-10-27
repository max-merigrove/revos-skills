# Hours check and the one-week time log

Founders under-report delivery hours: they remember the call and forget the prep, the follow-up, the chasing and the rework. The ceiling is only as good as the step hours, so the skill checks them two ways.

## 1. The quick check (every run)

Ask, inside the hours question: "And roughly how many hours a week does delivery take you now?" Pass it as `delivery_hours_now_week`. Run compute on every reply, provisional figures included: the script compares it with the hours the founder's steps add up to and reports a gap above 15 per cent (`references/method.md` section 9). When the steps come up short, compute prints the question; ask it once, in the next reply, beside the provisional figures: "Your steps come to X hours a month but you said delivery takes Y. What's missing: client messages, chasing, rework, travel, team time?" Add what they name as steps and run again. Over 30 per cent short, build refuses until the steps are added or the founder says they cannot place the hours (`"confirmed": ["hours_gap"]`); the reading then says the ceiling reads high.

## 2. The one-week time log (offered, never required)

Offer it when the founder cannot say what delivery takes, when the gap is large and they cannot place it, or when they say "I've no idea where the time goes". Say in one line: "Want a truer number? Log one normal week and I'll redo the check from it." Give them `assets/time-log-template.csv` (or paste the columns) and these rules:

1. Log for five working days, in blocks of 15 minutes or more, as you go, not at the end of the day.
2. One row per block: date, start, minutes, client or offer, what you did, and whether it was delivery, selling or admin.
3. Count everything you did for a client: messages, prep, rework, travel.
4. Pick a normal week, not a launch week or a holiday week.

When they bring it back:
- Sum minutes by client and activity yourself only through the script: pass each step's hours as the parts, for example `"=(45+30+20)/60"`, and let `capacity.py` work them out. Never add a column by eye.
- Turn the week's totals into steps: a week's minutes on an activity for one client, divided by 60, is the hours each time for a weekly step.
- Delivery hours now = the week's delivery minutes / 60.
- Selling and admin minutes tell you what to take off their working hours for the available figure.

Save the corrected hours to memory with a learning if the log showed a steady gap ("Reporting takes twice the stated hours in quarter-end months", step: hours).
