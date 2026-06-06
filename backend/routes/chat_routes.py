"""
chat_routes.py — Crop Advisor full chat backend (OpenAI).

Powers the Crop Advisor chat assistant: text + image (vision) + attached-file
text, with conversation history. Uses the OpenAI Chat Completions REST API via
`requests` (no extra dependency). Set OPENAI_API_KEY in backend/.env.

    from routes.chat_routes import chat_bp
    app.register_blueprint(chat_bp)
"""

from flask import Blueprint, request, jsonify
import os
import requests

chat_bp = Blueprint("chat", __name__)

OPENAI_URL   = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")   # vision-capable + cheap

SYSTEM_PROMPT = (
    "You are SmartZameen AI — a friendly, practical farming assistant for Pakistani "
    "farmers. Help with crops, soil, fertilizer, irrigation, weather, pests, diseases, "
    "seasons, and market guidance. Reply in the SAME language the user writes in "
    "(Urdu, Punjabi, Sindhi, Pashto, or English). Keep answers clear and concise. "
    "If the user sends a photo of soil, a crop, or a leaf, analyse it and give specific advice."
)

# Languages the assistant may receive (only used to hint behaviour).
LANG_NAMES = {"ur": "Urdu", "pa": "Punjabi", "sd": "Sindhi", "ps": "Pashto", "en": "English"}


@chat_bp.route("/api/chat", methods=["POST"])
def chat():
    """Crop Advisor chat. Accepts text, an optional image (data URI), and
    optional attached-file text. Returns the assistant's reply."""
    data = request.get_json(silent=True) or {}
    message   = (data.get("message") or "").strip()
    image     = data.get("image")                      # data:image/...;base64,... or None
    file_text = (data.get("file_text") or "").strip()  # extracted text from an attached file
    file_name = (data.get("file_name") or "").strip()
    history   = data.get("history") or []              # [{role, content(str)}], text-only
    lang      = data.get("lang") or ""

    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return jsonify({
            "ok": False,
            "error": "OpenAI API key not set. Add OPENAI_API_KEY to backend/.env and restart."
        }), 503

    if not message and not image and not file_text:
        return jsonify({"ok": False, "error": "Empty message."}), 400

    # ---- build the message list ----
    system = SYSTEM_PROMPT
    if lang in LANG_NAMES:
        system += f" The user's selected language is {LANG_NAMES[lang]}."
    messages = [{"role": "system", "content": system}]

    # prior turns (text only — keeps payload/cost small)
    for turn in history[-10:]:
        role = turn.get("role")
        content = turn.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content:
            messages.append({"role": role, "content": content})

    # current user turn (multimodal)
    text = message
    if file_text:
        label = f' "{file_name}"' if file_name else ""
        text += f"\n\n[Attached file{label}]:\n{file_text[:6000]}"
    parts = []
    if text:
        parts.append({"type": "text", "text": text})
    if image and isinstance(image, str) and image.startswith("data:image"):
        parts.append({"type": "image_url", "image_url": {"url": image}})
    if not parts:
        parts = [{"type": "text", "text": "(no input)"}]
    messages.append({"role": "user", "content": parts})

    try:
        res = requests.post(
            OPENAI_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": OPENAI_MODEL, "messages": messages, "max_tokens": 700, "temperature": 0.6},
            timeout=60,
        )
        if res.status_code != 200:
            detail = ""
            try:
                detail = res.json().get("error", {}).get("message", "")
            except Exception:
                detail = res.text[:200]
            return jsonify({"ok": False, "error": f"OpenAI error ({res.status_code}): {detail}"}), 502

        reply = res.json()["choices"][0]["message"]["content"].strip()
        return jsonify({"ok": True, "reply": reply})

    except requests.exceptions.Timeout:
        return jsonify({"ok": False, "error": "OpenAI request timed out — please try again."}), 504
    except Exception as e:
        return jsonify({"ok": False, "error": f"Chat failed: {type(e).__name__}: {e}"}), 500
