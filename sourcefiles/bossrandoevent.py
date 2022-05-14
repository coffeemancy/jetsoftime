from __future__ import annotations

from byteops import to_little_endian
import dataclasses
import copy
from collections.abc import Callable
import random

# from ctdecompress import compress, decompress, get_compressed_length
from bossdata import BossScheme, get_default_boss_assignment
from ctenums import LocID, BossID, EnemyID, CharID, Element, StatusEffect,\
    RecruitID
from ctevent import Event, free_event, get_loc_event_ptr
from ctrom import CTRom
import enemyrewards
from eventcommand import EventCommand as EC, get_command, FuncSync
from eventfunction import EventFunction as EF
# from eventscript import get_location_script, get_loc_event_ptr
from freespace import FreeSpace as FS
from mapmangler import LocExits, duplicate_heckran_map, duplicate_map, \
    duplicate_location_data

import randosettings as rset
import randoconfig as cfg


def set_manoria_boss(ctrom: CTRom, boss: BossScheme):
    # 0xC6 is Yakra's map - Manoria Command
    loc_id = 0xC6

    boss_obj = 0xA
    first_x, first_y = 0x80, 0xA0

    set_generic_one_spot_boss(ctrom, boss, loc_id, boss_obj,
                              lambda s: s.get_function_end(0xA, 3) - 1,
                              first_x, first_y)


def set_denadoro_boss(ctrom: CTRom, boss: BossScheme):
    # 0x97 is M&M's map - Cave of the Masamune
    loc_id = 0x97
    boss_obj = 0x14

    first_x, first_y = 0x80, 0xE0

    set_generic_one_spot_boss(ctrom, boss, loc_id, boss_obj,
                              lambda s: s.get_function_end(0x14, 4) - 1,
                              first_x, first_y)


def set_reptite_lair_boss(ctrom: CTRom, boss: BossScheme):
    # 0x121 is Nizbel's map - Reptite Lair Azala's Room
    loc_id = 0x121
    boss_obj = 0x9

    first_x, first_y = 0x370, 0xC0

    set_generic_one_spot_boss(ctrom, boss, loc_id, boss_obj,
                              lambda s: s.get_function_end(0x9, 4) - 1,
                              first_x, first_y)


def set_magus_castle_flea_spot_boss(ctrom: CTRom, boss: BossScheme):
    # 0xAD is Flea's map - Castle Magus Throne of Magic
    loc_id = 0xAD

    boss_obj = 0xC

    first_x, first_y = 0x70, 0x150

    def show_pos_fn(script: Event) -> int:
        # The location to insert is a bit before the second battle in this
        # function.  The easiest marker is a 'Mem.7F020C = 01' command.
        # In bytes it is '7506'
        pos = script.find_exact_command(EC.generic_one_arg(0x75, 0x06),
                                        script.get_function_start(0xC, 0))

        if pos is None:
            print("Error finding show pos (flea spot)")
            exit()

        return pos
    # end show_pos_fn

    set_generic_one_spot_boss(ctrom, boss, loc_id, boss_obj, show_pos_fn,
                              first_x, first_y)
# End set_magus_castle_flea_spot_boss


def set_magus_castle_slash_spot_boss(ctrom: CTRom, boss: BossScheme):
    # 0xA9 is Slash's map - Castle Magus Throne of Strength
    loc_id = 0xA9
    script = ctrom.script_manager.get_script(loc_id)

    if boss.ids[0] in [EnemyID.ELDER_SPAWN_SHELL, EnemyID.LAVOS_SPAWN_SHELL]:
        # Some sprite issue with overlapping slots?
        # If the shell is the static part, it will be invisible until it is
        # interacted with.
        boss.ids[0], boss.ids[1] = boss.ids[1], boss.ids[0]
        boss.slots[0], boss.slots[1] = boss.slots[1], boss.slots[0]
        boss.disps[0] = (-boss.disps[0][0], -boss.disps[0][1])
        boss.disps[1] = (-boss.disps[1][0], -boss.disps[1][1])

    # Slash's spot is ugly because there's a second Slash object that's used
    # for one of the endings (I think?).  You really have to set both of them
    # to the boss you want, otherwise you're highly likely to hit graphics
    # limits.
    set_object_boss(script, 0xC, boss.ids[0], boss.slots[0])

    # The real, used Slash is in object 0xB.
    boss_obj = 0xB

    first_x, first_y = 0x80, 0x240

    def show_pos_fn(script: Event) -> int:
        pos = script.find_exact_command(EC.generic_one_arg(0xE8, 0x8D),
                                        script.get_function_start(0xB, 1))

        if pos is None:
            print("Failed to find show pos (slash spot)")
            exit()

        return pos

    set_generic_one_spot_boss_script(script, boss, boss_obj,
                                     show_pos_fn, first_x, first_y)
# End set_magus_castle_slash_spot_boss


def set_giants_claw_boss(ctrom: CTRom, boss: BossScheme):

    if EnemyID.RUST_TYRANO in boss.ids:
        return

    loc_id = LocID.GIANTS_CLAW_TYRANO
    script = ctrom.script_manager.get_script(loc_id)

    # Copying the existing command from when Tyrano dies.
    copy_tiles_cmd = EC.copy_tiles(0, 0, 7, 9, 4, 0x22,
                                   copy_l1=True,
                                   copy_l2=True,
                                   copy_props=True,
                                   unk_0x10=True,
                                   unk_0x20=True)

    # Yes, the tiles will be copied again when the Tyrano dies.  If that's
    # a problem we'll remove the other calls.

    pos = script.get_object_start(0)
    script.insert_commands(copy_tiles_cmd.to_bytearray(), pos)

    # You need to do the copy in obj0, func1 (activate) too.  This is the
    # function that gets called after returning from a menu.

    # Change to a wait for vblank version
    copy_tiles_cmd.command = 0xE4
    func = EF()
    func.add(copy_tiles_cmd)
    script.set_function(0, 1, func)

    # First part is in object 0x9, function 0 (init)
    boss_obj = 0x9
    first_x, first_y = 0x80, 0x27F

    # Objects can start out shown, no real need for show_pos_fn
    set_generic_one_spot_boss_script(script, boss, boss_obj,
                                     lambda s: s.get_function_start(0, 0) + 1,
                                     first_x, first_y, True)
# end set giant's claw boss


def set_tyrano_lair_midboss(ctrom: CTRom, boss: BossScheme):
    # 0x130 is the Nizbel II's map - Tyrano Lair Nizbel's Room
    loc_id = 0x130
    boss_obj = 0x8
    first_x = 0x70
    first_y = 0xD0

    set_generic_one_spot_boss(ctrom, boss, loc_id, boss_obj,
                              lambda s: s.get_function_end(8, 3) - 1,
                              first_x, first_y)
# end set_tyrano_lair_midboss


def set_zeal_palace_boss(ctrom: CTRom, boss: BossScheme):
    # 0x14E is the Golem's map - Zeal Palace's Throneroom (Night)
    # Note this is different from vanilla, where it's 0x14C
    loc_id = 0x14E
    script = ctrom.script_manager.get_script(loc_id)

    # So much easier to just manually set the coordinates than parse
    # the script for them.  This is after the golem comes down.
    first_x = 0x170
    first_y = 0x90

    # First, let's delete some objects to avoid sprite limits.
    #   - Object F: Schala
    #   - Object E: Queen Zeal
    #   - Object 10: Magus Prophet

    # reverse order to not screw things up
    # removing seems to mess up the color of the beam above the portal.
    # I think it's the colormath commands needing palettes loaded?
    # For now, see if just leaving the junk in is ok.
    # del_objs = [0x10, 0xF, 0xE]

    # for obj in del_objs:
    #     script.remove_object(obj)

    # After deletion, the boss object is 0xA (unmoved)
    boss_obj = 0xA

    def show_pos_fn(script: Event) -> int:
        # Right after the golem comes down to its final position.  The marker
        # is a play anim 5 command 'AA 05'
        pos = script.find_exact_command(EC.generic_one_arg(0xAA, 0x5),
                                        script.get_function_start(0xA, 3))

        if pos is None:
            print('Error finding show pos (zeal palace)')
            exit()

        return pos

    set_generic_one_spot_boss_script(script, boss, boss_obj,
                                     show_pos_fn,
                                     first_x, first_y)


# Two spot locations follow the same general procedure:
#   - For a 1-spot boss, overwrite the legs object (0xB3 for Zombor) with the
#     new boss id.  Then delete the head object and all references to it.
#   - For a 2-spot boss, overwrite the legs and head object with the new
#     boss ids.  Add in coordinate shifts (will vary with location).
#     Possibly it's easier to delete all but one object and then
#   - For a 3+ spot boss, do the 2-spot procedure and then add new objects
#     that pop into existence right
def set_zenan_bridge_boss(ctrom: CTRom, boss: BossScheme):
    # 0x87 is Zombor's map - Zenan Bridge (Middle Ages)
    # Except to avoid sprite bugs we changed it
    # loc_id = 0x87
    loc_id = LocID.ZENAN_BRIDGE_BOSS
    script = ctrom.script_manager.get_script(loc_id)

    num_parts = len(boss.ids)

    if num_parts == 1:
        # Use object 0xB (Zombor's Head, 0xB4) for the boss because it has
        # sound effects in it.  But we'll change the coordinates so that the
        # boss will be on the ground

        # Zombor has an attract battle scene.  So we skip over the conditionals
        pos = script.get_function_start(0xB, 0)
        found_boss = False
        found_coord = False

        first_x, first_y = 0xE0, 0x80
        first_id, first_slot = boss.ids[0], boss.slots[0]

        while pos < script.get_function_end(0xB, 0):
            cmd = get_command(script.data, pos)

            # print(cmd)
            if cmd.command in EC.fwd_jump_commands:
                pos += (cmd.args[-1] - 1)
            elif cmd.command == 0x83:
                found_boss = True
                cmd.args[0] = first_id
                cmd.args[1] = first_slot
                script.data[pos:pos+len(cmd)] = cmd.to_bytearray()
            elif cmd.command == 0x8B:
                found_coord = True
                # This is only safe because we know it will give the tile
                # based command to perfectly overwrite the existing tile based
                # command.
                cmd = EC.set_object_coordinates(first_x, first_y)
                script.data[pos:pos+len(cmd)] = cmd.to_bytearray()

            pos += len(cmd)

        if not found_boss or not found_coord:
            print(f"Error: found boss({found_boss}), " +
                  f"found coord({found_coord})")
            exit()

        # Delete the other Zombor object (0xC) to save memory.  It might be
        # OK to leave it in, set it to the one-spot boss, and delete all
        # references as we do below.
        script.remove_object(0xC)

    # end 1 part

    if num_parts > 1:

        first_x, first_y = 0xE0, 0x60

        if (
                EnemyID.GUARDIAN_BIT in boss.ids or
                EnemyID.MOTHERBRAIN in boss.ids
        ):
            boss.reorder_horiz(left=False)

        # object to overwrite with new boss ids and coords
        reused_objs = [0xB, 0xC]

        for i in [0, 1]:
            new_x = first_x + boss.disps[i][0]
            new_y = first_y + boss.disps[i][1]

            # print(f"({new_x:04X}, {new_y:04X})")
            # input()
            new_id = boss.ids[i]
            new_slot = boss.slots[i]

            set_object_boss(script, reused_objs[i], new_id, new_slot)
            set_object_coordinates(script, reused_objs[i], new_x, new_y)

        show_cmds = bytearray()
        for i in range(2, len(boss.ids)):
            new_obj = append_boss_object(script, boss, i,
                                         first_x, first_y, False)
            show = EC.set_object_drawing_status(new_obj, True)
            show_cmds.extend(show.to_bytearray())

        # Suitable time for them to appear is right after the first two parts'
        # entrance.  The very end of obj C, activate (1), before the return
        ins_pos = script.get_function_end(0xC, 1) - 1
        script.insert_commands(show_cmds, ins_pos)
    # end multi-part


