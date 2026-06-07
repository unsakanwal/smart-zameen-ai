if (typeof API_URL === 'undefined') {
  var API_URL = (window.location.protocol === 'file:' || (window.location.port !== '' && window.location.port !== '80')) 
    ? 'http://localhost' 
    : window.location.origin;
}

// ── State ──
let cameraStream      = null;
let capturedImageData = null;
let cameraOpen        = false;

// ── DOM refs (lazy) ──
const $  = id => document.getElementById(id);

// ══════════════════════════════════════════════
//  CAMERA PANEL TOGGLE
// ══════════════════════════════════════════════
function toggleCameraPanel() {
  const panel = $('camera-panel');
  if (!panel) return;

  cameraOpen = !cameraOpen;
  panel.style.display = cameraOpen ? 'block' : 'none';

  if (!cameraOpen) {
    stopCamera();
  }

  // Toggle button style
  const btn = $('camera-toggle-btn');
  if (btn) {
    btn.classList.toggle('active', cameraOpen);
    btn.querySelector('.cam-btn-txt').textContent =
      cameraOpen ? 'کیمرہ بند کریں' : '📷 مٹی کی تصویر سے تجزیہ';
  }
}

// ══════════════════════════════════════════════
//  OPEN LIVE CAMERA
// ══════════════════════════════════════════════
async function openCamera() {
  const video     = $('soil-video');
  const camBox    = $('camera-live-box');
  const photoBox  = $('photo-preview-box');

  if (!video || !camBox) return;

  try {
    // Pehle wali stream band karo
    stopCamera();

    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: false
    });

    video.srcObject = cameraStream;
    await video.play();

    camBox.style.display   = 'block';
    if (photoBox) photoBox.style.display = 'none';

    // Capture button dikhao
    showCamControls('live');

  } catch (err) {
    if (err.name === 'NotAllowedError') {
      showCamMsg('❌ کیمرہ کی اجازت نہیں ملی۔ براہ کرم browser settings میں اجازت دیں۔');
    } else {
      showCamMsg('❌ کیمرہ نہیں کھل سکا: ' + err.message);
    }
  }
}

// ══════════════════════════════════════════════
//  CAPTURE PHOTO FROM CAMERA
// ══════════════════════════════════════════════
function capturePhoto() {
  const video   = $('soil-video');
  const canvas  = $('soil-canvas');
  const camBox  = $('camera-live-box');
  const photoBox = $('photo-preview-box');
  const preview = $('soil-preview');

  if (!video || !canvas) return;

  // Canvas pe draw karo
  canvas.width  = video.videoWidth  || 640;
  canvas.height = video.videoHeight || 480;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  // Base64 image
  capturedImageData = canvas.toDataURL('image/jpeg', 0.85);

  // Preview dikhao
  if (preview) preview.src = capturedImageData;
  if (camBox)  camBox.style.display   = 'none';
  if (photoBox) photoBox.style.display = 'block';

  stopCamera();
  showCamControls('captured');
}

// ══════════════════════════════════════════════
//  UPLOAD FROM GALLERY
// ══════════════════════════════════════════════
function openGallery() {
  const input = $('gallery-input');
  if (input) input.click();
}

function handleGalleryUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  if (!file.type.startsWith('image/')) {
    showCamMsg('❌ صرف تصویر فائل قبول کی جائے گی۔');
    return;
  }

  const reader = new FileReader();
  reader.onload = (e) => {
    capturedImageData = e.target.result;

    const preview  = $('soil-preview');
    const camBox   = $('camera-live-box');
    const photoBox = $('photo-preview-box');

    if (preview)  preview.src = capturedImageData;
    if (camBox)   camBox.style.display   = 'none';
    if (photoBox) photoBox.style.display = 'block';

    stopCamera();
    showCamControls('captured');
    showCamMsg('✅ تصویر اپلوڈ ہوگئی! اب "تجزیہ شروع کریں" دبائیں۔');
  };
  reader.readAsDataURL(file);
}

// ══════════════════════════════════════════════
//  RETAKE PHOTO
// ══════════════════════════════════════════════
function retakePhoto() {
  capturedImageData = null;
  const photoBox = $('photo-preview-box');
  if (photoBox) photoBox.style.display = 'none';
  showCamControls('initial');
  openCamera();
}

