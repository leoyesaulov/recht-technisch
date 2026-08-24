import json
from shared import db
from google import genai
from google.genai import types
from collections import defaultdict
from datetime import datetime, timezone
from shared import MonthlyVolumeResponse, ChartsStatsResponse, MonthlyVolume, StatItem

_monthly_cache: dict = {"data": None, "expires_at": 0.0}
_charts_cache: dict = {"data": None, "expires_at": 0.0}
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
    """
    Generate every calendar month between two periods, inclusive.

    Input:  start — a "YYYY-MM" string representing the first month to include.
            end   — a "YYYY-MM" string representing the last month to include.
    Returns: An ordered list of "YYYY-MM" strings covering every month from
             start through end, with no gaps. If start == end the list has one
             element.
    Processing: Pure arithmetic — parses year and month integers from the two
                strings, then increments a (year, month) counter in a loop,
                rolling the month back to 1 and incrementing the year when
                month exceeds 12. No I/O is performed.
    Ownership: stats.py — calendar utility used by build_monthly_volume to fill
               months that have zero complaints so the monthly volume series is
               contiguous.
    """
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
    """
    Classify a batch of complaints by severity, channel, and retailer using
    the Gemini LLM.

    Input:  client — an initialised google.genai.Client pointed at Vertex AI.
            batch  — a list of complaint dicts; each dict must contain a "body"
                     key with the raw complaint text. At most 50 items should
                     be passed to stay within the prompt token budget.
    Returns: A list of dicts in the same order as batch, each containing:
               "severity" — one of "critical", "high", "medium", "low"
               "channel"  — one of "online", "in_person"
               "retailer" — a lowercase canonical retailer identifier, or
                            "unknown" if no retailer is mentioned.
             Values outside the allowed sets are normalised to their respective
             defaults ("low", "online", "unknown").
    Processing: Formats the batch into a numbered list (truncating each body to
                300 characters), injects it into _CLASSIFY_PROMPT, and calls
                gemini-2.5-flash-lite with JSON response mode. The raw JSON
                array is parsed; each item's fields are validated against their
                allowed value sets before being appended to the result.
    Ownership: stats.py — LLM classification helper, called exclusively by
               build_charts_stats in batches of up to 50 complaints.
    """
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


def build_monthly_volume() -> MonthlyVolumeResponse:
    docs = list(db.collection("complaints").stream())
    total = len(docs)
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    month_counts: dict[str, int] = defaultdict(int)
    for d in docs:
        data = d.to_dict() or {}
        dc = data.get("date_created")
        if dc and len(dc) >= 7:
            month_counts[dc[:7]] += 1

    if month_counts:
        min_period = min(month_counts)
        cur_period = datetime.now(timezone.utc).strftime("%Y-%m")
        periods = _month_range(min_period, cur_period)
    else:
        periods = []
    monthly_volume = [MonthlyVolume(period=p, value=month_counts.get(p, 0)) for p in periods]

    return MonthlyVolumeResponse(
        updated_at=now_utc,
        total_complaints=total,
        monthly_volume=monthly_volume,
    )


def build_charts_stats() -> ChartsStatsResponse:
    docs = list(db.collection("complaints").stream())
    total = len(docs)
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    records: list[dict] = []
    unclassified_idx: list[int] = []

    for d in docs:
        data = d.to_dict() or {}
        sev = data.get("severity")
        ch = data.get("channel")
        ret = data.get("retailer")
        classified = sev in _SEV_ORDER and ch in _CH_ORDER and ret is not None
        records.append({
            "body": data.get("body") or "",
            "severity": sev if classified else None,
            "channel": ch if classified else None,
            "retailer": ret if classified else None,
            "ref": d.reference,
        })
        if not classified:
            unclassified_idx.append(len(records) - 1)

    if unclassified_idx:
        genai_client = genai.Client(vertexai=True, project="recht-technisch", location="europe-west1")
        bodies = [{"body": records[i]["body"]} for i in unclassified_idx]
        new_cls: list[dict] = []
        for i in range(0, len(bodies), 50):
            new_cls.extend(_classify_batch(genai_client, bodies[i : i + 50]))

        batch = db.batch()
        ops = 0
        for doc_idx, cls in zip(unclassified_idx, new_cls):
            records[doc_idx].update(cls)
            batch.update(records[doc_idx]["ref"], cls)
            ops += 1
            if ops == 500:
                batch.commit()
                batch = db.batch()
                ops = 0
        if ops:
            batch.commit()

    for r in records:
        if r["severity"] not in _SEV_ORDER:
            r["severity"] = "low"
        if r["channel"] not in _CH_ORDER:
            r["channel"] = "online"
        if not r["retailer"]:
            r["retailer"] = "unknown"

    sev_counts: dict[str, int] = defaultdict(int)
    ch_counts: dict[str, int] = defaultdict(int)
    ret_counts: dict[str, int] = defaultdict(int)
    for r in records:
        sev_counts[r["severity"]] += 1
        ch_counts[r["channel"]] += 1
        ret_counts[r["retailer"]] += 1

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

    return ChartsStatsResponse(
        updated_at=now_utc,
        severity=to_fixed_items(sev_counts, _SEV_ORDER),
        channels=to_fixed_items(ch_counts, _CH_ORDER),
        retailers=retailers,
    )
