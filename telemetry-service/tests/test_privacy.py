import ast
from pathlib import Path

from viva_metrics.privacy import redact


def test_redaction_implementations_are_identical_in_both_images():
    root = Path(__file__).parents[2]
    producer = root / "agent-starter-python/src/viva_telemetry/privacy.py"
    collector = root / "telemetry-service/src/viva_metrics/privacy.py"
    assert ast.dump(ast.parse(producer.read_text())) == ast.dump(ast.parse(collector.read_text()))
    result, _ = redact("Correo demo@example.com y token=NO_GUARDAR")
    assert "demo@example.com" not in result and "NO_GUARDAR" not in result
