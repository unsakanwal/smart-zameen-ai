// The backend base is normally resolved once in js/config.js (loaded first) and
// exposed as window.API_URL / window.SZ_API. These blocks are a safety net for
// the rare case config.js didn't load — they only run if those are still unset.
if (typeof API_URL === 'undefined') {
    var API_URL = (window.location.protocol === 'file:' || (window.location.port !== '' && window.location.port !== '80'))
      ? 'http://localhost'
      : window.location.origin;
}

if (typeof window.SZ_API === 'undefined') {
    window.SZ_API = (function () {
        if (window.SZ_BACKEND) return window.SZ_BACKEND;
        var dev = ['5500', '5501', '5502', '3000', '4200', '8080'];
        if (location.protocol === 'file:') return 'http://localhost:5000';
        if (dev.indexOf(location.port) !== -1) return 'http://' + location.hostname + ':5000';
        return ''; // same-origin (served by Flask)
    })();
}


// =============
// PREDICT PAGE 
// =============
async function predictCrop() {

    // Step 1
    const nitrogen    = document.getElementById('i-n')?.value;
    const phosphorus  = document.getElementById('i-p')?.value;
    const potassium   = document.getElementById('i-k')?.value;
    const ph          = document.getElementById('i-ph')?.value;
    const temperature = document.getElementById('i-tmp')?.value;
    const rainfall    = document.getElementById('i-rain')?.value;
    const region      = document.getElementById('i-reg')?.value || 'punjab';
    const season      = document.getElementById('i-sea')?.value || 'rabi';

    // Step 2: Validation 
    if (!nitrogen || !phosphorus || !potassium || !ph || !temperature || !rainfall) {
        showError('تمام خانے بھریں  -  کوئی خالی نہ رہے!');
        return;
    }

    // Step 3: 
    showLoading(true);
    hideResult();
    hideError();

    try {
        // Step 4: 
        const response = await fetch(`${API_URL}/api/predict-crop`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                nitrogen:    parseFloat(nitrogen),
                phosphorus:  parseFloat(phosphorus),
                potassium:   parseFloat(potassium),
                ph:          parseFloat(ph),
                temperature: parseFloat(temperature),
                rainfall:    parseFloat(rainfall),
                region:      region,
                season:      season
            })
        });

        // Step 5: 
        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        const result = await response.json();

        // Step 6: 
        showLoading(false);

        if (result.success) {
            // Step 7: Result dikhao
            displayResult(result);
        } else {
            showError(result.error || 'Kuch masla hua  -  dobara koshish karein');
        }

    } catch (error) {
        showLoading(false);

        // Agar Flask nahi chal raha
        if (error.message.includes('Failed to fetch') ||
            error.message.includes('NetworkError')) {
            showError('⚠️ Backend server nahi chal raha! Terminal mein chalao: python app.py');
        } else {
            showError('Error: ' + error.message);
        }
    }
}


