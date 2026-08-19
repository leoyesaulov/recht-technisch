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

## Run

After pulling `pyproject.toml` and (optionally, but recommended) `poetry.lock`, run `poetry install` to create project venv (if does not exist) and install the locked dependencies.

`poetry run <args>` executes the args in the venv of the selected project. The usual command is hence `poetry run python main.py`

Dependency installation is required to run the project.

### API
`poetry run python main.py`


## References
- [Google Cloud Project](https://console.cloud.google.com/welcome?project=recht-technisch)
- [Backend URL](https://recht-technisch-backend-339540402730.europe-west1.run.app/)
- [Challenge page](https://legallovestech.vercel.app/#:~:text=Recht%20Technisch,IV\)%20(PDF))
