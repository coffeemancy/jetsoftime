from __future__ import annotations
import typing

import byteops
from ctenums import EnemyID
import ctrom

_action_lens = [
    4, 4, 6, 1, 1, 3, 1, 4, 1, 2, 3, 5, 4, 3, 1, 2, 4, 10, 16, 3,
    10, 16, 12
]


def print_bytes(data: bytes, pos: int = None, length: int = None):
    print(bytes_to_str(data, pos, length))


def bytes_to_str(data: bytes, pos: int = None, length: int = None):
    if pos is None:
        start = 0
    else:
        start = pos

    if length is None:
        end = len(data)
    else:
        end = start+length

    return ' '.join(f'{x:02X}' for x in data[start:end])


# From https://www.chronocompendium.com/Term/Enemy_AI.html
_target_str = {
    0x00: 'Nothing',
    0x01: 'All PCs',
    0x02: 'All Enemies',
    0x03: 'Self',
    0x04: 'Attacking PC',
    0x05: 'Random PC',
    0x06: 'Nearest PC',
    0x07: 'Farthest PC',
    0x08: 'PC with lowest HP',
    0x09: 'PCs with 0x1D flags set',
    0x0A: 'PCs with any negative status',
    0x0B: 'PCs with 0x1F flags set',
    0x0C: 'PCs with +Evade, Haste',
    0x0D: 'PCs with shades, specs, shield, barrier, berserk, mp regen',
    0x0E: 'Sleeping PCs',
    0x0F: 'Stopped PCs',
    0x10: 'Chaotic PCs',
    0x11: 'Shielded PCs',
    0x12: 'Barriered PCs',
    0x13: 'PCs with Unused Status 2.10',
    0x14: 'PCs with 1.08 set',
    0x15: 'Other enemies',
    0x16: 'Living enemies',
    0x17: 'Nearest enemy',
    0x18: 'Farthest enemy',
    0x19: 'Enemy with lowest HP',
    0x1A: 'Other enemies with 0x1D flags set',
    0x1B: 'All enemies with 0x1D flags set',
    0x1C: 'Other enemies with negative status',
    0x1D: 'All enemies with negative status',
    0x1E: 'Other enemies with 0x1F flags set',
    0x1F: 'All enemies with 0x1F flags set',
    0x20: 'Other sleeping enemies',
    0x21: 'Other stopped enemies',
    0x22: 'Other chaotic enemies',
    0x23: 'Other barriered enemies',
    0x24: 'Other enemies with 0x1D.02 set',
    0x25: 'Other enemies with 0x19.01 set',
    0x26: 'Other enemy with lowest HP',
    0x27: 'Enemy 03',
    0x28: 'Enemy 04',
    0x29: 'Enemy 05',
    0x2A: 'Enemy 06',
    0x2B: 'Enemy 07',
    0x2C: 'Enemy 08',
    0x2D: 'Enemy 09',
    0x2E: 'Enemy 0A',
    0x2F: 'Random enemy with $7E:AF15.80 set',
    0x30: 'PC1',
    0x31: 'PC2',
    0x32: 'PC3',
    0x33: 'Enemy 3',
    0x34: 'Enemy 4',
    0x35: 'Enemy 5',
    0x36: 'Enemy 6',
    0x37: 'PC with highest HP',
    0x38: 'Random other enemy'
}


