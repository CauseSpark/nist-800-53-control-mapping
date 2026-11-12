import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.loaders import Control, load_controls, load_crosswalk, load_detections  # noqa: E402


@pytest.fixture(scope="session")
def controls():
    return load_controls()


@pytest.fixture(scope="session")
def crosswalk():
    return load_crosswalk()


@pytest.fixture(scope="session")
def detections():
    return load_detections()


def make_control(cid, low=False, moderate=False, high=False, privacy=False):
    family = cid.split("-")[0]
    return Control(cid, family, family, f"title {cid}", "(" in cid, low, moderate, high, privacy)


@pytest.fixture
def tiny_controls():
    """A small hand-built catalog so logic tests don't depend on NIST data."""
    items = [
        make_control("AC-2", low=True, moderate=True, high=True),
        make_control("AC-2(4)", moderate=True, high=True),
        make_control("AC-2(12)", high=True),
        make_control("AU-6", low=True, moderate=True, high=True),
        make_control("SC-41"),
    ]
    return {c.control_id: c for c in items}
