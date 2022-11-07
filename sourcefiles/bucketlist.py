import dataclasses
from enum import Enum, auto
import random
import typing

import bossrandotypes as rotypes
from bossrandotypes import BossSpotID as BSID

import ctenums
import ctevent
import ctrom

import eventcommand
from eventcommand import EventCommand as EC, Operation as OP, FuncSync as FS

import eventfunction
from eventfunction import EventFunction as EF

import itemdata

import objectivetypes as oty

import randoconfig as cfg
import randosettings as rset

import xpscale


@dataclasses.dataclass(frozen=True)
class RomFlag:
    address: int = 0
    bit: int = 0


# Many of these are taken from Anguirel's Tracker code.
_boss_spot_flags: dict[BSID, RomFlag] = {
    BSID.ARRIS_DOME: RomFlag(0x7F00EC, 0x01),
    BSID.BLACK_OMEN_ELDER_SPAWN: RomFlag(0x7F01A9, 0x01),
    BSID.BLACK_OMEN_GIGA_MUTANT: RomFlag(0x7F0071, 0x10),
    BSID.BLACK_OMEN_TERRA_MUTANT: RomFlag(0x7F015A, 0x01),
    BSID.DEATH_PEAK: RomFlag(0x7F0064, 0x20),
    # Epoch reborn doesn't have a flag, but it sets 0x7F00D2 = 7 before the
    # cutscene starts.  So we can test any of the 0x07 bits for this one.
    BSID.EPOCH_REBORN: RomFlag(0x7F00D2, 0x2),
    # Actually the flag for activating the power core.
    BSID.FACTORY_RUINS: RomFlag(0x7F0103, 0x40),
    BSID.GENO_DOME: RomFlag(0x7F013B, 0x10),
    BSID.GIANTS_CLAW: RomFlag(0x7F01D2, 0x40),
    BSID.HECKRAN_CAVE: RomFlag(0x7F01A3, 0x08),
    BSID.KINGS_TRIAL: RomFlag(0x7F0050, 0x40),
    BSID.MAGUS_CASTLE_FLEA: RomFlag(0x7F00A3, 0x08),
    BSID.MAGUS_CASTLE_SLASH: RomFlag(0x7F00A3, 0x40),
    BSID.MANORIA_CATHERDAL: RomFlag(0x7F000D, 0x01),
    BSID.MT_WOE: RomFlag(0x7F0100, 0x20),
    BSID.OCEAN_PALACE_TWIN_GOLEM: RomFlag(0x7F0100, 0x80),
    BSID.OZZIES_FORT_FLEA_PLUS: RomFlag(0x7F01A1, 0x04),
    BSID.OZZIES_FORT_SUPER_SLASH: RomFlag(0x7F01A1, 0x08),
    BSID.PRISON_CATWALKS: RomFlag(0x7F0198, 0x08),
    BSID.REPTITE_LAIR: RomFlag(0x7F0105, 0x20),
    BSID.SUN_PALACE: RomFlag(0x7F013A, 0x01),
    BSID.SUNKEN_DESERT: RomFlag(0x7F01AD, 0x04),
    BSID.TYRANO_LAIR_NIZBEL: RomFlag(0x7F00EE, 0x01),
    BSID.ZEAL_PALACE: RomFlag(0x7F0105, 0x80),
    BSID.ZENAN_BRIDGE: RomFlag(0x7F0101, 0x02)
}


_boss_names: dict[rotypes.BossID, str] = {
    rotypes.BossID.ATROPOS_XR: 'AtroposXR',
    rotypes.BossID.DALTON_PLUS: 'DaltonPlus',
    rotypes.BossID.ELDER_SPAWN: 'ElderSpawn',
    rotypes.BossID.FLEA: 'Flea',
    rotypes.BossID.FLEA_PLUS: 'Flea Plus',
    rotypes.BossID.GIGA_MUTANT: 'GigaMutant',
    rotypes.BossID.GOLEM: 'Golem',
    rotypes.BossID.GOLEM_BOSS: 'Golem Boss',
    rotypes.BossID.HECKRAN: 'Heckran',
    rotypes.BossID.LAVOS_SPAWN: 'LavosSpawn',
    rotypes.BossID.MAMMON_M: 'Mammon M',
    rotypes.BossID.MAGUS_NORTH_CAPE: 'Magus (NC)',
    rotypes.BossID.MASA_MUNE: 'Masa&Mune',
    rotypes.BossID.MEGA_MUTANT: 'MegaMutant',
    rotypes.BossID.MUD_IMP: 'Mud Imp',
    rotypes.BossID.NIZBEL: 'Nizbel',
    rotypes.BossID.NIZBEL_2: 'Nizbel II',
    rotypes.BossID.RETINITE: 'Retinite',
    rotypes.BossID.R_SERIES: 'R Series',
    rotypes.BossID.RUST_TYRANO: 'RustTyrano',
    rotypes.BossID.SLASH_SWORD: 'Slash',
    rotypes.BossID.SUPER_SLASH: 'Super Slash',
    rotypes.BossID.SON_OF_SUN: 'Son of Sun',
    rotypes.BossID.TERRA_MUTANT: 'TerraMutant',
    rotypes.BossID.TWIN_BOSS: 'Twin Boss',
    rotypes.BossID.YAKRA: 'Yakra',
    rotypes.BossID.YAKRA_XIII: 'Yakra XIII',
    rotypes.BossID.ZOMBOR: 'Zombor',
    rotypes.BossID.MOTHER_BRAIN: 'Mother Brain',
    rotypes.BossID.DRAGON_TANK: 'Dragon Tank',
    rotypes.BossID.GIGA_GAIA: 'Giga Gaia',
    rotypes.BossID.GUARDIAN: 'Guardian',

    # Midbosses -- Should be unused
    rotypes.BossID.MAGUS: 'Magus',
    rotypes.BossID.BLACK_TYRANO: 'Black Tyrano'
}


