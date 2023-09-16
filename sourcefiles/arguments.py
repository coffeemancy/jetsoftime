from __future__ import annotations
import argparse
import copy
import functools
import operator

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Generator, Mapping, Optional, Protocol, Union, Tuple, Type

import ctstrings
import ctoptions
import objectivehints as obhint
import randosettings as rset

from randosettings import Difficulty, TechOrder, ShopPrices
from randosettings import GameFlags as GF, GameMode as GM, CosmeticFlags as CF

SettingsFlags = Union[rset.GameFlags, rset.CosmeticFlags]

# Flags ######################################################################

@dataclass
class FlagEntry:
    name: str = ""
    short_name: Optional[str] = None
    help_text: Optional[str] = None


_flag_entry_dict: Dict[SettingsFlags, FlagEntry] = {
    GF.FIX_GLITCH: FlagEntry(
        "--fix-glitch", "-g",
        "disable save anywhere and HP overflow glitches"),
    GF.BOSS_SCALE: FlagEntry(
        "--boss-scale", "-b",
        "scale bosses based on key-item locations"),
    GF.ZEAL_END: FlagEntry(
        "--zeal-end", "-z",
        "allow the game to be won when Zeal is defeated in the "
        "Black Omen"),
    GF.FAST_PENDANT: FlagEntry(
        "--fast-pendant", "-p",
        "the pendant will be charged when 2300 is reached"),
    GF.LOCKED_CHARS: FlagEntry(
        "--locked-chars", "-c",
        "require dreamstone for the dactyl character and factory for "
        "the Proto Dome character"),
    GF.UNLOCKED_MAGIC: FlagEntry(
        "--unlocked-magic", "-m",
        "magic is unlocked from the beginning of the game without "
        "visiting Spekkio"),
    GF.CHRONOSANITY: FlagEntry(
        "--chronosanity", "-cr",
        "key items may be found in treasure chests"),
    GF.ROCKSANITY: FlagEntry(
        "--rocksanity", None,
        "rocks are added as key items and key items may be found "
        "in rock locations"),
    GF.TAB_TREASURES: FlagEntry(
        "--tab-treasures", None,
        "all treasure chests contain tabs"),
    GF.BOSS_RANDO: FlagEntry(
        "--boss-randomization", "-ro",
        "randomize the location of bosses and scale based on location"),
    GF.CHAR_RANDO: FlagEntry(
        "--char-rando", "-rc",
        "randomize character identities and models"), 
    GF.DUPLICATE_CHARS: FlagEntry(
        "--duplicate-characters", "-dc",
        "allow multiple copies of a character to be present in a seed"),
    GF.DUPLICATE_TECHS: FlagEntry(
        "--duplicate-techs", None,
        "allow duplicate characters to perform dual techs together"),
    GF.VISIBLE_HEALTH: FlagEntry(
        "--visible-health", None,
        "the sightscope effect will always be present"),
    GF.FAST_TABS: FlagEntry(
        "--fast-tabs", None,
        "picking up a tab will not pause movement for the fanfare"),
    GF.BUCKET_LIST: FlagEntry(
        "--bucket-list", "-k",
        "allow the End of Time bucket to Lavos to activate when enough "
        "objectives have been completed."),
    GF.TECH_DAMAGE_RANDO: FlagEntry(
        "--tech-damage-rando", None,
        "Randomize the damage dealt by single techs."),
    GF.MYSTERY: FlagEntry(
        "--mystery", None,
        "choose flags randomly according to mystery settings"),
    GF.BOSS_SIGHTSCOPE: FlagEntry(
        "--boss-sightscope", None,
        "allow the sightscope to work on bosses"),
    GF.USE_ANTILIFE: FlagEntry(
        "--use-antilife", None,
        "use Anti-Life instead of Black Hole for Magus"),
    GF.TACKLE_EFFECTS_ON: FlagEntry(
        "--tackle-on-hit-effects", None,
        "allow Robo Tackle to use the on-hit effects of Robo's weapons"),
    GF.HEALING_ITEM_RANDO: FlagEntry(
        "--healing-item-rando", "-he",
        "randomizes effects of healing items"),
    GF.FREE_MENU_GLITCH: FlagEntry(
        "--free-menu-glitch", None,
        "provides a longer window to enter the menu prior to Lavos3 and "
        "Zeal2"),
    GF.GEAR_RANDO: FlagEntry(
        "--gear-rando", "-q",
        "randomizes effects on weapons, armors, and accessories"),
    GF.STARTERS_SUFFICIENT: FlagEntry(
        "--starters-sufficient", None,
        "go mode will be acheivable without recruiting additional "
        "characters"),
    GF.EPOCH_FAIL: FlagEntry(
        "--epoch-fail", "-ef",
        "Epoch flight must be unlocked by bringing the JetsOfTime to "
        "Dalton in the Snail Stop"),
    GF.BOSS_SPOT_HP: FlagEntry(
        "--boss-spot-hp",
        "boss HP is set to match the vanilla boss HP in each spot"),
    # Logic Tweak flags from VanillaRando mode
    GF.UNLOCKED_SKYGATES: FlagEntry(
        "--unlocked-skyways", None,
        "Skyways are available as soon as 12kBC is. Normal go mode is still "
        "needed to unlock the Ocean Palace."),
    GF.ADD_SUNKEEP_SPOT: FlagEntry(
        "--add-sunkeep-spot", None,
        "Adds Sun Stone as an independent key item.  Moonstone charges to a "
        "random item"),
    GF.ADD_BEKKLER_SPOT: FlagEntry(
        "--add-bekkler-spot", None,
        "C.Trigger unlocks clone game for a KI"),
    GF.ADD_CYRUS_SPOT: FlagEntry(
        "--add-cyrus-spot", None,
        "Gain a KI from Cyrus's Grave w/ Frog.  No Frog stat boost."),
    GF.RESTORE_TOOLS: FlagEntry(
        "--restore-tools", None,
        "Adds Tools. Tools will fix Norther Ruins."),
    GF.ADD_OZZIE_SPOT: FlagEntry(
        "--add-ozzie-spot", None, "Gain a KI after Ozzie's Fort."),
    GF.RESTORE_JOHNNY_RACE: FlagEntry(
        "--restore-johnny-race", None,
        "Add bike key and Johnny Race. Bike Key is required to cross Lab32."),
    GF.ADD_RACELOG_SPOT: FlagEntry(
        "--add-racelog-spot", None,
        "Gain a KI from the vanilla Race Log chest."),
    GF.REMOVE_BLACK_OMEN_SPOT: FlagEntry(
        "--remove-black-omen-spot", None,
        "Removes Black Omen rock chest being a possible KI."),
    GF.SPLIT_ARRIS_DOME: FlagEntry(
        "--split-arris-dome", None,
        "Get one key item from the dead guy after Guardian.  Get a second "
        "after checking the Arris dome computer and bringing the Seed "
        "(new KI) to Doan."),
    GF.VANILLA_ROBO_RIBBON: FlagEntry(
        "--vanilla-robo-ribbon", None,
        "Gain Robo stat boost from defeating AtroposXR.  If no Atropos in "
        "seed, then gain from Geno Dome."),
    GF.VANILLA_DESERT: FlagEntry(
        "--vanilla-desert", None,
        "The sunken desert only unlocks after talking to the plant lady "
        "in Zeal"),
    # Cosmetic Flags
    CF.AUTORUN: FlagEntry(
        "--autorun", None,
        "Automatically run.  Push run button to walk."
    ),
    CF.DEATH_PEAK_ALT_MUSIC: FlagEntry(
        "--death-peak-alt-music", None,
        "use Singing Mountain track on Death Peak"
    ),
    CF.ZENAN_ALT_MUSIC: FlagEntry(
        "--zenan-alt-music", None,
        "use alt battle theme for Zenan Bridge"
    ),
    CF.QUIET_MODE: FlagEntry(
        "--quiet", None,
        "disable all music (not sound effects)"
    ),
    CF.REDUCE_FLASH: FlagEntry(
        "--reduce-flashes", None,
        "disable most flashing effects"
    )
}