def set_death_peak_boss(ctrom: CTRom, boss: BossScheme):
    # 0x1EF is the Lavos Spawn's map - Death Peak Guardian Spawn
    loc_id = 0x1EF
    script = ctrom.script_manager.get_script(loc_id)

    # The shell is important since it needs to stick around after battle.
    # It is in object 9, and the head is in object 0xA
    boss_objs = [0x9, 0xA]

    num_used = min(len(boss.ids), 2)

    first_x, first_y = 0x70, 0xC0

    for i in range(num_used):
        boss_id = boss.ids[i]
        boss_slot = boss.slots[i]

        new_x = first_x + boss.disps[i][0]
        new_y = first_y + boss.disps[i][1]
        set_object_boss(script, boss_objs[i], boss_id, boss_slot)
        set_object_coordinates(script, boss_objs[i], new_x, new_y)

    # Remove unused boss objects from the original script.
    # Will do nothing unless there are fewer boss ids provided than there
    # are original boss objects
    for i in range(len(boss.ids), len(boss_objs)):
        script.remove_object(boss_objs[i])

    # For every object exceeding the count in this map, make a new object.
    # For this particular map, we're going to copy the object except for
    # the enemy load/coords
    calls = bytearray()

    for i in range(len(boss_objs), len(boss.ids)):
        obj_id = script.append_copy_object(0xA)

        new_x = first_x + boss.disps[i][0]
        new_y = first_y + boss.disps[i][1]

        set_object_boss(script, obj_id, boss.ids[i], boss.slots[i])
        set_object_coordinates(script, obj_id, new_x, new_y)

        call = EC.call_obj_function(obj_id, 3, 3, FuncSync.CONT)
        calls.extend(call.to_bytearray())

    # Insertion point is right before the first Move Party command (0xD9)
    pos, cmd = script.find_command([0xD9],
                                   script.get_function_start(8, 1),
                                   script.get_function_end(8, 1))

    if pos is None:
        print('Error finding insertion point.')
        exit()

    script.insert_commands(calls, pos)


def set_giga_mutant_spot_boss(ctrom: CTRom, boss: BossScheme):
    # 0x143 is the Giga Mutant's map - Black Omen 63F Divine Guardian
    loc_id = 0x143
    script = ctrom.script_manager.get_script(loc_id)

    boss_objs = [0xE, 0xF]

    num_used = min(len(boss.ids), 2)
    first_x, first_y = 0x278, 0x1A0

    # mutant coords are weird.  The coordinates are the bottom of the mutant's
    # bottom part.  We need to shift up so non-mutants aren't on the party.
    if boss.ids[0] not in [EnemyID.GIGA_MUTANT_HEAD,
                           EnemyID.GIGA_MUTANT_BOTTOM,
                           EnemyID.TERRA_MUTANT_HEAD,
                           EnemyID.TERRA_MUTANT_BOTTOM,
                           EnemyID.MEGA_MUTANT_HEAD,
                           EnemyID.MEGA_MUTANT_BOTTOM]:
        first_y -= 0x20

    # overwrite as many boss objects as possible
    for i in range(num_used):
        boss_id = boss.ids[i]
        boss_slot = boss.slots[i]

        new_x = first_x + boss.disps[i][0]
        new_y = first_y + boss.disps[i][1]

        set_object_boss(script, boss_objs[i], boss_id, boss_slot)
        set_object_coordinates(script, boss_objs[i], new_x, new_y)

    # Remove unused boss objects.
    for i in range(len(boss.ids), len(boss_objs)):
        script.remove_object(boss_objs[i])

    # Add more boss objects if needed
    calls = bytearray()
    for i in range(len(boss_objs), len(boss.ids)):
        obj_id = script.append_copy_object(boss_objs[1])

        new_x = first_x + boss.disps[i][0]
        new_y = first_y + boss.disps[i][1]

        set_object_boss(script, obj_id, boss.ids[i], boss.slots[i])
        set_object_coordinates(script, obj_id, new_x, new_y)

        # mimic call of other objects
        call = EC.call_obj_function(obj_id, 3, 3, FuncSync.CONT)
        calls.extend(call.to_bytearray())

    # Insertion point is right after call_obj_function(0xE, touch, 3, cont)
    ins_cmd = EC.call_obj_function(0xE, 2, 3, FuncSync.CONT)
    # print(f"{ins_cmd.command:02X}" + str(ins_cmd))

    pos = script.find_exact_command(ins_cmd,
                                    script.get_function_start(0xA, 1),
                                    script.get_function_end(0xA, 1))
    if pos is None:
        print("Error finding insertion position (giga mutant)")
        exit()
    else:
        # shift to after the found command
        pos += len(ins_cmd)

    script.insert_commands(calls, pos)

    # This script is organized as a bunch of call(...., cont) with a terminal
    # call(...., halt).  We may have deleted the halting one, so just make sure
    # the last call is a halt
    script.data[pos + len(calls) - len(ins_cmd)] = 0x4  # Call w/ halt


def set_terra_mutant_spot_boss(ctrom: CTRom, boss: BossScheme):
    # 0x145 is the Terra Mutant's map - Black Omen 98F Astral Guardian
    loc_id = 0x145
    script = ctrom.script_manager.get_script(loc_id)

    boss_objs = [0xF, 0x10]

    num_used = min(len(boss.ids), 2)
    first_x, first_y = 0x70, 0x80

    # mutant coords are weird.  The coordinates are the bottom of the mutant's
    # bottom part.  We need to shift up so non-mutants aren't on the party.
    if boss.ids[0] not in [EnemyID.GIGA_MUTANT_HEAD,
                           EnemyID.GIGA_MUTANT_BOTTOM,
                           EnemyID.TERRA_MUTANT_HEAD,
                           EnemyID.TERRA_MUTANT_BOTTOM,
                           EnemyID.MEGA_MUTANT_HEAD,
                           EnemyID.MEGA_MUTANT_BOTTOM]:
        first_y -= 0x20

    for i in range(num_used):
        boss_id = boss.ids[i]
        boss_slot = boss.slots[i]

        new_x = first_x + boss.disps[i][0]
        new_y = first_y + boss.disps[i][1]

        set_object_boss(script, boss_objs[i], boss_id, boss_slot)
        set_object_coordinates(script, boss_objs[i], new_x, new_y)

    # Remove unused boss objects.
    for i in range(len(boss.ids), len(boss_objs)):
        script.remove_object(boss_objs[i])

    # Add more boss objects if needed
    calls = bytearray()
    for i in range(len(boss_objs), len(boss.ids)):
        obj_id = script.append_copy_object(boss_objs[1])

        new_x = first_x + boss.disps[i][0]
        new_y = first_y + boss.disps[i][1]

        set_object_boss(script, obj_id, boss.ids[i], boss.slots[i])
        set_object_coordinates(script, obj_id, new_x, new_y)

        # mimic call of other objects
        call = EC.call_obj_function(obj_id, 3, 1, FuncSync.SYNC)
        calls.extend(call.to_bytearray())

    # Insertion point is right after call_obj_function(0xF, arb0, 1, sync)
    ins_cmd = EC.call_obj_function(0xF, 3, 1, FuncSync.SYNC)

    pos = script.find_exact_command(ins_cmd,
                                    script.get_function_start(8, 1))
    if pos is None:
        print("Error finding insertion position (terra mutant)")
        exit()
    else:
        pos += len(ins_cmd)

    script.insert_commands(calls, pos)


def set_elder_spawn_spot_boss(ctrom: CTRom, boss: BossScheme):
    # 0x60 is the Elder Spawn's map - Black Omen 98F Astral Progeny
    loc_id = 0x60
    script = ctrom.script_manager.get_script(loc_id)

    boss_objs = [0x8, 0x9]

    num_used = min(len(boss.ids), 2)
    first_x, first_y = 0x170, 0xB2

    # overwrite as many boss objects as possible
    for i in range(num_used):
        boss_id = boss.ids[i]
        boss_slot = boss.slots[i]

        new_x = first_x + boss.disps[i][0]
        new_y = first_y + boss.disps[i][1]

        set_object_boss(script, boss_objs[i], boss_id, boss_slot)
        # The coordinate setting is in activate for whatever reason.
        set_object_coordinates(script, boss_objs[i], new_x, new_y, True, 1)

    # Remove unused boss objects.
    for i in range(len(boss.ids), len(boss_objs)):
        script.remove_object(boss_objs[i])

    # Add more boss objects if needed
    calls = bytearray()
    for i in range(len(boss_objs), len(boss.ids)):
        obj_id = script.append_copy_object(boss_objs[1])

        new_x = first_x + boss.disps[i][0]
        new_y = first_y + boss.disps[i][1]

        set_object_boss(script, obj_id, boss.ids[i], boss.slots[i])
        # The coordinate setting is in activate for whatever reason.
        set_object_coordinates(script, obj_id, new_x, new_y, True,
                               fn_id=1)

        # mimic call of other objects
        call = EC.call_obj_function(obj_id, 2, 6, FuncSync.CONT)
        calls.extend(call.to_bytearray())

    # Insertion point is right before call_obj_function(0x8, touch, 6, cont)
    ins_cmd = EC.call_obj_function(0x8, 2, 6, FuncSync.CONT)

    pos = script.find_exact_command(ins_cmd,
                                    script.get_function_start(0, 0))

    if pos is None:
        print("Error finding insertion point (elder spawn)")
        exit()
    else:
        pos += len(ins_cmd)

    script.insert_commands(calls, pos)


