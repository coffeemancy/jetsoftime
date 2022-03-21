from __future__ import annotations
import ctrom

_action_lens = [
    4, 4, 6, 1, 1, 3, 1, 4, 1, 2, 3, 5, 4, 3, 1, 2, 4, 10, 16, 3,
    10, 16, 12
]

def print_bytes(data: bytes, pos: int = None, length: int = None):

    if pos is None:
        start = 0
    else:
        start = pos

    if length is None:
        end = len(data)
    else:
        end = start+length

    print(' '.join(f'{x:02X}' for x in data[start:end]))

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

# Very limited initial form.
# The only functionality that we need right now is to change tech usage.
# Printing out AI scripts might be useful too.
class EnemyAIDB:

    def __init__(self, ptrs: list[int], ai_data: bytes):
        self.ptrs = list(ptrs)
        self._orig_ptrs = list(ptrs)  # May need for swapping enemies

        self.data = ai_data

        self.tech_to_enemy_usage = {x: [] for x in range(0x100)}
        self.enemy_to_tech_usage = {x: [] for x in range(0x100)}
        self.enemy_atk_usage = {x: [] for x in range(0x100)}
        self.unused_techs = []
        self._build_tech_usage()

    def _build_tech_usage(self):

        for enemy_id in range(0x100):

            # print(enemy_id)
            pos = self.ptrs[enemy_id]
            # See comments in change_tech_in_ai
            for block in range(2):
                # print('Block', block)
                while self.data[pos] != 0xFF:  # Conditions
                    while self.data[pos] != 0xFE:
                        pos += 4

                    pos += 1  # Skip terminal 0xFE
                    while self.data[pos] != 0xFE:  # Actions
                        action_id = self.data[pos]
                        tech_pos = None
                        if action_id == 2:
                            # Use Tech action, tech_id in byte 1
                            tech_pos = pos+1
                        elif action_id == 0x12:
                            # Use Tech and change stats, tech_id in byte 1 too
                            tech_pos = pos+1

                        if tech_pos is not None:
                            tech_id = self.data[tech_pos]
                            self.enemy_to_tech_usage[enemy_id].append(tech_id)
                            self.tech_to_enemy_usage[tech_id].append(enemy_id)

                        if action_id == 1:
                            atk_index = self.data[pos+1]
                            if atk_index not in self.enemy_atk_usage[enemy_id]:
                                self.enemy_atk_usage[enemy_id].append(
                                    atk_index)

                        if action_id == 0xFF:
                            break
                        else:
                            pos += _action_lens[action_id]
                    pos += 1  # Skip terminal 0xFE
                pos += 1  # Skip terminal 0xFF

        # Remove duplicates in the dicts
        for enemy in self.enemy_to_tech_usage:
            self.enemy_to_tech_usage[enemy] = \
                list(set(self.enemy_to_tech_usage[enemy]))

        for tech in self.tech_to_enemy_usage:
            self.tech_to_enemy_usage[tech] = \
                list(set(self.tech_to_enemy_usage[tech]))

        self.unused_techs = [tech for tech in self.tech_to_enemy_usage
                             if not self.tech_to_enemy_usage[tech]
                             and tech not in (0xFF, 0xFE)]

        # print(self.unused_techs)

    # Uses original pointers to avoid circular swap issues.
    def change_enemy_ai(self, enemy_id, to_orig_enemy_id):
        self.ptrs[enemy_id] = self._orig_ptrs[to_orig_enemy_id]

        # Update Tech Usage
        techs_used = self.enemy_to_tech_usage[enemy_id]
        for tech in techs_used:
            self.tech_to_enemy_usage[tech].remove(enemy_id)

        techs_used_to = self.enemy_to_tech_usage[to_orig_enemy_id]
        for tech in techs_used_to:
            self.tech_to_enemy_usage[tech].append(enemy_id)

        self.enemy_to_tech_usage[enemy_id] = \
            list(self.enemy_to_tech_usage[to_orig_enemy_id])

        self.enemy_atk_usage = \
            list(self.enemy_atk_usage[to_orig_enemy_id])

    def change_tech_in_ai(self,
                          enemy_id: int,
                          from_tech_id: int,
                          to_tech_id: int):

        pos = self.ptrs[enemy_id]

        made_update = False
        # Action/Reaction block are identical.
        for block in range(2):
            # Block terminates with a 0xFF
            while self.data[pos] != 0xFF:

                # Skip through the conditions
                while self.data[pos] != 0xFE:
                    # Read the condition and do something, if desired
                    # Conditions are all 4 bytes
                    pos += 4

                # Skip past the 0xFE that terminates the condition block
                pos += 1

                # Read through the actions
                while self.data[pos] != 0xFE:
                    action_id = self.data[pos]
                    tech_pos = None
                    if action_id == 2:
                        # Use Tech action, tech_id in byte 1
                        tech_pos = pos+1
                    elif action_id == 0x12:
                        # Use Tech and change stats, tech_id in byte 1 too
                        tech_pos = pos+1

                    if tech_pos is not None:
                        tech_id = self.data[tech_pos]
                        if tech_id == from_tech_id:
                            made_update = True
                            self.data[tech_pos] = to_tech_id
                    # Bug: Some blocks are FF terminated instead of FE FF
                    if action_id == 0xFF:
                        break
                    else:
                        pos += _action_lens[action_id]
                pos += 1  # Skip terminal 0xFE
            pos += 1  # Skip terminal 0xFF

        if made_update:
            # Now update the usage information
            if to_tech_id in self.unused_techs:
                self.unused_techs.remove(to_tech_id)

            self.tech_to_enemy_usage[from_tech_id].remove(enemy_id)
            if enemy_id not in self.tech_to_enemy_usage[to_tech_id]:
                self.tech_to_enemy_usage[to_tech_id].append(enemy_id)
            self.enemy_to_tech_usage[enemy_id].remove(from_tech_id)

            if from_tech_id not in self.enemy_to_tech_usage[enemy_id]:
                self.enemy_to_tech_usage[enemy_id].append(from_tech_id)

    def get_ai_script(self, enemy_id: int):
        pos = self.ptrs[enemy_id]
        for block in range(2):
            if block == 0:
                print('Actions:')
            else:
                print('Reactions:')

            while self.data[pos] != 0xFF:  # Conditions
                while self.data[pos] != 0xFE:
                    print_bytes(self.data[pos:pos+4])
                    pos += 4

                pos += 1  # Skip terminal 0xFE
                while self.data[pos] != 0xFE:  # Actions
                    action_id = self.data[pos]

                    if action_id == 0xFF:
                        break
                    else:
                        size = _action_lens[action_id]
                        print('\t', end ='')
                        print_bytes(self.data[pos:pos+size])
                        pos += size
                pos += 1  # Skip terminal 0xFE
            pos += 1  # Skip terminal 0xFF


    @classmethod
    def from_rom(cls, rom: bytes) -> EnemyAIDB:
        ptr_bytes = bytes(rom[0x0C8B08:0x0C8D08])

        ptrs = [
            int.from_bytes(ptr_bytes[x:x+2], 'little') - 0x8D08
            for x in range(0, len(ptr_bytes), 2)
        ]

        # print(' '.join(f'{x:04X}' for x in ptrs))
        # print(len(ptrs))
        # input(f'{ptrs[127]:04X}')

        ai_data = bytearray(rom[0x0C8D08:0x0CCBC9])
        # print(f'{len(ai_data):04X}')

        return EnemyAIDB(ptrs, ai_data)

    @classmethod
    def from_ctrom(cls, ct_rom: ctrom.CTRom):
        return cls.from_rom(ct_rom.rom_data.getbuffer())

    def write_to_ctrom(self, ct_rom: ctrom.CTRom):
        rom = ct_rom.rom_data
        rom.seek(0x0C8B08)

        ptr_bytes = b''.join(int.to_bytes(x+0x8D08, 2, 'little')
                             for x in self.ptrs)
        rom.write(ptr_bytes)

        rom.seek(0x0C8D08)
        rom.write(self.data)
