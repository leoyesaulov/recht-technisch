# Dashboard API contract


The dashboard reads three independent categories. The API returns the complete
available data set and stable IDs; the frontend owns layout and trims older
monthly data for display.

## Rules

- Base URL: the deployed backend URL, without a path suffix or trailing slash.
- Requests and responses use JSON.
- Stored and API dates use `YYYY-MM-DD`; timestamps use ISO 8601.
- CSV ingestion accepts `date_created` as either `YYYY-MM-DD` or
  `YYYY-MM-DD HH:MM:SS`. When a time is supplied, it is discarded before
  storage and API responses still return `YYYY-MM-DD`.
- IDs are stable strings. Cluster titles and text are supplied by the backend.
- Do not return presentation fields such as `label` or `icon`.
- Generated recommendation content is rendered as text, never as HTML.

## 1. Descriptive statistics

### `GET /descriptive-stats/monthly-volume`

This endpoint is accessed by the frontend to update the complaint volume chart within descriptive statistics module. This element should act as an attention grabber to mask long processing times for new complaints through an LLM.

FastAPI route:

```python
@app.get("/descriptive-stats/monthly-volume")
def monthly-volume():
    ...
```

```json
{
  "updated_at": "2025-01-03T09:15:00Z",
  "total_complaints": 2736,
  "monthly_volume": [
    { "period": "2024-01", "value": 112 },
    { "period": "2024-02", "value": 138 },
    { "period": "2024-03", "value": 151 },
    { "period": "...", "value": 0 }
  ]
}
```

The response contains all available data. There are no period query
parameters; the frontend trims older monthly entries for display.
`monthly_volume` is chronological and includes months with zero complaints.

### `GET /descriptive-stats/charts`

This endpoint is accessed by frontend to update the severity/retailer/channel charts within descriptive statistics module. The processing takes a long time for new complaints, so this data will arrive later than deterministic monthly volume.

FastAPI route:

```python
@app.get("/descriptive-stats/charts")
```

```json
{
  "updated_at": "2025-01-03T09:15:00Z",
  "severity": [
    { "id": "critical", "value": 492, "percentage": 18 },
    { "id": "high", "value": 876, "percentage": 32 },
    { "id": "medium", "value": 1014, "percentage": 37 },
    { "id": "low", "value": 354, "percentage": 13 }
  ],
  "channels": [
    { "id": "online", "value": 1751, "percentage": 64 },
    { "id": "in_person", "value": 985, "percentage": 36 }
  ],
  "retailers": [
    { "id": "retailco", "value": 848, "percentage": 31 },
    { "id": "...", "value": 0, "percentage": 0 }
  ]
}
```

Percentages are numbers from `0` to `100`; every complete distribution sums
to exactly `100` after rounding.

## 2. Complaint clusters

### `GET /clusters`

FastAPI route:

```python
@app.get("/clusters")
def clusters():
    ...
```

The response is a simple array containing all available clusters; pagination
and period query parameters are not needed for this app.

```json
[
  {
    "id": "delivery_delays",
    "title": "Delivery Delays",
    "text": "Complaints about packages arriving late or not arriving.",
    "count": 247
  }
]
```

`title` and `text` are supplied by the backend. `text` must be anonymized if
it contains a representative complaint.

### `GET /clusters/{cluster_id}/complaints`

Returns the newest complaints for the selected cluster. `cluster_id` is the
numeric string returned as a cluster's `id`. The response contains at most 50
items, ordered newest first. There are no query parameters.

```json
[
  {
    "id": "172",
    "date_created": "2025-01-03",
    "body": "Meine Bestellung ist weiterhin nicht eingetroffen."
  }
]
```

`date_created` always uses `YYYY-MM-DD`, even if ingestion received
`YYYY-MM-DD HH:MM:SS`; the time is not stored. The frontend formats the date
for display. The complaint body is plain text and must never be rendered as
HTML.

## 3. Recommendations

### `GET /recommendations`

FastAPI route:

```python
@app.get("/recommendations")
def recommendations():
    ...
```

The response contains exactly three recommendations: one each for `political`,
`focus`, and `user_warning`. There are no nested sub-suggestions.

```json
[
  {
    "id": "political",
    "text": "Advocate for mandatory delivery SLA legislation",
    "detail": "Push for clearer delivery commitments."
  },
  {
    "id": "focus",
    "text": "Prioritize delivery complaints in consumer advice",
    "detail": "..."
  },
  {
    "id": "user_warning",
    "text": "Warn users about delayed deliveries",
    "detail": "..."
  }
]
```

`id` is one of `political`, `focus`, or `user_warning`; each occurs exactly
once. `text` and `detail` are generated content, not UI labels.

## Errors

Each endpoint returns its own error. Invalid request data returns `400`:

```json
{ "error": "The request data is invalid." }
```

An unexpected failure returns `500`:

```json
{ "error": "Something went wrong." }
```

The frontend should show the affected section's error and keep the other two
sections usable.

## 4. Data ingestion

### `POST /ingestion`

Uploads a `multipart/form-data` body with one `file` field. The file must be a
UTF-8 CSV no larger than 10 MiB, with exactly these columns in this order:

```csv
date_created,complaint
2026-08-24,"The delivery arrived late."
```

`date_created` must be a valid `YYYY-MM-DD` date and `complaint` must be
non-empty. The API validates the full file before it writes records. A
successful upload returns `201`:

```json
{ "inserted": 1 }
```

Invalid files return `400` with `{ "error": "..." }`; unexpected ingestion
failures return `500`.

## Health check

### `GET /health`

FastAPI route:

```python
@app.get("/health")
def health():
    ...
```

```json
{ "status": "ok" }
```

The cluster-detail endpoint exposes only a complaint's stable ID, creation
date, and plain-text body; complainant personal data is out of scope.
