"""P2H.2 / SPEC-06 §4.6 / BEH-01.60–.63: 9 refusal codes × 2 languages (18/18), 11 persona display strings, and refusal contract shapes."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.access_control import ALL_PERSONAS_ORDERED
from app.answer_composer import (
    PERSONA_DISPLAY,
    PERSONA_DISPLAY_STRINGS,
    REFUSAL_CODES_9,
    build_refusal_contract,
    load_refusal_copy,
    persona_display_info,
    render_refusal_copy,
    validate_and_repair_contract,
)
from app.auth import PERSONA_DIRECTORY

EXPECTED_COPY = {
    ("R-NAMED", "en"): "I can't share individual names at your access level. Here is the same group as counts by grade (groups under 5 shown as '<5').",
    ("R-NAMED", "hi"): "आपके एक्सेस स्तर पर व्यक्तिगत नाम साझा नहीं किए जा सकते। यही समूह ग्रेड-वार संख्या में दिखा रही हूँ (5 से कम को '<5' लिखा है)।",
    ("R-PAY", "en"): "Individual pay is confidential. I can show the average pay for that grade, or your own payslip.",
    ("R-PAY", "hi"): "किसी व्यक्ति का वेतन गोपनीय है। मैं उस ग्रेड का औसत वेतन या आपकी अपनी वेतन पर्ची दिखा सकती हूँ।",
    ("R-APAR", "en"): "Appraisal ratings are confidential. I can show your own APAR history.",
    ("R-APAR", "hi"): "मूल्यांकन रेटिंग गोपनीय हैं। मैं आपका अपना APAR इतिहास दिखा सकती हूँ।",
    ("R-SENS", "en"): "Case records like these are restricted to the CMD and Director (HR). I can explain the policy and the reporting process.",
    ("R-SENS", "hi"): "ऐसे मामलों के रिकॉर्ड केवल CMD और निदेशक (मानव संसाधन) देख सकते हैं। मैं नीति और शिकायत प्रक्रिया बता सकती हूँ।",
    ("R-FUNC", "en"): "Ledger-level finance data is available to the Finance team. Here are the company-level totals instead.",
    ("R-FUNC", "hi"): "लेजर-स्तर का वित्त डेटा वित्त टीम के लिए है। इसके बजाय कंपनी-स्तर के कुल आँकड़े दिखा रही हूँ।",
    ("R-BOARD", "en"): "That Board note is restricted. I can summarise the published Annual Report position.",
    ("R-BOARD", "hi"): "वह बोर्ड नोट प्रतिबंधित है। मैं प्रकाशित वार्षिक रिपोर्ट की स्थिति बता सकती हूँ।",
    ("R-ROLE", "en"): "I can't change your access level from a conversation. You're signed in as Pooja Verma, HR Executive (E2).",
    ("R-ROLE", "hi"): "बातचीत से आपका एक्सेस स्तर नहीं बदला जा सकता। आप Pooja Verma, HR Executive (E2) के रूप में साइन-इन हैं।",
    ("R-K5", "en"): "This group is too small to show without identifying people. Try a wider filter, e.g. all Delhi executives.",
    ("R-K5", "hi"): "यह समूह इतना छोटा है कि संख्या दिखाने से लोग पहचाने जा सकते हैं। कृपया दायरा बढ़ाएँ।",
    ("E-AUTH", "en"): "I can't reach the data service right now. Nothing is wrong with your question; please try again in a minute.",
    ("E-AUTH", "hi"): "अभी डेटा सेवा से संपर्क नहीं हो पा रहा। कृपया एक मिनट बाद फिर पूछें।",
}


def test_refusal_copy_yaml_has_all_9_codes():
    codes = load_refusal_copy()
    assert set(codes.keys()) == set(REFUSAL_CODES_9)
    assert len(codes) == 9


@pytest.mark.parametrize("code", list(REFUSAL_CODES_9))
@pytest.mark.parametrize("lang", ["en", "hi"])
def test_18_refusal_codes_x_languages_render_exact_spec06_copy(code: str, lang: str):
    """P2H.2 AC-2: All 9 refusal codes × 2 languages (18/18) render from refusal_copy.yaml with exact SPEC-06 §4.6 copy."""
    rendered = render_refusal_copy(code=code, lang=lang, persona="E2_HR", grade_num="2")
    assert rendered["code"] == code
    assert rendered["text"] == EXPECTED_COPY[(code, lang)]
    assert rendered["rule_ref"], f"Missing rule_ref for {code}"

    # BEH-01.60: No 'Access denied' and no rule IDs in the headline text
    assert "Access denied" not in rendered["text"]
    for rule_id in ("D-10", "D-11", "D-41", "D-43", "SPEC-06", "BUG-33"):
        assert rule_id not in rendered["text"]

    # BEH-01.61: Alternative offered for all R-* codes; None for E-AUTH
    if code == "E-AUTH":
        assert rendered["alternative"] is None
    else:
        alt = rendered["alternative"]
        assert isinstance(alt, dict)
        assert isinstance(alt.get("label"), str) and alt["label"]
        assert isinstance(alt.get("question"), str) and alt["question"]


@pytest.mark.parametrize("persona", list(ALL_PERSONAS_ORDERED))
def test_11_persona_display_strings_loaded_from_app_users_yaml(persona: str):
    """P2H.2: answer_composer loads all 11 display strings from app_users.yaml and substitutes {display_name}, {designation}."""
    assert persona in PERSONA_DISPLAY
    assert persona in PERSONA_DISPLAY_STRINGS
    info = persona_display_info(persona)
    auth_info = PERSONA_DIRECTORY[persona]
    assert info["display_name"] == auth_info["display_name"]
    assert info["designation"] == auth_info["designation"]
    assert info["display_string"] == f"{auth_info['display_name']}, {auth_info['designation']}"

    for lang in ("en", "hi"):
        r_role = render_refusal_copy("R-ROLE", lang=lang, persona=persona)
        assert info["display_name"] in r_role["text"]
        assert info["designation"] in r_role["text"]


@pytest.mark.parametrize("code", list(REFUSAL_CODES_9))
@pytest.mark.parametrize("lang", ["en", "hi"])
def test_build_refusal_contract_validates_and_carries_required_fields(code: str, lang: str):
    """P2H.2: Every refusal contract carries access.code, access.rule_ref, access.alternative {question, label}, and passes schema validation."""
    c = build_refusal_contract(code=code, persona="E3_FIN", turn_id=f"t-{code}-{lang}", language=lang, grade_num="1")
    validated = validate_and_repair_contract(c)
    assert validated["access"]["code"] == code
    assert validated["access"]["rule_ref"]
    assert validated["visual"]["type"] == "refusal"
    assert validated["visual"]["code"] == code
    if code == "E-AUTH":
        assert validated["access"]["alternative"] is None
    else:
        assert isinstance(validated["access"]["alternative"], dict)
        assert set(validated["access"]["alternative"].keys()) >= {"label", "question"}
    if code == "R-PAY":
        assert "E1" in validated["access"]["alternative"]["label"]


def test_build_refusal_contract_with_auto_answer_aggregate_visual():
    """P2H.2: When policy allows an auto-answer (R-NAMED / R-FUNC), the contract carries the aggregate visual + refusal copy lead."""
    agg_vis = {
        "type": "table",
        "mode": "replace",
        "title": "Employees by grade · Delhi HQ",
        "table": {"columns": ["grade", "headcount"], "rows": [{"grade": "E1", "headcount": 10}, {"grade": "E2", "headcount": 29}]},
    }
    c = build_refusal_contract(
        code="R-NAMED",
        persona="E1_FIN",
        turn_id="t-auto-agg",
        language="en",
        auto_answer_visual=agg_vis,
    )
    validated = validate_and_repair_contract(c)
    assert validated["access"]["status"] == "partial"
    assert validated["access"]["code"] == "R-NAMED"
    assert validated["access"]["rule_ref"] == "D-11"
    assert validated["access"]["alternative"] == {"label": "Counts by grade", "question": "Show counts by grade"}
    assert validated["visual"]["type"] == "table"
    assert validated["visual"]["table"]["masking"]["level"] == "aggregate"
    assert validated["visual"]["table"]["masking"]["code"] == "R-NAMED"
    assert validated["display_text"].startswith("I can't share individual names at your access level.")
