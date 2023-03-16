from __future__ import annotations

import typing

import byteops
import ctenums
import ctrom
import ctstrings

from freespace import FSWriteType as FSW

import cttypes as ctt
from cttypes import SizedBinaryData, byte_prop, bytes_prop


T = typing.TypeVar('T', bound=SizedBinaryData)


class DamageFormula(ctenums.StrIntEnum):
    '''
    Enum for different damage formualas.
    '''
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


# TODO: This coincides with itemdata.WeaponEffects.  Pick one place for it.
class EffectMod(ctenums.StrIntEnum):
    '''
    Enum for possible effects on a tech.
    '''
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
    '''
    Enum for the different effect modes an effect header can have.
    '''
    HEALING = 0
    HEALSTATUS = 1
    STATUS = 2
    DAMAGE = 3
    STEAL = 6
    MULTIHIT = 8


class ControlHeader(SizedBinaryData):
    '''
    A class for representing a tech's control header.

    In theory this class will work for enemy atacks, enemy techs, and player
    techs as well.
    '''
    SIZE: int = 0xB

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
    def element(self) -> ctenums.Element:
        elem_byte = self[3]
        elem_byte &= 0xF0

        if bin(elem_byte).count('1') > 1:
            raise ValueError('A tech can only have one element set.')
        if bin(elem_byte).count('1') == 0:
            return ctenums.Element.NONELEMENTAL
        if elem_byte & 0x80:
            return ctenums.Element.LIGHTNING
        if elem_byte & 0x40:
            return ctenums.Element.SHADOW
        if elem_byte & 0x20:
            return ctenums.Element.ICE
        if elem_byte & 0x10:
            return ctenums.Element.FIRE

        raise ValueError("Invalid Element Byte")

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
    ROM_RW = ctt.AbsPointerRW(0x01CBA1)

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


class EffectHeader(SizedBinaryData):
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
        if self.effect_type == EffectType.HEALSTATUS:
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
    ROM_RW = ctt.AbsPointerRW(0x01BF96)


class TargetData(SizedBinaryData):
    SIZE = 2


class PCTechTargetData(TargetData):
    ROM_RW = ctt.AbsPointerRW(0x01C25A)


class TechGfxHeader(SizedBinaryData):
    SIZE = 7

    script_id = byte_prop(0, 0xFF)
    layer3_packet_id = byte_prop(6, 0xFF)


class PCTechGfxHeader(TechGfxHeader):
    ROM_RW = ctt.AbsPointerRW(0x0145BC)


class PCTechBattleGroup(SizedBinaryData):
    SIZE = 3
    ROM_RW = ctt.AbsPointerRW(0x01CBAE)

    @classmethod
    def validate_data(cls: typing.Type[T], data: T):
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
    def from_charids(cls, char_ids: list[ctenums.CharID]):

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


class PCTechLearnRW(ctt.RomRW):

    def __init__(self):
        '''Do Nothing'''
        self.stuff = None

    @staticmethod
    def get_learn_requirment_start(rom: bytes) -> int:
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

    @staticmethod
    def get_record_start(rom: bytes,
                         record_size: int = 3,
                         record_num: int = 0) -> int:
        block_start = PCTechLearnRW.get_learn_requirment_start(rom)
        record_start = block_start + record_num*record_size
        return record_start

    def read_data_from_ctrom(self,
                             ct_rom: ctrom.CTRom,
                             num_bytes: int,
                             record_num: int = 0) -> bytes:
        '''
        Read num_bytes bytes from a ctrom.CTRom.  If the data is arranged in
        records, read record number record_num.
        '''
        rom = ct_rom.rom_data.getbuffer()
        record_start = PCTechLearnRW.get_record_start(
            rom, num_bytes, record_num)
        return bytes(rom[record_start:record_start+num_bytes])

    def write_data_to_ct_rom(self,
                             ct_rom: ctrom.CTRom,
                             data: bytes,
                             record_num: int = 0):
        '''
        Write data to a ctrom.CTRom.  If the target data is arranged in
        records of length len(data), write to record number record_num.
        '''
        record_start = PCTechLearnRW.get_record_start(
            ct_rom.rom_data.getbuffer(), len(data), record_num)
        ct_rom.rom_data.seek(record_start)
        ct_rom.rom_data.write(data, ctrom.freespace.FSWriteType.MARK_USED)

    def free_data_on_ct_rom(self, ct_rom: ctrom.CTRom,
                            num_bytes: int, record_num: int = 0):
        '''
        Mark the data on the ROM that would be read/written as free
        '''
        rom = ct_rom.rom_data.getbuffer()
        record_start = PCTechLearnRW.get_record_start(
            rom, num_bytes, record_num)

        ct_rom.rom_data.space_manager.mark_block(
            (record_start, record_start+num_bytes),
            ctrom.freespace.FSWriteType.MARK_FREE
        )


