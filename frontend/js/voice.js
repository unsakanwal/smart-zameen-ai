if (typeof API_URL === 'undefined') {
    var API_URL = (window.location.protocol === 'file:' || (window.location.port !== '' && window.location.port !== '80')) 
      ? 'http://localhost' 
      : window.location.origin;
}

let recognition  = null;
let isListening  = false;
let isSpeaking   = false;
let voiceEnabled = false;
let chatHistory  = [];

// =============
// VOICE TOGGLE
// =============
function toggleVoiceMode() {
    voiceEnabled = !voiceEnabled;
    const bar     = document.getElementById('voice-toggle-bar');
    const badge   = document.getElementById('voice-mode-badge');
    const section = document.getElementById('voice-section-full');

    if (voiceEnabled) {
        if (bar)     bar.classList.add('active');
        if (badge)   badge.style.display = 'flex';
        if (section) section.style.display = 'block';
        const lang = document.getElementById('voice-lang')?.value || 'ur-PK';
        setTimeout(() => speakText(getLangTexts(lang).greeting, lang), 300);
        renderChatBubble('ai', getLangTexts(lang).greeting_short);
    } else {
        if (bar)     bar.classList.remove('active');
        if (badge)   badge.style.display = 'none';
        if (section) section.style.display = 'none';
        window.speechSynthesis?.cancel();
        if (recognition) { try { recognition.stop(); } catch(e) {} }
    }
}

// ===================
// SPEECH RECOGNITION
// ===================
function setupRecognition() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
        showVoiceMsg('Chrome استعمال کریں  -  voice support نہیں ہے', 'error');
        return null;
    }
    const lang = document.getElementById('voice-lang')?.value || 'ur-PK';
    const rec  = new SR();
    rec.lang            = lang;
    rec.continuous      = false;
    rec.interimResults  = true;
    rec.maxAlternatives = 3;

    rec.onstart = () => {
        isListening = true;
        updateMicUI(true);
        showVoiceStatus(true);
        hideVoiceMsg();
    };

    rec.onresult = (event) => {
        let interim = '', finalText = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const t = event.results[i][0].transcript;
            if (event.results[i].isFinal) finalText += t;
            else interim += t;
        }
        const heardEl  = document.getElementById('voice-heard');
        const heardTxt = document.getElementById('voice-heard-txt');
        if (heardEl && heardTxt) {
            heardEl.style.display = 'block';
            heardTxt.textContent  = finalText || interim;
        }
        if (finalText) handleVoiceInput(finalText);
    };

    rec.onend = () => {
        isListening = false;
        updateMicUI(false);
        showVoiceStatus(false);
    };

    rec.onerror = (event) => {
        isListening = false;
        updateMicUI(false);
        showVoiceStatus(false);
        const errMap = {
            'no-speech':     'Kuch suna nahi  -  dobara bolein 🎤',
            'not-allowed':   'Mic ki permission dijiye',
            'network':       'Internet check karein',
            'audio-capture': 'Mic check karein',
            'aborted':       '',
        };
        const msg = errMap[event.error];
        if (msg) showVoiceMsg(msg, 'error');
    };
    return rec;
}

function startVoice() {
    if (isListening) { recognition?.stop(); return; }
    recognition = setupRecognition();
    if (!recognition) return;
    hideVoiceMsg();
    const heardEl = document.getElementById('voice-heard');
    if (heardEl) heardEl.style.display = 'none';
    setTimeout(() => { try { recognition.start(); } catch(e) {} }, 100);
}

// ============================================================
// MAIN: VOICE INPUT HANDLER  -  chatbot + form fill
// ============================================================
async function handleVoiceInput(text) {
    const lang = document.getElementById('voice-lang')?.value || 'ur-PK';

    renderChatBubble('user', text);

    const typingId = renderTypingIndicator();

    const isFormInput = detectFormInput(text);

    if (isFormInput) {
        removeTypingIndicator(typingId);
        const filled = fillFormFromVoice(text);
        const texts  = getLangTexts(lang);
        let reply;
        if (filled > 0 && checkAllFilled()) {
            reply = texts.all_filled;
            renderChatBubble('ai', reply);
            speakText(reply, lang);
            setTimeout(() => predictCrop(), 1200);
        } else if (filled > 0) {
            reply = texts.filled.replace('{n}', filled);
            renderChatBubble('ai', reply);
            speakText(reply, lang);
        } else {
            reply = texts.not_understood;
            renderChatBubble('ai', reply);
            speakText(reply, lang);
        }
    } else {
        try {
            const aiReply = await callClaudeChatbot(text, lang);
            removeTypingIndicator(typingId);
            renderChatBubble('ai', aiReply);
            speakText(aiReply, lang);
        } catch(e) {
            removeTypingIndicator(typingId);
            const fallback = getLocalReply(text, lang);
            renderChatBubble('ai', fallback);
            speakText(fallback, lang);
        }
    }
}

