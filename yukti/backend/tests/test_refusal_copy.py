"""P2H.2 / SPEC-06 §4.6 / BEH-01.60–.63: 9 refusal codes × 2 languages (18/18), 11 persona display strings, and refusal contract shapes."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.access_control import ALL_PERSONAS_ORDERED, check_access
from app.answer_composer import (
    PERSONA_DISPLAY,
    PERSONA_DISPLAY_STRINGS,
    REFUSAL_CODES_9,
    _infer_refusal_code,
    build_refusal_contract,
    load_refusal_copy,
    persona_display_info,
    render_refusal_copy,
    validate_and_repair_contract,
)
from app.auth import PERSONA_DIRECTORY
from app.brain import compiler, planner, rbac
from app.ui_control import UI_ACTIONS, _ALIASES

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


@pytest.mark.parametrize("lang,query", [
    ("en", "What is the salary of my reporting officer?"),
    ("hi", "मेरे रिपोर्टिंग अधिकारी का वेतन क्या है?"),
])
def test_m1_legacy_refusal_contract_repaired_to_spec06_without_rule_id_in_title_or_spoken(lang: str, query: str):
    """P2H.2 G4 M1: Legacy check_access & validate_and_repair_contract overwrite 'Access Restricted (D1)' and rule-ID prose with SPEC-06 copy."""
    dec = check_access("E2_HR", query=query)
    assert dec.status == "refused"
    assert dec.code == "R-PAY"

    # Also verify that even if a legacy caller passed 'Access Restricted (D1)' into validate_and_repair_contract,
    # it gets repaired to SPEC-06 copy with no rule ID in title, spoken_summary, or display_text.
    legacy_payload = {
        "turn_id": "t-legacy-m1",
        "persona": "E2_HR",
        "language": lang,
        "intent": "refused",
        "spoken_summary": f"I cannot share these confidential records under {dec.rule_ref}. {dec.reason}",
        "display_text": f"Refusal under {dec.rule_ref}: {dec.reason}. Safe alternative: {dec.alternative}.",
        "access": {
            "status": "refused",
            "rule_ref": dec.rule_ref,
            "reason": dec.reason,
            "safe_alternative": dec.alternative,
        },
        "visual": {
            "type": "refusal",
            "mode": "replace",
            "title": f"Access Restricted ({dec.rule_ref})",
        },
    }
    repaired = validate_and_repair_contract(legacy_payload)
    assert repaired["access"]["code"] == "R-PAY"
    assert repaired["spoken_summary"] == EXPECTED_COPY[("R-PAY", lang)]
    assert repaired["display_text"] == EXPECTED_COPY[("R-PAY", lang)]
    assert repaired["access"]["reason"] == EXPECTED_COPY[("R-PAY", lang)]
    assert repaired["visual"]["title"] == "Access restricted"
    assert "D1" not in repaired["visual"]["title"]
    assert "D1" not in repaired["spoken_summary"]
    assert "D1" not in repaired["display_text"]


@pytest.mark.asyncio
@pytest.mark.parametrize("lang,query", [
    ("en", "What is the salary of my reporting officer?"),
    ("hi", "मेरे रिपोर्टिंग अधिकारी का वेतन क्या है?"),
])
async def test_m1_turn_runner_check_access_hook_emits_spec06_refusal(lang: str, query: str):
    """P2H.2 G4 M1: AgentTurnRunner.execute_turn check_access refusal hook emits SPEC-06 R-PAY copy in EN and HI with no rule IDs in title/spoken/display."""
    from app.turn_runner import get_agent_turn_runner

    runner = get_agent_turn_runner()
    contract = await runner.execute_turn_async(query=query, persona="E2_HR", language=lang, session_id=f"s-m1-{lang}")
    assert contract["access"]["status"] == "refused"
    assert contract["access"]["code"] == "R-PAY"
    assert contract["access"]["rule_ref"]
    assert contract["spoken_summary"] == EXPECTED_COPY[("R-PAY", lang)]
    assert contract["display_text"] == EXPECTED_COPY[("R-PAY", lang)]
    assert contract["visual"]["title"] == "Access restricted"
    for forbidden in ("Access Restricted (", "I cannot share these confidential records", "(D1)", "(D-10)"):
        assert forbidden not in contract["spoken_summary"]
        assert forbidden not in contract["display_text"]
        assert forbidden not in contract["visual"]["title"]


def test_m4_refusal_copy_yaml_every_alternatives_item_has_question_hi_and_no_duplicates():
    """P2H.2 G4 M4: Every alternatives[] item in refusal_copy.yaml has question_hi, and render_refusal_copy deduplicates alternative vs alternatives."""
    codes = load_refusal_copy()
    for code, entry in codes.items():
        alts = entry.get("alternatives") or []
        for idx, item in enumerate(alts):
            assert item.get("label") or item.get("label_en"), f"{code} alternatives[{idx}] missing label"
            assert item.get("label_hi"), f"{code} alternatives[{idx}] missing label_hi"
            assert item.get("question"), f"{code} alternatives[{idx}] missing question"
            assert item.get("question_hi"), f"{code} alternatives[{idx}] missing question_hi"

        for lang in ("en", "hi"):
            rendered = render_refusal_copy(code=code, lang=lang, persona="E2_HR", grade_num="2")
            primary = rendered.get("alternative")
            extra = rendered.get("alternatives") or []
            if primary:
                primary_key = (primary.get("label"), primary.get("question"))
                for ex in extra:
                    assert (ex.get("label"), ex.get("question")) != primary_key, (
                        f"Duplicate chip in {code} ({lang}): {ex} matches primary {primary}"
                    )


@pytest.mark.parametrize("persona", list(ALL_PERSONAS_ORDERED))
@pytest.mark.parametrize("code", [c for c in REFUSAL_CODES_9 if c != "E-AUTH"])
@pytest.mark.parametrize("lang", ["en", "hi"])
def test_m5_every_chip_question_passes_real_gate_for_all_11_personas_and_both_langs(
    persona: str, code: str, lang: str
):
    """P2H.2 G4 M5: Every offered chip (primary alternative + extra alternatives, EN & HI) passes planner->compile->decide and check_access with allow|self|aggregate."""
    rendered = render_refusal_copy(code=code, lang=lang, persona=persona)
    chips = []
    if rendered.get("alternative"):
        chips.append(rendered["alternative"])
    for ex in rendered.get("alternatives") or []:
        chips.append(ex)
    assert chips, f"Expected at least 1 chip for {code} ({lang})"

    for chip in chips:
        q = chip["question"]
        assert isinstance(q, str) and q.strip(), f"Empty chip question on {code} ({lang}) for {persona}"

        # 1. Brain gate: planner.to_plan -> compiler.compile_spec -> rbac.decide
        pl = planner.get_planner().to_plan(q, {}, None)
        if pl.spec is not None:
            compiled = compiler.compile_spec(pl.spec)
            classes = compiled.data_classes
        elif pl.intent == "policy":
            classes = ["policy"]
        else:
            classes = ["general_hr"]
        dec = rbac.decide(persona, classes, question=q, spec=pl.spec)
        assert dec.action in ("allow", "self", "aggregate"), (
            f"Chip {q!r} ({code}, {lang}) failed rbac.decide for {persona}: "
            f"action={dec.action}, code={dec.code}, classes={classes}, intent={pl.intent}"
        )

        # 2. Legacy check_access gate
        legacy_dec = check_access(persona, query=q)
        assert legacy_dec.status == "allowed", (
            f"Chip {q!r} ({code}, {lang}) failed check_access for {persona}: "
            f"status={legacy_dec.status}, code={legacy_dec.code}, reason={legacy_dec.reason}"
        )


def test_should_fix_unknown_persona_uses_neutral_fallback_and_word_boundaries():
    """P2H.2 G4 Should-fix #1, #6, and ui_control 11-persona parity."""
    # Should-fix #1: Unknown persona never defaults to Pooja Verma / E2_HR
    info = persona_display_info("UNKNOWN_ROLE")
    assert info["display_name"] != "Pooja Verma"
    assert "Pooja Verma" not in info["display_string"]
    r_role = render_refusal_copy("R-ROLE", lang="en", persona="UNKNOWN_ROLE")
    assert "Pooja Verma" not in r_role["text"]

    # Should-fix #6: _infer_refusal_code uses word boundaries so 'display' != 'pay' and 'dashboard' != 'board'
    assert _infer_refusal_code({"rule_ref": "", "reason": "Cannot display individual records"}) == "R-NAMED"
    assert _infer_refusal_code({"rule_ref": "", "reason": "Executive dashboard restricted"}) == "R-NAMED"
    assert _infer_refusal_code({"rule_ref": "", "reason": "Individual pay is confidential"}) == "R-PAY"
    assert _infer_refusal_code({"rule_ref": "", "reason": "Board note is restricted"}) == "R-BOARD"

    # ui_control 11-persona parity
    assert set(ALL_PERSONAS_ORDERED).issubset(set(UI_ACTIONS["persona"]))
    assert _ALIASES[("persona", "asha")] == ("persona", "E3_FIN")


@pytest.mark.asyncio
async def test_m6_m7_full_turn_refusal_suggestions_and_hindi():
    """P2H.2 G4 M6, M7: Legacy LLM path returns refusal in EN with visual none.
    validate_and_repair_contract forces it to HI refusal visual and suggestions = [] (M7)."""
    from app.answer_composer import validate_and_repair_contract
    # Simulate LLM returning a legacy refusal with English text and visual: none, but language: hi
    contract = {
        "turn_id": "t1",
        "language": "hi",
        "persona": "E2_HR",
        "spoken_summary": "Individual pay is confidential. I can show the average pay for that grade, or your own payslip.",
        "visual": {"type": "none", "mode": "replace"},
        "suggestions": ["Show breakdown by discipline", "What are the relevant policy rules?"],
        "access": {
            "status": "refused",
            "reason": "Individual pay is confidential. I can show the average pay for that grade, or your own payslip.",
            "rule_ref": "SPEC-06 §4.6"
        }
    }
    repaired = validate_and_repair_contract(contract)
    assert repaired["visual"]["type"] == "refusal"
    assert "किसी व्यक्ति का वेतन गोपनीय है" in repaired["spoken_summary"]
    assert repaired["suggestions"] == []
