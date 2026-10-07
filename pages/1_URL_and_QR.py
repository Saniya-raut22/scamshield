import os
import requests
import streamlit as st

import style

API = os.environ.get("API_BASE", "http://127.0.0.1:8000")

st.set_page_config(page_title="URL & QR Scanner", page_icon="🔗", layout="wide")
style.apply("🔗 URL & QR Scanner", "Check suspicious links and QR codes before you open or pay",
            chips=["🔗 Link risk score", "📱 QR scanning", "💸 UPI QR warnings"])


def show(res):
    style.risk_card(res["level"], res["risk_score"], res["advice"])
    style.gauge(res["risk_score"])
    st.subheader("Why?")
    for reason in res["reasons"]:
        st.write("• " + reason)


tab_url, tab_qr = st.tabs(["🔗 Check a link", "📱 Scan a QR code"])

with tab_url:
    url = st.text_input("Paste a link", placeholder="e.g. http://sbi-kyc-update.xyz/login")
    if st.button("Check link", type="primary"):
        if not url.strip():
            st.warning("Please paste a link first.")
        else:
            try:
                r = requests.post(f"{API}/check_url", json={"url": url}, timeout=10)
                r.raise_for_status()
                show(r.json())
            except Exception:
                st.error("Can't reach the API. Is `uvicorn api:app --reload` running?")

with tab_qr:
    mode = st.radio("Input", ["Upload image", "Use camera"], horizontal=True)
    if mode == "Upload image":
        img = st.file_uploader("QR code image", type=["png", "jpg", "jpeg", "webp"], key="qr")
    else:
        img = st.camera_input("Point the camera at a QR code")

    if img and st.button("Scan QR", type="primary"):
        try:
            r = requests.post(
                f"{API}/scan_qr",
                files={"file": ("qr.png", img.getvalue(), "image/png")},
                timeout=30,
            )
            r.raise_for_status()
            res = r.json()
        except Exception:
            st.error("Can't reach the API. Is `uvicorn api:app --reload` running?")
            res = None

        if res:
            if not res["found"]:
                st.warning(res["message"])
            else:
                st.write(f"**Type:** {res['type'].upper()}")
                st.code(res["content"])
                if res["type"] == "upi":
                    d = res["details"]
                    st.write(f"Payee ID: `{d['payee_id']}` | Name: `{d['payee_name']}` | Amount: `{d['amount']}`")
                show(res)