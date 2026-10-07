import os
import requests
import streamlit as st

import style

API = os.environ.get("API_BASE", "http://127.0.0.1:8000")

st.set_page_config(page_title="Voice Scam Scan", page_icon="🎙️", layout="wide")
style.apply("🎙️ Voice Scam Detection",
            "Upload or record a call. ScamShield transcribes it and checks it for scam patterns",
            chips=["🎧 Whisper transcription", "🚩 Red-flag phrases", "🌐 Hindi to English"])

mode = st.radio("Input", ["Upload recording", "Record now"], horizontal=True)
audio, name, mime = None, "audio.wav", "audio/wav"

if mode == "Upload recording":
    audio = st.file_uploader("Call recording", type=["wav", "mp3", "m4a", "ogg", "flac", "webm"], key="aud")
    if audio:
        name, mime = audio.name, audio.type or "audio/wav"
        st.audio(audio)
else:
    if hasattr(st, "audio_input"):
        audio = st.audio_input("Record")
    else:
        st.warning("Recording needs a newer Streamlit. Run: pip install --upgrade streamlit")

if audio and st.button("Analyze call", type="primary"):
    with st.spinner("Transcribing... the first time it downloads the Whisper model, so wait a minute."):
        try:
            r = requests.post(f"{API}/analyze_audio",
                              files={"file": (name, audio.getvalue(), mime)}, timeout=600)
        except Exception:
            r = None
            st.error("Can't reach the API. Is `uvicorn api:app --reload` running?")

    if r is not None:
        if not r.ok:
            st.error(r.json().get("detail", "Something went wrong."))
        else:
            res = r.json()
            if not res["found"]:
                st.warning(res["message"])
            else:
                style.risk_card(res["level"], res["risk_score"], res["advice"])
                style.gauge(res["risk_score"])

                left, right = st.columns(2)
                with left:
                    st.subheader("🚩 Red flags found")
                    if res["flags"]:
                        for fl in res["flags"]:
                            st.write(f"• **{fl['category']}**: " + ", ".join(f"`{m}`" for m in fl["matched"]))
                    else:
                        st.write("No scam phrases found.")
                    if res["top_chunks"]:
                        st.subheader("Most suspicious parts")
                        for c in res["top_chunks"]:
                            st.write(f"• ({c['spam_probability']:.0%}) {c['text']}")
                with right:
                    st.subheader("📝 Transcript")
                    st.write(f"Detected language: `{res['language']}`")
                    st.write(res["transcript"])
                    if res["english"] != res["transcript"]:
                        with st.expander("English translation (used for the check)"):
                            st.write(res["english"])