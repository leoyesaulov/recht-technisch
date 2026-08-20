"""
This file owns import of complaints from any source into firestore

The pipeline is as follows:
Data sources => Transform in the script => Load into Firestore using a standardized format
A complaint is a json object with the following keys:
{
  "id": integer, primary key
  "date_created": YYYY-MM-DD,
  "body": <text of the complaint>
  "embedding": <n-dimensional vector> (absent at ingest time)
}

Use google's firestore. The code is geared towards cloud, so do not run locally
There should be a singular "run" function that loads from <blank> and inserts into firestore.
On error raise ImportError
"""

from typing import Any


def ingest_data() -> None:
    """Import the complaints into the Firestore"""
    # ADC automatically picks up the Cloud Run service account credentials.
    from google.cloud import firestore
    from google import genai
    db = firestore.Client(project="recht-technisch")

    complaints = db.collection("complaints")
    # WARNING: no checks for duplicate complaints. All complaints are assumed unique
    latest = (
        complaints.order_by("id", direction=firestore.Query.DESCENDING)
        .limit(1)
        .stream()
    )
    max_id = max([doc.to_dict()["id"] for doc in latest], default=0)

    # TODO: figure out raw complaints
    raw_complaints: list[Any] = []

    genai_client = genai.Client(
        vertexai=True,
        project="recht-technisch",
        location="europe-west1",
    )

    response = genai_client.models.embed_content(
        model="gemini-embedding-001",
        contents=[raw_complaint["body"] for raw_complaint in raw_complaints],
    )

    embeddings = response.embeddings[0].values

    for complaint, embedding in zip(raw_complaints, embeddings):
        max_id += 1
        complaints.document("complaint_" + str(max_id)).set({
            "id": max_id,
            "date_created": complaint["date_created"],
            "body": complaint["body"],
            "embedding": embedding,
        })

    return None
