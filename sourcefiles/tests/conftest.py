from __future__ import annotations
import sys

from enum import Enum
from typing import Type

from pathlib import Path

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
