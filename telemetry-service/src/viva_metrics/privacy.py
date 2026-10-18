"""Basic deterministic redaction, not full anonymization. Never logs input."""

import re
import unicodedata

VERSION = "basic-v1"
LIMIT = 4000
RULES = [
    (r"(?i)https?://[^\s<>]+", "[URL]"),
    (r"(?i)[\w.+-]+@[\w.-]+\.[a-z]{2,}", "[CORREO]"),
    (
        r"(?i)\b(?:bearer\s+|(?:api[_ -]?key|token|contrase[ñn]a|password)\s*[:=]\s*)[^\s,;]+",
        "[SECRETO]",
    ),
    (r"\b(?:sk-|AIza)[A-Za-z0-9_-]{16,}\b", "[SECRETO]"),
    (
        r"(?i)\b(?:c[eé]dula|documento|identificaci[oó]n|pasaporte|cc)\s*(?:es\s+|n[uú]mero\s+)?[:#=-]?\s*[\d. -]{4,}\d",
        "[DOCUMENTO]",
    ),
    (r"(?<!\w)\+?\d[\d(). -]{5,}\d(?!\w)", "[NÚMERO]"),
    (
        r"(?i)\b(?:me llamo|mi nombre es|soy el se[ñn]or|soy la se[ñn]ora)\s+[A-Za-zÀ-ÿ]+(?:\s+[A-ZÀ-Ý][a-zà-ÿ]+){0,3}",
        "[NOMBRE]",
    ),
]


def redact(text):
    # Normalize before matching; remove invisible format/control chars except whitespace.
    value = unicodedata.normalize("NFKC", text)
    value = "".join(c for c in value if c in "\n\t" or not unicodedata.category(c).startswith("C"))
    for pattern, replacement in RULES:
        value = re.sub(pattern, replacement, value)
    return value[:LIMIT], len(value) > LIMIT
