"""Select NIST SP 800-53 Rev. 5 controls by baseline, family, or 800-171r3 requirement.

Examples:
    python -m src.baseline_selector --baseline moderate --summary
    python -m src.baseline_selector --baseline high --family AU --family SI
    python -m src.baseline_selector --baseline moderate --diff-from low
    python -m src.baseline_selector --from-171 03.01.01 03.03.05
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from typing import Iterable

from src.loaders import BASELINES, Control, load_controls, load_crosswalk, normalize_control_id

_SORT_RE = re.compile(r"^([A-Z]{2})-(\d+)(?:\((\d+)\))?$")


def sort_key(control_id: str) -> tuple[str, int, int]:
    """Sort 'AC-2' before 'AC-2(1)' before 'AC-10'."""
    family, number, enh = _SORT_RE.match(control_id).groups()
    return family, int(number), int(enh or 0)


def select(
    controls: dict[str, Control],
    baseline: str,
    families: Iterable[str] | None = None,
    include_enhancements: bool = True,
) -> list[Control]:
    """Return controls in a baseline, optionally filtered by family."""
    fams = {f.upper() for f in families} if families else None
    picked = [
        c
        for c in controls.values()
        if c.in_baseline(baseline)
        and (fams is None or c.family in fams)
        and (include_enhancements or not c.is_enhancement)
    ]
    return sorted(picked, key=lambda c: sort_key(c.control_id))


def diff(controls: dict[str, Control], from_baseline: str, to_baseline: str) -> list[Control]:
    """Controls in to_baseline that are not in from_baseline (e.g. what Moderate adds to Low)."""
    picked = [
        c for c in controls.values() if c.in_baseline(to_baseline) and not c.in_baseline(from_baseline)
    ]
    return sorted(picked, key=lambda c: sort_key(c.control_id))


def family_summary(selected: Iterable[Control]) -> dict[str, int]:
    """Count selected controls per family, sorted by family code."""
    return dict(sorted(Counter(c.family for c in selected).items()))


def controls_for_171(crosswalk: list[dict], requirement_ids: Iterable[str]) -> list[str]:
    """800-53 source controls behind one or more 800-171r3 requirements."""
    wanted = {r.strip() for r in requirement_ids}
    unknown = wanted - {row["req_171"] for row in crosswalk}
    if unknown:
        raise ValueError(f"Unknown 800-171r3 requirement(s): {sorted(unknown)}")
    found = {row["control_53"] for row in crosswalk if row["req_171"] in wanted}
    return sorted(found, key=sort_key)


def _write_rows(controls: list[Control], out) -> None:
    writer = csv.writer(out)
    writer.writerow(["control_id", "family", "title", *BASELINES])
    for c in controls:
        writer.writerow([c.control_id, c.family, c.title, *(int(c.in_baseline(b)) for b in BASELINES)])


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--baseline", choices=BASELINES, default="moderate")
    p.add_argument("--family", action="append", help="Filter to a family code, e.g. AC. Repeatable.")
    p.add_argument("--no-enhancements", action="store_true", help="Base controls only.")
    p.add_argument("--diff-from", choices=BASELINES, help="Show only what --baseline adds to this baseline.")
    p.add_argument("--from-171", nargs="+", metavar="REQ", help="800-171r3 requirement ids, e.g. 03.01.01")
    p.add_argument("--summary", action="store_true", help="Print counts per family instead of rows.")
    args = p.parse_args(argv)

    controls = load_controls()

    if args.from_171:
        ids = controls_for_171(load_crosswalk(), args.from_171)
        selected = [controls[normalize_control_id(i)] for i in ids]
    elif args.diff_from:
        selected = diff(controls, args.diff_from, args.baseline)
    else:
        selected = select(controls, args.baseline, args.family, not args.no_enhancements)

    if args.family and (args.from_171 or args.diff_from):
        fams = {f.upper() for f in args.family}
        selected = [c for c in selected if c.family in fams]

    if args.summary:
        for fam, n in family_summary(selected).items():
            print(f"{fam}\t{n}")
        print(f"TOTAL\t{len(selected)}")
    else:
        _write_rows(selected, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