# Adapters and Settings ######################################################


def load_preset(attr: str, impl: Type[Any]):
    '''Decorate SettingsAdapter classmethod to inject initialized object or copy from preset.'''
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(cls, args: argparse.Namespace):
            # copy value from preset or initialize new object
            if 'preset' in args:
                obj = copy.deepcopy(getattr(args.preset, attr))
            else:
                obj = impl()
            # inject object as last parameter in wrapped classmethod
            return fn(cls, args, obj)
        return wrapper
    return decorator


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
    _field: str

    @classmethod
    def to_setting(cls, args: argparse.Namespace):
        '''Get coerced setting from args, preset, or default.'''
        if cls._arg in args:
            choice = getattr(args, cls._arg)
            return cls._adapter[choice.lower()]
        elif 'preset' in args:
            return copy.deepcopy(getattr(args.preset, cls._field))
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
    _field = 'game_mode'


class DifficultyAdapter(ArgumentAdapter):
    _adapter: Dict[str, Difficulty] = {'easy': Difficulty.EASY, 'normal': Difficulty.NORMAL, 'hard': Difficulty.HARD}
    _cls = Difficulty


class EnemyDifficultyAdapter(DifficultyAdapter):
    _arg = 'enemy_difficulty'
    _field = 'enemy_difficulty'


class ItemDifficultyAdapter(DifficultyAdapter):
    _arg = 'item_difficulty'
    _field = 'item_difficulty'


class TechOrderAdapter(ArgumentAdapter):
    _adapter: Dict[str, TechOrder] = {
        'normal': TechOrder.NORMAL,
        'balanced': TechOrder.BALANCED_RANDOM,
        'random': TechOrder.FULL_RANDOM,
    }
    _arg = 'tech_order'
    _cls = TechOrder
    _field = 'techorder'


