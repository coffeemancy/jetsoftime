
import hashlib
from io import BytesIO

from byteops import get_value_from_bytes, get_value_from_bytes_be, \
    to_little_endian, to_rom_ptr
from ctdecompress import compress
from ctenums import LocID
from ctevent import Event, ScriptManager, get_loc_event_ptr
from eventcommand import get_command
from freespace import FSRom, FSWriteType


class InvalidRomException(Exception):

    def __init__(self, message='Invalid Chrono Trigger rom file.'):
        self.message = message


# CTRom is just a combination FSRom and ScriptManager
# It needs to have all of the information that other modules need to make
# freespace-aware changes to the rom.
# The driving need here is that a randoconfig.ChestTreasure only needs the
# rom data to make a change but a randoconfig.ScriptTreasure needs the rom
# and mechanisms for manipulating scripts.
class CTRom():

    def __init__(self, rom: bytes, ignore_checksum=False):
        # ignore_checksum is so that I can load already-randomized roms
        # if need be.
        if not ignore_checksum and not CTRom.validate_ct_rom_bytes(rom):
            raise InvalidRomException('Bad checksum.')

        self.rom_data = FSRom(rom, False)
        self.script_manager = ScriptManager(self.rom_data, [])

    @classmethod
    def from_file(cls, filename: str, ignore_checksum=False):
        with open(filename, 'rb') as infile:
            rom_bytes = infile.read()

        return cls(rom_bytes, ignore_checksum)

    def write_all_scripts_to_rom(self):
        script_dict = self.script_manager.script_dict
        for loc_id in script_dict.keys():
            if script_dict[loc_id] is not None:
                self.script_manager.write_script_to_rom(loc_id)

    def validate_ct_rom_file(filename: str) -> bool:
        with open(filename, 'rb') as infile:
            hasher = hashlib.md5()

            infile.seek(0, 2)
            file_size = infile.tell()

            if file_size == 4194816:
                print('Header detected.')
                infile.seek(0x200)

            chunk_size = 8192

            infile.seek(0)
            chunk = infile.read(chunk_size)
            while chunk:
                hasher.update(chunk)
                chunk = infile.read(chunk_size)

            # print(f"\'{filename}\' hash: {hasher.hexdigest()}")
            # print('Known good hash: a2bc447961e52fd2227baed164f729dc')
            return hasher.hexdigest() == 'a2bc447961e52fd2227baed164f729dc'

    def validate_ct_rom_bytes(rom: bytes) -> bool:
        hasher = hashlib.md5()
        # Check if this is the size of a headered ROM.
        # If it is, strip off the header before hashing.
        if len(rom) == 4194816:
            rom = rom[0x200:]

        chunk_size = 8192
        start = 0

        while start < len(rom):
            hasher.update(rom[start:start+chunk_size])
            start += chunk_size

        return hasher.hexdigest() == 'a2bc447961e52fd2227baed164f729dc'


def main():
    filename = './roms/jets_test.sfc'

    ctrom = CTRom.from_file(filename, True)
    space_manager = ctrom.rom_data.space_manager

    ctrom.rom_data.patch_ips_file('./patches/hard.ips')

    with open('./roms/jets_test_out.sfc', 'wb') as outfile:
        ctrom.rom_data.seek(0)
        outfile.write(ctrom.rom_data.read())

    quit()

    # Set up some safe free blocks.
    space_manager.mark_block((0, 0x40FFFF),
                             FSWriteType.MARK_USED)
    space_manager.mark_block((0x411007, 0x5B8000),
                             FSWriteType.MARK_FREE)

    script_manager = ctrom.script_manager
    script = script_manager.get_script(LocID.ARRIS_DOME)
    ctrom.write_script_to_rom(LocID.ARRIS_DOME)


if __name__ == '__main__':
    main()
