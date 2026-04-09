"""Basic pipeline tests"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

def test_config_loads():
    from config import ANALYSIS_MODEL, RSS_FEEDS, GDELT_TERROR_CODES
    assert ANALYSIS_MODEL
    assert len(RSS_FEEDS) >= 20
    assert len(GDELT_TERROR_CODES) >= 5

def test_fips_to_iso():
    from fips_to_iso import fips_to_iso
    assert fips_to_iso("IS") == "IL"  # Israel, not Iceland
    assert fips_to_iso("NI") == "NG"  # Nigeria, not Nicaragua
    assert fips_to_iso("TU") == "TR"  # Turkey
    assert fips_to_iso("UK") == "GB"  # UK

def test_casualty_extractor():
    from casualty_extractor import extract_casualties
    r = extract_casualties("Israeli strike kills 12 in Lebanon")
    assert r["fatalities_estimated"] == 12

    r = extract_casualties("At least 25 people were killed")
    assert r["fatalities_estimated"] == 25
    assert r["confidence"] == "HIGH"

    r = extract_casualties("No casualties reported")
    assert r["fatalities_estimated"] == 0

def test_mapper_org_matching():
    from mapper import TerrorMapper
    m = TerrorMapper()

    # Should match
    assert m.match_organization("Hamas") is not None
    assert m.match_organization("hezbollah") is not None
    assert m.match_organization("TTP") is not None
    assert m.match_organization("ISIS") is not None
    assert m.match_organization("al qaeda") is not None
    assert m.match_organization("houthis") is not None

    # Should NOT match (generic actors)
    assert m.match_organization("POLICE") is None
    assert m.match_organization("IRAN") is None
    assert m.match_organization("ISRAEL") is None
    assert m.match_organization("MILITARY") is None
    assert m.match_organization("") is None

def test_mapper_country():
    from mapper import TerrorMapper
    m = TerrorMapper()

    r = m.match_country("IL")
    assert r is not None
    assert r["name"] == "Israel"

    r = m.match_country("NG")
    assert r is not None
    assert "Nigeria" in r["name"]

def test_mapper_cameo_attack():
    from mapper import TerrorMapper
    m = TerrorMapper()

    r = m.classify_attack("", "", event_code="195")
    assert r["category"] == "airstrike"

    r = m.classify_attack("", "", event_code="181")
    assert r["category"] == "bombing"

    r = m.classify_attack("", "", event_code="183")
    assert r["category"] == "cbrn"

def test_data_files_valid():
    import json
    data_dir = Path(__file__).resolve().parent.parent / "data"

    orgs = json.loads((data_dir / "organizations.json").read_text(encoding="utf-8"))
    assert len(orgs["organizations"]) >= 280

    zones = json.loads((data_dir / "conflict_zones.json").read_text(encoding="utf-8"))
    assert len(zones["conflict_zones"]) >= 70

    countries = json.loads((data_dir / "countries.json").read_text(encoding="utf-8"))
    total = sum(len(r.get("countries", [])) for r in countries["regions"].values())
    assert total >= 170

def test_db_schema():
    from database import get_conn
    conn = get_conn()
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    conn.close()
    assert "events" in tables
    assert "sanctions" in tables
    assert "daily_stats" in tables

if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    passed = failed = 0
    for test in tests:
        try:
            test()
            print(f"  PASS {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL {test.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
