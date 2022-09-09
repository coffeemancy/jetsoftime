import random

import bossrandoevent
import ctenums
import ctrom
import ctstrings
import eventcommand
import itemdata
import treasuredata

import randoconfig as cfg


def apply_vanilla_keys_scripts(ct_rom: ctrom.CTRom):
    '''
    Apply only the parts of VanillaRando that have to do with Key items.
    '''
    restore_ribbon_boost(ct_rom)
    add_vanilla_clone_check_scripts(ct_rom)
    restore_cyrus_grave_script(ct_rom)
    restore_tools_to_carpenter_script(ct_rom)
    split_arris_dome(ct_rom)
    revert_sunken_desert_lock(ct_rom)
    unlock_skyways(ct_rom)


def apply_vanilla_keys_to_config(config: cfg.RandoConfig):
    '''
    Only update the config with vanilla KI data.
    '''
    add_vanilla_clone_check_to_config(config)
    restore_cyrus_grave_check_to_config(config)
    add_arris_food_locker_check_to_config(config)


def unlock_skyways(ct_rom: ctrom.CTRom):
    '''
    Undo the skyway locks to allow Access to Zeal as soon as the player
    lands in the Dark Ages.
    '''

    # This is vanilla functionality used when the players return to Zeal
    # after obtaining the Epoch.  0x7F0057 & 80 being set locks the Skyways.
    # In Jets, this flag is set in the telepod script.

    script = ct_rom.script_manager.get_script(ctenums.LocID.TELEPOD_EXHIBIT)
    del_cmd = eventcommand.EventCommand.set_bit(0x7F0057, 0x80)
    st = script.get_function_start(0xE, 4)
    end = script.get_function_end(0xE, 4)

    pos = script.find_exact_command(del_cmd, st, end)
    if pos is not None:
        script.delete_commands(pos, 1)
    else:
        raise ValueError('Command not found')


