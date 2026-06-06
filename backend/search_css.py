import re

path = r"c:\Users\Al-Hussain Com\Desktop\SmartZameen Ai\frontend\predict.html"
with open(path, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

style_match = re.search(r"<style>([\s\S]+?)</style>", content)
if style_match:
    styles = style_match.group(1)
    
    # Extract blocks that contain soil-card
    blocks = re.findall(r"(\.[a-zA-Z0-9_\-\s,]+?\{[\s\S]*?\})", styles)
    for b in blocks:
        if "soil-card" in b:
            print("-" * 40)
            print(b.strip())
