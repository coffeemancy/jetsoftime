import eventcommand

import ctenums
import ctevent
import ctrom

import randoconfig as cfg


# I think vanilla coords are 0x0270, 0x258
def ground_epoch(ct_rom: ctrom.CTRom):
    '''Disable Epoch flight on game start.  Places it in 1000AD'''
    script = ct_rom.script_manager.get_script(
        ctenums.LocID.TELEPOD_EXHIBIT
    )

    EC = ctevent.EC
    EF = ctevent.EF

    epoch_status_byte = 0x7E0294
    epoch_loc_byte = 0x7E029F

    # Bytes that indicate what kind of movement to do on the ow.  Should be
    # set to 0 for normal walking.  Originally were 2 for flying.
    ow_move_type_byte1 = 0x7E027E
    ow_move_type_byte2 = 0x7E028F  # Pretty sure this is a typo.  0x7E027F

    ow_move_type_cmd1 = EC.assign_val_to_mem(0x02, ow_move_type_byte1, 1)
    new_move_type_cmd1 = EC.assign_val_to_mem(0x00, ow_move_type_byte1, 1)

    ow_move_type_cmd2 = EC.assign_val_to_mem(0x02, ow_move_type_byte2, 1)
    new_move_type_cmd2 = EC.assign_val_to_mem(0x00, ow_move_type_byte2, 1)

    pos = script.find_exact_command(ow_move_type_cmd1)
    script.data[pos: pos+len(ow_move_type_cmd1)] = \
        new_move_type_cmd1.to_bytearray()

    pos = script.find_exact_command(ow_move_type_cmd2)
    script.data[pos: pos+len(ow_move_type_cmd2)] = \
        new_move_type_cmd2.to_bytearray()

    pos = script.find_exact_command(
        EC.set_reset_bit(0x7F00BA, 0x80, True)
    )
    script.delete_commands(pos, 1)

    func = EF()
    (
        func
        .add(EC.set_reset_bit(0x7F00EC, 0x04, True))  # Epoch out of hangar
        .add(EC.set_reset_bit(0x7F00EE, 0x80, True))  # Nu in Hangar on
        .add(EC.set_reset_bit(0x7F00EF, 0x10, True))  # Seen Epoch scene
        .add(EC.set_reset_bit(0x7F01F0, 0x01, True))  # Vortex Pt
        .add(EC.set_reset_bit(0x7F01A3, 0x02, True))  # H. Cave 1st Fight Done
    )

    script.insert_commands(func.get_bytearray(), pos)

    epoch_status_cmd = EC.assign_val_to_mem(0xF2, epoch_status_byte, 1)
    new_status_cmd = EC.assign_val_to_mem(0x80, epoch_status_byte, 1)
    status_cmd_len = len(epoch_status_cmd)

    pos = script.find_exact_command(epoch_status_cmd)
    script.data[pos:pos+status_cmd_len] = new_status_cmd.to_bytearray()

    epoch_map_cmd = EC.assign_val_to_mem(0x01F1, epoch_loc_byte, 2)
    new_map_cmd = EC.assign_val_to_mem(0x01F0, epoch_loc_byte, 2)
    map_cmd_len = len(epoch_map_cmd)

    pos = script.find_exact_command(epoch_map_cmd)
    script.data[pos:pos+map_cmd_len] = new_map_cmd.to_bytearray()

    new_loc_cmd = EC.change_location(
        int(ctenums.LocID.LEENE_SQUARE),
        0x18, 0x1
    )

    func = (
        EF()
        .add(new_loc_cmd)
    )

    pos = script.find_exact_command(EC.fade_screen(),
                                    script.get_function_start(0xE, 4))
    script.insert_commands(EC.darken(1).to_bytearray(), pos)

    pos, cmd = script.find_command([0xE0], pos)
    script.delete_commands(pos, 1)
    script.insert_commands(new_loc_cmd.to_bytearray(), pos)

    # Remove Epoch sfx
    st = script.get_function_start(0x0E, 4)

    pos, _ = script.find_command([0xEA], st)
    script.delete_commands(pos, 1)
    pos, cmd = script.find_command([0xEC], pos)

    script.delete_commands(pos, 5)


def update_keepers_dome(ct_rom: ctrom.CTRom):
    '''
    Set the Keeper's dome corridor and hangar script to allow for access with
    both flying and grounded epochs.
    '''

    # Keeper's Dome Corridor
    # 1) Always leave the door open.  Otherwise it would potentially softlock
    #    if you warp to the future and leave the hangar without the pendant.
    # 2) Use Vanilla logic to block the door when the Epoch isn't in the
    #    hangar.

    script = ctevent.Event.from_flux('./flux/EF_0F2_Keepers_Dome.Flux')
    ct_rom.script_manager.set_script(
        script, ctenums.LocID.KEEPERS_DOME_CORRIDOR
    )

    # Remember to set the in hangar flag correctly when flight is obtained.

    # Another issue is that leaving in the epoch from Keeper's Dome will
    # set three characters in the epoch.  This will lock if only two are
    # present.

    script = ctevent.Event.from_flux('./flux/EF_0F3_Keepers_Dome_Hangar.Flux')
    ct_rom.script_manager.set_script(
        script, ctenums.LocID.KEEPERS_DOME_HANGAR
    )


