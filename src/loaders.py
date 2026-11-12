"""Load and normalize the CSV data files in data/."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
BASELINES = ("low", "moderate", "high", "privacy")

_CONTROL_RE = re.compile(
    r"^\s*([A-Za-z]{2})\s*-\s*0*(\d{1,2})\s*(?:(?:\(\s*0*(\d{1,2})\s*\))|(?:\.\s*0*(\d{1,2})))?\s*$"
)


def normalize_control_id(raw: str) -> str:
    """Return a control id in the 'AC-2(3)' form.

    Accepts common variants: 'ac-2', 'AC-02', 'AC-02(03)', 'ac-2.3', 'AC-2 (3)'.
    Raises ValueError for anything else.
    """
    m = _CONTROL_RE.match(raw or "")
    if not m:
        raise ValueError(f"Not a valid SP 800-53 control id: {raw!r}")
    family, number, enh_paren, enh_dot = m.groups()
    enh = enh_paren or enh_dot
    label = f"{family.upper()}-{int(number)}"
    return f"{label}({int(enh)})" if enh else label


def base_control(control_id: str) -> str:
    """'AC-2(3)' -> 'AC-2'."""
    return normalize_control_id(control_id).split("(")[0]


@dataclass(frozen=True)
class Control:
    control_id: str
    family: str
    family_name: str
    title: str
    is_enhancement: bool
    low: bool
    moderate: bool
    high: bool
    privacy: bool

    def in_baseline(self, baseline: str) -> bool:
        baseline = baseline.lower()
        if baseline not in BASELINES:
            raise ValueError(f"Unknown baseline {baseline!r}; choose from {BASELINES}")
        return getattr(self, baseline)


def _read(path: Path) -> list[dict]:
    with Path(path).open(newline="") as f:
        return list(csv.DictReader(f))


def load_controls(path: Path | None = None) -> dict[str, Control]:
    """Return {control_id: Control} for every active 800-53 Rev. 5 control."""
    rows = _read(path or DATA_DIR / "baselines_rev5.csv")
    controls = {}
    for r in rows:
        cid = normalize_control_id(r["control_id"])
        controls[cid] = Control(
            control_id=cid,
            family=r["family"],
            family_name=r["family_name"],
            title=r["title"],
            is_enhancement=r["is_enhancement"] == "1",
            **{b: r[b] == "1" for b in BASELINES},
        )
    return controls


def load_crosswalk(path: Path | None = None) -> list[dict]:
    """Rows of 800-171r3 requirement -> 800-53r5 source control."""
    rows = _read(path or DATA_DIR / "crosswalk_171_to_53.csv")
    for r in rows:
        r["control_53"] = normalize_control_id(r["control_53"])
    return rows


def load_detections(path: Path | None = None) -> list[dict]:
    """Rows of detection -> 800-53r5 control it supports."""
    rows = _read(path or DATA_DIR / "detections_to_controls.csv")
    for r in rows:
        r["control_53"] = normalize_control_id(r["control_53"])
    return rows
