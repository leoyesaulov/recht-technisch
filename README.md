# Legal Loves Tech Hackathon 2026

Team `Recht Technisch`'s pilot project at Legal Loves Tech Hackathon 2026

## Team members

- Leo Y
- Daniel B
- Timon G
- Michael K

## Design

- There will be no stage / test / local environment. Everything will run in prod to reduce development compexity.
- Each complaint is forcefully assigned to a singular cluster. Reason: simplify clustering
- Noise clusters are intentionally dropped.

### Architecture

* python + FastAPI
* Google Firestore
* Google Bucket (for agents)
* Google Vertex AI (gemini-embedding-001)
* Google Vertex AI Agent Engine
* Typescript + Vite

## Run

After pulling `pyproject.toml` and (optionally, but recommended) `poetry.lock`, run `poetry install` to create project
venv (if it does not exist) and install the locked dependencies.

`poetry run <args>` executes the args in the venv of the selected project. The usual command is hence
`poetry run python main.py`

Dependency installation is required to run the project.

### API

- Make sure you're logged in with Google Cloud (see Etc setup)
- cd to `backend/`
- `poetry run python api.py`
  (Run without docker)
- Don't forget to edit frontend/server.js with `BACKEND_URL = "http://localhost:8080"`

### Frontend

- cd to `frontend/`
- `gcloud auth application-default login` to login with your user to the Google Cloud console - get token. If you
  haven't run yet.
- Run

```
  docker build -t complaints-dashboard . && \ 
  docker run --rm --network host -v ~/.config/gcloud:/root/.config/gcloud:ro complaints-dashboard
```

The volume mount is needed to access google's credentials within the container

- Access on `http://localhost:3000`

## Etc setup

### Integrate cloud environment locally

- pull `gcloud` cli
- `gcloud auth login` to auth the cli
- `gcloud config set project recht-technisch` to set the default project
- `gcloud auth application-default login` to pull the ADC locally
- Done. Now you can run the code locally as if it were on the cloud

## References

- [Google Cloud Project](https://console.cloud.google.com/welcome?project=recht-technisch)
- [Webpage](https://recht.omniserv.me) - hosted with Google Cloud Run
- [Backend URL](https://recht-technisch-backend-339540402730.europe-west1.run.app/)
- [Challenge page](https://legallovestech.vercel.app/)
