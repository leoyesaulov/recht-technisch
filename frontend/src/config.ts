// The browser never talks to the backend directly — it only ever calls this
// same-origin path, which app/server.js proxies to the real backend after
// attaching a Google-signed ID token (see server.js for details).
export const API_BASE_URL = "/api";
