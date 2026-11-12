"""Rebuild the NIST reference CSVs from NIST's official OSCAL content.

This script reads only control identifiers, short control titles, and baseline
membership from the OSCAL files that NIST publishes at
https://github.com/usnistgov/oscal-content. It does not copy control statements
or guidance text.

Usage:
    git clone --depth 1 https://github.com/usnistgov/oscal-content.git /tmp/oscal-content
    python scripts/build_data.py /tmp/oscal-content

Outputs:
    data/baselines_rev5.csv
    data/crosswalk_171_to_53.csv
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

R5_DIR = Path("nist.gov/SP800-53/rev5/json")
CATALOG_53 = R5_DIR / "NIST_SP-800-53_rev5_catalog.json"
PROFILES = {
    "low": R5_DIR / "NIST_SP-800-53_rev5_LOW-baseline_profile.json",
    "moderate": R5_DIR / "NIST_SP-800-53_rev5_MODERATE-baseline_profile.json",
    "high": R5_DIR / "NIST_SP-800-53_rev5_HIGH-baseline_profile.json",
    "privacy": R5_DIR / "NIST_SP-800-53_rev5_PRIVACY-baseline_profile.json",
}
CATALOG_171 = Path("nist.gov/SP800-171/rev3/json/NIST_SP800-171_rev3_catalog.json")

# Matches 800-53 identifiers as written in the 800-171r3 OSCAL references,
# e.g. "AC-02" or "AC-02(03)".
REF_ID = re.compile(r"^([A-Z]{2})-(\d{1,2})(?:\((\d{1,2})\))?$")


def oscal_id_to_label(oscal_id: str) -> str:
    """Convert an OSCAL id like 'ac-2.3' to the familiar label 'AC-2(3)'."""
    base, _, enh = oscal_id.partition(".")
    family, _, number = base.partition("-")
    label = f"{family.upper()}-{int(number)}"
    return f"{label}({int(enh)})" if enh else label


def ref_title_to_label(title: str) -> str | None:
    """Convert a reference title like 'AC-02(03)' to 'AC-2(3)'. None if not a control."""
    m = REF_ID.match(title.strip())
    if not m:
        return None
    family, number, enh = m.groups()
    label = f"{family}-{int(number)}"
    return f"{label}({int(enh)})" if enh else label


def is_withdrawn(control: dict) -> bool:
    return any(
        p.get("name") == "status" and p.get("value") == "withdrawn"
        for p in control.get("props", [])
    )


def walk_controls(controls, family):
    for c in controls:
        yield c, family
        yield from walk_controls(c.get("controls", []), family)


def build_baselines(src: Path) -> list[dict]:
    catalog = json.loads((src / CATALOG_53).read_text())["catalog"]
    version = catalog["metadata"]["version"]

    selections = {}
    for name, rel in PROFILES.items():
        profile = json.loads((src / rel).read_text())["profile"]
        ids = set()
        for imp in profile["imports"]:
            for inc in imp.get("include-controls", []):
                ids.update(inc.get("with-ids", []))
        selections[name] = ids

    rows = []
    for group in catalog["groups"]:
        for control, family in walk_controls(group.get("controls", []), group["title"]):
            if is_withdrawn(control):
                continue
            cid = control["id"]
            rows.append(
                {
                    "control_id": oscal_id_to_label(cid),
                    "family": cid.split("-")[0].upper(),
                    "family_name": family,
                    "title": control["title"],
                    "is_enhancement": int("." in cid),
                    **{name: int(cid in ids) for name, ids in selections.items()},
                }
            )
    print(f"800-53 catalog release {version}: {len(rows)} active controls/enhancements")
    return rows


def build_crosswalk(src: Path) -> list[dict]:
    catalog = json.loads((src / CATALOG_171).read_text())["catalog"]
    resources = {r["uuid"]: r for r in catalog["back-matter"]["resources"]}

    rows = []
    for group in catalog["groups"]:
        family = group["title"]
        for req in group.get("controls", []):
            if is_withdrawn(req):
                continue
            req_id = req["id"].removeprefix("SP_800_171_")
            for link in req.get("links", []):
                res = resources.get(link["href"].lstrip("#"))
                if not res:
                    continue
                label = ref_title_to_label(res.get("title", ""))
                if label:
                    rows.append(
                        {
                            "req_171": req_id,
                            "req_title": req["title"],
                            "req_family": family,
                            "control_53": label,
                        }
                    )
    reqs = {r["req_171"] for r in rows}
    print(f"800-171r3: {len(reqs)} active requirements, {len(rows)} source-control links")
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    src = Path(argv[1])
    write_csv(DATA_DIR / "baselines_rev5.csv", build_baselines(src))
    write_csv(DATA_DIR / "crosswalk_171_to_53.csv", build_crosswalk(src))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
