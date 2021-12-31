from __future__ import annotations
from dataclasses import dataclass
from io import BufferedRWPair

from byteops import get_value_from_bytes, to_little_endian
import ctstrings
import ctenums


@dataclass
class EnemyStats:
    hp: int = 0
    level: int = 0
    speed: int = 0
    magic: int = 0
    mdef: int = 0
    offense: int = 0
    defense: int = 0
    # rewards
    xp: int = 0
    gp: int = 0
    drop_item: ctenums.ItemID = ctenums.ItemID.MOP
    charm_item: ctenums.ItemID = ctenums.ItemID.MOP
    tp: int = 0

    # There are more special flags, but I'm ignoring them for now
    can_sightscope: bool = False

    name: str = 'Nu'

    def __str__(self):
        ret = ''
        stats = [str.rjust(str(x), 3)
                 for x in [self.speed, self.offense, self.defense,
                           self.magic, self.mdef]]
        stat_string = ' '.join(x for x in stats)
        ret += (f"Name: {self.name}\n"
                f"HP = {self.hp}\tLevel = {self.level}\n"
                f"XP = {self.xp}\tTP = {self.tp}\tGP = {self.gp}\n"
                "Spd Off Def Mag Mdf\n" +
                stat_string + '\n'
                f"Drop = {self.drop_item}\n"
                f"Charm = {self.charm_item}")

        return ret

    # bossscaler.py uses lists of stats to do the scaling.  This method takes
    # one of those lists and replaces the relevant stats in the class.
    def replace_from_stat_list(self, stat_list: list[int]):
        # stat list order is hp, lvl, mag, mdf, off, def, xp, gp, tp

        # Some records have missing stats at the end.  Pad with ""
        missing_stat_count = 9-len(stat_list)
        stat_list.extend([""]*missing_stat_count)

        cur_stats = [self.hp, self.level, self.magic, self.mdef, self.offense,
                     self.defense, self.xp, self.gp, self.tp]

        new_stats = [stat_list[i] if stat_list[i] != "" else cur_stats[i]
                     for i in range(len(cur_stats))]

        [
            self.hp, self.level, self.magic, self.mdef, self.offense,
            self.defense, self.xp, self.gp, self.tp
        ] = new_stats[:]

    def from_rom(rom: bytearray, enemy_id: int):
        # enemy stat data is a 23 byte structure beginning at 0x0C4700
        stat_addr = 0x0C4700 + 23*enemy_id

        hp = get_value_from_bytes(rom[stat_addr:stat_addr+2])
        level = rom[stat_addr+2]
        speed = rom[stat_addr+9]
        magic = rom[stat_addr+0xA]
        mdef = rom[stat_addr+0xD]
        offense = rom[stat_addr+0xE]
        defense = rom[stat_addr+0xF]

        can_sightscope = not bool(rom[stat_addr+0x15] & 0x2)

        # enemy rewards data is a 7 byte structure beginning at 0x0C5E00
        reward_addr = 0x0C5E00 + 7*enemy_id

        xp = get_value_from_bytes(rom[reward_addr:reward_addr+2])
        gp = get_value_from_bytes(rom[reward_addr+2:reward_addr+4])
        drop_item = ctenums.ItemID(rom[reward_addr+4])
        charm_item = ctenums.ItemID(rom[reward_addr+5])
        tp = rom[reward_addr+6]

        # enemy name starts at 0x0C6500
        # TODO: read pointer from rom
        name_start = 0x0C6500
        name_b = rom[name_start+enemy_id*11:name_start+(enemy_id+1)*11]
        name = ctstrings.CTString.ct_bytes_to_ascii(name_b)

        return EnemyStats(hp, level, speed, magic, mdef, offense, defense,
                          xp, gp, drop_item, charm_item, tp, can_sightscope,
                          name)


    # The stream will just about always be a BytesIO from CTRom.
    # Since we don't have all of the extra flags in EnemyStats, we need
    # to read and modify the flags, hence BufferedRWPair.
    def write_to_stream(self, stream: BufferedRWPair, enemy_id: int):
        # enemy stat data is a 23 byte structure beginning at 0x0C4700
        stat_addr = 0x0C4700 + 23*enemy_id

        stream.seek(stat_addr)
        stream.write(to_little_endian(self.hp, 2))

        stream.write(to_little_endian(self.level, 1))

        stream.seek(stat_addr+9)
        stream.write(to_little_endian(self.speed, 1))
        stream.write(to_little_endian(self.magic, 1))

        stream.seek(stat_addr+0xD)
        stream.write(to_little_endian(self.mdef, 1))
        stream.write(to_little_endian(self.offense, 1))
        stream.write(to_little_endian(self.defense, 1))

        stream.seek(stat_addr + 0x15)
        flags = stream.read()[0]
        # 0x02 is the "sightscope fails" flag.
        if self.can_sightscope:
            flags &= 0xFD  # Unset the flag

            # The name/hp doesn't show up unless the following is set to 0.
            stream.seek(0x21DE80+enemy_id)
            stream.write(b'\x00')
        else:
            flags |= 0x02

        stream.seek(stat_addr + 0x15)
        stream.write(bytes([flags]))

        # enemy rewards data is a 7 byte structure beginning at 0x0C5E00
        reward_addr = 0x0C5E00 + 7*enemy_id

        stream.seek(reward_addr)
        stream.write(to_little_endian(self.xp, 2))
        stream.write(to_little_endian(self.xp, 2))
        stream.write(to_little_endian(self.drop_item, 1))
        stream.write(to_little_endian(self.charm_item, 1))
        stream.write(to_little_endian(self.tp, 1))

        # I'm going to skip writing the name out for now.
        # We shouldn't be changing those, right?


