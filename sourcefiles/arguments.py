from __future__ import annotations
import argparse
import copy

from pathlib import Path
from typing import Iterable, Optional, Union

import cli.adapters as adp
import ctstrings
import ctoptions
import randosettings as rset

from cli.constants import FLAG_ENTRY_DICT, MYSTERY_FLAG_PROB_ENTRIES
from randosettings import GameFlags as GF, GameMode as GM, CosmeticFlags as CF


def add_flags_to_parser(
        group_text: Optional[str],
        flag_list: Iterable[GF | CF],
        parser: argparse.ArgumentParser):

    add_target: Union[argparse.ArgumentParser, argparse._ArgumentGroup]

    if group_text is None:
        add_target = parser
    else:
        group = parser.add_argument_group(group_text)
        add_target = group

    for flag in flag_list:
        flag_entry = FLAG_ENTRY_DICT[flag]
        add_args: Iterable[str]
        if flag_entry.short_name is None:
            add_args = (flag_entry.name,)
        else:
            add_args = (flag_entry.name, flag_entry.short_name)
        add_target.add_argument(
            *add_args,
            help=flag_entry.help_text,
            action="store_true"
        )

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
    val_dict = vars(args)
    
    disable_other_go_modes = val_dict['bucket_disable_other_go']
    objectives_win = val_dict['bucket_objectives_win']
    num_objectives = val_dict['bucket_objective_count']
    num_objectives_needed = val_dict['bucket_objective_needed_count']

    obj_strs: list[str] = []
    for obj_ind in range(num_objectives_needed):
        obj_strs.append(val_dict['bucket_objective'+str(obj_ind+1)])

    return rset.BucketSettings(
        disable_other_go_modes, objectives_win, num_objectives,
        num_objectives_needed, obj_strs
    )


def get_ctoptions(args: argparse.Namespace) -> ctoptions.CTOpts:
    '''Extract CTOpts from argparse.Namespace.'''
    ct_opts = ctoptions.CTOpts()
    ct_opts.save_menu_cursor = args.save_menu_cursor
    ct_opts.save_battle_cursor = args.save_battle_cursor
    ct_opts.save_tech_cursor = not args.save_skill_cursor_off
    ct_opts.skill_item_info = not args.skill_item_info_off
    ct_opts.consistent_paging = args.consistent_paging
    ct_opts.battle_speed = args.battle_speed - 1
    ct_opts.battle_msg_speed = args.battle_msg_speed - 1
    ct_opts.battle_gauge_style = args.battle_gauge_style
    ct_opts.menu_background = args.background - 1
    return ct_opts


def get_mystery_settings(args: argparse.Namespace) -> rset.MysterySettings:
    mset = rset.MysterySettings()
    val_dict = vars(args)

    mset.game_mode_freqs = {
        GM.STANDARD: val_dict['mystery_mode_std'],
        GM.LOST_WORLDS: val_dict['mystery_mode_lw'],
        GM.LEGACY_OF_CYRUS: val_dict['mystery_mode_loc'],
        GM.ICE_AGE: val_dict['mystery_mode_ia'],
        GM.VANILLA_RANDO: val_dict['mystery_mode_van'],
    }

    mset.item_difficulty_freqs = {
        rset.Difficulty.EASY: val_dict['mystery_item_easy'],
        rset.Difficulty.NORMAL: val_dict['mystery_item_norm'],
        rset.Difficulty.HARD: val_dict['mystery_item_hard']
    }

    mset.enemy_difficulty_freqs = {
        rset.Difficulty.NORMAL: val_dict['mystery_enemy_norm'],
        rset.Difficulty.HARD: val_dict['mystery_enemy_hard']
    }

    mset.tech_order_freqs = {
        rset.TechOrder.NORMAL: val_dict['mystery_tech_norm'],
        rset.TechOrder.BALANCED_RANDOM: val_dict['mystery_tech_balanced'],
        rset.TechOrder.FULL_RANDOM: val_dict['mystery_tech_rand']
    }
    mset.shop_price_freqs = {
        rset.ShopPrices.NORMAL: val_dict['mystery_prices_norm'],
        rset.ShopPrices.MOSTLY_RANDOM: val_dict['mystery_prices_mostly_rand'],
        rset.ShopPrices.FULLY_RANDOM: val_dict['mystery_prices_rand'],
        rset.ShopPrices.FREE: val_dict['mystery_prices_free']
    }

    mset.flag_prob_dict = {
        flag: getattr(args, f"mystery_{name}")
        for flag, name, _ in MYSTERY_FLAG_PROB_ENTRIES
    }

    return mset


