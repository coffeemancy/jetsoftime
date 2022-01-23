'''
Provides functions to implement Cthulhu Crisis's Ice Age Mode.
'''
from __future__ import annotations

import functools

import ctenums
import ctevent
import ctrom
import ctstrings
import eventfunction
import eventcommand
import freespace

import randoconfig as cfg
import randosettings as rset


def get_key_chars_from_config(config: cfg.RandoConfig) -> set[ctenums.CharID]:

    RecruitID = cfg.RecruitID
    key_chars = set(
        [config.char_assign_dict[RecruitID.DACTYL_NEST].held_char,
         ctenums.CharID.AYLA]
    )

    return key_chars


def write_config(settings: rset.Settings,
                 config: cfg.RandoConfig):
    '''
    Writes Ice Age specific changes to the config.  Apply AFTER ro scaling.

    For now this only means writing the buffed Giga Gaia out.  We'll also
    verify that GG is on Woe where he ought to be.
    '''

    if rset.GameFlags.ICE_AGE not in settings.gameflags:
        return

    BossID = ctenums.BossID
    LocID = ctenums.LocID
    boss_dict = config.boss_assign_dict

    if boss_dict[LocID.MT_WOE_SUMMIT] != BossID.GIGA_GAIA:
        print('Error: Ice Age and GG not on Woe.')
        exit()

    EnemyID = ctenums.EnemyID

    gg_head = config.enemy_dict[EnemyID.GIGA_GAIA_HEAD]
    gg_left_arm = config.enemy_dict[EnemyID.GIGA_GAIA_LEFT]
    gg_right_arm = config.enemy_dict[EnemyID.GIGA_GAIA_RIGHT]

    gg_left_arm.magic = 30
    gg_left_arm.hp = 4000
    gg_left_arm.defense = 185
    gg_left_arm.speed = 14

    gg_right_arm.magic = 20
    gg_right_arm.hp = 5000
    gg_right_arm.mdef = 90
    gg_right_arm.speed = 13

    gg_head.hp = 15500


def set_ending_after_woe(ct_rom: ctrom.CTRom):
    script = ct_rom.script_manager.get_script(
        ctenums.LocID.MT_WOE_SUMMIT
    )

    # find battle (with GG)
    pos, _ = script.find_command([0xD9])

    # Wait for silence
    pos, cmd = script.find_command([0xED])
    pos += len(cmd)

    EC = eventcommand.EventCommand
    EF = eventfunction.EventFunction

    # There are so many different, seemingly identical warp commands.
    # I'm copying the one from Tesseract exactly to avoid weirdness
    warp_ending_cmd = EC.change_location(
        ctenums.LocID.ENDING_SELECTOR, 0, 0, 1, 0, True
    )
    warp_ending_cmd.command = 0xDF

    func = EF()
    (
        func
        .add(EC.set_storyline_counter(0x75))
        .add(EC.darken(0xC))
        .add(EC.fade_screen())
        .add(warp_ending_cmd)
    )

    script.insert_commands(func.get_bytearray(), pos)

def remove_darkages_from_eot(ct_rom: ctrom.CTRom):
    # Rather than lock Mt. Woe directly.  Revert to old logic by changing
    # the behavior when entering Mystic Mts and proto portals.

    EC = eventcommand.EventCommand
    EF = eventfunction.EventFunction
    OP = eventcommand.Operation

    # Writing to these spaces tell the time gauge what maps to travel to
    # and also inform EoT of which pillars to display
    darkages_cmd = EC.assign_val_to_mem(0x1F4, 0x7E2889, 2)

    for loc_id in [ctenums.LocID.PROTO_DOME_PORTAL,
                   ctenums.LocID.MYSTIC_MTN_PORTAL]:
        script = ct_rom.script_manager.get_script(loc_id)
        pos = script.find_exact_command(darkages_cmd)

        if pos is not None:
            # possibly we have non-beta logic and it isn't making this
            # change
            script.delete_commands(pos, 1)

    # We still have to disable the pillars
    da_pillar = EC.copy_tiles(0xE, 0x7, 0xE, 0x8,
                              0xF, 0xA,
                              True, True, False, True, False, False,
                              True)

    script = ct_rom.script_manager.get_script(
        ctenums.LocID.END_OF_TIME
    )

    # We take for granted that the DA loc_id is stored to 0x7F022C.
    # If needed, we can compute that.

    # This only puts the pillar there if 12k BC is on the time gauge
    func = EF().add_if(
        EC.if_mem_op_value(0x7F022C, OP.NOT_EQUALS, 0x00, 2, 0),
        EF().add(da_pillar)
    )

    pos = script.find_exact_command(da_pillar)
    script.insert_commands(func.get_bytearray(), pos)
    pos += len(func)
    script.delete_commands(pos, 1)

    # Pillars work by constantly checking the player's position/button press
    # instead of using activate.  Put a loop at the front that catches whe
    # 0x7F022C is 0

    func = EF().add_while(
        EC.if_mem_op_value(0x7F022C, OP.EQUALS, 0x00, 2, 0),
        EF()
    )

    # DA pillar in obj 0x17
    pos = script.find_exact_command(EC.return_cmd(),
                                    script.get_function_start(0x17, 0),
                                    script.get_function_end(0x17, 0))

    # get past the initial return
    pos += 1
    script.insert_commands(func.get_bytearray(), pos)


