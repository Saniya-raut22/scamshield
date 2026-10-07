import os

import joblib
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from hinglish_data import HINGLISH_HAM, HINGLISH_SPAM

# Hinglish training messages are repeated so 5,000+ English ones don't drown them out
HINGLISH_REPEAT = 4
NAMES = ["Naive Bayes", "Logistic Regression", "Linear SVM"]

# ---------- English data (UCI SMS Spam Collection) ----------
df = pd.read_csv("data/sms.tsv", sep="\t", header=None, names=["label", "text"])
df["y"] = (df["label"] == "spam").astype(int)
en_train_X, en_test_X, en_train_y, en_test_y = train_test_split(
    df["text"], df["y"], test_size=0.2, random_state=42, stratify=df["y"]
)

# ---------- Hinglish data ----------
hi = pd.DataFrame({
    "text": HINGLISH_SPAM + HINGLISH_HAM,
    "y": [1] * len(HINGLISH_SPAM) + [0] * len(HINGLISH_HAM),
})
extra = "data/hinglish_extra.csv"  # optional: your own examples, columns: label,text
if os.path.exists(extra):
    ex = pd.read_csv(extra)
    ex["y"] = (ex["label"].astype(str).str.lower() == "spam").astype(int)
    hi = pd.concat([hi, ex[["text", "y"]]], ignore_index=True)
    print(f"Added {len(ex)} examples from {extra}")
hi = hi.drop_duplicates(subset="text").reset_index(drop=True)

hi_train_X, hi_test_X, hi_train_y, hi_test_y = train_test_split(
    hi["text"], hi["y"], test_size=0.3, random_state=42, stratify=hi["y"]
)

comb_X = pd.concat([en_train_X] + [hi_train_X] * HINGLISH_REPEAT, ignore_index=True)
comb_y = pd.concat([en_train_y] + [hi_train_y] * HINGLISH_REPEAT, ignore_index=True)

print(f"English: {len(df)} messages | Hinglish: {len(hi)} messages "
      f"({len(hi_train_X)} train, {len(hi_test_X)} test)")


def build(name):
    models = {
        "Naive Bayes": MultinomialNB(),
        "Logistic Regression": LogisticRegression(max_iter=1000, class_weight="balanced"),
        "Linear SVM": CalibratedClassifierCV(LinearSVC(class_weight="balanced")),
    }
    return Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2)),
        ("clf", models[name]),
    ])


def evaluate(pipe, X, y):
    pred = pipe.predict(X)
    return {
        "acc": accuracy_score(y, pred),
        "prec": precision_score(y, pred, zero_division=0),
        "rec": recall_score(y, pred, zero_division=0),
        "f1": f1_score(y, pred, zero_division=0),
    }


def row(name, label, en, hi_s):
    return {"Model": name, "Training data": label,
            "English F1": en["f1"], "Hinglish Precision": hi_s["prec"],
            "Hinglish Recall": hi_s["rec"], "Hinglish F1": hi_s["f1"]}


compare_rows, english_rows = [], []
base_pipes, comb_pipes, scores = {}, {}, {}

for name in NAMES:
    base = build(name).fit(en_train_X, en_train_y)
    comb = build(name).fit(comb_X, comb_y)
    base_pipes[name], comb_pipes[name] = base, comb

    en_b, hi_b = evaluate(base, en_test_X, en_test_y), evaluate(base, hi_test_X, hi_test_y)
    en_c, hi_c = evaluate(comb, en_test_X, en_test_y), evaluate(comb, hi_test_X, hi_test_y)

    compare_rows.append(row(name, "English only", en_b, hi_b))
    compare_rows.append(row(name, "English + Hinglish", en_c, hi_c))
    english_rows.append({"Model": name, "Accuracy": en_c["acc"], "Precision": en_c["prec"],
                         "Recall": en_c["rec"], "F1": en_c["f1"]})
    scores[name] = (en_c["f1"] + hi_c["f1"]) / 2

compare_df = pd.DataFrame(compare_rows).round(4)
english_df = pd.DataFrame(english_rows).round(4)
compare_df.to_csv("results_hinglish.csv", index=False)
english_df.to_csv("results.csv", index=False)

print("\nBefore vs after Hinglish (Hinglish scores are on unseen Hinglish test messages):\n")
print(compare_df.to_string(index=False))

best_name = max(scores, key=scores.get)
joblib.dump(comb_pipes[best_name], "spam_model.pkl")
print(f"\nBest model: {best_name}. Saved spam_model.pkl")

# ---------- Quick demo on new messages ----------
SAMPLES = [
    "Aapka account band hone wala hai, turant KYC update karo warna block ho jayega",
    "Badhai ho, aapne lottery jeeti hai, inaam lene ke liye apni bank details bhejo",
    "Free recharge milega, abhi link par click karo",
    "Kal subah milte hain, notes leke aana",
    "Main ghar pahunch gaya, tum log kab nikal rahe ho?",
    "URGENT! You won a free prize, click this link now",
]
old_p = base_pipes[best_name].predict_proba(SAMPLES)[:, 1]
new_p = comb_pipes[best_name].predict_proba(SAMPLES)[:, 1]
print("\nSpam probability: English-only model vs new model")
for text, a, b in zip(SAMPLES, old_p, new_p):
    print(f"  {a:5.0%} -> {b:5.0%}   {text[:62]}")