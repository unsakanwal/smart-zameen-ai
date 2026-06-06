from flask import Blueprint, request
from twilio.twiml.messaging_response import MessagingResponse
from routes.whatsapp_routes import (
    sessions, STRINGS, LANG_TRIGGERS, MENU_TRIGGERS,
    VALID, predict_from_simple, get_weather
)

sms_bp = Blueprint('sms', __name__)

@sms_bp.route('/sms', methods=['POST'])
def sms():
    incoming       = request.form.get('Body', '').strip()
    sender         = request.form.get('From')
    incoming_lower = incoming.lower()

    resp = MessagingResponse()
    msg  = resp.message()

    session = sessions.get(sender, {})
    lang    = session.get('lang', 'ur')
    s       = STRINGS[lang]

    # Language switch
    for code, triggers in LANG_TRIGGERS.items():
        if incoming_lower in triggers:
            session['lang'] = code
            session['flow'] = None
            sessions[sender] = session
            msg.body(STRINGS[code]['lang_changed'])
            return str(resp)

    # Menu
    if incoming_lower in MENU_TRIGGERS:
        session = {'lang': lang}
        sessions[sender] = session
        msg.body(s['welcome'])
        return str(resp)

    # Weather
    if incoming == '2' and not session.get('flow'):
        session['flow'] = 'weather'
        sessions[sender] = session
        msg.body(s['ask_weather_city'])
        return str(resp)

    if session.get('flow') == 'weather':
        result = get_weather(incoming, s)
        msg.body(result + s['weather_footer'])
        session['flow'] = None
        sessions[sender] = session
        return str(resp)

    # Crops list
    if incoming == '3' and not session.get('flow'):
        try:
            from database.db import get_all_crops
            crops = get_all_crops()
            lines = [f"* {c['name']} - {c['urdu_name']}" for c in crops[:8]]
            msg.body(s['crops_header'] + "\n".join(lines) + s['crops_footer'])
        except:
            msg.body("Error loading crops.")
        return str(resp)

    # Crop recommendation flow
    if incoming == '1' and not session.get('flow'):
        session['flow'] = 'crop'
        session['step'] = 0
        session['data'] = {}
        sessions[sender] = session
        msg.body(s['flow_start'] + s['questions'][0][1])
        return str(resp)

    if session.get('flow') == 'crop':
        step      = session.get('step', 0)
        data      = session.get('data', {})
        questions = s['questions']

        if incoming not in VALID:
            msg.body(s['invalid'] + questions[step][1])
        else:
            field       = questions[step][0]
            data[field] = incoming
            step       += 1
            session['step'] = step
            session['data'] = data

            if step < len(questions):
                sessions[sender] = session
                msg.body(questions[step][1])
            else:
                sessions[sender] = {'lang': lang}
                msg.body(predict_from_simple(data, s, lang))

        return str(resp)

    msg.body(s['not_understood'])
    return str(resp)