def get_learn_req_romrw(rom: bytes) -> ctt.AbsPointerRW:
    learn_req_start = PCTechLearnRW.get_learn_requirment_start(rom)
    return ctt.AbsPointerRW(learn_req_start)


class PCTechLearnRequirements(SizedBinaryData):
    ROM_RW = PCTechLearnRW()
    SIZE = 3

    @classmethod
    def validate_data(cls, data: PCTechLearnRequirements):
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


class PCEffectMP(ctt.BinaryData):
    SIZE = 1
    ROM_RW = ctt.AbsPointerRW(0x02BC4E)

def get_total_tech_count(ct_rom: ctrom.CTRom) -> int:
    # Control count is based on the control index of Magus' basic attack.
    # It should be the last control header, so count is that + 1.
    magus_atk_id = ct_rom.rom_data.getbuffer()[0x0C2589]
    control_count = magus_atk_id + 1
    num_techs = control_count - 7
    return num_techs


def get_pc_control_header_count(
        ct_rom: ctrom.CTRom,
        num_techs: typing.Optional[int] = None
        ) -> int:

    if num_techs is None:
        num_techs = get_total_tech_count(ct_rom)

    return num_techs + 7  # 7 basic attacksk + all tech controls


def get_dual_tech_count(ct_rom: ctrom.CTRom):
    # $FF/F910 C9 0F       CMP #$0F
    # A count of the dual groups.  Multiply by 3 for the number of dual techs.
    num_dual_groups = ct_rom.rom_data.getbuffer()[0x3FF911]
    num_dual_techs = 3*num_dual_groups
    return num_dual_techs


def get_triple_tech_count(ct_rom: ctrom.CTRom):
    # $FF/F936 C9 0F       CMP #$0F
    # This is the same but for triple techs.  It's hard but not impossible
    num_trip_techs = ct_rom.rom_data.getbuffer()[0x3FF937]
    return num_trip_techs


def get_rock_tech_count(ct_rom: ctrom.CTRom) -> int:
    return ct_rom.rom_data.getbuffer()[0x3FF9B5]

