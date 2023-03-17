import argparse
from dataclasses import dataclass
import functools
import typing

import ctenums
import randosettings as rset
from randosettings import GameFlags as GF, GameMode as GM

@dataclass
class FlagEntry:
    name: str = ""
    short_name: typing.Optional[str] = None
    help_text: typing.Optional[str] = None


_flag_entry_dict: dict[GF, FlagEntry] = {
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
    GF.TAB_TREASURES: FlagEntry(
        "--tab-treasures", None,
        "all treasure chests contain tabs"),
    GF.BOSS_RANDO: FlagEntry(
        "--boss-randomization", "-ro",
        "randomize the location of bosses and scale based on location"),
    GF.DUPLICATE_CHARS: FlagEntry(
        "--duplicate-characters", "-dc",
        "allow multiple copies of a character to be present in a seed"),
    GF.DUPLICATE_TECHS: FlagEntry(
        "--duplicate-techs", None,
        "Allow duplicate characters to perform dual techs together."),
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
    GF.SPLIT_ARRIS_DOME: FlagEntry(
        "--split-arris=dome", None,
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
        "in Zeal")
}

_mode_dict: dict[str, GM] = {
    'std': GM.STANDARD,
    'lw': GM.LOST_WORLDS,
    'loc': GM.LEGACY_OF_CYRUS,
    'ia': GM.ICE_AGE,
    'van': GM.VANILLA_RANDO
}

_diff_dict: dict[str, rset.Difficulty] = {
    'easy': rset.Difficulty.EASY,
    'normal': rset.Difficulty.NORMAL,
    'hard': rset.Difficulty.HARD
}

_tech_order_dict: dict[str, rset.TechOrder] = {
    'normal': rset.TechOrder.NORMAL,
    'balanced': rset.TechOrder.BALANCED_RANDOM,
    'random': rset.TechOrder.FULL_RANDOM
}

_shop_price_dict: dict[str, rset.ShopPrices] = {
    'normal': rset.ShopPrices.NORMAL,
    'random': rset.ShopPrices.FULLY_RANDOM,
    'mostrandom': rset.ShopPrices.MOSTLY_RANDOM,
    'free': rset.ShopPrices.FREE
}

def add_flags_to_parser(
        group_text: typing.Optional[str],
        flag_list: typing.Iterable[GF],
        parser: argparse.ArgumentParser):

    add_target: typing.Union[argparse.ArgumentParser,
                             argparse._ArgumentGroup]

    if group_text is None:
        add_target = parser
    else:
        group = parser.add_argument_group(group_text)
        add_target = group

    for flag in flag_list:
        flag_entry = _flag_entry_dict[flag]
        add_args: typing.Iterable[str]
        if flag_entry.short_name is None:
            add_args = (flag_entry.name,)
        else:
            add_args = (flag_entry.name, flag_entry.short_name)
        add_target.add_argument(
            *add_args,
            help=flag_entry.help_text,
            action="store_true"
        )

def flag_name_to_namespace_key(flag_name: str):
    return flag_name[2:].replace('-','_')
        
# https://stackoverflow.com/questions/3853722/
# how-to-insert-newlines-on-argparse-help-text
class SmartFormatter(argparse.HelpFormatter):

    def _split_lines(self, text, width):
        if text.startswith('R|'):
            return text[2:].splitlines()
        # this is the RawTextHelpFormatter._split_lines
        return argparse.HelpFormatter._split_lines(self, text, width)


def get_bucket_settings(args: argparse.Namespace) -> rset.BucketSettings:
    '''Extract BucketSettings from argparse.Namespace.'''
    # TODO:
    return rset.BucketSettings()


_pc_index_dict: dict[str, int] = {
    'crono': 0,
    'marle': 1,
    'lucca': 2,
    'robo': 3,
    'frog': 4,
    'ayla': 5,
    'magus': 6
}


def get_dc_choices(args: argparse.Namespace) -> list[list[int]]:
    '''Extract dc-flag settings from argparse.Namespace.'''

    arg_dict = vars(args)
    def parse_choices(choice_string: str) -> list[int]:
        choice_string = choice_string.lower()

        if choice_string == 'all':
            return [val for val in range(7)]

        choices = choice_string.split()
        if choices[0] == 'not':
            choices = choices[1:]
            choice_ints = [_pc_index_dict[choice] for choice in choices]
            return [ind for ind in range(7) if ind not in choice_ints]
        else:
            choice_ints = [_pc_index_dict[choice] for choice in choices]
            return [ind for ind in range(7) if ind in choice_ints]

    namespace_vars = [name + '_choices' for name in _pc_index_dict]
    
    return [parse_choices(arg_dict[name]) for name in namespace_vars]


