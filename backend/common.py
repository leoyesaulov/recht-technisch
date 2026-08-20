"""
This file owns import and embedding of complaints from any source into firestore

The pipeline is as follows:
Data sources => Transform in the script => Embed contents => Load into Firestore using a standardized format
A complaint is a JSON object with the following keys:
[collection: "complaints"]
{
  "id": integer, primary key
  "date_created": YYYY-MM-DD,
  "body": <text of the complaint>
  "embedding": <n-dimensional vector>,
  "cluster_label": integer (>=0),
  "cluster_prob": float (0<=x<=1)
}

A cluster object is a JSON object with the following keys:
[collection: "clusters"]
{
    "cluster_label": integer (>=0),
    "cluster_size": integer (>0),
    "cluster_title": text,
    "cluster_body": text
}

This object exists at the final state of the document's lifetime.

Use Google's firestore. The code is geared towards cloud, so do not run locally
There should be a singular "ingest_data" function that loads from ... and inserts into firestore.
On error raise ImportError
"""

from typing import Any


def ingest_data() -> None:
    """Import the complaints into the Firestore"""
    db = None
    genai_client = None

    try:
        # ADC automatically picks up the Cloud Run service account credentials.
        from google.cloud import firestore
        from google import genai
        from google.genai.types import EmbedContentConfig

        db = firestore.Client(project="recht-technisch")
        complaints = db.collection("complaints")
        # TODO: figure out raw complaints
        raw_complaints: list[Any] = []
        if not raw_complaints:
            return None

        genai_client = genai.Client(
            # "enterprise" means the Vertex AI / Google Cloud endpoint here;
            # it does not imply an enterprise subscription.
            enterprise=True,
            project="recht-technisch",
            location="europe-west1",
        )

        # gemini-embedding-001 is documented as accepting one input per
        # request on Vertex AI, so do not send the complaints as one batch.
        embeddings = []
        for complaint in raw_complaints:
            response = genai_client.models.embed_content(
                model="gemini-embedding-001",
                contents=complaint["body"],
                config=EmbedContentConfig(task_type="CLUSTERING"),
            )
            if len(response.embeddings) != 1:
                raise ValueError(
                    "Expected exactly one embedding per complaint, "
                    f"received {len(response.embeddings)}"
                )
            embeddings.append(response.embeddings[0].values)

        complaint_embeddings = list(
            zip(raw_complaints, embeddings, strict=True)
        )

        @firestore.transactional
        def write_complaints(transaction, items):
            latest = (
                complaints.order_by("id", direction=firestore.Query.DESCENDING)
                .limit(1)
                .stream(transaction=transaction)
            )
            max_id = max(
                (doc.to_dict()["id"] for doc in latest),
                default=0,
            )

            for complaint, embedding in items:
                max_id += 1
                if embedding.values is None:
                    raise ValueError("Google returned an embedding without values")
                transaction.set(
                    complaints.document(f"complaint_{max_id}"),
                    {
                        "id": max_id,
                        "date_created": complaint["date_created"],
                        "body": complaint["body"],
                        "embedding": embedding,
                    },
                )

        # Firestore transactions support at most 500 writes.
        for start in range(0, len(complaint_embeddings), 400):
            write_complaints(
                db.transaction(), complaint_embeddings[start: start + 400]
            )

    finally:
        if genai_client is not None:
            genai_client.close()
        if db is not None:
            db.close()

    return None


def cluster_complaints() -> None:
    """
    Query complaints stored in Firestore and insert clusters back into Firestore
    """
    # Keep these imports local: importing common.py should not require Google
    # credentials (or the comparatively heavy sklearn dependency).
    from google.cloud import firestore
    from sklearn.cluster import HDBSCAN

    db = None
    # TODO: continue simplifying
    try:
        db = firestore.Client(project="recht-technisch")
        complaints = db.collection("complaints")
        documents = list(complaints.select(["embedding"]).stream())

        embeddings = [document.get("embedding") for document in documents]

        model = HDBSCAN(min_samples=10, min_cluster_size=30).fit(embeddings)
        labels = [int(label) for label in model.labels_]
        probabilities = model.probabilities_

        for document, label, probability in zip(
            documents,
            labels,
            probabilities,
            strict=True,
        ):
            document.reference.update(
                {
                    "cluster_label": int(label),
                    "cluster_prob": float(probability),
                }
            )

        clusters = dict()
        for l in labels:
            clusters[l] = clusters.get(l, 0) + 1

        for label, count in clusters.items():
            db.collection("clusters").document(f"cluster_{label}").set(
                {
                    "cluster_label": label,
                    "cluster_size": count,
                },
            )
    finally:
        if db is not None:
            db.close()

    return None