class MenuMPReqRW(ctt.RomRW):
    DATA_PTR = 0x3FF8F7
    
    def __init__(self):
        pass

    @classmethod
    def _get_data_start(cls, ct_rom: ctrom.CTRom) -> int:
        rom = ct_rom.rom_data
        rom.seek(cls.DATA_PTR)
        ptr_b = rom.read(3)
        rom_ptr = int.from_bytes(ptr_b, 'little')
        ptr = byteops.to_file_ptr(rom_ptr)
        return ptr

    def _get_ptr_and_size(self, ct_rom: ctrom.CTRom,
                          record_num: int) -> typing.Tuple[int, int]:
        if record_num < 0x39:
            raise ValueError(
                f"No Menu Reqs for single techs {record_num:02X}"
            )

        num_techs = get_total_tech_count(ct_rom)
        if record_num >= num_techs:
            raise ValueError(
                f"Tech number {record_num:02X} exceeds the maximum "
                f"{num_techs-1:02X}."
            )

        num_duals = get_dual_tech_count(ct_rom)
        num_techs = get_total_tech_count(ct_rom)
        data_start = self._get_data_start(ct_rom)

        if record_num < 0x39 + num_duals:
            record_start = data_start + (record_num - 0x39)*2
            record_size = 2
            return record_start, record_size

        # Otherwise it's a triple tech
        triple_start = data_start + 2*num_duals
        triple_index = record_num - (0x39 + num_duals)

        record_start = triple_start + 3*triple_index
        record_size = 3
        
        return record_start, record_size


    def read_data_from_ctrom(self,
                             ct_rom: ctrom.CTRom,
                             num_bytes: int,
                             record_num: int = 0) -> bytes:
        '''
        Read num_bytes bytes from a ctrom.CTRom.  If the data is arranged in
        records, read record number record_num.
        '''
        start, size = self._get_ptr_and_size(ct_rom, record_num)

        if size != num_bytes:
            raise ValueError(
                f"Computed size of record ({size}) does not match given "
                f"size ({num_bytes})"
            )

        rom = ct_rom.rom_data
        rom.seek(start)
        return rom.read(size)

    def write_data_to_ct_rom(self,
                             ct_rom: ctrom.CTRom,
                             data: bytes,
                             record_num: int = 0):
        '''
        Write data to a ctrom.CTRom.  If the target data is arranged in
        records of length len(data), write to record number record_num.
        '''
        start, size = self._get_ptr_and_size(ct_rom, record_num)

        if size != len(data):
            raise ValueError(
                f"Computed size of record ({size}) does not match given "
                f"size ({len(data)})"
            )

        rom = ct_rom.rom_data
        rom.seek(start)
        rom.write(data, FSW.MARK_USED)


    def free_data_on_ct_rom(self, ct_rom: ctrom.CTRom,
                            num_bytes: int, record_num: int = 0):
        '''
        Mark the data on the ROM that would be read/written as free
        '''
        start, size = self._get_ptr_and_size(ct_rom, record_num)

        if size != num_bytes:
            raise ValueError(
                f"Computed size of record ({size}) does not match given "
                f"size ({num_bytes})"
            )

        rom = ct_rom.rom_data
        rom.seek(start)
        rom.space_manager.mark_block((start, start+size), FSW.MARK_FREE)


class PCTechMenuMPReq(ctt.BinaryData):
    SIZE = None
    ROM_RW = MenuMPReqRW()


def get_tech_name_romrw():
    return ctt.LocalPointerRW(0x010B75, 0x010B6A)

def get_desc_ptr_romrw():
    return ctt.LocalPointerRW(0x02BE6A, 0x0D0323)

_tech_name_rw = ctt.LocalPointerRW(0x010B75, 0x010B6A)
def read_tech_name_from_ctrom(
        ct_rom: ctrom.CTRom, tech_id: int) -> ctstrings.CTNameString:
    name_b = _tech_name_rw.read_data_from_ctrom(ct_rom, 0x0B, tech_id)
    return ctstrings.CTNameString(name_b)


_desc_ptr_rw = ctt.LocalPointerRW(0x02BE6A, 0x0D0323)
def read_tech_desc_from_ctrom_address(
        ct_rom: ctrom.CTRom, address: int
        ) -> ctstrings.CTString:

    rom = ct_rom.rom_data

    chunk_size = 0x100
    num_chunks = 0
    rom.seek(address)
    while True:
        chunk = rom.read(chunk_size)
        if 0 in chunk:
            desc_size = chunk.index(0) + chunk_size*num_chunks + 1
            break

        if len(chunk) < chunk_size:
            raise ValueError("Unterminated description")

        num_chunks += 1

    rom.seek(address)
    desc_b = rom.read(desc_size)
    return ctstrings.CTString(desc_b)


def read_tech_desc_from_ctrom(
        ct_rom: ctrom.CTRom, tech_id: int) -> ctstrings.CTString:

    rom = ct_rom.rom_data
    start = _desc_ptr_rw.get_data_start_from_ctrom(ct_rom)
    bank = start & 0xFF0000

    local_ptr_b = _desc_ptr_rw.read_data_from_ctrom(ct_rom, 2, tech_id)
    ptr = bank + int.from_bytes(local_ptr_b, 'little')

    chunk_size = 0x100
    num_chunks = 0
    rom.seek(ptr)
    while True:
        chunk = rom.read(chunk_size)
        if 0 in chunk:
            desc_size = chunk.index(0) + chunk_size*num_chunks + 1
            break

        num_chunks += 1

    rom.seek(ptr)
    desc_b = rom.read(desc_size)
    return ctstrings.CTString(desc_b)


