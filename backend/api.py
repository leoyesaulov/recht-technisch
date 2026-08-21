import time
import uvicorn
from shared import db
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from shared import DescriptiveStatsResponse, ClusterResponse, RecommendationResponse
from stats import _build_stats, _stats_cache, _CACHE_TTL

app = FastAPI(title="Recht Technisch API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.get("/")
def main():
    return {"name": "Legal Loves Tech 2026", "message": "Hello World!"}


@app.get("/test_connection")
def test_connection():
    return {"password": "abhschda"}


@app.get("/health")
def health():
    try:
        first = next(iter(db.collection("complaints").limit(1).stream()), None)
        db_status = "ok" if first is not None else "empty"
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"status": "error", "db": str(exc)})
    return {"status": "ok", "db": db_status}


@app.get("/descriptive-stats", response_model=DescriptiveStatsResponse)
def descriptive_stats():
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
    # TODO: Replace with a call to the Vertex AI Agent Engine that analyses the current
    # Firestore complaint corpus and returns fresh recommendations.
    # Cache the result (TTL ~1 hour) to avoid hitting the LLM on every request.
    return [
        RecommendationResponse(
            id="political",
            text="Advocate for mandatory delivery SLA legislation",
            detail=(
                "Delivery delays account for the single largest complaint cluster (847 cases). "
                "Push for statutory maximum delivery windows with automatic consumer compensation, "
                "analogous to EU flight-delay rules."
            ),
        ),
        RecommendationResponse(
            id="focus",
            text="Prioritise delivery and billing complaints in consumer advice",
            detail=(
                "Delivery delays and billing issues together represent 37% of all complaints. "
                "Advisors should be briefed with a dedicated FAQ covering parcel tracking rights, "
                "double-charge dispute procedures, and escalation paths."
            ),
        ),
        RecommendationResponse(
            id="user_warning",
            text="Issue a public alert about recurring delivery and return failures",
            detail=(
                "Bol (25%) and Coolblue (21%) together account for 46% of logged complaints, "
                "with delivery and return failures dominating. A consumer-facing advisory during "
                "the current peak period is warranted."
            ),
        ),
    ]


uvicorn.run(app, host="0.0.0.0", port=8080)
