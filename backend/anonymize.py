import re

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


def _find_spans(text: str) -> list[tuple[int, int, str, str]]:
    """Collect non-overlapping entity spans; addresses take priority over names."""
    spans: list[tuple[int, int, str, str]] = []
    used: list[tuple[int, int]] = []

    def overlaps(s: int, e: int) -> bool:
        return any(s < eu and e > su for su, eu in used)

    for m in _ADDRESS_RE.finditer(text):
        spans.append((m.start(), m.end(), m.group(), "address"))
        used.append((m.start(), m.end()))

    for m in _PERSON_HONORIFIC_RE.finditer(text):
        if not overlaps(m.start(), m.end()):
            spans.append((m.start(), m.end(), m.group(), "person"))
            used.append((m.start(), m.end()))

    for m in _PERSON_INTRO_RE.finditer(text):
        s, e = m.start(1), m.end(1)
        if not overlaps(s, e):
            spans.append((s, e, m.group(1), "person"))
            used.append((s, e))

    spans.sort(key=lambda x: x[0])
    return spans


def _apply_entities(
    text: str,
    spans: list[tuple[int, int, str, str]],
    entity_map: dict[str, str],
    addr_count: list[int],
    person_count: list[int],
) -> str:
    parts: list[str] = []
    prev = 0
    for start, end, matched, kind in spans:
        parts.append(text[prev:start])
        if matched not in entity_map:
            if kind == "address":
                addr_count[0] += 1
                entity_map[matched] = f"Adresse {addr_count[0]}"
            else:
                person_count[0] += 1
                entity_map[matched] = f"Person {person_count[0]}"
        parts.append(entity_map[matched])
        prev = end
    parts.append(text[prev:])
    return "".join(parts)


def anonymize(title: str, body: str) -> tuple[str, str]:
    """Replace person names and addresses with consistent labels across title and body."""
    entity_map: dict[str, str] = {}
    addr_count = [0]
    person_count = [0]
    anon_title = _apply_entities(title, _find_spans(title), entity_map, addr_count, person_count)
    anon_body = _apply_entities(body, _find_spans(body), entity_map, addr_count, person_count)
    return anon_title, anon_body
