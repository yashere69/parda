# parda

*parda* (पर्दा): a curtain.

parda replaces Indian personal identifiers with tokens before text goes to an LLM, then puts
the real values back into the model's reply, even after the model has lowercased the
tokens, dropped the brackets or translated the labels into Hindi.

```python
from parda import Parda

p = Parda()                      # one per conversation; the mapping stays in memory
safe = p.redact("Mera number ९८७६५ ४३२१० hai, refund asha.k@okicici pe kar do")
safe.text   # 'Mera number [PHONE_1] hai, refund [UPI_1] pe kar do'

reply = call_your_llm(safe.text) # 'ठीक है, refund [upi_1] पर भेज दिया। फोन_1 पर कॉल करेंगे।'
p.restore(reply).text            # 'ठीक है, refund asha.k@okicici पर भेज दिया। 9876543210 पर कॉल करेंगे।'
```

![parda demo: a Hinglish message with a phone number in Devanagari digits, a PAN and a UPI id is redacted, a Hindi reply with rewritten tokens is restored](docs/demo.png)

## Why

Customers in India paste PAN numbers, UPI IDs and phone numbers into support chats as a
matter of course, often in Devanagari digits or spelled out ("nau aath double saat…").
If that chat goes to a hosted model, so does their data. The DPDP Rules were notified in
November 2025, with most obligations phased in over the following 18 months, so this now
has a deadline attached.

