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

from google.cloud import firestore


def ingest_data() -> None:
    """Import the complaints into the Firestore"""
    # ADC automatically picks up the Cloud Run service account credentials.
    db = firestore.Client(project="recht-technisch")

    complaints = db.collection("complaints")
    latest = (
        complaints.order_by("id", direction=firestore.Query.DESCENDING)
        .limit(1)
        .stream()
    )
    max_id = max([doc.to_dict()["id"] for doc in latest], default=0)

    # TODO: figure out raw complaints
    # raw_complaints = ...

    for complaint in raw_complaints:
        max_id += 1
        complaints.document("complaint_" + str(max_id)).set({
            "id": max_id,
            "date_created": complaint["date_created"],
            "body": complaint["body"],
        })

    return None
