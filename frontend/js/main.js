if (typeof API_URL === 'undefined') {
    var API_URL = (window.location.protocol === 'file:' || (window.location.port !== '' && window.location.port !== '80')) 
      ? 'http://localhost' 
      : window.location.origin;
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
    const _origDisplay = window.displayResult;
    window.displayResult = function(result) {
        if (_origDisplay) _origDisplay(result);
    
        // Speak result button add karo
        const resultBox = document.getElementById('result-box');
        if (resultBox && !document.getElementById('speak-btn')) {
            const btn = document.createElement('button');
            btn.id        = 'speak-btn';
            btn.className = 'speak-result-btn';
            btn.innerHTML = '🔊 <span class="urdu-font">نتیجہ سنیں</span>';
            btn.onclick   = function() {
                speakResult(
                    result.crop,
                    result.confidence,
                    result.urdu
                );
            };
            resultBox.querySelector('.result-card').appendChild(btn);
        }
    };
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
            setEl('weather-temp',  data.temperature + '°C');
            setEl('weather-humid', data.humidity    + '%');
            setEl('weather-rain',  data.rainfall    + 'mm');
            setEl('weather-wind',  data.wind_speed  + 'km/h');
            setEl('weather-desc',  data.description || '');
            setEl('weather-city',  data.urdu_city   || city);
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
        const email = localStorage.getItem('sz_email') || 'User';
        const name = email.split('@')[0];
        if (userNameDisplay) userNameDisplay.textContent = name.charAt(0).toUpperCase() + name.slice(1);
    } else {
        if (authButtons) authButtons.style.display = 'flex';
        if (userPill) userPill.style.display = 'none';
    }
}

// Global logout function
function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('sz_email');
    localStorage.removeItem('sz_loggedIn');
    window.location.href = 'login.html';
}

// =============================================
// PAGE LOAD HOTE HI CHALAO
// =============================================
document.addEventListener('DOMContentLoaded', function () {

    // Current page detect karo
    const page = window.location.pathname;

    // Run auth check to update navbar buttons
    checkAuth();

    // Dashboard page pe ho to weather load karo
    if (page.includes('dashboard')) {
        loadWeather('multan');
        loadRecommendations();

        // Shahar change karne ka button
        const citySelect = document.getElementById('city-select');
        if (citySelect) {
            citySelect.addEventListener('change', function () {
                loadWeather(this.value);
            });
        }
    }

    // Predict page pe ho to form ready karo
    if (page.includes('predict')) {
        const form = document.getElementById('predict-form');
        if (form) {
            // Enter dabane se bhi predict ho
            form.addEventListener('keypress', function (e) {
                if (e.key === 'Enter') predictCrop();
            });
        }
    }

    // Saved language apply karo
    const savedLang = localStorage.getItem('sa_lang') || 'ur';
    const langBtn   = document.querySelector(`.lb[onclick="setLang('${savedLang}',this)"]`);
    if (langBtn && typeof setLang === 'function') {
        setLang(savedLang, langBtn);
    }
});