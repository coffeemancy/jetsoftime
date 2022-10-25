'''Module for shortening various event scripts for the randomizer.'''
import ctrom
import ctenums

import eventcommand
import eventfunction

from eventcommand import EventCommand as EC, FuncSync as FS, Operation as OP
from eventfunction import EventCommand as EF


def shorten_fritz_script(ct_rom: ctrom.CTRom):
    '''
    Remove most of Fritz's dialog and remove his father entirely.
    '''
    script = ct_rom.script_manager.get_script(ctenums.LocID.TRUCE_MARKET)

    pos = script.find_exact_command(
        EC.call_obj_function(8, 3, 5, FS.HALT),  # Dad entering
        script.get_function_start(0, 3),
        script.get_function_end(0, 4)
    )
    script.delete_commands(pos, 1)

    # Fritz's text is in obj9, touch (2)
    # 1) Come on in!
    # 2) Crono, I owe you one.
    # 3) I was up the creek .... <--- Remove this one
    # 4) Hope my dad never hears about this.
    pos, cmd = script.find_command([0xBB], script.get_function_start(9, 2))
    pos, cmd = script.find_command([0xBB], pos+len(cmd))
    pos, _ = script.find_command([0xBB], pos+len(cmd))
    script.delete_commands(pos, 1)


def shorten_lavos_crash_script(ct_rom: ctrom.CTRom):
    '''
    After Lavos falls in 65m BC, there's a long scene on the cliffside.
    Remove all unneeded pauses from this scene
    '''

    script = ct_rom.script_manager.get_script(
        ctenums.LocID.PREHISTORIC_CANYON
    )

    start = script.get_function_start(0, 0)
    end = script.get_function_end(0, 0)

    pos = start

    # First, remove all pauses
    while True:
        pos, _ = script.find_command([0xAD], pos, end)
        if pos is None:
            break

        script.delete_commands(pos, 1)

    # Put a slight pause after the lavos scream
    pos = script.find_exact_command(
        EC.generic_command(0xEA, 0x3A), start
    ) + 2

    script.insert_commands(EC.pause(3.0).to_bytearray(), pos)
    pos, _ = script.find_command([0xEB], pos)

    script.delete_commands(pos, 5)  # Delete a second scream and wind song

    # Next command is scroll layers.
    # Make the scroll larger in magnitude, cut it off after 1.75 seconds.
    cmd = eventcommand.get_command(script.data, pos)
    cmd.args[0] = 0x0900
    script.data[pos:pos+len(cmd)] = cmd.to_bytearray()
    pos += len(cmd)
    script.insert_commands(EC.pause(1.75).to_bytearray(), pos)

    # Add the missing function call to make the 3rd sparke move away.
    pos, _ = script.find_command([2], pos)
    script.insert_commands(
        EC.call_obj_function(1, 4, 3, FS.CONT).to_bytearray(),
        pos
    )


def shorten_all_scripts(ct_rom: ctrom.CTRom):
    shorten_fritz_script(ct_rom)
    shorten_lavos_crash_script(ct_rom)
