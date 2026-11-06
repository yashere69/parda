# Changelog

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
