'''
Module for turning text expressions into objective choices.
'''
from __future__ import annotations

from typing import Dict, Tuple, Union

import bossrandotypes as rotypes
import objectivetypes
from characters import pcrecruit
from common import distribution
import ctenums

import randosettings as rset


class InvalidNameException(Exception):
    pass


class WeightException(Exception):
    pass


def get_forced_bosses(hint: str) -> list[rotypes.BossID]:
    hint = ''.join(hint.split())
    parts = hint.split(',')

    boss_list = []
    for part in parts:
        if ':' in part:
            part = part.split(':')[1]

        items = part.split('_')
        p_type = items[0]

        if p_type != 'boss':
            continue

        boss_name = items[1]
        try:
            boss = parse_boss_name(boss_name)
            boss_list.append(boss)
        except InvalidNameException:  # 'go', 'nogo', etc
            continue

    return boss_list

def parse_boss_name(name: str):
    '''
    One day we can go crazy and do some partial string matching.  Today is
    not that day.
    '''
    if name in ('atropos', 'atroposxr'):
        return rotypes.BossID.ATROPOS_XR
    if name in ('dalton', 'daltonplus', 'dalton+'):
        return rotypes.BossID.DALTON_PLUS
    if name in ('dragontank', 'dtank'):
        return rotypes.BossID.DRAGON_TANK
    if name in ('elderspawn', 'elder'):
        return rotypes.BossID.ELDER_SPAWN
    if name == 'flea':
        return rotypes.BossID.FLEA
    if name in ('fleaplus', 'flea+'):
        return rotypes.BossID.FLEA_PLUS
    if name in ('gigagaia', 'gg'):
        return rotypes.BossID.GIGA_GAIA
    if name == 'gigamutant':
        return rotypes.BossID.GIGA_MUTANT
    if name == 'golem':
        return rotypes.BossID.GOLEM
    if name in ('bossgolem', 'golemboss'):
        return rotypes.BossID.GOLEM_BOSS
    if name == 'guardian':
        return rotypes.BossID.GUARDIAN
    if name == 'heckran':
        return rotypes.BossID.HECKRAN
    if name == 'lavosspawn':
        return rotypes.BossID.LAVOS_SPAWN
    if name in ('magusnc', 'ncmagus'):
        return rotypes.BossID.MAGUS_NORTH_CAPE
    if name in ('masamune', 'masa&mune'):
        return rotypes.BossID.MASA_MUNE
    if name == 'megamutant':
        return rotypes.BossID.MEGA_MUTANT
    if name == 'motherbrain':
        return rotypes.BossID.MOTHER_BRAIN
    if name == 'mudimp':
        return rotypes.BossID.MUD_IMP
    if name == 'nizbel':
        return rotypes.BossID.NIZBEL
    if name in ('nizbel2', 'nizbelii'):
        return rotypes.BossID.NIZBEL_2
    if name == 'rseries':
        return rotypes.BossID.R_SERIES
    if name == 'retinite':
        return rotypes.BossID.RETINITE
    if name in ('rusty', 'rusttyrano'):
        return rotypes.BossID.RUST_TYRANO
    if name == 'slash':
        return rotypes.BossID.SLASH_SWORD
    if name in ('sos', 'sonofsun'):
        return rotypes.BossID.SON_OF_SUN
    if name == 'superslash':
        return rotypes.BossID.SUPER_SLASH
    if name == 'terramutant':
        return rotypes.BossID.TERRA_MUTANT
    if name == 'twinboss':
        return rotypes.BossID.TWIN_BOSS
    if name == 'yakra':
        return rotypes.BossID.YAKRA
    if name in ('yakraxiii', 'yakra13'):
        return rotypes.BossID.YAKRA_XIII
    if name == 'zombor':
        return rotypes.BossID.ZOMBOR

    raise InvalidNameException(name)


