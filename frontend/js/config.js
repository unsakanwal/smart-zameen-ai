/* config.js - single source of truth for the backend API base URL.
 *
 * The frontend is deployed on Vercel and the backend on Render, so they live on
 * DIFFERENT origins. Set BACKEND_URL below to your Render service URL. When the
 * page runs locally (file://, localhost, or served by Flask) it auto-uses the
 * local backend instead, so you don't have to change anything for development.
 *
 * This must be the FIRST script loaded on every page (before main.js, chat.js,
 * camera.js, lang.js, etc.) so they all pick up the right API base.
 */
(function () {
  // 👇 CHANGE THIS to your Render backend URL after deploying the backend.
  var BACKEND_URL = 'https://smart-zameen-ai.onrender.com';

  var host = location.hostname;
  var isLocal =
    location.protocol === 'file:' ||
    host === 'localhost' ||
    host === '127.0.0.1' ||
    /^192\.168\./.test(host) ||
    /^10\./.test(host);

  var base;
  if (window.SZ_BACKEND) {
    base = window.SZ_BACKEND;                       // explicit manual override wins
  } else if (location.protocol === 'file:') {
    base = 'http://localhost:5000';                 // opened as a file → local Flask
  } else if (isLocal) {
    base = '';                                       // served by Flask locally → same-origin
  } else {
    base = BACKEND_URL;                              // deployed (Vercel) → Render backend
  }

  // Expose the resolved base under every name the app's scripts read.
  window.SZ_BACKEND = base;
  window.SZ_API = base;
  window.API_URL = base;
})();
