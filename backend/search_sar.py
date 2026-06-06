path = r"c:\Users\Al-Hussain Com\Desktop\SmartZameen Ai\frontend\predict.html"
with open(path, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

# Find any lines containing "sar-"
for line_no, line in enumerate(content.splitlines(), 1):
    if "sar-" in line:
        print(f"{line_no}: {line.strip()}")
