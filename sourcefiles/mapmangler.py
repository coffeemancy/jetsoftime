from __future__ import annotations
from dataclasses import dataclass
from byteops import get_value_from_bytes, to_file_ptr, to_little_endian,\
    update_ptrs, print_bytes
from freespace import FSRom, FSWriteType


# Location Data (above):
# 360000	361BFF	DATA	N	Location Data (14 bytes each)

# Location Data	00	FF	1	Music played at location
# Location Data	01	FF	1	Tileset Layer 1 & 2
# Location Data	02	FF	1	Tile Chunks for Layer 3
# Location Data	03	FF	1	PaletteSet
#   ((PS * 0xD2) + 0x3624C0)
# Location Data	04	FF	2	Loaded map
# Location Data	06	FF	2	Ignored
# Location Data	08	FF	2	Location Events
# Location Data	0A	FF	1	Left
# Location Data	0B	FF	1	Top
# Location Data	0C	FF	1	Right
# Location Data	0D	FF	1	Bottom

@dataclass
class LocationData:
    music: int = 0
    tile_l12: int = 0
    tile_l3: int = 0
    palette: int = 0
    map_id: int = 0
    event_id: int = 0
    left: int = 0
    top: int = 0
    right: int = 0
    bottom: int = 0

    def from_rom(rom: bytearray, loc_id: int) -> LocationData:
        ptr_st = 0x360000 + loc_id*14

        music = rom[ptr_st]
        tile_l12 = rom[ptr_st+1]
        tile_l3 = rom[ptr_st+2]
        palette = rom[ptr_st+3]

        map_id = get_value_from_bytes(rom[ptr_st+4: ptr_st+6])
        # bytes 6,7 ignored
        event_id = get_value_from_bytes(rom[ptr_st+8: ptr_st+0xA])

        left = rom[ptr_st+0xA]
        top = rom[ptr_st+0xB]
        right = rom[ptr_st+0xC]
        bottom = rom[ptr_st+0xD]

        return LocationData(music, tile_l12, tile_l3, palette, map_id,
                            event_id, left, top, right, bottom)

    def to_bytearray(self) -> bytearray:
        x = bytearray([0 for i in range(14)])
        x[0] = self.music
        x[1] = self.tile_l12
        x[2] = self.tile_l3
        x[3] = self.palette
        x[4:6] = to_little_endian(self.map_id, 2)
        x[8:0xA] = to_little_endian(self.event_id, 2)
        x[0xA] = self.left
        x[0xB] = self.top
        x[0xC] = self.right
        x[0xD] = self.bottom

        return x

    def write_to_rom(self, rom: bytearray, loc_id: int):
        ptr_st = 0x360000 + loc_id*14
        rom[ptr_st:ptr_st+14] = self.to_bytearray()


# Location Exit	00	FF	1	X coord	2004.04.21
# Location Exit	01	FF	1	Y coord	2004.04.21
# Location Exit	02	7F	1	Width - 1	2004.04.22
# Location Exit	02	80	1	Vertical flag	2004.04.22
# Location Exit	03	01FF	2	Destination Location	2004.04.30
# Location Exit	04	06	1	Destination Facing	2004.04.21
# Location Exit	04	08	1	Half tile to the left of Dest exit
# Location Exit	04	10	1	Half tile above Dest exit
# Location Exit	04	E0	1	Not used	2004.04.22
# Location Exit	05	FF	1	Destination X coord	2004.04.21
# Location Exit	06	FF	1	Destination Y coord	2004.04.21

@dataclass
class LocationExit:
    x_coord: int = 0
    y_coord: int = 0
    width: int = 0
    vertical: bool = False
    dest_loc: int = 0
    dest_facing: int = 0
    half_left: bool = False
    half_top: bool = False
    dest_x: int = 0
    dest_y: int = 0

    def get_bytearray(self) -> bytearray:
        ret = bytearray([0 for x in range(7)])

        ret[0] = self.x_coord
        ret[1] = self.y_coord

        ret[2] |= 0x80*self.vertical
        ret[2] |= (self.width & 0x7F)

        ret[3:5] = to_little_endian(self.dest_loc, 2)
        ret[4] |= ((self.dest_facing & 0x3) << 1)
        ret[4] |= 0x8*self.half_left
        ret[4] |= 0x10*self.half_top
        ret[5] = self.dest_x
        ret[6] = self.dest_y

        return ret

    def from_rom(rom: bytearray, ptr: int) -> LocationExit:
        x_coord = rom[ptr]
        y_coord = rom[ptr+1]

        byte2 = rom[ptr+2]
        width = byte2 & 0x7F
        vertical = bool(byte2 & 0x80)

        dest_loc = get_value_from_bytes(rom[ptr+3:ptr+4]) & 0x1FF

        byte4 = rom[ptr+4]
        facing = byte4 & 0x06
        half_left = byte4 & 0x08
        half_top = byte4 & 0x10

        dest_x = rom[ptr+5]
        dest_y = rom[ptr+6]

        return LocationExit(x_coord, y_coord, width, vertical, dest_loc,
                            facing, half_left, half_top, dest_x, dest_y)


