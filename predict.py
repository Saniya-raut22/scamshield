import joblib

model = joblib.load("spam_model.pkl")

print("Spam Detector (type 'quit' to exit)")
while True:
    msg = input("\nEnter message: ").strip()
    if msg.lower() == "quit":
        break
    prob = model.predict_proba([msg])[0][1]
    label = "SPAM" if prob >= 0.5 else "NOT SPAM"
    print(f"Result: {label} (spam probability: {prob:.2f})")