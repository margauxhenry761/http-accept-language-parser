# HTTP Accept Language Parser

Parses an HTTP `Accept-Language` header into a list of `(language, q, original)` tuples, handling q-values, wildcards, and malformed entries. Pure Python, standard library only.

## Usage

```python
from http_accept_language_parser import parse_accept_language, LanguageTag

tags: list[LanguageTag] = parse_accept_language("en-GB, en;q=0.9, fr;q=0.5, *;q=0.1")
for tag in tags:
    print(tag.language, tag.q, tag.original)
```

`parse_accept_language(header: str) -> list[LanguageTag]` — returns tags in header order. Empty/whitespace-only input returns `[]`. Non-string input raises `ParseError`.

`LanguageTag` is a frozen dataclass with fields `language` (str, lowercased; wildcards kept as `*`), `q` (float in `[0.0, 1.0]`), and `original` (str, the raw token as received).

## Why

Real-world `Accept-Language` headers are messy: browsers emit q-values greater than 1.0, stray tokens appear between valid ones, and whitespace is inconsistent. This library does the boring work of normalising that into a clean list of weighted tags without rejecting the whole header over one bad entry. It is deliberately small and dependency-free because header parsing should not pull in a framework.

## Edge cases

- Malformed tokens are silently skipped, not raised — a single garbage entry does not invalidate the rest of the header. This mirrors browser behaviour but means you cannot detect that a token was rejected; if you need that, this is not the right library.
- q-values outside `[0.0, 1.0]` are clamped, not rejected.
- Tags are **not** deduplicated or sorted by q. If a caller needs the RFC's precedence ordering, sort the returned list yourself.

## Design notes

The window stores values eagerly rather than keeping running aggregates. Running
sums drift with floating point over long streams, and recomputing from a small
buffer is cheap enough that the drift is not worth the speed.