Redaction tools exist. [Presidio](https://github.com/microsoft/presidio) has India
recognisers (compared below), [LLM Guard](https://github.com/protectai/llm-guard) keeps a
vault for de-anonymising replies, and there are smaller reversible-masking wrappers on
PyPI. Presidio's and LLM Guard's docs describe putting values back but don't measure how
often that works once a model has rewritten the tokens. Once a model has seen `[UPI_1]`, does the value come
back in its reply? A plain `str.replace` restore only works if the model copied the token
exactly. Often it doesn't.

## Install

```bash
pip install git+https://github.com/yashere69/parda
parda demo
```

No dependencies outside the standard library. 800 KB of text with 50,000 identifiers
redacts in about a third of a second.

## What it finds

| Kind | How it's confirmed |
|---|---|
| Aadhaar | 12 digits, first digit 2–9, **Verhoeff** check digit |
| GSTIN | state code + PAN + entity + `Z` + **mod-36 check character** |
| PAN | shape, with the 4th letter restricted to valid holder types |
| Phone | Indian mobile (6–9 start), with or without `+91`/`0`, grouped 5-5 or plain |
| UPI | `handle@psp`, kept apart from email by the dotless PSP part |
| IFSC, email | shape |
| Card | 13–19 digits, **Luhn** |
| PIN code | 6 digits **only** when "pin", "pincode", "postal" or पिन appears just before it |

Numbers in Devanagari digits (`९८७६५`) and spoken numbers in English, romanised Hindi or
Devanagari words ("nau aath double saat…", "नौ आठ सात…") are handled too. When spans
overlap, the longest wins, so a GSTIN isn't also reported as the PAN inside it.

For chat-completions calls, `p.redact_messages(messages)` returns a redacted copy of the
whole message list through one vault, so the same number in turn 1 and turn 5 is the same
token and the model can still tell they're the same.

Already running Presidio or a name recogniser? Pass its spans in as `extra=` and parda
tokenises those too: `p.redact(text, extra=[Span(0, 11, "NAME", "Asha Sharma")])`.

## How well it works

Three measurements, all on generated data (no real identifiers). Each one says what it can
and can't tell you.

**Detection on the benchmark corpus.** `python tools/benchmark.py` regenerates
[results/benchmark.md](results/benchmark.md): 600 generated Hinglish/Hindi messages, a
quarter of them negatives (order ids, invoice numbers, prices, dates). The detectors were
tuned against this corpus, so it measures the rules, not the world:

| Kind | Precision | Recall |
|---|---|---|
| PAN, GSTIN, IFSC, UPI, phone | 100% | 100% |
| Aadhaar | 97.4% | 100% |
| PIN | 100% | 54.3% |

Phone was at 84.9% precision and 86.3% recall until this release. US-style `987 654 3210`
grouping was never detected, and ten-digit order ids starting with 6–9 were redacted as
phone numbers. A number whose nearest keyword is "order", "invoice", "AWB", "UTR" and the
like is now read as a reference, unless a call word ("call", "phone", "WhatsApp") is nearer.
Account numbers are deliberately not exempted: a wrong label is better than a leak. PIN
recall is low by design. Without a cue word, "Dehradun 248001" is left alone, because six
digits on their own are too often prices, quantities or codes.

**Detection on text it wasn't tuned on.** [examples/heldout.jsonl](examples/heldout.jsonl)
(`tools/make_heldout.py`) has 105 messages in phrasings the corpus doesn't use, 30 of them
negatives (UTR, AWB, OTP, SKU, invoice and booking numbers, prices). It includes forms parda
was expected to miss. It scores 100% precision on every kind and 100% recall on every kind
but phone, which is 82%. The misses are landlines (`0135-9521279`, since parda only knows
mobiles) and `98-76-54-32-10` pair grouping. The first run also showed `wa.me/91…` links
being read as Aadhaar numbers, because one in ten `91`+mobile strings passes the Verhoeff
check by chance. A `91` number in a phone context is now a phone.

**Against Presidio.** `tools/compare_presidio.py` runs both on the same messages
([results/presidio.md](results/presidio.md)). Presidio 2.2.366 is set up with its Indian
recognisers and spaCy `en_core_web_sm`. Cells are precision / recall:

| Kind | parda (corpus) | Presidio (corpus) | parda (held-out) | Presidio (held-out) |
|---|---|---|---|---|
| Aadhaar | 97% / 100% | 96% / 63% | 100% / 100% | 90% / 75% |
| PAN | 100% / 100% | 61% / 100% | 100% / 100% | 25% / 100% |
| GSTIN | 100% / 100% | 100% / 100% | 100% / 100% | 100% / 100% |
| Phone | 100% / 100% | 80% / 74% | 100% / 82% | 69% / 100% |

The table uses Presidio's default threshold. At a score threshold of 0.5 its PAN results
match parda's (100% / 100% on both sets), so the PAN gap above is a threshold setting, not
a detector gap. Phone is where the trade-off is real: Presidio uses libphonenumber, so it
finds the landlines and odd groupings parda misses, pays for that with false positives on
reference numbers, and at 0.5 its phone recall falls to 26–27%. At either threshold it
misses spaced and Devanagari-digit Aadhaar numbers.
The two combine: Presidio spans can be passed to parda through `extra=`.

**Round trip.** The share of replies with every value restored, after the tokens are
rewritten the way models tend to rewrite them:

| Rewrite in the reply | `str.replace` | parda |
|---|---|---|
| verbatim `[UPI_1]` | 100% | 100% |
| lowercase `[upi_1]` | 0% | 100% |
| brackets dropped `UPI_1` | 0% | 100% |
| `UPI 1` | 0% | 100% |
| label in Hindi `[यूपीआई_1]` | 0% | 100% |
| label and digit in Hindi `[यूपीआई_१]` | 0% | 100% |
| label renamed `[MOBILE_1]` | 0% | 0% |

These rewrites are simulated, so the table shows what the restorer tolerates. It can't say
how often a given model rewrites tokens, and this repository has no real-model run yet. The
harness for one is in place and needs no paid service. Any OpenAI-compatible endpoint works,
including a local model:

```bash
ollama pull qwen2.5:3b        # or any model; llama.cpp's server works the same way
python tools/benchmark.py --endpoint http://localhost:11434/v1 --model qwen2.5:3b \
    --record results/live-qwen2.5-3b.jsonl
python tools/benchmark.py --replay results/live-qwen2.5-3b.jsonl   # re-score, no model
```

The recording keeps each message and the model's reply, so a run can be re-scored after
parda changes and shared without re-running the model. The run reports how many replies
came back with every value, some values or none, plus any unknown tokens.

## Decisions worth knowing about

- **Opaque tokens, not fake look-alike values.** Swapping a real PAN for a fake but valid-looking
  one helps the model reason ("it's a PAN"). But PAN and phone numbers have no check digit,
  so a fake can collide with a real person's ID. The token already carries the type in its
  label.
- **Restore is tolerant only towards tokens it issued.** It accepts case, bracket, separator
  and Hindi-label variants of `KIND_n`, but only for kinds that appeared in this session.
  An index it never issued (`[UPI_2]` when only one UPI was seen) is reported in
  `RestoreResult.unknown` and left as-is, never filled with a guess.
- **Values come back canonical.** A phone number spoken as words returns as `9876543210`,
  and a lowercase PAN returns in capitals. That's what tools and databases downstream want.
  If you need the customer's original spelling back, the spans on `Redacted` have the offsets.
- **The mapping never leaves memory.** There's no persistence and no logging of values. The
  CLI's `--show-spans` prints kinds and offsets, never the values.
- **`leaks()` is a smoke check, not a guarantee.** It runs the same detectors over the
  outgoing text, so it can't catch what the detectors miss.

## Not covered

- Names and street addresses. These need NER; pass spans from Presidio or spaCy through
  `extra=`.
- Landline numbers, and phone numbers grouped in pairs
- Voter ID, passport, driving licence, vehicle numbers
- Images, PDFs, audio

Redaction is one control among several. Using parda doesn't make a system DPDP-compliant.

Stable: `Parda.redact`/`restore`/`redact_messages`, the token format and the CLI.
Experimental: the context-word lists, and `leaks()`.

## Development

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check . && mypy src && pytest
```

Example identifiers in the tests and the benchmark are generated so that their check digits
pass. Any match with a real person's ID is accidental, and the generated corpus is never
written to disk.

MIT licensed.
