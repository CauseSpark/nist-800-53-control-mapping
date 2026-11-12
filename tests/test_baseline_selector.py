import pytest

from src.baseline_selector import controls_for_171, diff, family_summary, main, select, sort_key
from src.loaders import base_control, normalize_control_id


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("ac-2", "AC-2"),
        ("AC-02", "AC-2"),
        ("AC-02(03)", "AC-2(3)"),
        ("ac-2.3", "AC-2(3)"),
        (" AC-2 (12) ", "AC-2(12)"),
        ("si-4", "SI-4"),
    ],
)
def test_normalize_control_id(raw, expected):
    assert normalize_control_id(raw) == expected


@pytest.mark.parametrize("bad", ["", "AC", "AC2", "A-2", "AC-2(", "03.01.01"])
def test_normalize_rejects_bad_ids(bad):
    with pytest.raises(ValueError):
        normalize_control_id(bad)


def test_base_control():
    assert base_control("ac-02(04)") == "AC-2"


def test_sort_key_orders_numerically():
    ids = ["AC-10", "AC-2(12)", "AC-2", "AC-2(3)", "AB-9"]
    assert sorted(ids, key=sort_key) == ["AB-9", "AC-2", "AC-2(3)", "AC-2(12)", "AC-10"]


def test_select_by_baseline(tiny_controls):
    assert [c.control_id for c in select(tiny_controls, "low")] == ["AC-2", "AU-6"]
    assert [c.control_id for c in select(tiny_controls, "high")] == ["AC-2", "AC-2(4)", "AC-2(12)", "AU-6"]


def test_select_family_and_enhancement_filters(tiny_controls):
    assert [c.control_id for c in select(tiny_controls, "high", families=["ac"])] == ["AC-2", "AC-2(4)", "AC-2(12)"]
    assert [c.control_id for c in select(tiny_controls, "high", include_enhancements=False)] == ["AC-2", "AU-6"]


def test_select_rejects_unknown_baseline(tiny_controls):
    with pytest.raises(ValueError):
        select(tiny_controls, "extreme")


def test_diff(tiny_controls):
    assert [c.control_id for c in diff(tiny_controls, "low", "moderate")] == ["AC-2(4)"]
    assert [c.control_id for c in diff(tiny_controls, "moderate", "high")] == ["AC-2(12)"]


def test_family_summary(tiny_controls):
    assert family_summary(select(tiny_controls, "high")) == {"AC": 3, "AU": 1}


def test_controls_for_171(crosswalk):
    ids = controls_for_171(crosswalk, ["03.01.01"])
    assert ids[0] == "AC-2" and "AC-2(3)" in ids


def test_controls_for_171_unknown_requirement(crosswalk):
    with pytest.raises(ValueError):
        controls_for_171(crosswalk, ["03.99.99"])


def test_moderate_adds_138_to_low(controls):
    assert len(diff(controls, "low", "moderate")) == 287 - 149


def test_cli_summary(capsys):
    assert main(["--baseline", "low", "--summary"]) == 0
    out = capsys.readouterr().out
    assert "TOTAL\t149" in out


def test_cli_from_171(capsys):
    assert main(["--from-171", "03.03.05"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith("control_id,")
    assert any(line.startswith("AU-6(3),") for line in out)
