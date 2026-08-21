import time
import uvicorn
from shared import db
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from shared import DescriptiveStatsResponse, ClusterResponse, RecommendationResponse
from stats import _build_stats, _stats_cache, _CACHE_TTL
from recommend import build_recommendations, _reco_cache, _RECO_TTL

app = FastAPI(title="Recht Technisch API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["GET"],
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


@app.get("/test_connection")
def test_connection():
    """
    Connectivity diagnostic stub.

    Input:  None — no parameters.
    Returns: A JSON object with a hard-coded "password" field used during
             development to verify the service is reachable end-to-end.
    Processing: No computation; returns a hard-coded dict immediately.
    Ownership: API layer (api.py) — development/debug utility, not used in
               production flows.
    """
    return {"password": "abhschda"}


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


@app.get("/descriptive-stats", response_model=DescriptiveStatsResponse)
def descriptive_stats():
    """
    Aggregated complaint statistics endpoint.

    Input:  None — no query or path parameters.
    Returns: A DescriptiveStatsResponse JSON object containing the timestamp of
             the last computation, total complaint count, monthly volume series,
             and percentage breakdowns by severity, channel, and retailer.
    Processing: Checks the module-level _stats_cache dict against the current
                Unix timestamp. If a valid cached result exists (within the
                300-second TTL), it is returned immediately without any I/O. On
                a cache miss, delegates to _build_stats() from stats.py, which
                reads Firestore and calls the Gemini LLM; the result is stored
                in the cache before being returned. Any exception from
                _build_stats() is caught, logged to stdout, and re-raised as
                HTTP 500.
    Ownership: API layer (api.py) — thin cache wrapper; computation lives in
               stats.py:_build_stats.
    """
    now = time.time()
    if _stats_cache["stats"] is not None and now < _stats_cache["expires_at"]:
        return _stats_cache["stats"]
    try:
        result = _build_stats()
    except Exception as exc:
        import traceback
        print(f"ERROR descriptive_stats: {exc}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail={"error": "Something went wrong."})
    _stats_cache["stats"] = result
    _stats_cache["expires_at"] = now + _CACHE_TTL
    return result


@app.get("/clusters", response_model=list[ClusterResponse])
def clusters():
    """
    Complaint cluster listing endpoint.

    Input:  None — no query or path parameters.
    Returns: A list of ClusterResponse objects, each containing an id, title,
             representative anonymised complaint text, and complaint count for
             one semantic cluster.
    Processing: Currently returns six hard-coded ClusterResponse objects as a
                placeholder. These will be replaced by a live Firestore query
                against the pre-computed cluster documents produced by the Vertex
                AI embedding and HDBSCAN clustering pipeline in common.py.
    Ownership: API layer (api.py) — pending integration with the clustering
               pipeline (common.py:cluster_complaints /
               common.py:compile_semantic_averages).
    """
    # TODO: Replace with a Firestore query for pre-computed clusters produced by the
    # Vertex AI embedding + clustering pipeline. Each document: id, title,
    # representative_text (must be anonymised), count.
    return [
        ClusterResponse(
            id="delivery_delays",
            title="Delivery Delays",
            text="I ordered a package two weeks ago and it still hasn't arrived. The tracking hasn't updated in five days and customer service told me to wait.",
            count=847,
        ),
        ClusterResponse(
            id="product_quality",
            title="Product Quality",
            text="The item I received was clearly damaged in the box. The screen was cracked and the packaging looked like it had been opened before.",
            count=612,
        ),
        ClusterResponse(
            id="customer_service",
            title="Customer Service",
            text="I tried to reach support three times by phone and each time was put on hold for over 45 minutes before being disconnected.",
            count=534,
        ),
        ClusterResponse(
            id="billing_issues",
            title="Billing Issues",
            text="I was charged twice for the same order. Despite raising this a week ago, the duplicate charge has not been refunded.",
            count=389,
        ),
        ClusterResponse(
            id="return_process",
            title="Return Process",
            text="I requested a return three weeks ago and still haven't received the return label. The product is sitting in my hallway.",
            count=298,
        ),
        ClusterResponse(
            id="app_web_bugs",
            title="App & Website Bugs",
            text="The checkout process fails at the payment step every time I try on the mobile app. I have to use a different device just to complete an order.",
            count=271,
        ),
    ]


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


uvicorn.run(app, host="0.0.0.0", port=8080)
