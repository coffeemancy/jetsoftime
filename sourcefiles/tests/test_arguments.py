import pytest

import arguments

from randosettings import CosmeticFlags as CF, GameFlags as GF


@pytest.fixture(scope='session')
def parser():
    return arguments.get_parser()


@pytest.mark.parametrize(
    'cli_args, init, expected_flags',
    [
        (['--fix-glitch', '--zeal-end', '--fast-pendant'], GF(0), GF.FIX_GLITCH | GF.ZEAL_END | GF.FAST_PENDANT),
        (['--autorun', '--reduce-flashes'], CF(0), CF.AUTORUN | CF.REDUCE_FLASH),
        (
            ['--chronosanity', '--unlocked-skyways'],
            GF.FIX_GLITCH | GF.FAST_TABS,
            GF.FIX_GLITCH | GF.FAST_TABS | GF.CHRONOSANITY | GF.UNLOCKED_SKYGATES,
        ),
    ],
    ids=('gameflags', 'cosmetic_flags', 'init'),
)
def test_fill_flags(cli_args, init, expected_flags, parser):
    args = parser.parse_args(cli_args + ['-i', 'ct.rom'])
    val_dict = vars(args)

    flags = arguments.fill_flags(val_dict, init)
    expected_type = type(expected_flags)

    assert isinstance(flags, expected_type), f"Flags are not expected type: {expected_type}"
    assert flags == expected_flags, 'Flags do not match expected flags'
