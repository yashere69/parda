# Reporting a security problem

Please use GitHub's private vulnerability reporting (the **Security** tab → "Report a
vulnerability") rather than a public issue, and include a minimal input that shows it.

What counts here:

- an original value reaching text that was supposed to be redacted, when the value is a kind
  parda claims to detect (Aadhaar, PAN, GSTIN, UPI, Indian mobile, PIN with a cue word) in a
  form the README says it handles
- `restore()` putting a value somewhere other than where its token was, or into a different
  session's text
- a vault value written to disk, a log or an exception message

What doesn't: missed names, addresses or other kinds parda doesn't claim, and the misses the
README already lists. Those are ordinary issues, and a failing example is very welcome.

parda is one control in front of an LLM call, not a compliance guarantee. There is no
bounty. I'll reply within a week.