class LocExits:
    LOC_SIZE = 7

    def __init__(self, ptrs: list[int] = [], data: bytearray = b''):
        self.ptrs = ptrs
        self.data = data

        # should probably check for integer here...
        self.num_records = len(data) // LocExits.LOC_SIZE

    def __num_loc_exits(self, loc_id):
        return (self.ptrs[loc_id+1] - self.ptrs[loc_id]) // 7

    def add_exits(self, loc_id: int, exits: list[LocationExit]):

        new_data = b''.join(x.get_bytearray() for x in exits)

        for i in range(loc_id+1, len(self.ptrs)):
            self.ptrs[i] += len(new_data)

        ins_pt = self.ptrs[loc_id]
        self.data[ins_pt:ins_pt] = new_data[:]
        self.num_records += len(exits)

    def add_exit(self, loc_id: int, exit_data: LocationExit):
        self.add_exits(loc_id, [exit_data])

    def set_exit(self, loc_id: int, exit_id: int,
                 exit_data: bytearray):

        num_loc_exits = self.__num_loc_exits(loc_id)

        if exit_id == num_loc_exits:
            self.add_exit(loc_id, exit_data)
        elif 0 <= exit_id < num_loc_exits:
            ptr = self.ptrs[loc_id] + 7*exit_id
            self.data[ptr:ptr+7] = exit_data[:]
        else:
            print("Invalid exit id")
            exit()

    def delete_exits(self, loc_id: int):
        st = self.ptrs[loc_id]
        end = self.ptrs[loc_id+1]

        del(self.data[st:end])

        for i in range(loc_id+1, len(self.ptrs)):
            self.ptrs[i] -= (end-st)

    def get_exits(self, loc_id: int) -> list[LocationExit]:

        st = self.ptrs[loc_id]
        end = self.ptrs[loc_id+1]

        ret = []
        for x in range(st, end, 7):
            ret.append(LocationExit.from_rom(self.data, x))

        return ret

    def from_rom(fsrom: FSRom) -> LocExits:
        # get the ptr from the rom

        rom = fsrom.getbuffer()

        ptr_loc = 0x00A69E
        exit_ptr_st = get_value_from_bytes(rom[ptr_loc:ptr_loc+3])
        exit_ptr_st = to_file_ptr(exit_ptr_st)
        bank = (exit_ptr_st >> 16) << 16

        # Now read the 0x200 ptrs for the 0x1FF locations.  The last ptr is
        # just used for length calculations.
        # Loc i uses range [ptr[i], ptr[i+1])
        num_ptrs = 0x200

        exit_ptrs = []
        first = get_value_from_bytes(rom[exit_ptr_st:exit_ptr_st+2])

        for x in range(exit_ptr_st, exit_ptr_st + 2*num_ptrs, 2):
            exit_ptrs.append(get_value_from_bytes(rom[x:x+2])-first)

        data_st = exit_ptrs[0] + first + bank
        data_end = exit_ptrs[-1] + first + bank
        data = bytearray(rom[data_st:data_end])

        return LocExits(exit_ptrs, data)

    def write_to_rom(self, rom, ptr_st, data_st):
        ptr_len = len(self.ptrs*2)  # should always be 0x400
        print(f"ptr len: {ptr_len:04X}")

        data_len = len(self.data)
        print(f"data len: {data_len:04X}")

        ptr_bytes = b''.join(to_little_endian(x, 2) for x in self.ptrs)
        rom[ptr_st:ptr_st+ptr_len] = ptr_bytes[:]

        rom[data_st:data_st+data_len] = self.data[:]

    def write_to_fsrom(self, fsrom: FSRom):

        rom = fsrom.getbuffer()
        space_man = fsrom.space_manager

        # Get the existing data's bounds
        ptr_loc = 0x009CD4
        exit_ptr_st = get_value_from_bytes(rom[ptr_loc:ptr_loc+3])

        exit_ptr_st = to_file_ptr(exit_ptr_st)
        bank = (exit_ptr_st >> 16) << 16

        first_ptr = \
            get_value_from_bytes(rom[exit_ptr_st:exit_ptr_st+2]) + bank

        last_addr = exit_ptr_st + 0x1FF*2
        last_ptr = get_value_from_bytes(rom[last_addr:last_addr+2]) + bank

        num_exits = (last_ptr-first_ptr) / 7

        if not num_exits.is_integer():
            print("Error: non-integer number of records")
            exit()
        else:
            num_exits = int(num_exits)

        if num_exits >= self.num_records:
            # Can overwrite without checking with fsrom
            out_ptr_st = exit_ptr_st
            out_data_st = first_ptr

            # Free the leftovers
            if num_exits > self.num_records:
                space_man.mark_block(
                    (out_data_st+len(self.data), last_ptr),
                    FSWriteType.MARK_FREE
                )
        else:
            # Insufficient space, need a new start
            # Ptrs and data need to live in the same bank.  FS won't allow a
            # requested block to span banks but still need to test that the
            # ptr block and data block are in the same bank.

            # Free the old space
            
            space_man.mark_block(
                (exit_ptr_st, exit_ptr_st+0x400), FSWriteType.MARK_FREE
            )
            space_man.mark_block((first_ptr, first_ptr+7*num_exits),
                                 FSWriteType.MARK_FREE)
            # Get new starts
            starts = space_man.get_same_bank_free_addrs([len(self.data),
                                                         2*len(self.ptrs)])
            out_data_st = starts[0]
            out_ptr_st = starts[1]


        # delay writing until we do some tests

        ptr_offset = out_data_st % 0x10000
        ptr_bytes = b''.join(to_little_endian(x+ptr_offset, 2)
                             for x in self.ptrs)

        ptr_refs = [0x00A69E, 0x00A6A6]
        data_refs = [0x00A6B9, 0x00A6C2, 0x009CF6, 0x009D10, 0x009D1E,
                     0x009CD4, 0x009CDC, 0x009CE6, 0x009D17, 0x00A6E2]


        # [0x000000, 0x010000) must be mirrored in [0x400000, 0x410000)
        # Perhaps this can be enforced in FreeSpace?

        # The above isn't exactly true.  It might just be 0x008000 to
        # 0x010000?
        ptr_mirror = [x+0x400000 for x in ptr_refs
                      if x < 0x010000]

        data_mirror = [x+0x400000 for x in data_refs
                       if x < 0x010000]

        # Make sure that this mirroring is enforced before we alter things.
        for i, x in enumerate(ptr_refs):
            val1 = get_value_from_bytes(rom[x:x+3])

            y = ptr_mirror[i]
            val2 = get_value_from_bytes(rom[y:y+3])

            if val1 != val2:
                print(f'Error mirroring {x:06X}')
                input()

        for i, x in enumerate(data_refs):
            val1 = get_value_from_bytes(rom[x:x+3])

            y = data_mirror[i]
            val2 = get_value_from_bytes(rom[y:y+3])

            if val1 != val2:
                print(f'Error mirroring {x:06X}')
                input()

        ptr_refs += ptr_mirror
        data_refs += data_mirror

        # annoying part of dealing with getbuffer().  Have to do this or else
        # an existing MemoryView blocks writes.
        del(rom)

        fsrom.seek(out_ptr_st)
        fsrom.write(ptr_bytes, FSWriteType.MARK_USED)

        fsrom.seek(out_data_st)
        fsrom.write(self.data, FSWriteType.MARK_USED)

        # update ptrs wants both ptrs to be file ptrs.  It converts to
        # rom ptrs when writing
        update_ptrs(fsrom.getbuffer(), ptr_refs, exit_ptr_st, out_ptr_st)

        # All of the data pointers are based off of the bank.
        new_bank = (out_data_st >> 16) << 16
        update_ptrs(fsrom.getbuffer(), data_refs, bank, new_bank)
