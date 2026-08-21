import json
from shared import db
from google import genai
from google.genai import types
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
    Ownership: stats.py — calendar utility used by _build_stats to fill months
               that have zero complaints so the monthly volume series is
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
               _build_stats in batches of up to 50 complaints.
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


def _build_stats() -> DescriptiveStatsResponse:
    """
    Build the full descriptive statistics response from the complaints corpus.

    Input:  None — reads from the module-level Firestore client (db) imported
            from shared.py.
    Returns: A DescriptiveStatsResponse containing:
               updated_at      — ISO 8601 UTC timestamp of this computation
               total_complaints — total number of complaint documents
               monthly_volume  — contiguous list of MonthlyVolume objects from
                                 the earliest complaint month to the present
               severity        — list of StatItems for critical/high/medium/low
               channels        — list of StatItems for online/in_person
               retailers       — list of StatItems sorted by complaint count
                                 descending
    Processing:
      1. Streams all documents from the Firestore "complaints" collection.
      2. Aggregates monthly complaint counts from each document's date_created
         field (YYYY-MM-DD prefix); fills gaps to the current month using
         _month_range so the series is contiguous.
      3. Sends complaint bodies to the Gemini LLM in batches of 50 via
         _classify_batch to obtain severity, channel, and retailer labels.
      4. Tallies per-category counts; computes percentages against total
         (floored to 1 to avoid division by zero).
      5. Assembles and returns the DescriptiveStatsResponse.
    Ownership: stats.py — primary orchestrator for statistics computation;
               called by api.py:descriptive_stats on each cache miss.
    """
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
        """
        Build a fixed-order list of StatItems from a count dict.

        Input:  counts — dict mapping category id strings to integer complaint
                         counts; keys absent from counts are treated as zero.
                order  — list of category id strings defining output order;
                         every id in order will appear in the result regardless
                         of whether it has a non-zero count.
        Returns: A list of StatItem objects in the same order as `order`, each
                 carrying id, value (raw count), and percentage (rounded to one
                 decimal place) computed against the enclosing _build_stats
                 function's safe_total.
        Processing: Simple list comprehension; looks up each id in counts,
                    defaulting to 0 for missing keys. Percentage is
                    count / safe_total * 100. No I/O.
        Ownership: stats.py — inner helper of _build_stats; used for the
                   severity and channel breakdowns where the set of categories
                   is fixed and must always be present in the response.
        """
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