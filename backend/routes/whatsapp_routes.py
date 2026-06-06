from flask import Blueprint, request
from twilio.twiml.messaging_response import MessagingResponse
import joblib
import numpy as np
import os

whatsapp_bp = Blueprint('whatsapp', __name__)

MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'ml_models')
model     = joblib.load(os.path.join(MODEL_DIR, 'crop_model.pkl'))
le_crop   = joblib.load(os.path.join(MODEL_DIR, 'le_crop.pkl'))
le_season = joblib.load(os.path.join(MODEL_DIR, 'le_season.pkl'))
le_region = joblib.load(os.path.join(MODEL_DIR, 'le_region.pkl'))

sessions = {}

# ─────────────────────────────────────────
#  SOIL / WATER / CROP PROFILES
# ─────────────────────────────────────────
SOIL_PROFILES = {
    '1': {'n': 30,  'p': 25, 'k': 35, 'ph': 7.5},  # Sandy
    '2': {'n': 60,  'p': 45, 'k': 55, 'ph': 7.0},  # Clay
    '3': {'n': 50,  'p': 40, 'k': 45, 'ph': 6.8},  # Loam
}

WATER_PROFILES = {
    '1': 120,  # Canal
    '2': 90,   # Tube well
    '3': 45,   # Rain-fed
}

PREV_CROP_ADJUST = {
    '1': {'n': +10, 'p': -5,  'k': -5},
    '2': {'n': +5,  'p': -10, 'k': -10},
    '3': {'n': -5,  'p': +5,  'k': +5},
    '4': {'n': 0,   'p': 0,   'k': 0},
}

REGION_MAP = {'1': 'Punjab', '2': 'Sindh', '3': 'KPK', '4': 'Balochistan'}
SEASON_MAP = {'1': 'rabi',   '2': 'kharif'}

def estimate_temp(region, season):
    temps = {
        ('Punjab',      'rabi'):   15, ('Punjab',      'kharif'): 32,
        ('Sindh',       'rabi'):   18, ('Sindh',       'kharif'): 36,
        ('KPK',         'rabi'):   10, ('KPK',         'kharif'): 28,
        ('Balochistan', 'rabi'):   12, ('Balochistan', 'kharif'): 30,
    }
    return temps.get((region, season), 25)

VALID = {'1', '2', '3', '4'}