def set_heckrans_cave_boss(ctrom: CTRom, boss: BossScheme):

    # Heckran is in 0xC0 now.
    loc_id = 0xC0

    boss_obj = 0xA
    first_x, first_y = 0x340, 0x190

    set_generic_one_spot_boss(ctrom, boss, loc_id, boss_obj,
                              lambda scr: scr.get_function_end(0xA, 1)-1,
                              first_x, first_y)


def set_kings_trial_boss(ctrom: CTRom, boss: BossScheme):
    # Yakra XIII is in 0xC1 now.
    loc_id = 0xC1
    boss_obj = 0xB
    first_x, first_y = 0x40, 0x100

    if EnemyID.GUARDIAN_BIT in boss.ids:
        boss.disps[1] = (-0x08, -0x3A)
        boss.disps[2] = (-0x08, 0x30)
    elif EnemyID.MOTHERBRAIN in boss.ids:
        boss.reorder_horiz(left=True)

    # show spot is right at the end of obj 0xB, arb 0
    set_generic_one_spot_boss(ctrom, boss, loc_id, boss_obj,
                              lambda scr: scr.get_function_end(0xB, 3)-1,
                              first_x, first_y)


def set_ozzies_fort_flea_plus_spot_boss(ctrom: CTRom, boss: BossScheme):
    loc_id = 0xB7
    boss_obj = 0x9
    first_x, first_y = 0x270, 0x250

    # show spot is right at the end of obj 0xB, arb 0
    # This one is different since we're adding at the start of a function.
    # Need to double check that the routines are setting start/end correctly
    set_generic_one_spot_boss(ctrom, boss, loc_id, boss_obj,
                              lambda scr: scr.get_function_start(0x9, 1),
                              first_x, first_y)


def set_ozzies_fort_super_slash_spot_boss(ctrom: CTRom, boss: BossScheme):
    loc_id = 0xB8

    boss_obj = 0x9
    first_x, first_y = 0x270, 0x250

    # show spot is right at the end of obj 0xB, arb 0
    # This one is different since we're adding at the start of a function.
    # Need to double check that the routines are setting start/end correctly
    set_generic_one_spot_boss(ctrom, boss, loc_id, boss_obj,
                              lambda scr: scr.get_function_start(0x9, 1),
                              first_x, first_y)


def set_sun_palace_boss(ctrom: CTRom, boss: BossScheme):
    # 0xFB is Son of Sun's map - Sun Palace
    loc_id = 0xFB
    script = ctrom.script_manager.get_script(loc_id)

    # Eyeball in 0xB and rest are flames. 0x10 is hidden in rando.
    # Really, 0x10 should just be removed from the start.
    script.remove_object(0x10)

    pos, _ = script.find_command([0x96],
                                 script.get_function_start(0x0B, 4))
    script.data[pos+2] = 0x1F
    pos +=3
    cmd = EC.set_object_coordinates(0x100, 0x1FF, False)

    script.delete_commands(pos, 1)
    script.insert_commands(cmd.to_bytearray(), pos)

    boss_objs = [0xB, 0xC, 0xD, 0xE, 0xF]
    num_used = min(len(boss.ids), len(boss_objs))

    # After the ambush
    first_x, first_y = 0x100, 0x1B0

    # overwrite as many boss objects as possible
    for i in range(num_used):
        boss_id = boss.ids[i]
        boss_slot = boss.slots[i]

        new_x = first_x + boss.disps[i][0]
        new_y = first_y + boss.disps[i][1]

        set_object_boss(script, boss_objs[i], boss_id, boss_slot)
        set_object_coordinates(script, boss_objs[i], new_x, new_y, True,
                               shift=False)

        if i == 0:
            # SoS is weird about the first part moving before the rest are
            # visible.  So the rest will pop in relative to these coords
            first_x, first_y = 0x100, 0x1FF

    # Remove unused boss objects.  In reverse order of course.
    for i in range(len(boss_objs), len(boss.ids), -1):
        script.remove_object(boss_objs[i-1])

    # Add more boss objects if needed.  This will never happen for vanilla
    # Son of Sun, but maybe if scaling adds flames?

    calls = bytearray()
    for i in range(len(boss_objs), len(boss.ids)):
        obj_id = script.append_copy_object(boss_objs[1])

        new_x = first_x + boss.disps[i][0]
        new_y = first_y + boss.disps[i][1]

        set_object_boss(script, obj_id, boss.ids[i], boss.slots[i])
        # The coordinate setting is in init
        set_object_coordinates(script, obj_id, new_x, new_y, True,
                               shift=False)

        # mimic call of other objects
        call = EF()
        if i == len(boss.ids)-1:
            call.add(EC.call_obj_function(obj_id, 1, 1, FuncSync.SYNC))
        else:
            call.add(EC.call_obj_function(obj_id, 1, 1, FuncSync.HALT))

        call.add(EC.generic_one_arg(0xAD, 0x01))
        calls.extend(call.get_bytearray())

    # Insertion point is before the pause before Animate 0x1.
    ins_cmd = EC.generic_one_arg(0xAA, 0x01)

    # In the eyeball's (0xB) arb 1
    pos = script.find_exact_command(ins_cmd,
                                    script.get_function_start(0xB, 4))

    if pos is None:
        print("Error: Couldn't find insertion point (SoS)")
        exit()
    else:
        # pos -= (len(ins_cmd) + 2)  # +2 for the pause command prior
        pos += len(ins_cmd)

    script.insert_commands(calls, pos)


def set_desert_boss(ctrom: CTRom, boss: BossScheme):
    # 0xA1 is Retinite's map - Sunken Desert Devourer
    loc_id = 0xA1
    script = ctrom.script_manager.get_script(loc_id)

    boss_objs = [0xE, 0xF, 0x10]

    # Extra copies of retinite bottom for the vanilla random location
    # There are some blank objects that can be removed, but will not do so.
    del_objs = [0x12, 0x11]
    for x in del_objs:
        script.remove_object(x)

    num_used = min(len(boss.ids), 3)
    first_x, first_y = 0x120, 0xC9
    shift = False

    # overwrite as many boss objects as possible
    for i in range(num_used):
        boss_id = boss.ids[i]
        boss_slot = boss.slots[i]

        new_x = first_x + boss.disps[i][0]
        new_y = first_y + boss.disps[i][1]

        set_object_boss(script, boss_objs[i], boss_id, boss_slot)
        # The coordinate setting is in arb0 for whatever reason.
        set_object_coordinates(script, boss_objs[i], new_x, new_y, True, 3,
                               shift=shift)

    # Remove unused boss objects.  In reverse order of course.
    for i in range(len(boss_objs), len(boss.ids), -1):
        script.remove_object(boss_objs[i-1])

    # Add more boss objects if needed.
    calls = bytearray()

    for i in range(len(boss_objs), len(boss.ids)):
        obj_id = script.append_copy_object(boss_objs[1])

        new_x = first_x + boss.disps[i][0]
        new_y = first_y + boss.disps[i][1]

        set_object_boss(script, obj_id, boss.ids[i], boss.slots[i])
        # The coordinate setting is in arb0
        set_object_coordinates(script, obj_id, new_x, new_y, True,
                               fn_id=4, shift=shift)

        # mimic call of other objects
        call = EC.call_obj_function(obj_id, 4, 0, FuncSync.SYNC)

        calls.extend(call.to_bytearray())

    # Insertion point is before the pause before Calling obj 0xE, arb 1
    ins_cmd = EC.call_obj_function(0xE, 4, 2, FuncSync.HALT)

    # In the eyeball's (0xB) arb 1
    pos = script.find_exact_command(ins_cmd,
                                    script.get_function_start(0x2, 0))

    if pos is None:
        print("Error: Couldn't find insertion point (SoS)")
        exit()
    else:
        pos -= len(ins_cmd)

    script.insert_commands(calls, pos)


def set_twin_golem_spot(ctrom: CTRom, boss: BossScheme):
    # This one is unique because it actually depends on the size of the boss.
    # One spot bosses will be duplicated and others will just appear as-is.

    # 0x19E is the Twin Golems' map - Ocean Palace Regal Antechamber
    loc_id = 0x19E
    script = ctrom.script_manager.get_script(loc_id)

    if len(boss.ids) == 1:
        # Now, it should be that single target bosses get copied into
        # EnemyID.TWIN_BOSS.

        print('Error putting single boss in twin spot.')
        exit()
    else:
        # Somewhat center the multi_spot boss
        # 1) Change the move command to have an x-coord of 0x80 + displacement
        # Only twin golem has a displacement on its first part though.
        move_cmd = EC.generic_two_arg(0x96, 0x6, 0xE)
        pos = script.find_exact_command(move_cmd,
                                        script.get_function_start(0xA, 3))

        first_x = 0x80
        first_y = 0xE0

        # Move command is given in tile coords, so >> 4
        new_x = (first_x + boss.disps[0][0] >> 4)
        new_y = (first_y + boss.disps[0][1] >> 4)
        script.data[pos+1] = new_x

        # Back to pixels for set coords
        new_x = new_x << 4
        new_y = new_y << 4

        # 2) Change the following set coords command to the dest of the move
        coord_cmd = EC.set_object_coordinates(new_x, new_y)

        pos += len(move_cmd)
        script.data[pos:pos+len(coord_cmd)] = coord_cmd.to_bytearray()

    # Now proceed with a normal multi-spot assignment
    boss_objs = [0xA, 0xB]

    # overwrite the boss objs
    for i in range(0, 2):
        set_object_boss(script, boss_objs[i], boss.ids[i], boss.slots[i])

        new_x = first_x + boss.disps[i][0]
        new_y = first_y + boss.disps[i][1]

        # first object's coordinates don't matter.  Second is set in arb0
        if i != 0:
            set_object_coordinates(script, boss_objs[i], new_x, new_y,
                                   True, 3)

    # Add as many new ones as needed.  Slight modification of one spot stuff

    show = EF()
    for i in range(2, len(boss.ids)):
        new_obj = append_boss_object(script, boss, i, first_x, first_y,
                                     False)
        show.add(EC.set_object_drawing_status(new_obj, True))

    # Show after part 2 shows up.
    show_pos = script.get_function_end(0xB, 4) - 1
    script.insert_commands(show.get_bytearray(), show_pos)