def lock_magic_cave(ct_rom: ctrom.CTRom):
    # Prevent Frog from opening the mountain so that we can't access
    # the Dark Ages through the castle.

    script = ct_rom.script_manager.get_script(
        ctenums.LocID.MAGIC_CAVE_EXTERIOR
    )

    EC = eventcommand.EventCommand
    frog_active = EC.check_active_pc(int(ctenums.CharID.FROG), 0).command
    pos, if_frog_active_cmd = script.find_command([frog_active])

    new_string = ctstrings.CTString.from_str(
        '{frog}: We must make haste to the{line break}'
        'Tyrano Lair!{null}'
    )

    new_string_id = script.add_string(new_string)

    pos += len(if_frog_active_cmd)
    script.insert_commands(
        EC.text_box(new_string_id).to_bytearray(),
        pos
    )

    after_text_pos = pos + len(EC.text_box(0))

    # the jump has changed after our insertion, so refetch command
    pos, if_frog_active_cmd = script.find_command([frog_active])

    jump_length = if_frog_active_cmd.args[-1]
    jump_target = pos + len(if_frog_active_cmd) + jump_length - 1

    # This is a little crude.  We could keep the check for masamune forged.
    script.delete_commands_range(after_text_pos, jump_target)


def lock_mount_woe(ct_rom: ctrom.CTRom,
                   char_set: set[ctenums.CharID]):
    # We're going to lock woe by locking it behind tyrano lair
    pass


def lock_tyrano_lair(ct_rom: ctrom.CTRom,
                     char_set: set[ctenums.CharID]):
    # The strategy here is to piggyback on the dreamstone switch.
    EF = eventfunction.EventFunction
    EC = eventcommand.EventCommand

    script = ct_rom.script_manager.get_script(
        ctenums.LocID.TYRANO_LAIR_ANTECHAMBERS
    )

    start = script.get_function_start(0x09, 0x01)
    end = script.get_function_end(0x09, 0x01)

    orig_func = EF.from_bytearray(script.data[start:end])
    orig_func.set_label('return', len(orig_func)-1)

    new_string = ctstrings.CTString.from_str(
        'We need {ayla} and whoever is at the {linebreak+0}'
        'Dactyl Nest Summit before proceeding!{null}'
    )

    new_string_id = script.add_string(new_string)

    func = EF()
    for char in list(char_set):
        func.add_if_else(
            EC.check_active_pc(int(char), 0),
            EF(),
            (
                EF()
                .add(EC.text_box(new_string_id))
                .jump_to_label(EC.jump_forward(0), 'return')
            )
        )

    func.append(orig_func)
    script.set_function(0x09, 0x01, func)


def set_ice_age_dungon_locks(ct_rom: ctrom.CTRom,
                             config: cfg.RandoConfig):
    key_chars = get_key_chars_from_config(config)
    lock_mount_woe(ct_rom, key_chars)
    lock_tyrano_lair(ct_rom, key_chars)
    lock_magic_cave(ct_rom)
    remove_darkages_from_eot(ct_rom)