def args_to_settings(args: argparse.Namespace) -> rset.Settings:
    '''Convert result of argparse to settings object.'''

    val_dict = vars(args)
    # Fill GameFlags
    flags = functools.reduce(
        lambda x, y: x | y,
        (flag for flag, entry in _flag_entry_dict.items()
         if val_dict[flag_name_to_namespace_key(entry.name)] is True),
        GF(0)
    )

    mode = _mode_dict[val_dict['mode']]
    item_difficulty = _diff_dict[val_dict['item_difficulty']]
    enemy_difficulty = _diff_dict[val_dict['enemy_difficulty']]
    tech_order = _tech_order_dict[val_dict['tech_order']]

    ret_set = rset.Settings()
    ret_set.game_mode = mode
    ret_set.gameflags = flags
    ret_set.item_difficulty = item_difficulty
    ret_set.enemy_difficulty = enemy_difficulty
    ret_set.techorder = tech_order

    return ret_set


def get_parser():
    parser = argparse.ArgumentParser(formatter_class=SmartFormatter)

    parser.add_argument(
        "--mode",
        choices=['std', 'lw', 'ia', 'loc', 'van'],
        help="R|"
        "the basic game mode\n"
        " std: standard Jets of Time (default)\n"
        "  lw: lost worlds\n"
        "  ia: ice age\n"
        " loc: legacy of cyrus\n"
        " van: vanilla rando",
        default='std',
        type=str.lower
    )

    parser.add_argument(
        "--item-difficulty", "-idiff",
        help="controls quality of treasure, drops, and starting gold "
        "(default: normal)",
        choices=['easy','normal', 'hard'],
        default='normal',
        type=str.lower
    )

    parser.add_argument(
        "--enemy-difficulty", "-ediff",
        help="controls strength of enemies and xp/tp rewards "
        "(default: normal)",
        choices=['normal', 'hard'],
        default='normal',
        type=str.lower
    )

    parser.add_argument(
        "--tech-order",
        help="R|"
        "controls the order in which characters learn techs\n"
        "  normal - vanilla tech order\n"
        "balanced - random but biased towards better techs later\n"
        "  random - fully random (default)",
        choices=['normal', 'balanced', 'random'],
        default='normal',
        type=str.lower
    )

    parser.add_argument(
        "--shop_prices",
        help="R|"
        "controls the prices in shops\n"
        "    normal - standard prices (default)\n"
        "    random - fully random prices\n"
        "mostrandom - random except for staple consumables\n"
        "      free - all items cost 1G",
        choices=['normal', 'random', 'mostrandom', 'free'],
        default='normal',
        type=str.lower
    )

    add_flags_to_parser(
        'Basic Flags',
        (GF.FIX_GLITCH, GF.BOSS_SCALE, GF.ZEAL_END, GF.FAST_PENDANT,
         GF.LOCKED_CHARS, GF.UNLOCKED_MAGIC, GF.CHRONOSANITY,
         GF.TAB_TREASURES, GF.BOSS_RANDO, GF.DUPLICATE_CHARS,
         GF.MYSTERY, GF.HEALING_ITEM_RANDO, GF.GEAR_RANDO,
         GF.EPOCH_FAIL), parser
    )

    add_flags_to_parser(
        'QoL Flags',
        (GF.FAST_TABS, GF.VISIBLE_HEALTH, GF.BOSS_SIGHTSCOPE,
         GF.FREE_MENU_GLITCH),
        parser
    )

    add_flags_to_parser(
        "Extra Flags",
        (GF.STARTERS_SUFFICIENT, GF.USE_ANTILIFE, GF.TACKLE_EFFECTS_ON,
         GF.BUCKET_LIST),
        parser
    )

    add_flags_to_parser(
        "Logic Tweak Flags that add a KI",
        (GF.RESTORE_JOHNNY_RACE, GF.RESTORE_TOOLS),
        parser
    )

    add_flags_to_parser(
        "Logic Tweak Flags that add a KI Spot",
        (GF.ADD_BEKKLER_SPOT, GF.ADD_OZZIE_SPOT, GF.ADD_RACELOG_SPOT,
         GF.ADD_CYRUS_SPOT, GF.VANILLA_ROBO_RIBBON),
        parser
    )

    add_flags_to_parser(
        "Logic Flags that are KI/KI Spot Neutral",
        (GF.UNLOCKED_SKYGATES, GF.ADD_SUNKEEP_SPOT, GF.SPLIT_ARRIS_DOME,
         GF.VANILLA_DESERT),
        parser
    )

    bucket_options = parser.add_argument_group(
        "--bucket-list [-k] options"
    )

    bucket_options.add_argument(
        "--bucket-objective-count",
        help="Number of objectives to use.",
        type=int,
        default=5
    )

    bucket_options.add_argument(
        "--bucket-objective-needed_count",
        help="Number of objectives needed to meet goal.",
        type=int,
        default=3
    )

    bucket_options.add_argument(
        "--bucket-objectives-win",
        help="Objectives win game instead of unlocking bucket.",
        action="store_true"
    )

    bucket_options.add_argument(
        "--bucket-disable-other-go",
        help="The only way to win is through the bucket.",
        action="store_true"
    )

    for obj_ind in range(8):
        bucket_options.add_argument(
            "--bucket-objective"+str(obj_ind+1), "-obj"+str(obj_ind+1),
            default="random"
        )

    # Boss Rando Options
    ro_options = parser.add_argument_group(
        "-ro Options",
        "These options are only valid when --boss-randomization [-ro] is set"
    )
    ro_options.add_argument(
        "--boss-spot-hp",
        help="boss HP is set to match the vanilla boss HP in each spot",
        action="store_true"
    )

    # Duplicate Character Options
    dc_options = parser.add_argument_group(
        "-dc Options",
        "These options are only valid when --duplicate-characters [-dc] "
        "is set"
    )

    dc_options.add_argument(
        "--duplicate-techs",
        help="Allow duplicate characters to perform dual techs together.",
        action="store_true"
    )

    dc_options.add_argument(
        "--crono-choices",
        help="The characters Crono is allowed to be assigned. For example, "
        "--crono-choices \"lucca robo\" would allow Crono to be assigned to "
        "either Lucca or Robo.  If the list is preceded with \"not\" "
        "(e.g. not lucca ayla) then all except the listed characters will be "
        "allowed.",
        default="all"
    )

    dc_options.add_argument(
        "--marle-choices",
        help="Same as --crono-choices.",
        default="all"
    )

    dc_options.add_argument(
        "--lucca-choices",
        help="Same as --crono-choices.",
        default="all"
    )

    dc_options.add_argument(
        "--robo-choices",
        help="Same as --crono-choices.",
        default="all"
    )

    dc_options.add_argument(
        "--frog-choices",
        help="Same as --crono-choices.",
        default="all"
    )

    dc_options.add_argument(
        "--ayla-choices",
        help="Same as --crono-choices.",
        default="all"
    )

    dc_options.add_argument(
        "--magus-choices",
        help="Same as --crono-choices.",
        default="all"
    )

    # Tab Options
    tab_options = parser.add_argument_group(
        "Tab Settings"
    )

    tab_options.add_argument(
        "--min-power_tab",
        help="The minimum value a power tab can increase power by (default 2)",
        default=1,
        type=int,
        choices=range(1, 10)
    )

    tab_options.add_argument(
        "--max-power_tab",
        help="The maximum value a power tab can increase power by (default 4)",
        default=1,
        type=int,
        choices=range(1, 10)
    )

    tab_options.add_argument(
        "--min-magic-tab",
        help="The minimum value a magic tab can increase power by (default 1)",
        default=1,
        type=int,
        choices=range(1, 10)
    )

    tab_options.add_argument(
        "--max-magic-tab",
        help="The maximum value a magic tab can increase power by (default 3)",
        default=1,
        type=int,
        choices=range(1, 10)
    )

    tab_options.add_argument(
        "--min-speed-tab",
        help="The minimum value a speed tab can increase power by (default 1)",
        default=1,
        type=int,
        choices=range(1, 10)
    )

    tab_options.add_argument(
        "--max-speed-tab",
        help="The maximum value a speed tab can increase power by (default 1)",
        default=1,
        type=int,
        choices=range(1, 10)
    )

    mystery_flag_prob_entries = [
        ("flag_tab_treasures", 0.10),
        ("flag_unlocked_magic", 0.50),
        ("flag_bucket_list", 0.15),
        ("flag_chronosanity", 0.30),
        ("flag_boss_rando", 0.50),
        ("flag_boss_scaling", 0.30),
        ("flag_locked_chars", 0.25),
        ("flag_duplicate_chars", 0.25),
        ("flag_epoch_fail", 0.50),
        ("flag_gear_rando", 0.25),
        ("flag_heal_rando", 0.25),
    ]

    def check_non_neg(value):
        ivalue = int(value)
        if ivalue < 0:
            raise argparse.ArgumentTypeError(
                "%s is an invalide negative frequency" % value
            )

        return ivalue

    def fill_mystery_freq_group(freq_dict, arg_group: argparse._ArgumentGroup):
        for string, rel_freq in freq_dict:
            arg_group.add_argument(
                "--mystery_"+string,
                type=check_non_neg,
                help="default: %d" % rel_freq,
                default=rel_freq,
            )

    mystery_modes = parser.add_argument_group(
        "Mystery Game Mode relative frequency (only if --mystery is set). "
        "Set the relative frequency with which "
        "each game mode can appear.  These must be non-negative integers." 
    )

    mystery_mode_freq_entries = [
        ("mode_std", 1), ("mode_lw", 1), ("mode_loc", 1),
        ("mode_ia", 1), ("mode_van", 0),
    ]

    fill_mystery_freq_group(mystery_mode_freq_entries, mystery_modes)

    mystery_item_diff = parser.add_argument_group(
        "Mystery Item Difficulty relative frequency (only with --mystery)"
    )

    mystery_idiff_freq_entries = [
        ("item_easy", 15),
        ("item_norm", 75),
        ("item_hard", 15),
    ]

    fill_mystery_freq_group(mystery_idiff_freq_entries, mystery_item_diff)

    mystery_enemy_diff = parser.add_argument_group(
        "Mystery Enemy Difficulty relative frequency (only with --mystery)"
    )
    mystery_ediff_freq_entries = [
        ("enemy_norm", 75),
        ("enemy_hard", 25),
    ]

    fill_mystery_freq_group(mystery_ediff_freq_entries, mystery_enemy_diff)


    mystery_tech_order_freq_entries = [
        ("tech_norm", 10),
        ("tech_rand", 80),
        ("tech_balanced_rand", 10),
    ]

    mystery_tech_order = parser.add_argument_group(
        "Mystery Tech Order relative frequency (only with --mystery)"
    )
    fill_mystery_freq_group(mystery_tech_order_freq_entries,
                            mystery_tech_order)

    mystery_price_freq_entries = [
        ("prices_norm", 70),
        ("prices_rand", 10),
        ("prices_mostly_rand", 10),
        ("prices_free", 10)
    ]
    mystery_prices = parser.add_argument_group(
        "Mystery Shop Price relative frequency (only with --mystery)"
    )

    fill_mystery_freq_group(mystery_price_freq_entries, mystery_prices)

    mystery_flags = parser.add_argument_group(
        "Mystery Flags Probabilities.  The chance that a flag will be set in "
        "the mystery settings.  All flags not listed here will be set as they "
        "are in the main settings."
    )

    def check_prob(val):
        fval = float(val)

        if not 0 <= fval <= 1:
            raise argparse.ArgumentTypeError("Probability must be in [0,1]")

        return fval

    mystery_flag_prob_entries = [
        ("flag_tab_treasures", 0.10),
        ("flag_unlocked_magic", 0.50),
        ("flag_bucket_list", 0.15),
        ("flag_chronosanity", 0.30),
        ("flag_boss_rando", 0.50),
        ("flag_boss_scaling", 0.30),
        ("flag_locked_chars", 0.25),
        ("flag_duplicate_chars", 0.25),
        ("flag_epoch_fail", 0.50),
        ("flag_gear_rando", 0.25),
        ("flag_heal_rando", 0.25),
    ]

    for flag_str, prob in mystery_flag_prob_entries:
        mystery_flags.add_argument(
            "--mystery_"+flag_str,
            type=check_prob,
            default=prob,
            help="default %0.2f" % prob
        )

    return parser