def set_mt_woe_boss(ctrom: CTRom, boss: BossScheme):

    if EnemyID.GIGA_GAIA_HEAD in boss.ids:
        return

    loc_id = LocID.MT_WOE_SUMMIT
    script = ctrom.script_manager.get_script(loc_id)

    # Copy blank tiles over GG's body
    pos = script.get_object_start(0)
    copytiles = EC.copy_tiles(2, 1, 0xD, 9, 0x2, 0x11,
                              copy_l1=True, copy_l2=True, copy_l3=True,
                              copy_props=True, wait_vblank=False)
    script.insert_commands(copytiles.to_bytearray(), pos)

    # Copy on return from menu too.
    copytiles_vblank = copytiles.copy()
    copytiles_vblank.command = 0xE4
    pos = script.get_function_start(0, 1)
    script.insert_commands(copytiles_vblank.to_bytearray(), pos)

    # delete the loading of melchior
    pos = script.get_function_start(8, 0)
    script.delete_commands(pos, 1)

    boss_objs = [0x0A, 0x0B, 0x0C]

    first_x, first_y = 0x80, 0x158
    shift = False  # The original coords are pixel coords, don't correct

    if len(boss_objs) > len(boss.ids):
        # Remove unused objects
        for i in range(len(boss_objs), len(boss.ids), -1):
            script.remove_object(boss_objs[i-1])
            del(boss_objs[i-1])
    elif len(boss.ids) > len(boss_objs):
        # Add new copies of a GG Hand object
        for i in range(len(boss_objs), len(boss.ids)):
            obj_id = script.append_copy_object(boss_objs[1])
            boss_objs.append(obj_id)

    for ind, obj in enumerate(boss_objs):
        new_x = first_x + boss.disps[ind][0]
        new_y = first_y + boss.disps[ind][1]

        boss_id = boss.ids[ind]
        boss_slot = boss.slots[ind]

        set_object_boss(script, boss_objs[ind], boss_id, boss_slot)
        set_object_coordinates(script, boss_objs[ind],
                               new_x, new_y, shift=shift)

    # Mt. Woe starts with everything visible so there's no need for anything
    # extra inserted.


# This is line-for-line almost identical to the woe one... may be time to
# abstract some of this out.
def set_geno_dome_boss(ctrom: CTRom, boss: BossScheme):

    if EnemyID.MOTHERBRAIN in boss.ids:
        return

    loc_id = LocID.GENO_DOME_MAINFRAME
    script = ctrom.script_manager.get_script(loc_id)

    # There appears to be an unused display object in 0x23.  It has to go
    # to avoid sprite bugs.
    script.remove_object(0x23)

    # One screen has a function to make the screens shift colors.
    # Get rid of it.
    func = script.get_function(0x21, 1)
    script.set_function(0x22, 1, func)

    # Weird commands that make mother brain's colors shift.
    # Setting 0x7E2A21 to  2 or 0.  Both are command 0x4A.
    script.delete_command_from_function([0x4A], 0x1E, 0)
    script.delete_command_from_function([0x4A], 0x1E, 0)

    boss_objs = [0x1F, 0x20, 0x21, 0x22]

    first_x, first_y = 0xA0, 0x6F
    shift = False

    ins_cmds = EF()
    if len(boss_objs) > len(boss.ids):
        # Remove unused objects
        for i in range(len(boss_objs), len(boss.ids), -1):
            script.remove_object(boss_objs[i-1])
            del(boss_objs[i-1])
    elif len(boss.ids) > len(boss_objs):
        # Add new copies of a display object
        ins_cmds = EF()
        for i in range(len(boss_objs), len(boss.ids)):
            obj_id = script.append_copy_object(boss_objs[1])
            boss_objs.append(obj_id)

            # record the command that needs to be called to display the
            # new object.  Just call its activate function in this case.
            ins_cmds.add(EC.call_obj_function(obj_id, 1, 1, FuncSync.CONT))

    for ind, obj in enumerate(boss_objs):
        new_x = first_x + boss.disps[ind][0]
        new_y = first_y + boss.disps[ind][1]

        boss_id = boss.ids[ind]
        boss_slot = boss.slots[ind]

        set_object_boss(script, boss_objs[ind], boss_id, boss_slot)
        set_object_coordinates(script, boss_objs[ind],
                               new_x, new_y, shift=shift)

    start = script.get_function_start(0x1E, 0)
    end = script.get_function_end(0x1E, 0)
    ins_pos_cmd = EC.call_obj_function(0x1F, 1, 1, FuncSync.CONT)
    ins_pos = script.find_exact_command(ins_pos_cmd, start, end)
    ins_pos += len(ins_pos_cmd)

    script.insert_commands(ins_cmds.get_bytearray(), ins_pos)


def set_arris_dome_boss(ctrom: CTRom, boss: BossScheme):

    if EnemyID.GUARDIAN in boss.ids:
        return

    loc_id = LocID.ARRIS_DOME_GUARDIAN_CHAMBER
    script = ctrom.script_manager.get_script(loc_id)

    copy_tiles = EC.copy_tiles(3, 0x11, 0xC, 0x1C,
                               3, 2,
                               copy_l1=True,
                               copy_l3=True,
                               copy_props=True,
                               unk_0x10=True,
                               unk_0x20=True,
                               wait_vblank=False)

    pos = script.get_object_start(0)
    script.insert_commands(copy_tiles.to_bytearray(), pos)

    # copy the vblank waiting version to obj0 func 1 for post-menu
    copy_tiles_vblank = EC.copy_tiles(3, 0x11, 0xC, 0x1C,
                                      3, 2,
                                      copy_l1=True,
                                      copy_l3=True,
                                      copy_props=True,
                                      unk_0x10=True,
                                      unk_0x20=True,
                                      wait_vblank=True)

    pos = script.get_function_start(0, 0)
    script.insert_commands(copy_tiles_vblank.to_bytearray(), pos)

    first_x, first_y = 0x80, 0xB8
    # first_x, first_y = 0x80, 0xC8
    shift = False

    boss_objs = [0xB, 0xC, 0xD]

    # Remove an unneeded move cmd from the arb0.  The bits float down from
    # the ceiling, but we don't need that.
    script.delete_command_from_function([0x96], 0xC, 3)
    script.delete_command_from_function([0x96], 0xD, 3)

    # Remove the hide command from startup
    script.delete_command_from_function([0x91], 0xB, 0)
    script.delete_command_from_function([0x91], 0xC, 0)
    script.delete_command_from_function([0x91], 0xD, 0)

    # Remove old calls to bit arb0s.  We will recreate these once we have the
    # right list of objects.
    call = EC.call_obj_function(0xC, 3, 3, FuncSync.CONT)
    start = script.get_function_start(9, 1)
    end = script.get_function_end(9, 1)
    pos = script.find_exact_command(call, start, end)
    script.delete_commands(pos, 2)

    if len(boss_objs) > len(boss.ids):
        # Remove unused objects
        for i in range(len(boss_objs), len(boss.ids), -1):
            script.remove_object(boss_objs[i-1])
            del(boss_objs[i-1])
    elif len(boss.ids) > len(boss_objs):
        # Add new copies of a bit object (that we cleaned up above)
        for i in range(len(boss_objs), len(boss.ids)):
            obj_id = script.append_copy_object(boss_objs[1])
            boss_objs.append(obj_id)

    for ind, obj in enumerate(boss_objs):
        new_x = first_x + boss.disps[ind][0]
        new_y = first_y + boss.disps[ind][1]

        boss_id = boss.ids[ind]
        boss_slot = boss.slots[ind]

        set_object_boss(script, obj, boss_id, boss_slot)
        set_object_coordinates(script, boss_objs[ind],
                               new_x, new_y, shift=shift)

    # add calls to arb0s for all but first object.  This makes them visible
    # and sets collisions correctly.
    new_calls = EF()
    for ind in range(1, len(boss_objs)):
        # The last function halts, so all of them are finished before
        # proceeding to the battle.
        if ind == len(boss_objs) - 1:
            sync = FuncSync.HALT
        else:
            sync = FuncSync.CONT

        new_calls.add(EC.call_obj_function(boss_objs[ind], 3, 3, sync))

    start = script.get_function_start(9, 1)
    end = script.get_function_end(9, 1)
    pos, _ = script.find_command([0xD8], start, end)  # Battle

    if pos is None:
        raise SystemExit('Couldn\'t find insertion point (Arris)')

    script.insert_commands(new_calls.get_bytearray(), pos)


# set_generic_one_spot_boss should be able to set any one spot location's boss
# with a little help
#       ctrom: has the script manager to get scripts from
#        boss: A BossScheme object with the boss's coordinates/slots
#      loc_id: The id of the location to write to (not the location event id)
#    boss_obj: The id of the one spot boss's object in the script
# show_pos_fn: A function to determine how to find the insertion point after
#              the objects have been added.
#     first_x: The x-coordinate of the boss when show_pos is hit.  This should
#              be after all movement is done.
#     first_y: The same as first_x but for the y_coordinate
#    is_shown: Should the boss be shown by default.  Usually this is False.
def set_generic_one_spot_boss(ctrom: CTRom,
                              boss: BossScheme,
                              loc_id: int,
                              boss_obj: int,
                              show_pos_fn: Callable[[Event], int],
                              first_x: int = None,
                              first_y: int = None,
                              is_shown: bool = False):

    script_manager = ctrom.script_manager
    script = script_manager.get_script(loc_id)

    set_generic_one_spot_boss_script(script, boss, boss_obj,
                                     show_pos_fn, first_x, first_y, is_shown)


# This is exactly like the above except that the user provides the script.
# This is needed in some cases when there is preprocessing required before
# Following the general procedure.
def set_generic_one_spot_boss_script(script: Event,
                                     boss: BossScheme,
                                     boss_obj: int,
                                     show_pos_fn: Callable[[Event], int],
                                     first_x: int = None,
                                     first_y: int = None,
                                     is_shown: bool = False):

    first_id = boss.ids[0]
    first_slot = boss.slots[0]

    set_object_boss(script, boss_obj, first_id, first_slot)

    show = EF()

    for i in range(1, len(boss.ids)):
        new_obj = append_boss_object(script, boss, i,
                                     first_x, first_y,
                                     is_shown)
        show.add(EC.set_object_drawing_status(new_obj, True))

    # If a boss starts out shown, no need to insert commands
    if not is_shown:
        # script.print_fn_starts()
        show_pos = show_pos_fn(script)
        # print(f"{show_pos:04X}")
        # input()
        script.insert_commands(show.get_bytearray(), show_pos)


def set_object_boss(script: Event, obj_id: int, boss_id: int, boss_slot: int,
                    ignore_jumps: bool = True):

    start = script.get_object_start(obj_id)
    end = script.get_function_end(obj_id, 0)

    pos = start
    while pos < end:

        cmd = get_command(script.data, pos)

        if cmd.command in EC.fwd_jump_commands and ignore_jumps:
            pos += (cmd.args[-1] - 1)
        elif cmd.command == 0x83:
            is_static = cmd.args[1] & 0x80
            cmd.args[0], cmd.args[1] = boss_id, (boss_slot | is_static)
            script.data[pos:pos+len(cmd)] = cmd.to_bytearray()
            break

        pos += len(cmd)