def add_objectives_to_config(settings: rset.Settings,
                             config: cfg.RandoConfig):
    IID = ctenums.ItemID
    objective_pool = [
        IID.UNUSED_1C, IID.UNUSED_1D, IID.UNUSED_1E,
        IID.UNUSED_2A, IID.UNUSED_2B, IID.UNUSED_2C, IID.UNUSED_2D,
        IID.UNUSED_56, IID.UNUSED_57, IID.UNUSED_58, IID.UNUSED_59,
        IID.UNUSED_EA, IID.UNUSED_EB, IID.UNUSED_EC, IID.UNUSED_ED,
        IID.UNUSED_EE, IID.UNUSED_EF, IID.UNUSED_F0, IID.UNUSED_F1
    ]

    QID = oty.QuestID
    ungated_quests = [
        QID.CLEAR_CATHEDRAL, QID.CLEAR_DENADORO, QID.CLEAR_HECKRANS_CAVE,
        QID.CLEAR_ZENAN_BRIDGE
    ]
    gated_quests = [
        QID.GIVE_JERKY_TO_MAYOR, QID.GET_ARRIS_FOOD_ITEM,
        QID.GIVE_SEED_TO_DOAN, QID.GAIN_EPOCH_FLIGHT, QID.CLEAR_FACTORY_RUINS,
        QID.CLEAR_GIANTS_CLAW, QID.CLEAR_KINGS_TRIAL, QID.CLEAR_OZZIES_FORT,
        QID.CLEAR_PENDANT_TRIAL, QID.CLEAR_REPTITE_LAIR,
        QID.CLEAR_SUN_PALACE, QID.CLEAR_SUNKEN_DESERT, QID.CHARGE_MOONSTONE
    ]
    late_gated_quests = [
        QID.FORGE_MASAMUNE, QID.CLEAR_MT_WOE, QID.CLEAR_GENO_DOME,
        QID.CLEAR_BLACK_TYRANO
    ]
    go_mode_quests = [
        QID.CLEAR_ZEAL_PALACE, QID.CLEAR_MAGUS_CASTLE
    ]

    rem_objs = config.item_db[IID.OBJ_COUNT]
    rem_objs.set_name_from_str('*ObjsRemain')
    rem_objs.set_desc_from_str('Count shows remaining objectives')
    rem_objs.secondary_stats.is_unsellable = True
    rem_objs.secondary_stats.is_key_item = True

    config.objectives = []

    quest_objs = oty.get_quest_obj_dict(settings, config)
    boss_objs = oty.get_defeat_boss_obj_dict(settings, config)
    recruit_objs = oty.get_recruit_obj_dict(settings, config)
    collect_objs = oty.get_item_collect_obj_dict(settings, config)

    categories = ['quest', 'boss', 'recruit', 'collect']
    weights = [35, 35, 15, 15]

    # OK, this is going to be very rough for now
    # Go for 35 35 15 15 for quest, boss, recruit, collect
    for ind in range(settings.bucket_settings.num_objectives):
        category = random.choices(categories, weights, k=1)[0]

        if category == 'quest':
            qid, objective = random.choice(list(quest_objs.items()))

            del quest_objs[qid]
            # At most one ungated quest
            if qid in ungated_quests:
                for ungated_id in ungated_quests:
                    if ungated_id in quest_objs:
                        del quest_objs[ungated_id]

        elif category == 'boss':
            boss_id, objective = random.choice(list(boss_objs.items()))
            del boss_objs[boss_id]
        elif category == 'recruit':
            _, objective = random.choice(list(recruit_objs.items()))
            weights[2] = 0  # no more recruit objectives
        else:
            _, objective = random.choice(list(collect_objs.items()))
            weights[3] = 0

        objective.item_id = objective_pool[ind]
        objective.add_objective_to_config(settings, config)

    # charge_obj = oty.ChargeMoonStoneObjective(objective_pool[0])
    # charge_obj.add_objective_to_config(config)
    # jerky_obj = oty.JerkyRewardObjective(objective_pool[0])
    # jerky_obj.add_objective_to_config(config)
    # recruit = config.char_assign_dict[ctenums.RecruitID.CATHEDRAL]
    # recruit_obj = oty.RecruitSpotObjective(
    #     f'*Find {str(recruit.held_char)}',
    #     f'Recruit {str(recruit.held_char)}',
    #     recruit,
    #     objective_pool[0]
    # )
    # recruit_obj.add_objective_to_config(config)
    # recruit_n = oty.RecruitNCharactersObjective(
    #     2, 0x7F003E, objective_pool[0])
    # recruit_n.add_objective_to_config(config)
    # rock_n = oty.ObtainNRocksObjective(1, 0x7F003D, objective_pool[0])
    # rock_n.add_objective_to_config(settings, config)

    # forge_obj = oty.ForgeMasaMuneObjective(objective_pool[1])
    # forge_obj.add_objective_to_config(config)
    # frag = oty.CollectNFragmentsObjective(10, 5, objective_pool[1])
    # frag.add_objective_to_config(settings, config)


