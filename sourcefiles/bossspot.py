from __future__ import annotations

from enum import auto
import json
import math
import typing

import bossdata
import enemystats
import ctenums
import ctrom

import randoconfig as cfg


class BossSpotID(ctenums.StrIntEnum):
    MANORIA_CATHERDAL = auto()
    HECKRAN_CAVE = auto()
    DENADORO_MTS = auto()
    ZENAN_BRIDGE = auto()
    REPTITE_LAIR = auto()
    MAGUS_CASTLE_FLEA = auto()
    MAGUS_CASTLE_SLASH = auto()
    GIANTS_CLAW = auto()
    TYRANO_LAIR_NIZBEL = auto()
    ZEAL_PALACE = auto()
    DEATH_PEAK = auto()
    BLACK_OMEN_GIGA_MUTANT = auto()
    BLACK_OMEN_TERRA_MUTANT = auto()
    BLACK_OMEN_ELDER_SPAWN = auto()
    KINGS_TRIAL = auto()
    OZZIES_FORT_FLEA_PLUS = auto()
    OZZIES_FORT_SUPER_SLASH = auto()
    SUN_PALACE = auto()
    SUNKEN_DESERT = auto()
    OCEAN_PALACE_TWIN_GOLEM = auto()
    GENO_DOME = auto()
    MT_WOE = auto()
    ARRIS_DOME = auto()


def get_scaled_hp_dict(
        from_boss: bossdata.Boss,
        to_boss: bossdata.Boss,
        stat_dict: dict[ctenums.EnemyID, enemystats.EnemyStats],
        additional_power_scaling: bool = False
) -> dict[ctenums.EnemyID, int]:
    boss_total_hp = get_boss_total_hp(from_boss.scheme, stat_dict)
    hp_dict = get_part_new_hps(to_boss.scheme, stat_dict, boss_total_hp)

    # I fear that many bosses become too easy in endgame spots with with
    # spot-based hp values.  This does something do alleviate the problem.
    if additional_power_scaling:
        hp_mod = get_power_scale_factor(
            from_boss.power, to_boss.power
        )

        for part in hp_dict:
            hp_dict[part] = hp_dict[part] * hp_mod

    return hp_dict


def get_power_scale_factor(
        from_power: int,
        to_power: int
) -> float:
    '''
    Determine additional hp scaling based on power differential.
    '''
    hp_mod = round(math.log2(to_power/from_power))
    hp_mod = 1+0.1*hp_mod

    return hp_mod


def get_boss_total_hp(
        boss_scheme: bossdata.BossScheme,
        stat_dict: dict[ctenums.EnemyID, enemystats.EnemyStats]
) -> int:

    EnID = ctenums.EnemyID
    main_ids = set([EnID.LAVOS_SPAWN_HEAD,
                    EnID.ELDER_SPAWN_HEAD,
                    EnID.GUARDIAN,
                    EnID.GIGA_GAIA_HEAD])
    if len(boss_scheme.ids) == 1:
        ret_hp = stat_dict[boss_scheme.ids[0]].hp
        if boss_scheme.ids[0] == EnID.RUST_TYRANO:
            ret_hp = round(ret_hp / 1.75)
    elif boss_scheme.ids[0] == EnID.TWIN_BOSS:
        ret_hp = round((stat_dict[EnID.TWIN_BOSS].hp*3)/2)
    elif EnID.TERRA_MUTANT_HEAD in boss_scheme.ids:
        head_hp = max(1, stat_dict[EnID.TERRA_MUTANT_HEAD].hp)
        ret_hp = round(3*head_hp/2)
    elif not main_ids.isdisjoint(set(boss_scheme.ids)):
        main_id = next(x for x in main_ids if x in boss_scheme.ids)
        ret_hp = stat_dict[main_id].hp
    elif EnID.MOTHERBRAIN in boss_scheme.ids:
        ret_hp = stat_dict[EnID.MOTHERBRAIN].hp
    elif EnID.SON_OF_SUN_EYE in boss_scheme.ids:
        ret_hp = 6500  # Completely Fabricated!
    else:
        # The general case.  Just sum up the part HPs.

        ret_hp = sum(stat_dict[part].hp for part in boss_scheme.ids)

    return ret_hp


def get_part_new_hps(
        boss_scheme: bossdata.BossScheme,
        stat_dict: dict[ctenums.EnemyID, enemystats.EnemyStats],
        new_hp: int
) -> dict[ctenums.EnemyID, int]:

    EnID = ctenums.EnemyID

    main_ids = set([EnID.LAVOS_SPAWN_HEAD,
                    EnID.ELDER_SPAWN_HEAD,
                    EnID.GUARDIAN,
                    EnID.GIGA_GAIA_HEAD])
    
    if len(boss_scheme.ids) == 1:
        if boss_scheme.ids[0] == EnID.RUST_TYRANO:
            new_hp = round(new_hp * 1.75)
        ret_dict = {boss_scheme.ids[0]: new_hp}
    elif boss_scheme.ids[0] == EnID.TWIN_BOSS:
        ret_dict = {EnID.TWIN_BOSS: round((new_hp*2)/3)}
    elif EnID.TERRA_MUTANT_HEAD in boss_scheme.ids:
        head_hp = max(1, stat_dict[EnID.TERRA_MUTANT_HEAD].hp)
        bottom_hp = stat_dict[EnID.TERRA_MUTANT_BOTTOM].hp
        bot_proportion = bottom_hp/head_hp

        # Terra gets 2/3 of the spot hp and maintains head/bot proportion
        new_head_hp = round(new_hp*2/3)
        new_bottom_hp = round(bot_proportion*new_head_hp)
        ret_dict = {
            EnID.TERRA_MUTANT_HEAD: new_head_hp,
            EnID.TERRA_MUTANT_BOTTOM: new_bottom_hp
        }
    elif not main_ids.isdisjoint(set(boss_scheme.ids)):
        # Covers Lavos Spawns, Guardian, Giga Gaia
        # Give the main part the spot hp.  Assign the others proportionally.
        main_id = next(x for x in main_ids if x in boss_scheme.ids)
        main_hp = stat_dict[main_id].hp
        ret_dict = {
            part: round(new_hp*(stat_dict[part].hp/main_hp))
            for part in boss_scheme.ids
        }
    elif EnID.MOTHERBRAIN in boss_scheme.ids:
        ret_dict = {
            EnID.MOTHERBRAIN: new_hp,
            EnID.DISPLAY: 1
        }
    elif EnID.SON_OF_SUN_EYE in boss_scheme.ids:
        ret_dict = {}
    else:
        # The general case.  Carve up new_hp by the original hp distribution.
        # Being lazy because no leftover bosses have duplicate parts.
        total_hp = sum(stat_dict[part].hp for part in boss_scheme.ids)
        part_props = {
            part: stat_dict[part].hp/total_hp for part in boss_scheme.ids
        }
        ret_dict = {
            part: round(part_props[part]*new_hp) for part in part_props
        }

    return ret_dict