// =============================================
// FARMER FRIENDLY PREDICT
// =============================================
async function predictCropFarmer() {
    // Step 1: Simple questions se data lo
    const prevCrop   = document.getElementById('farmer-nitrogen')?.value || 'wheat';
    const soilType   = document.getElementById('farmer-ph')?.value || 'normal';
    const seasonTemp = document.getElementById('farmer-temp')?.value || 'moderate';
    const rainLevel  = document.getElementById('farmer-rainfall')?.value || 'theek';
    const fertilizer = document.getElementById('farmer-potassium')?.value || 'zyada';
    const region     = document.getElementById('farmer-region')?.value || 'punjab';

    // Step 2: Technical values map karo
    let nitrogen = 45;
    let phosphorus = 22;
    let potassium = 30;

    if (prevCrop === 'legume') { nitrogen = 80; phosphorus = 30; potassium = 40; }
    else if (prevCrop === 'fallow') { nitrogen = 60; phosphorus = 25; potassium = 35; }
    else if (prevCrop === 'wheat') { nitrogen = 45; phosphorus = 22; potassium = 30; }
    else if (prevCrop === 'cotton') { nitrogen = 40; phosphorus = 20; potassium = 28; }
    else if (prevCrop === 'rice') { nitrogen = 35; phosphorus = 18; potassium = 25; }
    else if (prevCrop === 'maize') { nitrogen = 30; phosphorus = 15; potassium = 20; }

    // Fertilizer ke mutabiq values change karo
    if (fertilizer === 'zyada') {
        nitrogen += 10;
        phosphorus = Math.round(phosphorus * 1.3);
        potassium = Math.round(potassium * 1.3);
    } else if (fertilizer === 'kam') {
        nitrogen = Math.max(10, nitrogen - 10);
        phosphorus = Math.round(phosphorus * 0.7);
        potassium = Math.round(potassium * 0.7);
    }

    // Soil pH mapping
    let ph = 6.8;
    if (soilType === 'normal') ph = 6.8;
    else if (soilType === 'namkeen') ph = 8.2;
    else if (soilType === 'khatti') ph = 5.2;

    // Temperature & Season mapping
    let temperature = 24;
    let season = 'rabi';
    if (seasonTemp === 'moderate') {
        temperature = 24;
        season = 'rabi';
    } else if (seasonTemp === 'cold') {
        temperature = 15;
        season = 'rabi';
    } else if (seasonTemp === 'hot') {
        temperature = 36;
        season = 'kharif';
    }

    // Rainfall mapping
    let rainfall = 150;
    if (rainLevel === 'theek') rainfall = 150;
    else if (rainLevel === 'kam') rainfall = 50;
    else if (rainLevel === 'zyada') rainfall = 280;

    // Step 3: Loading dikhao
    showLoading(true);
    hideResult();
    hideError();

    try {
        // Step 4: Flask API ko request bhejo
        const response = await fetch(`${API_URL}/api/predict-crop`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                nitrogen:    parseFloat(nitrogen),
                phosphorus:  parseFloat(phosphorus),
                potassium:   parseFloat(potassium),
                ph:          parseFloat(ph),
                temperature: parseFloat(temperature),
                rainfall:    parseFloat(rainfall),
                region:      region,
                season:      season
            })
        });

        // Step 5: Response check karo
        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        const result = await response.json();

        // Step 6: Loading band karo
        showLoading(false);

        if (result.success) {
            // Step 7: Result dikhao
            displayResult(result);
        } else {
            showError(result.error || 'Kuch masla hua  -  dobara koshish karein');
        }

    } catch (error) {
        showLoading(false);

        if (error.message.includes('Failed to fetch') ||
            error.message.includes('NetworkError')) {
            showError('⚠️ Backend server nahi chal raha! Terminal mein chalao: python app.py');
        } else {
            showError('Error: ' + error.message);
        }
    }
}


