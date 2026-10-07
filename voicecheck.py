import re

ADVICE = {
    "High": "Hang up now. Never share an OTP, PIN, password or card details on a call, and never "
            "install apps like AnyDesk because a caller asked. Real banks and police do not "
            "demand money or secrecy on a phone call. Call your bank on the number printed on "
            "your card, and report scams at cybercrime.gov.in or call 1930.",
    "Medium": "Be careful. Don't share any OTP, PIN or personal details. End the call and call "
              "back on the official number of the bank or office, not the number that called you.",
    "Low": "No strong scam patterns found, but never share an OTP or PIN with anyone who calls you.",
}

# (category, weight, phrases)
RED_FLAGS = [
    ("Asks for OTP, PIN, CVV or password", 40,
     ["otp", "one time password", "pin number", "cvv", "card number", "password"]),
    ("Asks to install a remote-access app or share the screen", 40,
     ["anydesk", "teamviewer", "quicksupport", "screen share", "install the app",
      "download the app", "share the code"]),
    ("Demands secrecy or asks you to stay on the call", 25,
     ["do not tell", "don't tell", "keep this confidential", "stay on the call",
      "do not disconnect", "don't disconnect", "do not cut the call"]),
    ("Pretends to be an authority", 20,
     ["cyber crime", "cybercrime", "cbi", "rbi", "customs", "trai", "income tax",
      "narcotics", "police", "bank manager", "customer care", "kyc", "aadhaar"]),
    ("Creates fear or urgency", 20,
     ["arrested", "arrest", "arrest warrant", "case has been registered", "legal action",
      "immediately", "right now", "urgent", "last warning", "within 24 hours",
      "within two hours", "account will be blocked", "account will be suspended"]),
    ("Asks for money or fees", 20,
     ["send money", "transfer money", "processing fee", "registration fee",
      "gift card", "pay a fee", "security deposit"]),
    ("Prize, lottery or reward", 20,
     ["lottery", "you have won", "lucky winner", "cashback", "prize"]),
]


def _find(text_low, phrases):
    return [p for p in phrases if re.search(r"\b" + re.escape(p) + r"\b", text_low)]


def _chunks(text, size=30, step=20):
    words = text.split()
    if not words:
        return []
    if len(words) <= size:
        return [" ".join(words)]
    out = []
    for i in range(0, len(words), step):
        out.append(" ".join(words[i:i + size]))
        if i + size >= len(words):
            break
    return out


def analyze_transcript(text, model):
    low = text.lower()

    flags, cue_score = [], 0
    for category, weight, phrases in RED_FLAGS:
        hit = _find(low, phrases)
        if hit:
            cue_score += weight
            flags.append({"category": category, "matched": hit[:4]})

    chunks = _chunks(text)
    probs = model.predict_proba(chunks)[:, 1] if chunks else []
    model_score = round(float(max(probs)) * 100) if chunks else 0

    ranked = sorted(zip(chunks, probs), key=lambda x: -x[1])[:3]
    top_chunks = [{"text": c, "spam_probability": round(float(p), 3)}
                  for c, p in ranked if p >= 0.3]

    score = min(100, max(model_score, cue_score))
    level = "High" if score >= 60 else ("Medium" if score >= 35 else "Low")
    return {"risk_score": score, "level": level, "flags": flags,
            "top_chunks": top_chunks, "advice": ADVICE[level]}