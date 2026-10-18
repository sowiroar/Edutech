import json
from pathlib import Path

from viva_metrics.contract import event_schema


def test_exported_schema_is_the_runtime_contract():
    saved = json.loads(
        (Path(__file__).parents[2] / "contracts/telemetry-event.v1.schema.json").read_text()
    )
    assert saved == event_schema()
