import os
import tempfile
import wave
from io import BytesIO
from typing import List

import cv2
import joblib
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image
from pydantic import BaseModel, Field

from db import clear_history, get_stats, init_db, log_scan
from urlcheck import analyze_content, analyze_url
from voicecheck import analyze_transcript

app = FastAPI(title="ScamShield API", version="1.4")
model = joblib.load("spam_model.pkl")
init_db()

_ocr = None
_whisper = None
LEVEL_TO_LABEL = {"High": "scam", "Medium": "suspicious", "Low": "safe"}
AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm", ".aac", ".mp4"}
MAX_AUDIO_MB = 25


def get_ocr():
    global _ocr
    if _ocr is None:
        from rapidocr_onnxruntime import RapidOCR
        _ocr = RapidOCR()
    return _ocr


def get_whisper():
    # Loaded on first use; the model downloads once
    global _whisper
    if _whisper is None:
        from faster_whisper import WhisperModel
        size = os.environ.get("WHISPER_MODEL", "base")
        _whisper = WhisperModel(size, device="cpu", compute_type="int8")
    return _whisper


def read_wav_16k(path):
    """Read a 16-bit PCM WAV as 16 kHz mono float32, without needing av/ffmpeg."""
    with wave.open(path, "rb") as wf:
        channels, width = wf.getnchannels(), wf.getsampwidth()
        rate, frames = wf.getframerate(), wf.getnframes()
        raw = wf.readframes(frames)
    if width != 2:
        raise ValueError("Only 16-bit WAV is supported here")
    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    if rate != 16000:
        new_len = int(len(audio) * 16000 / rate)
        audio = np.interp(
            np.linspace(0, len(audio) - 1, new_len),
            np.arange(len(audio)),
            audio,
        ).astype(np.float32)
    return audio


def safe_log(kind, content, label, score):
    try:
        return log_scan(kind, content, label, score)
    except Exception as e:
        print("DB log failed:", e)
        return None


class Message(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)


class Batch(BaseModel):
    texts: List[str] = Field(..., min_length=1, max_length=100)


class UrlIn(BaseModel):
    url: str = Field(..., min_length=3, max_length=2000)


def verdict(prob: float) -> dict:
    return {
        "label": "spam" if prob >= 0.5 else "ham",
        "spam_probability": round(prob, 4),
    }


def text_label(prob: float) -> str:
    return "scam" if prob >= 0.5 else "safe"


def load_image(file: UploadFile):
    data = file.file.read()
    try:
        img = Image.open(BytesIO(data)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="That file is not a valid image.")
    img.thumbnail((2000, 2000))
    return img


@app.get("/")
def root():
    return {"service": "ScamShield API", "status": "running", "docs": "/docs"}


@app.post("/predict")
def predict(m: Message):
    prob = float(model.predict_proba([m.text])[0][1])
    safe_log("text", m.text, text_label(prob), round(prob * 100))
    return {"text": m.text, **verdict(prob)}


@app.post("/predict_batch")
def predict_batch(b: Batch):
    probs = model.predict_proba(b.texts)[:, 1]
    return [{"text": t, **verdict(float(p))} for t, p in zip(b.texts, probs)]


@app.post("/predict_image")
def predict_image(file: UploadFile = File(...)):
    img = load_image(file)
    result, _ = get_ocr()(np.array(img))
    if not result:
        return {"text": "", "label": "unknown", "spam_probability": None,
                "message": "No text found in the image."}
    text = " ".join(line[1] for line in result)
    prob = float(model.predict_proba([text])[0][1])
    safe_log("image", text, text_label(prob), round(prob * 100))
    return {"text": text, **verdict(prob)}


@app.post("/check_url")
def check_url(u: UrlIn):
    res = analyze_url(u.url)
    safe_log("url", u.url, LEVEL_TO_LABEL[res["level"]], res["risk_score"])
    return res


@app.post("/scan_qr")
def scan_qr(file: UploadFile = File(...)):
    img = load_image(file)
    bgr = np.array(img)[:, :, ::-1].copy()
    detector = cv2.QRCodeDetector()

    content = ""
    for scale in (1.0, 2.0, 0.5):
        frame = bgr if scale == 1.0 else cv2.resize(bgr, None, fx=scale, fy=scale)
        content, _, _ = detector.detectAndDecode(frame)
        if content:
            break

    if not content:
        return {"found": False, "message": "No QR code found. Try a clearer, closer image."}

    res = analyze_content(content)

    if res["type"] == "text":
        prob = float(model.predict_proba([res["content"]])[0][1])
        if prob >= 0.5:
            res.update(risk_score=int(prob * 100), level="High",
                       reasons=["The text inside this QR code looks like spam or a scam."],
                       advice="Do not follow any instructions in this QR code.")

    safe_log("qr", res["content"], LEVEL_TO_LABEL[res["level"]], res["risk_score"])
    return {"found": True, **res}


@app.post("/analyze_audio")
def analyze_audio(file: UploadFile = File(...)):
    data = file.file.read()
    if len(data) > MAX_AUDIO_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Audio is larger than {MAX_AUDIO_MB} MB.")
    ext = os.path.splitext(file.filename or "")[1].lower() or ".wav"
    if ext not in AUDIO_EXTS:
        raise HTTPException(status_code=400, detail="Unsupported audio format.")

    fd, path = tempfile.mkstemp(suffix=ext)
    os.close(fd)
    try:
        with open(path, "wb") as f:
            f.write(data)

        # WAV files are read directly; other formats need av/ffmpeg
        audio_input = path
        if ext == ".wav":
            try:
                audio_input = read_wav_16k(path)
            except Exception as e:
                print("WAV fallback to av:", repr(e))
                audio_input = path

        w = get_whisper()
        segs, info = w.transcribe(audio_input, beam_size=1)
        original = " ".join(s.text.strip() for s in segs).strip()
        english = original
        if original and info.language != "en":
            segs2, _ = w.transcribe(audio_input, task="translate",
                                    language=info.language, beam_size=1)
            english = " ".join(s.text.strip() for s in segs2).strip()
    except Exception as e:
        print("Audio error:", repr(e))
        tip = "" if ext == ".wav" else " Tip: try a .wav file."
        raise HTTPException(
            status_code=400,
            detail=f"Could not process audio: {type(e).__name__}: {str(e)[:200]}.{tip}",
        )
    finally:
        try:
            os.remove(path)
        except OSError:
            pass

    if not original:
        return {"found": False, "message": "No speech detected in this audio."}

    res = analyze_transcript(english, model)
    safe_log("voice", english, LEVEL_TO_LABEL[res["level"]], res["risk_score"])
    return {"found": True, "language": info.language, "transcript": original,
            "english": english, **res}


@app.get("/stats")
def stats(limit: int = 50):
    return get_stats(limit)


@app.delete("/history")
def delete_history():
    clear_history()
    return {"status": "cleared"}