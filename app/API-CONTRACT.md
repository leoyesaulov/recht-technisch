# Dashboard API contract

Status: proposed

This is the small API for the hackathon dashboard. The dashboard is one page,
so the backend returns the page and the objects that appear on it in one
request. There is no separate endpoint for every chart or section.

## Rules

- Base URL: the deployed backend URL followed by `/api`.
- Requests and responses use JSON.
- Dates use `YYYY-MM-DD`; timestamps use ISO 8601.
- IDs are strings.
- A missing optional value is `null`.
- The frontend renders `text` values as text, never as HTML.

Authentication can be added by the deployment later. It is not part of the
hackathon contract.

## Get the page

### `GET /api/dashboard`

Returns everything needed for the dashboard. `from` and `to` are optional; if
omitted, the backend chooses the latest available complete period.

Example request:

```text
GET /api/dashboard?from=2024-01-01&to=2024-12-31
```

Example response:

```json
{
  "id": "complaint-dashboard",
  "title": "Complaint Intelligence",
  "period": { "from": "2024-01-01", "to": "2024-12-31" },
  "updated_at": "2025-01-03T09:15:00Z",
  "elements": [
    {
      "id": "total-complaints",
      "type": "metric",
      "title": "Total complaints",
      "value": 2736,
      "unit": "complaints"
    },
    {
      "id": "monthly-volume",
      "type": "chart",
      "title": "Monthly complaint volume",
      "chart": "line",
      "items": [
        { "label": "Jan", "value": 112 },
        { "label": "Feb", "value": 138 }
      ]
    },
    {
      "id": "severity",
      "type": "breakdown",
      "title": "Severity breakdown",
      "items": [
        { "id": "critical", "label": "Critical", "value": 492, "percentage": 18 },
        { "id": "high", "label": "High", "value": 876, "percentage": 32 }
      ]
    },
    {
      "id": "channels",
      "type": "breakdown",
      "title": "Channel split",
      "items": [
        { "id": "online", "label": "Online", "value": 1751, "percentage": 64 },
        { "id": "in-person", "label": "In-person", "value": 985, "percentage": 36 }
      ]
    },
    {
      "id": "top-retailers",
      "type": "list",
      "title": "Top retailers by volume",
      "items": [
        { "id": "retailco", "label": "RetailCo", "value": 848, "percentage": 31 }
      ]
    },
    {
      "id": "delivery-delays",
      "type": "cluster",
      "title": "Delivery Delays",
      "icon": "delivery",
      "count": 247,
      "change_percentage": 34,
      "trend": "rising",
      "quote": "My package hasn't arrived after 2 weeks..."
    },
    {
      "id": "recommendations",
      "type": "recommendations",
      "title": "Recommended actions",
      "items": [
        {
          "id": "rec-1",
          "category": "political",
          "title": "Advocate for mandatory delivery SLA legislation",
          "detail": "Push for clearer delivery commitments."
        }
      ]
    }
  ]
}
```

`elements` is the important part of the contract: each object represents one
thing placed on the page. The frontend can render an element by its `type` and
does not need to know how the backend calculated it.

### Element types

| Type | Required fields | Intended UI |
|---|---|---|
| `metric` | `title`, `value` | A number or stat card |
| `chart` | `title`, `chart`, `items` | A chart; `chart` is currently `line` |
| `breakdown` | `title`, `items` | A percentage breakdown |
| `list` | `title`, `items` | A ranked list |
| `cluster` | `title`, `count`, `trend` | A complaint cluster card |
| `recommendations` | `title`, `items` | Action cards grouped on the page |

Common item fields are `id`, `label`, and `value`. `percentage` is included
when the item is a share. Element-specific fields are allowed when they make
the element easier to render.

The backend should return all six dashboard clusters when available. No
pagination is needed for the hackathon. A cluster `trend` is one of
`rising`, `falling`, or `stable`.

## Health check

### `GET /api/health`

Returns:

```json
{ "status": "ok" }
```

## Errors

For a bad date range, return `400`:

```json
{ "error": "The end date must not be before the start date." }
```

For an unexpected backend failure, return `500`:

```json
{ "error": "Something went wrong." }
```

The frontend only needs to display the error message and offer a retry.

## Out of scope for now

- Separate overview, cluster, and recommendation endpoints.
- Pagination, filtering, refresh flags, and localization.
- Authentication and user roles.
- ETags, cache negotiation, request IDs, and model metadata.
- Raw complaint records or complainant personal data.

Keep these out of the contract until the app needs them. Additive fields are
fine; changing an element's `id` or `type` is a breaking change.
