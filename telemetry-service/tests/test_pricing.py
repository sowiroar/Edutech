from decimal import Decimal

from viva_metrics.pricing import price, rates


def test_exact_decimal_cost_and_unknown():
    assert price(1250, Decimal("0.00000075")) == Decimal("0.00093750")
    assert price(1250, None) is None


def test_rates_have_provenance_and_no_unspecified_guess():
    assert len(rates()) == 9
    assert all(r["source_url"].startswith("https://ai.google.dev/") for r in rates())
    assert not any(r["modality"] == "unspecified" for r in rates())
