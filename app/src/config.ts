const backendUrl = import.meta.env.VITE_BACKEND_URL ??
  "https://recht-technisch-backend-339540402730.europe-west1.run.app";

export const API_BASE_URL = `${backendUrl.replace(/\/$/, "")}/api`;
