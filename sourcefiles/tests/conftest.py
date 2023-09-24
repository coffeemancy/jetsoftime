from __future__ import annotations
import sys

from enum import Enum
from typing import Type

from pathlib import Path
from typing import Dict, List

import pytest

# add sourcefiles to import search path
sys.path.append(str(Path(__file__).parent.parent))


class TestData:
    '''Singleton-ish re-useable non-fixture data for testing.

    The data is in lieu of using fixtures for these, since fixtures cannot be used
    as values in parametrized tests to create separate tests.

    In general, data in this class should be exceptional, only to be able to generate
    separate tests i.e. with pytest.mark.parametrize.
    '''

    paths: Dict[str, Path] = {'tests': Path(__file__).parent.resolve()}
    paths['sourcefiles'] = Path(paths['tests'].parent.resolve())
    paths['presets'] = paths['sourcefiles'] / 'presets'
    paths['schemas'] = paths['sourcefiles'] / 'schemas'

    presets: List[Path] = [
        path
        for directory in [paths['presets'], paths['tests'] / 'data/presets']
        for path in directory.rglob('*.preset.json')
    ]
    presets_ids: List[str] = [str(path.parts[-1]) for path in presets]
    invalid_presets: List[Path] = [path for path in (paths['tests'] / 'data/invalid-presets').rglob('*.preset.json')]
    invalid_presets_ids: List[str] = [str(path.parts[-1]) for path in invalid_presets]


def pytest_addoption(parser):
    # pytest CLI option to run tests requiring local access to vanilla CT rom at location from $CTROM env var
    parser.addoption('--run-ctrom', action='store_true', default=False, help='run tests that require CT rom')


def pytest_configure(config):
    config.addinivalue_line('markers', 'ctrom: mark test requires CT rom to run')


def pytest_collection_modifyitems(config, items):
    '''Automatically skip tests marked with pytest.mark.ctrom unless --run-ctrom option passed.'''

    if config.getoption('--run-ctrom'):
        return

    skip_ctrom = pytest.mark.skip(reason='need --run-ctrom option to run')
    for item in items:
        if 'ctrom' in item.keywords:
            item.add_marker(skip_ctrom)


class TestHelpers:
    '''Re-useable static methods for testing.

    The methods can be used to make assertions instead of copy-pasting test code.
    '''

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
    return TestData.paths


@pytest.fixture(scope='session')
def presets(paths) -> List[Path]:
    '''All preset JSON files.'''
    return TestData.presets
