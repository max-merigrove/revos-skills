# Crawlers and what blocking each one means

The data lives in `agents.json` (read by `robots_check.py`), one row per crawler with its operator, purpose, what blocking it does, the source page and the date the row was checked. This file explains the three purposes.

| Purpose | What it does | If the founder blocks it |
|---|---|---|
| search | Feeds an assistant's or search engine's answers and links: OAI-SearchBot (ChatGPT search), Claude-SearchBot, PerplexityBot, Googlebot, Bingbot, Applebot | Their pages drop out of those answers. Usually an accident (a security plugin, a firewall default). Always a FAIL, with the exact fix |
| user | Opens a page when a person asks the assistant to: ChatGPT-User, Claude-User, Perplexity-User | Mixed: OpenAI says robots.txt may not apply; Perplexity says its fetcher generally ignores it; Anthropic says blocking stops Claude retrieving the page for a user. Reported as "check", never as a fail |
| training | Collects pages for model training: GPTBot, ClaudeBot, Google-Extended, Applebot-Extended, CCBot | An opt-out from training. It does not keep a business out of search answers. The founder's choice; the skill never tells them to change it |

How the file is read (RFC 9309): a crawler obeys the group that names it and ignores the `*` group; groups naming the same crawler are combined; the longest matching rule wins, and Allow wins a tie; `*` and `$` are wildcards; a file served as a web page (HTML) is not a robots.txt.

The fix the script writes: for each blocked search crawler, remove it from the group that blocks it and add its own group that allows the site, keeping any narrower rules (such as `/wp-admin/`). It re-checks the corrected file and refuses to write it if any other crawler's status would change. A robots.txt change can take about a day to be picked up (OpenAI's note for its own crawlers).

What robots.txt cannot show: a firewall or bot-protection rule that turns crawlers away before they read the file. If a plugin added AI blocking to robots.txt, the kit asks whoever manages the plugin to check its firewall settings too.

## Freshness

Names and purposes change. Rows for OpenAI, Anthropic, Perplexity and Google were checked against each operator's own page on 2 November 2026. Rows for Bing, Apple and Common Crawl are marked "not checked: verify before release" until someone opens their pages. The kit prints the date it used.

Script-only pages: Vercel and MERJ reported in December 2024 that the major AI crawlers they measured did not run scripts, with Gemini (through Googlebot) and Apple's crawler the exceptions. That is a dated finding. The kit treats an empty served page as a reason to fix the page, and says the finding's date.
