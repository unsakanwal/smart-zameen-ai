/* chat.js — Crop Advisor full chat (text · image · camera · file · voice) powered by OpenAI. */
(function () {
  const API = window.SZ_API || '';
  const log = document.getElementById('chat-log');
  if (!log) return; // not on the chat page

  const input   = document.getElementById('chat-input');
  const sendBtn = document.getElementById('chat-send');
  const micBtn  = document.getElementById('chat-mic');
  const attachBtn = document.getElementById('chat-attach');
  const camBtn  = document.getElementById('chat-camera-btn');
  const fileInput = document.getElementById('chat-file-input');
  const preview = document.getElementById('chat-attach-preview');
  const ttsBtn  = document.getElementById('chat-tts');

  let history = [];          // [{role, content(str)}] text-only context
  let pendingImage = null;   // data URI (vision)
  let pendingFile = null;    // { name, text }
  let ttsOn = false;
  let listening = false, recog = null;

  const LANG = (localStorage.getItem('sz_lang') || 'en');
  const SPEECH = { en: 'en-US', ur: 'ur-PK', pa: 'pa-PK', sd: 'sd-PK', ps: 'ps-AF' };

  const esc = s => (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  // ---------- rendering ----------
  function bubble(role, opts) {
    const wrap = document.createElement('div');
    wrap.className = 'chat-msg ' + role;
    let inner = '';
    if (opts.image) inner += `<img class="chat-img" src="${opts.image}" alt="attachment">`;
    if (opts.file)  inner += `<div class="chat-file">📎 ${esc(opts.file)}</div>`;
    if (opts.text)  inner += `<div class="chat-text">${esc(opts.text).replace(/\n/g, '<br>')}</div>`;
    wrap.innerHTML = `<div class="chat-bubble">${inner}</div>`;
    log.appendChild(wrap);
    log.scrollTop = log.scrollHeight;
    return wrap;
  }
  function typing() {
    const w = document.createElement('div');
    w.className = 'chat-msg assistant'; w.id = 'chat-typing';
    w.innerHTML = '<div class="chat-bubble"><div class="chat-dots"><span></span><span></span><span></span></div></div>';
    log.appendChild(w); log.scrollTop = log.scrollHeight;
  }
  const untyping = () => { const t = document.getElementById('chat-typing'); if (t) t.remove(); };

  // ---------- attachments ----------
  function clearAttach() { pendingImage = null; pendingFile = null; preview.innerHTML = ''; preview.style.display = 'none'; }
  function showAttach(html) { preview.innerHTML = html + '<button class="chat-attach-x" title="Remove">✕</button>'; preview.style.display = 'flex'; preview.querySelector('.chat-attach-x').onclick = clearAttach; }

  function downscale(file) {
    return new Promise((resolve, reject) => {
      const img = new Image(); const url = URL.createObjectURL(file);
      img.onload = () => {
        const max = 1024; let { width, height } = img;
        if (width > max || height > max) { const s = max / Math.max(width, height); width = Math.round(width * s); height = Math.round(height * s); }
        const cv = document.createElement('canvas'); cv.width = width; cv.height = height;
        cv.getContext('2d').drawImage(img, 0, 0, width, height);
        URL.revokeObjectURL(url); resolve(cv.toDataURL('image/jpeg', 0.85));
      };
      img.onerror = reject; img.src = url;
    });
  }

  async function handleFile(file) {
    if (!file) return;
    if (file.type.startsWith('image/')) {
      pendingImage = await downscale(file); pendingFile = null;
      showAttach(`<img src="${pendingImage}" class="chat-attach-thumb" alt=""><span>${esc(file.name)}</span>`);
    } else {
      // text-like files: read as text and pass as context
      const readable = /^(text\/|application\/(json|csv|xml|x-yaml))/.test(file.type) || /\.(txt|csv|md|json|log|xml|yml|yaml)$/i.test(file.name);
      if (readable) {
        const text = await file.text();
        pendingFile = { name: file.name, text: text.slice(0, 8000) }; pendingImage = null;
        showAttach(`<div class="chat-attach-file">📄 ${esc(file.name)}</div>`);
      } else {
        pendingFile = { name: file.name, text: '' }; pendingImage = null;
        showAttach(`<div class="chat-attach-file">📄 ${esc(file.name)} <em>(name only — non-text file)</em></div>`);
      }
    }
  }

  attachBtn.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', e => { handleFile(e.target.files[0]); fileInput.value = ''; });

  // ---------- camera ----------
  let stream = null;
  const modal = document.getElementById('cam-modal');
  const video = document.getElementById('cam-video');
  async function openCamera() {
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
      video.srcObject = stream; modal.classList.add('open');
    } catch (e) { alert('Camera not available: ' + e.message); }
  }
  function closeCamera() { if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null; } modal.classList.remove('open'); }
  async function capture() {
    const cv = document.createElement('canvas');
    const max = 1024; let w = video.videoWidth, h = video.videoHeight;
    if (w > max || h > max) { const s = max / Math.max(w, h); w = Math.round(w * s); h = Math.round(h * s); }
    cv.width = w; cv.height = h; cv.getContext('2d').drawImage(video, 0, 0, w, h);
    pendingImage = cv.toDataURL('image/jpeg', 0.85); pendingFile = null;
    showAttach(`<img src="${pendingImage}" class="chat-attach-thumb" alt=""><span>Camera photo</span>`);
    closeCamera();
  }
  if (camBtn) camBtn.addEventListener('click', openCamera);
  document.getElementById('cam-capture')?.addEventListener('click', capture);
  document.getElementById('cam-close')?.addEventListener('click', closeCamera);

  // ---------- voice input (speech-to-text) ----------
  function setupRecog() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { alert('Voice input needs Chrome/Edge.'); return null; }
    const r = new SR(); r.lang = SPEECH[LANG] || 'en-US'; r.interimResults = true; r.continuous = false;
    r.onstart = () => { listening = true; micBtn.classList.add('on'); };
    r.onend = () => { listening = false; micBtn.classList.remove('on'); };
    r.onerror = () => { listening = false; micBtn.classList.remove('on'); };
    r.onresult = (e) => {
      let final = '', interim = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript;
        if (e.results[i].isFinal) final += t; else interim += t;
      }
      input.value = (final || interim);
      autosize();
      if (final.trim()) { setTimeout(() => sendChat(), 300); }
    };
    return r;
  }
  if (micBtn) micBtn.addEventListener('click', () => {
    if (listening) { recog && recog.stop(); return; }
    recog = setupRecog(); if (recog) try { recog.start(); } catch (e) {}
  });

  // ---------- voice output (TTS) ----------
  if (ttsBtn) ttsBtn.addEventListener('click', () => {
    ttsOn = !ttsOn; ttsBtn.classList.toggle('on', ttsOn);
    ttsBtn.querySelector('span').textContent = ttsOn ? 'Voice: On' : 'Voice: Off';
    if (!ttsOn) window.speechSynthesis?.cancel();
  });
  function speak(text) {
    if (!ttsOn || !window.speechSynthesis || !text) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = SPEECH[LANG] || 'en-US'; u.rate = 0.95;
    window.speechSynthesis.speak(u);
  }

  // ---------- send ----------
  async function sendChat() {
    const text = input.value.trim();
    if (!text && !pendingImage && !pendingFile) return;

    bubble('user', { text, image: pendingImage, file: pendingFile ? pendingFile.name : null });
    history.push({ role: 'user', content: text + (pendingImage ? ' [sent an image]' : '') + (pendingFile ? ` [file: ${pendingFile.name}]` : '') });

    const payload = {
      message: text, image: pendingImage,
      file_text: pendingFile ? pendingFile.text : '', file_name: pendingFile ? pendingFile.name : '',
      history: history.slice(0, -1), lang: LANG,
    };
    input.value = ''; autosize(); const img = pendingImage; clearAttach();
    sendBtn.disabled = true; typing();

    try {
      const res = await fetch(API + '/api/chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
      });
      const d = await res.json();
      untyping();
      if (res.ok && d.ok) {
        bubble('assistant', { text: d.reply });
        history.push({ role: 'assistant', content: d.reply });
        speak(d.reply);
      } else {
        bubble('assistant', { text: '⚠️ ' + (d.error || 'Something went wrong.') });
      }
    } catch (e) {
      untyping();
      bubble('assistant', { text: "⚠️ Can't reach the backend. Make sure the app is opened via Flask (http://localhost) and python app.py is running." });
    } finally {
      sendBtn.disabled = false;
    }
  }
  sendBtn.addEventListener('click', sendChat);
  input.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); } });

  function autosize() { input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight, 140) + 'px'; }
  input.addEventListener('input', autosize);

  // greeting
  bubble('assistant', { text: 'Assalam-o-Alaikum! 🌾 I\'m your Crop Advisor. Ask me anything about crops, soil, weather or pests — type, talk (🎤), or send a photo (📷) of your crop or soil.' });
})();
