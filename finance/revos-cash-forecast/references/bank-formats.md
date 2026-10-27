# Bank exports: what the parser expects, and how sure we are

`scripts/parse_bank_csv.py` reads any export by its column names, or by its content when there is no header row. That generic mapper is the backbone; the layouts below only add what a header cannot say (a documented date order, a sign that runs the other way, which columns make the description, the currency a bank's accounts are usually held in). Where an export carries a running balance, the parser checks every row against it (balance before plus amount equals balance after). That check, not this table, is what proves the columns were read the right way round. When a layout is unverified and the export has no running balance, the parser asks the founder one question (exit 3) and the answer is saved as a `--map` line in memory, so it is never asked twice.

Researched 20 October 2026. Banks change their exports without notice; treat this table as a starting point, not a promise. "Not verified" means no published source confirming the columns was found; the fixtures for those layouts were written from the best available description, not from a real export.

Contents
1. The layouts
2. Quirks the parser handles
3. Dates: day first or month first
4. Currency
5. The one question, and the map line
6. Where founders find the export

## 1. The layouts

| Bank | What the parser recognises | Dates | Money in and out | Status and source |
|---|---|---|---|---|
| Chase (US) | `Details,Posting Date,Description,Amount,Type,Balance,Check or Slip #`; rows end in a comma | Month first | Signed Amount; running Balance | Posting Date and month-first dates confirmed by beancount.io's Chase converter; the other column names are community-reported |
| Bank of America (US) | Summary lines (beginning balance, totals), then `Date,Description,Amount,Running Bal.` and a beginning-balance row | Read from the data | Signed Amount; Running Bal. | Summary block and Running Bal. confirmed by beancount.io's Bank of America converter; the date format is not stated there. Descriptions carry ACH codes (`GUSTO DES:NET B0BC77 ID:... INDN:... CCD`), wire fields (`WIRE TYPE:WIRE IN ... ORIG:<sender> ID:...`) and card prefixes (`CHECKCARD mmdd`): the finder reads the payee from the text before `DES:` plus the `DES:` word, from `ORIG:` for wires, and drops every token holding a digit, so each pay run is the same payee |
| Wells Fargo (US) | No header: date, amount, `*`, an empty column, description | Read from the data | Signed amount; no balance | Five columns by position confirmed by beancount.io's Wells Fargo converter; the sign convention is **not verified**. Read by inference, then one question |
| American Express (US and elsewhere) | `Date,Description,...,Amount` with Card Member or Extended Details | Read from the data | Charges shown as a plus, payments as a minus: every sign is turned round | Charges positive confirmed by beancount.io's Amex converter; column names **not verified**. A card is not a bank account: the parser asks whether to use the bank export instead |
| Mercury (US) | `Date (UTC),Description,Amount,Status,Source Account,Bank Description,...` | Read from the data | Signed Amount; Status (Sent, Pending, Failed, Cancelled); no balance | **Not verified.** Mercury's help centre describes the export screen but not its columns |
| DBS (Singapore) | Preamble with Available and Ledger Balance, then `Transaction Date,Reference,Debit Amount,Credit Amount,Transaction Ref1,Transaction Ref2,Transaction Ref3` | Named months | Debit and Credit columns; no running balance; the ledger balance at the top is used as the opening balance | **Not verified.** No published description of DBS's CSV columns was found |
| OCBC (Singapore) | Preamble, then `Transaction date,Value date,Description,Withdrawals (SGD),Deposits (SGD)`; descriptions often run onto a second row | Read from the data | Withdrawals and Deposits columns; ledger balance at the top | **Not verified.** No published description of OCBC's CSV columns was found |
| Commonwealth Bank (Australia) | No header: date, signed amount (with a plus for money in), description, balance | Read from the data | Signed amount; running balance | **Not verified**; sources disagree on the columns. Read by inference; the balance check proves it when the balance column is present |
| ANZ (Australia) | No header: date, signed amount, description | Read from the data | Signed amount; no balance | **Not verified.** Read by inference, then one question |
| Wise (any country) | `TransferWise ID,Date,Amount,Currency,Description,Payment Reference,Running Balance,...,Total fees` | Day first | Signed Amount, net of fees; a Currency column; a running balance per currency | Day-first dates, the Currency column and amounts net of fees confirmed by beancount.io's Wise converter; exact column names **not verified**. Wise's newer export with a Direction column is not covered: ask for the statement CSV |
| Barclays (UK) | `Number,Date,Account,Amount,Subcategory,Memo` | Read from the data | Signed Amount; no balance; Memo padded with tabs | Header confirmed by two independent write-ups (natalian.org and beancount.io) |
| HSBC (UK and elsewhere) | `Date,Type,Description,Amount,Balance` | Named months | Signed Amount; running Balance | Community-reported (QuickFile forum). A headerless download is read by inference, then one question |
| Lloyds (UK) | `Transaction Date,Transaction Type,Sort Code,Account Number,Transaction Description,Debit Amount,Credit Amount,Balance,` | Read from the data | Separate Debit and Credit columns | Header from an open-source Lloyds parser (github.com/ggirtsou/lloyds) |
| Lloyds Commercial Banking Online (UK) | `Account,Date,Type,Narrative,Value Date,Payments,Receipts,Balance` | `09MAY26` | Payments and Receipts columns | Lloyds' own CSV layout guide |
| NatWest (UK) | `Date, Type, Description, Value, Balance, Account Name, Account Number` | Read from the data | Signed Value; running Balance | **Not verified**: the widely reported online banking layout. The balance check proves it when present |
| Monzo Business (UK) | `Transaction ID,Date,Time,Type,Name,Emoji,Category,Amount,Currency,...,Balance,Balance currency` | Day first | Signed Amount in the account currency | Columns from the Monzo community; day-first dates from beancount.io's converter |
| Starling (UK) | `Date,Counter Party,Reference,Type,Amount (GBP),Balance (GBP),Spending Category,Notes` | Day first | Signed Amount; running Balance | Day-first dates and the Amount column confirmed by beancount.io's converter; exact names **not verified** |
| Tide (UK) | `Date,Transaction ID,Transaction description,Reference,Paid in,Paid out,Transaction type` | Read from the data | Paid in and Paid out columns | **Not verified.** No public description of Tide's CSV columns was found |
| Revolut Business (any country) | `Date started (UTC),Date completed (UTC),ID,Type,State,Description,...,Amount,Fee,Balance,...` | Year first | Signed Amount; separate Fee column; State column | Column list from an integration partner (Dativery); pending rows ignored by an open-source parser. Whether Fee is inside Amount is decided by the balance check |

Any other export is read by its column names: a date column, then either one amount column or separate money in and money out columns, then a balance, description, type, status, fee and currency column where they exist.

## 2. Quirks the parser handles

| Quirk | What it does |
|---|---|
| Money in and money out in separate columns, positive or already negative | Combines them into one signed amount, column by column |
| Unsigned amounts with a CR or DR column | Signs each row from the marker |
| Signs that run against the balance | Turns every sign round when only that makes the balance add up, and says so |
| A layout documented to show money out as a plus (Amex) | Turns every sign round and says so |
| Pending rows (a State or Status column, the words pending or authorised, or a row with no balance where every other row has one) | Held out of the history and the opening balance, and listed |
| Declined, reversed, reverted, failed, cancelled rows | Dropped and counted |
| Repeated header rows (several exports pasted into one file) | Skipped; each pasted block is treated as its own export |
| Overlapping exports (the same week in two files) | Rows already seen in an earlier block are dropped and counted |
| Two identical rows with no balance column | Kept (two coffees are two coffees) and counted in a note |
| Preamble lines (account name, summary totals) and total or balance-brought-forward lines | Skipped; a ledger or closing balance printed there is kept as the opening balance when the rows carry none |
| A description that runs onto a second row with no date or amount | Joined to the row above |
| Newest first or oldest first, and either order within a day | Sorted; the order within a day is chosen by the balance check |
| Dates day first, month first, year first, named months, `09MAY26`, spreadsheet serial numbers | Read; see section 3 |
| Mixed date formats in one file | STOP: it was edited in a spreadsheet; export again |
| Commas, semicolons, tabs; comma decimals (1.234,56); currency signs and codes; brackets for negatives; a leading plus | Read |
| Several currencies in one file | Keeps the main currency, drops the rest before the balance check, and says how many rows were left out |
| A PDF, Excel file, OFX or QIF, or an empty file | STOP with the one thing to do |
| Two different layouts in one run | STOP: one account at a time |

## 3. Dates: day first or month first

The order comes from the data, never from a country. In turn: any day over 12 settles it (31/10 is day first, 10/31 is month first); if every day is 12 or under, the reading that keeps the rows in date order wins; if both readings keep the order, a layout's documented order is used and named; if there is none, the parser asks once (exit 3) and the founder's answer goes back in with `--dates day-first` or `--dates month-first` and is saved. The MAP line printed while the question is open carries no date order, so a saved map never settles it by accident.

## 4. Currency

In turn: a currency column (the main currency is kept); a code in a column name ("Amount (GBP)", "Withdrawals (SGD)"); codes or unambiguous signs in the amounts; a balance line above the header ("SGD 56,102.39"); then, for a layout whose accounts are usually in one currency, a labelled guess ("a guess from the layout: Chase accounts are usually in USD; confirm it with the founder"). A bare "$" is never read as one country's dollar. With none of these, the founder is asked (intake question 5).

## 5. The one question, and the map line

The parser prints `ASK:` lines (exit 3) when the layout or the date order cannot be proved: no header row, an unverified layout with no running balance, two columns that could both be the amount, unsigned amounts with nothing to tell money in from money out, a card export, or dates that read either way. Claude puts that question in the same message as the intake questions, with the first three rows as the parser read them, so the founder answers once ("yes", "the third column is money out", "month first").

The parser also prints a `MAP:` line, for example `date=Date; in=Paid in; out=Paid out; desc=Transaction description; dates=day-first; sign=as-is`. Columns can be named or numbered from 0 (`date=0; desc=4; amount=1` for a file with no header). After the founder confirms, run again with `--map "<that line>"` and save it to memory. If a saved map no longer fits (the bank changed its layout), the parser stops and says so; run again without `--map`.

## 6. Where founders find the export

Say this only when the founder asks how. Most banks put a CSV download beside the statement download, sometimes labelled "Export", "Download transactions", "Excel" or "spreadsheet". Choose CSV, the business account, and the last three months. If the bank offers a choice that includes a running balance, choose it: it lets every row be checked. If unsure, the founder can search their bank's help pages for "export transactions CSV".