# ─────────────────────────────────────────
#  ALL STRINGS IN 5 LANGUAGES
# ─────────────────────────────────────────
STRINGS = {

    # ── URDU (default) ──────────────────────────────────────────────────
    'ur': {
        'welcome': (
            "🌾 *السلام علیکم! SmartZameen میں خوش آمدید*\n\n"
            "میں آپ کو بہترین فصل بتاؤں گا — بس 5 آسان سوال!\n\n"
            "1️⃣ فصل تجویز کروائیں\n"
            "2️⃣ موسم دیکھیں\n"
            "3️⃣ فصلوں کی فہرست\n\n"
            "زبان تبدیل کریں:\n"
            "🔤 *en* — English\n"
            "🔤 *pa* — پنجابی\n"
            "🔤 *sd* — سنڌي\n"
            "🔤 *ps* — پښتو\n\n"
            "نمبر لکھیں 👇"
        ),
        'ask_weather_city': "🌤 کس شہر کا موسم دیکھنا ہے؟\n\nلکھیں: Lahore / Karachi / Multan / Peshawar / Quetta",
        'crops_header': "*پاکستان کی اہم فصلیں:*\n\n",
        'crops_footer': "\n\n↩️ مینو: *menu*",
        'flow_start': "✅ *فصل تجویز شروع کریں*\n\nبس 5 آسان سوال — کوئی آلہ درکار نہیں! 😊\n\n",
        'invalid': "⚠️ براہ کرم صرف نمبر لکھیں: 1، 2، 3، یا 4\n\n",
        'not_understood': "سمجھ نہیں آیا 😊\nشروع کرنے کے لیے *menu* لکھیں۔",
        'weather_footer': "\n\n↩️ مینو کے لیے *menu* لکھیں",
        'weather_not_found': "❌ شہر نہیں ملا۔ درست نام لکھیں۔",
        'weather_error': "❌ موسم لوڈ نہیں ہوا۔",
        'result_header': "✅ *آپ کی فصل تجویز تیار ہے!*\n\n",
        'result_best': "💡 *{crop}* آپ کے لیے سب سے موزوں ہے!\n\n",
        'result_top': "*بہترین فصلیں:*\n",
        'result_footer': "\n\n↩️ دوبارہ: *menu*",
        'result_detail': "مزید تفصیل:\n🌐 http://localhost:5000/predict.html\n\n",
        'error': "❌ خرابی آئی: {e}\nدوبارہ کوشش کریں: *menu*",
        'lang_changed': "✅ زبان اردو میں تبدیل ہو گئی!\n\nشروع کریں: *menu*",
        'questions': [
            ("region",    "آپ کا علاقہ کونسا ہے؟\n\n1️⃣ پنجاب\n2️⃣ سندھ\n3️⃣ خیبرپختونخوا\n4️⃣ بلوچستان"),
            ("season",    "موسم کونسا ہے؟\n\n1️⃣ 🌨 سردی (اکتوبر–مارچ)\n2️⃣ ☀️ گرمی (اپریل–ستمبر)"),
            ("soil",      "آپ کی زمین کیسی ہے؟\n\n1️⃣ ریتلی — پانی جلدی جذب ہو\n2️⃣ چکنی — پانی دیر تک رہے\n3️⃣ درمیانی — نارمل زمین"),
            ("water",     "پانی کا ذریعہ کیا ہے؟\n\n1️⃣ 🌊 نہر\n2️⃣ ⚙️ ٹیوب ویل\n3️⃣ 🌧 بارش پر منحصر"),
            ("prev_crop", "پچھلی فصل کونسی تھی؟\n\n1️⃣ گندم\n2️⃣ چاول\n3️⃣ کپاس\n4️⃣ کوئی نہیں / نئی زمین"),
        ],
        'soil_labels': {'1': 'ریتلی', '2': 'چکنی', '3': 'درمیانی'},
        'region_label': 'علاقہ',
        'season_label': 'موسم',
        'soil_label':   'زمین',
    },

    # ── ENGLISH ─────────────────────────────────────────────────────────
    'en': {
        'welcome': (
            "🌾 *Welcome to SmartZameen AI!*\n\n"
            "I will suggest the best crop for you — just 5 easy questions!\n\n"
            "1️⃣ Get Crop Recommendation\n"
            "2️⃣ Check Weather\n"
            "3️⃣ List of Crops\n\n"
            "Change language:\n"
            "🔤 *ur* — اردو\n"
            "🔤 *pa* — پنجابی\n"
            "🔤 *sd* — سنڌي\n"
            "🔤 *ps* — پښتو\n\n"
            "Type a number 👇"
        ),
        'ask_weather_city': "🌤 Which city's weather do you want?\n\nType: Lahore / Karachi / Multan / Peshawar / Quetta",
        'crops_header': "*Major Crops of Pakistan:*\n\n",
        'crops_footer': "\n\n↩️ Main menu: *menu*",
        'flow_start': "✅ *Starting Crop Recommendation*\n\nJust 5 easy questions — no instruments needed! 😊\n\n",
        'invalid': "⚠️ Please type only a number: 1, 2, 3, or 4\n\n",
        'not_understood': "Didn't understand 😊\nType *menu* to start.",
        'weather_footer': "\n\n↩️ Type *menu* for main menu",
        'weather_not_found': "❌ City not found. Please type a valid city name.",
        'weather_error': "❌ Could not load weather. Try again later.",
        'result_header': "✅ *Your Crop Recommendation is Ready!*\n\n",
        'result_best': "💡 *{crop}* is the best choice for you!\n\n",
        'result_top': "*Best Crops:*\n",
        'result_footer': "\n\n↩️ Again: *menu*",
        'result_detail': "More details:\n🌐 http://localhost:5000/predict.html\n\n",
        'error': "❌ Error: {e}\nTry again: *menu*",
        'lang_changed': "✅ Language changed to English!\n\nType *menu* to start.",
        'questions': [
            ("region",    "What is your region?\n\n1️⃣ Punjab\n2️⃣ Sindh\n3️⃣ Khyber Pakhtunkhwa\n4️⃣ Balochistan"),
            ("season",    "What is the current season?\n\n1️⃣ 🌨 Winter (Oct–Mar)\n2️⃣ ☀️ Summer (Apr–Sep)"),
            ("soil",      "How is your soil?\n\n1️⃣ Sandy — water drains quickly\n2️⃣ Clay — water stays long\n3️⃣ Medium — normal soil"),
            ("water",     "What is your water source?\n\n1️⃣ 🌊 Canal\n2️⃣ ⚙️ Tube well\n3️⃣ 🌧 Rain-fed only"),
            ("prev_crop", "What was your last crop?\n\n1️⃣ Wheat\n2️⃣ Rice\n3️⃣ Cotton\n4️⃣ None / New land"),
        ],
        'soil_labels': {'1': 'Sandy', '2': 'Clay', '3': 'Medium'},
        'region_label': 'Region',
        'season_label': 'Season',
        'soil_label':   'Soil',
    },

    # ── PUNJABI ─────────────────────────────────────────────────────────
    'pa': {
        'welcome': (
            "🌾 *جی آیاں نوں! SmartZameen وچ خوش آمدید*\n\n"
            "میں تینوں سب توں ودیا فصل دساں گا — بس 5 آسان سوال!\n\n"
            "1️⃣ فصل دی صلاح لؤ\n"
            "2️⃣ موسم ویکھو\n"
            "3️⃣ فصلاں دی لسٹ\n\n"
            "زبان بدلو:\n"
            "🔤 *ur* — اردو\n"
            "🔤 *en* — English\n"
            "🔤 *sd* — سنڌي\n"
            "🔤 *ps* — پښتو\n\n"
            "نمبر لکھو 👇"
        ),
        'ask_weather_city': "🌤 کیہڑے شہر دا موسم ویکھنا اے؟\n\nلکھو: Lahore / Karachi / Multan / Peshawar / Quetta",
        'crops_header': "*پاکستان دیاں اہم فصلاں:*\n\n",
        'crops_footer': "\n\n↩️ مینو: *menu*",
        'flow_start': "✅ *فصل دی صلاح شروع کرو*\n\nبس 5 سوال — کوئی آلہ نئیں چاہیدا! 😊\n\n",
        'invalid': "⚠️ صرف نمبر لکھو: 1، 2، 3 یا 4\n\n",
        'not_understood': "سمجھ نئیں آئی 😊\nشروع کرن لئی *menu* لکھو۔",
        'weather_footer': "\n\n↩️ مینو لئی *menu* لکھو",
        'weather_not_found': "❌ شہر نئیں لبیا۔ سہی نام لکھو۔",
        'weather_error': "❌ موسم لوڈ نئیں ہویا۔",
        'result_header': "✅ *تیری فصل دی صلاح تیار اے!*\n\n",
        'result_best': "💡 *{crop}* تیرے لئی سب توں ودیا اے!\n\n",
        'result_top': "*سب توں ودیاں فصلاں:*\n",
        'result_footer': "\n\n↩️ فیر: *menu*",
        'result_detail': "ہور تفصیل:\n🌐 http://localhost:5000/predict.html\n\n",
        'error': "❌ غلطی آئی: {e}\nفیر کوشش کرو: *menu*",
        'lang_changed': "✅ زبان پنجابی وچ بدل گئی!\n\nشروع کرو: *menu*",
        'questions': [
            ("region",    "تیرا علاقہ کیہڑا اے؟\n\n1️⃣ پنجاب\n2️⃣ سندھ\n3️⃣ خیبرپختونخوا\n4️⃣ بلوچستان"),
            ("season",    "موسم کیہڑا اے؟\n\n1️⃣ 🌨 سردی (اکتوبر–مارچ)\n2️⃣ ☀️ گرمی (اپریل–ستمبر)"),
            ("soil",      "تیری زمین کیہو جئی اے؟\n\n1️⃣ ریتلی — پانی جلدی جذب ہو جاوے\n2️⃣ چکنی — پانی چِر رہے\n3️⃣ وچکارلی — نارمل زمین"),
            ("water",     "پانی کتھوں ملدا اے؟\n\n1️⃣ 🌊 نہر\n2️⃣ ⚙️ ٹیوب ویل\n3️⃣ 🌧 بارش تے منحصر"),
            ("prev_crop", "پچھلی فصل کیہڑی سی؟\n\n1️⃣ کنک\n2️⃣ چاول\n3️⃣ کپاہ\n4️⃣ کوئی نئیں / نویں زمین"),
        ],
        'soil_labels': {'1': 'ریتلی', '2': 'چکنی', '3': 'وچکارلی'},
        'region_label': 'علاقہ',
        'season_label': 'موسم',
        'soil_label':   'زمین',
    },

    # ── SINDHI ──────────────────────────────────────────────────────────
    'sd': {
        'welcome': (
            "🌾 *ڀلي ڪري آيا! SmartZameen ۾ خوش آمديد*\n\n"
            "مان توکي بهترين فصل ٻڌائيندس — بس 5 سوال!\n\n"
            "1️⃣ فصل جي صلاح وٺو\n"
            "2️⃣ موسم ڏسو\n"
            "3️⃣ فصلن جي فهرست\n\n"
            "ٻولي بدلايو:\n"
            "🔤 *ur* — اردو\n"
            "🔤 *en* — English\n"
            "🔤 *pa* — پنجابی\n"
            "🔤 *ps* — پښتو\n\n"
            "نمبر لکھو 👇"
        ),
        'ask_weather_city': "🌤 ڪهڙي شهر جو موسم ڏسڻو آهي؟\n\nلکھو: Lahore / Karachi / Multan / Peshawar / Quetta",
        'crops_header': "*پاڪستان جا اهم فصل:*\n\n",
        'crops_footer': "\n\n↩️ مينيو: *menu*",
        'flow_start': "✅ *فصل جي صلاح شروع ڪريو*\n\nبس 5 سوال — ڪو اوزار نه گهرجي! 😊\n\n",
        'invalid': "⚠️ مهرباني ڪري صرف نمبر لکھو: 1، 2، 3 يا 4\n\n",
        'not_understood': "سمجھ ۾ نه آيو 😊\nشروع ڪرڻ لاءِ *menu* لکھو۔",
        'weather_footer': "\n\n↩️ مينيو لاءِ *menu* لکھو",
        'weather_not_found': "❌ شهر نه مليو۔ صحيح نالو لکھو۔",
        'weather_error': "❌ موسم لوڊ نه ٿيو۔",
        'result_header': "✅ *توهان جي فصل جي صلاح تيار آهي!*\n\n",
        'result_best': "💡 *{crop}* توهان لاءِ سڀ کان بهتر آهي!\n\n",
        'result_top': "*بهترين فصل:*\n",
        'result_footer': "\n\n↩️ ٻيهر: *menu*",
        'result_detail': "وڌيڪ تفصيل:\n🌐 http://localhost:5000/predict.html\n\n",
        'error': "❌ غلطي آئي: {e}\nٻيهر ڪوشش ڪريو: *menu*",
        'lang_changed': "✅ ٻولي سنڌي ۾ بدلجي وئي!\n\nشروع ڪريو: *menu*",
        'questions': [
            ("region",    "توهان جو علائقو ڪهڙو آهي؟\n\n1️⃣ پنجاب\n2️⃣ سنڌ\n3️⃣ خيبرپختونخوا\n4️⃣ بلوچستان"),
            ("season",    "موسم ڪهڙو آهي؟\n\n1️⃣ 🌨 سياري (آڪٽوبر–مارچ)\n2️⃣ ☀️ اونهاري (اپريل–سيپٽمبر)"),
            ("soil",      "توهان جي زمين ڪيئن آهي؟\n\n1️⃣ ريتيلي — پاڻي جلدي جذب ٿئي\n2️⃣ چڪڻي — پاڻي دير تائين رهي\n3️⃣ وچولي — نارمل زمين"),
            ("water",     "پاڻي جو ذريعو ڪهڙو آهي؟\n\n1️⃣ 🌊 نهر\n2️⃣ ⚙️ ٽيوب ويل\n3️⃣ 🌧 برسات تي منحصر"),
            ("prev_crop", "گذريل فصل ڪهڙي هئي؟\n\n1️⃣ ڪڻڪ\n2️⃣ چانور\n3️⃣ ڪپهه\n4️⃣ ڪجھ به نه / نئين زمين"),
        ],
        'soil_labels': {'1': 'ريتيلي', '2': 'چڪڻي', '3': 'وچولي'},
        'region_label': 'علائقو',
        'season_label': 'موسم',
        'soil_label':   'زمين',
    },

    # ── PASHTO ──────────────────────────────────────────────────────────
    'ps': {
        'welcome': (
            "🌾 *ښه راغلاست! SmartZameen ته ښه راغلاست*\n\n"
            "زه به تاسو ته غوره فصل وښيم — یوازې ۵ اسانه پوښتنې!\n\n"
            "1️⃣ د فصل وړاندیز واخلئ\n"
            "2️⃣ هوا وګورئ\n"
            "3️⃣ د فصلونو لیست\n\n"
            "ژبه بدله کړئ:\n"
            "🔤 *ur* — اردو\n"
            "🔤 *en* — English\n"
            "🔤 *pa* — پنجابی\n"
            "🔤 *sd* — سنڌي\n\n"
            "شمیره ولیکئ 👇"
        ),
        'ask_weather_city': "🌤 د کوم ښار هوا وګورئ؟\n\nولیکئ: Lahore / Karachi / Multan / Peshawar / Quetta",
        'crops_header': "*د پاکستان مهم فصلونه:*\n\n",
        'crops_footer': "\n\n↩️ مینو: *menu*",
        'flow_start': "✅ *د فصل وړاندیز پیل کړئ*\n\nیوازې ۵ پوښتنې — هیڅ وسیله نه دي پکار! 😊\n\n",
        'invalid': "⚠️ مهرباني وکړئ یوازې شمیره ولیکئ: 1، 2، 3 یا 4\n\n",
        'not_understood': "پوه نه شوم 😊\nد پیل لپاره *menu* ولیکئ۔",
        'weather_footer': "\n\n↩️ د مینو لپاره *menu* ولیکئ",
        'weather_not_found': "❌ ښار ونه موندل شو۔ سم نوم ولیکئ۔",
        'weather_error': "❌ هوا لوډ نه شوه۔",
        'result_header': "✅ *ستاسو د فصل وړاندیز چمتو دی!*\n\n",
        'result_best': "💡 *{crop}* ستاسو لپاره غوره انتخاب دی!\n\n",
        'result_top': "*غوره فصلونه:*\n",
        'result_footer': "\n\n↩️ بیا: *menu*",
        'result_detail': "نور تفصیل:\n🌐 http://localhost:5000/predict.html\n\n",
        'error': "❌ تیروتنه: {e}\nبیا هڅه وکړئ: *menu*",
        'lang_changed': "✅ ژبه پښتو ته بدله شوه!\n\nپیل کړئ: *menu*",
        'questions': [
            ("region",    "ستاسو سیمه کومه ده؟\n\n1️⃣ پنجاب\n2️⃣ سند\n3️⃣ خیبرپښتونخوا\n4️⃣ بلوچستان"),
            ("season",    "موسم کوم دی؟\n\n1️⃣ 🌨 ژمی (اکتوبر–مارچ)\n2️⃣ ☀️ اوړی (اپریل–سپتمبر)"),
            ("soil",      "ستاسو ځمکه څنګه ده؟\n\n1️⃣ شګه — اوبه ژر جذبیږي\n2️⃣ خټکه — اوبه ډیر وخت پاتې کیږي\n3️⃣ منځني — نورمال ځمکه"),
            ("water",     "د اوبو سرچینه کومه ده؟\n\n1️⃣ 🌊 کانال\n2️⃣ ⚙️ ټیوب ویل\n3️⃣ 🌧 باران باندې تکیه"),
            ("prev_crop", "وروستۍ فصل کومه وه؟\n\n1️⃣ غنم\n2️⃣ وریجې\n3️⃣ پنبه\n4️⃣ هیڅ / نوې ځمکه"),
        ],
        'soil_labels': {'1': 'شګه', '2': 'خټکه', '3': 'منځني'},
        'region_label': 'سیمه',
        'season_label': 'موسم',
        'soil_label':   'ځمکه',
    },
}

