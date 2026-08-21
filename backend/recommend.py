import json
from shared import db, RecommendationResponse
from google import genai
from google.genai import types

_reco_cache: dict = {"recs": None, "expires_at": 0.0}
_RECO_TTL = 3600  # 1 hour

_PROMPT = """\
You are a consumer-rights analyst. Given the complaint clusters below, produce \
exactly three recommendations. Return only a JSON object with keys "political", \
"focus", and "user_warning". Each value is an object with:
- "text": one short actionable headline (≤ 80 characters)
- "detail": one sentence of reasoning (≤ 200 characters)

Base each recommendation on the cluster sizes and descriptions. No extra keys, \
no conversational text, no markdown.

Clusters:
{clusters}"""


def build_recommendations() -> list[RecommendationResponse]:
    cluster_docs = list(db.collection("clusters").stream())
    rows = []
    for doc in cluster_docs:
        d = doc.to_dict()
        size = d.get("cluster_size")
        title = d.get("cluster_title")
        body = d.get("cluster_body")
        if title and body:
            rows.append(f"- {title} ({size} complaints): {body}")

    cluster_text = "\n".join(rows) if rows else "(no clusters available)"

    client = genai.Client(vertexai=True, project="recht-technisch", location="europe-west1")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=_PROMPT.format(clusters=cluster_text),
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    parsed = json.loads(response.text)

    return [
        RecommendationResponse(id=rec_id, **parsed[rec_id])
        for rec_id in ("political", "focus", "user_warning")
    ]
