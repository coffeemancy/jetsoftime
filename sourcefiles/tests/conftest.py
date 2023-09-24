from __future__ import annotations
import sys

from enum import Enum
from typing import Type

from pathlib import Path
from typing import Dict, List

import pytest

# add sourcefiles to import search path
sys.path.append(str(Path(__file__).parent.parent))


class TestHelpers:
    '''Re-useable static methods for testing.'''

    @staticmethod
    def check_enum_coherence(cls: Type[Enum], item):
        key = str(item)
        assert key, f"Empty string representation for {cls}.{item}"

        assert hasattr(cls, 'get'), f"Missing .get method for enum class: {cls}"

        lookup = cls.get(key)
        assert lookup is not None, f"Lookup for enum item was None: {cls}.{item}"

        assert lookup == item, f"Enum item lookup not equal to original value: {cls}.{item}"


@pytest.fixture
def helpers():
    return TestHelpers


@pytest.fixture(scope='session')
def paths() -> Dict[str, Path]:
    paths = {'tests': Path(__file__).parent.resolve()}
    paths['sourcefiles'] = Path(paths['tests'].parent.resolve())
    paths['presets'] = paths['sourcefiles'] / 'presets'
    return paths


@pytest.fixture(scope='session')
def presets(paths) -> List[Path]:
    '''All preset JSON files.'''
    return [
        path
        for directory in [paths['presets'], paths['tests'] / 'data/presets']
        for path in directory.rglob('*.preset.json')
    ]