class PCTechDescriptionPointer(SizedBinaryData):
    SIZE = 2
    ROM_RW = ctt.LocalPointerRW(0x02BE6A, 0x0D0323)

    pointer = bytes_prop(0, 2, 0xFFFF, 'little', int)


class PCTechATBPenaltyRW(ctt.AbsPointerRW):

    def __init__(self, abs_file_ptr: int,
                 num_dual_techs: int,
                 num_triple_techs: int):
        ctt.AbsPointerRW.__init__(self, abs_file_ptr)
        self.num_dual_techs = num_dual_techs
        self.num_triple_techs = num_triple_techs

    def _get_real_size(
            self, num_bytes: typing.Optional[int], record_num: int
    ) -> int:
        first_triple_id = 0x39 + self.num_dual_techs
        if record_num >= first_triple_id:
            if num_bytes is None:
                num_bytes = 2
            elif num_bytes != 2:
                raise ValueError(f"Tech {record_num} is a triple tech "
                                 f"(2 bytes) but {num_bytes} bytes was "
                                 "requested")
        else:
            if num_bytes is None:
                num_bytes = 1
            elif num_bytes != 1:
                raise ValueError(f"Tech {record_num} is not a triple tech "
                                 f"(1 byte) but {num_bytes} bytes was "
                                 "requested")

        return num_bytes

    def read_data_from_ctrom(self,
                             ct_rom: ctrom.CTRom,
                             num_bytes: typing.Optional[int],
                             record_num: int = 0) -> bytes:

        num_bytes = self._get_real_size(num_bytes, record_num)

        data_start = self.get_data_start_from_ctrom(ct_rom)
        record_start = data_start + record_num

        rom = ct_rom.rom_data
        rom.seek(record_start)
        ret_b = rom.read(1)

        if num_bytes == 2:
            rom.seek(record_start + self.num_triple_techs)
            byte_2 = rom.read(1)
            ret_b += byte_2

        return ret_b

    def write_data_to_ct_rom(self, ct_rom: ctrom.CTRom,
                             data: bytes,
                             record_num: int = 0):
        num_bytes = self._get_real_size(len(data), record_num)

        data_start = self.get_data_start_from_ctrom(ct_rom)
        record_start = data_start + record_num

        rom = ct_rom.rom_data
        rom.seek(record_start)
        rom.write(data[0:1], FSW.MARK_USED)

        if num_bytes == 2:
            rom.seek(record_start + self.num_triple_techs)
            rom.write(data[1:2], FSW.MARK_USED)

    def free_data_on_ct_rom(self, ct_rom: ctrom.CTRom, num_bytes,
                            record_num: int = 0):
        num_bytes = self._get_real_size(num_bytes, record_num)

        data_start = self.get_data_start_from_ctrom(ct_rom)
        record_start = data_start + record_num

        space_man = ct_rom.rom_data.space_manager
        space_man.mark_block((record_start, record_start+1), FSW.MARK_FREE)

        if num_bytes == 2:
            extra_start = record_start + self.num_triple_techs
            space_man.mark_block((extra_start, extra_start+1), FSW.MARK_FREE)


class PCTechATBPenalty(ctt.BinaryData):

    def get_pc_penalty(self, battle_group_pc_index: int) -> int:
        if battle_group_pc_index == 0:
            return (self[0] & 0xF0) >> 4

        if battle_group_pc_index == 1:
            return self[0] & 0x0F

        if battle_group_pc_index == 2:
            if len(self) != 2:
                raise ValueError("No entry for pc index 2")
            return self[1] & 0x0F

        raise ValueError("battle_group_pc_index may not exceed 2")

    def set_pc_penalty(self, battle_group_pc_index: int, value: int):
        if value not in range(0x10):
            raise ValueError(f"Value ({value:02X}) must be in range(0, 0x10)")

        if battle_group_pc_index == 0:
            self[0] &= 0x0F
            self[0] &= (value << 4)

        if battle_group_pc_index == 1:
            self[0] &= 0xF0
            self[0] &= value

        if battle_group_pc_index == 2:
            if len(self) != 2:
                raise ValueError("No entry for pc index 2")
            self[1] = value


