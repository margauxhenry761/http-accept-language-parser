from __future__ import annotations

import dataclasses
import re
from typing import List, Optional


@dataclasses.dataclass(frozen=True)
class LanguageTag:
    """A single weighted entry parsed from an Accept-Language header.

    `language` is the normalised tag: trimmed, lowercase. Wildcards ('*')
    are preserved verbatim because they carry distinct matching semantics.

    `q` is the quality weight in the closed interval [0.0, 1.0]. It is
    stored as a float rather than a Decimal because callers almost always
    feed it back into numeric comparisons, and float avoids dragging a
    Decimal dependency through downstream code. Equality comparisons on
    q-values in tests should use the provided helpers rather than `==`,
    but the value itself is a plain float.

    `original` is the raw token as it appeared in the header (trimmed),
    preserved for diagnostics without re-parsing.
    """

    language: str
    q: float
    original: str


class ParseError(ValueError):
    """Raised only for values that cannot be interpreted as an Accept-Language header.

    A non-string input is a structural error and is rejected outright.
    Malformed *contents* of a string header (bad q-values, stray tokens) are
    recovered from per RFC guidance; this class is reserved for type-level
    failures so callers can distinguish "you gave me the wrong kind of thing"
    from "the header was messy but handled".
    """


# Matches a single language-range plus an optional ";q=..." parameter.
# We intentionally accept the q as a bare float rather than enforcing the
# RFC's 1-3 digit grammar, because real-world senders emit values like "0.3333"
# and rejecting them loses information we can trivially represent.
_RANGE_RE = re.compile(
    r"""
    ^
    \s*
    (?P<lang>[A-Za-z]{1,8}(?:-[A-Za-z0-9]{1,8})*|\*)  # language-range or wildcard
    \s*
    (?:;\s*q=(?P<q>-?[0-9]+(?:\.[0-9]+)?))?               # optional q-parameter
    \s*
    $
    """,
    re.VERBOSE,
)


def _parse_q(raw: Optional[str], original_token: str) -> float:
    """Convert a raw q-value string to a float, clamped to [0.0, 1.0].

    Missing q defaults to 1.0 per RFC 9110. Out-of-range values are clamped
    rather than rejected: browsers have historically emitted values like 1.2,
    and clamping preserves the caller's ability to match the tag.
    """

    if raw is None:
        return 1.0
    try:
        value = float(raw)
    except ValueError:
        # A syntactically broken q is unrecoverable for this token; treat it
        # as absent so the tag still participates with the default weight.
        return 1.0
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _parse_token(token: str) -> Optional[LanguageTag]:
    """Parse one comma-separated token, or return None if it is irrecoverable.

    Returns None (rather than raising) for malformed tokens so that a single
    bad entry does not destroy the entire header — this matches browser
    behaviour where one garbage tag is simply ignored.
    """

    match = _RANGE_RE.match(token)
    if match is None:
        return None
    lang = match.group("lang").lower()
    q = _parse_q(match.group("q"), token)
    return LanguageTag(language=lang, q=q, original=token.strip())


def parse_accept_language(header: object) -> List[LanguageTag]:
    """Parse an Accept-Language header value into a list of LanguageTag.

    The list is returned in the order tags appeared in the header, with their
    normalised q-values. Tags with q=0 are kept: they mean "not acceptable"
    and the caller needs that information to exclude them.

    Empty or whitespace-only headers return an empty list.

    Non-string input raises ParseError. We do not coerce bytes or numbers
    because Accept-Language is text and silent coercion hides bugs.
    """

    if not isinstance(header, str):
        raise ParseError(
            "Accept-Language header must be a string, got " + type(header).__name__
        )

    if header.strip() == "":
        return []

    tags: List[LanguageTag] = []
    for token in header.split(","):
        parsed = _parse_token(token)
        if parsed is not None:
            tags.append(parsed)

    return tags