def args_to_settings(args: argparse.Namespace) -> rset.Settings:
    '''Convert result of argparse to settings object.'''

    ret_set = rset.Settings()
    ret_set.seed = args.seed
    ret_set.game_mode = adp.GameModeAdapter.to_setting(args)
    ret_set.gameflags = adp.GameFlagsAdapter.to_setting(args)
    ret_set.initial_flags = copy.deepcopy(ret_set.gameflags)
    ret_set.item_difficulty =  adp.ItemDifficultyAdapter.to_setting(args)
    ret_set.enemy_difficulty =  adp.EnemyDifficultyAdapter.to_setting(args)
    ret_set.techorder = adp.TechOrderAdapter.to_setting(args)
    ret_set.shopprices = adp.ShopPricesAdapter.to_setting(args)
    ret_set.mystery_settings = get_mystery_settings(args)
    ret_set.cosmetic_flags = adp.CosmeticFlagsAdapter.to_setting(args)
    ret_set.ctoptions = get_ctoptions(args)
    ret_set.char_settings = adp.CharSettingsAdapter.to_setting(args)

    return ret_set


def add_generation_options(parser: argparse.ArgumentParser):

    gen_group = parser.add_argument_group("Generation options")

    gen_group.add_argument(
        "--input-file", "-i",
        required=True,
        help="path to Chrono Trigger (U) rom",
        type=Path,
    )

    gen_group.add_argument(
        "--output-path", "-o",
        help="path to output directory (default same as input)",
        type=Path,
    )

    gen_group.add_argument(
        "--seed",
        help="seed for generation (not website share id)"
    )

    gen_group.add_argument(
        "--spoilers",
        help="generate spoilers with the randomized rom.",
        action="store_true"
    )

    gen_group.add_argument(
        "--json-spoilers",
        help="generate json spoilers with the randomized rom.",
        action="store_true"
    )


