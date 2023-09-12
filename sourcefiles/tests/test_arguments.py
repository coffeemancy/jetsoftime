from __future__ import annotations
import pytest

import arguments
import randosettings as rset

from randosettings import CosmeticFlags as CF, GameFlags as GF, GameMode as GM


@pytest.fixture(scope='session')
def parser():
    return arguments.get_parser()


@pytest.mark.parametrize(
    'cli_args, expected_settings',
    [
        # defaults
        (
            [],
            {
                'game_mode': GM.STANDARD,
                'item_difficulty': rset.Difficulty.NORMAL,
                'techorder': rset.TechOrder.FULL_RANDOM,
            },
        ),
        # overriding most non-flag settings
        (
            (
                '--mode loc --boss-randomization --char-rando --gear-rando --zenan-alt-music'
                ' --item-difficulty hard --enemy-difficulty hard --tech-order balanced'
                ' --shop-prices free --frog-name Glenn --epoch-name Apoch'
            ).split(' '),
            {
                'game_mode': GM.LEGACY_OF_CYRUS,
                'gameflags': GF.BOSS_RANDO | GF.CHAR_RANDO | GF.GEAR_RANDO,
                'cosmetic_flags': CF.ZENAN_ALT_MUSIC,
                'item_difficulty': rset.Difficulty.HARD,
                'enemy_difficulty': rset.Difficulty.HARD,
                'techorder': rset.TechOrder.BALANCED_RANDOM,
                'shopprices': rset.ShopPrices.FREE,
                'char_names': ['Crono', 'Marle', 'Lucca', 'Robo', 'Glenn', 'Ayla', 'Magus', 'Apoch'],
            },
        ),
    ],
    ids=('defaults', 'complex'),
)
def test_args_to_settings(cli_args, expected_settings, parser):
    args = parser.parse_args(cli_args + ['-i', 'ct.rom'])
    settings = arguments.args_to_settings(args)

    assert settings
    assert isinstance(settings, rset.Settings), f"Wrong type for settings: {type(settings)}"

    for attr, value in expected_settings.items():
        assert getattr(settings, attr) == value


@pytest.mark.parametrize(
    'cli_args, expected_choices',
    [
        # default all characters to all
        (
            [],
            [
                [0, 1, 2, 3, 4, 5, 6],
                [0, 1, 2, 3, 4, 5, 6],
                [0, 1, 2, 3, 4, 5, 6],
                [0, 1, 2, 3, 4, 5, 6],
                [0, 1, 2, 3, 4, 5, 6],
                [0, 1, 2, 3, 4, 5, 6],
                [0, 1, 2, 3, 4, 5, 6],
            ],
        ),
        # cover various options for character restriction including specifying characters,
        # specificying "all", defaulting to all, and specifying "not" (can be other characters)
        (
            [
                '--crono-choices=robo magus',
                '--marle-choices=marle lucca ayla',
                '--lucca-choices=crono lucca robo frog ayla',
                '--robo-choices=all',
                '--frog-choices=not magus crono',
                '--ayla-choices=ayla',
            ],
            [
                [3, 6],
                [1, 2, 5],
                [0, 2, 3, 4, 5],
                [0, 1, 2, 3, 4, 5, 6],
                [1, 2, 3, 4, 5],
                [5],
                [0, 1, 2, 3, 4, 5, 6],
            ],
        ),
    ],
    ids=('default', 'restricted'),
)
def test_char_choices(cli_args, expected_choices, parser):
    args = parser.parse_args(cli_args + ['-i', 'ct.rom'])
    settings = arguments.args_to_settings(args)

    assert settings.char_choices == expected_choices


@pytest.mark.parametrize(
    'cli_args, cls, init, expected_flags',
    [
        # game flags
        (
            ['--fix-glitch', '--zeal-end', '--fast-pendant'],
            arguments.GameFlagsAdapter,
            None,
            GF.FIX_GLITCH | GF.ZEAL_END | GF.FAST_PENDANT,
        ),
        # cosmetic flags
        (['--autorun', '--reduce-flashes'], arguments.CosmeticFlagsAdapter, None, CF.AUTORUN | CF.REDUCE_FLASH),
        # starting with initial flags and adding more game flags from CLI args
        (
            ['--chronosanity', '--unlocked-skyways'],
            arguments.GameFlagsAdapter,
            GF.FIX_GLITCH | GF.FAST_TABS,
            GF.FIX_GLITCH | GF.FAST_TABS | GF.CHRONOSANITY | GF.UNLOCKED_SKYGATES,
        ),
    ],
    ids=('gameflags', 'cosmetic_flags', 'init'),
)
def test_flags_adapters(cli_args, cls, init, expected_flags, parser):
    args = parser.parse_args(cli_args + ['-i', 'ct.rom'])

    flags = cls.to_setting(args, init=init)
    expected_type = type(expected_flags)

    assert isinstance(flags, expected_type), f"Flags are not expected type: {expected_type}"
    assert flags == expected_flags, 'Flags do not match expected flags'