def revert_sunken_desert_lock(ct_rom: ctrom.CTRom):
    '''
    Restore vanilla behavior of locking Sunken Desert behind talking with the
    NPC in Zeal Palace.
    '''

    # Note that in VanillaRando games, this does not even need a logic change.
    # Desert is a high-level area that is locked logically behind EoT access.

    # The Sunken Desert is available exactly when 0x7F00F7 & 0x02 is set.
    # This is done in the Telepod Exhibit Script
    EC = ctrom.ctevent.EC
    EF = ctrom.ctevent.EF

    desert_set_cmd = EC.assign_val_to_mem(0x02, 0x7F00F7, 1)

    script = ct_rom.script_manager.get_script(ctenums.LocID.TELEPOD_EXHIBIT)
    pos = script.find_exact_command(desert_set_cmd)
    script.delete_commands(pos, 1)

    # The plant lady is in Zeal Palace (0x191), Object C.
    script = ct_rom.script_manager.get_script(ctenums.LocID.ZEAL_PALACE)

    start = script.get_function_start(0xC, 1)
    del_st, _ = script.find_command([0xC0], start)
    del_cmd = EC.generic_one_arg(0x75, 0x18//2)

    del_end = script.find_exact_command(
        del_cmd, start
    )

    script.delete_commands_range(del_st, del_end)

    new_str = "You're right! Even if it IS the Queen's{linebreak+0}" \
        "command, the Guru of Life gave it to{linebreak+0}" \
        "me. I can't burn it...{full break}" \
        "I'm going to grow it with love.{linebreak+0}"\
        "Someday it may save the environment.{null}"
    new_ctstr = ctstrings.CTString.from_str(new_str)
    new_ctstr.compress()
    new_index = script.add_string(new_ctstr)

    # ctevent functionality can be weird when inserting around jumps and/or
    # ends of functions.  Here we're sort of doing both, so I'm using
    # eventfunctions.
    old_func = script.get_function(0x0C, 1)
    ins_func = EF()
    (
        ins_func
        .add(EC.set_bit(0x7F00F7, 0x02))
        .add(EC.auto_text_box(new_index))
    )

    old_func.insert(ins_func, len(old_func) - len(del_cmd))
    script.set_function(0x0C, 1, old_func)


def add_arris_food_locker_check(ct_rom: ctrom.CTRom):
    # Maybe these should be parameters if we want to be dynamic about it?
    flag_addr = 0x7F00A4
    flag_bit = 0x02

    script = ct_rom.script_manager.get_script(
        ctenums.LocID.ARRIS_DOME_FOOD_LOCKER
    )

    EF = ctrom.ctevent.EF
    EC = ctrom.ctevent.EC
    OP = eventcommand.Operation

    new_str = '{line break}            Got 1 {item}!{null}'
    new_ctstr = ctstrings.CTString.from_str(new_str)
    new_ctstr.compress()

    new_index = script.add_string(new_ctstr)

    item_id = int(ctenums.ItemID.SEED)
    func = EF()
    (
        func
        .add_if_else(
            EC.if_mem_op_value(flag_addr, OP.BITWISE_AND_NONZERO,
                               flag_bit, 1, 0),
            EF(),
            (
                EF()
                .add(EC.add_item(item_id))
                .add(EC.set_bit(flag_addr, flag_bit))
                .add(EC.assign_val_to_mem(item_id, 0x7F0200, 1))
                .add(EC.text_box(new_index, False))
            )
        )
    )

    hook_cmd = EC.set_bit(0x7F00EC, 0x10)
    hook_loc = script.find_exact_command(hook_cmd)
    hook_loc += len(hook_cmd)

    script.insert_commands(func.get_bytearray(), hook_loc)


def add_arris_food_locker_check_to_config(config: cfg.RandoConfig):
    td = treasuredata
    assigned_item = random.choice(td.get_item_list(td.ItemTier.HIGH_GEAR))

    food_locker_check = cfg.ScriptTreasure(
        ctenums.LocID.ARRIS_DOME_FOOD_LOCKER, 0x8, 0x1, assigned_item, 0
    )

    config.treasure_assign_dict[ctenums.TreasureID.ARRIS_DOME_FOOD_LOCKER_KEY]\
        = food_locker_check


def add_arris_dome_seed_turn_in(ct_rom: ctrom.CTRom):

    script = ct_rom.script_manager.get_script(
        ctenums.LocID.ARRIS_DOME
    )

    EF = ctrom.ctevent.EF
    EC = ctrom.ctevent.EC
    OP = eventcommand.Operation
    FS = eventcommand.FuncSync

    # The normal item reward is given by an invisible trigger on the ladder.
    # This is object 0xF, touch
    obj_id = 0xF
    func_id = 2
    start = script.get_function_start(obj_id, func_id)
    end = script.get_function_end(obj_id, func_id)

    hook_cmd = EC.if_mem_op_value(0x7F00A4, OP.BITWISE_AND_NONZERO,
                                  0x01, 1, 0)
    hook_pos = script.find_exact_command(hook_cmd, start, end)

    func = EF()

    # If has seed, do nothing, else return
    (
        func
        .add_if_else(
            EC.if_has_item(ctenums.ItemID.SEED, 0),
            EF(),
            EF().add(EC.return_cmd())
        )
    )

    script.insert_commands(func.get_bytearray(), hook_pos)

    # Update Doan's dialog and allow turn-in by talking to Doan.
    new_str = 'DOAN: Are you sure there was no food?{line break}'\
        'Not even a Seed?{null}'
    new_ctstr = ctstrings.CTString.from_str(new_str)
    new_ctstr.compress()
    new_index = script.add_string(new_ctstr)

    obj_id = 0x0E
    func_id = 0x01
    start = script.get_function_start(obj_id, func_id)
    end = script.get_function_end(obj_id, func_id)

    hook_cmd = EC.if_mem_op_value(0x7F0105, OP.BITWISE_AND_NONZERO, 0x04,
                                  1, 0)
    hook_pos = script.find_exact_command(hook_cmd, start, end)
    hook_pos += len(hook_cmd)

    func = EF()
    (
        func
        .add_if_else(
            # If Doan item given
            EC.if_mem_op_value(0x7F00A4, OP.BITWISE_AND_NONZERO, 0x01,
                               1, 0),
            EF(),  # do nothing... will fall through to the normal text
            (
                EF()
                .add_if(
                    # elif has seed
                    EC.if_has_item(ctenums.ItemID.SEED, 0),
                    (
                        # Call the previous trigger touch function
                        EF()
                        # The moveparty in the other touch function doesn't
                        # quite work.  PCs get stuck in DOAN.
                        .add(EC.move_party(0x2F, 0xD, 0x2E, 0xE, 0x30, 0xE))
                        .add(EC.call_obj_function(0xF, 2, 4, FS.SYNC))
                        .add(EC.return_cmd())
                    )
                )
                .add(EC.text_box(new_index, False))
                .add(EC.return_cmd())
            )
        )
    )

    script.insert_commands(func.get_bytearray(),  hook_pos)


def split_arris_dome(ct_rom: ctrom.CTRom):
    '''
    Updates Arris Dome scripts to have two KI spots.
      (1) The Corpse in the food storage room gives a KI (vanilla Seed)
      (2) Doan gives a KI for checking computer and bringing Seed
    '''

    # (1) The Corpse in the food storage room gives a KI (vanilla Seed)
    add_arris_food_locker_check(ct_rom)

    # (2) Add the seed turn-in to Doan/ladder trigger
    add_arris_dome_seed_turn_in(ct_rom)


def restore_scripts(ct_rom: ctrom.CTRom):
    apply_vanilla_keys_scripts(ct_rom)

    restore_geno_dome_conveyor(ct_rom)
    restore_r_series(ct_rom)
    use_easy_lavos(ct_rom)


def restore_r_series(ct_rom: ctrom.CTRom):
    '''
    Puts the R-Series fight back to 6 robots.
    '''
    script = ctrom.ctevent.Event.from_flux(
        './flux/VR_0E6_RSeries.Flux'
    )
    ct_rom.script_manager.set_script(
        script,
        ctenums.LocID.FACTORY_RUINS_SECURITY_CENTER
    )


def restore_tools_to_carpenter_script(ct_rom: ctrom.CTRom):
    '''
    Make the carpenter accept tools instead of GrandLeon.
    '''
    script = ctrom.ctevent.Event.from_flux(
        './flux/VR_0BC_Choras_Cafe.Flux'
    )
    ct_rom.script_manager.set_script(script, ctenums.LocID.CHORAS_CAFE)


def restore_ribbon_boost(ct_rom: ctrom.CTRom):
    '''
    Gives Robo +3 speed and +10 mdef after the Geno Dome.
    '''
    script = ct_rom.script_manager.get_script(
        ctenums.LocID.GENO_DOME_MAINFRAME
    )

    EC = ctrom.ctevent.EC
    EF = ctrom.ctevent.EF
    OP = eventcommand.Operation

    ribbon_str = \
        'Found AtroposXR\'s ribbon!{line break}' \
        '{robo}\'s Speed+3 and Mdef+10{null}'

    ribbon_ct_str = ctstrings.CTString.from_str(ribbon_str)
    ribbon_ct_str.compress()

    ribbon_str_id = script.add_string(ribbon_ct_str)

    func = EF()
    (
        func
        .add(EC.assign_mem_to_mem(0x7E26FD, 0x7F021C, 1))
        .add(EC.add_value_to_mem(3, 0x7F021C))
        .add_if(
            EC.if_mem_op_value(0x7F021C, OP.GREATER_THAN, 0x10, 1, 0),
            (
                EF()
                .add(EC.assign_val_to_mem(0x10, 0x7F021C, 1))
            )
        )
        .add(EC.assign_mem_to_mem(0x7F021C, 0x7E26FD, 1))
        .add(EC.assign_mem_to_mem(0x7E2701, 0x7F021C, 1))
        .add(EC.add_value_to_mem(0xA, 0x7F021C))
        .add_if(
            EC.if_mem_op_value(0x7F021C, OP.GREATER_THAN, 0x50, 1, 0),
            (
                EF()
                .add(EC.assign_val_to_mem(0x50, 0x7F021C, 1))
            )
        )
        .add(EC.assign_mem_to_mem(0x7F021C, 0x7E2701, 1))
        .add(EC.text_box(ribbon_str_id))
    )

    st = script.get_function_start(1, 4)
    end = script.get_function_end(1, 4)

    pos, _ = script.find_command([0xBB], st, end)
    script.insert_commands(func.get_bytearray(), pos)


def restore_geno_dome_conveyor(ct_rom: ctrom.CTRom):
    '''
    Make the enemies on the Geno Dome conveyor the vanilla enemies.
    '''
    script = ctrom.ctevent.Event.from_flux(
        './flux/VR_07E_geno_conveyor.Flux'
    )
    ct_rom.script_manager.set_script(script, ctenums.LocID.GENO_DOME_CONVEYOR)


class BekklerTreasure(cfg.ScriptTreasure):
    '''
    Treasure type for setting the Bekkler key item.
    '''
    def __init__(self,
                 location: ctenums.LocID,
                 object_id: int, function_id: int,
                 held_item: ctenums.ItemID = ctenums.ItemID.MOP,
                 item_num=0,
                 bekkler_location: ctenums.LocID = ctenums.LocID.BEKKLERS_LAB,
                 bekkler_object_id: int = 0x0B,
                 bekkler_function_id: int = 0x01):
        cfg.ScriptTreasure.__init__(
            self, location, object_id, function_id, held_item, item_num
        )

        self.bekkler_location = bekkler_location
        self.bekkler_object_id = bekkler_object_id
        self.bekkler_function_id = bekkler_function_id

    def write_to_ctrom(self, ct_rom: ctrom.CTRom):
        cfg.ScriptTreasure.write_to_ctrom(self, ct_rom)
        self.write_bekkler_name_to_ct_rom(ct_rom)

    def write_bekkler_name_to_ct_rom(self, ct_rom: ctrom.CTRom):
        script = ct_rom.script_manager.get_script(self.bekkler_location)

        st = script.get_function_start(self.bekkler_object_id,
                                       self.bekkler_function_id)
        end = script.get_function_end(self.bekkler_object_id,
                                      self.bekkler_function_id)

        pos, _ = script.find_command([0x4F], st, end)
        script.data[pos+1] = int(self.held_item)


def add_vanilla_clone_check_to_config(config: cfg.RandoConfig):
    td = treasuredata
    assigned_item = random.choice(
        td.get_item_list(td.ItemTier.AWESOME_GEAR)
    )

    bekkler_check = BekklerTreasure(
        ctenums.LocID.CRONOS_ROOM, 0x13, 1, assigned_item, 0,
        ctenums.LocID.BEKKLERS_LAB, 0xB, 1
    )

    config.treasure_assign_dict[ctenums.TreasureID.BEKKLER_KEY] = \
        bekkler_check


def add_vanilla_clone_check_scripts(ct_rom: ctrom.CTRom):
    script = ctrom.ctevent.Event.from_flux('./flux/VR_002_Crono_Room.Flux')
    ct_rom.script_manager.set_script(script, ctenums.LocID.CRONOS_ROOM)

    script = ctrom.ctevent.Event.from_flux('./flux/VR_1B2_Bekkler_Lab.Flux')
    ct_rom.script_manager.set_script(script, ctenums.LocID.BEKKLERS_LAB)


def restore_cyrus_grave_script(ct_rom: ctrom.CTRom):
    script = ctrom.ctevent.Event.from_flux(
        './flux/VR_049_Northern_Ruins_Heros_Grave.Flux'
    )
    ct_rom.script_manager.set_script(
        script, ctenums.LocID.NORTHERN_RUINS_HEROS_GRAVE
    )


def restore_magus_castle_decedents(config: cfg.RandoConfig):
    '''Copy Decedent to Frog King spot'''
    decedent_stats = config.enemy_dict[ctenums.EnemyID.DECEDENT].get_copy()
    config.enemy_dict[ctenums.EnemyID.DECEDENT_II] = decedent_stats
    config.enemy_aidb.change_enemy_ai(
        ctenums.EnemyID.DECEDENT_II, ctenums.EnemyID.DECEDENT
    )
    config.enemy_atkdb.copy_atk_gfx(
        ctenums.EnemyID.DECEDENT_II, ctenums.EnemyID.DECEDENT
    )


def restore_cyrus_grave_check_to_config(config: cfg.RandoConfig):

    td = treasuredata
    assigned_item = random.choice(
        td.get_item_list(td.ItemTier.AWESOME_GEAR)
    )
    cyrus_check = cfg.ScriptTreasure(
        ctenums.LocID.NORTHERN_RUINS_HEROS_GRAVE, 5, 8,
        assigned_item
    )

    config.treasure_assign_dict[ctenums.TreasureID.CYRUS_GRAVE_KEY] = \
        cyrus_check


def restore_sos(ct_rom: ctrom.CTRom, config: cfg.RandoConfig):

    if config.boss_assign_dict[ctenums.LocID.SUN_PALACE] == \
       ctenums.BossID.SON_OF_SUN:

        bossrandoevent.set_sun_palace_boss(
            ct_rom,
            config.boss_data_dict[ctenums.BossID.SON_OF_SUN].scheme
        )


def fix_item_data(config: cfg.RandoConfig):

    item_db = config.itemdb
    IID = ctenums.ItemID

    config.itemdb[IID.MASAMUNE_2].set_name_from_str('{blade}GrandLeon')
    roboribbon = config.itemdb[IID.ROBORIBBON]

    # Put roboribbon in (but inaccessible) so that roboribbon.py doesn't
    # mess things up.
    T9 = itemdata.Type_09_Buffs
    roboribbon.stats.has_battle_buff = True
    roboribbon.stats.has_stat_boost = True
    roboribbon.stats.battle_buffs = (T9.SPECS, T9.SHIELD, T9.BARRIER)
    roboribbon.secondary_stats.stat_boost_index = 9

    # Fix prices for normally unsellable things
    for item_id in (IID.BANDANA, IID.RIBBON, IID.POWERGLOVE, IID.DEFENDER,
                    IID.MAGICSCARF, IID.SIGHTSCOPE):
        item_db[item_id].price = 100

    for item_id in (IID.HIT_RING, IID.BERSERKER, IID.POWERSCARF,
                    IID.MUSCLERING, IID.SERAPHSONG):
        item_db[item_id].price = 1000

    for item_id in (IID.POWER_RING, IID.MAGIC_RING, IID.SILVERERNG):
        item_db[item_id].price = 5000

    item_db[IID.RAGE_BAND].price = 2000
    item_db[IID.THIRD_EYE].price = 2000
    item_db[IID.WALLET].price = 4000
    item_db[IID.WALL_RING].price = 4000
    item_db[IID.FRENZYBAND].price = 5500
    item_db[IID.SLASHER].price = 16500
    item_db[IID.RAINBOW].price = 65000
    item_db[IID.PRISMSPECS].price = 62000
    item_db[IID.SUN_SHADES].price = 62000
    item_db[IID.GOLD_STUD].price = 60000
    item_db[IID.TABAN_SUIT].price = 53000
    item_db[IID.AMULET].price = 50000
    item_db[IID.DASH_RING].price = 40000
    item_db[IID.SILVERSTUD].price = 40000
    item_db[IID.GOLD_ERNG].price = 30000
    item_db[IID.CHARM_TOP].price = 20000
    item_db[IID.SPEED_BELT].price = 20000
    item_db[IID.MAGIC_SEAL].price = 20000
    item_db[IID.POWER_SEAL].price = 25000
    item_db[IID.TABAN_VEST].price = 10000

    # Make things sellable


def scale_enemy_xp_tp(config: cfg.RandoConfig,
                      xp_scale_factor: float = 4.0,
                      tp_scale_factor: float = 2.0):

    xp_thresh = config.char_manager.xp_thresh
    for ind, x in enumerate(xp_thresh):
        xp_thresh[ind] = round(x/xp_scale_factor)

    for char in config.char_manager.pcs:
        # fix xp to next
        char.stats.xp_thresh = list(config.char_manager.xp_thresh)
        char.stats.set_level(char.stats.level)

        for ind, tp_thresh in enumerate(char.stats.tp_thresh):
            new_thresh = round(tp_thresh/tp_scale_factor)
            new_thresh = max(1, new_thresh)
            char.stats.tp_thresh[ind] = new_thresh


def fix_required_tp(config: cfg.RandoConfig):

    CharID = ctenums.CharID

    # Crono, Lucca, Marle, and Frog have no TP for 3rd tech
    for char_id in (CharID.CRONO, CharID.MARLE, CharID.LUCCA, CharID.FROG):
        char = config.char_manager.pcs[char_id]
        char.stats.tp_thresh[2] = 100

    # Robo has no TP for first two techs and 5 TP for Laser Spin
    robo = config.char_manager.pcs[CharID.ROBO]
    robo.stats.tp_thresh[0:3] = [5, 50, 100]

    # Magus has no TP for first three techs
    magus = config.char_manager.pcs[CharID.MAGUS]
    magus.stats.tp_thresh[0:3] = [100, 100, 100]


def fix_magic_learning(config: cfg.RandoConfig):
    CharID = ctenums.CharID
    magic_learners = (CharID.CRONO, CharID.MARLE, CharID.LUCCA, CharID.FROG)
    for char_id in magic_learners:
        for tech_num in range(3):
            tech_id = 1 + char_id*8 + tech_num
            magic_byte = tech_id*0xB
            config.techdb.controls[magic_byte] &= 0x7F
        for tech_num in range(3, 8):
            tech_id = 1 + char_id*8 + tech_num
            magic_byte = tech_id*0xB
            config.techdb.controls[magic_byte] |= 0x80


def restore_son_of_sun_flame(config: cfg.RandoConfig):
    EID = ctenums.EnemyID
    sos_scheme = cfg.bossdata.BossScheme(
        [EID.SON_OF_SUN_EYE, EID.SON_OF_SUN_FLAME, EID.SON_OF_SUN_FLAME,
         EID.SON_OF_SUN_FLAME, EID.SON_OF_SUN_FLAME, EID.SON_OF_SUN_FLAME],
        [(0, 0), (0x18, -0x8), (0xC, 0x17), (-0xC, 0x17), (-0x18, -0x8),
         (0, -0x16)],
        [3, 4, 5, 6, 7, 8]
    )

    config.boss_data_dict[ctenums.BossID.SON_OF_SUN].scheme = sos_scheme


def fix_twin_boss(config: cfg.RandoConfig):
    '''Rewrite Vanilla Twin Golem i the Twin Boss spot'''
    EnemyID = ctenums.EnemyID
    # In vanilla, the twin boss is just a copy of the golem
    golem_stats = config.enemy_dict[EnemyID.GOLEM].get_copy()
    config.enemy_dict[EnemyID.TWIN_BOSS] = golem_stats
    config.enemy_aidb.change_enemy_ai(EnemyID.TWIN_BOSS, EnemyID.GOLEM)
    config.enemy_atkdb.copy_atk_gfx(EnemyID.TWIN_BOSS, EnemyID.GOLEM)

    base_slot = config.boss_data_dict[ctenums.BossID.GOLEM].scheme.slots[0]
    alt_slot = bossrandoevent.get_alt_twin_slot(config, ctenums.BossID.GOLEM)

    new_slots = [base_slot, alt_slot]
    config.boss_data_dict[ctenums.BossID.TWIN_BOSS].scheme.slots = new_slots


def rebalance_nizbel(config: cfg.RandoConfig):
    '''
    Make Nizbel take ~50% damage without shock instead of almost none.
    '''

    nizbel = config.enemy_dict[ctenums.EnemyID.NIZBEL]
    nizbel.defense = 0xC3  # 195
    nizbel.mdef = 0x4B  # 75

    nizbel_ai = config.enemy_aidb.scripts[ctenums.EnemyID.NIZBEL]
    nizbel_ai_b = nizbel_ai.get_as_bytearray()

    loc = nizbel_ai.find_command(nizbel_ai_b, 0x12)[0]
    new_cmd = bytearray.fromhex(
        '12 27 05 00 00 3E C3 3C 4B 3C 4B 3C 4B 3C 4B 24'
    )

    nizbel_ai_b[loc: loc + len(new_cmd)] = new_cmd

    config.enemy_aidb.scripts[ctenums.EnemyID.NIZBEL] = \
        cfg.enemyai.AIScript(nizbel_ai_b)


def rescale_bosses(config: cfg.RandoConfig):
    BID = ctenums.BossID
    bdd = config.boss_data_dict

    bdd[BID.ATROPOS_XR].power = 20
    bdd[BID.DALTON_PLUS].power = 30
    bdd[BID.ELDER_SPAWN].power = 45
    bdd[BID.FLEA].power = 20
    bdd[BID.FLEA_PLUS].power = 20
    bdd[BID.GIGA_GAIA].power = 30
    bdd[BID.GIGA_MUTANT].power = 45
    bdd[BID.GOLEM].power = 25
    bdd[BID.GOLEM_BOSS].power = 25
    bdd[BID.GUARDIAN].power = 10
    bdd[BID.HECKRAN].power = 10
    bdd[BID.LAVOS_SPAWN].power = 25
    bdd[BID.MASA_MUNE].power = 12
    bdd[BID.MEGA_MUTANT].power = 40
    bdd[BID.MOTHER_BRAIN].power = 30
    bdd[BID.NIZBEL].power = 20
    bdd[BID.NIZBEL_2].power = 25
    bdd[BID.RETINITE].power = 40
    bdd[BID.RUST_TYRANO].power = 40
    bdd[BID.SON_OF_SUN].power = 45
    bdd[BID.SLASH_SWORD].power = 20
    bdd[BID.SUPER_SLASH].power = 20
    bdd[BID.TERRA_MUTANT].power = 50
    bdd[BID.TWIN_BOSS].power = 25  # power of single golem
    bdd[BID.YAKRA].power = 1
    bdd[BID.YAKRA_XIII].power = 40


def use_easy_lavos(ct_rom: ctrom.CTRom):

    EC = ctrom.ctevent.EC

    load_lavos = EC.load_enemy(int(ctenums.EnemyID.LAVOS_OCEAN_PALACE),
                               3, True)
    script = ct_rom.script_manager.get_script(ctenums.LocID.LAVOS)
    pos = script.find_exact_command(load_lavos)
    script.data[pos+1] = int(ctenums.EnemyID.LAVOS_1)


def fix_config(config: cfg.RandoConfig):
    apply_vanilla_keys_to_config(config)

    fix_item_data(config)
    fix_required_tp(config)  # Do before scaling.
    scale_enemy_xp_tp(config, 2, 2)
    fix_magic_learning(config)
    restore_son_of_sun_flame(config)
    restore_magus_castle_decedents(config)
    fix_twin_boss(config)
    rebalance_nizbel(config)
    rescale_bosses(config)
