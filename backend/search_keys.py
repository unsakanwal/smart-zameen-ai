import re

path = r"c:\Users\Al-Hussain Com\Desktop\SmartZameen Ai\frontend\js\lang.js"
with open(path, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

# Match top-level keys inside LANG object
# e.g., LANG = { en: { ... }, ur: { ... } } or similar
match = re.search(r"const\s+LANG\s*=\s*\{([\s\S]+?)\};", content)
if match:
    keys = re.findall(r"^\s+([a-zA-Z0-9_]+)\s*:\s*\{", match.group(1), re.MULTILINE)
    print("Found language keys:", keys)
else:
    # Just print the first 300 lines to see
    print("Could not match LANG object regex. Printing first 200 chars:")
    print(content[:200])