def set_ice_age_recruit_locks(ct_rom: ctrom.CTRom,
                              config: cfg.RandoConfig):
    '''
    Forces Ayla and Dactyl recruit into the party after recruitment.
    '''

    key_chars = get_key_chars_from_config(config)

    RecruitID = cfg.RecruitID
    recruit_ids_to_lock = [
        RecruitID.CATHEDRAL,
        RecruitID.CASTLE,
        RecruitID.FROGS_BURROW,
        RecruitID.DACTYL_NEST,
        RecruitID.PROTO_DOME
    ]

    for recruit_id in recruit_ids_to_lock:
        recruit = config.char_assign_dict[recruit_id]
        loc_id = recruit.loc_id
        recruit_obj = recruit.recruit_obj_id
        script = ct_rom.script_manager.get_script(loc_id)

        insert_char_lock(script, recruit_obj, key_chars)


def insert_char_lock(script: ctevent.Event,
                     obj_id: int,
                     char_set: set[ctenums.CharID]) -> eventfunction:
    '''
    Generate some script to enforce a character lock after recruitment.
    '''

    # The general idea is to do the following
    #   1) Unset any character locks
    #   2) Allow the party shuffle (Y menu)
    #   3) Kick the user back to party shuffle if required characters
    #      are missing
    #   4) Set the character locks
    func = eventfunction.EventFunction()

    # Turn chars into bytes (0x80 >> char_id) and logical OR them up
    chars = list(char_set)
    char_lock_bytes = functools.reduce(
        lambda a, b: a | b,
        [0x80 >> int(x) for x in chars]
    )

    EC = eventcommand.EventCommand
    EF = eventfunction.EventFunction
    # charlock bytes are in 0x7F01DF
    func.add(EC.assign_val_to_mem(0x0, 0x7F01DF, 1))
    func.set_label('replace')
    func.add(EC.replace_characters())

    for char in chars:
        char_str = str(char).lower()
        error_string = f"Must include {{{char_str}}}!{{null}}"
        script.strings.append(ctstrings.CTString.from_str(error_string))
        error_string_index = len(script.strings) - 1

        func.add_if(
            EC.check_recruited_pc(int(char), 0),
            (
                EF.if_else(
                    EC.check_active_pc(int(char), 0),
                    EF(),
                    (
                        EF()
                        .add(EC.text_box(error_string_index))
                        .jump_to_label(EC.jump_back(0), 'replace')
                    )
                )
            )
        )
    func.add(EC.assign_val_to_mem(char_lock_bytes, 0x7F01DF, 1))

    start = script.get_object_start(obj_id)
    end = script.get_object_end(obj_id)

    # Find the Add to reserve command
    pos, cmd = script.find_command([0xD0], start, end)

    # There should be a jump immediately before.  This jump jumps over the
    # add to reserve command when there are only 2 PCs
    jump_cmd_pos = pos - 2

    # Make sure it's really the forward jump
    if script.data[jump_cmd_pos] != 0x10:
        # This happens in castle because castle *always* has 3+ PCs.
        # print('Warning: No jump prior to add reserve.  Castle?')
        jump_pos = None
    else:
        # store the location of the jump for later.
        jump_pos = jump_cmd_pos + 1

    pos += len(cmd)

    if script.data[pos] != EC.replace_characters().command:
        print('Failed to find replace characters')
        quit()

    script.modified_strings = True
    script.delete_commands(pos)
    script.insert_commands(func.get_bytearray(), pos)

    # Now fix that jump to jump over everything we just added.
    # If it needs fixing anyway.
    if jump_pos is not None:
        after_pos = pos + len(func)
        script.data[jump_pos] = after_pos - jump_pos

    # for string in script.strings:
    #     print(ctstrings.CTString.ct_bytes_to_ascii(string))


def main():
    CharID = ctenums.CharID
    char_set = set((CharID.CRONO, CharID.MAGUS, CharID.LUCCA))

    ct_rom = ctrom.CTRom.from_file('./roms/jets_test.sfc', True)

    script_man = ct_rom.script_manager
    script = script_man.get_script(0)
    func = script.get_function(0,0)

    # insert_char_lock(script, 0x19, char_set)
    # lock_tyrano_lair(ct_rom, char_set)
    # lock_magic_cave(ct_rom)
    remove_darkages_from_eot(ct_rom)

    space_manager = ct_rom.rom_data.space_manager
    mark_free = freespace.FSWriteType.MARK_FREE
    space_manager.mark_block((0x4F8000, 0x5F0000), mark_free)
    ct_rom.write_all_scripts_to_rom()
    input('outrom')

    with open('./roms/jets_test_out.sfc', 'wb') as outfile:
        outfile.write(ct_rom.rom_data.getvalue())


if __name__ == '__main__':
    main()
