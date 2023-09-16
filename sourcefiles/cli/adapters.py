from __future__ import annotations
import argparse
import functools
import operator

from typing import Any, Dict, Mapping, Optional, Protocol, Union, Type

import randosettings as rset

from cli.constants import FLAG_ENTRY_DICT, FlagEntry
from randosettings import GameMode as GM

SettingsFlags = Union[rset.GameFlags, rset.CosmeticFlags]


class SettingsAdapter(Protocol):
    '''Protocol to adapt CLI arguments to Settings object attributes.

    These classes are used to provide a consistent interface for converting CLI argparse arguments
    into attributes for a randosettings.Settings object (.to_setting classmethod). Some adapters
    set a single value (e.g. GameModeAdapter) while others build and set complex nested objects
    (e.g. MysterySettingsAdapter).
    '''

    # mapping of argument (per argparse.Namespace) mapped to values related to Settings attribute
    _adapter: Mapping[str, Any] = {}
    _cls: Type[Any]

    @classmethod
    def get(cls, arg: str) -> Any:
        '''Get attribute values associated with specified argparse argument.'''
        key = arg.lstrip('-').replace('-', '_')
        return cls._adapter[key]

    @classmethod
    def to_setting(cls, args: argparse.Namespace):
        raise NotImplementedError


class ArgumentAdapter(SettingsAdapter):
    '''Adapter for converting single CLI arg directly into a setting.'''

    _adapter: Mapping[str, rset.StrIntEnum] = {}
    _arg: str
    _cls: Type[rset.StrIntEnum]

    @classmethod
    def to_setting(cls, args: argparse.Namespace) -> rset.StrIntEnum:
        '''Get coerced setting from args or default.'''
        if cls._arg in args:
            choice = getattr(args, cls._arg)
            return cls._adapter[choice.lower()]
        return cls._cls.default()


class GameModeAdapter(ArgumentAdapter):
    _adapter: Dict[str, rset.GameMode] = {
        'std': GM.STANDARD,
        'lw': GM.LOST_WORLDS,
        'loc': GM.LEGACY_OF_CYRUS,
        'ia': GM.ICE_AGE,
        'van': GM.VANILLA_RANDO,
    }
    _arg = 'mode'
    _cls = rset.GameMode


class DifficultyAdapter(ArgumentAdapter):
    _adapter: Dict[str, rset.Difficulty] = {
        'easy': rset.Difficulty.EASY,
        'normal': rset.Difficulty.NORMAL,
        'hard': rset.Difficulty.HARD,
    }
    _cls = rset.Difficulty


class EnemyDifficultyAdapter(DifficultyAdapter):
    _arg = 'enemy_difficulty'


class ItemDifficultyAdapter(DifficultyAdapter):
    _arg = 'item_difficulty'


class TechOrderAdapter(ArgumentAdapter):
    _adapter: Dict[str, rset.TechOrder] = {
        'normal': rset.TechOrder.NORMAL,
        'balanced': rset.TechOrder.BALANCED_RANDOM,
        'random': rset.TechOrder.FULL_RANDOM,
    }
    _arg = 'tech_order'
    _cls = rset.TechOrder


class ShopPricesAdapter(ArgumentAdapter):
    _adapter: Dict[str, rset.ShopPrices] = {
        'normal': rset.ShopPrices.NORMAL,
        'random': rset.ShopPrices.FULLY_RANDOM,
        'mostrandom': rset.ShopPrices.MOSTLY_RANDOM,
        'free': rset.ShopPrices.FREE,
    }
    _arg = 'shop_prices'
    _cls = rset.ShopPrices


class FlagsAdapter(SettingsAdapter):
    '''Adapter for converting arguments into a Flag.'''

    _cls: Type[SettingsFlags]

    @classmethod
    def to_setting(cls, args: argparse.Namespace, init: Optional[SettingsFlags] = None) -> SettingsFlags:
        if init is None:
            init = cls._cls(0)
        flags = (
            flag
            for (flag, entry) in FLAG_ENTRY_DICT.items()
            if isinstance(flag, cls._cls) and getattr(args, cls._flag_to_arg(entry), None) is True
        )
        return functools.reduce(operator.or_, flags, init)

    @staticmethod
    def _flag_to_arg(entry: FlagEntry) -> str:
        return entry.name.lstrip('-').replace('-', '_')


class GameFlagsAdapter(FlagsAdapter):
    _cls = rset.GameFlags


class CosmeticFlagsAdapter(FlagsAdapter):
    _cls = rset.CosmeticFlags
