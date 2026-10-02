"""Rule-based checks for German patent claims (no AI involved).

The checks are heuristics: formal defects such as broken references are
detected reliably, article checks may produce occasional false positives.
User-facing messages are German because the tool targets German applications.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Severity = Literal["error", "warning", "info"]


@dataclass(frozen=True)
class Finding:
    severity: Severity
    claim: int  # 0 = applies to the whole claim set
    message: str


VAGUE_TERMS = (
    "schlechter",
    "besser",
    "signifikant",
    "erheblich",
    "ungefähr",
    "etwa",
    "möglichst",
    "vorzugsweise",
    "beispielsweise",
    "z. B.",
    "insbesondere",
    "relativ",
    "deutlich",
    "sofortig",
    "sofortige",
    "sofortigen",
)

CLAIM_START = re.compile(r"(?m)^\s*(\d+)\.\s+")
INTRODUCTION = re.compile(r"\b(?i:ein|eine|einen|einem|einer|eines)\s+([A-ZÄÖÜ][\w-]+)")
REFERENCE = re.compile(r"\b(?i:der|die|das|den|dem|des)\s+([A-ZÄÖÜ][\w-]+)")
NUMBER = re.compile(r"\d+(?:[.,]\d+)?\s*(?:°C|%|[a-zA-Zµ]{1,3}\b)?")
IGNORED_TERMS = frozenset({"anspruch", "ansprüche", "ansprüchen", "erfindung"})


# ---------- Parsing ----------


def split_claims(text: str) -> list[tuple[int, str]]:
    """Split a claim set into [(number, text), ...]."""
    matches = list(CLAIM_START.finditer(text))
    claims = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        claims.append((int(match.group(1)), " ".join(text[match.end() : end].split())))
    return claims


def parse_dependencies(number: int, text: str) -> list[int]:
    """Return the claim numbers a claim refers back to."""
    head = re.split(r"dadurch gekennzeichnet|wobei", text)[0]
    if re.search(r"nach einem der vorhergehenden Ansprüche", head):
        return list(range(1, number))
    match = re.search(r"nach einem der Ansprüche (\d+) bis (\d+)", head)
    if match:
        return list(range(int(match.group(1)), int(match.group(2)) + 1))
    match = re.search(
        r"nach (?:einem der |den )?Anspr(?:uch|üchen|üche) "
        r"((?:\d+(?:\s*,\s*|\s+oder\s+|\s+und\s+)?)+)",
        head,
    )
    if match:
        return [int(n) for n in re.findall(r"\d+", match.group(1))]
    return []


def _same_term(a: str, b: str) -> bool:
    """Compare terms tolerant to inflection (Sensor / Sensors)."""
    a, b = a.lower(), b.lower()
    if a == b:
        return True
    short, long = sorted((a, b), key=len)
    return long.startswith(short) and len(long) - len(short) <= 3


def _contains(term: str, terms: set[str]) -> bool:
    return any(_same_term(term, t) for t in terms)


# ---------- Individual checks ----------


def _check_numbering(numbers: list[int], findings: list[Finding]) -> None:
    if numbers != list(range(1, len(numbers) + 1)):
        findings.append(Finding("error", 0, f"Nummerierung nicht fortlaufend: {numbers}."))


def _check_dependencies(
    number: int, refs: list[int], numbers: list[int], findings: list[Finding]
) -> list[int]:
    """Report invalid back-references and return the valid ones."""
    if number == 1 and refs:
        findings.append(
            Finding("error", number, "Anspruch 1 darf sich auf keinen anderen Anspruch beziehen.")
        )
    valid = []
    for ref in refs:
        if ref not in numbers:
            findings.append(
                Finding("error", number, f"Rückbezug auf Anspruch {ref}, den es nicht gibt.")
            )
        elif ref >= number:
            findings.append(
                Finding(
                    "error",
                    number,
                    f"Rückbezug auf Anspruch {ref}. Rückbezüge sind nur auf "
                    "vorhergehende Ansprüche zulässig.",
                )
            )
        else:
            valid.append(ref)
    return valid


def _check_independent(number: int, text: str, findings: list[Finding]) -> None:
    values = [v.strip() for v in NUMBER.findall(text)]
    if values:
        findings.append(
            Finding(
                "warning",
                number,
                f"Enthält Zahlenwerte ({', '.join(values)}). Das engt den Schutz ein. "
                "Besser in Unteransprüche verschieben.",
            )
        )
    if "dadurch gekennzeichnet" not in text and "wobei" not in text:
        findings.append(
            Finding(
                "info",
                number,
                "Keine zweiteilige Form ('dadurch gekennzeichnet, dass' oder 'wobei') erkannt.",
            )
        )


def _check_vague_terms(number: int, text: str, findings: list[Finding]) -> None:
    for term in VAGUE_TERMS:
        if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text, re.IGNORECASE):
            findings.append(
                Finding(
                    "warning",
                    number,
                    f"Unklarer Begriff '{term}'. Prüfer verlangen bestimmte, "
                    "prüfbare Angaben (z. B. einen Grenzwert).",
                )
            )


def _inherited_terms(valid_refs: list[int], available: dict[int, set[str]]) -> set[str]:
    """Terms known in ALL referenced claims ("nach einem der Ansprüche ...")."""
    inherited: set[str] | None = None
    for ref in valid_refs:
        terms = available.get(ref, set())
        inherited = (
            set(terms) if inherited is None else {t for t in inherited if _contains(t, terms)}
        )
    return inherited or set()


def _check_articles(
    number: int,
    text: str,
    inherited: set[str],
    first_introduced: dict[str, int],
    reported_never: set[str],
    findings: list[Finding],
) -> set[str]:
    """Check definite/indefinite articles and return the terms known after this claim."""
    introductions = [(m.start(), m.group(1)) for m in INTRODUCTION.finditer(text)]

    # "ein X" although X is already known
    seen = set(inherited)
    for _, term in introductions:
        if _contains(term, seen):
            findings.append(
                Finding(
                    "warning",
                    number,
                    f"'{term}' wird erneut mit 'ein/eine' eingeführt, obwohl der Begriff "
                    "schon bekannt ist. Das wirkt, als wäre etwas anderes gemeint. "
                    "Hier 'der/die/das' verwenden.",
                )
            )
        seen.add(term)

    # "der X" although X was never introduced
    known = set(inherited)
    for match in REFERENCE.finditer(text):
        term = match.group(1)
        if term.lower() in IGNORED_TERMS:
            continue
        before = known | {t for pos, t in introductions if pos < match.start()}
        if _contains(term, before):
            continue

        origin = next((c for t, c in first_introduced.items() if _same_term(t, term)), None)
        if origin is not None:
            findings.append(
                Finding(
                    "error",
                    number,
                    f"'{match.group(0)}' verweist auf einen Begriff, der erst in Anspruch "
                    f"{origin} eingeführt wird und nicht in allen bezogenen Ansprüchen "
                    "vorkommt (Rückbezugsproblem).",
                )
            )
        elif not _contains(term, reported_never):
            findings.append(
                Finding(
                    "warning",
                    number,
                    f"'{match.group(0)}' wird nie mit 'ein/eine' eingeführt. Beim ersten "
                    f"Auftreten sollte es z. B. 'ein/eine {term}' heißen.",
                )
            )
            reported_never.add(term)
        known.add(term)  # report each term only once per chain

    return known | {t for _, t in introductions}


# ---------- Public API ----------


def check_claims(text: str) -> list[Finding]:
    """Check a claim set and return all findings."""
    findings: list[Finding] = []
    claims = split_claims(text)
    if not claims:
        if text.strip():
            findings.append(
                Finding(
                    "error",
                    0,
                    "Keine nummerierten Ansprüche erkannt. Jeder Anspruch muss in einer "
                    "neuen Zeile mit '1.', '2.' ... beginnen.",
                )
            )
        return findings

    numbers = [n for n, _ in claims]
    _check_numbering(numbers, findings)

    first_introduced: dict[str, int] = {}
    for number, body in claims:
        for match in INTRODUCTION.finditer(body):
            first_introduced.setdefault(match.group(1), number)

    available: dict[int, set[str]] = {}
    reported_never: set[str] = set()

    for number, body in claims:
        refs = parse_dependencies(number, body)
        valid = _check_dependencies(number, refs, numbers, findings)
        if not refs:
            _check_independent(number, body, findings)
        _check_vague_terms(number, body, findings)
        inherited = _inherited_terms(valid, available)
        available[number] = _check_articles(
            number, body, inherited, first_introduced, reported_never, findings
        )

    return findings