def parse_quest_name(name: str):
    '''Turn a quest name into a QuestID.'''
    QID = objectivetypes.QuestID

    if name in ('repairmasamune', 'masamune', 'masa', 'forge'):
        return QID.FORGE_MASAMUNE
    if name in ('chargemoon', 'moon', 'moonstone'):
        return QID.CHARGE_MOONSTONE
    if name == "arris":
        return QID.CLEAR_ARRIS_DOME
    if name == 'jerky':
        return QID.GIVE_JERKY_TO_MAYOR
    if name in ('deathpeak', 'death'):
        return QID.CLEAR_DEATH_PEAK
    if name == 'denadoro':
        return QID.CLEAR_DENADORO
    if name in ('epoch', 'flight', 'epochflight'):
        return QID.GAIN_EPOCH_FLIGHT
    if name in ('factory', 'factoryruins'):
        return QID.CLEAR_FACTORY_RUINS
    if name in ('geno', 'genodome'):
        return QID.CLEAR_GENO_DOME
    if name in ('claw', 'giantsclaw'):
        return QID.CLEAR_GIANTS_CLAW
    if name in ('heckran', 'heckranscave', 'heckrancave'):
        return QID.CLEAR_HECKRANS_CAVE
    if name in ('kingstrial', 'shard', 'shardtrial', 'prismshard'):
        return QID.CLEAR_KINGS_TRIAL
    if name in ('cathedral', 'cath', 'manoria'):
        return QID.CLEAR_CATHEDRAL
    if name in ('woe', 'mtwoe'):
        return QID.CLEAR_MT_WOE
    if name in ('ocean', 'oceanpalace'):
        return QID.CLEAR_OCEAN_PALACE
    if name in ('ozzie', 'fort', 'ozziefort', 'ozziesfort'):
        return QID.CLEAR_OZZIES_FORT
    if name in ('pendant', 'pendanttrial'):
        return QID.CLEAR_PENDANT_TRIAL
    if name in ('reptite', 'reptitelair'):
        return QID.CLEAR_REPTITE_LAIR
    if name in ('sunpalace', 'sun'):
        return QID.CLEAR_SUN_PALACE
    if name in ('desert', 'sunkendesert'):
        return QID.CLEAR_SUNKEN_DESERT
    if name in ('zealthrone', 'zealpalace', 'golemspot'):
        return QID.CLEAR_ZEAL_PALACE
    if name in ('zenan', 'bridge', 'zenanbridge'):
        return QID.CLEAR_ZENAN_BRIDGE
    if name in ('tyrano', 'blacktyrano', 'azala'):
        return QID.CLEAR_BLACK_TYRANO
    if name in ('tyranomid', 'nizbel2spot'):
        return QID.CLEAR_TYRANO_MIDBOSS
    if name in ('magus', 'maguscastle'):
        return QID.CLEAR_MAGUS_CASTLE
    if name in ('omengiga', 'gigamutant', 'gigaspot'):
        return QID.CLEAR_OMEN_GIGASPOT
    if name in ('omenterra', 'terramutant', 'terraspot'):
        return QID.CLEAR_OMEN_TERRASPOT
    if name in ('flea', 'magusflea'):
        return QID.CLEAR_MAGUS_FLEA_SPOT
    if name in ('slash', 'magusslash'):
        return QID.CLEAR_MAGUS_SLASH_SPOT
    if name in ('omenelder', 'elderspawn', 'elderspot'):
        return QID.CLEAR_OMEN_ELDERSPOT
    if name in ('twinboss', 'twingolem', 'twinspot'):
        return QID.CLEAR_TWINBOSS_SPOT
    if name in ('cyrus', 'nr', 'northernruins'):
        return QID.VISIT_CYRUS_GRAVE
    if name in ('johnny', 'johnnyrace'):
        return QID.DEFEAT_JOHNNY
    if name in ('fairrace', 'fairbet'):
        return QID.WIN_RACE_BET
    if name in ('soda', 'drink'):
        return QID.DRINK_SODA

    raise InvalidNameException(name)


_BossDict = Dict[rotypes.BossSpotID, rotypes.BossID]
_RecruitDict = Dict[ctenums.RecruitID, pcrecruit.RecruitSpot]


def get_go_bosses(boss_assign_dict: _BossDict) -> list[rotypes.BossID]:
    BSID = rotypes.BossSpotID
    go_spots = [BSID.BLACK_OMEN_ELDER_SPAWN, BSID.BLACK_OMEN_GIGA_MUTANT,
                BSID.BLACK_OMEN_TERRA_MUTANT, BSID.OCEAN_PALACE_TWIN_GOLEM,
                BSID.ZEAL_PALACE, BSID.DEATH_PEAK, BSID.MAGUS_CASTLE_FLEA,
                BSID.MAGUS_CASTLE_SLASH]

    return [
        boss_id for spot, boss_id in boss_assign_dict.items()
        if spot in go_spots
    ]


