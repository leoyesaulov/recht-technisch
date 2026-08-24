"""Read the complaints assigned to one complaint cluster."""

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from shared import ComplaintResponse, db

MAX_CLUSTER_COMPLAINTS = 50


def get_cluster_complaints(cluster_label: int) -> list[ComplaintResponse]:
    """Return up to the 50 newest complaints forcefully assigned to a cluster.

    The cluster label is the same numeric identifier exposed by ``GET /clusters``.
    The limit is intentionally fixed at the data-access layer so callers cannot
    accidentally request a complete raw-complaint dump.
    """
    documents = (
        db.collection("complaints")
        .where(filter=FieldFilter("cluster_label", "==", cluster_label))
        .order_by("date_created", direction=firestore.Query.DESCENDING)
        .limit(MAX_CLUSTER_COMPLAINTS)
        .stream()
    )

    return [
        ComplaintResponse(
            id=str(document.get("id") or document.id),
            date_created=document.get("date_created"),
            body=document.get("body"),
        )
        for document in documents
    ]