function detectFormInput(text) {
    const t = text.toLowerCase();
    const formKeywords = [
        'punjab','sindh','kpk','balochistan','پنجاب','سندھ','بلوچستان','خیبر',
        'rabi','kharif','ربیع','خریف','winter','summer','سردی','گرمی',
        'nitrogen','phosphorus','potassium','نائٹروجن','فاسفورس','پوٹاشیم',
        'form','fill','bharain','بھریں','درج',
    ];
    const hasNumbers = /\d+/.test(text);
    const hasKeyword = formKeywords.some(k => t.includes(k.toLowerCase()) || text.includes(k));
    return hasNumbers || hasKeyword;
}

async function callClaudeChatbot(userMessage, lang) {
    const langName = { 'ur-PK':'Urdu','pa-PK':'Punjabi','sd-PK':'Sindhi','ps-AF':'Pashto','en-US':'English' }[lang] || 'Urdu';

    const systemPrompt = `You are SmartZameen AI  -  a friendly agricultural assistant for Pakistani farmers. 
Answer in ${langName} language ONLY. Keep answers SHORT (2-3 sentences max) and simple for farmers.
Topics: crops, soil, fertilizer, weather, irrigation, pests, diseases, seasons, market prices.
If asked about soil data form: guide them to say numbers like "Punjab, Rabi, nitrogen 80".
Always be helpful, warm, and practical. Use simple words.`;

    chatHistory.push({ role: 'user', content: userMessage });
    if (chatHistory.length > 10) chatHistory = chatHistory.slice(-10);

    const response = await fetch(`${API_URL}/api/voice-chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            message: userMessage,
            lang:    lang,
            history: chatHistory.slice(-6),
            system:  systemPrompt,
        })
    });

    if (!response.ok) throw new Error('API error');
    const data = await response.json();

    if (data.reply) {
        chatHistory.push({ role: 'assistant', content: data.reply });
        return data.reply;
    }
    throw new Error('No reply');
}

function getLocalReply(text, lang) {
    const t = text.toLowerCase();
    const replies = {
        'ur-PK': {
            wheat:     'گندم ربیع کی فصل ہے  -  نومبر سے مارچ تک بوئیں۔ نائٹروجن 80-100 کلو فی ایکڑ ڈالیں۔',
            cotton:    'کپاس کے لیے درجہ حرارت 25-35°C اور اچھی نکاسی آب ضروری ہے۔',
            rice:      'چاول کے لیے زیادہ پانی اور گرم موسم چاہیے  -  خریف میں بوئیں۔',
            fertilizer:'کھاد کے لیے مٹی کا ٹیسٹ ضروری ہے  -  عام طور پر DAP اور یوریا استعمال کریں۔',
            water:     'فصل کے حساب سے پانی دیں  -  گندم کو 4-5 مرتبہ، کپاس کو 6-8 مرتبہ۔',
            pest:      'کیڑوں سے بچاؤ کے لیے وقت پر سپرے کریں اور فصل کا معائنہ کرتے رہیں۔',
            default:   'آپ کا سوال سمجھ آیا! براہ کرم انٹرنیٹ چیک کریں تاکہ میں بہتر مدد کر سکوں۔',
        },
        'en-US': {
            wheat:     'Wheat is a Rabi crop  -  sow November to March. Apply 80-100kg nitrogen per acre.',
            cotton:    'Cotton needs 25-35°C temperature and good drainage for best yield.',
            rice:      'Rice needs lots of water and warm weather  -  grow in Kharif season.',
            fertilizer:'Get a soil test first  -  generally use DAP and Urea for most crops.',
            water:     'Irrigation depends on crop  -  wheat 4-5 times, cotton 6-8 times per season.',
            pest:      'Spray on time and inspect crops regularly to prevent pest damage.',
            default:   'Good question! Please check internet connection for better AI responses.',
        },
    };
    const r = replies[lang] || replies['ur-PK'];
    if (t.includes('wheat') || t.includes('گندم')) return r.wheat;
    if (t.includes('cotton') || t.includes('کپاس')) return r.cotton;
    if (t.includes('rice') || t.includes('چاول')) return r.rice;
    if (t.includes('fertilizer') || t.includes('کھاد') || t.includes('khad')) return r.fertilizer;
    if (t.includes('water') || t.includes('پانی') || t.includes('irrigation')) return r.water;
    if (t.includes('pest') || t.includes('کیڑ') || t.includes('spray')) return r.pest;
    return r.default;
}


function getChatBox() {
    let box = document.getElementById('voice-chat-box');
    if (!box) {
        box = document.createElement('div');
        box.id = 'voice-chat-box';
        box.style.cssText = `
            max-height: 280px;
            overflow-y: auto;
            padding: 10px 4px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-bottom: 10px;
        `;
        const sec = document.getElementById('voice-section-full');
        const micBtn = document.getElementById('mic-btn');
        if (sec && micBtn) sec.insertBefore(box, micBtn);
        else if (sec) sec.appendChild(box);
    }
    return box;
}

function renderChatBubble(role, text) {
    const box = getChatBox();
    const wrap = document.createElement('div');
    wrap.style.cssText = `display:flex;align-items:flex-end;gap:6px;${role==='user'?'flex-direction:row-reverse;':''}`;

    const avatar = document.createElement('div');
    avatar.style.cssText = `
        width:28px;height:28px;border-radius:50%;flex-shrink:0;
        display:flex;align-items:center;justify-content:center;
        font-size:14px;
        background:${role==='ai'?'#1e6b2e':'#e8f5e9'};
        color:${role==='ai'?'#fff':'#1e6b2e'};
    `;
    avatar.textContent = role === 'ai' ? '🌾' : '👤';

    const bubble = document.createElement('div');
    bubble.style.cssText = `
        max-width: 78%;
        padding: 9px 13px;
        border-radius: ${role==='ai'?'16px 16px 16px 4px':'16px 16px 4px 16px'};
        font-size: 13px;
        line-height: 1.5;
        direction: rtl;
        text-align: right;
        font-family: 'Noto Nastaliq Urdu', sans-serif;
        background: ${role==='ai'?'#eaf3de':'#1e6b2e'};
        color: ${role==='ai'?'#27500a':'#fff'};
        word-break: break-word;
        animation: bubblePop 0.2s ease;
    `;
    bubble.textContent = text;

    wrap.appendChild(avatar);
    wrap.appendChild(bubble);
    box.appendChild(wrap);
    box.scrollTop = box.scrollHeight;

    // Bubble animation
    if (!document.getElementById('bubble-style')) {
        const st = document.createElement('style');
        st.id = 'bubble-style';
        st.textContent = '@keyframes bubblePop{from{opacity:0;transform:scale(0.92)}to{opacity:1;transform:scale(1)}}';
        document.head.appendChild(st);
    }
}

function renderTypingIndicator() {
    const box  = getChatBox();
    const id   = 'typing-' + Date.now();
    const wrap = document.createElement('div');
    wrap.id = id;
    wrap.style.cssText = 'display:flex;align-items:flex-end;gap:6px;';
    wrap.innerHTML = `
        <div style="width:28px;height:28px;border-radius:50%;background:#1e6b2e;display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0;">🌾</div>
        <div style="background:#eaf3de;border-radius:16px 16px 16px 4px;padding:10px 14px;display:flex;gap:4px;align-items:center;">
            <span style="width:6px;height:6px;background:#97c459;border-radius:50%;animation:dot 1.2s ease-in-out infinite;"></span>
            <span style="width:6px;height:6px;background:#97c459;border-radius:50%;animation:dot 1.2s ease-in-out infinite 0.4s;"></span>
            <span style="width:6px;height:6px;background:#97c459;border-radius:50%;animation:dot 1.2s ease-in-out infinite 0.8s;"></span>
        </div>`;
    if (!document.getElementById('dot-style')) {
        const st = document.createElement('style');
        st.id = 'dot-style';
        st.textContent = '@keyframes dot{0%,80%,100%{transform:scale(0.6);opacity:.5}40%{transform:scale(1);opacity:1}}';
        document.head.appendChild(st);
    }
    box.appendChild(wrap);
    box.scrollTop = box.scrollHeight;
    return id;
}

function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function fillFormFromVoice(text) {
    const t = text.toLowerCase();
    let filled = 0;

    const regionKeywords = {
        punjab:      ['punjab','پنجاب','لاہور','lahore','ملتان','multan','فیصل','faisalabad','راولپنڈی','rawalpindi'],
        sindh:       ['sindh','سندھ','سنڌ','karachi','کراچی','hyderabad','حیدرآباد'],
        kpk:         ['kpk','khyber','خیبر','peshawar','پشاور','swat','سوات'],
        balochistan: ['balochistan','بلوچستان','quetta','کوئٹہ'],
    };
    for (const [region, keywords] of Object.entries(regionKeywords)) {
        if (keywords.some(k => t.includes(k.toLowerCase()) || text.includes(k))) {
            const el = document.getElementById('i-reg');
            if (el) { el.value = region; filled++; highlightField('i-reg'); } break;
        }
    }

    const rabiWords   = ['rabi','ربیع','سردی','winter','sardi','thanda','ٹھنڈا','december','january','february'];
    const kharifWords = ['kharif','خریف','گرمی','summer','garmi','june','july','august'];
    if (rabiWords.some(w => t.includes(w) || text.includes(w))) {
        const el = document.getElementById('i-sea');
        if (el) { el.value = 'rabi'; filled++; highlightField('i-sea'); }
    } else if (kharifWords.some(w => t.includes(w) || text.includes(w))) {
        const el = document.getElementById('i-sea');
        if (el) { el.value = 'kharif'; filled++; highlightField('i-sea'); }
    }

    const labeledPatterns = [
        { pattern: /(?:nitrogen|n|نائٹروجن)\s*[:=]?\s*(\d+(?:\.\d+)?)/i, field: 'i-n' },
        { pattern: /(?:phosphorus|p|فاسفورس)\s*[:=]?\s*(\d+(?:\.\d+)?)/i, field: 'i-p' },
        { pattern: /(?:potassium|k|پوٹاشیم)\s*[:=]?\s*(\d+(?:\.\d+)?)/i, field: 'i-k' },
        { pattern: /(?:ph|پی ایچ|تیزابیت)\s*[:=]?\s*(\d+(?:\.\d+)?)/i,   field: 'i-ph' },
        { pattern: /(?:temperature|temp|درجہ)\s*[:=]?\s*(\d+(?:\.\d+)?)/i, field: 'i-tmp' },
        { pattern: /(?:rainfall|rain|بارش)\s*[:=]?\s*(\d+(?:\.\d+)?)/i,   field: 'i-rain' },
    ];
    let usedLabeled = false;
    labeledPatterns.forEach(({ pattern, field }) => {
        const match = text.match(pattern);
        if (match) { const el = document.getElementById(field); if (el) { el.value = match[1]; filled++; highlightField(field); usedLabeled = true; } }
    });

    if (!usedLabeled) {
        const numbers = text.match(/\d+(?:\.\d+)?/g);
        if (numbers) {
            ['i-n','i-p','i-k','i-ph','i-tmp','i-rain'].forEach((id, idx) => {
                if (numbers[idx]) { const el = document.getElementById(id); if (el) { el.value = numbers[idx]; filled++; highlightField(id); } }
            });
        }
    }
    return filled;
}

function checkAllFilled() {
    return ['i-n','i-p','i-k','i-ph','i-tmp','i-rain','i-reg','i-sea']
        .every(id => { const el = document.getElementById(id); return el && el.value !== ''; });
}


function speakResult(cropName, confidence, urduName, extraInfo, force) {
    if (!voiceEnabled && !force) return;
    const lang  = document.getElementById('voice-lang')?.value || 'ur-PK';
    const texts = getLangTexts(lang);
    let msg = texts.result.replace('{crop}', urduName || cropName).replace('{conf}', Math.round(confidence || 0));
    if (extraInfo) msg += ' ' + extraInfo;
    renderChatBubble('ai', msg);
    speakText(msg, lang);
}

function autoSpeakAfterResult(result) {
    if (!voiceEnabled) return;
    setTimeout(() => speakResult(result.crop, result.confidence, result.urdu || result.crop, null, true), 800);
}

function speakText(text, lang) {
    if (!window.speechSynthesis || !text) return;
    window.speechSynthesis.cancel();
    setTimeout(() => {
        const utter  = new SpeechSynthesisUtterance(text);
        utter.lang   = lang || document.getElementById("voice-lang")?.value || "ur-PK";
        utter.rate   = 0.88;
        utter.pitch  = 1.0;
        utter.volume = 1.0;
        isSpeaking   = true;
        const icon   = document.getElementById("mic-icon");
        if (icon && !isListening) icon.textContent = "🔊";
        utter.onend = () => {
            isSpeaking = false;
            const ic = document.getElementById("mic-icon");
            if (ic && !isListening) ic.textContent = "🎤";
        };
        utter.onerror = () => { isSpeaking = false; };
        const doSpeak = () => { window.speechSynthesis.speak(utter); };
        const voices  = window.speechSynthesis.getVoices();
        if (voices.length === 0) {
            window.speechSynthesis.addEventListener("voiceschanged", doSpeak, { once: true });
        } else { doSpeak(); }
    }, 200);
}


function getLangTexts(lang) {
    const map = {
        'ur-PK': {
            greeting:       'السلام علیکم! میں SmartZameen AI ہوں  -  آپ کا زرعی معاون۔ مٹی کے نمبر بتائیں یا کوئی بھی سوال پوچھیں!',
            greeting_short: 'السلام علیکم! مٹی کے نمبر بتائیں یا کوئی سوال پوچھیں 🌾',
            listening:      'سن رہا ہوں...',
            predicting:     'تمام معلومات مل گئیں  -  اندازہ لگا رہا ہوں...',
            result:         '{crop} آپ کے لیے بہترین فصل ہے  -  {conf} فیصد یقین',
            filled:         '✅ {n} خانے بھر گئے! باقی بھی بتائیں۔',
            all_filled:     'شکریہ! تمام معلومات مل گئیں  -  اب فصل کا اندازہ لگاتا ہوں...',
            not_understood: '⚠️ سمجھ نہیں آیا۔ مثال: "پنجاب، ربیع، 80 40 30 6.8" یا کوئی سوال پوچھیں',
            hint_speak:     'بولیں: صوبہ، موسم، نائٹروجن، فاسفورس... یا کوئی سوال',
            hint_ui:        'مثال: "گندم کو کتنا پانی چاہیے؟" یا "پنجاب، ربیع، 80 40 30"',
        },
        'pa-PK': {
            greeting:       'ستِ سری اکال! میں SmartZameen AI ہاں  -  مٹی دے نمبر دسو یا سوال پچھو!',
            greeting_short: 'ستِ سری اکال! کوئی وی سوال پچھو 🌾',
            listening:      'سن رہا ہاں...',
            predicting:     'ٹھیک اے  -  اندازہ لا رہا ہاں...',
            result:         '{crop} تیرے لئی سب توں ودیا اے  -  {conf} فیصد',
            filled:         '✅ {n} خانے بھر گئے!',
            all_filled:     'ٹھیک اے  -  ہُن اندازہ لاندا ہاں...',
            not_understood: '⚠️ سمجھ نئیں آیا  -  دسو: پنجاب، ربیع، 80 40 30',
            hint_speak:     'دسو: صوبہ، رُت، نمبر یا سوال',
            hint_ui:        'مثال: "گندم لئی کیہڑا کھاد؟" یا "پنجاب، ربیع، 80 40"',
        },
        'sd-PK': {
            greeting:       'مان SmartZameen AI آهيان  -  مٽيءَ جا نمبر ٻڌايو يا سوال ڪيو!',
            greeting_short: 'ڪوبه سوال ڪيو 🌾',
            listening:      'ٻڌي رهيو آهيان...',
            predicting:     'سڀ معلومات مليون  -  اندازو لڳائي رهيو آهيان...',
            result:         '{crop} توهان لاءِ بهترين آهي  -  {conf} سيڪڙو',
            filled:         '✅ {n} خانا ڀرجي ويا!',
            all_filled:     'ٺيڪ آهي  -  هاڻي اندازو لڳائيندس...',
            not_understood: '⚠️ سمجهه نه آيو  -  مثال: سنڌ، ربيع، 80 40 30',
            hint_speak:     'ڳالهايو: صوبو، موسم، نمبر يا سوال',
            hint_ui:        'مثال: "ڪڻڪ لاءِ ڪيترو پاڻي؟" يا "سنڌ، ربيع، 80 40"',
        },
        'ps-AF': {
            greeting:       'زه SmartZameen AI یم  -  د خاورې شمیرې راکړئ یا پوښتنه وکړئ!',
            greeting_short: 'کومه پوښتنه وکړئ 🌾',
            listening:      'اوریدل کوم...',
            predicting:     'ښه  -  اټکل کوم...',
            result:         '{crop} ستاسو لپاره غوره ده  -  {conf} سلنه',
            filled:         '✅ {n} بکسونه ډک شول!',
            all_filled:     'ښه  -  اوس اټکل کوم...',
            not_understood: '⚠️ پوه نه شوم  -  مثال: پنجاب، ربیع، 80 40 30',
            hint_speak:     'ووایئ: صوبه، فصل، شمیرې یا پوښتنه',
            hint_ui:        'مثال: "غنم لپاره اوبه؟" یا "پنجاب، ربیع، 80 40"',
        },
        'en-US': {
            greeting:       'Welcome! I am SmartZameen AI  -  your farming assistant. Tell me soil numbers or ask any question!',
            greeting_short: 'Hello! Ask me anything about farming 🌾',
            listening:      'Listening...',
            predicting:     'Got all data  -  predicting now...',
            result:         '{crop} is best for you  -  {conf}% confidence',
            filled:         '✅ {n} fields filled! Tell me more.',
            all_filled:     'All info received  -  predicting your best crop...',
            not_understood: '⚠️ Could not understand. Try: Punjab, Rabi, 80 40 30 or ask a question',
            hint_speak:     'Say: province, season, numbers or any farming question',
            hint_ui:        'Example: "How much water for wheat?" or "Punjab, Rabi, 80 40 30"',
        },
    };
    return map[lang] || map['ur-PK'];
}


function updateMicUI(listening) {
    const btn  = document.getElementById('mic-btn');
    const icon = document.getElementById('mic-icon');
    const txt  = document.getElementById('mic-txt');
    if (!btn) return;
    if (listening) {
        btn.classList.add('listening');
        if (icon) icon.textContent = '⏹';
        if (txt)  txt.textContent  = 'روکیں';
    } else {
        btn.classList.remove('listening');
        if (icon) icon.textContent = '🎤';
        if (txt)  txt.textContent  = 'بولیں';
    }
}

function showVoiceStatus(show) {
    const el = document.getElementById('voice-status');
    if (el) el.style.display = show ? 'flex' : 'none';
}

function highlightField(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.style.borderColor = '#1e6b2e'; el.style.backgroundColor = '#eaf3de';
    setTimeout(() => { el.style.borderColor = ''; el.style.backgroundColor = ''; }, 2500);
}

function showVoiceMsg(msg, type) {
    const box = getOrCreateMsgBox();
    const s = { success:['#eaf3de','#27500a'], error:['#fff3cd','#78450a'], info:['#e6f1fb','#185fa5'] }[type] || ['#e6f1fb','#185fa5'];
    box.style.background = s[0]; box.style.color = s[1];
    box.textContent = msg; box.style.display = 'block';
}

function hideVoiceMsg() {
    const box = document.getElementById('voice-msg-box');
    if (box) box.style.display = 'none';
}

function getOrCreateMsgBox() {
    let box = document.getElementById('voice-msg-box');
    if (!box) {
        box = document.createElement('div');
        box.id = 'voice-msg-box';
        box.style.cssText = 'margin:6px 0;padding:8px 12px;border-radius:10px;font-size:12px;text-align:center;font-weight:600;display:none';
        const sec = document.getElementById('voice-section-full') || document.querySelector('.voice-section');
        if (sec) sec.appendChild(box);
    }
    return box;
}

document.addEventListener('DOMContentLoaded', function () {
    const langSel = document.getElementById('voice-lang');
    if (langSel) {
        langSel.addEventListener('change', function () {
            const texts = getLangTexts(this.value);
            const hintEl = document.getElementById('voice-hint-txt');
            if (hintEl) hintEl.textContent = texts.hint_ui;
            const statEl = document.getElementById('voice-status-txt');
            if (statEl) statEl.textContent = texts.listening;
        });
    }
    const lang = langSel?.value || 'ur-PK';
    const hintEl = document.getElementById('voice-hint-txt');
    if (hintEl) hintEl.textContent = getLangTexts(lang).hint_ui;
});