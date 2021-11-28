# File for hacks that just change looks/sounds without changing gameplay.
# In a perfect world, cosmetic hacks can be turned on/off with a share link.
import ctenums

from ctrom import CTRom
# import randoconfig as cfg

import ctevent
import mapmangler
import randosettings as rset


# Play the unused alternate battle theme while going through Zenan Bridge
def zenan_bridge_alt_battle_music(ctrom: CTRom, settings: rset.Settings):

    if rset.CosmeticFlags.ZENAN_ALT_MUSIC not in settings.cosmetic_flags:
        return

    LocID = ctenums.LocID
    script_man = ctrom.script_manager

    script = script_man.get_script(LocID.ZENAN_BRIDGE)

    start = script.get_function_start(0x15, 3)
    end = script.get_function_end(0x15, 3)

    # There should only be one playsong command in that function
    pos, cmd = script.find_command([0xEA], start, end)

    if pos is None:
        print("Error finding Zenan Bridge battle song command")
        input()

    # Byte after the command id has the song id.
    script.data[pos+1] = 0x51


# Change Death Peak to use Singing Mountain music
def death_peak_singing_mountain_music(ctrom: CTRom,
                                      settings: rset.Settings):

    if rset.CosmeticFlags.DEATH_PEAK_ALT_MUSIC not in settings.cosmetic_flags:
        return

    LocID = ctenums.LocID
    death_peak_maps = [
        LocID.DEATH_PEAK_CAVE,
        LocID.DEATH_PEAK_GUARDIAN_SPAWN,
        LocID.DEATH_PEAK_LOWER_NORTH_FACE,
        LocID.DEATH_PEAK_NORTHEAST_FACE,
        LocID.DEATH_PEAK_NORTHWEST_FACE,
        LocID.DEATH_PEAK_SOUTH_FACE,
        LocID.DEATH_PEAK_SOUTHEAST_FACE,
        LocID.DEATH_PEAK_SUMMIT,
        LocID.DEATH_PEAK_UPPER_NORTH_FACE
    ]

    LocData = mapmangler.LocationData
    rom = ctrom.rom_data.getbuffer()

    for loc in death_peak_maps:
        data = LocData.from_rom(rom, loc)
        data.music = 0x52
        data.write_to_rom(rom, loc)

    script = ctrom.script_manager.get_script(LocID.DEATH_PEAK_GUARDIAN_SPAWN)

    change_music = ctevent.EC.generic_one_arg(0xEA, 0x3C)

    start = script.get_function_start(0x08, 1)
    end = script.get_function_end(0x08, 1)
    pos = script.find_exact_command(change_music, start, end)

    if pos is None:
        print('Error finding silent light')
        raise SystemExit

    script.data[pos+1] = 0x52
