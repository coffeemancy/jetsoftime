from __future__ import annotations

import ctenums
import ctrom
import ctstrings


class EnemySpriteData:
    def __init__(self, data: bytes):
        if len(data) != 10:
            print('Error: Sprite data must be 10 bytes')

        self._data = bytearray(data)

    def get_as_bytearray(self) -> bytearray:
        return bytearray(self._data)

    def get_copy(self) -> EnemySpriteData:
        return EnemySpriteData(self._data)

    def set_affect_layer_1(self, affects_layer_1: bool):
        if affects_layer_1:
            self._data[4] |= 0x04
        else:
            self._data[4] &= 0xFB

    def set_sprite_to_pc(self, pc: ctenums.CharID):
        for ind in range(4):
            self._data[ind] = int(pc)

    @classmethod
    def from_rom(cls, rom: bytes, enemy_id: int):
        sprite_st = 0x24F600 + 10*enemy_id
        data = bytes(rom[sprite_st:sprite_st+10])

        return cls(data)

    def write_to_rom(self, rom: bytearray, enemy_id: int):
        sprite_st = 0x24F600 + 10*enemy_id
        rom[sprite_st:sprite_st+10] = self._data

    def write_to_ctrom(self, ct_rom: ctrom.CTRom, enemy_id):
        self.write_to_rom(ct_rom.rom_data.getbuffer(), enemy_id)

    def __str__(self):
        ret_str = self.__class__.__name__
        ret_str += ': '
        ret_str += ' '.join(f'{x:02X}' for x in self._data)