class ShopPricesAdapter(ArgumentAdapter):
    _adapter: Dict[str, ShopPrices] = {
        'normal': ShopPrices.NORMAL,
        'random': ShopPrices.FULLY_RANDOM,
        'mostrandom': ShopPrices.MOSTLY_RANDOM,
        'free': ShopPrices.FREE,
    }
    _arg = 'shop_prices'
    _cls = ShopPrices
    _field = 'shopprices'


class FlagsAdapter(SettingsAdapter):
    '''Adapter for converting arguments into a Flag.'''

    _cls: Type[SettingsFlags]
    _field: str

    @classmethod
    def get(cls, arg: str) -> SettingsFlags:
        '''Get Flag associated with specified argparse argument.'''
        for flag, entry in _flag_entry_dict.items():
            if cls._flag_to_arg(entry) == arg:
                return flag
        else:
            raise KeyError(f"No flag associated with '{arg}'")

    @classmethod
    def to_setting(cls, args: argparse.Namespace, init: Optional[SettingsFlags] = None):
        if init is None:
            if 'preset' in args:
                # add flags to flags loaded from preset
                init = copy.deepcopy(getattr(args.preset, cls._field))
            else:
                init = cls._cls(0)
        flags = (
            flag
            for (flag, entry) in _flag_entry_dict.items()
            if isinstance(flag, cls._cls) and getattr(args, cls._flag_to_arg(entry), None) is True
        )
        return functools.reduce(operator.or_, flags, init)

    @staticmethod
    def _flag_to_arg(entry: FlagEntry) -> str:
        return entry.name.lstrip('-').replace('-', '_')


class GameFlagsAdapter(FlagsAdapter):
    _cls = rset.GameFlags
    _field = 'gameflags'


class CosmeticFlagsAdapter(FlagsAdapter):
    _cls = rset.CosmeticFlags
    _field = 'cosmetic_flags'


class BucketSettingsAdapter(SettingsAdapter):
    _adapter: Dict[str, str] = {
        'bucket_disable_other_go': 'disable_other_go_modes',
        'bucket_objectives_win': 'objectives_win',
        'bucket_objective_count': 'num_objectives',
        'bucket_objective_needed_count': 'num_objectives_needed',
    }
    _cls = rset.BucketSettings

    @classmethod
    @load_preset('bucket_settings', rset.BucketSettings)
    def to_setting(cls, args: argparse.Namespace, bset: rset.BucketSettings) -> rset.BucketSettings:
        '''Extract BucketSettings from argparse.Namespace.'''
        for arg, prop in cls._adapter.items():
            if arg in args:
                setattr(bset, prop, getattr(args, arg))

        # objectives
        objectives = (getattr(args, f"bucket_objective{obj}", None) for obj in range(1, bset.num_objectives + 1))
        hints: List[str] = [hint for hint in objectives if hint is not None]
        if hints:
            bset.hints = hints

        return bset


class TabSettingsAdapter(SettingsAdapter):
    _adapter: Dict[str, str] = {
        'min_power_tab': 'power_min',
        'max_power_tab': 'power_max',
        'min_magic_tab': 'magic_min',
        'max_magic_tab': 'magic_max',
        'min_speed_tab': 'speed_min',
        'max_speed_tab': 'speed_max',
        'tab_binom_success': 'binom_success',
    }
    _cls = rset.TabSettings

    @classmethod
    @load_preset('tab_settings', rset.TabSettings)
    def to_setting(cls, args: argparse.Namespace, tset: rset.TabSettings):
        '''Extract TabSettings from argparse.Namespace.'''
        for arg, prop in cls._adapter.items():
            if arg in args:
                setattr(tset, prop, getattr(args, arg))

        if 'tab_scheme' in args:
            scheme = getattr(args, 'tab_scheme')
            if scheme == 'binomial':
                setattr(tset, 'scheme', rset.TabRandoScheme.BINOMIAL)
            elif scheme == 'uniform':
                setattr(tset, 'scheme', rset.TabRandoScheme.UNIFORM)
            else:
                raise ValueError(f"Invalid tab scheme: {scheme}")

        return tset


class CTOptsAdapter(SettingsAdapter):
    _adapter: Dict[str, str] = {
        'save_menu_cursor': 'save_menu_cursor',
        'save_battle_cursor': 'save_battle_cursor',
        'save_skill_cursor_off': 'save_tech_cursor',
        'skill_item_info_off': 'skill_item_info',
        'consistent_paging': 'consistent_paging',
        'battle_speed': 'battle_speed',
        'battle_msg_speed': 'battle_msg_speed',
        'battle_gauge_style': 'battle_gauge_style',
        'background': 'menu_background',
    }
    _cls = ctoptions.CTOpts

    @classmethod
    @load_preset('ctoptions', ctoptions.CTOpts)
    def to_setting(cls, args: argparse.Namespace, ct_opts: ctoptions.CTOpts) -> ctoptions.CTOpts:
        '''Extract CTOpts from argparse.Namespace.'''
        inverted_args = ['save_skill_cursor_off', 'skill_item_info_off']
        plus_one_args = ['battle_speed', 'battle_msg_speed', 'background']

        for arg, prop in cls._adapter.items():
            if arg in args:
                if arg in inverted_args:
                    setattr(ct_opts, prop, not getattr(args, arg))
                elif arg in plus_one_args:
                    setattr(ct_opts, prop, getattr(args, arg) - 1)
                else:
                    setattr(ct_opts, prop, getattr(args, arg))
        return ct_opts


