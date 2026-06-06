import re

path = r"c:\Users\Al-Hussain Com\Desktop\SmartZameen Ai\frontend\predict.html"
with open(path, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

print("File length:", len(content))

for line_no, line in enumerate(content.splitlines(), 1):
    if any(k in line for k in ["soil-analysis-result", "awaiting-data-card", "soil-preview", "camera-panel"]):
        # Keep only ASCII characters to prevent Windows console encoding crashes
        clean_line = "".join(c if ord(c) < 128 else "?" for c in line.strip())
        print(f"{line_no}: {clean_line}")