class EnemyStats:
    element_offsets = {
        ctenums.Element.LIGHTNING: 0,
        ctenums.Element.SHADOW: 1,
        ctenums.Element.ICE: 2,
        ctenums.Element.FIRE: 3
    }

    MAX_HP = 0x7FFF
    MAX_LEVEL = 0xFF
    MAX_MAGIC = 0xFF
    MAX_HIT = 100
    MAX_EVADE = 100
    MAX_DEFENSE = 0xFF
    MAX_OFFENSE = 0xFF
    MAX_XP = 0x7FFF
    MAX_TP = 0xFF
    MAX_GP = 0x7FFF

    def __init__(self,
                 stat_data: bytes = None,
                 name_bytes: bytes = None,
                 reward_bytes: bytes = None,
                 sprite_bytes: bytes = None,
                 hide_name: bool = False):
        # Just to list the actual class members in one place
        self._stat_data = None
        self._name_bytes = None
        self._reward_data = None
        self._sprite_data = None
        self.hide_name = hide_name

        if stat_data is None:
            stat_data = bytes([0 for i in range(0x17)])

        if name_bytes is None:
            name_bytes = ctstrings.CTString.from_str('No Name')
        else:
            name_bytes = ctstrings.CTString(name_bytes)

        if reward_bytes is None:
            reward_bytes = bytes([0 for i in range(7)])

        if sprite_bytes is None:
            sprite_bytes = bytes([0 for i in range(10)])

        self._set_stats(stat_data)
        self._set_name(name_bytes)
        self._set_rewards(reward_bytes)
        self.sprite_data = EnemySpriteData(sprite_bytes)

    def _jot_json(self):
        return {
            'hp': self.hp,
            'level': self.level,
            'speed': self.speed,
            'magic': self.magic,
            'mdef': self.mdef,
            'offense': self.offense,
            'defense': self.defense,
            'xp': self.xp,
            'gp': self.gp,
            'drop_item': str(self.drop_item),
            'charm_item': str(self.charm_item),
            'tp': self.tp,
            'can_sightscope': self.can_sightscope,
            'name': self.name.strip()
        }

    def __str__(self, item_db = None):
        ret = ''
        stats = [str.rjust(str(x), 3)
                 for x in [self.speed, self.offense, self.defense,
                           self.magic, self.mdef, self.hit, self.evade]]
        stat_string = ' '.join(x for x in stats)

        if item_db is None:
            drop_str = str(self.drop_item)
            charm_str = str(self.charm_item)
        else:
            drop_str = item_db[self.drop_item].get_name_as_str(True)
            charm_str = item_db[self.charm_item].get_name_as_str(True)

        ret += (f"Name: {self.name}\n"
                f"HP = {self.hp}\tLevel = {self.level}\n"
                f"XP = {self.xp}\tTP = {self.tp}\tGP = {self.gp}\n"
                f"Drop = {drop_str}\t"
                f"Charm = {charm_str}\n"
                "Spd Off Def Mag Mdf Hit Evd\n" +
                stat_string + '\n')

        Elem = ctenums.Element
        resists = [self.get_resistance(Elem.LIGHTNING),
                   self.get_resistance(Elem.SHADOW),
                   self.get_resistance(Elem.ICE),
                   self.get_resistance(Elem.FIRE)]

        for ind, x in enumerate(resists):
            sign = 1 - 2*(x > 127)
            mag = x & 0x7F
            if mag > 0:
                mag = 400 / (x & 0x7F)
            else:
                mag = 0
            val = sign*mag
            resists[ind] = f'{val:3.0f}'

        res_str = ' '.join(str.rjust(str(x), 4) for x in resists)

        ret += 'Elemental Resistances:\n'
        ret += (' Lit  Shd  Ice  Fir\n' + res_str + '\n')
        ret += (f'Hide name: {self.hide_name}')

        # Don't bother printing sprite data.

        return ret

    def get_copy(self) -> EnemyStats:
        return EnemyStats(self._stat_data, self._name_bytes,
                          self._reward_data,
                          self.sprite_data.get_as_bytearray(),
                          self.hide_name)

    @classmethod
    def from_rom(cls, rom: bytearray, enemy_id: ctenums.EnemyID):
        data_st = 0x0C4700 + 0x17*enemy_id
        data = bytes(rom[data_st:data_st+0x17])

        name_st = 0x0C6500 + 0xB*enemy_id
        name = bytes(rom[name_st:name_st+0xB])

        rewards_st = 0x0C5E00 + 7*enemy_id
        rewards = bytes(rom[rewards_st: rewards_st+7])

        hide_name_st = 0x21DE80+enemy_id
        hide_name = bool(rom[hide_name_st])

        sprite_data = EnemySpriteData.from_rom(rom, enemy_id)
        sprite_bytes = sprite_data.get_as_bytearray()

        return EnemyStats(data, name, rewards, sprite_bytes, hide_name)

    @classmethod
    def from_ctrom(cls, ct_rom: ctrom.CTRom, enemy_id: ctenums.EnemyID):
        return cls.from_rom(ct_rom.rom_data.getbuffer(), enemy_id)

    def write_to_ctrom(self, ct_rom: ctrom.CTRom, enemy_id: ctenums.EnemyID):
        ct_rom.rom_data.seek(0x0C4700 + 0x17*enemy_id)
        ct_rom.rom_data.write(self._stat_data)

        ct_rom.rom_data.seek(0x0C6500 + 0xB*enemy_id)
        ct_rom.rom_data.write(self._name_bytes)

        ct_rom.rom_data.seek(0x0C5E00 + 7*enemy_id)
        ct_rom.rom_data.write(self._reward_data)

        self.sprite_data.write_to_ctrom(ct_rom, enemy_id)

        ct_rom.rom_data.seek(0x21DE80+enemy_id)
        ct_rom.rom_data.write(self.hide_name.to_bytes(1, 'little'))

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

    def _set_stats(self, stat_bytes: bytes):
        if len(stat_bytes) != 0x17:
            print('Error: stat data must be exactly 17 bytes')
            exit()

        self._stat_data = bytearray(stat_bytes)

    def _set_name(self, name_bytes: ctstrings.CTString):
        if len(name_bytes) < 0xB:
            slack = 0xB - len(name_bytes)
            name_bytes.extend(bytearray([0xEF]*slack))
        elif len(name_bytes) > 0xB:
            # Truncate long names instead of erroring
            name_bytes = name_bytes[0:0xB]

        self._name_bytes = name_bytes

    def _set_rewards(self, reward_bytes: bytes):
        if len(reward_bytes) != 7:
            print('Error: reward data must be exactly 7 bytes')
            exit()

        self._reward_data = bytearray(reward_bytes)

    # Property for getting/setting name
    @property
    def name(self) -> str:
        return self._name_bytes.to_ascii()

    @name.setter
    def name(self, string):
        ct_string = ctstrings.CTString.from_str(string)
        self._set_name(ct_string)

    # Properties for getting/setting stats
    @property
    def hp(self):
        return int.from_bytes(self._stat_data[0:2], 'little')

    @hp.setter
    def hp(self, val: int):
        self._stat_data[0:2] = val.to_bytes(2, 'little')

    @property
    def level(self):
        return int(self._stat_data[2])

    @level.setter
    def level(self, val: int):
        self._stat_data[2] = val

    def get_is_immune(self, status: ctenums.StatusEffect):
        return bool(self._stat_data[4] & int(status))

    def set_is_immune(self, status: ctenums.StatusEffect, is_immune: bool):
        if is_immune:
            self._stat_data[4] |= int(status)
        else:
            self._stat_data[4] &= 0xFF ^ int(status)

    @property
    def stamina(self):
        return int(self._stat_data[8])

    @stamina.setter
    def stamina(self, value: int):
        self._stat_data[8] = value

    @property
    def speed(self):
        return int(self._stat_data[9])

    @speed.setter
    def speed(self, value: int):
        self._stat_data[9] = value

    @property
    def magic(self):
        return int(self._stat_data[0xA])

    @magic.setter
    def magic(self, value: int):
        self._stat_data[0xA] = value

    @property
    def hit(self):
        return int(self._stat_data[0xB])

    @hit.setter
    def hit(self, value: int):
        self._stat_data[0xB] = value

    @property
    def evade(self):
        return int(self._stat_data[0xC])

    @evade.setter
    def evade(self, value: int):
        self._stat_data[0xC] = min(value, 100)

    @property
    def mdef(self):
        return int(self._stat_data[0xD])

    @mdef.setter
    def mdef(self, value: int):
        self._stat_data[0xD] = min(value, 100)

    @property
    def offense(self):
        return int(self._stat_data[0xE])

    @offense.setter
    def offense(self, value: int):
        self._stat_data[0xE] = min(value, 0xFF)

    @property
    def defense(self):
        return int(self._stat_data[0xF])

    @defense.setter
    def defense(self, value: int):
        self._stat_data[0xF] = min(value, 0xFF)

    def get_resistance(self, element: ctenums.Element):
        offset = 0x10 + self.element_offsets[element]
        return self._stat_data[offset]

    def set_resistance(self, element: ctenums.Element, value):
        offset = 0x10 + self.element_offsets[element]
        self._stat_data[offset] = value

    # confusing becaues data[0x15] & 0x02 is the sightscope fails flag
    @property
    def can_sightscope(self):
        sightscope_fails = self._stat_data[0x15] & 0x02
        return not sightscope_fails

    @can_sightscope.setter
    def can_sightscope(self, val: bool):
        if val:
            self._stat_data[0x15] &= 0xFD
            self.hide_name = False
        else:
            self._stat_data[0x15] &= 0x02

    @property
    def immune_rock_throw(self):
        return bool(self._stat_data[0x14] & 0x40)

    @immune_rock_throw.setter
    def immune_rock_throw(self, val: bool):
        mask = 0xFF - 0x40
        self._stat_data[0x14] &= mask
        self._stat_data[0x14] |= (0x40 * val)

    @property
    def immune_slurp_cut(self):
        return bool(self._stat_data[0x14] & 0x20)

    @immune_slurp_cut.setter
    def immune_slurp_cut(self, val: bool):
        mask = 0xFF - 0x20
        self._stat_data[0x14] &= mask
        self._stat_data[0x14] |= (0x20 * val)

    # Properties for getting/setting rewards
    @property
    def xp(self):
        return int.from_bytes(self._reward_data[0:2], 'little')

    @xp.setter
    def xp(self, val: int):
        self._reward_data[0:2] = val.to_bytes(2, 'little')

    @property
    def gp(self):
        return int.from_bytes(self._reward_data[2:4], 'little')

    @gp.setter
    def gp(self, val: int):
        self._reward_data[2:4] = val.to_bytes(2, 'little')

    @property
    def drop_item(self):
        return ctenums.ItemID(self._reward_data[4])

    @drop_item.setter
    def drop_item(self, val: ctenums.ItemID):
        self._reward_data[4] = val

    @property
    def charm_item(self):
        return ctenums.ItemID(self._reward_data[5])

    @charm_item.setter
    def charm_item(self, val: ctenums.ItemID):
        self._reward_data[5] = val

    @property
    def tp(self):
        return int(self._reward_data[6])

    @tp.setter
    def tp(self, val: int):
        self._reward_data[6] = val

    @property
    def secondary_attack_id(self):
        return self._stat_data[0x16]

    @secondary_attack_id.setter
    def secondary_attack_id(self, val):
        self._stat_data[0x16] = val


def get_stat_dict(rom: bytearray) -> dict[ctenums.EnemyID, EnemyStats]:
    stat_dict = dict()
    ct_rom = ctrom.CTRom(rom, True)

    for enemy_id in list(ctenums.EnemyID):
        stat_dict[enemy_id] = EnemyStats.from_ctrom(ct_rom, enemy_id)

    return stat_dict


if __name__ == '__main__':
    pass
    # Byte 0,1 - hp
    # Byte 2 - level
    # Byte 3 - constant statuses
    # Byte 4 - status immunities
    # Byte 5 - unused 0x05
    # Byte 6 - constant statuses 2
    # Byte 7 - constant statuses 3
    # Byte 8 - stamina (only used for ai conditions)
    # Byte 9 - speed
    # Byte 0xA - magic
    # Byte 0xB - hit
    # Byte 0xC - evade
    # Byte 0xD - mdef
    # Byte 0xE - offense
    # Byte 0xF - defense
    # Byte 0x10 - lit resist
    # Byte 0x11 - shadow resist
    # Byte 0x12 - water resist
    # Byte 0x13 - fire resist
    # Byte 0x14 - tech immunities
    # Byte 0x15 - special flags and types
    # Byte 0x16 - Attack 2 index
