from typing import Literal
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

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
    # TODO: verify Firestore connectivity once data sources are connected
    return {"status": "ok"}


@app.get("/descriptive-stats", response_model=DescriptiveStatsResponse)
def descriptive_stats():
    # TODO: Replace with a Firestore aggregation query on the `complaints` collection.
    # Group by month, severity, channel, and retailer; compute counts and percentages.
    # Set `updated_at` to the Firestore query execution timestamp.
    return DescriptiveStatsResponse(
        updated_at="2026-08-20T07:00:00Z",
        total_complaints=8743,
        monthly_volume=[
            MonthlyVolume(period="2025-09", value=198),
            MonthlyVolume(period="2025-10", value=224),
            MonthlyVolume(period="2025-11", value=261),
            MonthlyVolume(period="2025-12", value=189),
            MonthlyVolume(period="2026-01", value=215),
            MonthlyVolume(period="2026-02", value=243),
            MonthlyVolume(period="2026-03", value=278),
            MonthlyVolume(period="2026-04", value=252),
            MonthlyVolume(period="2026-05", value=301),
            MonthlyVolume(period="2026-06", value=289),
            MonthlyVolume(period="2026-07", value=314),
            MonthlyVolume(period="2026-08", value=187),
        ],
        severity=[
            StatItem(id="critical", value=1573, percentage=18),
            StatItem(id="high",     value=2797, percentage=32),
            StatItem(id="medium",   value=3234, percentage=37),
            StatItem(id="low",      value=1139, percentage=13),
        ],
        channels=[
            StatItem(id="online",    value=5596, percentage=64),
            StatItem(id="in_person", value=3147, percentage=36),
        ],
        retailers=[
            StatItem(id="bol",        value=2185, percentage=25),
            StatItem(id="coolblue",   value=1836, percentage=21),
            StatItem(id="ah",         value=1574, percentage=18),
            StatItem(id="mediamarkt", value=1311, percentage=15),
            StatItem(id="hema",       value=1049, percentage=12),
            StatItem(id="overige",    value=788,  percentage=9),
        ],
    )


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
