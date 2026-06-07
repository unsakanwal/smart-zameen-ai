"""
voice_routes.py — Speech-to-text for the Crop Advisor chat (OpenAI Whisper).

The voice feature lives inside the main chat: the browser records the farmer's
voice, uploads it here, and we transcribe it with OpenAI Whisper (far more
accurate for Urdu / Punjabi / Sindhi / Pashto than the browser's built-in
recognizer). The transcribed text is then sent through the normal /api/chat
flow, so a single OpenAI-powered assistant handles text, image AND voice.

    from routes.voice_routes import voice_bp
    app.register_blueprint(voice_bp)
"""

import os
import requests
from flask import Blueprint, request, jsonify

voice_bp = Blueprint('voice', __name__)

OPENAI_TRANSCRIBE_URL = "https://api.openai.com/v1/audio/transcriptions"
WHISPER_MODEL = os.getenv("OPENAI_WHISPER_MODEL", "whisper-1")

# UI language code -> ISO-639-1 hint for Whisper (improves accuracy a lot).
LANG_HINT = {'ur': 'ur', 'pa': 'pa', 'sd': 'sd', 'ps': 'ps', 'en': 'en'}


@voice_bp.route('/api/transcribe', methods=['POST'])
def transcribe():
    """Accept an uploaded audio blob ('audio' multipart field) and return its
    text via OpenAI Whisper. Optional 'lang' form field hints the language."""
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return jsonify({'ok': False,
                        'error': 'OpenAI API key not set. Add OPENAI_API_KEY to backend/.env.'}), 503

    if 'audio' not in request.files:
        return jsonify({'ok': False, 'error': 'No audio uploaded.'}), 400

    audio = request.files['audio']
    lang = (request.form.get('lang') or '').strip().lower()

    try:
        files = {'file': (audio.filename or 'voice.webm',
                          audio.stream,
                          audio.mimetype or 'audio/webm')}
        data = {'model': WHISPER_MODEL}
        if lang in LANG_HINT:
            data['language'] = LANG_HINT[lang]

        res = requests.post(
            OPENAI_TRANSCRIBE_URL,
            headers={'Authorization': f'Bearer {key}'},
            files=files,
            data=data,
            timeout=60,
        )
        if res.status_code != 200:
            detail = ''
            try:
                detail = res.json().get('error', {}).get('message', '')
            except Exception:
                detail = res.text[:200]
            return jsonify({'ok': False, 'error': f'Whisper error ({res.status_code}): {detail}'}), 502

        text = (res.json().get('text') or '').strip()
        return jsonify({'ok': True, 'text': text})

    except requests.exceptions.Timeout:
        return jsonify({'ok': False, 'error': 'Transcription timed out — please try again.'}), 504
    except Exception as e:
        return jsonify({'ok': False, 'error': f'Transcription failed: {type(e).__name__}: {e}'}), 500
