import re

# ── Existing patterns ─────────────────────────────────────────────────────────

_SFXL = r"(?:straße|strasse|str\.|gasse|weg|allee|platz|ring|damm|chaussee|promenade|ufer|steig|hof|graben)"
_SFXU = r"(?:Straße|Strasse|Str\.|Gasse|Weg|Allee|Platz|Ring|Damm|Chaussee|Promenade|Ufer|Steig|Hof|Graben)"
_NUM = r"\s+\d+[a-z]?"
_OPT_PLZ = r"(?:,?\s*\d{5}\s+[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*)?"

_ADDRESS_RE = re.compile(
    r"\b[A-ZÄÖÜ][a-zäöüß-]*" + _SFXL + _NUM + _OPT_PLZ
    + r"|\b[A-ZÄÖÜ][a-zäöüß-]+\s+" + _SFXU + _NUM + _OPT_PLZ
    + r"|\b\d{5}\s+[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*\b"
)

_PERSON_HONORIFIC_RE = re.compile(
    r"\b(?:Herr|Frau|Hr\.|Fr\.|Dr\.|Prof\.(?:\s+Dr\.)?)\s+"
    r"[A-ZÄÖÜ][a-zäöüß-]+(?:\s+[A-ZÄÖÜ][a-zäöüß-]+)?\b"
)

_PERSON_INTRO_RE = re.compile(
    r"(?:[Mm]ein(?:em|en)?\s+[Nn]amen?\s+(?:ist|lautet)|[Ii]ch\s+heiße)\s+"
    r"([A-ZÄÖÜ][a-zäöüß-]+(?:\s+[A-ZÄÖÜ][a-zäöüß-]+)?)\b"
)

# ── New patterns ──────────────────────────────────────────────────────────────

# URLs — matched before email so mailto: links don't split on @
_URL_RE = re.compile(
    r"https?://[^\s<>\"\')\]]+"
    r"|www\.[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}[^\s<>\"\')\]]*"
)

# Email addresses
_EMAIL_RE = re.compile(
    r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b"
)

# IBANs (DE / AT / CH; optional spaces between digit groups)
_IBAN_RE = re.compile(
    r"\bDE\d{2}[\s]?(?:\d{4}[\s]?){4}\d{2}\b"
    r"|\bAT\d{2}[\s]?(?:\d{4}[\s]?){4}\b"
    r"|\bCH\d{2}[\s]?(?:\d{4}[\s]?){3}\d\b",
    re.IGNORECASE,
)

# Credit card numbers: 4×4 digits separated by spaces or hyphens
_CC_RE = re.compile(r"\b\d{4}[\s\-]\d{4}[\s\-]\d{4}[\s\-]\d{4}\b")

# IPv4 addresses
_IP_RE = re.compile(
    r"(?<!\d)(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)(?!\d)"
)

# German phone numbers in the most common formats.
# (?<!\w) on 0-prefixed patterns prevents matching digits embedded in order numbers.
_PHONE_RE = re.compile(
    r"\+49[\s\-./]?\(?\d{2,5}\)?[\s\-./]?\d{3,7}(?:[\s\-./]?\d{1,5})?"
    r"|\(0\d{2,4}\)[\s\-.]?\d{4,11}"
    r"|(?<!\w)0\d{2,4}[/\s\-.]\d{3,12}"
    r"|(?<!\w)0[1-9]\d{8,10}(?!\d)"
)

# German licence plates: district code + letter group + digits (e.g. M AB 1234, HH-AB-1234E)
_PLATE_RE = re.compile(r"\b[A-ZÄÖÜ]{1,3}[\s\-][A-Z]{1,2}[\s\-]\d{1,4}[EH]?\b")

# Order / reference / invoice numbers: keyword followed by an alphanumeric identifier.
# \b anchors the keyword start; [\s:\.#]+ (one or more) requires an explicit separator
# between the keyword and the identifier to prevent partial-keyword false matches.
# Group 1 captures only the identifier so the keyword prefix stays in the text.
_ORDER_RE = re.compile(
    r"\b(?:bestell(?:ung)?(?:s?nummer|s?nr\.?)?|auftrags?(?:nummer|nr\.?)?"
    r"|referenz(?:nummer|nr\.?)?|rechnungs?(?:nummer|nr\.?)?"
    r"|kunden?(?:[\-\s]?nr\.?|nummer)?|transaktions?(?:nummer|nr\.?)?"
    r"|vorgangs?(?:nummer|nr\.?)?)[\s:\.#]+([A-Z0-9][A-Z0-9\-_/]{3,24})",
    re.IGNORECASE,
)

# ── Priority-ordered dispatch table ───────────────────────────────────────────
# Earlier entries win when spans overlap.
# Tuple: (compiled_regex, entity_kind, capturing_group_index | None)

_PATTERNS: list[tuple[re.Pattern, str, int | None]] = [
    (_URL_RE,              "url",         None),
    (_EMAIL_RE,            "email",       None),
    (_IBAN_RE,             "iban",        None),
    (_CC_RE,               "credit_card", None),
    (_IP_RE,               "ip",          None),
    (_PHONE_RE,            "phone",       None),
    (_PLATE_RE,            "plate",       None),
    (_ADDRESS_RE,          "address",     None),
    (_ORDER_RE,            "order",       1),
    (_PERSON_HONORIFIC_RE, "person",      None),
    (_PERSON_INTRO_RE,     "person",      1),
]

_KIND_LABELS: dict[str, str] = {
    "url":         "URL",
    "email":       "E-Mail-Adresse",
    "iban":        "IBAN",
    "credit_card": "Kartennummer",
    "ip":          "IP-Adresse",
    "phone":       "Telefonnummer",
    "plate":       "Kennzeichen",
    "address":     "Adresse",
    "order":       "Referenznummer",
    "person":      "Person",
}


def _find_spans(text: str) -> list[tuple[int, int, str, str]]:
    """Collect non-overlapping entity spans in priority order."""
    spans: list[tuple[int, int, str, str]] = []
    used: list[tuple[int, int]] = []

    def overlaps(s: int, e: int) -> bool:
        return any(s < eu and e > su for su, eu in used)

    for pattern, kind, group in _PATTERNS:
        for m in pattern.finditer(text):
            s = m.start(group) if group is not None else m.start()
            e = m.end(group)   if group is not None else m.end()
            matched = m.group(group) if group is not None else m.group()
            if not overlaps(s, e):
                spans.append((s, e, matched, kind))
                used.append((s, e))

    spans.sort(key=lambda x: x[0])
    return spans


def _apply_entities(
    text: str,
    spans: list[tuple[int, int, str, str]],
    entity_map: dict[str, str],
    counts: dict[str, int],
) -> str:
    parts: list[str] = []
    prev = 0
    for start, end, matched, kind in spans:
        parts.append(text[prev:start])
        if matched not in entity_map:
            counts[kind] = counts.get(kind, 0) + 1
            entity_map[matched] = f"{_KIND_LABELS[kind]} {counts[kind]}"
        parts.append(entity_map[matched])
        prev = end
    parts.append(text[prev:])
    return "".join(parts)


def anonymize(title: str, body: str) -> tuple[str, str]:
    """Replace PII entities with consistent labels across title and body."""
    entity_map: dict[str, str] = {}
    counts: dict[str, int] = {}
    anon_title = _apply_entities(title, _find_spans(title), entity_map, counts)
    anon_body  = _apply_entities(body,  _find_spans(body),  entity_map, counts)
    return anon_title, anon_body
