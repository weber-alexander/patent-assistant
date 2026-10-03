"""Tests for the rule-based claim checker."""

import pytest

from patent_assistant.claim_checker import check_claims, parse_dependencies

CLEAN_CLAIMS = """1. Messsystem mit einem Sensor und einer Steuereinheit, dadurch gekennzeichnet, dass die Steuereinheit eine Abtastrate erhöht, wenn ein Signal-Rausch-Verhältnis einen Schwellenwert unterschreitet.
2. Messsystem nach Anspruch 1, dadurch gekennzeichnet, dass die Steuereinheit die Abtastrate verdoppelt.
3. Messsystem nach Anspruch 1 oder 2, dadurch gekennzeichnet, dass der Schwellenwert durch einen Benutzer einstellbar ist."""


def messages(findings, severity=None):
    return [f.message for f in findings if severity is None or f.severity == severity]


def test_clean_claim_set_has_no_findings():
    assert check_claims(CLEAN_CLAIMS) == []


def test_empty_text_has_no_findings():
    assert check_claims("") == []


def test_text_without_numbered_claims_is_an_error():
    findings = check_claims("Messsystem mit einem Sensor.")
    assert len(findings) == 1
    assert findings[0].severity == "error"


def test_numbering_gap_is_an_error():
    text = "1. Messsystem mit einem Sensor, wobei der Sensor misst.\n3. Messsystem nach Anspruch 1, wobei der Sensor kalibriert ist."
    assert any("Nummerierung" in m for m in messages(check_claims(text), "error"))


def test_reference_to_missing_claim_is_an_error():
    text = "1. Messsystem mit einem Sensor, wobei der Sensor misst.\n2. Messsystem nach Anspruch 7, wobei der Sensor kalibriert ist."
    findings = check_claims(text)
    assert any(f.claim == 2 and "nicht gibt" in f.message for f in findings)


def test_term_introduced_in_sibling_claim_is_a_reference_problem():
    text = """1. Messsystem mit einem Sensor, dadurch gekennzeichnet, dass der Sensor eine Abtastrate erhöht.
2. Messsystem nach Anspruch 1, dadurch gekennzeichnet, dass ein Schwellenwert vorgesehen ist.
3. Messsystem nach Anspruch 1, dadurch gekennzeichnet, dass der Schwellenwert einstellbar ist."""
    findings = check_claims(text)
    assert any(f.claim == 3 and "Rückbezugsproblem" in f.message for f in findings)


def test_term_never_introduced_is_a_warning():
    text = (
        "1. Messsystem mit einem Sensor, dadurch gekennzeichnet, dass die Abtastrate erhöht wird."
    )
    assert any("'die Abtastrate'" in m for m in messages(check_claims(text), "warning"))


def test_repeated_introduction_is_a_warning():
    text = """1. Messsystem mit einem Sensor, dadurch gekennzeichnet, dass der Sensor einen Schwellenwert nutzt.
2. Messsystem nach Anspruch 1, dadurch gekennzeichnet, dass ein Schwellenwert einstellbar ist."""
    assert any("erneut" in m for m in messages(check_claims(text), "warning"))


def test_numbers_in_independent_claim_are_a_warning():
    text = (
        "1. Messsystem mit einem Sensor, dadurch gekennzeichnet, dass der Sensor alle 100 ms misst."
    )
    assert any("Zahlenwerte" in m for m in messages(check_claims(text), "warning"))


def test_claim_reference_number_is_not_reported_as_value():
    """Regression: 'nach Anspruch 1' must not count as a numeric value."""
    text = (
        CLEAN_CLAIMS
        + "\n4. Messsystem nach Anspruch 3, dadurch gekennzeichnet, dass die Abtastrate höchstens 10 kHz beträgt."
    )
    assert not any("Zahlenwerte" in m for m in messages(check_claims(text)))


@pytest.mark.parametrize("term", ["schlechter", "etwa", "z. B."])
def test_vague_terms_are_detected(term):
    """Regression: 'z. B.' was not detected because of the trailing dot."""
    text = f"1. Messsystem mit einem Sensor, dadurch gekennzeichnet, dass der Sensor {term} misst."
    assert any(f"'{term}'" in m for m in messages(check_claims(text), "warning"))


@pytest.mark.parametrize(
    ("number", "text", "expected"),
    [
        (2, "Messsystem nach Anspruch 1, wobei", [1]),
        (3, "Messsystem nach Anspruch 1 oder 2, wobei", [1, 2]),
        (4, "Messsystem nach einem der vorhergehenden Ansprüche, wobei", [1, 2, 3]),
        (5, "Messsystem nach einem der Ansprüche 2 bis 4, wobei", [2, 3, 4]),
        (1, "Messsystem mit einem Sensor, wobei", []),
    ],
)
def test_parse_dependencies(number, text, expected):
    assert parse_dependencies(number, text) == expected