def set_object_coordinates(script: Event, obj_id: int, x: int, y: int,
                           ignore_jumps: bool = True, fn_id: int = 0,
                           shift: bool = True):

    start = script.get_function_start(obj_id, fn_id)
    end = script.get_function_end(obj_id, fn_id)

    pos = start
    while pos < end:

        cmd = get_command(script.data, pos)

        if cmd.command in EC.fwd_jump_commands and ignore_jumps:
            pos += (cmd.args[-1] - 1)
        elif cmd.command in [0x8B, 0x8D]:
            new_coord_cmd = EC.set_object_coordinates(x, y, shift)
            # print(f"x={x:04X}, y={y:04X}")
            # print(new_coord_cmd)
            # input()

            # The pixel-based and tile-based commands have different lengths.
            # If the new coordinates don't match the old, you have to do a
            # delete/insert.
            if new_coord_cmd.command == cmd.command:
                script.data[pos:pos+len(new_coord_cmd)] = \
                    new_coord_cmd.to_bytearray()
            else:
                script.insert_commands(new_coord_cmd.to_bytearray(),
                                       pos+len(cmd))
                script.delete_commands(pos, 1)

            break

        pos += len(cmd)


# Make a barebones object to make a boss part and hide it.
def append_boss_object(script: Event, boss: BossScheme, part_index: int,
                       first_x: int, first_y: int,
                       is_shown: bool = False) -> int:

    new_id = boss.ids[part_index]
    new_slot = boss.slots[part_index]

    # Pray these don't come up negative.  They shouldn't?
    new_x = first_x + boss.disps[part_index][0]
    new_y = first_y + boss.disps[part_index][1]

    # There's a problem because of the inconsistencies between the tile
    # coords and pixel coords.  For now, we're going to check if the initial
    # coords are tile based (%16 == 0).  If not, shift them so that the
    # set_coords will shift them back to the right place.
    # TODO: Fix by using the set_coord command in the script to determine
    #       Whether pixels or tiles are specified for first_x, first_y
    shift = True
    if first_x % 16 != 0 or first_y % 16 != 0:
        # shift pixel coordinates to match their tile counterparts
        shift = False

    # print(f"({first_x:04X}, {first_y:04X})")
    # print(f"({new_x:04X}, {new_y:04X})")
    # input()

    # print(EC.set_object_coordinates(new_x, new_y))
    # print(' '.join(f"{x:02X}"
    #                for x in
    #                EC.set_object_coordinates(new_x, new_y).to_bytearray()))
    # input()

    # Make the new object
    init = EF()
    init.add(EC.load_enemy(new_id, new_slot)) \
        .add(EC.set_object_coordinates(new_x, new_y, shift)) \
        .add(EC.set_own_drawing_status(is_shown)) \
        .add(EC.return_cmd()) \
        .add(EC.end_cmd())

    act = EF()
    act.add(EC.return_cmd())

    obj_id = script.append_empty_object()
    script.set_function(obj_id, 0, init)
    script.set_function(obj_id, 1, act)

    return obj_id


# When Giga Gaia and Mother Brain get put into the pool, Zenan Bridge will
# hit the sprite limit.  This function will copy Zenan Bridge to a new map
# and adjust the scripts to link them together appropriately.
def duplicate_zenan_bridge(ctrom: CTRom, dup_loc_id: LocID):

    fsrom = ctrom.rom_data
    script_man = ctrom.script_manager

    # Copy the exists of the original Zenan Bridge to the copy
    exits = LocExits.from_rom(fsrom)
    duplicate_map(fsrom, exits, LocID.ZENAN_BRIDGE, dup_loc_id)
    exits.write_to_fsrom(fsrom)

    # Copy the script of the original Zenan Bridge to the copy
    script = script_man.get_script(LocID.ZENAN_BRIDGE)
    new_script = copy.deepcopy(script)

    # In the original script, the party runs off the screen, the screen
    # scrolls left, and then the Zombor fight begins.  To avoid sprite limits
    # we are going to warp to the Zenan copy when the team runs off the screen.

    # The part where the team runs off the screen is in obj1, func1
    start = script.get_function_start(0x01, 0x00)
    end = script.get_function_end(0x01, 0x00)

    move_party = EC.move_party(0x86, 0x08, 0x88, 0x7, 0x89, 0x0A)
    pos = script.find_exact_command(move_party, start, end)

    if pos is None:
        print('Error finding move_party')
        raise SystemExit

    # Insert the transition commands after the party moves
    new_move_party = EC.move_party(0x8B, 0x08, 0x8B, 0x7, 0x8B, 0x0A)

    script.delete_commands(pos, 1)
    # pos += len(new_move_party)

    change_loc = EC.change_location(dup_loc_id, 0x08, 0x08)

    # Make the string of new commands.
    # After the party runs off, the screen fades out and we change location
    insert_cmds = EF()
    (
        insert_cmds
        .add(new_move_party)
        .add(EC.darken(1))
        .add(EC.fade_screen())
        .add(change_loc)
    )

    script.insert_commands(insert_cmds.get_bytearray(), pos)

    # after the move party in the normal script, each pc strikes a pose and the
    # screen scrolls (4 commands). We'll delete those commands because they'll
    # never get executed since we're changing location.
    pos += len(insert_cmds.get_bytearray())
    script.delete_commands(pos, 4)

    # Now, trim down the event for the duplicate map by removing the skeletons
    # other than the ones that make Zombor and the guards.
    unneeded_objs = sorted(
        (0x0D, 0x0E, 0x0F, 0x10, 0x11, 0x12, 0x15, 0x16, 0x17, 0x0F,
         0x0E, 0x0D),
        reverse=True
    )

    for obj in unneeded_objs:
        new_script.remove_object(obj)

    # Trim down obj0, func0 so that all it does is get the party in position
    # for the fight... and preserve the string index of course.  Nobody
    # would forget to preserve the string index, right?
    string_index = new_script.get_string_index()
    string_index_cmd = EC.set_string_index(string_index)

    new_startup_func = EF()
    (
        new_startup_func
        .add(string_index_cmd)
        .add(EC.return_cmd())
        .add(move_party)
        .add(EC.end_cmd())
    )

    # TODO: Instead of a move party command, get conditionals, etc working
    #       in eventcommand.py so that I can write a short script to set
    #       initial coordinates in startup functions of player objs

    # Finally, set the new function and set the new script.
    new_script.set_function(0, 0, new_startup_func)
    script_man.set_script(new_script, LocID.ZENAN_BRIDGE_BOSS)


def duplicate_maps_on_ctrom(ctrom: CTRom):

    fsrom = ctrom.rom_data
    script_man = ctrom.script_manager

    # First do Heckran's Cave Passageways
    exits = LocExits.from_rom(fsrom)
    duplicate_heckran_map(fsrom, exits, LocID.HECKRAN_CAVE_NEW)

    exits.write_to_fsrom(fsrom)

    script = script_man.get_script(LocID.HECKRAN_CAVE_PASSAGEWAYS)

    # Notes for Hecrkan editing:
    #   - Remove 1, 2, 0xC, 0xE, 0xF, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16,
    #         0x17, 0x18
    #   - Heckran's object was 0xD, now 0xA (3 removed prior)
    #   - Can clean up object 0 because it controls multiple encounters, but
    #     There's no real value to doing so.

    new_script = copy.deepcopy(script)
    del_objs = [0x18, 0x17, 0x16, 0x15, 0x14, 0x13, 0x12, 0x11, 0x10, 0xF,
                0xE, 0xC, 2, 1]
    for x in del_objs:
        new_script.remove_object(x)

    script_man.set_script(new_script, LocID.HECKRAN_CAVE_NEW)

    # Now do King's Trial
    #   - In location 0x1B9 (Courtroom Lobby) change the ChangeLocation
    #     command of Obj8, Activate.  It's after a 'If Marle in party' command.

    script = script_man.get_script(LocID.COURTROOM_LOBBY)

    # Find the if Marle is in party command
    (pos, cmd) = script.find_command([0xD2],
                                     script.get_function_start(8, 1),
                                     script.get_function_end(8, 1))
    if pos is None or cmd.args[0] != 1:
        print("Error finding command (kings trial 1)")
        print(pos)
        print(cmd.args[1])
        exit()

    # Find the changelocation in this conditional block
    jump_target = pos + cmd.args[-1] - 1
    (pos, cmd) = script.find_command([0xDC, 0xDD, 0xDE,
                                      0xDF, 0xE0, 0xE1],
                                     pos, jump_target)

    if pos is None:
        print("Error finding command (kings trial 2)")
    else:
        loc = cmd.args[0]
        # The location is in bits 0x01FF of the argument.
        # Keep whatever the old bits have in 0xFE00 put put in the new location
        loc = (loc & 0xFE00) + int(LocID.KINGS_TRIAL_NEW)
        script.data[pos+1:pos+3] = to_little_endian(loc, 2)

    # Note, the script manager hands the actual object, so when edited there's
    # no need to script_man.set_script it

    # Duplicate King's Trial location, 0x1B6, to 0xC1
    duplicate_location_data(fsrom, LocID.KINGS_TRIAL, LocID.KINGS_TRIAL_NEW)

    # Copy and edit script to remove objects
    script = script_man.get_script(LocID.KINGS_TRIAL)
    new_script = copy.deepcopy(script)

    # Can delete:
    #   - Object 0xB: The false witness against the king
    #   - Object 0xC: The paper the chancellor holds up in trial (small)
    #   - Object 0xD: The blue sparkle left by the Yakra key
    # This might not be enough.  Maybe the soldiers can go too?  The scene will
    # be changed, but it's worth it?

    del_objs = [0x19, 0x0C, 0x0B]
    for x in del_objs:
        new_script.remove_object(x)

    # New Yakra XII object is 0xB for boss rando purposes
    script_man.set_script(new_script, LocID.KINGS_TRIAL_NEW)