class CharSettingsAdapter(SettingsAdapter):
    _cls = Type[rset.CharSettings]

    @classmethod
    @load_preset('char_settings', rset.CharSettings)
    def to_setting(cls, args: argparse.Namespace, charset: rset.CharSettings) -> rset.CharSettings:
        '''Extract CharSettings from argparse.Namespace.'''
        for name in rset.CharNames.default():
            name_arg = f"{name.lower()}_name"
            if name_arg in args:
                charset.names[name] = getattr(args, name_arg)

            choices_arg = f"{name.lower()}_choices"
            if choices_arg in args:
                charset.choices[name] = getattr(args, choices_arg)

        return charset


class MysterySettingsAdapter(SettingsAdapter):
    _adapter: Dict[str, Tuple[str, Any]] = {
        # game_mode_freqs
        'mystery_mode_std': ('game_mode_freqs', GM.STANDARD),
        'mystery_mode_lw': ('game_mode_freqs', GM.LOST_WORLDS),
        'mystery_mode_loc': ('game_mode_freqs', GM.LEGACY_OF_CYRUS),
        'mystery_mode_ia': ('game_mode_freqs', GM.ICE_AGE),
        'mystery_mode_van': ('game_mode_freqs', GM.VANILLA_RANDO),
        #  item_difficulty_freqs
        'mystery_item_easy': ('item_difficulty_freqs', Difficulty.EASY),
        'mystery_item_norm': ('item_difficulty_freqs', Difficulty.NORMAL),
        'mystery_item_hard': ('item_difficulty_freqs', Difficulty.HARD),
        # enemy_difficulty_freqs
        'mystery_enemy_norm': ('enemy_difficulty_freqs', Difficulty.NORMAL),
        'mystery_enemy_hard': ('enemy_difficulty_freqs', Difficulty.HARD),
        # tech_order_freqs
        'mystery_tech_norm': ('tech_order_freqs', TechOrder.NORMAL),
        'mystery_tech_balanced': ('tech_order_freqs', TechOrder.BALANCED_RANDOM),
        'mystery_tech_rand': ('tech_order_freqs', TechOrder.FULL_RANDOM),
        # shop_price_freqs
        'mystery_prices_norm': ('shop_price_freqs', ShopPrices.NORMAL),
        'mystery_prices_mostly_rand': ('shop_price_freqs', ShopPrices.MOSTLY_RANDOM),
        'mystery_prices_rand': ('shop_price_freqs', ShopPrices.FULLY_RANDOM),
        'mystery_prices_free': ('shop_price_freqs', ShopPrices.FREE),
        # flag_prob_dict
        'mystery_flag_tab_treasures': ('flag_prob_dict', GF.TAB_TREASURES),
        'mystery_flag_unlocked_magic': ('flag_prob_dict', GF.UNLOCKED_MAGIC),
        'mystery_flag_bucket_list': ('flag_prob_dict', GF.BUCKET_LIST),
        'mystery_flag_chronosanity': ('flag_prob_dict', GF.CHRONOSANITY),
        'mystery_flag_boss_rando': ('flag_prob_dict', GF.BOSS_RANDO),
        'mystery_flag_boss_scaling': ('flag_prob_dict', GF.BOSS_SCALE),
        'mystery_flag_locked_chars': ('flag_prob_dict', GF.LOCKED_CHARS),
        'mystery_flag_char_rando': ('flag_prob_dict', GF.CHAR_RANDO),
        'mystery_flag_duplicate_chars': ('flag_prob_dict', GF.DUPLICATE_CHARS),
        'mystery_flag_epoch_fail': ('flag_prob_dict', GF.EPOCH_FAIL),
        'mystery_flag_gear_rando': ('flag_prob_dict', GF.GEAR_RANDO),
        'mystery_flag_heal_rando': ('flag_prob_dict', GF.HEALING_ITEM_RANDO),
    }
    _cls = rset.MysterySettings

    @classmethod
    def args(cls, field: str) -> Generator[Tuple[str, Any], None, None]:
        '''Get all CLI arguments and key in field in MysterySettings.'''
        for arg, (item_field, key) in cls._adapter.items():
            if item_field == field:
                yield (arg, key)

    @classmethod
    @load_preset('mystery_settings', rset.MysterySettings)
    def to_setting(cls, args: argparse.Namespace, mset: rset.MysterySettings) -> rset.MysterySettings:
        '''Get mystery settings from args.

        This creates a MysterySettings object where all explicitly-passed values from the CLI
        override the inherent defaults. Values not explicitly passed are suppressed by
        the parser and will not override the defaults from randosettings.MysterySettings.
        '''
        for arg, (field, key) in cls._adapter.items():
            if arg in args:
                attr = getattr(mset, field)
                attr[key] = getattr(args, arg)
        return mset


