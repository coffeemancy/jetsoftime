from __future__ import annotations

import random

import bossassign
import bossrandotypes as rotypes
import bossrandoevent
import ctenums
import ctrom
import ctstrings
import eventcommand
import itemdata
from maps import locationtypes
from treasures import treasuredata, treasuretypes

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
    add_check_to_ozzies_fort_script(ct_rom)
    restore_johnny_race(ct_rom)
    split_sunstone_quest(ct_rom)


def apply_vanilla_keys_to_config(config: cfg.RandoConfig):
    '''
    Only update the config with vanilla KI data.
    '''
    add_vanilla_clone_check_to_config(config)
    restore_cyrus_grave_check_to_config(config)
    add_arris_food_locker_check_to_config(config)
    add_check_to_ozzies_fort_in_config(config)
    add_racelog_chest_to_config(config)
    add_sunstone_spot_to_config(config)


def add_sunstone_spot_to_config(config: cfg.RandoConfig):
    '''
    Add a treasure entry for the sunstone pickup in Sun Keep 2300.
    '''
    td = treasuredata
    assigned_item = random.choice(td.get_item_list(td.ItemTier.HIGH_GEAR))

    sunstone_spot = treasuretypes.ScriptTreasure(
        ctenums.LocID.SUN_KEEP_2300, 8, 1, assigned_item
    )

    config.treasure_assign_dict[ctenums.TreasureID.SUN_KEEP_2300] = \
        sunstone_spot


def split_sunstone_quest(ct_rom: ctrom.CTRom):
    '''
    Have the Moonstone charge into a random item.
    '''

    script = ct_rom.script_manager.get_script(ctenums.LocID.SUN_KEEP_2300)

    EC = ctrom.ctevent.EC
    EF = ctrom.ctevent.EF

    start = script.get_function_start(8, 1)
    explore_off_pos = script.find_exact_command(EC.set_explore_mode(False),
                                                start,
                                                script.get_function_end(8, 1))

    script.delete_commands(explore_off_pos, 1)

    song_cmd = eventcommand.get_command(b'\xEA\x3D')
    hook_pos = script.find_exact_command(song_cmd,
                                         explore_off_pos,
                                         script.get_function_end(8, 1))
    hook_pos += len(song_cmd)

    new_ind = script.add_py_string(
        "Moon Stone powered up!{linebreak+0}"
        "{item} acquired!{null}"
    )

    item_id = int(ctenums.ItemID.SUN_STONE)

    new_item_func = EF()
    (
        new_item_func
        .add(EC.set_bit(0x7F013A, 0x40))
        .add(EC.assign_val_to_mem(item_id, 0x7F0200, 1))
        .add(EC.add_item(item_id))
        .add(EC.auto_text_box(new_ind))
        .add(EC.generic_zero_arg(0xEE))  # Song End
        .add(eventcommand.get_command(b'\xEA\x10'))  # Manoria Song
        .add(EC.remove_object(8))
        .add(EC.return_cmd())
    )

    new_item_func_b = new_item_func.get_bytearray()
    script.insert_commands(new_item_func_b, hook_pos)

    del_st = hook_pos + len(new_item_func_b)
    del_end = script.get_function_end(8, 1)

    script.delete_commands_range(del_st, del_end)

    # Also need to change the Melchior check to check for sunstone instead
    # of the charged item received flag.

    script = ct_rom.script_manager.get_script(
        ctenums.LocID.GUARDIA_REAR_STORAGE
    )

    start = script.get_function_start(0x17, 1)
    hook_pos = script.find_exact_command(
        EC.if_mem_op_value(0x7F013A,
                           eventcommand.Operation.BITWISE_AND_NONZERO,
                           0x40, 1, 0)
    )

    cmd = eventcommand.get_command(script.data, hook_pos)
    bytes_jumped = cmd.args[-1]

    script.delete_commands(hook_pos, 1)
    script.insert_commands(EC.if_has_item(ctenums.ItemID.SUN_STONE,
                                          bytes_jumped).to_bytearray(),
                           hook_pos)


