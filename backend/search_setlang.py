path = r"c:\Users\Al-Hussain Com\Desktop\SmartZameen Ai\frontend\js\lang.js"
with open(path, "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

for line_no, line in enumerate(lines, 1):
    if "setLang" in line:
        print(f"{line_no}: {line.strip()}")
