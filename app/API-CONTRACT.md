# Dashboard API contract

Status: proposed

The dashboard reads three independent categories. The API returns data and
stable IDs; the frontend owns all headings, labels, icons, and layout.

## Rules

- Base URL: the deployed backend URL followed by `/api`.
- Requests and responses use JSON.
- Dates use `YYYY-MM-DD`; timestamps use ISO 8601.
- IDs are stable strings. The frontend maps IDs to display text.
- Do not return presentation fields such as `title`, `label`, or `icon`.
- Generated recommendation content is rendered as text, never as HTML.

## 1. Descriptive statistics

### `GET /api/descriptive-stats`

Optional query parameters: `from` and `to`. If omitted, the backend chooses
the latest available complete period.

```json
{
  "period": { "from": "2024-01-01", "to": "2024-12-31" },
  "updated_at": "2025-01-03T09:15:00Z",
  "total_complaints": 2736,
  "monthly_volume": [
    { "period": "2024-01", "value": 112 },
    { "period": "2024-02", "value": 138 }
  ],
  "severity": [
    { "id": "critical", "value": 492, "percentage": 18 },
    { "id": "high", "value": 876, "percentage": 32 }
  ],
  "channels": [
    { "id": "online", "value": 1751, "percentage": 64 },
    { "id": "in_person", "value": 985, "percentage": 36 }
  ],
  "retailers": [
    { "id": "retailco", "value": 848, "percentage": 31 }
  ]
}
```

`monthly_volume` is chronological and includes months with zero complaints.
Percentages are numbers from `0` to `100` and may differ from `100` slightly
because of rounding.

## 2. Complaint clusters

### `GET /api/clusters`

Uses the same optional `from` and `to` query parameters. The response is a
simple array; pagination is not needed for this app.

```json
[
  {
    "id": "delivery_delays",
    "count": 247,
    "change_percentage": 34,
    "trend": "rising",
    "quote": "My package hasn't arrived after 2 weeks..."
  }
]
```

`trend` is `rising`, `falling`, or `stable`. `quote` is optional and must be
anonymized. The frontend maps each cluster ID to its display name and icon.

## 3. Recommendations

### `GET /api/recommendations`

Uses the same optional `from` and `to` query parameters.

```json
[
  {
    "id": "political-1",
    "category": "political",
    "text": "Advocate for mandatory delivery SLA legislation",
    "detail": "Push for clearer delivery commitments."
  }
]
```

`category` is one of `political`, `audit`, or `campaign`. `text` and `detail`
are generated content, not UI labels. The frontend owns the category headings.

## Errors

Each endpoint returns its own error. A bad date range returns `400`:

```json
{ "error": "The end date must not be before the start date." }
```

An unexpected failure returns `500`:

```json
{ "error": "Something went wrong." }
```

The frontend should show the affected section's error and keep the other two
sections usable.

## Health check

### `GET /api/health`

```json
{ "status": "ok" }
```

Raw complaint records and complainant personal data are out of scope.
