import time
import csv
import io
import uvicorn
from shared import db
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from shared import MonthlyVolumeResponse, ChartsStatsResponse, ClusterResponse, ComplaintResponse, RecommendationResponse, IngestionResponse
from stats import build_monthly_volume, build_charts_stats, _monthly_cache, _charts_cache, _CACHE_TTL
from recommend import build_recommendations, _reco_cache, _RECO_TTL
from data_ingestion import ingest_data
from get_cluster_complaints import get_cluster_complaints
from cluster import run_pipeline, needs_reclustering

_clusters_cache: dict = {"data": None}

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
REQUIRED_CSV_COLUMNS = ["date_created", "complaint"]

app = FastAPI(title="Recht Technisch API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/")
def main():
    """
    Service identity endpoint.

    Input:  None — no path parameters, query parameters, or request body.
    Returns: A static JSON object containing the project name and a greeting
             message, confirming the service is running.
    Processing: No computation; returns a hard-coded dict immediately.
    Ownership: API layer (api.py) — service entry point.
    """
    return {"name": "Legal Loves Tech 2026", "message": "Hello World!"}


@app.get("/health")
def health():
    """
    Infrastructure health check.

    Input:  None — no parameters.
    Returns: {"status": "ok", "db": "ok"} when Firestore is reachable and
             contains at least one complaint document; {"status": "ok",
             "db": "empty"} when the collection exists but has no documents.
             Raises HTTP 503 with an error detail dict if the Firestore probe
             raises any exception.
    Processing: Issues a single-document .limit(1).stream() probe against the
                "complaints" Firestore collection. An empty result is treated as
                a valid (non-error) state; only an exception triggers a 503.
    Ownership: API layer (api.py) — infrastructure health check, consumed by
               Cloud Run liveness/readiness probes.
    """
    try:
        first = next(iter(db.collection("complaints").limit(1).stream()), None)
        db_status = "ok" if first is not None else "empty"
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"status": "error", "db": str(exc)})
    return {"status": "ok", "db": db_status}


@app.post("/ingestion", response_model=IngestionResponse, status_code=201)
async def ingestion(file: UploadFile | None = File(None)):
    """Ingest a UTF-8 CSV with exactly ``date_created,complaint`` columns."""
    if file is None or not file.filename or not file.filename.lower().endswith(".csv"):
        return JSONResponse(status_code=400, content={"error": "Please upload a .csv file."})

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        return JSONResponse(status_code=400, content={"error": "The CSV file must not exceed 10 MB."})

    try:
        decoded = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(decoded))
        if reader.fieldnames != REQUIRED_CSV_COLUMNS:
            raise ValueError("CSV columns must be exactly date_created and complaint.")
        rows = list(reader)
    except (UnicodeDecodeError, csv.Error, ValueError) as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})

    if not rows:
        return JSONResponse(status_code=400, content={"error": "The CSV file must contain at least one complaint."})

    try:
        inserted = ingest_data(rows)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except Exception as exc:
        import traceback
        print(f"ERROR ingestion: {exc}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Something went wrong.") from exc

    # All dashboard aggregates are derived from complaints and must be rebuilt.
    for cache in (_monthly_cache, _charts_cache, _reco_cache):
        cache["data" if "data" in cache else "recs"] = None
        cache["expires_at"] = 0
    _clusters_cache["data"] = None
    return IngestionResponse(inserted=inserted)