# Duplicate maps which run into sprite limits for boss rando
def duplicate_maps(fsrom: FS):

    exits = LocExits.from_rom(fsrom)
    duplicate_heckran_map(fsrom, exits, 0xC0)
    exits.write_to_fsrom(fsrom)

    # While we're here let's clean up the script.  Separate that from the
    # boss randomization part.

    # Notes for Hecrkan editing:
    #   - Remove 1, 2, 0xC, 0xE, 0xF, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16,
    #         0x17, 0x18
    #   - Heckran's object was 0xD, now 0xA (3 removed prior)
    #   - Can clean up object 0 because it controls multiple encounters, but
    #     There's no real value to doing so.

    loc_id = 0x2F  # Orig Heckran location id
    loc_ptr = get_loc_event_ptr(fsrom.getbuffer(), loc_id)
    script = Event.from_rom(fsrom.getbuffer(), loc_ptr)

    del_objs = [0x18, 0x17, 0x16, 0x15, 0x14, 0x13, 0x12, 0x11, 0x10, 0xF,
                0xE, 0xC, 2, 1]
    for x in del_objs:
        script.remove_object(x)

    free_event(fsrom, 0xC0)  # New Heckran location id
    Event.write_to_rom_fs(fsrom, 0xC0, script)

    # Now do King's Trial
    #   - In location 0x1B9 (Courtroom Lobby) change the ChangeLocation
    #     command of Obj8, Activate.  It's after a 'If Marle in party' command.

    loc_id = 0x1B9
    loc_ptr = get_loc_event_ptr(fsrom.getbuffer(), loc_id)
    script = Event.from_rom(fsrom.getbuffer(), loc_ptr)

    # Find the if Marle is in party command
    (pos, cmd) = script.find_command([0xD2],
                                     script.get_function_start(8, 1),
                                     script.get_function_end(8, 1))
    if pos is None or cmd.args[0] != 1:
        print("Error finding command (kings trial 1)")
        print(pos)
        print(cmd.args[1])
        exit()

    # Find the changelocation in this conditional block
    jump_target = pos + cmd.args[-1] - 1
    (pos, cmd) = script.find_command([0xDC, 0xDD, 0xDE,
                                      0xDF, 0xE0, 0xE1],
                                     pos, jump_target)

    if pos is None:
        print("Error finding command (kings trial 2)")
    else:
        loc = cmd.args[0]
        # print(f"{loc:04X}")
        loc = (loc & 0xFE00) + 0xC1
        # print(f"{loc:04X}")
        script.data[pos+1:pos+3] = to_little_endian(loc, 2)
        # input()

    free_event(fsrom, 0x1B9)
    Event.write_to_rom_fs(fsrom, 0x1B9, script)

    # duplicate the King's Trial, 0x1B6, to 0xC1 (unused)
    duplicate_location_data(fsrom, 0x1B6, 0xC1)

    loc_ptr = get_loc_event_ptr(fsrom.getbuffer(), 0x1B6)
    script = Event.from_rom(fsrom.getbuffer(), loc_ptr)

    # Can delete:
    #   - Object 0xB: The false witness against the king
    #   - Object 0xC: The paper the chancellor holds up in trial (small)
    #   - Object 0xD: The blue sparkle left by the Yakra key
    # This might not be enough.  Maybe the soldiers can go too?  The scene will
    # be changed, but it's worth it?

    del_objs = [0x19, 0x0C, 0x0B]
    for x in del_objs:
        script.remove_object(x)

    # New Yakra XII object is 0xB

    free_event(fsrom, 0xC1)
    Event.write_to_rom_fs(fsrom, 0xC1, script)


# Write the new EnemyID and slots into the Twin Boss data.
# This is also a convenient time to do the scaling, but it does make it weird
# when doing the rest of the scaling.
def set_twin_boss_in_config(one_spot_boss: BossID,
                            settings: rset.Settings,
                            config: cfg.RandoConfig):
    # If the base boss is golem, then we don't have to do anything because
    # patch.ips writes a super-golem in to the twin boss slot.

    # print(f'Writing {one_spot_boss} to twin boss.')
    if one_spot_boss != BossID.GOLEM:
        twin_boss = config.boss_data_dict[BossID.TWIN_BOSS]
        base_boss = config.boss_data_dict[one_spot_boss]
        base_id = base_boss.scheme.ids[0]
        base_slot = base_boss.scheme.slots[0]

        config.twin_boss_type = base_id

        # The enemy slot for the twin is finnicky.  There is a general rule
        # that works based on the base boss's slot.
        if base_slot == 3:
            alt_slot = 7
        elif base_slot == 6:
            alt_slot = 3
        elif base_slot == 7:
            alt_slot = 9
        else:
            alt_slot = 7

        if base_id == EnemyID.GOLEM_BOSS:
            alt_slot = 8
        elif base_id in (EnemyID.NIZBEL, EnemyID.NIZBEL_II,
                         EnemyID.RUST_TYRANO):
            alt_slot = 6

        # Set the twin boss scheme
        # Note, we do not change the EnemyID from EnemyID.TWIN_BOSS.
        # The stats, graphics, etc will all be copies from the original boss
        # into the Twin spot.
        twin_scheme = twin_boss.scheme
        twin_scheme.slots = [base_slot, alt_slot]

        # Give the twin boss the base boss's ai
        config.enemy_aidb.change_enemy_ai(EnemyID.TWIN_BOSS, base_id)
        config.enemy_atkdb.copy_atk_gfx(EnemyID.TWIN_BOSS, base_id)

        twin_stats = config.enemy_dict[EnemyID.TWIN_BOSS]

        base_stats = config.enemy_dict[base_id].get_copy()

        base_stats.xp = twin_stats.xp
        base_stats.tp = twin_stats.tp
        base_stats.gp = twin_stats.gp

        config.enemy_dict[EnemyID.TWIN_BOSS] = base_stats
        orig_power = config.boss_data_dict[one_spot_boss].power
        twin_boss.power = orig_power

        # Scale the stats and write them to the twin boss spot in the config
        # TODO: Golem has bespoke twin scaling.  Maybe everyone should?

        scaled_stats = twin_boss.scale_to_power(
            25,  # vs 18 in ocean palace
            config.enemy_dict,
            config.enemy_atkdb,
            config.enemy_aidb
        )[EnemyID.TWIN_BOSS]

        # Just here for rusty.
        scaled_stats.sprite_data.set_affect_layer_1(False)

        twin_boss.power = orig_power
        config.enemy_dict[EnemyID.TWIN_BOSS] = scaled_stats

        if base_id == EnemyID.RUST_TYRANO:
            elem = random.choice(list(Element))
            set_rust_tyrano_element(EnemyID.TWIN_BOSS, elem,
                                    config)
            set_rust_tyrano_script_mag(EnemyID.TWIN_BOSS, config)

# This function needs to write the boss assignment to the config respecting
# the provided settings.
def write_assignment_to_config(settings: rset.Settings,
                               config: cfg.RandoConfig):

    if rset.GameFlags.BOSS_RANDO not in settings.gameflags:
        config.boss_assign_dict = get_default_boss_assignment()
        return

    boss_settings = settings.ro_settings

    if boss_settings.preserve_parts:
        # Do some checks to make sure that the lists are ok.
        # TODO:  Make these sets to avoid repeat element errors.

        for boss in [BossID.SON_OF_SUN, BossID.RETINITE]:
            if boss in boss_settings.boss_list:
                print(f"Legacy Boss Randomization: Removing {boss} from the "
                      'boss pool')
                boss_settings.boss_list.remove(boss)

        for loc in [LocID.SUNKEN_DESERT_DEVOURER, LocID.SUN_PALACE]:
            if loc in boss_settings.loc_list:
                print(f"Legacy Boss Randomization: Removing {loc} from the "
                      'location pool')
                boss_settings.loc_list.remove(loc)

        # Make sure that there are enough one/two partbosses to distribute to
        # the one/two part locations
        one_part_bosses = [boss for boss in boss_settings.boss_list
                           if boss in BossID.get_one_part_bosses()]

        one_part_locations = [loc for loc in boss_settings.loc_list
                              if loc in LocID.get_one_spot_boss_locations()]

        # Now, we're allowing a repeat assignment to ocean palace, so it does
        # not require a unique boss to go there.
        if LocID.OCEAN_PALACE_TWIN_GOLEM in one_part_locations:
            has_twin_spot = True
            num_one_part_locs = len(one_part_locations) - 1
        else:
            has_twin_spot = False
            num_one_part_locs = len(one_part_locations)

        if len(one_part_bosses) < num_one_part_locs:
            print("Legacy Boss Randomization Error: "
                  f"{len(one_part_locations)} "
                  "one part locations provided but "
                  f"only {len(one_part_bosses)} one part bosses provided.")
            exit()

        two_part_bosses = [boss for boss in boss_settings.boss_list
                           if boss in BossID.get_two_part_bosses()]

        two_part_locations = [loc for loc in boss_settings.loc_list
                              if loc in LocID.get_two_spot_boss_locations()]

        if len(two_part_bosses) < len(two_part_locations):
            print("Legacy Boss Randomization Error: "
                  f"{len(two_part_locations)} "
                  "two part locations provided but "
                  f"only {len(two_part_locations)} two part bosses provided.")
            exit()

        # Now do the assignment

        # First make an assignment to the twin spot and remove that location
        # from the list.
        if has_twin_spot:
            twin_boss = random.choice(one_part_bosses)
            set_twin_boss_in_config(twin_boss, settings, config)
            config.boss_assign_dict[LocID.OCEAN_PALACE_TWIN_GOLEM] = \
                BossID.TWIN_BOSS
            one_part_locations.remove(LocID.OCEAN_PALACE_TWIN_GOLEM)

        # Shuffle the bosses and assign the head of the list to the remaining
        # locations.
        random.shuffle(one_part_bosses)
        for i in range(len(one_part_locations)):
            boss = one_part_bosses[i]
            location = one_part_locations[i]
            config.boss_assign_dict[location] = boss

        random.shuffle(two_part_bosses)

        for i in range(len(two_part_locations)):
            boss = two_part_bosses[i]
            location = two_part_locations[i]
            config.boss_assign_dict[location] = boss
    else:  # Ignore part count, just randomize!
        locations = boss_settings.loc_list
        bosses = boss_settings.boss_list

        # Why sort before shuffling?
        # Because the order in which the settings file specifies the bosses
        # and locations should not change the randomized output.
        # Boss/location enums IntEnums so it's fine to sort.
        bosses = sorted(bosses)
        locations = list(sorted(locations))  # Copy because we'll edit it

        # Make a special assignment for Twin Golem Spot
        if LocID.OCEAN_PALACE_TWIN_GOLEM in locations:
            # Make a decision on how frequently to see a multi-part boss
            # in the twin spot.  For now, always choose a one-parter if
            # there is one.

            one_part_bosses = [boss for boss in bosses if
                               boss in BossID.get_one_part_bosses()]

            if one_part_bosses:
                twin_boss = random.choice(one_part_bosses)
                set_twin_boss_in_config(twin_boss, settings, config)
                config.boss_data_dict[LocID.OCEAN_PALACE_TWIN_GOLEM] = \
                    BossID.TWIN_BOSS

                # Remove twin spot from the list.
                # Do not remove the boss.  It can be assigned elsewhere too.
                locations.remove(LocID.OCEAN_PALACE_TWIN_GOLEM)

            # If no one part bosses have been provided, then make no special
            # assignment.  Just proceed as usual.

        if len(bosses) < len(locations):
            print('RO Error: Fewer bosses than locations given.')
            exit()

        random.shuffle(bosses)
        for i in range(len(locations)):
            config.boss_assign_dict[locations[i]] = bosses[i]

    # Force GG on Woe for Ice Age
    if settings.game_mode == rset.GameMode.ICE_AGE:
        woe_boss = config.boss_assign_dict[LocID.MT_WOE_SUMMIT]
        if woe_boss != BossID.GIGA_GAIA:
            if BossID.GIGA_GAIA in config.boss_assign_dict.values():
                gg_loc = next(
                    x for x in config.boss_assign_dict
                    if config.boss_assign_dict[x] == BossID.GIGA_GAIA
                )
                config.boss_assign_dict[LocID.MT_WOE_SUMMIT] = \
                    BossID.GIGA_GAIA
                config.boss_assign_dict[gg_loc] = woe_boss
            else:
                config.boss_assign_dict[LocID.MT_WOE_SUMMIT] = \
                    BossID.GIGA_GAIA

    # Sprite data changes
    # Guardian is given Nu's appearance outside of Arris Dome
    arris_boss = config.boss_assign_dict[LocID.ARRIS_DOME_GUARDIAN_CHAMBER]
    if arris_boss != BossID.GUARDIAN:
        nu_sprite = config.enemy_dict[EnemyID.NU].sprite_data.get_copy()
        guardian_data = config.enemy_dict[EnemyID.GUARDIAN]
        guardian_data.sprite_data = nu_sprite

    # GG needs to not affect Layer1 when it is outside of Woe
    woe_boss = config.boss_assign_dict[LocID.MT_WOE_SUMMIT]
    if woe_boss != BossID.GIGA_GAIA:
        gg_data = config.enemy_dict[EnemyID.GIGA_GAIA_HEAD]
        gg_data.sprite_data.set_affect_layer_1(False)

    # Same for rusty outside of giant's claw
    claw_boss = config.boss_assign_dict[LocID.GIANTS_CLAW_TYRANO]
    if claw_boss != BossID.RUST_TYRANO:
        rusty_data = config.enemy_dict[EnemyID.RUST_TYRANO]
        rusty_data.sprite_data.set_affect_layer_1(False)