def get_objective_keys(obj_str: str, settings: rset.Settings,
                       boss_assign_dict: _BossDict,
                       char_assign_dict: _RecruitDict
                       ) -> list:
    '''
    Turn a part of an objective hint into a list of objective keys.
    '''
    BSID = rotypes.BossSpotID
    BossID = rotypes.BossID

    obj_parts = obj_str.split('_')
    obj_type = obj_parts[0]

    epoch_fail = rset.GameFlags.EPOCH_FAIL in settings.gameflags

    if obj_type == 'boss':
        # At some point, the one-spot BossID was put in the boss_assign_dict
        # instead of BossID.TWIN_BOSS.  We need to undo this here to get the
        # correct keys.
        modified_assign_dict = dict(boss_assign_dict)
        twin_spot = BSID.OCEAN_PALACE_TWIN_GOLEM
        if twin_spot in modified_assign_dict:
            modified_assign_dict[twin_spot] = BossID.TWIN_BOSS

        boss_type = obj_parts[1]
        if boss_type == 'any':
            return list(modified_assign_dict.values())
        if boss_type == 'go':
            return get_go_bosses(modified_assign_dict)
        if boss_type == 'nogo':
            go_bosses = get_go_bosses(modified_assign_dict)
            all_bosses = list(modified_assign_dict.values())
            return [boss_id for boss_id in all_bosses
                    if boss_id not in go_bosses]
        return [parse_boss_name(boss_type)]

    if obj_type == 'quest':
        QID = objectivetypes.QuestID
        quest_type = obj_parts[1]
        if quest_type == 'free':
            return [QID.CLEAR_CATHEDRAL, QID.CLEAR_HECKRANS_CAVE,
                    QID.CLEAR_DENADORO, QID.CLEAR_ZENAN_BRIDGE]
        if quest_type == 'gated':
            gated_quests = [
                QID.CHARGE_MOONSTONE, QID.GIVE_JERKY_TO_MAYOR,
                QID.CLEAR_ARRIS_DOME, QID.GAIN_EPOCH_FLIGHT,
                QID.CLEAR_FACTORY_RUINS, QID.CLEAR_GIANTS_CLAW,
                QID.CLEAR_OZZIES_FORT, QID.CLEAR_TYRANO_MIDBOSS,
                QID.CLEAR_KINGS_TRIAL,
                QID.CLEAR_PENDANT_TRIAL, QID.CLEAR_REPTITE_LAIR,
                QID.CLEAR_SUN_PALACE, QID.CLEAR_SUNKEN_DESERT,
            ]

            if not epoch_fail:
                gated_quests.remove(QID.GAIN_EPOCH_FLIGHT)

            return gated_quests
        if quest_type == 'late':
            late_quests = [QID.CLEAR_MT_WOE, QID.CLEAR_GENO_DOME,
                           QID.CLEAR_BLACK_TYRANO]
            return late_quests
        if quest_type == 'go':
            go_quests = [QID.CLEAR_ZEAL_PALACE, QID.CLEAR_TWINBOSS_SPOT,
                         QID.CLEAR_DEATH_PEAK,
                         QID.CLEAR_OMEN_GIGASPOT, QID.CLEAR_OMEN_TERRASPOT,
                         QID.CLEAR_OMEN_ELDERSPOT, QID.CLEAR_MAGUS_CASTLE]

            return go_quests
        return [parse_quest_name(quest_type)]

    if obj_type == 'recruit':
        chars = ['crono', 'marle', 'lucca', 'robo', 'frog', 'ayla', 'magus']
        spots = ['castle', 'dactyl', 'proto', 'burrow']
        RID = ctenums.RecruitID
        spot_ids = [RID.CASTLE, RID.DACTYL_NEST, RID.PROTO_DOME,
                    RID.FROGS_BURROW]
        char_choice = obj_parts[1]
        if char_choice == 'any':
            return list(ctenums.CharID)
        if char_choice == 'gated':
            return [
                char_assign_dict[rid].held_char
                for rid in spot_ids
            ]
        if char_choice in chars:
            char_id = ctenums.CharID(chars.index(char_choice))
            return [char_id]
        if char_choice in spots:
            index = spots.index(char_choice)
            return [spot_ids[index]]

        # num_recruits = int(char_choice)
        return ['recruits_' + char_choice]
    if obj_type == 'collect':
        # num_collect = int(obj_parts[1])
        collect_type = obj_parts[2]
        if collect_type == 'rocks':
            return ['_'.join(('rocks', obj_parts[1]))]
        if collect_type == 'fragments':
            # total_fragments = int(obj_parts[3])
            return ['_'.join(('fragments', obj_parts[1], obj_parts[3]))]
        raise InvalidNameException(collect_type)

    raise InvalidNameException(obj_type)


def is_hint_valid(hint: str) -> Tuple[bool, str]:
    '''
    Determine whether the given objective hint has a valid format.
    Returns a tuple of the validity (bool) and an error message (str).
    '''
    if hint == '':
        return True, ''

    fake_settings = rset.Settings.get_race_presets()
    boss_assign_dict = rotypes.get_default_boss_assignment()
    char_assign_dict = pcrecruit.get_base_recruit_dict()

    try:
        dist = parse_hint(hint, fake_settings, boss_assign_dict,
                          char_assign_dict)
    except InvalidNameException as exc:
        return (False, str(exc))

    if dist.get_total_weight() == 0:
        return (False, 'Empty Hint')

    return True, ''


def parse_hint(
        hint: str, settings: rset.Settings,
        boss_assign_dict: _BossDict,
        char_assign_dict: _RecruitDict
        ) -> distribution.Distribution:
    '''
    Turn an objective hint into a distribution which generates
    '''
    hint = ''.join(hint.lower().split())  # Remove whitespace
    obj_strs = hint.split(',')

    weight_obj_pairs = []

    has_weight = False
    for obj_str in obj_strs:
        if ':' in obj_str:
            has_weight = True
        elif has_weight:
            raise WeightException('Some but not all categories have weights.')

        if has_weight:
            weight_str, obj_str = obj_str.split(':')
            weight = int(weight_str)
        else:
            weight = 1

        # print(f'******* weight = {weight}')
        obj_keys = get_objective_keys(obj_str, settings,
                                      boss_assign_dict, char_assign_dict)
        # print(obj_keys)
        # print('*******')

        weight_obj_pairs.append((weight, obj_keys))

    return distribution.Distribution(*weight_obj_pairs)
