import re

path = r"c:\Users\Al-Hussain Com\Desktop\SmartZameen Ai\frontend\predict.html"
with open(path, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

lines = content.splitlines()

# Search for key div sections and their line numbers
keywords = [
    "predict-layout", "predict-left-col", "predict-center-col", "predict-right-col",
    "soil-card", "engine-card", "camera-panel", "voice-", "farmer-friendly-card", "awaiting-data-card"
]

for idx, line in enumerate(lines, 1):
    if "<div" in line and any(k in line for k in keywords):
        clean = "".join(c if ord(c) < 128 else "?" for c in line.strip())
        print(f"{idx}: {clean}")
