// Serves the built SPA and proxies /api/* to the real backend Cloud Run
// service, attaching a Google-signed ID token on every proxied request so
// the backend (deployed with `--no-allow-unauthenticated`) can enforce via
// IAM that only this frontend service may call it.
//
// A browser can never mint that token itself — only a Cloud Run service's
// own attached identity (via Application Default Credentials) can — which is
// why this proxy exists instead of the browser calling the backend directly.

import express from "express";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DIST_DIR = path.join(__dirname, "dist");

const PORT = 80;
const BACKEND_URL = "https://recht-technisch-backend-339540402730.europe-west1.run.app";

const isLocal = BACKEND_URL.startsWith("http://localhost") ||
  BACKEND_URL.startsWith("http://host.docker.internal");

// Fetches an OIDC ID token from the GCP metadata server. Cloud Run exposes
// this endpoint automatically; the token is scoped to `audience` so the
// backend can verify the caller's identity via IAM.
async function fetchIdToken(audience) {
  const url =
    `http://metadata.google.internal/computeMetadata/v1/instance/` +
    `service-accounts/default/identity?audience=${encodeURIComponent(audience)}`;
  const res = await fetch(url, { headers: { "Metadata-Flavor": "Google" } });
  if (!res.ok) throw new Error(`Metadata server returned HTTP ${res.status}`);
  return res.text();
}

const app = express();

// Proxy is registered before static serving so /api/* never falls through
// to the SPA fallback below.
app.use("/api", async (req, res) => {
  const targetUrl = new URL(
    req.originalUrl.replace(/^\/api/, "") || "/",
    BACKEND_URL,
  );

  try {
    const authHeaders = isLocal
      ? {}
      : { Authorization: `Bearer ${await fetchIdToken(BACKEND_URL)}` };

    const hasBody = !["GET", "HEAD"].includes(req.method);
    const backendRes = await fetch(targetUrl, {
      method: req.method,
      headers: {
        ...(authHeaders || {}),
        ...(req.headers["content-type"]
          ? { "content-type": req.headers["content-type"] }
          : {}),
        accept: req.headers["accept"] ?? "application/json",
      },
      body: hasBody ? req : undefined,
      duplex: hasBody ? "half" : undefined,
    });

    res.status(backendRes.status);
    const contentType = backendRes.headers.get("content-type");
    if (contentType) res.setHeader("content-type", contentType);

    if (backendRes.body) {
      const { Readable } = await import("node:stream");
      Readable.fromWeb(backendRes.body).pipe(res);
    } else {
      res.end();
    }
  } catch (err) {
    console.error("Failed to proxy request to backend:", err);
    res.status(502).json({ error: "Could not reach the backend service." });
  }
});

app.use(express.static(DIST_DIR));

// SPA fallback for client-side routing (react-router). Express 5's router
// (path-to-regexp v8) requires a named wildcard rather than a bare "*".
app.get("/*splat", (req, res) => {
  res.sendFile(path.join(DIST_DIR, "index.html"));
});

app.listen(PORT, "0.0.0.0", () => {
  console.log(`Frontend server listening on port ${PORT}`);
  console.log(`Proxying /api/* to ${BACKEND_URL}`);
});