def add_racelog_chest_to_config(config: cfg.RandoConfig):
    td = treasuredata
    assigned_item = random.choice(td.get_item_list(td.ItemTier.HIGH_GEAR))
    config.treasure_assign_dict[ctenums.TreasureID.LAB_32_RACE_LOG]\
          .held_item = assigned_item


def restore_johnny_race(ct_rom: ctrom.CTRom):
    '''
    Adds the Johhny race to Lab 32.  The Bike Key + Crono is required to race
    Johnny.  Just the Bike Key is needed to traverse Lab32 on foot.
    '''
    script = ctrom.ctevent.Event.from_flux('./flux/VR_0DF_Lab32_West.Flux')
    ct_rom.script_manager.set_script(script, ctenums.LocID.LAB_32_WEST)

    # delete the normal exit to Lab32.  It will be in-script.
    exits = locationtypes.LocExits.from_rom(ct_rom.rom_data)
    exits.delete_exit(ctenums.LocID.LAB_32_EAST, 1)
    exits.write_to_fsrom(ct_rom.rom_data)

    script = ctrom.ctevent.Event.from_flux('./flux/VR_0E1_Lab32_East.Flux')
    ct_rom.script_manager.set_script(script, ctenums.LocID.LAB_32_EAST)

def add_check_to_ozzies_fort_in_config(config: cfg.RandoConfig):
    '''
    Add an entry in the config for the Ozzie's Fort KI.
    '''
    td = treasuredata
    assigned_item = random.choice(td.get_item_list(td.ItemTier.HIGH_GEAR))

    ozzies_fort_check = treasuretypes.ScriptTreasure(
        ctenums.LocID.OZZIES_FORT_THRONE_INCOMPETENCE,
        0x8, 0x2, assigned_item, 0
    )

    config.treasure_assign_dict[ctenums.TreasureID.OZZIES_FORT_KEY]\
        = ozzies_fort_check


def add_check_to_ozzies_fort_script(ct_rom: ctrom.CTRom):
    '''
    Modify the script for Ozzie's Fort to give the player a KI after the cat
    drops Ozzie.
    '''
    script = ct_rom.script_manager.get_script(
        ctenums.LocID.OZZIES_FORT_THRONE_INCOMPETENCE
    )

    new_ind = script.add_py_string(
        '{line break}            Got 1 {item}!{null}'
    )

    EC = eventcommand.EventCommand
    EF = ctrom.ctevent.EF

    start = script.get_function_start(8, 2)
    hook_loc = script.find_exact_command(EC.party_follow(), start)

    item_id = int(ctenums.ItemID.MOP)
    get_item_func = (
        EF()
        .add(EC.assign_val_to_mem(item_id, 0x7F0200, 1))
        .add(EC.auto_text_box(new_ind))
        .add(EC.add_item(item_id))
    )

    script.insert_commands(get_item_func.get_bytearray(), hook_loc)


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

    update_zeal_throne_door(ct_rom)


