import re
from urllib.parse import urlparse, parse_qs

SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "cutt.ly",
              "rb.gy", "shorturl.at", "tiny.cc", "ow.ly", "rebrand.ly"}

RISKY_TLDS = {"xyz", "top", "tk", "ml", "ga", "cf", "gq", "click", "link",
              "icu", "buzz", "rest", "work", "support", "country", "zip", "mov"}

KEYWORDS = ["login", "verify", "verification", "update", "secure", "account",
            "bank", "kyc", "free", "prize", "winner", "claim", "reward", "bonus",
            "refund", "suspend", "blocked", "confirm", "password", "otp",
            "wallet", "gift", "lottery", "offer"]

OFFICIAL = {
    "sbi": ["sbi.co.in", "onlinesbi.sbi", "onlinesbi.com"],
    "hdfc": ["hdfcbank.com"],
    "icici": ["icicibank.com"],
    "axis": ["axisbank.com"],
    "paytm": ["paytm.com"],
    "phonepe": ["phonepe.com"],
    "amazon": ["amazon.in", "amazon.com"],
    "flipkart": ["flipkart.com"],
    "paypal": ["paypal.com"],
    "netflix": ["netflix.com"],
    "irctc": ["irctc.co.in"],
    "uidai": ["uidai.gov.in"],
    "google": ["google.com"],
    "microsoft": ["microsoft.com"],
    "apple": ["apple.com"],
    "whatsapp": ["whatsapp.com"],
    "facebook": ["facebook.com"],
    "instagram": ["instagram.com"],
}

IP_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://")
DOMAIN_RE = re.compile(r"^[\w.\-]+\.[a-zA-Z]{2,}(/.*)?$")

ADVICE = {
    "High": "Do not open this link or enter any password, OTP, or card details. "
            "If it claims to be from your bank or a service, open their official app "
            "or type the website address yourself.",
    "Medium": "Be careful. Don't enter personal details until you have confirmed the sender. "
              "Type the official website address yourself instead of using this link.",
    "Low": "No obvious red flags in the address itself, but always check the website "
           "name before logging in or paying.",
}


def _level(score):
    if score >= 50:
        return "High"
    if score >= 20:
        return "Medium"
    return "Low"


def _result(url, score, reasons):
    score = max(0, min(100, score))
    level = _level(score)
    return {"url": url, "risk_score": score, "level": level,
            "reasons": reasons, "advice": ADVICE[level]}


def analyze_url(url: str) -> dict:
    raw = url.strip()
    had_scheme = bool(SCHEME_RE.match(raw))
    full = raw if had_scheme else "https://" + raw

    try:
        parsed = urlparse(full)
        host = (parsed.hostname or "").lower()
    except ValueError:
        host = ""

    if not host:
        return _result(raw, 50, ["Could not read a valid website address from this text."])

    # Known official domains are treated as safe
    for brand, domains in OFFICIAL.items():
        if any(host == d or host.endswith("." + d) for d in domains):
            return _result(raw, 0, [f"Belongs to the known official domain of {brand.title()}."])

    score, reasons = 0, []
    labels = host.split(".")
    tokens = [t for t in re.split(r"[.\-_]", host) if t]

    for brand in OFFICIAL:
        if brand in tokens:
            score += 35
            reasons.append(f"Mentions '{brand}' but is not the official {brand.title()} website.")
            break

    is_ip = bool(IP_RE.match(host))
    if is_ip:
        score += 30
        reasons.append("Uses a raw IP address instead of a website name.")
    if "@" in raw:
        score += 20
        reasons.append("Contains '@', a trick used to hide the real destination.")
    if "xn--" in host:
        score += 20
        reasons.append("Uses lookalike (punycode) characters in the domain.")
    if host.replace("www.", "", 1) in SHORTENERS:
        score += 20
        reasons.append("Link shortener hides the real destination.")
    if labels[-1] in RISKY_TLDS:
        score += 15
        reasons.append(f"Ends in '.{labels[-1]}', which is often used in scam sites.")
    if had_scheme and parsed.scheme == "http":
        score += 10
        reasons.append("Not using HTTPS (not encrypted).")
    if len(labels) > 4:
        score += 10
        reasons.append("Has an unusually long chain of subdomains.")
    if host.count("-") >= 2:
        score += 10
        reasons.append("Domain has many hyphens.")
    if len(raw) > 75:
        score += 10
        reasons.append("Very long link.")
    if not is_ip and sum(ch.isdigit() for ch in host) / len(host) > 0.3:
        score += 10
        reasons.append("Domain contains a lot of digits.")

    text = (host + parsed.path + parsed.query).lower()
    found = [k for k in KEYWORDS if k in text]
    if found:
        score += min(len(found), 3) * 7
        reasons.append("Suspicious words in the link: " + ", ".join(found[:5]))

    if not reasons:
        reasons.append("No suspicious patterns found in the address.")
    return _result(raw, score, reasons)


def analyze_content(content: str) -> dict:
    c = content.strip()
    low = c.lower()

    if low.startswith("upi://"):
        q = parse_qs(urlparse(c).query)
        get = lambda k: q.get(k, [""])[0]
        return {
            "content": c, "type": "upi", "risk_score": 40, "level": "Medium",
            "reasons": [
                "This is a UPI payment QR. Scanning it sends money OUT of your account.",
                "Anyone who asks you to scan a QR code to RECEIVE money is a scammer. "
                "Receiving money never needs a scan or a PIN.",
            ],
            "advice": "Only scan UPI QR codes when YOU intend to pay that exact person or shop, "
                      "and check the name shown in your payment app before entering your PIN.",
            "details": {"payee_id": get("pa"), "payee_name": get("pn"), "amount": get("am")},
        }

    if low.startswith(("http://", "https://")) or (not SCHEME_RE.match(c) and DOMAIN_RE.match(c)):
        res = analyze_url(c)
        res.update(content=c, type="url")
        return res

    return {
        "content": c, "type": "text", "risk_score": 0, "level": "Low",
        "reasons": ["This QR code contains plain text, not a link."],
        "advice": ADVICE["Low"],
    }