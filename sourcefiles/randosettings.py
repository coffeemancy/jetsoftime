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
    BETA_LOGIC = auto()
    BUCKET_FRAGMENTS = auto()
    GUARANTEED_DROPS = auto()
    BUFF_XSTRIKE = auto()
    ICE_AGE = auto()
    LEGACY_OF_CYRUS = auto()


class CosmeticFlags(Flag):
    ZENAN_ALT_MUSIC = auto()
    DEATH_PEAK_ALT_MUSIC = auto()


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


@dataclass
class BucketSettings:
    num_fragments: int = 30
    needed_fragments: int = 20


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

        boss_list += [BossID.SON_OF_SUN, BossID.RETINITE,
                      BossID.MOTHER_BRAIN, BossID.GIGA_GAIA,
                      BossID.GUARDIAN]

        loc_list = LocID.get_boss_locations()
        # loc_list.remove(LocID.SUN_PALACE)
        # loc_list.remove(LocID.SUNKEN_DESERT_DEVOURER)

        self.ro_settings = ROSettings(loc_list, boss_list, False, False)
        self.bucket_settings = BucketSettings(30, 20)

        self.tab_settings = TabSettings()
        self.cosmetic_flags = CosmeticFlags(False)
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

        ret.gameflags = (GameFlags.FIX_GLITCH |
                         GameFlags.LOST_WORLDS |
                         GameFlags.ZEAL_END)

        ret.seed = ''
        return ret

    def get_hard_presets():
        ret = Settings()

        ret.item_difficulty = Difficulty.HARD
        ret.enemy_difficulty = Difficulty.HARD

        ret.shopprices = ShopPrices.NORMAL
        ret.techorder = TechOrder.BALANCED_RANDOM

        ret.gameflags = (GameFlags.FIX_GLITCH |
                         GameFlags.BOSS_SCALE |
                         GameFlags.LOCKED_CHARS)

        ret.seed = ''
        return ret

    def get_flag_string(self):
        # Flag string is based only on main game flags

        diff_str_dict = {
            Difficulty.EASY: 'e',
            Difficulty.NORMAL: 'n',
            Difficulty.HARD: 'h',
        }

        tech_str_dict = {
            TechOrder.FULL_RANDOM: 'te',
            TechOrder.BALANCED_RANDOM: 'tex',
            TechOrder.NORMAL: ''
        }

        flag_str_dict = {
            GameFlags.FIX_GLITCH: 'g',
            GameFlags.LOST_WORLDS: 'l',
            GameFlags.ICE_AGE: 'ia',
            GameFlags.LEGACY_OF_CYRUS: 'loc',
            GameFlags.BOSS_SCALE: 'b',
            GameFlags.BOSS_RANDO: 'ro',
            GameFlags.ZEAL_END: 'z',
            GameFlags.FAST_PENDANT: 'p',
            GameFlags.LOCKED_CHARS: 'c',
            GameFlags.UNLOCKED_MAGIC: 'm',
            GameFlags.QUIET_MODE: 'q',
            GameFlags.CHRONOSANITY: 'cr',
            GameFlags.TAB_TREASURES: 'tb',
            GameFlags.DUPLICATE_CHARS: 'dc',
        }

        shop_str_dict = {
            ShopPrices.FREE: 'spf',
            ShopPrices.MOSTLY_RANDOM: 'spm',
            ShopPrices.FULLY_RANDOM: 'spr',
            ShopPrices.NORMAL: ''
        }

        flag_string = ''

        # Now we have difficulty for enemies and items separated, but to
        # match the old flag string, just use enemy difficulty.
        flag_string += diff_str_dict[self.enemy_difficulty]

        for flag in flag_str_dict:
            if flag in self.gameflags:
                flag_string += flag_str_dict[flag]

        flag_string += tech_str_dict[self.techorder]
        flag_string += shop_str_dict[self.shopprices]

        return flag_string
