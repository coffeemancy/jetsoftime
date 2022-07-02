'''
Module for hacks that just change looks/sounds without changing gameplay.
'''
import ctenums

from ctrom import CTRom
# import randoconfig as cfg

import byteops
import ctevent
import ctstrings
import mapmangler
import randosettings as rset


def set_pc_names(
        ct_rom: CTRom,
        crono_name: str = None,
        marle_name: str = None,
        lucca_name: str = None,
        robo_name: str = None,
        frog_name: str = None,
        ayla_name: str = None,
        magus_name: str = None,
        epoch_name: str = None
):
    '''
    Provide names to be used for characters and epoch.
    '''
    default_names = (
        'Crono', 'Marle', 'Lucca', 'Robo', 'Frog', 'Ayla', 'Magus', 'Epoch'
    )

    copy_str = bytearray()

    provided_names = (crono_name, marle_name, lucca_name, robo_name,
                      frog_name, ayla_name, magus_name, epoch_name)

    for default_name, given_name in zip(default_names, provided_names):
        if given_name == '' or given_name is None:
            given_name = default_name

        name_b = ctstrings.CTNameString.from_string(given_name, length=5,
                                                    pad_val=0)
        name_b.append(0)
        copy_str.extend(name_b)

    script = ct_rom.script_manager.get_script(ctenums.LocID.LOAD_SCREEN)
    # Finding a memcpy command (0x4E) writing to 0x7E2C32 with a payload of
    # length 0x0032
    memcpy_cmd_b = bytes.fromhex('4E232C7E3200')
    pos = script.data.find(memcpy_cmd_b)
    pos += len(memcpy_cmd_b)

    script.data[pos:pos+len(copy_str)] = copy_str[:]


def apply_quiet_mode(ct_rom: CTRom, settings: rset.Settings):
    '''
    Set the volume of all songs to 0.
    '''

    if rset.CosmeticFlags.QUIET_MODE not in settings.cosmetic_flags:
        return

    rom = ct_rom.rom_data
    rom.seek(0x07241D)

    # Volumes of music tracks stored at 0x07241D.
    # 2 Bytes per song x * 0x53 songs = 0xA6 bytes.
    payload = b'\x00' * 0xA6
    rom.write(payload)


def zenan_bridge_alt_battle_music(ctrom: CTRom, settings: rset.Settings):
    '''
    Play the unused alternate battle theme while going through Zenan Bridge
    '''
    if rset.CosmeticFlags.ZENAN_ALT_MUSIC not in settings.cosmetic_flags:
        return

    LocID = ctenums.LocID
    script_man = ctrom.script_manager

    script = script_man.get_script(LocID.ZENAN_BRIDGE)

    start = script.get_function_start(0x15, 3)
    end = script.get_function_end(0x15, 3)

    # There should only be one playsong command in that function
    pos, _ = script.find_command([0xEA], start, end)

    if pos is None:
        raise ValueError("Error finding Zenan Bridge battle song command")

    # Byte after the command id has the song id.
    script.data[pos+1] = 0x51


def death_peak_singing_mountain_music(ctrom: CTRom,
                                      settings: rset.Settings):
    '''
    Change Death Peak to use Singing Mountain music
    '''
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
        raise ValueError('Error finding play \'Silent light\' command')

    script.data[pos+1] = 0x52


def set_default_background_menu(ctrom: CTRom,
                             settings: rset.Settings):

    '''
    Set the default menu background
    '''
    
    '''
    The RAM address 7E2991, bits 0-2 store the current runtime menu background.
    It is initialized from ROM into RAM from offset 0x02FCA7 , ref:
    0295F1	02960A	CODE	N	Routines copy default config and button settings	2007.06.29

        0295F1 ( A2 A6 FC ) LDX.W #$FCA6 ; source address, combined with MVN data bank operands, == C2FCA6

        0295F4 ( A0 90 29 ) LDY.W #$2990 ; destination address, combined with MVN data bank operands, == 7E2990

        0295F7 ( A9 0B 00 ) LDA.W #$000B ; length to copy -1 , ergo $0B == 11, thus total bytes == 11 + 1 = 12

        0295FA ( 54 7E C2 ) MVN $C2, $7E ; execute copy, data banks C2 source 7E dest
    
    The subroutine to render the save slots on the boot menu, save
    Entry condition to hook is immediately after X register is read, and no further reads exist prior to TAX
    
    most   least
    xxxxx000 0x00 Default grey
    xxxxx001 0x01 Brownish slate
    xxxxx010 0x02 Final Fantasy blue
    xxxxx011 0x03 Brown tiles
    xxxxx100 0x04 Green w/ gold trim
    xxxxx101 0x05 Faux Wood
    xxxxx110 0x06 Black w/ silver trim
    xxxxx111 0x07 Red wheat
    '''
    
    if settings.cosmetic_menu_background == 0:
        return
        
    rom = ctrom.rom_data
    space_man = rom.space_manager

    off = 0x02FCA7

    rom.seek(off)
    default_value = rom.read(1)
    rom.seek(off)
    
    new_value = byteops.get_value_from_bytes(default_value) | settings.cosmetic_menu_background
    
    rom.write(new_value.to_bytes(1, 'little'))

    #Entry condition (from 0x02D2A6, save slot render subroutine), A and X/Y are 16 bits wide, X contains nothing we want to keep, $79 contains current save slot
    
    bg = bytearray.fromhex(
        'E2 30'                         # SEP #$30 ; set A and X/Y to 8 bits; clears high byte of X/Y; irrelevent
        'AD 0C 02'                      # LDA $020C ; check if slot has no data, will be 1A if there is no data or invalid data in the save slot
        'C9 1A'                         # CMP #$1A ; known value
        'D0 07'                         # BNE exit
       f'A9 {new_value & 0x07:02x}'     # LDA #${new_value} ; Could do LDA $C2FCA7 here, but that consumes runtime clocks for no extra benefit
        'A6 79'                         # LDX $79 ; get current save slot from memory, 16 bits wide
        '9D 79 0D'                      # STA $0D79, X
        'C2 33'                         # REP #$33 [exit]; reset A and X/Y to 16 bits, clear carry and zero flags, same as entry condition
        'A5 78'                         # LDA #$78
        '29 00 03'                      # AND #$0300
        '6B'                            # RTL
    )
    
    start = space_man.get_same_bank_free_addrs([len(bg)])
    rom_start = byteops.to_rom_ptr(start[0])
    rom_start_bytes = rom_start.to_bytes(3, 'little')
    jsl = b'\x22' + rom_start_bytes
    
    nop = b'\xEA'
    
    rom.seek(0x02D2A6)
    rom.write(jsl + nop)
    
    mark_used = ctevent.FSWriteType.MARK_USED
    rom.seek(start[0])
    rom.write(bg, mark_used)