# Scale the bosses given (the game settings) and the current assignment of
# the bosses.  This is to be differentiated from the boss scaling flag which
# scales based on the key item assignment.
def scale_bosses_given_assignment(settings: rset.Settings,
                                  config: cfg.RandoConfig):
    # dictionaries: location --> BossID
    default_assignment = get_default_boss_assignment()
    current_assignment = config.boss_assign_dict

    # dictionaries: BossID --> Boss data
    orig_data = config.boss_data_dict

    endgame_locs = [
        LocID.OCEAN_PALACE_ENTRANCE, LocID.OCEAN_PALACE_TWIN_GOLEM,
        LocID.BLACK_OMEN_ELDER_SPAWN, LocID.BLACK_OMEN_GIGA_MUTANT,
        LocID.BLACK_OMEN_TERRA_MUTANT
    ]

    # Get the new obstacle (if needed) before tech scaling.  If further
    # obstacle duplicates are made, they will inherit the right status.
    enemy_aidb = config.enemy_aidb
    early_obstacle_bosses = []
    obstacle_bosses = [BossID.MEGA_MUTANT, BossID.TERRA_MUTANT]
    for loc in current_assignment:
        if current_assignment[loc] in obstacle_bosses and \
           loc not in endgame_locs:

            boss = current_assignment[loc]
            early_obstacle_bosses.append(boss)

    if early_obstacle_bosses:
        # Make a new obstacle
        atk_db = config.enemy_atkdb
        new_obstacle = atk_db.get_tech(0x58)
        # Choose a status that doesn't incapacitate the team.
        # But also no point choosing poison because mega has shadow slay
        new_status = random.choice(
            (StatusEffect.LOCK, StatusEffect.SLOW)
        )
        new_obstacle.effect.status_effect = new_status

        new_id = enemy_aidb.unused_techs[-1]
        atk_db.set_tech(new_obstacle, new_id)

        for boss in early_obstacle_bosses:
            boss_data = orig_data[boss]
            scheme = boss_data.scheme

            for part in list(set(scheme.ids)):
                enemy_aidb.change_tech_in_ai(part, 0x58, new_id)

    # We want to avoid a potential chain of assignments such as:
    #    A is scaled relative to B
    #    C is scaled relative to A
    # In the second scaling we want to scale relative to A's original stats,
    # not the stats that arose from the first scaling.

    # So here's a dict to store the scaled stats before writing them back
    # to the config at the very end.
    scaled_dict = dict()
    new_power_values = dict()

    for location in settings.ro_settings.loc_list:
        orig_boss = orig_data[default_assignment[location]]
        new_boss = orig_data[current_assignment[location]]
        scaled_stats = new_boss.scale_relative_to(orig_boss,
                                                  config.enemy_dict,
                                                  config.enemy_atkdb,
                                                  config.enemy_aidb)
        
        # Update rewards to match original boss
        # TODO: This got too big.  Break into own function?
        # orig_id = default_assignment[location]
        # new_id = current_assignment[location]
        # print(f'{orig_id} --> {new_id}')
        spot_xp = sum(config.enemy_dict[part].xp
                      for part in orig_boss.scheme.ids)
        spot_tp = sum(config.enemy_dict[part].tp
                      for part in orig_boss.scheme.ids)
        spot_gp = sum(config.enemy_dict[part].gp
                      for part in orig_boss.scheme.ids)
        spot_reward_group = enemyrewards.get_tier_of_enemy(
            orig_boss.scheme.ids[0]
        )

        boss_xp = sum(config.enemy_dict[part].xp
                      for part in new_boss.scheme.ids)
        boss_tp = sum(config.enemy_dict[part].tp
                      for part in new_boss.scheme.ids)
        boss_gp = sum(config.enemy_dict[part].gp
                      for part in new_boss.scheme.ids)

        for ind, part in enumerate(scaled_stats.keys()):
            part_count = sum(
                part_id == part for part_id in new_boss.scheme.ids
            )
            part_xp = sum(
                config.enemy_dict[part_id].xp
                for part_id in new_boss.scheme.ids
                if part_id == part
            )

            part_tp = sum(
                config.enemy_dict[part_id].tp
                for part_id in new_boss.scheme.ids
                if part_id == part
            )

            part_gp = sum(
                config.enemy_dict[part_id].gp
                for part_id in new_boss.scheme.ids
                if part_id == part
            )

            if boss_xp == 0:
                scaled_stats[part].xp = 0
            else:
                scaled_stats[part].xp = \
                    round(part_xp/(part_count*boss_xp)*spot_xp)

            if boss_tp == 0:
                scaled_stats[part].tp = 0
            else:
                scaled_stats[part].tp = \
                    round(part_tp/(part_count*boss_tp)*spot_tp)

            if boss_gp == 0:
                scaled_stats[part].gp = 0
            else:
                scaled_stats[part].gp = \
                    round(part_gp/(part_count*boss_gp)*spot_gp)

            enemyrewards.set_enemy_charm_drop(
                scaled_stats[part],
                spot_reward_group,
                settings.item_difficulty
            )

        new_power_values[location] = orig_boss.power

        # Put the stats in scaled_dict
        scaled_dict.update(scaled_stats)

    # In case of multiple power adjustments, make sure that the boss powers
    # are properly updated.
    for loc in new_power_values:
        boss = config.boss_assign_dict[loc]
        config.boss_data_dict[boss].power = new_power_values[loc]

    # Write all of the scaled stats back to config's dict
    config.enemy_dict.update(scaled_dict)

    # Update Rust Tyrano's magic boost in script
    set_rust_tyrano_script_mag(EnemyID.RUST_TYRANO, config)


def get_obstacle_id(enemy_id: EnemyID, config: cfg.RandoConfig) -> int:
    obstacle_msg_ids = (0xBA, 0x92)  # Only covers Terra, Mega

    ai_script = config.enemy_aidb.scripts[enemy_id]
    ai_script_b = ai_script.get_as_bytearray()
    tech_offsets = ai_script.find_command(ai_script_b, 0x02)

    for pos in tech_offsets:
        msg = ai_script_b[pos+5]

        if msg in obstacle_msg_ids:
            return ai_script_b[pos+1]

    return None

# getting/setting tyrano element share this data, so I'm putting here in a
# private global.
_tyrano_nukes = {
    Element.FIRE: 0x37,
    Element.ICE: 0x52,
    Element.LIGHTNING: 0xBB,
    Element.NONELEMENTAL: 0x8E,
    Element.SHADOW: 0x6B
}

_tyrano_minor_techs = {
    Element.FIRE: 0x0A,
    Element.ICE: 0x2A,
    Element.LIGHTNING: 0x2B,
    Element.NONELEMENTAL: 0x14,
    Element.SHADOW: 0x15  # Weird both 0x14 and 0x15 are lasers
}


def set_rust_tyrano_element(tyrano_id: EnemyID,
                            tyrano_element: Element,
                            config: cfg.RandoConfig):
    tyrano_ai = config.enemy_aidb.scripts[tyrano_id]
    tyrano_usage = tyrano_ai.tech_usage

    orig_nuke = [x for x in _tyrano_nukes.values()
                 if x in tyrano_usage]

    elem_str = {
        Element.FIRE: 'Fire',
        Element.ICE: 'Water',
        Element.SHADOW: 'Shadow',
        Element.LIGHTNING: 'Lightning',
        Element.NONELEMENTAL: 'Magic'
    }
    power_string = elem_str[tyrano_element] + ' Pwr Up!'
    # String goes in 6D
    config.enemy_aidb.battle_msgs.set_msg_from_str(0x6D, power_string)

    assert len(orig_nuke) == 1
    orig_nuke = orig_nuke[0]
    new_nuke = _tyrano_nukes[tyrano_element]

    tyrano_ai.change_tech_usage(orig_nuke, new_nuke)


def get_rust_tyrano_element(tyrano_id: EnemyID,
                            config: cfg.RandoConfig) -> Element:
    tyrano_ai = config.enemy_aidb.scripts[tyrano_id]
    tyrano_usage = tyrano_ai.tech_usage

    nuke_elem = [
        elem for elem in _tyrano_nukes
        if _tyrano_nukes[elem] in tyrano_usage
    ]

    assert len(nuke_elem) == 1

    return nuke_elem[0]


