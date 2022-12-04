from __future__ import annotations

import typing

import byteops
import ctenums
import ctrom
import ctstrings

from cttypes import BinaryData, BinaryData, byte_prop, bytes_prop

class DamageFormula(ctenums.StrIntEnum):
    NONE = 0
    PC_MELEE = 1
    PC_RANGED = 2
    MAGIC = 3
    ENEMY_PHYS = 4
    PC_AYLA = 5
    MISSING_HP = 6
    UNKNOWN_07 = 7
    UNKNOWN_08 = 8
    UNKNOWN_09 = 9
    UNKNOWN_0A = 0xA


class EffectMod(ctenums.StrIntEnum):
    NONE = 0x00
    CRIT_X2 = 0x01
    WONDERSHOT = 0x02
    DMG_125 = 0x03
    DMG_150 = 0x04
    DMG_175 = 0x05
    DMG_200 = 0x06
    MAGIC = 0x07
    DMG_MAG_125 = 0x08
    DMG_MAG_150 = 0x09
    DMG_MAG_175 = 0x0A
    DMG_MAG_200 = 0x0B
    DMG_TO_MAG_150 = 0x0C
    DMG_TO_MAG_200 = 0x0D
    HP_TO_1 = 0x0E
    CHARM_80 = 0x0F
    CHARM_100 = 0x10
    CLEAR_STATUS = 0x11
    DMG_33 = 0x13
    DMG_25 = 0x14
    SLEEP_80_AQUA = 0x15
    DOOMSICKLE = 0x16
    HP_50_50 = 0x18
    CRISIS = 0x19
    HP_50_100 = 0x1E
    ATTACKER_DIES = 0x23
    DEATH_40 = 0x24
    DEATH_100 = 0x25
    STOP_60 = 0x26
    SLOW_60 = 0x27
    STOP_80_MACHINES = 0x28
    CHAOS_60 = 0x29
    CHAOS_80 = 0x2E
    CRIT_4X = 0x2F
    CLEAR_SHIELD_BARRIER = 0x30
    DMG_400 = 0x34
    CLEAR_IMMUNITY = 0x35
    RANDOM_STATUS = 0x36
    SLEEP = 0x37
    CRIT_9999 = 0x38


class EffectType(ctenums.StrIntEnum):
    HEALING = 0
    HEALSTATUS = 1
    STATUS = 2
    DAMAGE = 3
    STEAL = 6
    MULTIHIT = 8


class ControlHeader(BinaryData):
    '''
    A class for representing a tech's control header.
    '''
    SIZE = 0xB

    is_physical = byte_prop(3, 0x04, ret_type=bool)
    is_magical = byte_prop(3, 0x02, ret_type=bool)
    
    @classmethod
    def verify_effect_num(cls, eff_num: int):
        if not 0 <= eff_num < 3:
            raise ValueError('Effect index must be in range(0, 3).')

    def get_effect_index(self, eff_num: int):
        self.verify_effect_num(eff_num)
        return self[5+eff_num]

    def set_effect_index(self, eff_num: int, new_index: int):
        self.verify_effect_num(eff_num)
        self[5+eff_num] = new_index

    def get_effect_mod(self, eff_num: int) -> EffectMod:
        self.verify_effect_num(eff_num)
        return EffectMod(self[8+eff_num])

    def set_effect_mod(self, eff_num: int, eff_mod: EffectMod):
        self.verify_effect_num(eff_num)
        self[8+eff_num] = eff_mod

    @property
    def element(self):
        elem_byte = self[3]
        elem_byte &= 0xF0

        if bin(elem_byte).count('1') > 1:
            raise ValueError('A tech can only have one element set.')
        elif bin(elem_byte).count('1') == 0:
            return ctenums.Element.NONELEMENTAL
        elif elem_byte & 0x80:
            return ctenums.Element.LIGHTNING
        elif elem_byte & 0x40:
            return ctenums.Element.SHADOW
        elif elem_byte & 0x20:
            return ctenums.Element.ICE
        elif elem_byte & 0x10:
            return ctenums.Element.FIRE

    @element.setter
    def element(self, value: ctenums.Element):
        self[3] &= 0x0F

        if value == ctenums.Element.LIGHTNING:
            self[3] |= 0x80
        elif value == ctenums.Element.SHADOW:
            self[3] |= 0x40
        elif value == ctenums.Element.ICE:
            self[3] |= 0x20
        elif value == ctenums.Element.FIRE:
            self[3] |= 0x10


