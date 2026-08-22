"""Import complaint data, embed it, and store it in Firestore.

The ingestion pipeline is:
data source -> source-specific transformation -> Gemini embedding -> Firestore.

Each stored complaint has the following shape (additional clustering fields are
added later by :mod:`cluster`):
```
{
    "id": integer,                 # primary key
    "date_created": "YYYY-MM-DD",
    "body": text,
    "embedding": <n-dimensional vector>,
    "cluster_label": integer,      # added by clustering
    "cluster_prob": float          # added by clustering
}
```

Use :func:`ingest_data` as the single entry point for loading a source into the
``complaints`` Firestore collection. It raises source or validation errors to
the caller instead of partially hiding them.
"""
import csv
import random
import time
from datetime import date

from google import genai
from google.cloud import firestore
from google.genai import errors
from google.genai.types import EmbedContentConfig

from shared import db

LOCATION = "europe-west1"


def _embed_with_backoff(client: genai.Client, body: str):
    """Embed one complaint, retrying temporary rate-limit responses."""
    max_retries = 5

    for attempt in range(max_retries + 1):
        try:
            return client.models.embed_content(
                model="gemini-embedding-001",
                contents=body,
                config=EmbedContentConfig(task_type="CLUSTERING", output_dimensionality=384),
            )
        except errors.ClientError as exc:
            if exc.code != 429 or attempt == max_retries:
                raise

            delay = random.uniform(0, 2 ** attempt)
            print(
                f"Embedding rate-limited; retrying in {delay:.1f}s "
                f"(attempt {attempt + 1}/{max_retries})"
            )
            time.sleep(delay)
    raise ValueError("Failed to embed complaint")


def ingest_data() -> None:
    """Load, validate, embed, and persist complaints from the configured CSV."""
    genai_client = None

    try:
        complaints = db.collection("complaints")
        clean_complaints = []

        with open("/Users/Misha/Documents/Dev/projects/playground/temp/prunned_complaints.csv") as f:
            raw_complaints = list(csv.DictReader(f))

        if not raw_complaints:
            return None

        genai_client = genai.Client(
            enterprise=True,
            project="recht-technisch",
            location=LOCATION,
        )

        for complaint in raw_complaints:
            if not isinstance(complaint, dict):
                raise ValueError("Complaint must be an object")

            body = complaint.get("body")
            date_created = complaint.get("date_created")

            if not isinstance(body, str) or not body.strip():
                raise ValueError("Complaint body must be non-empty text")
            if not isinstance(date_created, str):
                raise ValueError("date_created must be a YYYY-MM-DD string")

            try:
                date_created = date.fromisoformat(date_created).isoformat()
            except ValueError as exc:
                raise ValueError("date_created must be a YYYY-MM-DD string") from exc

            response = _embed_with_backoff(genai_client, body.strip())
            if len(response.embeddings) != 1:
                raise ValueError(
                    "Expected exactly one embedding per complaint, "
                    f"received {len(response.embeddings)}"
                )
            values = response.embeddings[0].values

            if not hasattr(values, "__iter__") or not all(isinstance(i, float) for i in values):
                raise ValueError("Malformed embedding values")

            clean_complaints.append({"date_created": date_created, "body": body.strip(), "embedding": values})

        @firestore.transactional
        def write_complaints(transaction, items):
            latest = complaints.order_by("id", direction=firestore.Query.DESCENDING).limit(1).stream(transaction=transaction)
            max_id = max((doc.to_dict()["id"] for doc in latest), default=0)

            for complaint in items:
                max_id += 1
                transaction.set(
                    complaints.document(f"complaint_{max_id}"),
                    {"id": max_id, "date_created": complaint["date_created"], "body": complaint["body"], "embedding": complaint["embedding"]},
                )

        # Firestore transactions support at most 500 writes.
        for start in range(0, len(clean_complaints), 400):
            write_complaints(db.transaction(), clean_complaints[start:start + 400])
    finally:
        if genai_client is not None:
            genai_client.close()

if __name__ == "__main__":
    print("Start data ingestion pipeline")
    ingest_data()
    print("Finished data ingestion pipeline successfully!")