// ══════════════════════════════════════════════
//  STOP CAMERA STREAM
// ══════════════════════════════════════════════
function stopCamera() {
  if (cameraStream) {
    cameraStream.getTracks().forEach(t => t.stop());
    cameraStream = null;
  }
  const video = $('soil-video');
  if (video) video.srcObject = null;
}

// ══════════════════════════════════════════════
//  SHOW/HIDE CONTROLS
// ══════════════════════════════════════════════
function showCamControls(state) {
  // initial = camera + gallery buttons
  // live    = capture button
  // captured = analyze + retake buttons

  const initialBtns  = $('cam-initial-btns');
  const liveBtns     = $('cam-live-btns');
  const capturedBtns = $('cam-captured-btns');

  if (initialBtns)  initialBtns.style.display  = state === 'initial'  ? 'flex' : 'none';
  if (liveBtns)     liveBtns.style.display     = state === 'live'     ? 'flex' : 'none';
  if (capturedBtns) capturedBtns.style.display = state === 'captured' ? 'flex' : 'none';
}

// ══════════════════════════════════════════════
//  ANALYZE SOIL IMAGE → local soil-classifier (/api/analyze-soil-image)
// ══════════════════════════════════════════════
async function analyzeSoilImage() {
  if (!capturedImageData) {
    showCamMsg('❌ پہلے تصویر لیں یا اپلوڈ کریں۔');
    return;
  }

  // Region & season from form
  const region = ($('i-reg') ? $('i-reg').value : 'punjab');
  const season = ($('i-sea') ? $('i-sea').value : 'rabi');

  // Show loading state
  showSoilLoading(true);
  hideSoilResult();
  showCamMsg('');

  try {
    const response = await fetch(`${API_URL}/api/analyze-soil-image`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image:  capturedImageData,
        region: region,
        season: season
      })
    });

    const contentType = response.headers.get('content-type');
    if (!response.ok) {
      let errMsg = 'Server error';
      if (contentType && contentType.includes('application/json')) {
        const errData = await response.json();
        errMsg = errData.error || errData.message || errMsg;
      } else {
        errMsg = `Server error (Status ${response.status})`;
      }
      throw new Error(errMsg);
    }

    if (!contentType || !contentType.includes('application/json')) {
      throw new Error('Server did not return a valid JSON response');
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || 'Server error');
    }

    // ── Auto-fill form ──
    if (data.auto_fill) {
      autoFillForm(data.auto_fill);
    }

    // ── Show soil analysis result ──
    showSoilResult(data.soil_analysis);

  } catch (err) {
    showCamMsg('❌ ' + (err.message || 'تجزیہ ناکام ہوا'));
  } finally {
    showSoilLoading(false);
  }
}

// ══════════════════════════════════════════════
//  AUTO-FILL FORM WITH ESTIMATED VALUES
// ══════════════════════════════════════════════
function autoFillForm(fill) {
  const map = {
    'i-n':    'nitrogen',
    'i-p':    'phosphorus',
    'i-k':    'potassium',
    'i-ph':   'ph',
    'i-tmp':  'temperature',
    'i-rain': 'rainfall',
  };

  Object.entries(map).forEach(([id, key]) => {
    const el = $(id);
    if (el && fill[key] !== undefined) {
      el.value = fill[key];
      // Flash animation
      el.style.transition = 'background 0.4s';
      el.style.background = '#e8f5e9';
      setTimeout(() => { el.style.background = ''; }, 1200);
    }
  });

  showCamMsg('✅ فارم خودکار بھر گیا! ضرورت پر تبدیل کریں۔', 'success');
}