# TODO: Avoid repeating the parsing code in every method.
#       (1) Put the script data into a higher level structure that's more
#           simple to interate through.
#       ...OR...
#       (2) Make one parsing function with hooks for other callables to be
#           called during parsing.
#       Probably (1).
class AIScript:

    def __init__(self,
                 script_bytes: bytes = b'\xFF\xFF',
                 start_pos: int = 0):
        self.uses_secondary_atk = False
        self.tech_usage = []
        self._data = None

        # Actually sets the above.  In its own function because it may need
        # to be called outside of object construction.
        self._parse_bytes(script_bytes, start_pos)

    def get_copy(self) -> AIScript:
        new_script = AIScript()
        new_script._data = bytearray(self._data)
        new_script.tech_usage = list(self.tech_usage)
        new_script.uses_secondary_atk = self.uses_secondary_atk

        return new_script

    def change_tech_usage(self, from_tech_id, to_tech_id) -> int:
        '''
        Change the tech used in the script.  Returns number of changes made.
        '''
        pos = 0
        num_changes = 0

        if from_tech_id not in self.tech_usage:
            print('Warning: tech not in self.tech_usage.')

        for block in range(2):
            while self._data[pos] != 0xFF:
                while self._data[pos] != 0xFE:  # Conditions
                    pos += 4

                pos += 1  # Skip terminal 0xFE
                while self._data[pos] != 0xFE:  # Actions
                    action_id = self._data[pos]

                    # The actual tech changing bit
                    if action_id in (2, 0x12):
                        tech_id = self._data[pos+1]
                        if tech_id == from_tech_id:
                            self._data[pos+1] = to_tech_id
                            num_changes += 1

                    if action_id == 0xFF:
                        break
                    else:
                        size = _action_lens[action_id]
                        pos += size
                pos += 1  # Skip terminal 0xFE
            pos += 1  # Skip terminal 0xFF

        if num_changes > 0 and from_tech_id not in self.tech_usage:
            print('Warning: Made changes when tech not in self.tech_usage')

        if num_changes > 0:
            if from_tech_id in self.tech_usage:
                self.tech_usage.remove(from_tech_id)
            self.tech_usage.append(to_tech_id)

        return num_changes

    def get_as_bytearray(self):
        return bytearray(self._data)

    def _parse_bytes(self, data: bytes, start_pos: int = 0):
        pos = start_pos
        tech_usage = list()
        uses_secondary_atk = False

        FE_ins_pos = []

        for block in range(2):
            while data[pos] != 0xFF:
                while data[pos] != 0xFE:  # Conditions
                    pos += 4

                pos += 1  # Skip terminal 0xFE
                while data[pos] != 0xFE:  # Actions
                    action_id = data[pos]

                    if action_id == 1 and data[pos+1] == 1:
                        uses_secondary_atk = True

                    if action_id in (2, 0x12):
                        tech_used = data[pos+1]
                        tech_usage.append(tech_used)

                    if action_id == 0xFF:
                        # insert at start so list is in reverse order
                        FE_ins_pos.insert(0, pos)
                        break
                    else:
                        size = _action_lens[action_id]
                        pos += size
                pos += 1  # Skip terminal 0xFE
            pos += 1  # Skip terminal 0xFF

        # Fix buggy ai scripts that don't have a terminal 0xFE.
        # Only 0x7F (Red Beast)
        new_data = bytearray(data[start_pos:pos])
        for ins_pos in FE_ins_pos:
            new_data.insert(ins_pos, 0xFE)

        self._data = new_data
        self.tech_usage = list(set(tech_usage))
        self.uses_secondary_atk = uses_secondary_atk

    def __len__(self):
        return len(self._data)

    def __str__(self):
        ret_str = ''
        pos = 0
        for block in range(2):

            if block == 0:
                ret_str += 'Actions:\n'
            else:
                ret_str += 'Reactions:\n'

            while self._data[pos] != 0xFF:
                while self._data[pos] != 0xFE:  # Conditions
                    ret_str += bytes_to_str(self._data[pos:pos+4])
                    ret_str += '\n'
                    pos += 4

                pos += 1  # Skip terminal 0xFE
                while self._data[pos] != 0xFE:  # Actions
                    action_id = self._data[pos]
                    if action_id == 0xFF:
                        break
                    else:
                        size = _action_lens[action_id]
                        ret_str += '\t'
                        ret_str += bytes_to_str(self._data[pos:pos+size])
                        ret_str += '\n'
                        pos += size
                pos += 1  # Skip terminal 0xFE
            pos += 1  # Skip terminal 0xFF

        return ret_str


