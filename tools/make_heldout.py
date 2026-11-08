"""Write examples/heldout.jsonl: messages in phrasings the benchmark corpus doesn't use.

The benchmark corpus (parda.bench.corpus) was used while tuning the detectors. These
templates were written afterwards, in different words, to measure on text that wasn't
tuned against. Values are generated (valid check digits), never real.

    python tools/make_heldout.py
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from parda.bench import _aadhaar, _gstin, _ifsc, _pan, _phone, _upi  # noqa: E402

DEV = str.maketrans("0123456789", "०१२३४५६७८९")

# (kind or None, template). {v} is the surface form; None marks a message with no PII.
TEMPLATES = [
    ("PHONE", "bhaiya mera alternate no. {p55} hai"),
    ("PHONE", "delivery boy ko bolo {p_dash} pe ring kare"),
    ("PHONE", "contact: +91-{p}"),
    ("PHONE", "mobile number badal gaya, naya wala {p0}"),
    ("PHONE", "मेरा फोन नंबर {p_dev} है"),
    ("PHONE", "call me at {p334} tomorrow"),
    ("PHONE", "is number pe whatsapp karo {p} pls"),
    ("AADHAAR", "aadhar card no {a_sp}"),
    ("AADHAAR", "Aadhaar: {a}"),
    ("AADHAAR", "आधार नंबर {a_dev}"),
    ("AADHAAR", "kyc docs - aadhaar {a_dash}"),
    ("PAN", "pan card {pan_lower} hai mera"),
    ("PAN", "PAN no. {pan}, GST bill chahiye"),
    ("GSTIN", "GST number: {gst}"),
    ("GSTIN", "hamara gstin {gst} hai, invoice pe daal dena"),
    ("UPI", "paise {upi} pe transfer kar do"),
    ("UPI", "gpay id: {upi}"),
    ("IFSC", "bank IFSC code {ifsc}"),
    ("PIN", "pin code {pin}"),
    ("PIN", "address - 12 Rajpur Road, Dehradun, PIN {pin}"),
    (None, "UTR {n10} se payment kiya hai"),
    (None, "AWB no {n10} track nahi ho raha"),
    (None, "invoice #{n10} ka copy bhejo"),
    (None, "booking ref {n10}"),
    (None, "total ₹{n4} hua, discount ke baad ₹{n3}"),
    (None, "OTP {n6} aaya hai, kisi ko mat batana"),
    (None, "delivery 15/11/2026 tak ho jayegi"),
    (None, "item code SKU-{n6}-BLU"),
    (None, "2 kurte size 42 aur 44"),
    (None, "order no {n10} cancel karna hai"),
    # forms I expected parda to struggle with, kept in so the score isn't a foregone result
    ("PHONE", "landline pe call karo 0135-{landline}"),
    ("PHONE", "number aise likha tha: {p_pairs}"),
    ("PHONE", "chat here wa.me/91{p}"),
    ("PHONE", "(+91) {p55}"),
    (None, "aadhaar XXXX XXXX {n4} wala card"),
]


def main() -> None:
    r = random.Random(2026)
    rows = []
    for kind, t in TEMPLATES:
        for _ in range(3):
            p, a, pan, gst = _phone(r), _aadhaar(r), _pan(r), _gstin(r)
            values = {
                "p": p,
                "p55": f"{p[:5]} {p[5:]}",
                "p_dash": f"{p[:5]}-{p[5:]}",
                "p0": "0" + p,
                "p_dev": p.translate(DEV),
                "p334": f"{p[:3]} {p[3:6]} {p[6:]}",
                "a": a,
                "a_sp": f"{a[:4]} {a[4:8]} {a[8:]}",
                "a_dash": f"{a[:4]}-{a[4:8]}-{a[8:]}",
                "a_dev": f"{a[:4]} {a[4:8]} {a[8:]}".translate(DEV),
                "pan": pan,
                "pan_lower": pan.lower(),
                "gst": gst,
                "upi": _upi(r),
                "ifsc": _ifsc(r),
                "pin": f"{r.randint(110, 855)}{r.randint(0, 999):03d}",
                "n10": r.choice("6789") + "".join(str(r.randrange(10)) for _ in range(9)),
                "n6": "".join(str(r.randrange(10)) for _ in range(6)),
                "n4": str(r.randint(1000, 9999)),
                "n3": str(r.randint(100, 999)),
                "landline": "".join(str(r.randrange(10)) for _ in range(7)),
                "p_pairs": "-".join(p[i : i + 2] for i in range(0, 10, 2)),
            }
            text = t.format(**values)
            phone = "135" + values["landline"] if "{landline}" in t else p
            truth = {
                None: [],
                "PHONE": [["PHONE", phone]],
                "AADHAAR": [["AADHAAR", a]],
                "PAN": [["PAN", pan]],
                "GSTIN": [["GSTIN", gst]],
                "UPI": [["UPI", values["upi"].lower()]],
                "IFSC": [["IFSC", values["ifsc"]]],
                "PIN": [["PIN", values["pin"]]],
            }[kind]
            rows.append({"text": text, "truth": truth})
    out = ROOT / "examples/heldout.jsonl"
    out.write_text(
        "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows), encoding="utf-8"
    )
    print(f"wrote {len(rows)} messages to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