class PCTechControlHeader(ControlHeader):
    
    @classmethod
    def from_rom(cls: typing.Type[T], rom: bytes, record_id: int) -> T:
        data_st = int.from_bytes(rom[0x01CBA1:0x01CBA1+3], 'little')
        data_st = byteops.to_file_ptr(data_st)
        record_st = data_st + record_id*cls.SIZE

        return cls(rom, record_st)

    # PC control headers have special behavior for effect indices.
    # If the 0x80 bit of the index is set, then the effect is ignored and only
    # the mp value of the effect is used when computing costs.
    def get_effect_index(self, eff_num: int):
        effect_index = ControlHeader.get_effect_index(self, eff_num)
        return effect_index & 0x7F

    def set_effect_index(self, eff_num, new_index: int):

        if not 0 <= new_index < 0x80:
            raise ValueError('Effect index must be in range(0x80)')

        effect_index = ControlHeader.get_effect_index(self, eff_num)
        effect_index &= 0x80
        effect_index |= new_index

        ControlHeader.set_effect_index(self, eff_num, effect_index)

    # Add methods for setting the 0x80 bit to indicate to only use the mp.
    def get_effect_mp_only(self, eff_num: int) -> bool:
        effect_index = ControlHeader.get_effect_index(self, eff_num)
        return bool(effect_index & 0x80)

    def set_effect_mp_only(self, eff_num: int, use_mp_only: bool):
        effect_index = ControlHeader.get_effect_index(self, eff_num)
        effect_index &= 0x7F
        effect_index |= 0x80*(use_mp_only is True)
        ControlHeader.set_effect_index(self, eff_num, effect_index)

    battle_group_id = byte_prop(0, 0x7F)


class EffectHeader(BinaryData):
    '''
    A class for representing an effect header.  Effect headers can be used for
    techs and basic attacks.
    '''
    SIZE = 0xC

    damage_formula_id = byte_prop(5, 0xFF, ret_type=DamageFormula)
    effect_type = byte_prop(0, 0xFF, ret_type=EffectType)
    power = byte_prop(9, 0xFF)
    
    @property
    def heal_power(self) -> int:
        if self.effect_type == EffectType.HEALING:
            return self[1]
        elif self.effect_type == EffectType.HEALSTATUS:
            return self[1] & 0x1F
        
        raise ValueError('Effect Type does not support healing')

    @heal_power.setter
    def heal_power(self, val: int):
        if self.effect_type == EffectType.HEALING:
            self[1] = val
        elif self.effect_type == EffectType.HEALSTATUS:
            self[1] |= 0x40
            self[1] &= 0xC0
            self[1] |= (val & 0x1F)
        else:
            raise ValueError('Effect Type does not support healing')

    @property
    def will_revive(self):
        if self.effect_type == EffectType.HEALSTATUS:
            return bool(self[1] & 0x80)

        else:
            return False

    @will_revive.setter
    def will_revive(self, val: bool):
        if self.effect_type == EffectType.HEALSTATUS:
            self[1] &= 0x7F
            self[1] |= val*0x80
        
    @property
    def status_effect(self) -> list[ctenums.StatusEffect]:
        status_byte = self[2]
        statuses = []
        for x in list(ctenums.StatusEffect):
            if int(x) & status_byte:
                statuses.append(x)
        return statuses

    @status_effect.setter
    def status_effect(
            self,
            statuses: typing.Union[typing.Iterable[ctenums.StatusEffect],
                                   ctenums.StatusEffect]
    ):
        if isinstance(statuses, ctenums.StatusEffect):
            status_byte = int(statuses)
        else:
            status_byte = 0
            for x in statuses:
                status_byte |= int(x)

        self[2] = status_byte

    defense_byte = byte_prop(6)


class PCTechEffectHeader(EffectHeader):
    DATA_PTR = 0x01BF96


class TargetData(BinaryData):
    SIZE = 2
    pass


class PCTechTargetData(TargetData):
    DATA_PTR = 0x01C25A


class TechGfxHeader(BinaryData):
    SIZE = 7

    script_id = byte_prop(0, 0xFF)
    layer3_packet_id = byte_prop(6, 0xFF)


class PCTechGfxHeader(TechGfxHeader):
    DATA_PTR = 0x0145BC


class PCTechBattleGroup(BinaryData):
    SIZE = 3
    DATA_PTR = 0x01CBAE

    @classmethod
    def validate_data(cls, data: bytes) -> bool:
        print('pctbg here')
        if 0xFF in data:
            last_pos = data.index(0xFF)
        else:
            last_pos = cls.SIZE

        for x in data[last_pos:]:
            if x != 0xFF:
                raise ValueError('Found non-0xFF after first 0xFF')

        for x in data[:last_pos]:
            if not 0 <= x < 8:
                raise ValueError('PC indices must be in range(8)')

    @classmethod
    def from_charids(cls: typing.Type[T], char_ids: list[ctenums.CharID]):

        data = cls.char_ids_to_bytes(char_ids)
        return cls(data)

    @staticmethod
    def char_ids_to_bytes(char_ids: list[ctenums.CharID]) -> bytes:
        data = bytes(int(x) for x in char_ids)
        missing_bytes = 3 - len(data)

        if missing_bytes < 0:
            raise ValueError('PCTechBattleGroup can have at most 3 PCs')

        data = data + b'\xFF'*(missing_bytes)
        return data

    def to_bitmask(self):
        if 0xFF in self:
            last_pos = self.index(0xFF)
        else:
            last_pos = self.SIZE

        bitmask = 0
        for pc_index in self[:last_pos]:
            bitmask |= (0x80 >> pc_index)

    @property
    def number_of_pcs(self) -> int:
        return 3 - self.count(0xFF)


