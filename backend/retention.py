import logging
from datetime import date, timedelta
from shared import db

logger = logging.getLogger(__name__)

_RETENTION_DAYS = 365


def purge_expired_complaints() -> int:
    today = date.today().isoformat()
    cutoff = (date.today() - timedelta(days=_RETENTION_DAYS)).isoformat()

    expired = list(db.collection("complaints").where("date_created", "<", cutoff).stream())
    future  = list(db.collection("complaints").where("date_created", ">", today).stream())

    to_delete = expired + future
    if not to_delete:
        logger.info("purge_expired_complaints: nothing to purge")
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
    logger.info("purge_expired_complaints: purged %d complaints (%d expired, %d future-dated)", count, len(expired), len(future))
    return count
