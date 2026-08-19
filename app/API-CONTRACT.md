# Dashboard API contract

Status: proposed

The dashboard reads three independent categories. The API returns the complete
available data set and stable IDs; the frontend owns layout and trims older
monthly data for display.

## Rules

- Base URL: the deployed backend URL, without a path suffix or trailing slash.
- Requests and responses use JSON.
- Dates use `YYYY-MM-DD`; timestamps use ISO 8601.
- IDs are stable strings. Cluster titles and text are supplied by the backend.
- Do not return presentation fields such as `label` or `icon`.
- Generated recommendation content is rendered as text, never as HTML.

## 1. Descriptive statistics

### `GET /descriptive-stats`

FastAPI route:

```python
@app.get("/descriptive-stats")
def descriptive_stats():
    ...
```

The response contains all available data. There are no period query
parameters; the frontend trims older monthly entries for display.

```json
{
  "updated_at": "2025-01-03T09:15:00Z",
  "total_complaints": 2736,
  "monthly_volume": [
    { "period": "2024-01", "value": 112 },
    { "period": "2024-02", "value": 138 },
    { "period": "2024-03", "value": 151 },
    { "period": "...", "value": 0 }
  ],
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

`monthly_volume` is chronological and includes months with zero complaints.
Percentages are numbers from `0` to `100` and may differ from `100` slightly
because of rounding.

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
    "id": "political-1",
    "category": "political",
    "text": "Advocate for mandatory delivery SLA legislation",
    "detail": "Push for clearer delivery commitments."
  },
  {
    "id": "focus-1",
    "category": "focus",
    "text": "Prioritize delivery complaints in consumer advice",
    "detail": "..."
  },
  {
    "id": "user-warning-1",
    "category": "user_warning",
    "text": "Warn users about delayed deliveries",
    "detail": "..."
  }
]
```

`category` is one of `political`, `focus`, or `user_warning`. `text` and
`detail` are generated content, not UI labels. Each category occurs once.

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

Raw complaint records and complainant personal data are out of scope.