def args_to_settings(args: argparse.Namespace) -> rset.Settings:
    '''Convert result of argparse to settings object.'''
    ret_set = rset.Settings()
    if 'seed' in args:
        ret_set.seed = args.seed
    ret_set.game_mode = GameModeAdapter.to_setting(args)
    ret_set.gameflags = GameFlagsAdapter.to_setting(args)
    ret_set.initial_flags = copy.deepcopy(ret_set.gameflags)
    ret_set.item_difficulty = ItemDifficultyAdapter.to_setting(args)
    ret_set.enemy_difficulty = EnemyDifficultyAdapter.to_setting(args)
    ret_set.techorder = TechOrderAdapter.to_setting(args)
    ret_set.shopprices = ShopPricesAdapter.to_setting(args)
    ret_set.mystery_settings = MysterySettingsAdapter.to_setting(args)
    ret_set.tab_settings = TabSettingsAdapter.to_setting(args)
    ret_set.cosmetic_flags = CosmeticFlagsAdapter.to_setting(args)
    ret_set.ctoptions = CTOptsAdapter.to_setting(args)
    ret_set.char_settings = CharSettingsAdapter.to_setting(args)
    ret_set.bucket_settings = BucketSettingsAdapter.to_setting(args)
    return ret_set


# Arguments and Parser #######################################################

class Argument:
    '''Container for argparse argument for use with ArgumentGroup classes.

    Sets most arguments to use argparse.SUPPRESS default, meaning unless explicitly
    passed on CLI, will not end up in argparse.Namespace. Code within SettingsAdapter
    checks for this, and when suppressed, does not override the default values
    assigned when randosettings.Settings is initialized. This prevents needing to
    double set default values in this file and elsewhere and prevents such regressions.
    '''
    name: Tuple[str, ...]
    options: Dict[str, Any]

    def __init__(self, *name: str, **options):
        if not options.get('required') and 'default' not in options:
            options['default'] = argparse.SUPPRESS
        self.name = name
        self.options = options

    @property
    def arg(self) -> str:
        longname = next(name for name in self.name if name.startswith('--'))
        return longname.lstrip('-').replace('-', '_')


class ArgumentGroup(Protocol):
    '''Protocol for building argparse argument groups and attaching to parser.'''

    # argument group title and description
    _title: str
    _desc: Optional[str] = None

    @classmethod
    def arguments(cls) -> Generator[Argument, None, None]:
        '''Yield arguments from group.'''
        raise NotImplementedError(f"Missing .arguments definition for '{cls}'.")

    @classmethod
    def add_to_parser(cls, parser: argparse.ArgumentParser) -> argparse._ArgumentGroup:
        '''Create argument group, add all arguments to it, and attach to parser.'''
        group = parser.add_argument_group(cls._title, description=cls._desc)
        for arg in cls.arguments():
            group.add_argument(*arg.name, **arg.options)
        return group


class FlagsArgumentGroup(ArgumentGroup):
    '''Implemention of ArgumentGroup for arguments related to Flag options.'''

    # list of flags which should have an argument created (one per flag)
    _flags: List[SettingsFlags]

    @classmethod
    def arguments(cls) -> Generator[Argument, None, None]:
        for flag in cls._flags:
            flag_entry = _flag_entry_dict[flag]
            name = [flag_entry.name]
            if flag_entry.short_name is not None:
                name.append(flag_entry.short_name)
            yield Argument(*name, help=flag_entry.help_text, action='store_true')


class BasicFlagsAG(FlagsArgumentGroup):
    _title = 'Basic Flags'
    _flags = [
        GF.FIX_GLITCH, GF.BOSS_SCALE, GF.ZEAL_END, GF.FAST_PENDANT, GF.LOCKED_CHARS, GF.UNLOCKED_MAGIC,
        GF.CHRONOSANITY, GF.TAB_TREASURES, GF.BOSS_RANDO, GF.CHAR_RANDO, GF.MYSTERY, GF.HEALING_ITEM_RANDO,
        GF.GEAR_RANDO, GF.EPOCH_FAIL
    ]


class QoLFlagsAG(FlagsArgumentGroup):
    _title = 'QoL Flags'
    _flags = [GF.FAST_TABS, GF.VISIBLE_HEALTH, GF.BOSS_SIGHTSCOPE, GF.FREE_MENU_GLITCH]


class ExtraFlagsAG(FlagsArgumentGroup):
    _title = 'Extra Flags'
    _flags = [GF.STARTERS_SUFFICIENT, GF.USE_ANTILIFE, GF.TACKLE_EFFECTS_ON, GF.BUCKET_LIST, GF.TECH_DAMAGE_RANDO]


class LogicKIFlagsAG(FlagsArgumentGroup):
    _title = 'Logic Tweak Flags that add a KI'
    _flags = [GF.RESTORE_JOHNNY_RACE, GF.RESTORE_TOOLS]


