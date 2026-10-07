import qrcode

qrcode.make("http://sbi-kyc-update.xyz/login").save("test_qr_scam.png")
qrcode.make("https://www.amazon.in").save("test_qr_safe.png")
qrcode.make("upi://pay?pa=cashprize@upi&pn=Lucky%20Draw&am=5000").save("test_qr_upi.png")
print("Created 3 test QR images")