/* sidebar.js - shared app sidebar with green "active" highlight.
   A page opts in via <body data-app="weather"> and an empty
   <aside class="app-sidebar" id="sz-sidebar"></aside> placeholder. */
(function () {
  const page = document.body.getAttribute('data-app');
  const holder = document.getElementById('sz-sidebar');
  if (!page || !holder) return;

  const I = {
    dashboard: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/></svg>',
    advisor:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 20s-4-1-4-7 4-7 4-7M12 20v-9"/><path d="M12 11c0-3 2-5 5-5 0 3-2 5-5 5zM12 14c0-2.5-2-4-4.5-4 0 2.5 2 4 4.5 4z"/></svg>',
    weather:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M19 5l-1.5 1.5M6.5 17.5L5 19"/></svg>',
    history:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v5h5"/><path d="M3.05 13A9 9 0 1 0 6 5.3L3 8"/><path d="M12 7v5l3 2"/></svg>',
    assistant: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"/><path d="M19 11a7 7 0 0 1-14 0M12 18v3"/></svg>',
    node:      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2"/><path d="M9 2v2M15 2v2M9 20v2M15 20v2M2 9h2M2 15h2M20 9h2M20 15h2"/><circle cx="12" cy="12" r="2"/></svg>',
    profile:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M4 21v-1a6 6 0 0 1 12 0v1"/></svg>',
    logout:    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/></svg>',
    globe:     '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15 15 0 0 1 0 20 15 15 0 0 1 0-20"/></svg>',
    settings:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-2.82 1.17V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 8 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15H4a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 5.6 9.4l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 11 4.6V4a2 2 0 0 1 4 0v.09A1.65 1.65 0 0 0 19 5.6l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 21 11h.09"/></svg>',
  };

  // 4th item is the i18n key so the label translates with the rest of the UI.
  const ITEMS = [
    ['dashboard', 'Dashboard',    'dashboard.html', 'dash'],
    ['advisor',   'Crop Advisor', 'ai-agent.html',  'nav_advisor'],
    ['node',      'IoT Node',     'crop-advisor.html', 'nav_node'],
    ['weather',   'Weather',      'weather.html',   'nav_weather'],
    ['history',   'History',      'history.html',   'nav_history'],
  ];

  const top = ITEMS.map(([key, label, href, i18n]) =>
    `<a href="${href}" class="app-sidebar-item${key === page ? ' active' : ''}">${I[key]}<span data-i18n="${i18n}">${label}</span></a>`
  ).join('');

  const LANGS = [['en','English'],['ur','اردو'],['pa','پنجابی'],['sd','سنڌي'],['ps','پښتو']];
  const langOpts = LANGS.map(([code,label]) => `<button class="lang-option" onclick="setLang('${code}', this)">${label}</button>`).join('');

  const bottom =
    `<div class="app-sidebar-sub">${I.globe}<span data-i18n="lang_btn">Languages</span></div>`
    + `<div class="app-sidebar-langopts">${langOpts}</div>`
    + `<a href="settings.html" class="app-sidebar-item${page === 'settings' ? ' active' : ''}">${I.profile}<span data-i18n="nav_profile">Profile</span></a>`
    + `<button class="app-sidebar-item app-sidebar-logout" onclick="logout()">${I.logout}<span data-i18n="logout">Logout</span></button>`;

  // profile header (reflects the saved profile - updates after editing in Settings)
  const esc = s => (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const email = localStorage.getItem('sz_email') || '';
  const name  = localStorage.getItem('sz_name') || (email ? email.split('@')[0] : 'Guest');
  const initial = (name.trim()[0] || 'U').toUpperCase();
  const profHead = `<a href="settings.html" class="app-sidebar-user" title="Edit profile">
      <div class="app-sidebar-avatar">${esc(initial)}</div>
      <div class="app-sidebar-uinfo"><b>${esc(name)}</b><span>${esc(email || 'Not signed in')}</span></div>
    </a>`;

  holder.innerHTML = profHead
    + `<div class="app-sidebar-menu">${top}</div>`
    + `<div class="app-sidebar-divider"></div>`
    + `<div class="app-sidebar-menu">${bottom}</div>`;

  // The sidebar is built after lang.js already ran its initial pass, so the
  // freshly-inserted data-i18n labels still read English. Re-apply the saved
  // language now (and it will also stay in sync on every later switch).
  if (typeof setLang === 'function') {
    setLang(localStorage.getItem('sz_lang') || 'en', null);
  }
})();
