import pyttsx3

SCAM = ("Hello sir, this is calling from the cyber crime department. "
        "A case has been registered against your Aadhaar number and you will be arrested "
        "within two hours. To close the case you must stay on the call and do not tell anyone. "
        "Please download AnyDesk and share the code. "
        "Also tell me the OTP you just received on your phone.")

NORMAL = ("Hi, are you coming to college tomorrow? Please bring the lab notes "
          "and let me know what time you will reach. I will wait near the library.")

engine = pyttsx3.init()
engine.save_to_file(SCAM, "test_call_scam.wav")
engine.save_to_file(NORMAL, "test_call_normal.wav")
engine.runAndWait()
print("Created 2 test audio files")