# Legal Loves Tech Hackathon 2026

Team `Recht Technisch`'s pilot project at Legal Loves Tech Hackathon 2026

## Team members
- Leo Y
- Daniel B
- Timon G
- Michael K

## Design
- There will be no stage / test / local environment. Everything will run in prod to reduce development compexity.

### Architecture
* Google Firestore
* Google Vertex AI (gemini-embedding-001)
* Google Vertex AI Agent Engine

### Security / Auth
The backend Cloud Run service is deployed with `--no-allow-unauthenticated`, so
Google's platform rejects unauthenticated requests before they ever reach the
FastAPI app — this is the actual enforcement boundary, not just a nicety on
top of something weaker. The frontend's Cloud Run service account has been
granted `roles/run.invoker` on the backend service:

```
gcloud run services add-iam-policy-binding <backend-service> \
  --member="serviceAccount:<frontend-service-account>" \
  --role="roles/run.invoker"
```

Because a browser can never mint a Google-signed ID token itself, the
frontend is not a pure static SPA — `app/server.js` also proxies `/api/*`
calls from the browser to the real backend, minting an ID token via
Application Default Credentials (`google-auth-library`) on each proxied
request. The browser only ever talks to the frontend's own origin.

## Run

After pulling `pyproject.toml` and (optionally, but recommended) `poetry.lock`, run `poetry install` to create project venv (if does not exist) and install the locked dependencies.

`poetry run <args>` executes the args in the venv of the selected project. The usual command is hence `poetry run python main.py`

Dependency installation is required to run the project.

### API
`poetry run python main.py`

### Frontend
- cd to `app/`
- `docker build -t complaints-dashboard . && docker run --rm -p 8080:8080 -e BACKEND_URL=https://recht-technisch-backend-339540402730.europe-west1.run.app complaints-dashboard`
- `BACKEND_URL` is required at runtime — the server exits immediately if it's missing.
- Without valid Application Default Credentials in the container, the static
  site still loads but `/api/*` calls fail with a `502` (the proxy can't mint
  an ID token). To test real proxying locally, run
  `gcloud auth application-default login` on the host and mount the
  resulting credentials into the container, e.g.
  `-v ~/.config/gcloud:/root/.config/gcloud:ro`. On Cloud Run itself this is
  automatic via the service's attached identity — no credential wiring
  needed.

## References
- [Google Cloud Project](https://console.cloud.google.com/welcome?project=recht-technisch)
- [Webpage](recht.omniserv.me) - hosted with Google CLoud Run
- [Backend URL](https://recht-technisch-backend-339540402730.europe-west1.run.app/)
- [Challenge page](https://legallovestech.vercel.app/#:~:text=Recht%20Technisch,IV\)%20(PDF))