# Language trigger words
LANG_TRIGGERS = {
    'ur': ['ur', 'urdu', 'اردو'],
    'en': ['en', 'english'],
    'pa': ['pa', 'punjabi', 'پنجابی'],
    'sd': ['sd', 'sindhi', 'سنڌي'],
    'ps': ['ps', 'pashto', 'پښتو'],
}

MENU_TRIGGERS = ['hi', 'hello', 'helo', 'salam', 'start', 'menu', '0',
                 'السلام', 'مینو', 'شروع', 'مينيو']


# ─────────────────────────────────────────
#  MAIN ROUTE
# ─────────────────────────────────────────
@whatsapp_bp.route('/whatsapp', methods=['POST'])
def whatsapp():
    incoming = request.form.get('Body', '').strip()
    sender   = request.form.get('From')
    incoming_lower = incoming.lower()

    resp = MessagingResponse()
    msg  = resp.message()

    session = sessions.get(sender, {})
    lang    = session.get('lang', 'ur')   
    s       = STRINGS[lang]             

    # ── Language switch ──
    for code, triggers in LANG_TRIGGERS.items():
        if incoming_lower in triggers:
            session['lang'] = code
            session['flow'] = None
            sessions[sender] = session
            msg.body(STRINGS[code]['lang_changed'])
            return str(resp)

    # ── Menu / Welcome ──
    if incoming_lower in MENU_TRIGGERS:
        session = {'lang': lang}
        sessions[sender] = session
        msg.body(s['welcome'])
        return str(resp)

    # ── Weather ──
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

    # ── Crops list ──
    if incoming == '3' and not session.get('flow'):
        try:
            from database.db import get_all_crops
            crops = get_all_crops()
            lines = [f"🌱 {c['name']} — {c['urdu_name']}" for c in crops[:8]]
            msg.body(s['crops_header'] + "\n".join(lines) + s['crops_footer'])
        except:
            msg.body("❌ Error loading crops.")
        return str(resp)

    # ── Crop recommendation flow ──
    if incoming == '1' and not session.get('flow'):
        session['flow'] = 'crop'
        session['step'] = 0
        session['data'] = {}
        sessions[sender] = session
        msg.body(s['flow_start'] + s['questions'][0][1])
        return str(resp)

    if session.get('flow') == 'crop':
        step = session.get('step', 0)
        data = session.get('data', {})
        questions = s['questions']

        if incoming not in VALID:
            msg.body(s['invalid'] + questions[step][1])
        else:
            field = questions[step][0]
            data[field] = incoming
            step += 1
            session['step'] = step
            session['data'] = data

            if step < len(questions):
                sessions[sender] = session
                msg.body(questions[step][1])
            else:
                sessions[sender] = {'lang': lang}
                msg.body(predict_from_simple(data, s, lang))

        return str(resp)

    # ── Fallback ──
    msg.body(s['not_understood'])
    return str(resp)


