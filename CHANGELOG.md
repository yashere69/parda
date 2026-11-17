# Changelog

## 0.3.2

- A phone number in a sentence that follows one mentioning an order ("order nahi aaya.
  Mera number 98765 43210 hai") is redacted again. The reference-word check no longer
  looks past the end of the previous sentence, and "mera number" / "my no" / मेरा नंबर
  count as call words.

## 0.3.1

- Output is UTF-8 even when redirected on Windows, where it used to follow the code page
  and fail on Devanagari text.
- `parda redact` reads stdin as UTF-8 bytes, so text piped in on Windows isn't decoded
  with the code page and redacted as mojibake.
- CI runs the tests on Windows and macOS as well as Linux.

## 0.3.0

- Phone numbers grouped 3-3-4 (`987 654 3210`) are detected.
- A ten-digit number whose nearest keyword is a reference word (order, invoice, AWB, UTR,
  booking…) is no longer redacted as a phone; a nearer call word still wins. Phone
  precision on the benchmark goes from 84.9% to 100%.
- `wa.me/91…` and `+91…` numbers in a phone context are phones, not Aadhaar numbers that
  happened to pass the Verhoeff check.
- `examples/heldout.jsonl`: 105 messages written after tuning, with a regression test.
- `tools/compare_presidio.py`: parda and Presidio on the same messages.
- Live round trips: `--record` saves each reply, `--replay` re-scores a saved run without a
  model; replies are counted as fully, partly or not restored; request errors no longer
  abort the run.

## 0.2.0

- `ignore=` / `--ignore`: never redact values in your own formats (order ids)
- `redact_messages()` for chat-completions message lists, one vault across turns
- Overlap resolution with bisect instead of a scan (800 KB input: ~56 s to ~0.3 s)

## 0.1.0

- Detectors for Aadhaar (Verhoeff), GSTIN (mod-36), PAN, phone, UPI, IFSC, email, card
  (Luhn) and context-cued PIN codes
- Devanagari digits and spoken numbers (English, romanised Hindi, Devanagari words)
- Session vault with stable tokens and tolerant restore; unknown indices reported
- Benchmark script: detection precision/recall and simulated round-trip; optional live run
- `parda redact`, `parda demo`
