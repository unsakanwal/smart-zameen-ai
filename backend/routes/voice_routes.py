import os
import anthropic
from flask import Blueprint, request, jsonify

voice_bp = Blueprint('voice', __name__)

@voice_bp.route('/api/voice-chat', methods=['POST'])
def voice_chat():
    try:
        data    = request.get_json()
        message = data.get('message', '').strip()
        lang    = data.get('lang', 'ur-PK')
        history = data.get('history', [])

        if not message:
            return jsonify({'error': 'Message khali hai!'}), 400

        lang_name = {
            'ur-PK': 'Urdu', 'pa-PK': 'Punjabi',
            'sd-PK': 'Sindhi', 'ps-AF': 'Pashto', 'en-US': 'English'
        }.get(lang, 'Urdu')

        system = f"""You are SmartZameen AI — a friendly, expert agricultural assistant for Pakistani farmers.

RULES:
- Reply ONLY in {lang_name} language
- Keep replies SHORT: 2-3 sentences maximum
- Use simple, easy words that farmers understand
- Be warm, helpful, and encouraging
- Topics: crops, soil, fertilizer, pesticides, irrigation, weather, pests, diseases, harvest, market prices, seeds
- If asked soil form data: tell them to say province + season + numbers like "Punjab, Rabi, 80 40 30 6.8 24 150"
- Never give harmful advice
- Always give practical, actionable tips"""

        messages = []
        for h in history[-6:]:
            if h.get('role') in ('user', 'assistant'):
                messages.append({'role': h['role'], 'content': h['content']})
        messages.append({'role': 'user', 'content': message})

        client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY', ''))
        response = client.messages.create(
            model      = 'claude-haiku-4-5-20251001',
            max_tokens = 300,
            system     = system,
            messages   = messages,
        )

        reply = response.content[0].text.strip()
        return jsonify({'success': True, 'reply': reply})

    except anthropic.APIError as e:
        return jsonify({'error': f'AI error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500