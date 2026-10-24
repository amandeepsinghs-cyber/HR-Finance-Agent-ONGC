import json
from pathlib import Path
from app.ui_control import detect_ui_control_intent

def test_export_intent_positive():
    p = Path(__file__).parent.parent.parent / "contracts" / "intents" / "export_intent.json"
    data = json.loads(p.read_text())
    positives = data.get("positive_utterances", [])
    assert len(positives) >= 40
    for query in positives:
        res = detect_ui_control_intent(query)
        assert res is not None, f"Failed positive: {query}"
        assert res.get("action") == "export"

def test_export_intent_negative():
    p = Path(__file__).parent.parent.parent / "contracts" / "intents" / "export_intent.json"
    data = json.loads(p.read_text())
    negatives = data.get("negative_utterances", [])
    assert len(negatives) >= 10
    for query in negatives:
        res = detect_ui_control_intent(query)
        if res:
            assert res.get("action") != "export", f"Failed negative (should not be export): {query}"