class LogicSpotFlagsAG(FlagsArgumentGroup):
    _title = 'Logic Tweak Flags that add/remove a KI Spot'
    _flags = [
        GF.ADD_BEKKLER_SPOT, GF.ADD_OZZIE_SPOT, GF.ADD_RACELOG_SPOT, GF.ADD_CYRUS_SPOT, GF.VANILLA_ROBO_RIBBON,
        GF.REMOVE_BLACK_OMEN_SPOT
    ]


class LogicNeutralFlagsAG(FlagsArgumentGroup):
    _title = 'Logic Flags that are KI/KI Spot Neutral'
    _flags = [GF.UNLOCKED_SKYGATES, GF.ADD_SUNKEEP_SPOT, GF.SPLIT_ARRIS_DOME, GF.VANILLA_DESERT, GF.ROCKSANITY]


class CosmeticsFlagsAG(FlagsArgumentGroup):
    _title = 'Cosmetic Flags'
    _desc = 'Have no effect on randomization.'
    _flags = [CF.AUTORUN, CF.DEATH_PEAK_ALT_MUSIC, CF.ZENAN_ALT_MUSIC, CF.QUIET_MODE, CF.REDUCE_FLASH]


class BucketListAG(ArgumentGroup):
    _title = '--bucket-list [-k] options'

    @classmethod
    def arguments(cls) -> Generator[Argument, None, None]:
        bset = rset.BucketSettings()
        yield Argument(
            '--bucket-objective-count',
            help=f"Number of objectives to use. [{bset.num_objectives}]",
            type=int,
        )
        yield Argument(
            '--bucket-objective-needed-count',
            help=f"Number of objectives needed to meet goal. [{bset.num_objectives_needed}]",
            type=int,
        )
        yield Argument(
            '--bucket-objectives-win',
            help=f"Objectives win game instead of unlocking bucket. [{bset.objectives_win}]",
            action='store_true',
        )
        yield Argument(
            '--bucket-disable-other-go',
            help=f"The only way to win is through the bucket. [{bset.disable_other_go_modes}]",
            action='store_true',
        )
        for obj in range(1, 9):
            yield Argument(f"--bucket-objective{obj}", f"-obj{obj}", type=cls._check_bucket_objective)

    @staticmethod
    def _check_bucket_objective(hint: str) -> str:
        valid, msg = obhint.is_hint_valid(hint)
        if not valid:
            raise argparse.ArgumentTypeError(f"Invalid bucket objective: '{msg}'")
        return hint


class BossRandoAG(ArgumentGroup):
    _title = '-ro Options'
    _desc = 'These options are only valid when --boss-randomization [-ro] is set'

    @classmethod
    def arguments(cls) -> Generator[Argument, None, None]:
        yield Argument(
            '--boss-spot-hp',
            help='boss HP is set to match the vanilla boss HP in each spot',
            action='store_true',
        )


class CharNamesAG(ArgumentGroup):
    _title = 'Character Names'

    @classmethod
    def arguments(cls) -> Generator[Argument, None, None]:
        for char_name in rset.CharNames.default():
            yield Argument(f"--{char_name.lower()}-name", help=f"[{char_name}]", type=cls._verify_name)

    @staticmethod
    def _verify_name(string: str) -> str:
        if len(string) > 5:
            raise argparse.ArgumentTypeError('Name must have length 5 or less.')
        try:
            ctnamestr = ctstrings.CTNameString.from_string(string, 5)
        except ctstrings.InvalidSymbolException as exc:
            raise argparse.ArgumentTypeError(f"Invalid symbol: '{exc}'")
        return string


class CharRandoAG(ArgumentGroup):
    _title = '-rc Options'
    _desc = 'These options are only valid when --char-rando [-rc] is set'

    @classmethod
    def arguments(cls) -> Generator[Argument, None, None]:
        yield Argument(
            '--duplicate-characters', '-dc',
            help='Allow multiple copies of a character to be present in a seed.',
            action='store_true',
        )
        yield Argument(
            '--duplicate-techs',
            help='Allow duplicate characters to perform dual techs together.',
            action='store_true',
        )
        yield Argument(
            '--crono-choices',
            help='The characters Crono is allowed to be assigned. For example, '
            '--crono-choices "lucca robo" would allow Crono to be assigned to '
            'either Lucca or Robo.  If the list is preceded with "not" '
            '(e.g. not lucca ayla) then all except the listed characters will be '
            'allowed.',
        )
        for name in rset.CharNames.default()[1:-1]:
            yield Argument(f"--{name.lower()}-choices", help='Same as --crono-choices.')


