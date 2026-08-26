from datetime import date, timedelta
from shared import db

_RETENTION_DAYS = 365


def purge_expired_complaints() -> int:
    today = date.today().isoformat()
    cutoff = (date.today() - timedelta(days=_RETENTION_DAYS)).isoformat()

    expired = list(db.collection("complaints").where("date_created", "<", cutoff).stream())
    future  = list(db.collection("complaints").where("date_created", ">", today).stream())

    to_delete = expired + future
    if not to_delete:
        return 0

    batch = db.batch()
    count = 0
    for doc in to_delete:
        batch.delete(doc.reference)
        count += 1
        if count % 500 == 0:
            batch.commit()
            batch = db.batch()
    if count % 500:
        batch.commit()
    db.collection("metadata").document("clustering").set(
        {"last_clustered_max_id": 0}, merge=True
    )
    print(f"Retention: purged {count} complaints ({len(expired)} old, {len(future)} future-dated)")
    return count
