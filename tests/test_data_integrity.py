"""Checks that the data files match NIST's published numbers and stay consistent."""

import csv
import re

from conftest import REPO_ROOT

SPL_DIR = REPO_ROOT / "detections" / "splunk"


# Counts published in SP 800-53B (unchanged in Release 5.2.0).
def test_baseline_counts_match_sp_800_53b(controls):
    counts = {b: sum(c.in_baseline(b) for c in controls.values()) for b in ("low", "moderate", "high", "privacy")}
    assert counts == {"low": 149, "moderate": 287, "high": 370, "privacy": 96}


def test_catalog_has_release_520_controls(controls):
    # Release 5.2.0 added SA-15(13), SA-24 and SI-2(7).
    assert {"SA-15(13)", "SA-24", "SI-2(7)"} <= set(controls)
    base = [c for c in controls.values() if not c.is_enhancement]
    assert len(base) == 300
    assert len(controls) == 1014


def test_security_baselines_are_nested(controls):
    for c in controls.values():
        if c.low:
            assert c.moderate, c.control_id
        if c.moderate:
            assert c.high, c.control_id


def test_control_ids_unique():
    with (REPO_ROOT / "data" / "baselines_rev5.csv").open() as f:
        ids = [r["control_id"] for r in csv.DictReader(f)]
    assert len(ids) == len(set(ids))


def test_known_baseline_selections(controls):
    assert controls["AC-2"].low
    assert not controls["AC-2(12)"].moderate and controls["AC-2(12)"].high
    assert not any(controls["SC-41"].in_baseline(b) for b in ("low", "moderate", "high"))


def test_crosswalk_covers_all_97_requirements(crosswalk):
    reqs = {r["req_171"] for r in crosswalk}
    assert len(reqs) == 97
    assert all(re.fullmatch(r"03\.\d{2}\.\d{2}", r) for r in reqs)


def test_crosswalk_controls_exist(crosswalk, controls):
    missing = {r["control_53"] for r in crosswalk} - set(controls)
    assert not missing


def test_crosswalk_spot_check(crosswalk):
    au = {r["control_53"] for r in crosswalk if r["req_171"] == "03.03.05"}
    assert {"AU-6", "AU-6(3)"} <= au


def test_detection_controls_exist(detections, controls):
    missing = {r["control_53"] for r in detections} - set(controls)
    assert not missing


def test_every_detection_has_a_file_and_every_file_is_mapped(detections):
    mapped = {r["spl_file"] for r in detections}
    on_disk = {p.name for p in SPL_DIR.glob("*.spl")}
    assert mapped == on_disk


def test_spl_headers_list_the_same_controls_as_the_csv(detections):
    for spl in SPL_DIR.glob("*.spl"):
        header = spl.read_text().split("```")[1]
        line = next(l for l in header.splitlines() if "Controls:" in l)
        in_header = {c.strip() for c in line.split(":", 1)[1].split("(see")[0].split(",")}
        in_csv = {r["control_53"] for r in detections if r["spl_file"] == spl.name}
        assert in_header == in_csv, spl.name


def test_spl_files_contain_no_real_environment_details():
    ipv4 = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
    for spl in SPL_DIR.glob("*.spl"):
        text = spl.read_text()
        assert not ipv4.search(text), f"IP literal in {spl.name}"
        assert "fictional" in text.lower(), f"{spl.name} should say its example environment is fictional"
