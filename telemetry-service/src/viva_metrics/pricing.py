"""Paid standard list estimates, observed 2026-10-17; never an invoice."""

from decimal import Decimal


def price(quantity, usd_per_unit):
    return None if usd_per_unit is None else Decimal(str(quantity)) * usd_per_unit


def rates():
    live = [
        dict(
            id=f"google-gemini38-20261017-{direction}-{modality}",
            provider="google",
            model="gemini-3.8-live",
            unit="tokens",
            direction=direction,
            modality=modality,
            cached=False,
            effective_at="2026-10-17T00:00:00+00:00",
            usd_per_unit=Decimal(value) / Decimal(1_000_000),
            source_url="https://ai.google.dev/gemini-api/docs/pricing",
        )
        for direction, modality, value in [
            ("input", "text", "0.75"),
            ("input", "audio", "3"),
            ("input", "image", "1"),
            ("output", "text", "4.5"),
            ("output", "audio", "12"),
        ]
    ]

    extra = []
    for model, direction, cached, value in [
        ("gemini-2.5-flash", "input", False, "0.30"),
        ("gemini-2.5-flash", "output", False, "2.50"),
        ("gemini-2.5-flash", "input", True, "0.03"),
        ("gemini-embedding-2", "input", False, "0.20"),
    ]:
        extra.append(
            dict(
                id=f"google-{model}-20261017-{direction}-{cached}",
                provider="google",
                model=model,
                unit="tokens",
                direction=direction,
                modality="text",
                cached=cached,
                effective_at="2026-10-17T00:00:00+00:00",
                usd_per_unit=Decimal(value) / Decimal(1_000_000),
                source_url="https://ai.google.dev/gemini-api/docs/pricing",
            )
        )
    return live + extra