def restore_dactyls(ct_rom: ctrom.CTRom):
    '''
    Put the party on Dactyls after Dactyl Recruit
    '''

    script = ct_rom.script_manager.get_script(
        ctenums.LocID.DACTYL_NEST_SUMMIT
    )

    pos, _ = script.find_command([0xE0])
    script.delete_commands(pos, 1)

    EF = ctevent.EF
    EC = ctevent.EC

    func = EF()
    (
        func
        .add(EC.assign_val_to_mem(3, 0x7E027E, 1))
        .add(EC.assign_val_to_mem(3, 0x7E028F, 1))
        .add(EC.assign_val_to_mem(0x01F8, 0x7E029A, 2))
        .add(EC.assign_val_to_mem(0x0048, 0x7E029C, 2))
        .add(EC.assign_val_to_mem(0xC3, 0x7E029E, 1))
        .add(EC.change_location(0x01F3, 0x3F, 0x09, 0, 1, False))
    )

    # Weird note.  The changelocation coordinates are essential.  If they are
    # not changed back to vanilla, the overworld never draws the dactyls and
    # softlocks as a result.

    script.insert_commands(func.get_bytearray(), pos)


def undo_epoch_relocation(ct_rom: ctrom.CTRom):
    '''
    Keep the Epoch from moving around before flight.
    '''

    # Possible Relocations
    #   After trial (Guardia Forest Dead End)
    #   After Heckran's Cave (Duplicated to 0xC0, Heckran Passageways New)
    #   After Desert turn-in (Fiona's Villa)
    #   After Zenan Bridge (Guardia Throneroom)
    #   After Magic Cave cutscene (Magic Cave Exterior)
    #   After defeating Magus (Magus Castle Inner Sanctum)
    #   After defeating Yakra (Manoria Command)
    #   Taking off from Keeper's Dome Hangar (don't change)
    #   After Lavos crashes (0x105 Prehistoric Canyon)
    #   Leaving Mystic Mts (0x112)
    #   Going through Lair Ruins portal (0x133)
    #   Maybe after losing to lavos?  Might have to just give flight.

    EC = eventcommand.EventCommand
    OP = eventcommand.Operation

    jump_len = 13  # 2 assignments + 1
    jmp = EC.if_mem_op_value(0x7F00BA, OP.BITWISE_AND_NONZERO,
                             0x80, 1, jump_len)

    LocID = ctenums.LocID
    locations = (
        LocID.GUARDIA_FOREST_DEAD_END, LocID.HECKRAN_CAVE_NEW,
        LocID.FIONAS_VILLA, LocID.GUARDIA_THRONEROOM_600,
        LocID.MAGIC_CAVE_EXTERIOR, LocID.MAGUS_CASTLE_INNER_SANCTUM,
        LocID.MANORIA_COMMAND, LocID.PREHISTORIC_CANYON,
        LocID.MYSTIC_MTN_GULCH, LocID.LAIR_RUINS_PORTAL
    )

    for loc in locations:
        script = ct_rom.script_manager.get_script(loc)

        pos = script.get_function_start(0, 0)
        found = False

        # You can get in an awkward spot when you do Cathedral.  The
        # Epoch is moved to 600.  The Epoch becomes unavailable until you
        # do bridge.
        jump_len = 13  # 1 + 2 assigns
        if loc in (LocID.MANORIA_COMMAND, LocID.GUARDIA_FOREST_DEAD_END):
            jump_len += 6  # Also jump over the map switch assign.

        jmp = EC.if_mem_op_value(0x7F00BA, OP.BITWISE_AND_NONZERO,
                                 0x80, 1, jump_len)

        while True:
            pos, cmd = script.find_command([0x4B], pos)
            if pos is None:
                break
            elif cmd.args[0] == 0x7E0290:
                found = True
                script.insert_commands(jmp.to_bytearray(), pos)

            pos += len(cmd)

        if not found:
            print(f'Error: {loc}')


def update_johnny_race(ct_rom):
    '''
    Lock Lab32 Access behind the Bike Key
    '''
    pass


def add_dalton_to_snail_stop(ct_rom: ctrom.CTRom):
    '''
    Add Dalton to fix the Epoch in the Snail Stop.
    '''

    script = ctevent.Event.from_flux('./flux/EF_035_Snail_Stop.Flux')    
    ct_rom.script_manager.set_script(script, ctenums.LocID.SNAIL_STOP)


def update_config(config: cfg.RandoConfig):
    '''
    Add JetsOfTime to the item list.
    '''

    jot = config.itemdb[ctenums.ItemID.JETSOFTIME]
    jot.set_name_from_str(' JetsOfTime')
