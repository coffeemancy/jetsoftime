import sys

from pathlib import Path
from typing import Dict

import pytest

# add sourcefiles to import search path
sys.path.append(str(Path(__file__).parent.parent))


@pytest.fixture(scope='session')
def paths() -> Dict[str, Path]:
    paths = {'tests': Path(__file__).parent.resolve()}
    paths['sourcefiles'] = Path(paths['tests'].parent.resolve())
    paths['presets'] = paths['sourcefiles'] / 'presets'
    return paths