# End class LocExits


def duplicate_heckran_map(fsrom: FSRom, exits: LocExits, dup_loc_id):

    # Change the exit leading into Heckran to go to the new map
    hc_river_exits = exits.get_exits(0x31)
    alter_exit = hc_river_exits[4]
    alter_exit.dest_loc = dup_loc_id
    exits.set_exit(0x31, 4, alter_exit.get_bytearray())

    # Copy the location information (except events)
    duplicate_location_data(fsrom, 0x2F, dup_loc_id)

    # Copy the exits to the new map
    hc_passage_exits = exits.get_exits(0x2F)
    exits.delete_exits(dup_loc_id)
    exits.add_exits(dup_loc_id, hc_passage_exits)

    # Write the result
    # exits.write_to_fsrom(fsrom)


# Except for events
def duplicate_location_data(fsrom: FSRom, loc_id, dup_loc_id):
    # I think all you have to do is change the LocationData and update the
    # exits?
    orig_data = LocationData.from_rom(fsrom.getbuffer(), loc_id)
    dup_data = LocationData.from_rom(fsrom.getbuffer(), dup_loc_id)
    orig_data.event_id = dup_data.event_id
    orig_data.write_to_rom(fsrom.getbuffer(), dup_loc_id)


def main():
    with open('jets_test.sfc', 'rb') as infile:
        rom = bytearray(infile.read())

    fsrom = FS(rom, False)
    fsrom.mark_block((0x41107C, 0x4F0000), True)
    fsrom.mark_block((0x4F2100, 0x5B8000), True)
    fsrom.mark_block((0x5B80C8, 0x5DBB68), True)
    fsrom.mark_block((0x5DBB85, 0x5F0000), True)

    exits = LocExits.from_rom(fsrom)

    duplicate_heckran_map(fsrom, exits, 0xC0)
    exits.write_to_fsrom(fsrom)

    with open('jets_test_out.sfc', 'wb') as outfile:
        fsrom.seek(0)
        outfile.write(fsrom.read())


if __name__ == '__main__':
    main()