// =============================================
// RESULT DIKHAO
// =============================================
function displayResult(result) {
    // Crop icons map
    const cropIcons = {
        'wheat':      '🌾',
        'rice':       '🌿',
        'maize':      '🌽',
        'cotton':     '🌸',
        'mustard':    '🌻',
        'chickpea':   '🫘',
        'sugarcane':  '🎋',
        'mango':      '🥭',
        'tomato':     '🍅',
        'onion':      '🧅',
        'potato':     '🥔',
        'kino':       '🍊',
    };

    const icon = cropIcons[result.crop] || '🌱';

    // Result elements update karo
    setEl('rc-ic',    icon);
    setEl('rc-crop',  result.urdu || result.crop);
    setEl('rc-ur',    result.season + '  -  ' + (result.best_time || ''));
    setEl('rc-conf',  result.confidence + '٪ درست اندازہ');
    setEl('rc-yield', result.yield     || '--');
    setEl('rc-time',  result.best_time || '--');
    setEl('rc-water', result.water     || '--');

    // Top 3 faslein dikhao (agar hain)
    if (result.top3 && result.top3.length > 0) {
        showTop3(result.top3, cropIcons);
    }

    // Result box dikhao
    const resultBox = document.getElementById('result-box');
    if (resultBox) {
        resultBox.style.display = 'block';
        // Smooth scroll karo result tak
        resultBox.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}


// =============================================
// TOP 3 FASLEIN
// =============================================
function showTop3(top3, cropIcons) {
    const container = document.getElementById('top3-box');
    if (!container) return;

    let html = '<div style="margin-top:12px"><div style="font-size:12px;color:#b0dca0;margin-bottom:8px;font-family:serif">دیگر ممکنہ فصلیں:</div>';

    top3.forEach((item, index) => {
        if (index === 0) return; // Pehli already dikhay di
        const ic = cropIcons[item.crop] || '🌱';
        html += `
            <div style="display:flex;align-items:center;gap:8px;
                        background:rgba(255,255,255,0.1);
                        border-radius:8px;padding:7px 10px;margin-bottom:6px">
                <span style="font-size:18px">${ic}</span>
                <span style="color:#fff;font-size:12px;flex:1">${item.urdu || item.crop}</span>
                <span style="color:#b0dca0;font-size:12px">${item.confidence}٪</span>
            </div>`;
    });

    html += '</div>';
    container.innerHTML = html;
    container.style.display = 'block';
}


// =============================================
// DASHBOARD  -  WEATHER DATA LOAD KARO
// =============================================
async function loadWeather(city = 'multan') {
    try {
        const response = await fetch(`${API_URL}/api/weather?city=${city}`);
        const data     = await response.json();

        if (data.success) {
            setEl('weather-temp',       data.temperature + '°C');
            setEl('weather-humid',      data.humidity    + '%');
            setEl('weather-wind-speed', data.wind_speed  + ' km/h');
            setEl('weather-desc',       data.description || '');
            // keep the card title in sync with the chosen city
            const cityLabel = data.urdu_city || (city.charAt(0).toUpperCase() + city.slice(1));
            setEl('today-weather', "Today's Weather – " + cityLabel);
        }
    } catch (error) {
        console.log('Weather load nahi hua:', error.message);
    }
}


// =============================================
// DASHBOARD  -  RECOMMENDATIONS LOAD KARO
// =============================================
async function loadRecommendations() {
    try {
        const response = await fetch(`${API_URL}/api/crops`);
        const data     = await response.json();

        if (data.success && data.crops) {
            console.log('Crops loaded:', data.crops.length);
        }
    } catch (error) {
        console.log('Recommendations load nahi hui:', error.message);
    }
}


// =============================================
// HELPER FUNCTIONS
// =============================================

// Element ka content set karo
function setEl(id, value) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = value;
}

// Loading spinner dikhao/chhupao
function showLoading(show) {
    const lb = document.getElementById('loading-box');
    if (lb) lb.style.display = show ? 'block' : 'none';
}

// Result chhupao
function hideResult() {
    const rb = document.getElementById('result-box');
    if (rb) rb.style.display = 'none';
}

// Error dikhao
function showError(msg) {
    let errBox = document.getElementById('error-box');

    // Agar error box nahi hai to banao
    if (!errBox) {
        errBox = document.createElement('div');
        errBox.id = 'error-box';
        errBox.style.cssText = `
            background: #fff3cd;
            border: 1px solid #f59e0b;
            border-radius: 10px;
            padding: 12px 16px;
            margin: 12px;
            font-size: 13px;
            color: #78450a;
            display: flex;
            align-items: center;
            gap: 8px;
        `;
        const card = document.querySelector('.predict-card') ||
                     document.querySelector('.pf-card');
        if (card) card.after(errBox);
    }

    errBox.innerHTML = '⚠️ ' + msg;
    errBox.style.display = 'flex';
}