@app.get("/descriptive-stats/monthly-volume", response_model=MonthlyVolumeResponse)
def descriptive_stats_monthly_volume():
    """
    Complaint volume time-series endpoint.

    Input:  None — no query or path parameters.
    Returns: A MonthlyVolumeResponse JSON object containing the computation
             timestamp, total complaint count, and a contiguous monthly volume
             series. No LLM calls are made; all data is derived from Firestore
             date_created fields.
    Processing: Checks _monthly_cache; on a miss delegates to
                build_monthly_volume() from stats.py and caches the result for
                _CACHE_TTL seconds. Exceptions are logged and re-raised as 500.
    Ownership: API layer (api.py) — thin cache wrapper; computation lives in
               stats.py:build_monthly_volume.
    """
    now = time.time()
    if _monthly_cache["data"] is not None and now < _monthly_cache["expires_at"]:
        return _monthly_cache["data"]
    try:
        result = build_monthly_volume()
    except Exception as exc:
        import traceback
        print(f"ERROR descriptive_stats_monthly_volume: {exc}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail={"error": "Something went wrong."})
    _monthly_cache["data"] = result
    _monthly_cache["expires_at"] = now + _CACHE_TTL
    return result


@app.get("/descriptive-stats/charts", response_model=ChartsStatsResponse)
def descriptive_stats_charts():
    """
    Severity, channel, and retailer breakdown endpoint.

    Input:  None — no query or path parameters.
    Returns: A ChartsStatsResponse JSON object containing the computation
             timestamp and percentage breakdowns by severity, channel, and
             retailer. Unclassified complaints are sent to the Gemini LLM in
             batches before breakdowns are computed.
    Processing: Checks _charts_cache; on a miss delegates to
                build_charts_stats() from stats.py and caches the result for
                _CACHE_TTL seconds. Exceptions are logged and re-raised as 500.
    Ownership: API layer (api.py) — thin cache wrapper; computation lives in
               stats.py:build_charts_stats.
    """
    now = time.time()
    if _charts_cache["data"] is not None and now < _charts_cache["expires_at"]:
        return _charts_cache["data"]
    try:
        result = build_charts_stats()
    except Exception as exc:
        import traceback
        print(f"ERROR descriptive_stats_charts: {exc}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail={"error": "Something went wrong."})
    _charts_cache["data"] = result
    _charts_cache["expires_at"] = now + _CACHE_TTL
    return result


@app.get("/clusters", response_model=list[ClusterResponse])
def clusters():
    """Return all complaint clusters, reclustering first if new complaints have been ingested."""
    if _clusters_cache["data"] is not None:
        return _clusters_cache["data"]

    try:
        if needs_reclustering():
            run_pipeline()
        cluster_docs = db.collection("clusters").stream()
        result = [
            ClusterResponse(
                id=str(cluster.get("cluster_label")),
                title=cluster.get("cluster_title"),
                text=cluster.get("cluster_body"),
                count=cluster.get("cluster_size"),
            )
            for cluster in cluster_docs
        ]
    except Exception as exc:
        import traceback
        print(f"ERROR clusters: {exc}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail={"error": "Something went wrong."})

    _clusters_cache["data"] = result
    return result


@app.get("/clusters/{cluster_id}/complaints", response_model=list[ComplaintResponse])
def cluster_complaints(cluster_id: int):
    """Return at most 50 newest complaints belonging to one cluster.

    ``cluster_id`` is the numeric identifier returned by :endpoint:`/clusters`.
    Complaint records are already forcefully assigned to one label by the
    clustering pipeline, so the endpoint only filters and serializes them.
    """
    try:
        return get_cluster_complaints(cluster_id)
    except Exception as exc:
        import traceback
        print(f"ERROR cluster_complaints({cluster_id}): {exc}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail={"error": "Something went wrong."})


@app.get("/recommendations", response_model=list[RecommendationResponse])
def recommendations():
    """
    LLM-generated policy recommendations endpoint.

    Input:  None — no query or path parameters.
    Returns: A list of exactly three RecommendationResponse objects, one each
             for the ids "political", "focus", and "user_warning". Each object
             contains a short actionable headline (text) and a one-sentence
             reasoning string (detail).
    Processing: Checks the module-level _reco_cache dict against the current
                Unix timestamp. If a valid cached result exists (within the
                3600-second TTL), it is returned immediately without any I/O. On
                a cache miss, delegates to build_recommendations() from
                recommend.py, which reads the Firestore clusters collection and
                calls the Gemini LLM; the result is stored in the cache before
                being returned. Any exception is caught, logged to stdout, and
                re-raised as HTTP 500.
    Ownership: API layer (api.py) — thin cache wrapper; computation lives in
               recommend.py:build_recommendations.
    """
    now = time.time()
    if _reco_cache["recs"] is not None and now < _reco_cache["expires_at"]:
        return _reco_cache["recs"]
    try:
        result = build_recommendations()
    except Exception as exc:
        import traceback
        print(f"ERROR recommendations: {exc}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail={"error": "Something went wrong."})
    _reco_cache["recs"] = result
    _reco_cache["expires_at"] = now + _RECO_TTL
    return result


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
