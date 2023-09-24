from __future__ import annotations
import bossrandotypes as brt

import pytest


@pytest.mark.parametrize('cls', [brt.BossID, brt.BossSpotID])
def test_coherence(cls, helpers):
    for item in cls:
        helpers.check_enum_coherence(cls, item)


@pytest.mark.parametrize(
    'boss, expected',
    [
        (brt.BossID.MAGUS_NORTH_CAPE, 'Magus (North Cape)'),
        (brt.BossID.YAKRA_XIII, 'Yakra XIII'),
        (brt.BossID.NIZBEL_2, 'Nizbel II'),
    ],
    ids=('Magus (North Cape)', 'Yakra XIII', 'Nizbel II'),
)
def test_irregular_boss_id(boss, expected):
    '''Check bosses that don't use standard stringification algorithm.'''
    assert str(boss) == expected
