import streamlit as st

import style

st.set_page_config(page_title="How It Works", page_icon="🧠", layout="wide")
style.apply("🧠 How ScamShield Works", "One backend, many ways to check a scam",
            chips=["FastAPI", "scikit-learn", "Whisper", "OCR", "SQLite", "Streamlit"])

st.subheader("Architecture")
st.graphviz_chart("""
digraph G {
  rankdir=LR; bgcolor="transparent";
  node [shape=box, style="rounded,filled", fillcolor="#1A1F2B", color="#4F8BF9",
        fontcolor="white", fontname="Helvetica"];
  edge [color="#8892a6"];
  "Streamlit website" -> "FastAPI backend";
  "Telegram bot (planned)" -> "FastAPI backend";
  "FastAPI backend" -> "Text model (TF-IDF + SVM)";
  "FastAPI backend" -> "OCR (screenshots)";
  "FastAPI backend" -> "URL risk checker";
  "FastAPI backend" -> "QR decoder";
  "FastAPI backend" -> "Whisper (voice)";
  "OCR (screenshots)" -> "Text model (TF-IDF + SVM)";
  "QR decoder" -> "URL risk checker";
  "Whisper (voice)" -> "Red-flag phrase rules";
  "FastAPI backend" -> "SQLite database";
}
""")

c1, c2, c3 = st.columns(3)
with c1:
    st.subheader("📝 Text and screenshots")
    st.write("A TF-IDF + SVM model trained on 5,500+ real SMS messages plus Hinglish examples. "
             "Screenshots are read with OCR first, then use the same model.")
with c2:
    st.subheader("🔗 Links and QR codes")
    st.write("Feature-based risk scoring: lookalike brand names, risky endings, link shorteners, "
             "raw IPs and suspicious words. UPI QR codes get a special payment warning.")
with c3:
    st.subheader("🎙️ Voice calls")
    st.write("Whisper transcribes the call, Hindi is translated to English, and the text is checked "
             "by the model plus red-flag phrases such as OTP requests and fake arrest threats.")

st.subheader("Honest limitations")
st.write("""
- The Hinglish training data is small and hand-written, so Hinglish results are a proof of concept.
- The link checker uses rules, not live blacklists or domain age.
- Call analysis depends on transcript quality, and Hindi translation is weaker on small Whisper models.
- Nothing replaces official channels: banks never ask for an OTP on a call. Report scams at cybercrime.gov.in or call 1930.
""")