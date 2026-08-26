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
import logging
import random
import time
from collections.abc import Mapping, Sequence
from datetime import datetime

from google import genai
from google.cloud import firestore
from google.genai import errors
from google.genai.types import EmbedContentConfig

from anonymize import anonymize
from shared import db, genai_client

logger = logging.getLogger(__name__)

LOCATION = "europe-west1"

DATE_CREATED_FORMATS = ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S")


def normalize_date_created(value: str) -> str:
    """Validate an input CSV date and return the date-only storage value.

    Source exports may contain either a date or a space-separated timestamp.
    The time is deliberately discarded because ``date_created`` is stored and
    exposed as a calendar date throughout the application.
    """
    for value_format in DATE_CREATED_FORMATS:
        try:
            return datetime.strptime(value, value_format).date().isoformat()
        except ValueError:
            continue
    raise ValueError(
        "date_created must use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS"
    )


def _embed_with_backoff(body: str):
    """Embed one complaint, retrying temporary rate-limit responses."""
    max_retries = 5

    for attempt in range(max_retries + 1):
        try:
            return genai_client.models.embed_content(
                model="gemini-embedding-001",
                contents=body,
                config=EmbedContentConfig(task_type="CLUSTERING", output_dimensionality=384),
            )
        except errors.ClientError as exc:
            if exc.code != 429 or attempt == max_retries:
                raise

            delay = random.uniform(0, 2 ** attempt)
            logger.warning("embedding rate-limited; retrying in %.1f s (attempt %d/%d)", delay, attempt + 1, max_retries)
            time.sleep(delay)
    raise ValueError("Failed to embed complaint")


def ingest_data(raw_complaints: Sequence[Mapping[str, object]]) -> int:
    """Validate, embed, and persist uploaded complaints.

    ``raw_complaints`` must contain dictionaries with ``date_created`` and
    ``complaint`` keys.  The function only writes after every record has been
    validated and embedded, so invalid input cannot leave a partial upload in
    Firestore.  It returns the number of inserted complaints.
    """
    try:
        complaints = db.collection("complaints")
        clean_complaints = []

        if not raw_complaints:
            return 0

        logger.info("ingest_data: starting ingestion of %d complaints", len(raw_complaints))

        for complaint in raw_complaints:
            if not isinstance(complaint, Mapping):
                raise ValueError("Complaint must be an object")

            body = complaint.get("complaint")
            date_created = complaint.get("date_created")

            if not isinstance(body, str) or not body.strip():
                raise ValueError("complaint must be non-empty text")
            if not isinstance(date_created, str):
                raise ValueError("date_created must use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS")

            normalized_date = normalize_date_created(date_created)

            clean_complaints.append({"date_created": normalized_date, "body": body.strip()})

        logger.info("ingest_data: embedding %d complaints via Gemini", len(clean_complaints))
        for complaint in clean_complaints:
            response = _embed_with_backoff(anonymize(complaint["body"]))
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
            batch_end = min(start + 400, len(clean_complaints))
            logger.info("ingest_data: writing batch %d-%d to Firestore", start + 1, batch_end)
            write_complaints(db.transaction(), clean_complaints[start:start + 400])
        logger.info("ingest_data: complete -- inserted %d complaints", len(clean_complaints))
        return len(clean_complaints)
    finally:
        pass

if __name__ == "__main__":
    print("ingest_data() now accepts a list of complaint dictionaries.")
