import pytest
import randosettings as rset

from randosettings import GameFlags as _GF
from randosettings import GameMode as _GM


ALL_KI_FLAGS: rset.GameFlags = _GF.RESTORE_JOHNNY_RACE | _GF.RESTORE_TOOLS | _GF.EPOCH_FAIL | _GF.ROCKSANITY
MOST_SPOT_FLAGS: rset.GameFlags = _GF.ADD_BEKKLER_SPOT | _GF.ADD_CYRUS_SPOT | _GF.ADD_OZZIE_SPOT | _GF.ADD_RACELOG_SPOT

# FIXTURES ###################################################################


@pytest.fixture(scope='function')
def settings():
    return rset.Settings()


# TESTS ###################################################################


@pytest.mark.parametrize(
    'mode, spot_flags, expected_flags',
    [
        (_GM.STANDARD, _GF.ADD_BEKKLER_SPOT | _GF.ADD_CYRUS_SPOT, ALL_KI_FLAGS),
        # no Epoch Fail / Ribbon for LW, nor other spots, so allget removed
        (_GM.LOST_WORLDS, MOST_SPOT_FLAGS | _GF.VANILLA_ROBO_RIBBON, _GF(0)),
        # need one more spot than standard because no black omen spot for rocksanity
        (_GM.ICE_AGE, _GF.ADD_BEKKLER_SPOT | _GF.ADD_OZZIE_SPOT | _GF.ADD_RACELOG_SPOT, ALL_KI_FLAGS),
        # no Johnny Race or Restore Tools for LoC
        (_GM.LEGACY_OF_CYRUS, MOST_SPOT_FLAGS, _GF.EPOCH_FAIL | _GF.ROCKSANITY),
        (_GM.VANILLA_RANDO, _GF.ADD_CYRUS_SPOT | _GF.ADD_OZZIE_SPOT, ALL_KI_FLAGS),
    ],
    ids=('std', 'lw', 'ia', 'loc', 'vr'),
)
def test_fix_flag_conflicts_adequate_spots(mode, spot_flags, expected_flags, settings):
    '''Check no unexpected flags added/removed when adequate spots.

    This test also partially covers _forced_off_dict being applied in fix_flag_conflicts by
    asserting that incompatible flags for the game mode are disabled.
    '''
    # turn on all the extra KI flags (some will be forced off based on mode)
    ki_flags = ALL_KI_FLAGS
    unexpected_flags = ki_flags - expected_flags

    settings.game_mode = mode
    settings.gameflags |= ki_flags | spot_flags

    settings.fix_flag_conflicts()

    assert _GF.VANILLA_ROBO_RIBBON not in settings.gameflags, 'Unexpected vanilla robo ribbon'

    # make sure incompatible flags get removed, but all other KI spots remain
    if mode == _GM.LOST_WORLDS:
        assert not settings.gameflags, 'Extra flags for Lost Worlds'
    else:
        assert expected_flags & settings.gameflags, 'Missing expected flags'
    assert not unexpected_flags & settings.gameflags, 'Unexpected incompatible flags'


@pytest.mark.parametrize(
    'mode, spot_flags, added, removed',
    [
        # no spots added, add ribbon and remove Epoch Fail
        (_GM.STANDARD, _GF(0), _GF.VANILLA_ROBO_RIBBON, _GF.EPOCH_FAIL),
        # added one spot, just ribbon
        (_GM.STANDARD, _GF.ADD_CYRUS_SPOT, _GF.VANILLA_ROBO_RIBBON, _GF(0)),
        # added one spot, adds ribbon and removes Epoch Fail since no Black Omen spot
        (_GM.ICE_AGE, _GF.ADD_OZZIE_SPOT, _GF.VANILLA_ROBO_RIBBON, _GF.EPOCH_FAIL),
        # no spots added, add ribbon since no Black Omen spot
        (_GM.LEGACY_OF_CYRUS, _GF(0), _GF.VANILLA_ROBO_RIBBON, _GF(0)),
    ],
    ids=('std', 'std+1', 'ia+1', 'loc'),
)
def test_fix_flag_conflicts_few_spots(mode, spot_flags, added, removed, settings):
    '''Check expected flags added/removed when not enough spots.'''
    # turn on all the extra KI flags (some will be forced off due to lacking spots)
    ki_flags = ALL_KI_FLAGS

    settings.game_mode = mode
    settings.gameflags |= ki_flags | spot_flags

    settings.fix_flag_conflicts()

    assert added & settings.gameflags, 'Missing expected additional flags'
    assert not removed & settings.gameflags, 'Unexpected additional flags'


@pytest.mark.parametrize(
    'flag, required',
    [
        (_GF.ROCKSANITY, _GF.UNLOCKED_SKYGATES),
        (_GF.DUPLICATE_CHARS, _GF.CHAR_RANDO),
    ],
    ids=('rocksanity', 'duplicate-chars'),
)
def test_fix_flag_conflicts_forces_on_required(flag, required, settings):
    '''Check that required flags are forced on when flags that depend on them are used.'''
    assert settings.gameflags == settings.gameflags & required, 'Unexpected required flags'

    settings.gameflags |= flag
    settings.fix_flag_conflicts()

    assert not (required - settings.gameflags), 'Missing required flags'


def test_fix_flag_conflicts_unfixable(settings):
    '''Check exception thrown when cannot adjust to have enough spots.'''
    settings.game_mode = _GM.ICE_AGE
    settings.gameflags |= ALL_KI_FLAGS
    with pytest.raises(ValueError) as ex:
        settings.fix_flag_conflicts()
    assert 'fix flag conflicts' in str(ex)