class GameOptionsAG(ArgumentGroup):
    _title = 'Game Options'
    _desc = ''

    @classmethod
    def arguments(cls) -> Generator[Argument, None, None]:
        ct_default = ctoptions.CTOpts()

        menu_opts = (
            ('--save-menu-cursor', 'save last used page of X-menu'),
            ('--save-battle-cursor', 'save battle cursor position'),
            ('--save-skill-cursor-off', 'do not save position in skill/item menu'),
            ('--skill-item-info-off', 'do not show skill/item descriptions'),
            ('--consistent-paging', 'page up/down have the same effect in all menus'),
        )

        for name, desc in menu_opts:
            default: Any = bool(getattr(ct_default, CTOptsAdapter.get(name)))
            if name.endswith('-off'):
                default = not default
            desc = f"{desc} [{default}]"
            yield Argument(name, help=desc, action="store_true")

        plus_one_opts = (
            ('--battle-speed', 'default battle speed (lower is faster)'),
            ('--battle-msg-speed', 'default battle message speed (lower is faster)'),
            ('--background', 'default background'),
        )
        for name, desc in plus_one_opts:
            default = int(getattr(ct_default, CTOptsAdapter.get(name))) + 1
            desc = f"{desc} [{default}]"
            yield Argument(name, help=desc, type=int, choices=range(1, 9))

        default = int(getattr(ct_default, CTOptsAdapter.get('battle_gauge_style')))
        desc = f"default atb gauge style [{default}]"
        yield Argument('--battle-gauge-style', help=desc, type=int, choices=range(3))


class GeneralOptionsAG(ArgumentGroup):
    _title = 'General options'

    @classmethod
    def arguments(cls) -> Generator[Argument, None, None]:
        diff_default = str(Difficulty.default()).lower()
        yield Argument(
            '--mode',
            choices=['std', 'lw', 'ia', 'loc', 'van'],
            help="R|"
            "the basic game mode\n"
            " std: standard Jets of Time [default]\n"
            "  lw: lost worlds\n"
            "  ia: ice age\n"
            " loc: legacy of cyrus\n"
            " van: vanilla rando",
            type=str.lower,
        )
        yield Argument(
            '--item-difficulty', '-idiff',
            help=f"controls quality of treasure, drops, and starting gold [{diff_default}]",
            choices=['easy', 'normal', 'hard'],
            type=str.lower,
        )
        yield Argument(
            '--enemy-difficulty', '-ediff',
            help=f"controls strength of enemies and xp/tp rewards [{diff_default}]",
            choices=['normal', 'hard'],
            type=str.lower,
        )
        yield Argument(
            '--tech-order',
            help="R|"
            "controls the order in which characters learn techs\n"
            "  normal - vanilla tech order\n"
            "balanced - random but biased towards better techs later\n"
            "  random - fully random [default]",
            choices=['normal', 'balanced', 'random'],
            type=str.lower,
        )
        yield Argument(
            '--shop-prices',
            help="R|"
            "controls the prices in shops\n"
            "    normal - standard prices [default]\n"
            "    random - fully random prices\n"
            "mostrandom - random except for staple consumables\n"
            "      free - all items cost 1G",
            choices=['normal', 'random', 'mostrandom', 'free'],
            type=str.lower,
        )


class GenerationOptionsAG(ArgumentGroup):
    _title = 'Generation options'

    @classmethod
    def arguments(cls) -> Generator[Argument, None, None]:
        yield Argument(
            '--input-file', '-i',
            required=True,
            help='path to Chrono Trigger (U) rom',
            type=Path,
        )
        yield Argument(
            '--output-path', '-o',
            help='path to output directory (default same as input)',
            default=None,
            type=Path,
        )
        yield Argument(
            '--seed',
            help='seed for generation (not website share id)',
        )
        yield Argument(
            '--spoilers',
            help='generate spoilers with the randomized rom.',
            default=None,
            action='store_true',
        )
        yield Argument(
            '--json-spoilers',
            help='generate json spoilers with the randomized rom.',
            default=None,
            action='store_true',
        )
        yield Argument(
            '--preset',
            help='path to preset JSON file from which to load settings',
            type=cls.load_preset
        )

    @classmethod
    def load_preset(cls, preset: Union[str, Path]) -> rset.Settings:
        try:
            data = rset.Settings.from_preset_file(Path(preset))
        except Exception as ex:
            raise argparse.ArgumentTypeError(f"Failed to parse preset as JSON: {preset}") from ex
        return data


class MysterySettingsArgumentGroup(ArgumentGroup):
    '''Implementation of ArgumentGroup for building arguments for mystery options.'''

    # field from randosettings.MysterySettings to build arguments
    _field: str

    @classmethod
    def arguments(cls) -> Generator[Argument, None, None]:
        ms_default = rset.MysterySettings()

        for arg, key in MysterySettingsAdapter.args(cls._field):
            flag = f"--{arg.replace('_', '-')}"
            rel_freq = ms_default[cls._field][key]
            desc = "[%d]" % rel_freq
            yield Argument(flag, type=cls._check_non_neg, help=desc)

    @staticmethod
    def _check_non_neg(value) -> int:
        ivalue = int(value)
        if ivalue < 0:
            raise argparse.ArgumentTypeError(f"Invalid negative frequency: {value}")
        return ivalue


class MysteryModeAG(MysterySettingsArgumentGroup):
    _title = 'Mystery Game Mode relative frequency (only with --mystery)'
    _desc = 'Set the relative frequency with which each game mode can appear. These must be non-negative integers.'
    _field = 'game_mode_freqs'