# ─────────────────────────────────────────
#  PREDICTION
# ─────────────────────────────────────────
def predict_from_simple(data, s, lang):
    try:
        region_key = data.get('region', '1')
        season_key = data.get('season', '1')
        soil_key   = data.get('soil',   '3')
        water_key  = data.get('water',  '1')
        prev_key   = data.get('prev_crop', '4')

        region = REGION_MAP[region_key]
        season = SEASON_MAP[season_key]
        soil   = SOIL_PROFILES[soil_key]
        adj    = PREV_CROP_ADJUST[prev_key]

        n        = max(0, soil['n'] + adj['n'])
        p        = max(0, soil['p'] + adj['p'])
        k        = max(0, soil['k'] + adj['k'])
        ph       = soil['ph']
        rainfall = WATER_PROFILES[water_key]
        temp     = estimate_temp(region, season)

        season_enc = le_season.transform([season])[0]
        region_enc = le_region.transform([region])[0]

        features = np.array([[n, p, k, ph, temp, rainfall, season_enc, region_enc]])
        pred     = model.predict(features)[0]
        proba    = model.predict_proba(features)[0]
        top3     = np.argsort(proba)[::-1][:3]

        best_crop = le_crop.inverse_transform([pred])[0]

        alt_lines = []
        for i, idx in enumerate(top3):
            crop_name = le_crop.inverse_transform([idx])[0]
            pct       = proba[idx] * 100
            emoji     = ["🥇", "🥈", "🥉"][i]
            alt_lines.append(f"{emoji} {crop_name} — {pct:.0f}%")

        soil_label   = s['soil_labels'][soil_key]
        region_label = s['region_label']
        season_label = s['season_label']
        soil_lbl     = s['soil_label']
        season_name  = "rabi" if season_key == '1' else "kharif"

        return (
            s['result_header'] +
            f"{region_label}: {region} | {season_label}: {season_name}\n"
            f"{soil_lbl}: {soil_label}\n\n" +
            s['result_top'] +
            "\n".join(alt_lines) + "\n\n" +
            s['result_best'].format(crop=best_crop) +
            s['result_detail'] +
            s['result_footer']
        )

    except Exception as e:
        return s['error'].format(e=str(e))


# ─────────────────────────────────────────
#  WEATHER
# ─────────────────────────────────────────
def get_weather(city, s):
    import requests as req
    try:
        API_KEY = os.getenv('WEATHER_API_KEY', '')
        r = req.get(
            f"http://api.openweathermap.org/data/2.5/weather"
            f"?q={city.strip().capitalize()},PK&appid={API_KEY}&units=metric",
            timeout=5
        )
        d = r.json()
        if d.get('cod') == 200:
            return (
                f"🌤 *{city.capitalize()}*\n\n"
                f"🌡 {d['main']['temp']}°C\n"
                f"💧 {d['main']['humidity']}%\n"
                f"💨 {d['wind']['speed']} m/s\n"
                f"☁️ {d['weather'][0]['description']}"
            )
        return s['weather_not_found']
    except:
        return s['weather_error']