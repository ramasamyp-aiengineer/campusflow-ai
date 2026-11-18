import re

EMAIL = re.compile(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE = re.compile(r"(?<!\d)(?:\+91[\s\-]?)?[6-9]\d{9}(?!\d)")
ROLL = re.compile(
    r"\b(?:RA\d{10,}|\d{2}[A-Z]{2,6}\d{3,6}|[A-Z]{2,4}\d{2}[A-Z]{2,5}\d{3,5})\b",
    re.IGNORECASE,
)


def redact_pii(text: str) -> tuple[str, int, list[str]]:
    """Replace direct identifiers with stable anonymized tokens.

    Original values are not returned. Callers keep only counts and types.
    """
    types: list[str] = []
    count = 0

    def _swap(label: str, pattern: re.Pattern[str], source: str) -> str:
        nonlocal count

        def repl(_match: re.Match[str]) -> str:
            nonlocal count
            count += 1
            if label not in types:
                types.append(label)
            return f"[{label}_{count}]"

        return pattern.sub(repl, source)

    redacted = _swap("EMAIL", EMAIL, text)
    redacted = _swap("PHONE", PHONE, redacted)
    redacted = _swap("ROLL", ROLL, redacted)
    return redacted, count, types
