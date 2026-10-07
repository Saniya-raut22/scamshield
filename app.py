import os
import requests
import pandas as pd
import streamlit as st

import style

API = os.environ.get("API_BASE", "http://127.0.0.1:8000")

st.set_page_config(page_title="ScamShield", page_icon="🛡️", layout="wide")
style.apply(
    "🛡️ ScamShield",
    "Real-time scam detection for messages, screenshots, links, QR codes and calls",
    chips=["📝 Text", "📷 Screenshots", "🔗 Links", "📱 QR codes", "🎙️ Voice calls", "🇮🇳 Hinglish"],
)

ADVICE = {
    "High": "This looks like a scam. Don't click links, call back numbers, or share OTPs and card details.",
    "Medium": "This might be a scam. Check who really sent it before you act.",
    "Low": "No strong scam signals. Still be careful with links and OTPs.",
}

EXAMPLES = [
    ("🎰 Prize scam", "URGENT! You won a free prize, click this link now"),
    ("🏦 KYC scam", "Your KYC is expired. Update immediately or account will be blocked"),
    ("🇮🇳 Hinglish scam", "Aapka SIM card band hone wala hai, turant is link par KYC verify karo"),
    ("💬 Normal chat", "Are you coming to class tomorrow?"),
    ("🇮🇳 Hinglish normal", "Kal shaam ko library mein milte hain, notes le aana"),
]

if "msg" not in st.session_state:
    st.session_state["msg"] = ""


def set_msg(text):
    st.session_state["msg"] = text


def predict(text):
    r = requests.post(f"{API}/predict", json={"text": text[:5000]}, timeout=10)
    r.raise_for_status()
    return r.json()


def predict_batch(texts):
    out = []
    for i in range(0, len(texts), 100):
        chunk = [t[:5000] if t.strip() else "." for t in texts[i:i + 100]]
        r = requests.post(f"{API}/predict_batch", json={"texts": chunk}, timeout=30)
        r.raise_for_status()
        out.extend(r.json())
    return out


def explain(text, base, top=8):
    tokens = text.split()
    words = list(dict.fromkeys(tokens))[:40]
    if len(words) < 2:
        return []
    variants = [" ".join(t for t in tokens if t != w) or "." for w in words]
    probs = predict_batch(variants)
    impact = [(w, base - p["spam_probability"]) for w, p in zip(words, probs)]
    impact.sort(key=lambda x: -abs(x[1]))
    return impact[:top]


# ---------------- Sidebar ----------------
st.sidebar.title("🛡️ ScamShield")
try:
    requests.get(f"{API}/", timeout=3).raise_for_status()
    st.sidebar.success("API connected")
    api_ok = True
except Exception:
    st.sidebar.error("API offline. Run: uvicorn api:app --reload")
    api_ok = False
st.sidebar.caption("Detects scams in English and Hinglish across text, images, links, QR codes and voice calls.")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["🔍 Detector", "📂 Bulk Scan", "📈 Dashboard", "📊 Model Performance", "📷 Screenshot"]
)

# ---------------- Tab 1: Detector ----------------
with tab1:
    st.write("**Try an example (one click):**")
    cols = st.columns(len(EXAMPLES))
    for i, (label, text) in enumerate(EXAMPLES):
        cols[i].button(label, key=f"ex{i}", on_click=set_msg, args=(text,),
                       use_container_width=True)

    msg = st.text_area("Message", height=140, key="msg",
                       placeholder="Paste an SMS, WhatsApp or email text here (English or Hinglish)")

    if st.button("Check message", type="primary", disabled=not api_ok):
        if not msg.strip():
            st.warning("Please enter a message first.")
        else:
            res = predict(msg)
            prob = res["spam_probability"]
            level = style.level_from_prob(prob)
            col1, col2 = st.columns([1, 1.4])
            with col1:
                style.risk_card(level, round(prob * 100), ADVICE[level])
                style.gauge(round(prob * 100))
            with col2:
                st.subheader("Why this verdict?")
                impact = explain(msg, prob)
                if impact:
                    exp = pd.DataFrame(impact, columns=["Word", "Impact"])
                    exp["Effect"] = exp["Impact"].apply(
                        lambda v: "Pushes toward SPAM" if v > 0.02
                        else ("Pushes toward SAFE" if v < -0.02 else "Neutral")
                    )
                    st.dataframe(exp.round(3), hide_index=True, use_container_width=True)
                    st.bar_chart(exp.set_index("Word")["Impact"], color="#4F8BF9")
                else:
                    st.info("Message too short to explain.")

# ---------------- Tab 2: Bulk Scan ----------------
with tab2:
    st.write("Upload a CSV of messages and scan them all at once.")
    f = st.file_uploader("CSV file", type="csv")
    if f:
        df = pd.read_csv(f)
        col = st.selectbox("Column that contains the messages", df.columns)
        st.dataframe(df.head(), use_container_width=True)
        if st.button("Scan all (max 500 rows)", disabled=not api_ok):
            texts = df[col].astype(str).tolist()[:500]
            res = predict_batch(texts)
            out = pd.DataFrame({
                "text": texts,
                "label": [r["label"] for r in res],
                "spam_probability": [r["spam_probability"] for r in res],
            })
            st.success(f"Scanned {len(out)} messages. Spam found: {(out['label'] == 'spam').sum()}")
            st.dataframe(out, use_container_width=True)
            st.download_button("Download results", out.to_csv(index=False),
                               "scan_results.csv", "text/csv")

