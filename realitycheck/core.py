"""Deterministic, annotation-based summaries of synthetic listing evidence.

This module does not fetch sources, infer claims from text, or verify annotations.
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

TOPICS = ("night_noise", "step_free_entry", "public_transit", "family_sleep")
SOURCE_TYPES = ("review", "host_disclosure", "map")
STANCES = ("supports", "concern", "unclear")
MAX_INPUT_BYTES = 2_000_000
MAX_SOURCES = 200
MAX_ASSERTIONS_PER_SOURCE = 12
MAX_ID_CHARS = 200
MAX_QUESTION_CHARS = 2_000
MAX_TEXT_CHARS = 8_000
MAX_EXCERPT_CHARS = 500
_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")

TOPIC_TITLES = {
    "night_noise": "Night noise",
    "step_free_entry": "Step-free entry",
    "public_transit": "Public transit",
    "family_sleep": "Family sleep",
}
HOST_QUESTIONS = {
    "night_noise": "What nighttime noise, if any, has been reported, and when does it occur?",
    "step_free_entry": "What is the complete route from the street to the sleeping area, including any steps, thresholds, lifts and backup access?",
    "public_transit": "Which stops, routes, frequencies and late-night services are available on our travel dates?",
    "family_sleep": "What are the sleeping arrangements and room separation, and what sleep disruptions have families reported?",
}


class InputError(ValueError):
    """An input document is not valid for the supported schema."""


def _keys(obj: Any, required: set[str], path: str) -> None:
    if not isinstance(obj, dict):
        raise InputError(f"{path} must be an object")
    missing = required - obj.keys()
    extra = obj.keys() - required
    if missing:
        raise InputError(f"{path} is missing required field(s): {', '.join(sorted(missing))}")
    if extra:
        # repr prevents ambiguous error messages when field names contain controls.
        raise InputError(f"{path} has unexpected field(s): {', '.join(sorted(repr(k) for k in extra))}")


def _string(value: Any, path: str, maximum: int, *, nonempty: bool = True) -> str:
    if not isinstance(value, str):
        raise InputError(f"{path} must be a string")
    if nonempty and not value.strip():
        raise InputError(f"{path} must be nonempty")
    if len(value) > maximum:
        raise InputError(f"{path} exceeds {maximum} characters")
    return value


def _date(value: Any, path: str) -> date:
    if not isinstance(value, str) or not _DATE_RE.fullmatch(value):
        raise InputError(f"{path} must be a date in YYYY-MM-DD format")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise InputError(f"{path} must be a valid date in YYYY-MM-DD format") from exc


def _enum(value: Any, allowed: tuple[str, ...], path: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise InputError(f"{path} must be one of: {', '.join(allowed)}")
    return value


def validate_data(data: Any) -> dict[str, Any]:
    """Validate the entire schema; return the original object if it is valid.

    Duplicate topic selections, IDs (after trimming outer whitespace), and
    identical assertion pairs are rejected. Different stances for the same
    topic within one source are allowed and are not treated as independent.
    """
    _keys(data, {"listing_id", "as_of", "question", "topics", "sources"}, "input")
    _string(data["listing_id"], "listing_id", MAX_ID_CHARS)
    _date(data["as_of"], "as_of")
    _string(data["question"], "question", MAX_QUESTION_CHARS)
    topics = data["topics"]
    if not isinstance(topics, list) or not topics:
        raise InputError("topics must be a nonempty array")
    if len(topics) > len(TOPICS):
        raise InputError(f"topics may contain at most {len(TOPICS)} items")
    seen_topics: set[str] = set()
    for i, topic in enumerate(topics):
        _enum(topic, TOPICS, f"topics[{i}]")
        if topic in seen_topics:
            raise InputError(f"topics[{i}] duplicates an earlier topic")
        seen_topics.add(topic)
    sources = data["sources"]
    if not isinstance(sources, list):
        raise InputError("sources must be an array")
    if len(sources) > MAX_SOURCES:
        raise InputError(f"sources may contain at most {MAX_SOURCES} items")
    seen_ids: set[str] = set()
    for i, source in enumerate(sources):
        path = f"sources[{i}]"
        _keys(source, {"id", "source_type", "date", "text", "assertions"}, path)
        source_id = _string(source["id"], f"{path}.id", MAX_ID_CHARS)
        if source_id.strip() in seen_ids:
            raise InputError(f"{path}.id duplicates an earlier source ID")
        seen_ids.add(source_id.strip())
        _enum(source["source_type"], SOURCE_TYPES, f"{path}.source_type")
        if source["date"] is not None:
            _date(source["date"], f"{path}.date")
        _string(source["text"], f"{path}.text", MAX_TEXT_CHARS, nonempty=False)
        assertions = source["assertions"]
        if not isinstance(assertions, list):
            raise InputError(f"{path}.assertions must be an array")
        if len(assertions) > MAX_ASSERTIONS_PER_SOURCE:
            raise InputError(f"{path}.assertions may contain at most {MAX_ASSERTIONS_PER_SOURCE} items")
        seen_assertions: set[tuple[str, str]] = set()
        for j, assertion in enumerate(assertions):
            apath = f"{path}.assertions[{j}]"
            _keys(assertion, {"topic", "stance"}, apath)
            topic = _enum(assertion["topic"], TOPICS, f"{apath}.topic")
            stance = _enum(assertion["stance"], STANCES, f"{apath}.stance")
            pair = (topic, stance)
            if pair in seen_assertions:
                raise InputError(f"{apath} duplicates an earlier assertion in this source")
            seen_assertions.add(pair)
    return data


def _no_duplicate_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InputError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def _invalid_constant(value: str) -> Any:
    raise InputError(f"invalid JSON constant: {value}")


def _invalid_number(_value: str) -> Any:
    # The schema has no numeric fields. This also avoids converting arbitrarily
    # long numeric tokens before they can fail type validation.
    raise InputError("numeric JSON values are not supported by this schema")


def load_input(path: str | Path) -> dict[str, Any]:
    """Read a bounded UTF-8 JSON file and validate it, including duplicate keys."""
    with open(path, "rb") as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise InputError(f"input exceeds {MAX_INPUT_BYTES} bytes")
    try:
        data = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_no_duplicate_object_keys,
            parse_constant=_invalid_constant,
            parse_int=_invalid_number,
            parse_float=_invalid_number,
        )
    except UnicodeDecodeError as exc:
        raise InputError("input must be valid UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise InputError(f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    except RecursionError as exc:
        raise InputError("input JSON is nested too deeply") from exc
    return validate_data(data)


def escape_markdown(value: str) -> str:
    """Encode untrusted text as literal Markdown, not syntax or active links.

    ASCII punctuation is entity-encoded (except harmless in-line hyphens).
    A zero-width space after dots, colons and at-signs prevents linkifiers
    which run *after* entity decoding from turning visible text into links.
    All input control, format, surrogate and line-separator codepoints are
    displayed as literal Unicode escapes, never emitted as controls.
    """
    out: list[str] = []
    for ch in value:
        cp = ord(ch)
        category = unicodedata.category(ch)
        if category in ("Cc", "Cf", "Cs", "Zl", "Zp"):
            digits = f"{cp:04X}" if cp <= 0xFFFF else f"{cp:08X}"
            prefix = "u" if cp <= 0xFFFF else "U"
            out.append(f"&#92;{prefix}{digits}")
        elif 33 <= cp <= 126 and not ch.isalnum() and ch != "-":
            out.append(f"&#{cp};")
            if ch in ".:@":
                out.append("&#8203;")
        else:
            out.append(ch)
    return "".join(out)


def _timing(value: str | None, as_of: date) -> tuple[str, str]:
    if value is None:
        return "unknown", "unknown date — not current evidence"
    delta = (as_of - date.fromisoformat(value)).days
    if delta < 0:
        return "future", f"future ({-delta} days after as-of) — not current evidence"
    if delta > 365:
        return "stale", f"stale ({delta} days before as-of) — not current evidence"
    return "current", f"current ({delta} days before as-of)"


def _excerpt(text: str) -> str:
    if not _has_readable_text(text):
        return "(empty source text)"
    rendered = escape_markdown(text[:MAX_EXCERPT_CHARS])
    if len(text) > MAX_EXCERPT_CHARS:
        rendered += " [excerpt truncated]"
    return rendered


def _has_readable_text(text: str) -> bool:
    """Require at least one non-whitespace, non-control source character."""
    return any(not ch.isspace() and not unicodedata.category(ch).startswith("C") for ch in text)


def _source_lines(source: dict[str, Any], as_of: date, assertions: list[dict[str, str]]) -> list[str]:
    timing = _timing(source["date"], as_of)[1]
    date_display = source["date"] if source["date"] is not None else "unknown"
    type_display = source["source_type"]
    if type_display == "map":
        type_display += " (synthetic/manual; not independently verified)"
    labels = ", ".join(f"{a['topic']}: {a['stance']}" for a in assertions) if assertions else "none"
    return [
        f"- **Source ID:** {escape_markdown(source['id'])}  ",
        f"  **Type:** {type_display} | **Date:** {date_display} | **Timing:** {timing}  ",
        f"  **Manual annotations shown:** {labels}  ",
        f"  **Text status:** {'supplied; not verified' if _has_readable_text(source['text']) else 'missing or unreadable — annotations not used in status'}  ",
        f"  **Text excerpt:** {_excerpt(source['text'])}",
    ]


def render_report(data: Any) -> str:
    """Render a validated, deterministic Markdown report; performs validation."""
    data = validate_data(data)
    as_of = date.fromisoformat(data["as_of"])
    topics = data["topics"]
    sources = data["sources"]
    requested = set(topics)
    lines = [
        "# Pre-Arrival Vibe & Reality Check",
        "",
        f"**Listing ID:** {escape_markdown(data['listing_id'])}  ",
        f"**As of:** {data['as_of']}  ",
        f"**Question:** {escape_markdown(data['question'])}",
        "",
        "**Synthetic inputs only.** These are user-supplied, manual annotations; "
        "they can be wrong and are not extracted or independently verified. "
        "Map records are supplied as fabricated/manual data, not verified measurements. "
        "No links are fetched, no account is accessed, no AI/LLM is used, and no one is contacted.",
        "",
        "This is not a guarantee, score, automated decision, or prediction of safety, "
        "stair-free access, travel conditions, or suitability. General reviews and "
        "map proximity do not prove quiet, safety, accessibility, or family suitability. "
        "Missing evidence is not negative evidence.",
        "",
        "Sources are displayed in input order, not assumed to be chronological. "
        "A dated assertion is current only when its date is on or before the as-of "
        "date and no more than 365 days earlier; stale, unknown-date, and future "
        "records are shown but excluded from status. Sources with missing or unreadable "
        "text are also shown but excluded from status. The 365-day rule is a prototype "
        "heuristic, not proof of freshness.",
        "",
        f"**Distinct sources in input:** {len(sources)}",
    ]
    for topic in topics:
        relevant = [s for s in sources if any(a["topic"] == topic for a in s["assertions"])]
        current = [s for s in relevant if _timing(s["date"], as_of)[0] == "current" and _has_readable_text(s["text"])]
        by_stance: dict[str, list[str]] = {stance: [] for stance in STANCES}
        for source in current:
            for stance in STANCES:
                if any(a["topic"] == topic and a["stance"] == stance for a in source["assertions"]):
                    by_stance[stance].append(source["id"])
        if by_stance["supports"] and by_stance["concern"]:
            status = "CONFLICTING REPORTS"
        elif by_stance["concern"]:
            status = "CONCERN REPORTED"
        elif by_stance["supports"]:
            status = "REPORTED SUPPORT — NOT VERIFIED"
        else:
            status = "INSUFFICIENT EVIDENCE"
        basis = []
        for stance in STANCES:
            ids = by_stance[stance]
            citation = ", ".join(f"ID {escape_markdown(sid)}" for sid in ids) if ids else "none"
            basis.append(f"{stance}: {citation}")
        lines += [
            "",
            f"## {TOPIC_TITLES[topic]}",
            "",
            f"**Status:** {status}  ",
            f"**Status basis (current annotations only):** {'; '.join(basis)}  ",
            f"**Distinct relevant sources:** {len(relevant)}; **current distinct sources:** {len(current)}.",
            "",
        ]
        if relevant:
            for source in relevant:
                annotations = [a for a in source["assertions"] if a["topic"] == topic]
                lines.extend(_source_lines(source, as_of, annotations))
        else:
            lines.append("No source has a manual assertion for this topic; absence is not a negative finding.")
        lines += ["", f"**Question to ask the host (not sent):** {HOST_QUESTIONS[topic]}"]
    lines += ["", "## Unrequested and otherwise unmatched sources", ""]
    unmatched = [s for s in sources if not any(a["topic"] in requested for a in s["assertions"])]
    if unmatched:
        lines.append("These sources did not contribute to any requested-topic status:")
        lines.append("")
        for source in unmatched:
            lines.extend(_source_lines(source, as_of, source["assertions"]))
    else:
        lines.append("None. Every supplied source has at least one requested-topic assertion.")
    partially_omitted = [s for s in sources if any(a["topic"] in requested for a in s["assertions"]) and any(a["topic"] not in requested for a in s["assertions"])]
    lines += ["", "**Unrequested annotations on otherwise relevant sources:**"]
    if partially_omitted:
        for source in partially_omitted:
            other = [a for a in source["assertions"] if a["topic"] not in requested]
            labels = ", ".join(f"{a['topic']}: {a['stance']}" for a in other)
            lines.append(f"- ID {escape_markdown(source['id'])}: {labels} (not used in status)")
    else:
        lines.append("None.")
    return "\n".join(lines) + "\n"
