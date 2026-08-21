import json
import time
import uvicorn
from google import genai
from typing import Literal
from pydantic import BaseModel
from google.genai import types
from google.cloud import firestore
from collections import defaultdict
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Recht Technisch API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


class MonthlyVolume(BaseModel):
    period: str  # "YYYY-MM"
    value: int


class StatItem(BaseModel):
    id: str
    value: int
    percentage: float


class DescriptiveStatsResponse(BaseModel):
    updated_at: str
    total_complaints: int
    monthly_volume: list[MonthlyVolume]
    severity: list[StatItem]
    channels: list[StatItem]
    retailers: list[StatItem]


class ClusterResponse(BaseModel):
    id: str
    title: str
    text: str
    count: int


class RecommendationResponse(BaseModel):
    id: Literal["political", "focus", "user_warning"]
    text: str
    detail: str


@app.get("/")
def main():
    return {"name": "Legal Loves Tech 2026", "message": "Hello World!"}


@app.get("/test_connection")
def test_connection():
    return {"password": "abhschda"}


@app.get("/health")
def health():
    try:
        db = firestore.Client(project="recht-technisch", database="complaints")
        first = next(iter(db.collection("complaints").limit(1).stream()), None)
        db_status = "ok" if first is not None else "empty"
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"status": "error", "db": str(exc)})
    return {"status": "ok", "db": db_status}


_stats_cache: dict = {"stats": None, "expires_at": 0.0}
_CACHE_TTL = 300  # seconds

_SEV_ORDER = ["critical", "high", "medium", "low"]
_CH_ORDER = ["online", "in_person"]

_CLASSIFY_PROMPT = """\
You are a consumer-complaint classifier. Classify each numbered complaint.
For each, choose exactly one value per field:
- severity: critical | high | medium | low
- channel: online | in_person
- retailer: extract the retailer name mentioned in the complaint and return it as a short, lowercase canonical identifier. Normalise spelling and branding variants to one form — e.g. "Aldi", "aldi", "Aldi Sud", "ALDI Nederland" all become "aldi"; "bol.com" and "Bol" become "bol"; "Albert Heijn" and "AH" become "ah". If no retailer is mentioned, return "unknown".

Rules:
- severity "critical" = serious harm (safety, fraud, large financial loss); "high" = significant inconvenience; "medium" = moderate issue; "low" = minor.
- channel "online" = purchased/contacted via website or app; "in_person" = visited a physical store.

Complaints:
{bodies}

Return a JSON array of objects in the same order, each with keys "severity", "channel", "retailer". No extra text."""


def _month_range(start: str, end: str) -> list[str]:
    sy, sm = int(start[:4]), int(start[5:7])
    ey, em = int(end[:4]), int(end[5:7])
    result = []
    y, m = sy, sm
    while (y, m) <= (ey, em):
        result.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return result


def _classify_batch(client, batch: list[dict]) -> list[dict]:

    bodies = "\n".join(
        f"[{i + 1}] {c['body'][:300]}" for i, c in enumerate(batch)
    )
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=_CLASSIFY_PROMPT.format(bodies=bodies),
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    parsed = json.loads(response.text)
    result = []
    for item in parsed:
        raw_retailer = str(item.get("retailer") or "unknown").lower().strip()
        result.append({
            "severity": item.get("severity", "low") if item.get("severity") in _SEV_ORDER else "low",
            "channel": item.get("channel", "online") if item.get("channel") in _CH_ORDER else "online",
            "retailer": raw_retailer or "unknown",
        })
    return result


def _build_stats() -> DescriptiveStatsResponse:
    db = firestore.Client(project="recht-technisch", database="complaints")
    docs = list(db.collection("complaints").stream())

    complaints = [
        {"date_created": d.get("date_created"), "body": d.get("body") or ""}
        for d in docs
    ]
    total = len(complaints)
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Monthly volume from date_created (no AI needed)
    month_counts: dict[str, int] = defaultdict(int)
    for c in complaints:
        dc = c["date_created"]
        if dc and len(dc) >= 7:
            month_counts[dc[:7]] += 1

    if month_counts:
        min_period = min(month_counts)
        cur_period = datetime.now(timezone.utc).strftime("%Y-%m")
        periods = _month_range(min_period, cur_period)
    else:
        periods = []
    monthly_volume = [MonthlyVolume(period=p, value=month_counts.get(p, 0)) for p in periods]

    # AI classification for severity / channel / retailer
    genai_client = genai.Client(vertexai=True, project="recht-technisch", location="europe-west1")
    classifications: list[dict] = []
    for i in range(0, total, 50):
        classifications.extend(_classify_batch(genai_client, complaints[i : i + 50]))

    sev_counts: dict[str, int] = defaultdict(int)
    ch_counts: dict[str, int] = defaultdict(int)
    ret_counts: dict[str, int] = defaultdict(int)
    for cls in classifications:
        sev_counts[cls["severity"]] += 1
        ch_counts[cls["channel"]] += 1
        ret_counts[cls["retailer"]] += 1

    safe_total = max(total, 1)

    def to_fixed_items(counts: dict, order: list[str]) -> list[StatItem]:
        return [
            StatItem(
                id=k,
                value=counts.get(k, 0),
                percentage=round(counts.get(k, 0) / safe_total * 100, 1),
            )
            for k in order
        ]

    retailers = [
        StatItem(id=k, value=v, percentage=round(v / safe_total * 100, 1))
        for k, v in sorted(ret_counts.items(), key=lambda x: -x[1])
    ]

    return DescriptiveStatsResponse(
        updated_at=now_utc,
        total_complaints=total,
        monthly_volume=monthly_volume,
        severity=to_fixed_items(sev_counts, _SEV_ORDER),
        channels=to_fixed_items(ch_counts, _CH_ORDER),
        retailers=retailers,
    )


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
