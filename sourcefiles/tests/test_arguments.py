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
        (
            [],
            {
                'game_mode': GM.STANDARD,
                'item_difficulty': rset.Difficulty.NORMAL,
                'techorder': rset.TechOrder.FULL_RANDOM,
            },
        ),
        (
            [
                '--mode',
                'loc',
                '--boss-randomization',
                '--char-rando',
                '--gear-rando',
                '--zenan-alt-music',
                '--item-difficulty',
                'hard',
                '--enemy-difficulty',
                'hard',
                '--tech-order',
                'balanced',
                '--shop-prices',
                'free',
            ],
            {
                'game_mode': GM.LEGACY_OF_CYRUS,
                'gameflags': GF.BOSS_RANDO | GF.CHAR_RANDO | GF.GEAR_RANDO,
                'cosmetic_flags': CF.ZENAN_ALT_MUSIC,
                'item_difficulty': rset.Difficulty.HARD,
                'enemy_difficulty': rset.Difficulty.HARD,
                'techorder': rset.TechOrder.BALANCED_RANDOM,
                'shopprices': rset.ShopPrices.FREE,
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
    'cli_args, cls, init, expected_flags',
    [
        (
            ['--fix-glitch', '--zeal-end', '--fast-pendant'],
            arguments.GameFlagsAdapter,
            None,
            GF.FIX_GLITCH | GF.ZEAL_END | GF.FAST_PENDANT,
        ),
        (['--autorun', '--reduce-flashes'], arguments.CosmeticFlagsAdapter, None, CF.AUTORUN | CF.REDUCE_FLASH),
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
