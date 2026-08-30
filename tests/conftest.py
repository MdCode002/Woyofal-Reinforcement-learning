from __future__ import annotations

from pathlib import Path

import pytest

from common import charger_scenario


@pytest.fixture(scope="session")
def scenario_fixture():
    return charger_scenario(Path("data/scenarios/foyer_fictif.json"))