class PCTechLearnRequirements(BinaryData):
    SIZE = 3

    @classmethod
    def validate_data(cls, data: bytes) -> bool:
        if 0xFF in data:
            last_pos = data.index(0xFF)
        else:
            last_pos = cls.SIZE

        for x in data[last_pos:]:
            if x != 0xFF:
                raise ValueError('Found non-0xFF after first 0xFF')

        for x in data[:last_pos]:
            if not 0 <= x < 9:
                raise ValueError('Learn requirements must be in range(9)')

    @staticmethod
    def get_learn_requirment_start(rom: bytes):
        ref_local_ptr = int.from_bytes(rom[0x01F261:0x01F261+2], 'little')
        ref_bank = rom[0x01F26A+3] * 0x10000

        lrn_ref_ptr = ref_bank + ref_local_ptr
        lrn_ref_ptr = byteops.to_file_ptr(lrn_ref_ptr)

        # Assume lrn refs are in order
        lrn_req_local_ptr = int.from_bytes(rom[lrn_ref_ptr+3:lrn_ref_ptr+5],
                                           'little')
        lrn_req_bank = rom[0x01F595+3] * 0x10000
        lrn_req_ptr = lrn_req_bank + lrn_req_local_ptr
        lrn_req_ptr = byteops.to_file_ptr(lrn_req_ptr)

        return lrn_req_ptr

    @classmethod
    def from_rom(cls, rom: bytes, record_id: int):
        lrn_req_ptr = cls.get_learn_requirment_start(rom)
        return cls(rom, lrn_req_ptr+cls.SIZE*record_id)


class PlayerTech:
    def __init__(
            self,
            battle_group: PCTechBattleGroup,
            control_header: PCTechControlHeader,
            effect_headers: typing.Iterable[PCTechEffectHeader],
            effect_mps: typing.Iterable[int],
            menu_mp_reqs: typing.Iterable[int],
            graphics_header: PCTechGfxHeader,
            target_data: PCTechTargetData,
            learn_reqs: PCTechLearnRequirements,
            name: ctstrings.CTNameString,
            desc: ctstrings.CTString
    ):
        self.battle_group = battle_group.get_copy()
        self.control_header = control_header.get_copy()
        self.graphics_header = graphics_header.get_copy()
        self.target_data = target_data.get_copy()
        self.learn_reqs = learn_reqs.get_copy()
        self.name = ctstrings.CTNameString(name)
        self.desc = ctstrings.CTString(desc)

        self.effect_headers = []
        self.effect_mps = []
        
        # Make sure that everything is sized correctly.
        num_pcs = battle_group.number_of_pcs
        if len(effect_headers) != num_pcs:
            raise ValueError('Number of PCs and effect headers differs')

        if len(effect_mps) != num_pcs:
            raise ValueError('Number of PCs and mps differs')

        if num_pcs > 1 and len(menu_mp_reqs) != num_pcs:
            raise ValueError('Number of PCs and menu mp requirements differs')

        for effect_header, mp in zip(effect_headers, effect_mps):
            self.effect_headers.append(effect_header)
            self.effect_mps.append(mp)

        if len(self.effect_headers) != len(self.battle_group):
            raise ValueError(
                'Number of PCs and effect headers differ.'
            )

    @property
    def is_single_tech(self) -> bool:
        return self.battle_group.number_of_pcs == 1

    @property
    def needs_magic_to_learn(self):
        if not self.is_single_tech:
            raise TypeError("Combo techs don't need magic to learn")

        return self.control_header.data[0] & 0x80

    @needs_magic_to_learn.setter
    def needs_magic_to_learn(self, val: bool):
        if not self.is_single_tech:
            raise TypeError("Combo techs don't need magic to learn")

        self.control_header.data[0] &= 0x7F
        self.control_header.data[0] |= 0x80*(val is True)

    @property
    def is_unlearnable(self):
        if self.is_single_tech:
            raise TypeError("Single techs cannot be marked unlearnable.")

        return self.control_header.data[0] & 0x80

    @is_unlearnable.setter
    def is_unlearnable(self, val: bool):
        if not self.is_single_tech:
            raise TypeError("Single techs cannot be marked unlearnable.")

        self.control_header.data[0] &= 0x7F
        self.control_header.data[0] |= 0x80*(val is True)


class PCTechDB:

    def __init__(self):
        # Make all possible bitmasks
        menu_groups = PCTechDB.get_menu_groups()
        self.menu_dict = {menu_group: [] for menu_group in menu_groups}
        self.tech_dict = {tech_id: None for tech_id in range(0x100)}

    @staticmethod
    def get_menu_groups() -> list[int]:
        single_groups = [0x80 >> i for i in range(7)]
        dual_groups = [0x80 >> i | 0x80 >> j
                       for i in range(7)
                       for j in range(7)
                       if i < j]
        triple_groups = [0x80 >> i | 0x80 >> j | 0x80 >> k
                         for i in range(7)
                         for j in range(7)
                         for k in range(7)
                         if i < j < k]

        return single_groups + dual_groups + triple_groups


def main():
    ct_rom = ctrom.CTRom.from_file('./roms/ct.sfc')




if __name__ == '__main__':
    main()
