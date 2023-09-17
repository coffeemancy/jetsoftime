'''
Tests for sourcefiles/arguments.py.

This file ends up exercising and covering a lot of settings-related code across arguments.py,
randosettings.py, ctoptions.py, bossrandotypes.py, and more, because it tests from passing CLI args through
the argparse parser to randosettings.args_to_settings creating a Settings object, and makes assertions about
that which cover testing settings for GameMode, GameFlags, CosmeticFlags, item and enemy difficulty,
TechOrder, ShopPrices, character names and settings (CharSettings), BucketSettings and more.
'''
from __future__ import annotations
import pytest

import arguments
import cli.adapters as adp
import ctoptions
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
                'enemy_difficulty': rset.Difficulty.NORMAL,
                'techorder': rset.TechOrder.FULL_RANDOM,
                'shopprices': rset.ShopPrices.NORMAL,
                'tab_settings': rset.TabSettings(),
                'char_settings': rset.CharSettings(),
            },
        ),
        # overriding most non-flag settings
        (
            (
                '--mode loc --boss-randomization --char-rando --gear-rando --zenan-alt-music'
                ' --item-difficulty hard --enemy-difficulty hard --tech-order balanced'
                ' --shop-prices free'
            ).split(' '),
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

    assert settings.char_settings.choices == expected_choices


@pytest.mark.parametrize(
    'cli_args, expected_names',
    [
        # default
        ([], ['Crono', 'Marle', 'Lucca', 'Robo', 'Frog', 'Ayla', 'Magus', 'Epoch']),
        # overrides
        (
            '--frog-name Glenn --marle-name Nadia --epoch-name Apoch'.split(' '),
            ['Crono', 'Nadia', 'Lucca', 'Robo', 'Glenn', 'Ayla', 'Magus', 'Apoch'],
        ),
    ],
    ids=('default', 'override'),
)
def test_char_names(cli_args, expected_names, parser):
    args = parser.parse_args(cli_args + ['-i', 'ct.rom'])
    settings = arguments.args_to_settings(args)

    assert settings.char_settings.names == expected_names


@pytest.mark.parametrize(
    'cli_args, expected_settings',
    [
        # default
        (
            [],
            {
                'battle_speed': 4,
                'save_menu_cursor': 0,
                'skill_item_info': 1,
                'menu_background': 0,
                'battle_msg_speed': 4,
                'save_battle_cursor': 0,
                'save_tech_cursor': 1,
                'battle_gauge_style': 1,
            },
        ),
        # override all ctoptions
        (
            (
                '--battle-speed=1 --save-menu-cursor --skill-item-info-off --background=3'
                ' --battle-msg-speed 1 --save-battle-cursor --save-skill-cursor-off'
                ' --battle-gauge-style 2'
            ).split(' '),
            {
                'battle_speed': 0,
                'save_menu_cursor': 1,
                'skill_item_info': 0,
                'menu_background': 2,
                'battle_msg_speed': 0,
                'save_battle_cursor': 1,
                'save_tech_cursor': 0,
                'battle_gauge_style': 2,
            },
        ),
    ],
    ids=('default', 'complex'),
)
def test_ctoptions_settings(cli_args, expected_settings, parser):
    args = parser.parse_args(cli_args + ['-i', 'ct.rom'])
    ctopts = arguments.args_to_settings(args).ctoptions

    assert isinstance(ctopts, ctoptions.CTOpts), f"Wrong type: {type(ctopts)}"

    for attr, value in expected_settings.items():
        assert getattr(ctopts, attr) == value


@pytest.mark.parametrize(
    'cli_args, cls, init, expected_flags',
    [
        # game flags
        (
            ['--fix-glitch', '--zeal-end', '--fast-pendant'],
            adp.GameFlagsAdapter,
            None,
            GF.FIX_GLITCH | GF.ZEAL_END | GF.FAST_PENDANT,
        ),
        # cosmetic flags
        (['--autorun', '--reduce-flashes'], adp.CosmeticFlagsAdapter, None, CF.AUTORUN | CF.REDUCE_FLASH),
        # starting with initial flags and adding more game flags from CLI args
        (
            ['--chronosanity', '--unlocked-skyways'],
            adp.GameFlagsAdapter,
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