# Rust Tyrano magic stat scales
# grows 30 (init), 65, 100, 175, 253.
# cumulative factors: 13/6, 10/3, 35/6, 253/30
def set_rust_tyrano_script_mag(tyrano_id: EnemyID,
                               config: cfg.RandoConfig):
    tyrano_ai = config.enemy_aidb.scripts[tyrano_id]
    tyrano_ai_b = tyrano_ai.get_as_bytearray()

    base_mag = config.enemy_dict[tyrano_id].magic
    factors = [13/6, 10/3, 35/6, 253/30]
    new_magic_vals = [min(round(x*base_mag), 255) for x in factors]

    # There should be four set magic commands of the form
    # 0B 39 XX 00 6D
    # 0B - Change Stat, 39 - Stat offset (magic), XX - Magnitude
    # 00 - Mode = set, 6D - message to display

    AI = cfg.enemyai.AIScript
    stat_set_cmd_locs = AI.find_command(tyrano_ai_b, 0x0B)

    stat_num = 0
    for ind in stat_set_cmd_locs:
        if tyrano_ai_b[ind] == 0x0B and tyrano_ai_b[ind+4] == 0x6D:
            tyrano_ai_b[ind+2] = new_magic_vals[stat_num]
            stat_num += 1
        else:
            print('Warning: Found other stat mod')

    config.enemy_aidb.scripts[tyrano_id] = AI(tyrano_ai_b)


def set_black_tyrano_element(tyrano_element: Element,
                             config: cfg.RandoConfig):
    # Update black tyrano AI to use the right elemental techs
    tyrano_ai = config.enemy_aidb.scripts[EnemyID.BLACKTYRANO]
    tyrano_usage = tyrano_ai.tech_usage

    orig_nuke = [x for x in _tyrano_nukes.values()
                 if x in tyrano_usage]
    orig_minor_tech = [x for x in _tyrano_minor_techs.values()
                       if x in tyrano_usage]

    assert len(orig_nuke) == 1 and len(orig_minor_tech) == 1

    orig_nuke = orig_nuke[0]
    orig_minor_tech = orig_minor_tech[0]

    new_nuke = _tyrano_nukes[tyrano_element]
    new_minor_tech = _tyrano_minor_techs[tyrano_element]

    tyrano_ai.change_tech_usage(orig_nuke, new_nuke)
    tyrano_ai.change_tech_usage(orig_minor_tech, new_minor_tech)


def get_black_tyrano_element(config: cfg.RandoConfig) -> Element:
    # Update black tyrano AI to use the right elemental techs
    tyrano_ai = config.enemy_aidb.scripts[EnemyID.BLACKTYRANO]
    tyrano_usage = tyrano_ai.tech_usage

    nuke_elem = [
        elem for elem in _tyrano_nukes
        if _tyrano_nukes[elem] in tyrano_usage
    ]

    assert len(nuke_elem) == 1, 'Multiple Tyrano nukes'

    minor_elem = [
        elem for elem in _tyrano_minor_techs
        if _tyrano_minor_techs[elem] in tyrano_usage
    ]

    assert len(minor_elem) == 1, 'Multiple Tyrano minor attacks'
    assert minor_elem[0] == nuke_elem[0], 'Element mismatch'

    return minor_elem[0]


# Magus gets random hp and a random character sprite (ctenums.CharID)
# Black Tyrano gets random hp and a random element (ctenums.Element)
def randomize_midbosses(settings: rset.Settings, config: cfg.RandoConfig):

    # Random hp from 10k to 15k
    magus_stats = config.enemy_dict[EnemyID.MAGUS]
    magus_stats.hp = random.randrange(10000, 15001, 1000)

    if settings.game_mode == rset.GameMode.LEGACY_OF_CYRUS:
        magus_char = config.char_assign_dict[RecruitID.PROTO_DOME].held_char
    else:
        magus_char = random.choice(list(CharID))

    magus_nukes = {
        CharID.CRONO: 0xBB,  # Luminaire
        CharID.MARLE: 0x52,  # Hexagon Mist
        CharID.LUCCA: 0xA9,  # Flare
        CharID.ROBO: 0xBB,   # Luminaire
        CharID.FROG: 0x52,   # Hexagon Mist
        CharID.AYLA: 0x8E,   # Energy Release
        CharID.MAGUS: 0x6B   # Dark Matter
    }

    nuke_strs = {
        CharID.CRONO: 'Luminaire / Crono\'s strongest attack!',
        CharID.MARLE: 'Hexagon Mist /Marle\'s strongest attack!',
        CharID.LUCCA: 'Flare / Lucca\'s strongest attack!',
        CharID.ROBO: 'Luminaire /Robo\'s strongest attack!',
        CharID.FROG: 'Hexagon Mist /Frog\'s strongest attack.',
        CharID.AYLA: 'Energy Flare /Ayla\'s strongest attack!',
        CharID.MAGUS: 'Dark Matter / Magus\' strongest attack!',
    }

    magus_ai = config.enemy_aidb.scripts[EnemyID.MAGUS]
    magus_usage = magus_ai.tech_usage

    orig_nukes = [x for x in magus_nukes.values()
                  if x in magus_usage]

    assert len(orig_nukes) == 1

    orig_nuke = orig_nukes[0]
    magus_ai.change_tech_usage(orig_nuke, magus_nukes[magus_char])
    magus_stats.sprite_data.set_sprite_to_pc(magus_char)
    magus_stats.name = str(magus_char)

    battle_msgs = config.enemy_aidb.battle_msgs
    battle_msgs.set_msg_from_str(0x23, nuke_strs[magus_char])

    config.enemy_dict[EnemyID.BLACKTYRANO].hp = \
        random.randrange(8000, 13001, 1000)

    tyrano_element = random.choice(list(Element))
    set_black_tyrano_element(tyrano_element, config)
    set_rust_tyrano_element(EnemyID.RUST_TYRANO, tyrano_element, config)

    # We're going to jam obstacle randomization here
    # Small block to randomize status inflicted by Obstacle/Chaotic Zone
    SE = StatusEffect
    rand_num = random.randrange(0, 10, 1)

    #  if rand_num < 2:
    #      status_effect = rand.choice(1,0x40) #Blind, Poison
    if rand_num < 8:
        status_effect = random.choice(
            [SE.SLEEP, SE.LOCK, SE.SLOW])
    else:
        status_effect = random.choice([SE.CHAOS, SE.STOP])     # Chaos, Stop

    obstacle = config.enemy_atkdb.get_tech(0x58)
    obstacle.effect.status_effect = status_effect
    config.enemy_atkdb.set_tech(obstacle, 0x58)


def write_bosses_to_ctrom(ctrom: CTRom, config: cfg.RandoConfig):

    # Config should have a list of what bosses are to be placed where, so
    # now it's just a matter of writing them to the ctrom.

    # Associate each boss location with the function which sets that
    # location's boss.
    assign_fn_dict = {
        LocID.MANORIA_COMMAND: set_manoria_boss,
        LocID.CAVE_OF_MASAMUNE: set_denadoro_boss,
        LocID.REPTITE_LAIR_AZALA_ROOM: set_reptite_lair_boss,
        LocID.MAGUS_CASTLE_FLEA: set_magus_castle_flea_spot_boss,
        LocID.MAGUS_CASTLE_SLASH: set_magus_castle_slash_spot_boss,
        LocID.GIANTS_CLAW_TYRANO: set_giants_claw_boss,
        LocID.TYRANO_LAIR_NIZBEL: set_tyrano_lair_midboss,
        LocID.ZEAL_PALACE_THRONE_NIGHT: set_zeal_palace_boss,
        LocID.ZENAN_BRIDGE_BOSS: set_zenan_bridge_boss,
        LocID.DEATH_PEAK_GUARDIAN_SPAWN: set_death_peak_boss,
        LocID.BLACK_OMEN_GIGA_MUTANT: set_giga_mutant_spot_boss,
        LocID.BLACK_OMEN_TERRA_MUTANT: set_terra_mutant_spot_boss,
        LocID.BLACK_OMEN_ELDER_SPAWN: set_elder_spawn_spot_boss,
        LocID.HECKRAN_CAVE_NEW: set_heckrans_cave_boss,
        LocID.KINGS_TRIAL_NEW: set_kings_trial_boss,
        LocID.OZZIES_FORT_FLEA_PLUS: set_ozzies_fort_flea_plus_spot_boss,
        LocID.OZZIES_FORT_SUPER_SLASH: set_ozzies_fort_super_slash_spot_boss,
        LocID.SUN_PALACE: set_sun_palace_boss,
        LocID.SUNKEN_DESERT_DEVOURER: set_desert_boss,
        LocID.OCEAN_PALACE_TWIN_GOLEM: set_twin_golem_spot,
        LocID.GENO_DOME_MAINFRAME: set_geno_dome_boss,
        LocID.MT_WOE_SUMMIT: set_mt_woe_boss,
        LocID.ARRIS_DOME_GUARDIAN_CHAMBER: set_arris_dome_boss
    }

    # Now do the writing. Only to locations in the above dict.  Only if the
    # assignment differs from default.

    default_assignment = get_default_boss_assignment()
    current_assignment = config.boss_assign_dict

    for loc in current_assignment.keys():
        if current_assignment[loc] == default_assignment[loc] and \
           loc != LocID.OCEAN_PALACE_TWIN_GOLEM:
            # print(f"Not assigning to {loc}.  No change from default.")
            pass
        else:
            if loc not in assign_fn_dict.keys():
                raise SystemExit(
                    f"Error: Tried assigning to {loc}.  Location not "
                    "supported for boss randomization."
                )
            else:
                assign_fn = assign_fn_dict[loc]
                boss_id = current_assignment[loc]
                boss_scheme = config.boss_data_dict[boss_id].scheme
                # print(f"Writing {boss_id} to {loc}")
                # print(f"{boss_scheme}")
                assign_fn(ctrom, boss_scheme)

    # New fun sprite bug:  Enemy 0x4F was a frog before it was turned into
    # the twin golem.  Turning it into other bosses can make for pink screens
    # in the LW credits.

    # Put a different frog sprite in there.
    script = ctrom.script_manager.get_script(LocID.CREDITS_4)
    frog1_load = EC.load_enemy(0x4F, 9, False)
    frog2_load = EC.load_enemy(0x4F, 8, False)

    pos = script.find_exact_command(frog1_load)
    script.data[pos+1] = int(EnemyID.T_POLE)

    pos = script.find_exact_command(frog2_load)
    script.data[pos+1] = int(EnemyID.T_POLE)