def modify_bucket_activation(
        ct_rom: ctrom.CTRom,
        num_objectives_needed: int,
        objective_count_addr: int
        ):
    '''
    Change to bucket to work when the objectives are complete or under the
    usual circumstances.
    '''

    script = ct_rom.script_manager.get_script(
        ctenums.LocID.END_OF_TIME
    )

    bucket_obj_id = 9
    bucket_func_id = 1

    start = script.get_function_start(bucket_obj_id, bucket_func_id)
    end = script.get_function_end(bucket_obj_id, bucket_func_id)

    jump_cmd = EC.if_mem_op_value(0x7F022E, OP.NOT_EQUALS, 0, 1, 0)
    jump_pos = script.find_exact_command(jump_cmd, start, end)
    jump_cmd = eventcommand.get_command(script.data, jump_pos)

    block_st = jump_pos + len(jump_cmd)
    jump_bytes = jump_cmd.args[-1]
    block_end = block_st + jump_bytes - 1

    bucket_act = EF.from_bytearray(script.data[block_st: block_end])
    bucket_func = (
        EF()
        .add_if(
            EC.if_mem_op_value(objective_count_addr, OP.GREATER_OR_EQUAL,
                               num_objectives_needed, 1, 0),
            EF().jump_to_label(EC.jump_forward(0), 'activate')
        )
        .add_if_else(
            EC.if_mem_op_value(0x7F022E, OP.NOT_EQUALS, 0, 1, 0),
            EF().jump_to_label(EC.jump_forward(0), 'activate'),
            EF().jump_to_label(EC.jump_forward(0), 'end')
        )
        .set_label('activate')
        .add(EC.pause(0))  # dummy command to attach label to
        .append(bucket_act)
        .add(EC.set_explore_mode(True))
        .set_label('end')
        .add(EC.return_cmd())
    )

    script.set_function(bucket_obj_id, bucket_func_id, bucket_func)


def write_objectives_to_ctrom(
        ct_rom: ctrom.CTRom,
        settings: rset.Settings,
        config: cfg.RandoConfig
        ):

    bucket_settings = settings.bucket_settings
    modify_bucket_activation(
        ct_rom, bucket_settings.objectives_needed, 0x7F003F
    )

    script = ct_rom.script_manager.get_script(ctenums.LocID.TELEPOD_EXHIBIT)
    obj_id = script.append_empty_object()

    objs = config.objectives
    obj_str = ''
    for ind, obj in enumerate(objs):
        obj_str += f'{ind+1}) {obj.desc}'

        if ind == len(objs)-1:
            obj_str += '{null}'
        elif (ind - 2) % 4 == 0:
            obj_str += '{full break}'
        else:
            obj_str += '{linebreak+0}'

    num_objs = len(config.objectives)
    needed_objs = settings.bucket_settings.objectives_needed
    if num_objs == needed_objs:
        count_str = 'All.{linebreak+0}'
    else:
        count_str = f'{needed_objs} of {num_objs}.{{linebreak+0}}'

    obj_str = 'Bucket List: Complete ' + count_str + obj_str
    dec_str = \
        'Review Objectives in the Item Menu!{line break}'\
        '   See the list again{line break}'\
        '   Close this message{null}'

    str_id = script.add_py_string(obj_str)
    dec_id = script.add_py_string(dec_str)

    add_objs_fn = EF()
    for ind in range(needed_objs):
        add_objs_fn.add(EC.add_item(ctenums.ItemID.OBJ_COUNT))

    for obj in objs:
        add_objs_fn.add(EC.add_item(obj.item_id))


        

    script.set_function(
        obj_id, 0,
        (
            EF()
            .add(EC.return_cmd())
            .add_if(
                EC.if_storyline_counter_lt(0x0C, 0),
                EF()
                .append(add_objs_fn)
                .set_label('text')
                .add(EC.auto_text_box(str_id))
                .add(EC.decision_box(dec_id, 1, 2, 'auto'))
                .add_if(
                    EC.if_result_equals(1, 0),
                    EF().jump_to_label(EC.jump_back(0), 'text')
                )
            )
            .add(EC.end_cmd())
        )
    )

    objectives = config.objectives
    for objective in objectives:
        objective.add_objective_check_to_ctrom(
            ct_rom,
            settings.bucket_settings.objectives_needed,
            0x7F003F)

    xpscale.double_xp(ct_rom, 0x7E287E)
