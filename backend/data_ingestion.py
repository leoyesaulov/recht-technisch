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
import random
import time
from datetime import date
from collections.abc import Mapping, Sequence

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


def ingest_data(raw_complaints: Sequence[Mapping[str, object]]) -> int:
    """Validate, embed, and persist uploaded complaints.

    ``raw_complaints`` must contain dictionaries with ``date_created`` and
    ``complaint`` keys.  The function only writes after every record has been
    validated and embedded, so invalid input cannot leave a partial upload in
    Firestore.  It returns the number of inserted complaints.
    """
    genai_client = None

    try:
        complaints = db.collection("complaints")
        clean_complaints = []

        if not raw_complaints:
            return 0

        for complaint in raw_complaints:
            if not isinstance(complaint, Mapping):
                raise ValueError("Complaint must be an object")

            body = complaint.get("complaint")
            date_created = complaint.get("date_created")

            if not isinstance(body, str) or not body.strip():
                raise ValueError("complaint must be non-empty text")
            if not isinstance(date_created, str):
                raise ValueError("date_created must be a YYYY-MM-DD string")

            try:
                if len(date_created) != 10 or date_created[4] != "-" or date_created[7] != "-":
                    raise ValueError
                normalized_date = date.fromisoformat(date_created).isoformat()
            except ValueError as exc:
                raise ValueError("date_created must be a YYYY-MM-DD string") from exc

            clean_complaints.append({"date_created": normalized_date, "body": body.strip()})

        genai_client = genai.Client(
            enterprise=True,
            project="recht-technisch",
            location=LOCATION,
        )

        for complaint in clean_complaints:
            response = _embed_with_backoff(genai_client, complaint["body"])
            if len(response.embeddings) != 1:
                raise ValueError(
                    "Expected exactly one embedding per complaint, "
                    f"received {len(response.embeddings)}"
                )
            values = response.embeddings[0].values

            if not hasattr(values, "__iter__") or not all(isinstance(i, float) for i in values):
                raise ValueError("Malformed embedding values")

            complaint["embedding"] = values

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
        return len(clean_complaints)
    finally:
        if genai_client is not None:
            genai_client.close()

if __name__ == "__main__":
    print("ingest_data() now accepts a list of complaint dictionaries.")