class EnemyAIDB:
    PTR_TO_AI_PTRS = 0x01AFD7

    unused_enemies = (
        EnemyID.LAVOS_3_CENTER_UNK_0B, EnemyID.LAVOS_GIGA_GAIA_RIGHT,
        EnemyID.LAVOS_GIGA_GAIA_LEFT, EnemyID.LAVOS_SUPPORT_UNK_1F,
        EnemyID.LAVOS_SUPPORT_UNK_21, EnemyID.OCTOBINO,
        EnemyID.UNKNOWN_3C, EnemyID.UNKNOWN_44, EnemyID.UNKNOWN_5A,
        EnemyID.UNKNOWN_60, EnemyID.LAVOS_SUPPORT_UNK_67,
        EnemyID.LAVOS_SUPPORT_UNK_77, EnemyID.LAVOS_SUPPORT_UNK_78,
        EnemyID.UNKNOWN_BF, EnemyID.LAVOS_GUARDIAN, EnemyID.LAVOS_HECKRAN,
        EnemyID.LAVOS_ZOMBOR_UPPER, EnemyID.LAVOS_MASA_MUNE,
        EnemyID.LAVOS_NIZBEL, EnemyID.LAVOS_MAGUS, EnemyID.LAVOS_TANK_HEAD,
        EnemyID.LAVOS_TANK_LEFT, EnemyID.LAVOS_TANK_RIGHT,
        EnemyID.LAVOS_GUARDIAN_LEFT, EnemyID.LAVOS_GUARDIAN_RIGHT,
        EnemyID.LAVOS_ZOMBOR_BOTTOM, EnemyID.LAVOS_TYRANO_AZALA,
        EnemyID.LAVOS_TYRANO, EnemyID.LAVOS_GIGA_GAIA_HEAD,
        EnemyID.LAVOS_UNK_E8, EnemyID.LAVOS_UNK_E9, EnemyID.LAVOS_UNK_EA,
        EnemyID.JOHNNY, EnemyID.MAGUS_NO_NAME, EnemyID.UNUSED_FC,
        EnemyID.UNUSED_FD, EnemyID.UNUSED_FE, EnemyID.UNUSED_FF)

    def __init__(self, scripts: dict[EnemyID, AIScript]):

        self.scripts = {x: AIScript() for x in list(EnemyID)}
        for enemy_id in scripts:
            self.scripts[enemy_id] = scripts[enemy_id].get_copy()

        self.tech_to_enemy_usage = {x: [] for x in range(0x100)}
        self._build_tech_usage()

    def _build_tech_usage(self):
        used_enemy_ids = (x for x in self.scripts
                          if x not in self.unused_enemies)

        for enemy_id in used_enemy_ids:
            script = self.scripts[enemy_id]
            for tech in script.tech_usage:
                self.tech_to_enemy_usage[tech].append(enemy_id)

        self.unused_techs = [
            tech_id for tech_id in range(0x100)
            if not self.tech_to_enemy_usage[tech_id]
            and tech_id not in (0xFE, 0xFF)
        ]

    def change_tech_in_ai(self,
                          enemy_id: int,
                          from_tech_id: int,
                          to_tech_id: int):
        # print(f'Changing {enemy_id} tech {from_tech_id:02X} '
        #       f'to {to_tech_id:02X}')
        script = self.scripts[enemy_id]
        num_changes = script.change_tech_usage(from_tech_id, to_tech_id)

        if num_changes > 0:
            if to_tech_id in self.unused_techs:
                self.unused_techs.remove(to_tech_id)

            self.tech_to_enemy_usage[from_tech_id].remove(enemy_id)
            if enemy_id not in self.tech_to_enemy_usage[to_tech_id]:
                self.tech_to_enemy_usage[to_tech_id].append(enemy_id)

    def change_enemy_ai(self, changed_enemy_id, copied_enemy_id):
        new_script = self.scripts[copied_enemy_id].get_copy()
        orig_script = self.scripts[changed_enemy_id]

        self.scripts[changed_enemy_id] = new_script

        for tech_id in orig_script.tech_usage:
            self.tech_to_enemy_usage[tech_id].remove(changed_enemy_id)

            if not self.tech_to_enemy_usage[tech_id] \
               and tech_id not in self.unused_techs:
                self.unused_techs.append(tech_id)

        for tech_id in new_script.tech_usage:
            self.tech_to_enemy_usage[tech_id].append(changed_enemy_id)

    def get_total_length(self):
        length = 0
        for enemy_id in list(EnemyID):
            if enemy_id not in self.unused_enemies:
                length += len(self.scripts[enemy_id])

        return length

    # Note: Every script is OK except for Johnny (0xF4) which spills into the
    #       next script.  No pointers go to the same script.
    @classmethod
    def from_rom(cls, rom: bytes):
        ai_ptr_start = int.from_bytes(
            rom[cls.PTR_TO_AI_PTRS:cls.PTR_TO_AI_PTRS+3],
            'little'
        )
        ai_ptr_start = byteops.to_file_ptr(ai_ptr_start)

        scripts = dict()
        for enemy_id in list(EnemyID):
            if enemy_id not in cls.unused_enemies:
                ptr_st = ai_ptr_start + 2*enemy_id
                ptr = int.from_bytes(rom[ptr_st:ptr_st+2], 'little')
                ptr += 0x0C0000
                scripts[enemy_id] = AIScript(rom, ptr)

        return cls(scripts)

    @classmethod
    def from_ctrom(cls, ct_rom: ctrom.CTRom):
        return cls.from_rom(ct_rom.rom_data.getbuffer())

    def write_to_ctrom(self, ct_rom: ctrom.CTRom):
        # For now, we are confident that removing the unused enemies will
        # leave space for whatever we do.

        # TODO:  Write the pointers anywhere free (contiguous) in bank 0C.
        #        Write the scripts anywhere free (wherever) in bank 0C.
        rom = ct_rom.rom_data
        ai_ptr_start = int.from_bytes(
            rom.getbuffer()[self.PTR_TO_AI_PTRS:self.PTR_TO_AI_PTRS+3],
            'little'
        )
        ai_ptr_pos = byteops.to_file_ptr(ai_ptr_start)

        ai_data_pos = 0x0C8D08
        ai_data_end = 0x0CCBC9

        # This should never be an issue with the removed enemies
        write_length = self.get_total_length()
        if write_length > ai_data_end - ai_data_pos:
            print('Error: No room for AI')
            exit()

        for i in range(0x100):
            enemy_id = EnemyID(i)
            ptr = ai_data_pos & 0x00FFFF

            rom.seek(ai_ptr_pos)
            rom.write(ptr.to_bytes(2, 'little'))
            ai_ptr_pos += 2

            rom.seek(ai_data_pos)
            if enemy_id not in self.unused_enemies:
                script = self.scripts[enemy_id]
                rom.write(script.get_as_bytearray())
                ai_data_pos += len(script)
