import os
import re
import sqlite3
from collections import Counter
from contextlib import closing

DB_PATH = os.environ.get("DB_PATH", "scamshield.db")

STOP = set("""this that with your have from will been they their what when where which would
there about into than then them were just only also more some such like over here very each
much many make""".split())


def _conn():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with closing(_conn()) as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                kind TEXT NOT NULL,
                content TEXT,
                label TEXT NOT NULL,
                score REAL
            )"""
        )
        c.commit()


def log_scan(kind, content, label, score):
    with closing(_conn()) as c:
        cur = c.execute(
            "INSERT INTO scans (kind, content, label, score) VALUES (?, ?, ?, ?)",
            (kind, (content or "")[:300], label, score),
        )
        c.commit()
        return cur.lastrowid


def get_stats(limit=50):
    limit = max(1, min(int(limit), 1000))
    with closing(_conn()) as c:
        total = c.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
        by_label = {r["label"]: r["n"] for r in c.execute(
            "SELECT label, COUNT(*) AS n FROM scans GROUP BY label")}
        by_kind = {r["kind"]: r["n"] for r in c.execute(
            "SELECT kind, COUNT(*) AS n FROM scans GROUP BY kind")}
        per_day = [dict(r) for r in c.execute(
            """SELECT date(created_at) AS day, COUNT(*) AS n,
                      COALESCE(SUM(label = 'scam'), 0) AS scams
               FROM scans GROUP BY day ORDER BY day DESC LIMIT 14""")]
        recent = [dict(r) for r in c.execute(
            """SELECT id, created_at, kind, content, label, score
               FROM scans ORDER BY id DESC LIMIT ?""", (limit,))]
        scam_texts = [r["content"] for r in c.execute(
            """SELECT content FROM scans
               WHERE label = 'scam' AND kind IN ('text', 'image')
               ORDER BY id DESC LIMIT 500""")]

    words = Counter()
    for t in scam_texts:
        for w in re.findall(r"[a-z]{4,}", (t or "").lower()):
            if w not in STOP:
                words[w] += 1

    return {
        "total": total,
        "by_label": by_label,
        "by_kind": by_kind,
        "per_day": per_day[::-1],
        "top_words": words.most_common(10),
        "recent": recent,
    }


def clear_history():
    with closing(_conn()) as c:
        c.execute("DELETE FROM scans")
        c.commit()