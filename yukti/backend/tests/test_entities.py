"""Unit tests for entity dictionary (Task Packet B1.3 §5.3)."""

import json
from pathlib import Path
import sys
import yaml
import pytest

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.semantic.entities import get_entities


@pytest.fixture(scope="module")
def ents():
    return get_entities()


def test_resolve_wc_mumbai(ents):
    assert ents.resolve_wc("Mumbai mein 5 saal se zyada kitne executives hain?") == "WC-MUM"


def test_resolve_wcs_delhi_vs_mumbai(ents):
    assert ents.resolve_wcs("Compare Delhi vs Mumbai") == ["WC-DEL", "WC-MUM"]


def test_resolve_wc_ro_mumbai(ents):
    assert ents.resolve_wc("What about RO Mumbai?") == "WC-ROM"


def test_resolve_wc_kakinada(ents):
    assert ents.resolve_wc("How many people in Kakinada") == "WC-EAS"


def test_resolve_wc_delhi_hindi(ents):
    assert ents.resolve_wc("दिल्ली में कितने अधिकारी") == "WC-DEL"


def test_resolve_wcs_and_region_eastern_offshore(ents):
    assert ents.resolve_wcs("Eastern Offshore capex") == ["WC-EAS"]
    assert ents.resolve_region("Eastern Offshore capex") is None


def test_resolve_region_north_east(ents):
    res = ents.resolve_region("North East vacancies")
    assert res is not None
    name, codes = res
    assert name == "north east"
    assert set(codes) == {"WC-AAB", "WC-ASM", "WC-INB", "WC-JOR", "WC-SIL", "WC-TRI"}


def test_replace_codes(ents):
    assert ents.replace_codes("WC-RAJ-BSN and WC-RAJ") == "Rajasthan Basin and Rajahmundry Asset"
    assert ents.replace_codes("WC-ZZZ") == "WC-ZZZ"
    nested_input = {
        "level1": ["WC-RAJ-BSN", {"level2": "WC-RAJ"}],
        "other": 123,
    }
    expected_output = {
        "level1": ["Rajasthan Basin", {"level2": "Rajahmundry Asset"}],
        "other": 123,
    }
    assert ents.replace_codes(nested_input) == expected_output


def test_resolve_field(ents):
    assert ents.resolve_field("Why is Champang losing money?") == "FLD-CHP"


def test_resolve_grades(ents):
    assert ents.resolve_grades("Which GMs retire in 2027?") == ["E7"]
    assert ents.resolve_grades("only E5 and above") == ["E5"]


def test_resolve_disciplines(ents):
    assert ents.resolve_disciplines("geoscience gap") == ["DISC-GEO", "DISC-GPS", "DISC-GPW"]


def test_all_codes_in_aliases_yaml_exist_in_entities_json():
    sem_dir = Path(__file__).resolve().parent.parent / "app" / "semantic"
    ej = json.loads((sem_dir / "entities.json").read_text(encoding="utf-8"))
    ay = yaml.safe_load((sem_dir / "entity_aliases.yaml").read_text(encoding="utf-8")) or {}

    for code in ay.get("work_centres", {}):
        assert code in ej.get("work_centres", {}), f"work_centre {code} not in entities.json"

    for code in ay.get("work_centre_notes", {}):
        assert code in ej.get("work_centres", {}), f"work_centre_note {code} not in entities.json"

    for code in ay.get("disciplines", {}):
        assert code in ej.get("disciplines", {}), f"discipline {code} not in entities.json"

    for code in ay.get("fields", {}):
        assert code in ej.get("fields", {}), f"field {code} not in entities.json"

    for code in ay.get("grades", {}):
        assert code in ej.get("grades", {}), f"grade {code} not in entities.json"

    for group_name, codes in (ay.get("discipline_groups") or {}).items():
        for code in codes:
            assert code in ej.get("disciplines", {}), f"discipline_group {group_name} code {code} not in entities.json"

    for region_name, reg_cfg in (ay.get("regions") or {}).items():
        for code in reg_cfg.get("wc_ids") or []:
            assert code in ej.get("work_centres", {}), f"region {region_name} wc_id {code} not in entities.json"


def test_work_centres_count(ents):
    assert len(ents.work_centres) == 46