def update_zeal_throne_door(ct_rom: ctrom.CTRom):
    '''
    Since Zeal opens earlier, make sure the door is locked properly.
    '''

    script = ct_rom.script_manager.get_script(
        ctenums.LocID.ZEAL_PALACE_REGAL_ANTECHAMBER
    )

    func = script.get_function(0xC, 2)
    EF = ctrom.ctevent.EF
    EC = ctrom.ctevent.EC
    OP = eventcommand.Operation

    new_ind = script.add_py_string(
        "The Ocean Palace is guarded by magic.{full break}"
        "Defeat the Black Tyrano and bring a{linebreak+0}"
        "Ruby Knife or defeat Magus to break{linebreak+0}"
        "the seal.{null}"
    )

    tyrano_check = (
        EF()
        .add_if_else(
            EC.if_mem_op_value(0x7F00EC, OP.BITWISE_AND_NONZERO, 0x80, 1, 0),
            func,
            (
                EF()
                .add(EC.auto_text_box(new_ind))
                .add(EC.return_cmd())
            )
        )
    )

    script.set_function(0xC, 2, tyrano_check)

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

    food_locker_check = treasuretypes.ScriptTreasure(
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


class BekklerTreasure(treasuretypes.ScriptTreasure):
    '''
    Treasure type for setting the Bekkler key item.
    '''
    def __init__(self,
                 location: ctenums.LocID,
                 object_id: int, function_id: int,
                 reward: treasuretypes.RewardType = ctenums.ItemID.MOP,
                 item_num=0,
                 bekkler_location: ctenums.LocID = ctenums.LocID.BEKKLERS_LAB,
                 bekkler_object_id: int = 0x0B,
                 bekkler_function_id: int = 0x01):
        treasuretypes.ScriptTreasure.__init__(
            self, location, object_id, function_id, reward, item_num
        )

        self.bekkler_location = bekkler_location
        self.bekkler_object_id = bekkler_object_id
        self.bekkler_function_id = bekkler_function_id

    def write_to_ctrom(self, ct_rom: ctrom.CTRom):
        # I'm not correctly handling gold rewards in this spot, so we'll just
        # make it a mop if somehow that happens.
        if not isinstance(self.reward, ctenums.ItemID):
            self.reward = ctenums.ItemID.MOP

        treasuretypes.ScriptTreasure.write_to_ctrom(self, ct_rom)
        self.write_bekkler_name_to_ct_rom(ct_rom)

    def write_bekkler_name_to_ct_rom(self, ct_rom: ctrom.CTRom):
        '''
        Write the item name out to the Bekkler script.
        '''
        script = ct_rom.script_manager.get_script(self.bekkler_location)

        start = script.get_function_start(self.bekkler_object_id,
                                       self.bekkler_function_id)
        end = script.get_function_end(self.bekkler_object_id,
                                      self.bekkler_function_id)

        pos, _ = script.find_command([0x4F], start, end)

        # TODO: Handle gold being placed at this spot.
        # TODO: Fix "The clone will be at Crono's house." text to have theen
        #       correct reward text.
        script.data[pos+1] = int(self.reward)


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
    config.enemy_ai_db.change_enemy_ai(
        ctenums.EnemyID.DECEDENT_II, ctenums.EnemyID.DECEDENT
    )
    config.enemy_atk_db.copy_atk_gfx(
        ctenums.EnemyID.DECEDENT_II, ctenums.EnemyID.DECEDENT
    )


def restore_cyrus_grave_check_to_config(config: cfg.RandoConfig):

    td = treasuredata
    assigned_item = random.choice(
        td.get_item_list(td.ItemTier.AWESOME_GEAR)
    )
    cyrus_check = treasuretypes.ScriptTreasure(
        ctenums.LocID.NORTHERN_RUINS_HEROS_GRAVE, 5, 8,
        assigned_item
    )

    config.treasure_assign_dict[ctenums.TreasureID.CYRUS_GRAVE_KEY] = \
        cyrus_check


def restore_sos(ct_rom: ctrom.CTRom, config: cfg.RandoConfig):

    if config.boss_assign_dict[rotypes.BossSpotID.SUN_PALACE] == \
       rotypes.BossID.SON_OF_SUN:

        bossassign.set_sun_palace_boss(
            ct_rom,
            config.boss_data_dict[rotypes.BossID.SON_OF_SUN]
        )


def fix_item_data(config: cfg.RandoConfig):

    item_db = config.item_db
    IID = ctenums.ItemID

    config.item_db[IID.MASAMUNE_2].set_name_from_str('{blade}GrandLeon')
    roboribbon = config.item_db[IID.ROBORIBBON]

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

    xp_thresh = config.pcstats.xp_thresholds
    for ind, x in enumerate(xp_thresh):
        xp_thresh[ind] = round(x/xp_scale_factor)

    for char, stats in config.pcstats.pc_stat_dict.items():
        # fix xp to next
        cur_level = config.pcstats.get_level(char)
        config.pcstats.set_level(char, cur_level)

        for ind in range(8):
            old_thresh = stats.tp_threshholds.get_threshold(ind)
            new_thresh = round(old_thresh/tp_scale_factor)
            new_thresh = max(1, new_thresh)
            stats.tp_threshholds.set_threshold(ind, new_thresh)


def fix_required_tp(config: cfg.RandoConfig):

    CharID = ctenums.CharID

    # Crono, Lucca, Marle, and Frog have no TP for 3rd tech
    for char_id in (CharID.CRONO, CharID.MARLE, CharID.LUCCA, CharID.FROG):
        tp_thresh = config.pcstats.pc_stat_dict[char_id].tp_threshholds
        tp_thresh.set_threshold(2, 100)

    # Robo has no TP for first two techs and 5 TP for Laser Spin
    robo_tp = config.pcstats.pc_stat_dict[CharID.ROBO].tp_threshholds
    robo_tp.set_threshold(0, 5)
    robo_tp.set_threshold(1, 50)
    robo_tp.set_threshold(2, 100)

    # Magus has no TP for first three techs
    magus_tp = config.pcstats.pc_stat_dict[CharID.MAGUS].tp_threshholds
    magus_tp.set_threshold(0, 100)
    magus_tp.set_threshold(1, 100)
    magus_tp.set_threshold(2, 100)


def fix_magic_learning(config: cfg.RandoConfig):
    CharID = ctenums.CharID
    magic_learners = (CharID.CRONO, CharID.MARLE, CharID.LUCCA, CharID.FROG)
    for char_id in magic_learners:
        for tech_num in range(3):
            tech_id = 1 + char_id*8 + tech_num
            magic_byte = tech_id*0xB
            config.tech_db.controls[magic_byte] &= 0x7F
        for tech_num in range(3, 8):
            tech_id = 1 + char_id*8 + tech_num
            magic_byte = tech_id*0xB
            config.tech_db.controls[magic_byte] |= 0x80


def restore_son_of_sun_flame(config: cfg.RandoConfig):
    '''
    Add fifth flame and restore vanilla flame displacements.
    '''
    EID = ctenums.EnemyID
    sos_scheme = rotypes.BossScheme(
        rotypes.BossPart(EID.SON_OF_SUN_EYE, 3, (0, 0)),
        rotypes.BossPart(EID.SON_OF_SUN_FLAME, 4, (0x18, -0x8)),
        rotypes.BossPart(EID.SON_OF_SUN_FLAME, 5, (0xC, 0x17)),
        rotypes.BossPart(EID.SON_OF_SUN_FLAME, 6, (-0xC, 0x17)),
        rotypes.BossPart(EID.SON_OF_SUN_FLAME, 7, (-0x18, 0x8)),
        rotypes.BossPart(EID.SON_OF_SUN_FLAME, 7, (0, 0x16)),
    )
    config.boss_data_dict[rotypes.BossID.SON_OF_SUN] = sos_scheme


def fix_twin_boss(config: cfg.RandoConfig):
    '''Rewrite Vanilla Twin Golem i the Twin Boss spot'''
    EnemyID = ctenums.EnemyID
    # In vanilla, the twin boss is just a copy of the golem
    golem_stats = config.enemy_dict[EnemyID.GOLEM].get_copy()
    config.enemy_dict[EnemyID.TWIN_BOSS] = golem_stats
    config.enemy_ai_db.change_enemy_ai(EnemyID.TWIN_BOSS, EnemyID.GOLEM)
    config.enemy_atk_db.copy_atk_gfx(EnemyID.TWIN_BOSS, EnemyID.GOLEM)

    base_slot = config.boss_data_dict[rotypes.BossID.GOLEM]\
        .parts[0].slot
    alt_slot = bossrandoevent.get_alt_twin_slot(config, rotypes.BossID.GOLEM)

    scheme = config.boss_data_dict[rotypes.BossID.TWIN_BOSS]
    scheme.parts[0].slot = base_slot
    scheme.parts[1].slot = alt_slot


def rebalance_nizbel(config: cfg.RandoConfig):
    '''
    Make Nizbel take ~50% damage without shock instead of almost none.
    '''

    nizbel = config.enemy_dict[ctenums.EnemyID.NIZBEL]
    nizbel.defense = 0xC3  # 195
    nizbel.mdef = 0x4B  # 75

    nizbel_ai = config.enemy_ai_db.scripts[ctenums.EnemyID.NIZBEL]
    nizbel_ai_b = nizbel_ai.get_as_bytearray()

    loc = nizbel_ai.find_command(nizbel_ai_b, 0x12)[0]
    new_cmd = bytearray.fromhex(
        '12 27 05 00 00 3E C3 3C 4B 3C 4B 3C 4B 3C 4B 24'
    )

    nizbel_ai_b[loc: loc + len(new_cmd)] = new_cmd

    config.enemy_ai_db.scripts[ctenums.EnemyID.NIZBEL] = \
        cfg.enemyai.AIScript(nizbel_ai_b)


def rescale_bosses(config: cfg.RandoConfig):
    BID = rotypes.BossID
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


def get_vanilla_treasure_tiers() -> dict[treasuredata.TreasureLocTier,
                                         ctenums.TreasureID]:

    TID = ctenums.TreasureID
    td = treasuredata

    ret_dict = {
        tier: None
        for tier in td.TreasureLocTier
    }

    # Recall Progression is Cath, Trial, Early Future, Heckran,
    # Denadoro, Reptite, Magus, Tyrano, Woe, Ocean Palace, Sidequests, Omen

    # Low = Open, Cath
    # LowMid = Trial, Early Future, Heckran
    # Mid = Denadoro, Repite, Magus, Tyrano
    # MidHigh = Woe, Ocean Palace, SideQuests
    # HighAwe = Omen

    ret_dict[td.TreasureLocTier.LOW] = [
        TID.TRUCE_MAYOR_1F, TID.TRUCE_MAYOR_2F, TID.KINGS_ROOM_1000,
        TID.QUEENS_ROOM_1000, TID.FOREST_RUINS, TID.PORRE_MAYOR_2F,
        TID.TRUCE_CANYON_1, TID.TRUCE_CANYON_2, TID.KINGS_ROOM_600,
        TID.QUEENS_ROOM_600, TID.ROYAL_KITCHEN, TID.CURSED_WOODS_1,
        TID.CURSED_WOODS_2, TID.FROGS_BURROW_RIGHT, TID.FIONAS_HOUSE_1,
        TID.FIONAS_HOUSE_2, TID.QUEENS_TOWER_600, TID.KINGS_TOWER_600,
        TID.KINGS_TOWER_1000, TID.QUEENS_TOWER_1000, TID.GUARDIA_COURT_TOWER,
        # Manoria Cathedral
        TID.MANORIA_CATHEDRAL_1, TID.MANORIA_CATHEDRAL_2,
        TID.MANORIA_CATHEDRAL_3,
        TID.MANORIA_INTERIOR_1, TID.MANORIA_INTERIOR_2,
        TID.MANORIA_INTERIOR_3, TID.MANORIA_INTERIOR_4,
        TID.MANORIA_SHRINE_SIDEROOM_1, TID.MANORIA_SHRINE_SIDEROOM_2,
        TID.MANORIA_BROMIDE_1, TID.MANORIA_BROMIDE_2,
        TID.MANORIA_BROMIDE_3,
    ]

    # TID.YAKRAS_ROOM to mid.  Vanilla mid ether
    # In standard jets TID.MANORIA_INTERIOR_3 is tiered mid

    ret_dict[td.TreasureLocTier.LOW_MID] = [
        # Magus's shrine has a speed belt (!) in vanilla.  Boost tier?
        TID.MANORIA_SHRINE_MAGUS_1, TID.MANORIA_SHRINE_MAGUS_2,
        # Heckran's Cave
        TID.HECKRAN_CAVE_SIDETRACK, TID.HECKRAN_CAVE_ENTRANCE,
        TID.HECKRAN_CAVE_1, TID.HECKRAN_CAVE_2,
        # Guardia Prison
        # Consider improving out-of-the-way chests.
        TID.PRISON_TOWER_1000, TID.GUARDIA_JAIL_FRITZ,
        TID.GUARDIA_JAIL_FRITZ_STORAGE, TID.GUARDIA_JAIL_CELL,
        TID.GUARDIA_JAIL_OMNICRONE_1, TID.GUARDIA_JAIL_OMNICRONE_2,
        TID.GUARDIA_JAIL_OMNICRONE_3, TID.GUARDIA_JAIL_HOLE_1,
        TID.GUARDIA_JAIL_HOLE_2, TID.GUARDIA_JAIL_OUTER_WALL,
        TID.GUARDIA_JAIL_OMNICRONE_4, TID.GIANTS_CLAW_KINO_CELL,
        # Early Future
        TID.ARRIS_DOME_FOOD_STORE, TID.ARRIS_DOME_RATS,
        TID.LAB_16_1, TID.LAB_16_2, TID.LAB_16_3, TID.LAB_16_4,
        TID.LAB_32_1, TID.LAB_32_RACE_LOG,
        TID.SEWERS_1, TID.SEWERS_2, TID.SEWERS_3,
        TID.FACTORY_LEFT_AUX_CONSOLE, TID.FACTORY_LEFT_SECURITY_LEFT,
        TID.FACTORY_LEFT_SECURITY_RIGHT, TID.FACTORY_RIGHT_CRANE_LOWER,
        TID.FACTORY_RIGHT_CRANE_UPPER, TID.FACTORY_RIGHT_DATA_CORE_1,
        TID.FACTORY_RIGHT_DATA_CORE_2, TID.FACTORY_RIGHT_FLOOR_BOTTOM,
        TID.FACTORY_RIGHT_FLOOR_LEFT, TID.FACTORY_RIGHT_FLOOR_SECRET,
        TID.FACTORY_RIGHT_FLOOR_TOP, TID.FACTORY_RIGHT_INFO_ARCHIVE,
        TID.FACTORY_RUINS_GENERATOR
    ]

    ret_dict[td.TreasureLocTier.MID] = [
        # Denadoro
        TID.DENADORO_MTS_SCREEN2_1, TID.DENADORO_MTS_SCREEN2_2,
        TID.DENADORO_MTS_SCREEN2_3, TID.DENADORO_MTS_FINAL_1,
        TID.DENADORO_MTS_FINAL_2, TID.DENADORO_MTS_FINAL_3,
        TID.DENADORO_MTS_WATERFALL_TOP_3, TID.DENADORO_MTS_WATERFALL_TOP_4,
        TID.DENADORO_MTS_WATERFALL_TOP_5, TID.DENADORO_MTS_ENTRANCE_1,
        TID.DENADORO_MTS_ENTRANCE_2, TID.DENADORO_MTS_SCREEN3_1,
        TID.DENADORO_MTS_SCREEN3_2, TID.DENADORO_MTS_SCREEN3_3,
        TID.DENADORO_MTS_SCREEN3_4, TID.DENADORO_MTS_AMBUSH,
        TID.DENADORO_MTS_SAVE_PT,
        # Castle Magus
        TID.MAGUS_CASTLE_RIGHT_HALL, TID.MAGUS_CASTLE_GUILLOTINE_1,
        TID.MAGUS_CASTLE_GUILLOTINE_2, TID.MAGUS_CASTLE_SLASH_ROOM_1,
        TID.MAGUS_CASTLE_SLASH_ROOM_2, TID.MAGUS_CASTLE_STATUE_HALL,
        TID.MAGUS_CASTLE_FOUR_KIDS, TID.MAGUS_CASTLE_OZZIE_1,
        TID.MAGUS_CASTLE_OZZIE_2, TID.MAGUS_CASTLE_ENEMY_ELEVATOR,
        # Tyrano Lair
        TID.TYRANO_LAIR_TRAPDOOR, TID.TYRANO_LAIR_MAZE_1,
        TID.TYRANO_LAIR_MAZE_2, TID.TYRANO_LAIR_MAZE_3,
        TID.TYRANO_LAIR_MAZE_4,
        TID.MAGUS_CASTLE_LEFT_HALL, TID.MAGUS_CASTLE_UNSKIPPABLES,
        TID.MAGUS_CASTLE_PIT_E, TID.MAGUS_CASTLE_PIT_NE,
        TID.MAGUS_CASTLE_PIT_NW, TID.MAGUS_CASTLE_PIT_W,
    ]

    ret_dict[td.TreasureLocTier.MID_HIGH] = [
        # Higher Tier for
        TID.DENADORO_MTS_WATERFALL_TOP_1, TID.DENADORO_MTS_WATERFALL_TOP_2,
        # Prismshard quest
        TID.GUARDIA_BASEMENT_1, TID.GUARDIA_BASEMENT_2, TID.GUARDIA_BASEMENT_3,
        TID.GUARDIA_TREASURY_1, TID.GUARDIA_TREASURY_2, TID.GUARDIA_TREASURY_3,
        # Desert
        TID.SUNKEN_DESERT_B1_NW, TID.SUNKEN_DESERT_B1_NE,
        TID.SUNKEN_DESERT_B1_SE, TID.SUNKEN_DESERT_B1_SW,
        TID.SUNKEN_DESERT_B2_NW, TID.SUNKEN_DESERT_B2_N,
        TID.SUNKEN_DESERT_B2_W,  TID.SUNKEN_DESERT_B2_SW,
        TID.SUNKEN_DESERT_B2_SE, TID.SUNKEN_DESERT_B2_E,
        TID.SUNKEN_DESERT_B2_CENTER,
        # Ozzie's Fort
        TID.OZZIES_FORT_GUILLOTINES_1, TID.OZZIES_FORT_GUILLOTINES_2,
        TID.OZZIES_FORT_GUILLOTINES_3, TID.OZZIES_FORT_GUILLOTINES_4,
        TID.OZZIES_FORT_FINAL_1, TID.OZZIES_FORT_FINAL_2,
        # Giant's Claw
        TID.GIANTS_CLAW_CAVES_1, TID.GIANTS_CLAW_CAVES_2,
        TID.GIANTS_CLAW_CAVES_3, TID.GIANTS_CLAW_CAVES_4,
        TID.GIANTS_CLAW_CAVES_5,
        # Free sealed Rooms
        TID.BANGOR_DOME_SEAL_1, TID.BANGOR_DOME_SEAL_2, TID.BANGOR_DOME_SEAL_3,
        TID.TRANN_DOME_SEAL_1, TID.TRANN_DOME_SEAL_2,
        # Death Peak
        TID.DEATH_PEAK_SOUTH_FACE_SPAWN_SAVE, TID.DEATH_PEAK_SOUTH_FACE_SUMMIT,
        TID.DEATH_PEAK_FIELD, TID.DEATH_PEAK_CAVES_LEFT,
        TID.DEATH_PEAK_CAVES_CENTER, TID.DEATH_PEAK_CAVES_RIGHT,
        TID.DEATH_PEAK_KRAKKER_PARADE,
        # Geno Dome
        TID.GENO_DOME_1F_1, TID.GENO_DOME_1F_2, TID.GENO_DOME_1F_3,
        TID.GENO_DOME_1F_4, TID.GENO_DOME_ROOM_1, TID.GENO_DOME_ROOM_2,
        TID.GENO_DOME_PROTO4_1, TID.GENO_DOME_PROTO4_2, TID.GENO_DOME_2F_1,
        TID.GENO_DOME_2F_2, TID.GENO_DOME_2F_3, TID.GENO_DOME_2F_4,
        # Most of Ocean Palace
        TID.OCEAN_PALACE_MAIN_S,
        TID.OCEAN_PALACE_MAIN_N, TID.OCEAN_PALACE_E_ROOM,
        TID.OCEAN_PALACE_W_ROOM, TID.OCEAN_PALACE_SWITCH_NW,
        TID.OCEAN_PALACE_SWITCH_SW, TID.OCEAN_PALACE_SWITCH_NE,
        # Mt. Woe
        TID.MT_WOE_2ND_SCREEN_1, TID.MT_WOE_2ND_SCREEN_2,
        TID.MT_WOE_2ND_SCREEN_3, TID.MT_WOE_2ND_SCREEN_4,
        TID.MT_WOE_2ND_SCREEN_5, TID.MT_WOE_3RD_SCREEN_1,
        TID.MT_WOE_3RD_SCREEN_2, TID.MT_WOE_3RD_SCREEN_3,
        TID.MT_WOE_3RD_SCREEN_4, TID.MT_WOE_3RD_SCREEN_5,
        TID.MT_WOE_1ST_SCREEN, TID.MT_WOE_FINAL_1,
        TID.MT_WOE_FINAL_2,
    ]

    ret_dict[td.TreasureLocTier.HIGH_AWESOME] = [
        TID.ARRIS_DOME_SEAL_1, TID.ARRIS_DOME_SEAL_2,
        TID.ARRIS_DOME_SEAL_3, TID.ARRIS_DOME_SEAL_4,
        TID.REPTITE_LAIR_SECRET_B2_NE_RIGHT, TID.REPTITE_LAIR_SECRET_B1_SW,
        TID.REPTITE_LAIR_SECRET_B1_NE, TID.REPTITE_LAIR_SECRET_B1_SE,
        TID.REPTITE_LAIR_SECRET_B2_SE_RIGHT,
        TID.REPTITE_LAIR_SECRET_B2_NE_OR_SE_LEFT,
        TID.REPTITE_LAIR_SECRET_B2_SW,
        TID.BLACK_OMEN_AUX_COMMAND_MID,
        TID.BLACK_OMEN_AUX_COMMAND_NE, TID.BLACK_OMEN_GRAND_HALL,
        TID.BLACK_OMEN_NU_HALL_NW, TID.BLACK_OMEN_NU_HALL_W,
        TID.BLACK_OMEN_NU_HALL_SW, TID.BLACK_OMEN_NU_HALL_NE,
        TID.BLACK_OMEN_NU_HALL_E, TID.BLACK_OMEN_NU_HALL_SE,
        TID.BLACK_OMEN_ROYAL_PATH, TID.BLACK_OMEN_RUMINATOR_PARADE,
        TID.BLACK_OMEN_EYEBALL_HALL, TID.BLACK_OMEN_TUBSTER_FLY,
        TID.BLACK_OMEN_MARTELLO, TID.BLACK_OMEN_ALIEN_SW,
        TID.BLACK_OMEN_ALIEN_NE, TID.BLACK_OMEN_ALIEN_NW,
        TID.BLACK_OMEN_TERRA_W, TID.BLACK_OMEN_TERRA_NE,
        # Copying standard for these two ocean palace chests
        TID.OCEAN_PALACE_SWITCH_SECRET, TID.OCEAN_PALACE_FINAL,
    ]
    return ret_dict


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
