import json
from google import genai
from google.genai import types
from google.cloud import firestore
from collections import defaultdict
from datetime import datetime, timezone
from shared import DescriptiveStatsResponse, MonthlyVolume, StatItem

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