def get_stat_dict(rom: bytearray) -> dict[ctenums.EnemyID,
                                          ctenums.EnemyID:EnemyStats]:

    EnemyID = ctenums.EnemyID
    stat_dict = dict()
    for enemy_id in list(EnemyID):
        # print(f"{int(enemy_id):02X}: {enemy_id}")
        stat_dict[enemy_id] = EnemyStats.from_rom(rom, enemy_id)

    return stat_dict


def main():

    with open('./roms/jets_test.sfc', 'rb') as infile:
        rom = infile.read()

    # Grab the original stats from the rom.
    EnemyID = ctenums.EnemyID
    left_arm = EnemyStats.from_rom(rom, EnemyID.GIGA_GAIA_LEFT)
    right_arm = EnemyStats.from_rom(rom, EnemyID.GIGA_GAIA_RIGHT)
    head = EnemyStats.from_rom(rom, EnemyID.GIGA_GAIA_HEAD)

    # So you can see the original stats
    print('Original:')
    print(left_arm)
    print(right_arm)
    print(head)

    # Do whatever with stats here.
    # Do not exceed 255 for most stats.
    # HP should not exceed 32k or so I think.
    # Do not exceed 16 speed.

    left_arm.magic = 100
    left_arm.hp = 10000

    right_arm.magic = 255

    # You need w+b because EnemyStats doesn't handle all flags
    with open('./roms/jets_test_out.sfc', 'w+b') as outfile:
        outfile.write(rom)
        left_arm.write_to_stream(outfile, EnemyID.GIGA_GAIA_LEFT)
        right_arm.write_to_stream(outfile, EnemyID.GIGA_GAIA_RIGHT)
        head.write_to_stream(outfile, EnemyID.GIGA_GAIA_HEAD)

        outfile.seek(0)
        rom = outfile.read()

    # Test to make sure it worked
    left_arm = EnemyStats.from_rom(rom, EnemyID.GIGA_GAIA_LEFT)
    right_arm = EnemyStats.from_rom(rom, EnemyID.GIGA_GAIA_RIGHT)
    head = EnemyStats.from_rom(rom, EnemyID.GIGA_GAIA_HEAD)

    # So you can see the original stats
    print('Altered:')
    print(left_arm)
    print(right_arm)
    print(head)


if __name__ == '__main__':
    main()
