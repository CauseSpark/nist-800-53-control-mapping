import pytest

from src.coverage_report import build_coverage, main, render_markdown


def det(name, control):
    return {"detection": name, "spl_file": "x.spl", "control_53": control, "rationale": ""}


CROSSWALK = [
    {"req_171": "03.01.01", "req_title": "", "req_family": "", "control_53": "AC-2"},
    {"req_171": "03.01.01", "req_title": "", "req_family": "", "control_53": "AC-2(4)"},
    {"req_171": "03.03.05", "req_title": "", "req_family": "", "control_53": "AU-6"},
]


def test_enhancement_does_not_credit_base_control(tiny_controls):
    cov = build_coverage(tiny_controls, [det("D1", "AC-2(4)")], CROSSWALK, "moderate")
    assert list(cov.covered) == ["AC-2(4)"]
    assert "AC-2" not in cov.covered


def test_outside_baseline_is_reported_separately(tiny_controls):
    dets = [det("D1", "AC-2(12)"), det("D2", "SC-41"), det("D3", "AU-6")]
    cov = build_coverage(tiny_controls, dets, CROSSWALK, "moderate")
    assert list(cov.covered) == ["AU-6"]
    assert list(cov.outside_baseline) == ["AC-2(12)", "SC-41"]


def test_percent_and_family_breakdown(tiny_controls):
    dets = [det("D1", "AC-2"), det("D2", "AC-2"), det("D3", "AU-6")]
    cov = build_coverage(tiny_controls, dets, CROSSWALK, "moderate")
    assert cov.baseline_total == 3
    assert cov.percent == pytest.approx(200 / 3)
    assert cov.by_family == {"AC": (1, 2), "AU": (1, 1)}
    assert cov.covered["AC-2"] == ["D1", "D2"]


def test_171_requirements_touched(tiny_controls):
    cov = build_coverage(tiny_controls, [det("D1", "AU-6")], CROSSWALK, "low")
    assert cov.req_171 == {"03.03.05": ["AU-6"]}
    assert cov.req_171_total == 2


def test_unknown_control_raises(tiny_controls):
    with pytest.raises(ValueError):
        build_coverage(tiny_controls, [det("D1", "ZZ-1")], CROSSWALK, "low")


def test_markdown_render(tiny_controls):
    cov = build_coverage(tiny_controls, [det("D1", "AU-6"), det("D2", "SC-41")], CROSSWALK, "low")
    md = render_markdown(cov, tiny_controls)
    assert md.startswith("# Detection coverage: SP 800-53 Rev. 5 Low baseline")
    assert "| AU-6 | title AU-6 | D1 |" in md
    assert "SC-41" in md and "not selected in this baseline" in md


def test_real_data_moderate(controls, detections, crosswalk):
    cov = build_coverage(controls, detections, crosswalk, "moderate")
    assert cov.baseline_total == 287
    assert {"AC-7", "AU-6", "SI-4"} <= set(cov.covered)
    assert "SC-41" in cov.outside_baseline


def test_cli_writes_file(tmp_path, capsys):
    out = tmp_path / "report.md"
    assert main(["--baseline", "high", "--output", str(out)]) == 0
    assert "High baseline" in out.read_text()