def get_parser():
    parser = argparse.ArgumentParser(formatter_class=SmartFormatter)

    add_generation_options(parser)

    # arguments with a default of "argparse.SUPPRESS", when explicitly specified
    # on the CLI, will override any other value (e.g. from a preset file)
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
        default=argparse.SUPPRESS,
        type=str.lower
    )

    parser.add_argument(
        "--item-difficulty", "-idiff",
        help="controls quality of treasure, drops, and starting gold "
        "(default: normal)",
        choices=['easy','normal', 'hard'],
        default=argparse.SUPPRESS,
        type=str.lower
    )

    parser.add_argument(
        "--enemy-difficulty", "-ediff",
        help="controls strength of enemies and xp/tp rewards "
        "(default: normal)",
        choices=['normal', 'hard'],
        default=argparse.SUPPRESS,
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
        default=argparse.SUPPRESS,
        type=str.lower
    )

    parser.add_argument(
        "--shop-prices",
        help="R|"
        "controls the prices in shops\n"
        "    normal - standard prices (default)\n"
        "    random - fully random prices\n"
        "mostrandom - random except for staple consumables\n"
        "      free - all items cost 1G",
        choices=['normal', 'random', 'mostrandom', 'free'],
        default=argparse.SUPPRESS,
        type=str.lower
    )

    add_flags_to_parser(
        'Basic Flags',
        (GF.FIX_GLITCH, GF.BOSS_SCALE, GF.ZEAL_END, GF.FAST_PENDANT,
         GF.LOCKED_CHARS, GF.UNLOCKED_MAGIC, GF.CHRONOSANITY,
         GF.TAB_TREASURES, GF.BOSS_RANDO, GF.CHAR_RANDO,
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
         GF.BUCKET_LIST, GF.TECH_DAMAGE_RANDO),
        parser
    )

    add_flags_to_parser(
        "Logic Tweak Flags that add a KI",
        (GF.RESTORE_JOHNNY_RACE, GF.RESTORE_TOOLS),
        parser
    )

    add_flags_to_parser(
        "Logic Tweak Flags that add/remove a KI Spot",
        (GF.ADD_BEKKLER_SPOT, GF.ADD_OZZIE_SPOT, GF.ADD_RACELOG_SPOT,
         GF.ADD_CYRUS_SPOT, GF.VANILLA_ROBO_RIBBON, GF.REMOVE_BLACK_OMEN_SPOT),
        parser
    )

    add_flags_to_parser(
        "Logic Flags that are KI/KI Spot Neutral",
        (GF.UNLOCKED_SKYGATES, GF.ADD_SUNKEEP_SPOT, GF.SPLIT_ARRIS_DOME,
         GF.VANILLA_DESERT, GF.ROCKSANITY),
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

    # Character Rando Options
    rc_options = parser.add_argument_group(
        "-rc Options",
        "These options are only valid when --char-rando [-rc] "
        "is set"
    )

    rc_options.add_argument(
        "--duplicate-characters", "-dc",
        help="Allow multiple copies of a character to be present in a seed.",
        action="store_true"
    )

    rc_options.add_argument(
        "--duplicate-techs",
        help="Allow duplicate characters to perform dual techs together.",
        action="store_true"
    )

    rc_options.add_argument(
        "--crono-choices",
        help="The characters Crono is allowed to be assigned. For example, "
        "--crono-choices \"lucca robo\" would allow Crono to be assigned to "
        "either Lucca or Robo.  If the list is preceded with \"not\" "
        "(e.g. not lucca ayla) then all except the listed characters will be "
        "allowed.",
        default="all"
    )

    rc_options.add_argument(
        "--marle-choices",
        help="Same as --crono-choices.",
        default="all"
    )

    rc_options.add_argument(
        "--lucca-choices",
        help="Same as --crono-choices.",
        default="all"
    )

    rc_options.add_argument(
        "--robo-choices",
        help="Same as --crono-choices.",
        default="all"
    )

    rc_options.add_argument(
        "--frog-choices",
        help="Same as --crono-choices.",
        default="all"
    )

    rc_options.add_argument(
        "--ayla-choices",
        help="Same as --crono-choices.",
        default="all"
    )

    rc_options.add_argument(
        "--magus-choices",
        help="Same as --crono-choices.",
        default="all"
    )

    # Tab Options
    tab_options = parser.add_argument_group(
        "Tab Settings"
    )

    tab_options.add_argument(
        "--min-power-tab",
        help="The minimum value a power tab can increase power by (default 2)",
        default=1,
        type=int,
        choices=range(1, 10)
    )

    tab_options.add_argument(
        "--max-power-tab",
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

    def check_non_neg(value) -> int:
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
        ("tech_balanced", 10),
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

    def check_prob(val) -> float:
        fval = float(val)

        if not 0 <= fval <= 1:
            raise argparse.ArgumentTypeError("Probability must be in [0,1]")

        return fval

    for _, flag_str, prob in MYSTERY_FLAG_PROB_ENTRIES:
        mystery_flags.add_argument(
            "--mystery_"+flag_str,
            type=check_prob,
            default=prob,
            help="default %0.2f" % prob
        )

    add_flags_to_parser(
        "Cosmetic Flags.  Have no effect on randomization.",
        (CF.AUTORUN, CF.DEATH_PEAK_ALT_MUSIC, CF.ZENAN_ALT_MUSIC,
         CF.QUIET_MODE, CF.REDUCE_FLASH),
        parser
    )

    def verify_name(string: str) -> str:
        if len(string) > 5:
            raise argparse.ArgumentTypeError(
                "Name must have length 5 or less.")

        try:
            ctnamestr = ctstrings.CTNameString.from_string(
                string, 5)
        except ctstrings.InvalidSymbolException as exc:
            raise argparse.ArgumentTypeError(
                "Invalid symbol: \'" + str(exc) +"'")

        return string

    name_group = parser.add_argument_group("Character Names")
    for char_name in rset.CharNames.default():
        name_group.add_argument(
            f"--{char_name.lower()}-name",
            type=verify_name,
            default=char_name
        )

    menu_opts = (
        ("--save-menu-cursor", "save last used page of X-menu"),
        ("--save-battle-cursor", "save battle cursor position"),
        ("--save-skill-cursor-off",
         "do not save position in skill/item menu"),
        ("--skill-item-info-off", "do not show skill/item descriptions"),
        ("--consistent-paging",
         "page up/down have the same effect in all menus")
    )

    opts_group = parser.add_argument_group("Game Options")
    for name, desc in menu_opts:
        opts_group.add_argument(
            name, help=desc, action="store_true"
        )

    opts_group.add_argument(
        "--battle-speed",
        help="default battle speed (lower is faster)",
        type=int,
        choices=range(1, 9),
        default=5
    )

    opts_group.add_argument(
        "--battle-msg-speed",
        help="default battle message speed (lower is faster)",
        type=int,
        choices=range(1, 9),
        default=5
    )

    opts_group.add_argument(
        "--battle-gauge-style",
        help="default atb gauge style (default 1)",
        type=int,
        choices=range(3),
        default=1
    )

    opts_group.add_argument(
        "--background",
        help="default background (default 1)",
        type=int,
        choices=range(1, 9),
        default=1
    )

    return parser