# ---------------- Tab 3: Dashboard (saved in the database) ----------------
with tab3:
    s = None
    if api_ok:
        try:
            s = requests.get(f"{API}/stats", params={"limit": 1000}, timeout=10).json()
        except Exception:
            s = None
    if not s or s["total"] == 0:
        st.info("No scans saved yet. Check a message, link, screenshot or call and it will appear here.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total scans", s["total"])
        c2.metric("Scams detected", s["by_label"].get("scam", 0))
        c3.metric("Suspicious", s["by_label"].get("suspicious", 0))
        c4.metric("Safe", s["by_label"].get("safe", 0))

        left, right = st.columns(2)
        with left:
            st.subheader("Scans by type")
            st.bar_chart(pd.Series(s["by_kind"]), color="#4F8BF9")
        with right:
            st.subheader("Scans per day")
            if s["per_day"]:
                d = pd.DataFrame(s["per_day"]).set_index("day")
                d = d.rename(columns={"n": "All scans", "scams": "Scams"})
                st.bar_chart(d, color=["#4F8BF9", "#ef4444"])

        st.subheader("Top words in detected scams")
        if s["top_words"]:
            kw = pd.DataFrame(s["top_words"], columns=["Word", "Count"]).set_index("Word")
            st.bar_chart(kw, color="#f59e0b")
        else:
            st.caption("Not enough detected scams yet.")

        st.subheader("Recent scans")
        h = pd.DataFrame(s["recent"])[["created_at", "kind", "content", "label", "score"]]
        h["created_at"] = (
            pd.to_datetime(h["created_at"]).dt.tz_localize("UTC")
            .dt.tz_convert("Asia/Kolkata").dt.strftime("%d %b %H:%M")
        )
        h.columns = ["Time", "Type", "Content", "Verdict", "Score"]
        st.dataframe(h, hide_index=True, use_container_width=True)
        st.download_button("Download history (CSV)", h.to_csv(index=False),
                           "scan_history.csv", "text/csv")

        with st.expander("Delete all saved history"):
            if st.checkbox("I understand this cannot be undone"):
                if st.button("Delete history"):
                    requests.delete(f"{API}/history", timeout=10)
                    st.rerun()

# ---------------- Tab 4: Model Performance ----------------
with tab4:
    if os.path.exists("results_hinglish.csv"):
        st.subheader("Hinglish support: before vs after")
        hres = pd.read_csv("results_hinglish.csv")
        st.dataframe(hres, hide_index=True, use_container_width=True)
        st.write("Hinglish scam recall (higher is better)")
        st.bar_chart(hres.pivot(index="Model", columns="Training data", values="Hinglish Recall"))
        st.caption("The Hinglish test set is small and hand-written, so treat this as a demo-level result.")
    if os.path.exists("results.csv"):
        st.subheader("Model comparison (English test set)")
        res = pd.read_csv("results.csv")
        st.dataframe(res, hide_index=True, use_container_width=True)
        st.bar_chart(res.set_index("Model")[["Precision", "Recall", "F1"]],
                     color=["#4F8BF9", "#22c55e", "#f59e0b"])
        st.write(f"Best model by F1: **{res.loc[res['F1'].idxmax(), 'Model']}**")
    if not os.path.exists("results.csv") and not os.path.exists("results_hinglish.csv"):
        st.info("Run `python train.py` to generate the results.")

# ---------------- Tab 5: Screenshot ----------------
with tab5:
    st.write("Upload a screenshot of a WhatsApp, SMS or email scam. ScamShield reads the text and checks it.")
    img_file = st.file_uploader("Screenshot", type=["png", "jpg", "jpeg", "webp"], key="shot")
    if img_file:
        left, right = st.columns([1, 1.4])
        with left:
            st.image(img_file, use_container_width=True)
        with right:
            if st.button("Scan screenshot", type="primary", disabled=not api_ok):
                with st.spinner("Reading text from image (the first scan is slower)..."):
                    r = requests.post(
                        f"{API}/predict_image",
                        files={"file": (img_file.name, img_file.getvalue(), img_file.type)},
                        timeout=120,
                    )
                if not r.ok:
                    st.error("Could not read that image. Try a clearer screenshot.")
                else:
                    res = r.json()
                    if res["label"] == "unknown":
                        st.warning("No text found in the image.")
                    else:
                        prob = res["spam_probability"]
                        level = style.level_from_prob(prob)
                        style.risk_card(level, round(prob * 100), ADVICE[level])
                        style.gauge(round(prob * 100))
                        with st.expander("Text extracted from the image"):
                            st.write(res["text"])

st.caption("Built with FastAPI · Streamlit · scikit-learn · Whisper · OCR")