class MysteryItemDiffAG(MysterySettingsArgumentGroup):
    _title = 'Mystery Item Difficulty relative frequency (only with --mystery)'
    _field = 'item_difficulty_freqs'


class MysteryEnemyDiffAG(MysterySettingsArgumentGroup):
    _title = 'Mystery Enemy Difficulty relative frequency (only with --mystery)'
    _field = 'enemy_difficulty_freqs'


class MysteryTechOrderAG(MysterySettingsArgumentGroup):
    _title = 'Mystery Tech Order relative frequency (only with --mystery)'
    _field = 'tech_order_freqs'


class MysteryShopPricesAG(MysterySettingsArgumentGroup):
    _title = 'Mystery Shop Price relative frequency (only with --mystery)'
    _field = 'shop_price_freqs'


class MysteryFlagsAG(ArgumentGroup):
    _title = 'Mystery Flags Probabilities (only with --mystery)'
    _desc = (
        'The chance that a flag will be set in  the mystery settings. '
        'All flags not listed here will be set as they are in the main settings.'
    )

    @classmethod
    def arguments(cls) -> Generator[Argument, None, None]:
        ms_default = rset.MysterySettings()

        for arg, key in MysterySettingsAdapter.args('flag_prob_dict'):
            flag = f"--{arg.replace('_', '-')}"
            prob = ms_default['flag_prob_dict'][key]
            desc = "[%0.2f]" % prob
            yield Argument(flag, type=cls._check_prob, help=desc)

    @staticmethod
    def _check_prob(val) -> float:
        fval = float(val)
        if not 0 <= fval <= 1:
            raise argparse.ArgumentTypeError(f"Invalid probability (must be in [0,1]): {fval}")
        return fval


class TabSettingsAG(ArgumentGroup):
    _title = 'Tab Settings'

    @classmethod
    def arguments(cls) -> Generator[Argument, None, None]:
        tabset = rset.TabSettings()
        yield Argument(
            '--min-power-tab',
            help=f"The minimum value a power tab can increase power by [{tabset.power_min}]",
            type=int,
            choices=range(1, 10),
        )
        yield Argument(
            '--max-power-tab',
            help=f"The maximum value a power tab can increase power by [{tabset.power_max}]",
            type=int,
            choices=range(1, 10),
        )
        yield Argument(
            '--min-magic-tab',
            help=f"The minimum value a magic tab can increase power by [{tabset.magic_min}]",
            type=int,
            choices=range(1, 10),
        )
        yield Argument(
            '--max-magic-tab',
            help=f"The maximum value a magic tab can increase power by [{tabset.magic_max}]",
            type=int,
            choices=range(1, 10),
        )
        yield Argument(
            '--min-speed-tab',
            help=f"The minimum value a speed tab can increase power by [{tabset.speed_min}]",
            type=int,
            choices=range(1, 10),
        )
        yield Argument(
            '--max-speed-tab',
            help=f"The maximum value a speed tab can increase power by [{tabset.speed_max}]",
            type=int,
            choices=range(1, 10),
        )
        scheme = str(tabset.scheme).lower()
        yield Argument(
            '--tab-scheme',
            help=f"Probability distribution scheme for tabs [{scheme}]",
            choices=['uniform', 'binomial'],
        )
        yield Argument(
            '--tab-binom-success',
            help=f"Success probability for tabs (when binomial scheme used) [{tabset.binom_success}]",
            type=float,
        )


# https://stackoverflow.com/questions/3853722/
# how-to-insert-newlines-on-argparse-help-text
class SmartFormatter(argparse.HelpFormatter):
    def _split_lines(self, text, width):
        if text.startswith('R|'):
            return text[2:].splitlines()
        # this is the RawTextHelpFormatter._split_lines
        return argparse.HelpFormatter._split_lines(self, text, width)


# list of all non-cosmetic argument groups affecting seed generation
# these are selected prior to generation in the web GUI and may be included in a preset
ALL_GENERATION_AG: List[Type[ArgumentGroup]] = [
    GeneralOptionsAG,
    BasicFlagsAG,
    BossRandoAG,
    CharRandoAG,
    TabSettingsAG,
    QoLFlagsAG,
    ExtraFlagsAG,
    LogicKIFlagsAG,
    LogicSpotFlagsAG,
    LogicNeutralFlagsAG,
    BucketListAG,
    MysteryModeAG,
    MysteryItemDiffAG,
    MysteryEnemyDiffAG,
    MysteryTechOrderAG,
    MysteryShopPricesAG,
    MysteryFlagsAG,
]

# list of all argument groups affectiong cosmetics
# these can be selected after seed generation in the web GUI and are not included in a preset
ALL_COSMETIC_AG: List[Type[ArgumentGroup]] = [
    CosmeticsFlagsAG,
    CharNamesAG,
    GameOptionsAG,
]


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(formatter_class=SmartFormatter)
    groups: List[Type[ArgumentGroup]] = [GenerationOptionsAG]
    groups.extend(ALL_GENERATION_AG)
    groups.extend(ALL_COSMETIC_AG)
    for ag in groups:
        ag.add_to_parser(parser)
    return parser