// Error chhupao
function hideError() {
    const errBox = document.getElementById('error-box');
    if (errBox) errBox.style.display = 'none';
}


// Check auth state and update navbar dynamically
function checkAuth() {
    const isLoggedIn = localStorage.getItem('sz_loggedIn') === 'true';
    const authButtons = document.getElementById('auth-buttons');
    const userPill = document.getElementById('user-pill');
    const userNameDisplay = document.getElementById('user-name-display');

    if (isLoggedIn) {
        if (authButtons) authButtons.style.display = 'none';
        if (userPill) userPill.style.display = 'flex';
        const stored = localStorage.getItem('sz_name');
        const email = localStorage.getItem('sz_email') || 'User';
        const name = stored && stored.trim() ? stored.trim() : email.split('@')[0];
        if (userNameDisplay) userNameDisplay.textContent = name.charAt(0).toUpperCase() + name.slice(1);
    } else {
        if (authButtons) authButtons.style.display = 'flex';
        if (userPill) userPill.style.display = 'none';
    }

    // Dashboard nav link is only shown when logged in (hidden after logout).
    // Home + About Us stay visible for everyone.
    document.querySelectorAll('.nav-auth').forEach(el => { el.style.display = isLoggedIn ? '' : 'none'; });
}

// Global logout function
function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('sz_email');
    localStorage.removeItem('sz_loggedIn');
    localStorage.removeItem('sz_name');
    localStorage.removeItem('sz_region');
    window.location.href = 'index.html';
}

// =============================================
// PAGE LOAD HOTE HI CHALAO
// =============================================
document.addEventListener('DOMContentLoaded', function () {

    // Current page detect karo
    const page = window.location.pathname;

    // Run auth check to update navbar buttons
    checkAuth();

    // Mobile hamburger: toggles the nav dropdown (portfolio pages) OR the
    // off-canvas dashboard sidebar drawer (app pages). Navbar stays sticky.
    (function () {
        const nav = document.querySelector('.navbar');
        if (!nav || nav.querySelector('.nav-toggle')) return;

        const btn = document.createElement('button');
        btn.className = 'nav-toggle';
        btn.setAttribute('aria-label', 'Toggle menu');
        btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 6h18M3 12h18M3 18h18"/></svg>';
        nav.appendChild(btn);

        // dim overlay behind the drawer
        let overlay = document.querySelector('.sz-overlay');
        if (!overlay) { overlay = document.createElement('div'); overlay.className = 'sz-overlay'; document.body.appendChild(overlay); }

        const close = () => document.body.classList.remove('sz-menu-open');
        btn.addEventListener('click', e => { e.stopPropagation(); document.body.classList.toggle('sz-menu-open'); });
        overlay.addEventListener('click', close);
        document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });
        // close after tapping any nav/sidebar link (language buttons keep it open)
        document.querySelectorAll('.nav-center a, .app-sidebar a, .app-sidebar-logout').forEach(el => el.addEventListener('click', close));
    })();

    // Dashboard page pe ho to weather load karo
    if (page.includes('dashboard')) {
        const citySelect = document.getElementById('city-select');
        loadWeather(citySelect ? citySelect.value : 'lahore');
        loadRecommendations();

        // Shahar change karne ka button
        if (citySelect) {
            citySelect.addEventListener('change', function () {
                loadWeather(this.value);
            });
        }
    }

    // Predict page pe ho to form ready karo
    if (page.includes('predict') || page.includes('crop-advisor')) {
        const form = document.getElementById('predict-form');
        if (form) {
            // Enter dabane se bhi predict ho
            form.addEventListener('keypress', function (e) {
                if (e.key === 'Enter') predictCrop();
            });
        }
    }

    // NOTE: the saved language is applied centrally in js/lang.js on
    // DOMContentLoaded (reads 'sz_lang', default 'en', flips RTL, persists).
    // Do NOT re-apply it here — a second pass with a different key/default
    // only causes a flicker and can fight lang.js.
});