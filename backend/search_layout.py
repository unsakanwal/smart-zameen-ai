path = r"c:\Users\Al-Hussain Com\Desktop\SmartZameen Ai\frontend\predict.html"
with open(path, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

for line_no, line in enumerate(content.splitlines(), 1):
    if "farmer" in line.lower() and "<div" in line:
        clean_line = "".join(c if ord(c) < 128 else "?" for c in line.strip())
        print(f"{line_no}: {clean_line}")
