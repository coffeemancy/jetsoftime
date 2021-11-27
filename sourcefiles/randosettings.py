from __future__ import annotations
from enum import Flag, IntEnum, auto
from dataclasses import dataclass, field

from ctenums import BossID, LocID


class StrIntEnum(IntEnum):

    def __str__(self):
        x = self.__repr__().split('.')[1].split(':')[0].lower().capitalize()
        x = x.replace('_', ' ')
        return x

    @classmethod
    def str_dict(cls) -> dict:
        return dict((x, str(x)) for x in list(cls))

    @classmethod
    def inv_str_dict(cls) -> dict:
        return dict((str(x), x) for x in list(cls))


class Difficulty(StrIntEnum):
    EASY = 0
    NORMAL = 1
    HARD = 2


class TechOrder(StrIntEnum):
    NORMAL = 0
    FULL_RANDOM = 1
    BALANCED_RANDOM = 2


class ShopPrices(StrIntEnum):
    NORMAL = 0
    MOSTLY_RANDOM = 1
    FULLY_RANDOM = 2
    FREE = 3


class GameFlags(Flag):
    FIX_GLITCH = auto()
    LOST_WORLDS = auto()
    BOSS_SCALE = auto()
    ZEAL_END = auto()
    FAST_PENDANT = auto()
    LOCKED_CHARS = auto()
    UNLOCKED_MAGIC = auto()
    QUIET_MODE = auto()
    CHRONOSANITY = auto()
    TAB_TREASURES = auto()  # Maybe needs to be part of treasure page?
    BOSS_RANDO = auto()
    DUPLICATE_CHARS = auto()
    DUPLICATE_TECHS = auto()
    VISIBLE_HEALTH = auto()
    FAST_TABS = auto()


class TabRandoScheme(StrIntEnum):
    UNIFORM = 0
    BINOMIAL = 1


@dataclass
class TabSettings:
    scheme: TabRandoScheme = TabRandoScheme.UNIFORM
    binom_success: float = 0.5  # Only used by binom if set
    power_min: int = 2
    power_max: int = 4
    magic_min: int = 1
    magic_max: int = 3
    speed_min: int = 1
    speed_max: int = 1


@dataclass
class ROSettings:
    loc_list: list[BossID] = field(default_factory=list)
    boss_list: list[BossID] = field(default_factory=list)
    preserve_parts: bool = False
    enable_sightscope: bool = False


class Settings:

    def __init__(self):

        self.item_difficulty = Difficulty.NORMAL
        self.enemy_difficulty = Difficulty.NORMAL

        self.techorder = TechOrder.FULL_RANDOM
        self.shopprices = ShopPrices.NORMAL

        self.gameflags = GameFlags.FIX_GLITCH
        self.char_choices = [[i for i in range(7)] for j in range(7)]

        boss_list = \
            BossID.get_one_part_bosses() + BossID.get_two_part_bosses()

        boss_list += [BossID.SON_OF_SUN, BossID.RETINITE]

        loc_list = LocID.get_boss_locations()
        # loc_list.remove(LocID.SUN_PALACE)
        # loc_list.remove(LocID.SUNKEN_DESERT_DEVOURER)

        self.ro_settings = ROSettings(loc_list, boss_list, False, False)

        self.tab_settings = TabSettings()
        self.seed = ''

    def get_race_presets():
        ret = Settings()

        ret.item_difficulty = Difficulty.NORMAL
        ret.enemy_difficulty = Difficulty.NORMAL

        ret.shopprices = ShopPrices.NORMAL
        ret.techorder = TechOrder.FULL_RANDOM

        ret.gameflags = (GameFlags.FIX_GLITCH |
                         GameFlags.FAST_PENDANT |
                         GameFlags.ZEAL_END)

        ret.seed = ''

        return ret

    def get_new_player_presets():
        ret = Settings()

        ret.item_difficulty = Difficulty.EASY
        ret.enemy_difficulty = Difficulty.NORMAL

        ret.shopprices = ShopPrices.NORMAL
        ret.techorder = TechOrder.FULL_RANDOM

        ret.gameflags = (GameFlags.FIX_GLITCH |
                         GameFlags.FAST_PENDANT |
                         GameFlags.ZEAL_END |
                         GameFlags.UNLOCKED_MAGIC |
                         GameFlags.VISIBLE_HEALTH |
                         GameFlags.FAST_TABS)

        ret.seed = ''

        return ret

    def get_lost_worlds_presets():
        ret = Settings()

        ret.item_difficulty = Difficulty.NORMAL
        ret.enemy_difficulty = Difficulty.NORMAL

        ret.shopprices = ShopPrices.NORMAL
        ret.techorder = TechOrder.FULL_RANDOM

        ret.gameflags = (GameFlags.LOST_WORLDS |
                         GameFlags.ZEAL_END)

        ret.seed = ''
        return ret

    def get_hard_presets():
        ret = Settings()

        ret.item_difficulty = Difficulty.HARD
        ret.enemy_difficulty = Difficulty.HARD

        ret.shopprices = ShopPrices.NORMAL
        ret.techorder = TechOrder.BALANCED_RANDOM

        ret.gameflags = (GameFlags.BOSS_SCALE |
                         GameFlags.LOCKED_CHARS)

        # All bosses, all spots
        ret.ro_settings = ROSettings(
            LocID.get_boss_locations(),
            list(BossID),
            False
        )

        ret.seed = ''
        return ret