class PCTech:
    def __init__(
            self,
            battle_group: PCTechBattleGroup,
            control_header: PCTechControlHeader,
            effect_headers: list[PCTechEffectHeader],
            effect_mps: list[int],
            menu_mp_reqs: typing.Optional[PCTechMenuMPReq],
            graphics_header: PCTechGfxHeader,
            target_data: PCTechTargetData,
            learn_reqs: typing.Optional[PCTechLearnRequirements],
            name: ctstrings.CTNameString,
            desc: ctstrings.CTString,
            atb_penalty: PCTechATBPenalty
    ):
        self.battle_group = battle_group.get_copy()
        self.control_header = control_header.get_copy()
        self.graphics_header = graphics_header.get_copy()
        self.target_data = target_data.get_copy()
        self.learn_reqs: typing.Optional[PCTechLearnRequirements]
        self.atb_penalty = atb_penalty.get_copy()

        if learn_reqs is not None:
            self.learn_reqs = learn_reqs.get_copy()
        else:
            self.learn_reqs = None

        self.menu_mp_reqs: typing.Optional[PCTechMenuMPReq]
        if menu_mp_reqs is not None:
            self.menu_mp_reqs = menu_mp_reqs.get_copy()
        else:
            self.menu_mp_reqs = None

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

        if len(atb_penalty) == 1 and num_pcs not in (1, 2):
            raise ValueError("Number of PCs and atb penalties differs.")
        if len(atb_penalty) == 2 and num_pcs != 3:
            raise ValueError("Number of PCs and atb penalties differs.")

        if menu_mp_reqs is None and num_pcs != 1:
            raise ValueError('Number of PCs and menu mp requirements differs')
        if menu_mp_reqs is not None and len(menu_mp_reqs) != num_pcs:
            raise ValueError('Number of PCs and menu mp requirements differs')

        for effect_header, mp in zip(effect_headers, effect_mps):
            self.effect_headers.append(effect_header)
            self.effect_mps.append(mp)

    @property
    def is_single_tech(self) -> bool:
        return self.battle_group.number_of_pcs == 1

    @property
    def is_dual_tech(self) -> bool:
        return self.battle_group.number_of_pcs == 2

    @property
    def is_triple_tech(self) -> bool:
        return self.battle_group.number_of_pcs == 3

    @property
    def needs_magic_to_learn(self):
        if not self.is_single_tech:
            raise TypeError("Combo techs don't need magic to learn")

        return self.control_header[0] & 0x80

    @needs_magic_to_learn.setter
    def needs_magic_to_learn(self, val: bool):
        if not self.is_single_tech:
            raise TypeError("Combo techs don't need magic to learn")

        self.control_header[0] &= 0x7F
        self.control_header[0] |= 0x80*(val is True)

    @property
    def is_unlearnable(self):
        if self.is_single_tech:
            raise TypeError("Single techs cannot be marked unlearnable.")

        return self.control_header[0] & 0x80

    @is_unlearnable.setter
    def is_unlearnable(self, val: bool):
        if not self.is_single_tech:
            raise TypeError("Single techs cannot be marked unlearnable.")

        self.control_header[0] &= 0x7F
        self.control_header[0] |= 0x80*(val is True)

    @classmethod
    def read_from_ctrom(
            cls, ct_rom: ctrom.CTRom, tech_id: int,
            lrn_req_rw: typing.Optional[ctt.RomRW] = None,
            atb_pen_rw: typing.Optional[ctt.RomRW] = None
            ) -> PCTech:
        control_header = PCTechControlHeader.read_from_ctrom(
            ct_rom, tech_id)

        battle_group_index = control_header.battle_group_id
        battle_group = PCTechBattleGroup.read_from_ctrom(
            ct_rom, battle_group_index)

        eff_inds = [control_header.get_effect_index(eff_num)
                    for eff_num in range(battle_group.number_of_pcs)]
        effect_headers = [
            PCTechEffectHeader.read_from_ctrom(ct_rom, eff_ind)
            for eff_ind in eff_inds
        ]

        effect_mps = [
            int(PCEffectMP.read_from_ctrom(ct_rom, eff_ind)[0])
            for eff_ind in eff_inds
        ]

        graphics_header = PCTechGfxHeader.read_from_ctrom(
            ct_rom, tech_id)

        target_data = PCTechTargetData.read_from_ctrom(
            ct_rom, tech_id)

        if battle_group.number_of_pcs > 1:
            if lrn_req_rw is None:
                lrn_req_rw = PCTechLearnRequirements.ROM_RW

                # There are always 0x39 single tech entries: 1 fake +
                # 7*8 singles.
                lrn_req_index = tech_id - 0x39
                learn_reqs = PCTechLearnRequirements.read_from_ctrom(
                    ct_rom, lrn_req_index, None, lrn_req_rw
                )
        else:
            learn_reqs = None

        if battle_group.number_of_pcs > 1:
            menu_mps = PCTechMenuMPReq.read_from_ctrom(
                ct_rom, tech_id, battle_group.number_of_pcs
            )
        else:
            menu_mps = None

        name = read_tech_name_from_ctrom(ct_rom, tech_id)
        desc = read_tech_desc_from_ctrom(ct_rom, tech_id)

        if atb_pen_rw is None:
            num_dual_techs = get_dual_tech_count(ct_rom)
            num_triple_techs = get_triple_tech_count(ct_rom)
            atb_pen_rw = PCTechATBPenaltyRW(0x01BDF6, num_dual_techs,
                                            num_triple_techs)

        if battle_group.number_of_pcs == 3:
            num_atb_bytes = 2
        else:
            num_atb_bytes = 1

        atb_penalty = PCTechATBPenalty.read_from_ctrom(
            ct_rom, tech_id, num_atb_bytes, atb_pen_rw)

        return PCTech(battle_group, control_header, effect_headers,
                      effect_mps, menu_mps, graphics_header, target_data,
                      learn_reqs, name, desc, atb_penalty)


