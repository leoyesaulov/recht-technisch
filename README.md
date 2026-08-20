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
* python + FastAPI
* Google Firestore
* Google Vertex AI (gemini-embedding-001)
* Google Vertex AI Agent Engine
* Typescript + Vite

## Run

After pulling `pyproject.toml` and (optionally, but recommended) `poetry.lock`, run `poetry install` to create project venv (if does not exist) and install the locked dependencies.

`poetry run <args>` executes the args in the venv of the selected project. The usual command is hence `poetry run python main.py`

Dependency installation is required to run the project.

**Warning:** running locally is not recommended since the project is geared towards cloud. 
Local runs may therefore be unstable or not run at all.

### API
`poetry run python api.py`

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
- [Webpage](https://recht.omniserv.me) - hosted with Google CLoud Run
- [Backend URL](https://recht-technisch-backend-339540402730.europe-west1.run.app/)
- [Challenge page](https://legallovestech.vercel.app/#:~:text=Recht%20Technisch,IV\)%20(PDF))