// ══════════════════════════════════════════════
//  SHOW SOIL ANALYSIS RESULT CARD
// ══════════════════════════════════════════════
function showSoilResult(soil) {
  const box = $('soil-analysis-result');
  if (!box) return;

  // Save to global variable so language switching re-renders this dynamically
  window.lastSoilData = soil;

  const lang = localStorage.getItem('sz_lang') || 'en';

  const i18n = {
    en: {
      title: "Soil Analysis Complete",
      health_label: "Soil Health",
      crop_label: "Recommended Crop",
      conf_label: "Confidence",
      n_label: "Nitrogen",
      p_label: "Phosphorus",
      k_label: "Potassium",
      ph_label: "pH (Acidity)",
      m_label: "Moisture",
      om_label: "Organic Matter",
      imp_title: "🌱 Improvements Advice:",
      predict_btn: "🤖 Run AI Crop Prediction Now",
      textures: { Fine: "Fine", "Fine-Medium": "Fine-Medium", Coarse: "Coarse", Medium: "Medium" },
      moisture: { High: "High", Moderate: "Moderate", Low: "Low" },
      om: { High: "High", Medium: "Medium", Low: "Low" },
      health: { Good: "Good", Poor: "Poor" }
    },
    ur: {
      title: "مٹی کا تجزیہ مکمل",
      health_label: "مٹی کی صحت",
      crop_label: "تجویز کردہ فصل",
      conf_label: "یقین",
      n_label: "نائٹروجن",
      p_label: "فاسفورس",
      k_label: "پوٹاشیم",
      ph_label: "تیزابیت (pH)",
      m_label: "نمی",
      om_label: "نامیاتی مادہ",
      imp_title: "🌱 بہتری کے مشورے:",
      predict_btn: "🤖 اب AI سے فصل کا تعین کریں",
      textures: { Fine: "باریک", "Fine-Medium": "درمیانی باریک", Coarse: "کھردری", Medium: "درمیانہ" },
      moisture: { High: "زیادہ", Moderate: "مناسب", Low: "کم" },
      om: { High: "زیادہ", Medium: "درمیانہ", Low: "کم" },
      health: { Good: "بہتر", Poor: "کمزور" }
    },
    pa: {
      title: "مٹی دا تجزیہ مکمل",
      health_label: "مٹی دی صحت",
      crop_label: "تجویز کیتی گئی فصل",
      conf_label: "یقین",
      n_label: "نائٹروجن",
      p_label: "فاسفورس",
      k_label: "پوٹاشیم",
      ph_label: "تیزابیت (pH)",
      m_label: "نمی",
      om_label: "نامیاتی مادہ",
      imp_title: "🌱 بہتری دے مشورے:",
      predict_btn: "🤖 ہن AI نال فصل دا پتہ لاؤ",
      textures: { Fine: "باریک", "Fine-Medium": "درمیانی باریک", Coarse: "کھردری", Medium: "درمیانہ" },
      moisture: { High: "زیادہ", Moderate: "مناسب", Low: "گھٹ" },
      om: { High: "زیادہ", Medium: "درمیانہ", Low: "گھٹ" },
      health: { Good: "بہتر", Poor: "کمزور" }
    },
    sd: {
      title: "مٽيءَ جو تجزيو مڪمل",
      health_label: "مٽيءَ جي صحت",
      crop_label: "تجويز ڪيل فصل",
      conf_label: "يقين",
      n_label: "نائٽروجن",
      p_label: "فاسفورس",
      k_label: "پوٽاشيم",
      ph_label: "تيزابیت (pH)",
      m_label: "نمي",
      om_label: "نامياتي مادو",
      imp_title: "🌱 بهتريءَ جا مشورا:",
      predict_btn: "🤖 هاڻي AI سان فصل جو اندازو لڳايو",
      textures: { Fine: "سٺي", "Fine-Medium": "وچولي", Coarse: "سخت", Medium: "وچولي" },
      moisture: { High: "وڌيڪ", Moderate: "مناسب", Low: "گهٽ" },
      om: { High: "وڌيڪ", Medium: "وچولي", Low: "گهٽ" },
      health: { Good: "بهتر", Poor: "ڪمزور" }
    },
    ps: {
      title: "د خاورې تجزیه بشپړه شوه",
      health_label: "د خاورې روغتیا",
      crop_label: "توصیه شوی فصل",
      conf_label: "باور",
      n_label: "نایټروجن",
      p_label: "فاسفورس",
      k_label: "پوټاشیم",
      ph_label: "تیزابیت (pH)",
      m_label: "رطوبت",
      om_label: "عضوي مواد",
      imp_title: "🌱 د ښه والي لارښوونې:",
      predict_btn: "🤖 اوس د AI په واسطه فصل وټاکئ",
      textures: { Fine: "میده", "Fine-Medium": "منځنی میده", Coarse: "زيږه", Medium: "منځنی" },
      moisture: { High: "ډیر", Moderate: "معتدل", Low: "لږ" },
      om: { High: "ډیر", Medium: "منځنی", Low: "لږ" },
      health: { Good: "ښه", Poor: "ضعیف" }
    }
  };

  const profiles = {
    clay: {
      en: {
        soil_type: "Clayey Soil",
        recommended_crop: "Rice",
        advice: "Your soil is Clayey. It has high water retention capacity, which is ideal for rice cultivation. Some nitrogen and phosphorus deficiencies are present.",
        improvements: ["Use organic manure for nitrogen.", "Apply DAP to correct phosphorus deficiency."]
      },
      ur: {
        soil_type: "چکنی مٹی",
        recommended_crop: "چاول",
        advice: "آپ کی مٹی چکنی مٹی (Clayey) قسم کی ہے۔ اس کی پانی جذب کرنے کی صلاحیت زیادہ ہے، جو چاول کی کاشت کے لیے نہایت موزوں ہے۔ نائٹروجن اور فاسفورس کی کچھ کمی ہے۔",
        improvements: ["نائٹروجن کے لیے گوبر کی کھاد کا استعمال کریں۔", "فاسفورس کی کمی پوری کرنے کے لیے ڈی اے پی (DAP) ڈالیں۔"]
      },
      pa: {
        soil_type: "چکنی مٹی",
        recommended_crop: "چاول",
        advice: "تہاڈی مٹی چکنی مٹی ورگی اے۔ ایہدے وچ پانی روکݨ دی صلاحیت زیادہ اے، جیہڑی چاول دی بیجائی لئی بہت ودھیا اے۔ نائٹروجن تے فاسفورس دی کچھ کمی اے۔",
        improvements: ["نائٹروجن لئی گوبر دی کھاد ورتو۔", "فاسفورس گھٹ دور کرن لئی ڈی اے پی (DAP) پاؤ۔"]
      },
      sd: {
        soil_type: "چڪڻي مٽي",
        recommended_crop: "چانور",
        advice: "توهان جي مٽي چڪڻي مٽي آهي. ان ۾ پاڻي بيهارڻ جي صلاحيت وڌيڪ آهي، جيڪا چانورن جي پوک لاءِ بهترين آهي. نائٽروجن ۽ فاسفورس جي ڪجهه کوٽ آهي.",
        improvements: ["نائٽروجن لاءِ ڇاڻيل ڀاڻ جو استعمال ڪريو.", "فاسفورس جي کوٽ ختم ڪرڻ لاءِ ڊي اي پي (DAP) وڌو."]
      },
      ps: {
        soil_type: "خټه لرونکې خاوره",
        recommended_crop: "وریجې",
        advice: "ستاسو خاوره خټه لرونکې خاوره ده. دا د اوبو جذب کولو لوړ ظرفیت لري، کوم چې د وریجو د کرلو لپاره خورا مناسب دی. نایټروجن او فاسفورس یو څه کمښت لري.",
        improvements: ["د نایټروجن لپاره د غواګانو سري وکاروئ.", "د فاسفورس د کمښت پوره کولو لپاره DAP واچوئ."]
      }
    },
    loam: {
      en: {
        soil_type: "Loamy Soil",
        recommended_crop: "Wheat",
        advice: "Your soil is fertile Loamy soil. It has an excellent balance of nutrients, which is highly favorable for wheat, cotton, and sugarcane.",
        improvements: ["Use green manure to maintain organic matter.", "Practice crop rotation."]
      },
      ur: {
        soil_type: "زرخیز لومڑی مٹی",
        recommended_crop: "گندم",
        advice: "آپ کی مٹی زرخیز لومڑی (Loamy) قسم کی ہے۔ اس میں غذائیت کی مقدار بہترین ہے، جو گندم، کپاس اور گنے کے لیے انتہائی سازگار ہے۔",
        improvements: ["نامیاتی مادہ برقرار رکھنے کے لیے سبز کھاد کا استعمال کریں۔", "فصلوں کی گردش (Crop Rotation) پر عمل کریں۔"]
      },
      pa: {
        soil_type: "زرخیز میرا مٹی",
        recommended_crop: "گندم",
        advice: "تہاڈی مٹی زرخیز میرا (Loamy) مٹی اے۔ ایہدے وچ غذائیت بہترین اے، جیہڑی گندم، کپاس تے گنے لئی بہت ودھیا اے۔",
        improvements: ["نامیاتی مادہ رکھن لئی ہری کھاد ورتو۔", "فصلاں دی گردش (Crop Rotation) تے عمل کرو۔"]
      },
      sd: {
        soil_type: "گچ مٽي (لومي)",
        recommended_crop: "ڪڻڪ",
        advice: "توهان جي مٽي زرخيز گچ مٽي آهي. ان ۾ غذائيت تمام بهترين آهي، جيڪا ڪڻڪ، ڪپهه ۽ ڪمند جي پوک لاءِ تمام سٺي آهي.",
        improvements: ["نامياتي مادو برقرار رکڻ لاءِ سائي ڀاڻ جو استعمال ڪريو.", "فصلن جي گردش (Crop Rotation) تي عمل ڪريو."]
      },
      ps: {
        soil_type: "شګلنه خاوره (لومي)",
        recommended_crop: "غنم",
        advice: "ستاسو خاوره حاصلخیزه لومي ده. په دې کې د مغذي موادو کچه خورا ښه ده، کوم چې د غنمو، پنبې او ګني لپاره خورا مناسب دی.",
        improvements: ["د عضوي موادو ساتلو لپاره زرغونه سره وکاروئ.", "د فصلونو نوبتي کرنه (Crop Rotation) عملي کړئ."]
      }
    },
    sand: {
      en: {
        soil_type: "Sandy Soil",
        recommended_crop: "Chickpea",
        advice: "Your soil is Sandy. It has low water and fertilizer retention capacity, which is suitable for chickpeas or pulses. Adding organic matter is recommended.",
        improvements: ["Add organic compost to retain soil moisture.", "Apply urea fertilizer to correct nitrogen deficiency."]
      },
      ur: {
        soil_type: "ریتلی مٹی",
        recommended_crop: "چنے",
        advice: "آپ کی مٹی ریتلی (Sandy) قسم کی ہے۔ اس میں پانی اور کھاد روکنے کی صلاحیت کم ہے، جو چنے یا دالوں کی کاشت کے لیے موزوں ہے۔",
        improvements: ["مٹی میں نمی روکنے کے لیے آرگینک کمپوسٹ ڈالیں۔", "نائٹروجن کی کمی پوری کرنے کے لیے یوریا کھاد ڈالیں۔"]
      },
      pa: {
        soil_type: "ریتلی مٹی",
        recommended_crop: "چنے",
        advice: "تہاڈی مٹی ریتلی اے۔ ایہدے وچ پانی تے کھاد روکݨ دی صلاحیت گھٹ اے، جیہڑی چنے یا دالاں لئی ٹھیک اے۔",
        improvements: ["مٹی وچ نمی رکھن لئی آرگینک کمپوسٹ پاؤ۔", "نائٹروجن گھٹ دور کرن لئی یوریا کھاد پاؤ۔"]
      },
      sd: {
        soil_type: "رڻ پٽ مٽي (ميرا)",
        recommended_crop: "چڻا",
        advice: "توهان جي مٽي وارياسي (سيلٽي) آهي. ان ۾ پاڻي ۽ ڀاڻ بيهارڻ جي صلاحيت گهٽ آهي، جيڪا چڻن ۽ دالين لاءِ مناسب آهي.",
        improvements: ["مٽيءَ ۾ نمي رکڻ لاءِ نامياتي ڪمپوسٽ وڌو.", "نائٽروجن جي کوٽ پوري ڪرڻ لاءِ يوريا ڀاڻ وڌو."]
      },
      ps: {
        soil_type: "شګلنه خاوره",
        recommended_crop: "چڼې",
        advice: "ستاسو خاوره شګلنه ده. دا د اوبو او سرې ساتلو ټیټ ظرفیت لري، کوم چې د چڼو یا دالونو لپاره مناسب دی.",
        improvements: ["په خاوره کې د رطوبت ساتلو لپاره عضوي کمپوسټ اضافه کړئ.", "د نایټروجن د کمښت پوره کولو لپاره یوریا سره واچوئ."]
      }
    },
    silt: {
      en: {
        soil_type: "Silty Soil",
        recommended_crop: "Maize",
        advice: "Your soil is Silty. Its moisture retention and medium texture are highly suitable for maize and millet production.",
        improvements: ["Apply gypsum to improve soil structure.", "Add moderate amounts of phosphorus and potassium."]
      },
      ur: {
        soil_type: "سلٹی مٹی",
        recommended_crop: "مکئی",
        advice: "آپ کی مٹی سلٹی (Silty) قسم کی ہے۔ اس کی نمی اور باریک ساخت مکئی اور جوار کی پیداوار کے لیے بہت موزوں ہے۔",
        improvements: ["مٹی کی ساخت بہتر بنانے کے لیے جپسم کا استعمال کریں۔", "فاسفورس اور پوٹاشیم کی ہلکی مقدار شامل کریں۔"]
      },
      pa: {
        soil_type: "سلٹی مٹی",
        recommended_crop: "مکئی",
        advice: "تہاڈی مٹی سلٹی اے۔ ایہدی نمی تے باریک ساخت مکئی لئی بہت ودھیا اے۔",
        improvements: ["مٹی دا ڈھانچہ بہتر بنان لئی جپسم ورتو۔", "فاسفورس تے پوٹاشیم دی ہلکی مقدار پاؤ۔"]
      },
      sd: {
        soil_type: "سيلٽي مٽي",
        recommended_crop: "مڪئي",
        advice: "توهان جي مٽي سيلٽي آهي. ان جي نمي ۽ بناوت مڪئي ۽ جوئر جي پوک لاءِ تمام سٺي آهي.",
        improvements: ["مٽيءَ جي بناوت بهتر ڪرڻ لاءِ جپسم جو استعمال ڪريو.", "فاسفورس ۽ پوٽاشيم جو ٿورو مقدار شامل ڪريو."]
      },
      ps: {
        soil_type: "سېلټ لرونکې خاوره",
        recommended_crop: "جواري",
        advice: "ستاسو خاوره سېلټ لرونکې ده. د دې رطوبت او منځنۍ جوړښت د جوار د تولید لپاره خورا مناسب دی.",
        improvements: ["د خاورې جوړښت ښه کولو لپاره جپسم وکاروئ.", "د فاسفورس او پوټاشیم لږ مقدار شامل کړئ."]
      }
    }
  };

  const t = i18n[lang] || i18n['en'];

  let soilKey = 'loam';
  const typeLower = (soil.soil_type || '').toLowerCase();
  if (typeLower.includes('clay')) soilKey = 'clay';
  else if (typeLower.includes('sand')) soilKey = 'sand';
  else if (typeLower.includes('silt')) soilKey = 'silt';
  else soilKey = 'loam';

  const p = profiles[soilKey][lang] || profiles[soilKey]['en'];

  const healthColor = {
    'Poor':      '#ef5350',
    'Fair':      '#ffa726',
    'Good':      '#66bb6a',
    'Excellent': '#26a69a',
  };

  const moistureIcon = {
    'Dry': '🏜️', 'Moderate': '💧', 'Wet': '🌊'
  };

  const omIcon = {
    'Low': '📉', 'Medium': '📊', 'High': '📈'
  };

  const hColor = healthColor[soil.soil_health] || '#66bb6a';
  const mIcon  = moistureIcon[soil.moisture_level] || '💧';
  const omIco  = omIcon[soil.organic_matter] || '📊';

  const typeName = p.soil_type;
  const textureName = t.textures[soil.texture] || soil.texture;
  const moistureName = t.moisture[soil.moisture_level] || soil.moisture_level;
  const omName = t.om[soil.organic_matter] || soil.organic_matter;
  const cropRec = p.recommended_crop;
  const adviceText = p.advice;
  const imps = p.improvements;

  let improvementsHtml = '';
  if (imps && imps.length > 0) {
    improvementsHtml = `
      <div class="soil-improvements">
        <div class="si-title">${t.imp_title}</div>
        ${imps.map(imp => `<div class="si-item">• ${imp}</div>`).join('')}
      </div>`;
  }

  const isRtl = ['ur','pa','sd','ps'].includes(lang);
  box.setAttribute('dir', isRtl ? 'rtl' : 'ltr');
  box.className = isRtl ? 'urdu-font' : '';

  const percentSymbol = isRtl ? '٪' : '%';

  box.innerHTML = `
    <div class="sar-header">
      <div class="sar-icon">🔬</div>
      <div>
        <div class="sar-title">${t.title}</div>
        <div class="sar-sub">${typeName} • ${textureName} ${t.textures.Medium === 'درمیانہ' ? 'بناوٹ' : 'Texture'}</div>
      </div>
      <div class="sar-health" style="background:${hColor}20;color:${hColor};border:1.5px solid ${hColor}40">
        ${t.health[soil.soil_health] || soil.soil_health}
      </div>
    </div>

    <div class="sar-crop-recommend">
      <div class="sar-rec-label">${t.crop_label}</div>
      <div class="sar-rec-crop">${cropRec}</div>
      <div class="sar-rec-conf">${soil.confidence}${percentSymbol} ${t.conf_label}</div>
    </div>

    <div class="sar-grid">
      <div class="sar-chip">
        <span class="sc-icon">🌿</span>
        <div class="sc-text-block">
          <span class="sc-v">N: ${soil.estimated_nitrogen}</span>
          <span class="sc-l">${t.n_label}</span>
        </div>
      </div>
      <div class="sar-chip">
        <span class="sc-icon">🧪</span>
        <div class="sc-text-block">
          <span class="sc-v">P: ${soil.estimated_phosphorus}</span>
          <span class="sc-l">${t.p_label}</span>
        </div>
      </div>
      <div class="sar-chip">
        <span class="sc-icon">⚡</span>
        <div class="sc-text-block">
          <span class="sc-v">K: ${soil.estimated_potassium}</span>
          <span class="sc-l">${t.k_label}</span>
        </div>
      </div>
      <div class="sar-chip">
        <span class="sc-icon">⚖️</span>
        <div class="sc-text-block">
          <span class="sc-v">pH ${soil.estimated_ph}</span>
          <span class="sc-l">${t.ph_label}</span>
        </div>
      </div>
      <div class="sar-chip">
        <span class="sc-icon">${mIcon}</span>
        <div class="sc-text-block">
          <span class="sc-v">${moistureName}</span>
          <span class="sc-l">${t.m_label}</span>
        </div>
      </div>
      <div class="sar-chip">
        <span class="sc-icon">${omIco}</span>
        <div class="sc-text-block">
          <span class="sc-v">${omName}</span>
          <span class="sc-l">${t.om_label}</span>
        </div>
      </div>
    </div>

    ${adviceText ? `<div class="sar-advice">💬 ${adviceText}</div>` : ''}

    ${improvementsHtml}

    <button class="sar-predict-btn" onclick="predictCrop()">
      ${t.predict_btn}
    </button>
  `;

  const awaitingCard = $('awaiting-data-card');
  const resultBox = $('result-box');
  if (awaitingCard) awaitingCard.style.display = 'none';
  if (resultBox) resultBox.style.display = 'none';

  box.style.display = 'block';

  // Scroll to result
  box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function hideSoilResult() {
  const box = $('soil-analysis-result');
  if (box) box.style.display = 'none';

  const awaitingCard = $('awaiting-data-card');
  const resultBox = $('result-box');
  const isResultVisible = resultBox && resultBox.style.display === 'block';

  if (awaitingCard && !isResultVisible) {
    awaitingCard.style.display = 'flex';
  }
}

function showSoilLoading(show) {
  const lb = $('soil-loading');
  if (lb) lb.style.display = show ? 'flex' : 'none';
}

function showCamMsg(msg, type = 'error') {
  const el = $('cam-message');
  if (!el) return;
  el.textContent  = msg;
  el.style.display = msg ? 'block' : 'none';
  el.className = 'cam-message ' + (type === 'success' ? 'cam-msg-success' : 'cam-msg-error');
}

// ══════════════════════════════════════════════
//  INITIALIZE DRAG & DROP
// ══════════════════════════════════════════════
window.addEventListener('DOMContentLoaded', () => {
  const dropBox = document.querySelector('.upload-dashed-box');
  if (dropBox) {
    // Prevent default behaviors for drag events
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
      dropBox.addEventListener(eventName, e => {
        e.preventDefault();
        e.stopPropagation();
      }, false);
    });

    // Highlight drop zone
    ['dragenter', 'dragover'].forEach(eventName => {
      dropBox.addEventListener(eventName, () => {
        dropBox.classList.add('highlight');
      }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
      dropBox.addEventListener(eventName, () => {
        dropBox.classList.remove('highlight');
      }, false);
    });

    // Handle drop
    dropBox.addEventListener('drop', e => {
      const dt = e.dataTransfer;
      const files = dt.files;
      if (files && files.length > 0) {
        const file = files[0];
        if (file.type.startsWith('image/')) {
          const eventMock = { target: { files: [file] } };
          handleGalleryUpload(eventMock);
        } else {
          showCamMsg('❌ صرف تصویر فائل قبول کی جائے گی۔');
        }
      }
    }, false);
  }
});