RockType = typing.Literal[
    ctenums.ItemID.BLUE_ROCK, ctenums.ItemID.BLACK_ROCK,
    ctenums.ItemID.SILVERROCK, ctenums.ItemID.WHITE_ROCK,
    ctenums.ItemID.GOLD_ROCK
]


def determine_rock_used(
        ct_rom: ctrom.CTRom, tech_id: int) -> Optional[RockType]:

    rom = ct_rom.rom_data

    hook_pos = 0x0282F3
    hook_value = rom.getbuffer()[hook_pos]

    rock_list = [
        ctenums.ItemID.BLACK_ROCK, ctenums.ItemID.BLUE_ROCK,
        ctenums.ItemID.SILVERROCK, ctenums.ItemID.WHITE_ROCK,
        ctenums.ItemID.GOLD_ROCK
    ]
    
    if hook_value == 0x5C:
        # Is modified
        pass
    elif hook_value == 0xA2:
        # Is vanilla
        num_techs = get_total_tech_count(ct_rom)
        first_rock_tech = num_techs - 5
        rock_num = tech_id - first_rock_tech

        if rock_num < 0:
            return None
        else:
            return rock_list[tech_id]
    else:
        raise ValueError("Unable to read rock data from rom.")

    

class PCTechMenuGroup(SizedBinaryData):
    SIZE = 1
    ROM_RW = ctt.AbsPointerRW(0x02BCE9)


class PCTechManagerMenuGroup:
    def __init__(self,
                 menu_group: PCTechManagerMenuGroup,
                 rock_used: typing.Optional[RockType]):
        self.menu_group = PCTechMenuGroup(menu_group)
        self.required_rock = rock_used

class PCTechManager:
    '''
    Replacement for TechDB.
    '''
    
    def __init__(self, techs: dict[PCTechManagerMenuGroup, list[PCTech]]):
        self.techs = dict(techs)

    def read_from_ctrom(ct_rom: ctrom.CTRom):
        pass


def main():
    ct_rom = ctrom.CTRom.from_file('./roms/ct.sfc')


if __name__ == '__main__':
    main()
