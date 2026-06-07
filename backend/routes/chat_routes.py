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
import json
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


@chat_bp.route("/api/ai-recommend", methods=["POST"])
def ai_recommend():
    """OpenAI-powered crop recommendation from soil-sensor values.

    The IoT node sends the soil sample the farmer crafted with the sliders; OpenAI
    (the same key that powers the chat) plays agronomist and returns a structured
    recommendation. Shape: {ok, success, crop, urdu, confidence, top3[], reason,
    model, model_key}. This replaces the on-disk ML models for the node.
    """
    data = request.get_json(silent=True) or {}

    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return jsonify({
            "ok": False,
            "error": "OpenAI API key not set. Add OPENAI_API_KEY to backend/.env and restart."
        }), 503

    def _val(k):
        v = data.get(k)
        return v if v not in (None, "", -1, "-1") else None

    soil = {
        "nitrogen":    _val("nitrogen"),    "phosphorus": _val("phosphorus"),
        "potassium":   _val("potassium"),   "ph":         _val("ph"),
        "temperature": _val("temperature"), "rainfall":   _val("rainfall"),
        "humidity":    _val("humidity"),    "moisture":   _val("moisture"),
    }
    reading = ", ".join(f"{k}={v}" for k, v in soil.items() if v is not None) or "no values provided"
    region = (data.get("region") or "Pakistan").strip() or "Pakistan"
    season = (data.get("season") or "").strip()
    lang   = data.get("lang") or "en"
    lang_name = LANG_NAMES.get(lang, "English")

    system = (
        "You are SmartZameen AI, an expert agronomist for Pakistani farms. Given soil "
        "sensor values, recommend the single best crop to grow plus two alternatives, "
        "considering common Pakistani crops and the Rabi/Kharif seasons. "
        "Respond with ONLY a compact JSON object (no prose, no markdown) of exactly this shape:\n"
        '{"crop":"<english crop name, lowercase>","urdu":"<urdu name>","confidence":<integer 0-100>,'
        '"top3":[{"crop":"<eng>","urdu":"<urdu>","confidence":<int>},{...},{...}],'
        '"reason":"<one short sentence in ' + lang_name + '>"}\n'
        "top3[0] MUST be the same as the main crop. Make confidence realistic for the soil."
    )
    user = (f"Soil sensor reading: {reading}. Region: {region}. "
            f"Season: {season or 'unspecified'}. Recommend the best crop for this soil.")

    try:
        res = requests.post(
            OPENAI_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": OPENAI_MODEL,
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": user}],
                "temperature": 0.3, "max_tokens": 400,
                "response_format": {"type": "json_object"},
            },
            timeout=60,
        )
        if res.status_code != 200:
            try:
                detail = res.json().get("error", {}).get("message", "")
            except Exception:
                detail = res.text[:200]
            return jsonify({"ok": False, "error": f"OpenAI error ({res.status_code}): {detail}"}), 502

        rec = json.loads(res.json()["choices"][0]["message"]["content"])

        def _crop(o):
            try:
                conf = int(round(float(o.get("confidence", 0))))
            except (TypeError, ValueError):
                conf = 0
            return {"crop": str(o.get("crop", "")).strip().lower(),
                    "urdu": o.get("urdu", ""),
                    "confidence": max(0, min(100, conf))}

        top3 = [_crop(o) for o in (rec.get("top3") or []) if o][:3]
        main = _crop(rec)
        if not main["crop"] and top3:
            main = top3[0]
        if not top3:
            top3 = [main]

        return jsonify({
            "ok": True, "success": True,
            "crop": main["crop"], "urdu": main["urdu"], "confidence": main["confidence"],
            "top3": top3, "reason": rec.get("reason", ""),
            "model": "OpenAI · " + OPENAI_MODEL, "model_key": "openai",
        })

    except requests.exceptions.Timeout:
        return jsonify({"ok": False, "error": "OpenAI request timed out — please try again."}), 504
    except (ValueError, KeyError) as e:
        return jsonify({"ok": False, "error": f"Could not parse the AI response ({e})."}), 502
    except Exception as e:
        return jsonify({"ok": False, "error": f"Recommend failed: {type(e).__name__}: {e}"}), 500
