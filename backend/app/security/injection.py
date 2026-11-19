import re

INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("ignore_instructions", re.compile(r"ignore\s+(all\s+)?((previous|prior|above)\s+)?instructions", re.I)),
    ("reveal_prompt", re.compile(r"(reveal|print|show|leak)\s+(the\s+)?(system|hidden)\s+prompt", re.I)),
    ("role_override", re.compile(r"you\s+are\s+now\s+", re.I)),
    ("jailbreak", re.compile(r"\b(jailbreak|do\s+anything\s+now|developer\s+mode)\b", re.I)),
    ("delimiter_break", re.compile(r"</?\s*student_submission\s*>", re.I)),
    ("policy_override", re.compile(r"(disable|bypass)\s+(the\s+)?(socratic|anti-?cheat|guardrail)", re.I)),
]


def detect_injection(text: str) -> list[str]:
    flags = [name for name, pattern in INJECTION_PATTERNS if pattern.search(text)]
    return flags


def neutralize_injection(text: str) -> str:
    cleaned = text.replace("<", "‹").replace(">", "›")
    cleaned = INJECTION_PATTERNS[0][1].sub("[neutralized instruction override]", cleaned)
    cleaned = INJECTION_PATTERNS[1][1].sub("[neutralized prompt request]", cleaned)
    cleaned = INJECTION_PATTERNS[3][1].sub("[neutralized]", cleaned)
    cleaned = INJECTION_PATTERNS[5][1].sub("[neutralized policy request]", cleaned)
    return cleaned
