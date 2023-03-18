'''
Module for PCTech class and functions related to manipulating PCTechs.
'''
from __future__ import annotations
import typing

import byteops
import ctenums
import ctrom
import ctstrings
import cttypes as cty
import cttechtypes as ctt


def get_menu_usable_list(ct_rom: ctrom.CTRom) -> list[int]:
    '''
    Get a list of techs marked as usuable in the menu.
    '''
    hook_pos = 0x3FF82E

    rom_buf = ct_rom.rom_data.getbuffer()
    hook_byte = rom_buf[hook_pos]

    if hook_byte == 0xA9:
        # Not expanded
        tech_list_start = 0x3FF830
    elif hook_byte == 0x22:
        # Expanded, starts with JSL
        rt_addr = byteops.file_ptr_from_rom(rom_buf, hook_pos+1)
        tech_list_start = rt_addr + 2
    else:
        raise ValueError("Could not read menu usable list from ct_rom.")

    # tech_list_start points to code that's just a list of instructions
    # TSB XX 77 which sets some bits in 0x7E77XX to mark tech XX as usable
    # in the menu.  TSB has opcode 0x0C.
    ret_list: list[int] = []
    cur_pos = tech_list_start
    while rom_buf[cur_pos] == 0x0C:
        ret_list.append(rom_buf[cur_pos+1])
        cur_pos += 3

    return ret_list


def get_menu_usable(ct_rom: ctrom.CTRom, tech_id: int) -> bool:
    '''Determine if tech tech_id is usable in the menu.'''
    return tech_id in get_menu_usable_list(ct_rom)


RockType = typing.Literal[
    ctenums.ItemID.BLUE_ROCK, ctenums.ItemID.BLACK_ROCK,
    ctenums.ItemID.SILVERROCK, ctenums.ItemID.WHITE_ROCK,
    ctenums.ItemID.GOLD_ROCK
]


def determine_rock_used(
        ct_rom: ctrom.CTRom, tech_id: int) -> typing.Optional[RockType]:
    '''
    Determine which rock a tech needs.  Returns None if no rock is needed.
    '''
    rom = ct_rom.rom_data

    hook_pos = 0x0282F3
    hook_value = rom.getbuffer()[hook_pos]

    rock_list: list[RockType] = [
        ctenums.ItemID.BLACK_ROCK, ctenums.ItemID.BLUE_ROCK,
        ctenums.ItemID.SILVERROCK, ctenums.ItemID.WHITE_ROCK,
        ctenums.ItemID.GOLD_ROCK
    ]

    if hook_value == 0x5C:
        # Is modified
        routine_addr = byteops.file_ptr_from_rom(rom.getbuffer(), hook_pos+1)

        num_rock_techs = ctt.get_rock_tech_count(ct_rom)
        num_techs = ctt.get_total_tech_count(ct_rom)

        rock_tech_number = tech_id - (num_techs - num_rock_techs)
        if rock_tech_number < 0:
            return None

        # Otherwise, find rock_tech_number in the rock assignment table.

        # We use raw offsets into the routine to find the location of their
        # rock pointer table and the actual rock data.
        rock_table_ptr = routine_addr + 0x30
        rock_table_addr = byteops.file_ptr_from_rom(rom.getbuffer(),
                                                    rock_table_ptr)

        # The rock table data is lexicographic order on (pc_id, rock_id)
        # Each entry is a 0xFF-terminated list of rock_tech_numbers.  So
        # We loop until we find the desired rock_tech_number and can % 5
        # to find which rock is used for that tech.
        ff_count = 0
        rom.seek(rock_table_addr)
        while ff_count < 35:

            # This could be more efficient by reading chunks, but it's unlikely
            # to matter with how infrequently we call this.
            cur_byte = rom.read(1)[0]

            if cur_byte == 0xFF:
                ff_count += 1
            elif cur_byte == rock_tech_number:
                rock_num = ff_count % 5
                return rock_list[rock_num]

        raise ValueError("No rock found for tech.")

    if hook_value == 0xA2:
        # Is vanilla
        num_techs = ctt.get_total_tech_count(ct_rom)
        first_rock_tech = num_techs - 5
        rock_num = tech_id - first_rock_tech

        if rock_num < 0:
            return None
        return rock_list[rock_num]

    raise ValueError("Unable to read rock data from rom.")


def get_pc_target_data(
        ct_rom: ctrom.CTRom, tech_id: int,
        tech_target_data: typing.Optional[ctt.PCTechTargetData] = None
) -> typing.Optional[ctenums.CharID]:
    '''
    Determine whether a tech needs to target based on a particular PC index.
    When charrando is used, this needs to be updated.

    Notable Examples:
    - Doublevbomb targets around PC with index 3.
    - Black hole targets around PC with index 6.
    '''

    hook_pos = 0x0122A9
    rom_buf = ct_rom.rom_data.getbuffer()

    hook_byte = rom_buf[hook_pos]

    if hook_byte == 0xBD:
        # Unmodified
        # Determine pc target data from normal tech target data.
        if tech_target_data is None:
            tech_target_data = ctt.PCTechTargetData.read_from_ctrom(
                ct_rom, tech_id)

        target_type = tech_target_data.select_target
        if target_type == ctt.TargetType.AREA_MAGUS:
            return ctenums.CharID.MAGUS
        if target_type in (ctt.TargetType.LINE_ROBO,
                           ctt.TargetType.AREA_ROBO_13,
                           ctt.TargetType.AREA_ROBO_14):
            return ctenums.CharID.ROBO
        return None
    if hook_byte == 0x5C:
        # Modified
        # Determine pc targt data from special range on rom
        rt_start = byteops.file_ptr_from_rom(rom_buf, hook_pos+1)
        rt_offset = 5
        target_table_start = byteops.file_ptr_from_rom(rom_buf,
                                                       rt_start + rt_offset)
        target_byte = rom_buf[target_table_start + tech_id]

        if target_byte == 0xFF:
            return None
        return ctenums.CharID(target_byte)

    raise ValueError("Could not parse rom target routine.")


class PCTech:
    '''
    Class to store all data needed by a tech.

    Most of this is straightforward, but there are two dc-flag specific
    fields that are included.
    - rock_used: With dc the rock -> tech association can not be determined
        from the tech_id.  This needs to be given explicitly.
    - menu_usable:  With dc, there can be many (or no) techs which are usable
        in the menu.
    - pc_target: Some techs target a particular CharID (e.g. Doublevbomb).
        The target needs to be tracked explicitly for dc flag when there may
        be multiple of the same character in a fight.
    '''
    def __init__(
            self,
            battle_group: ctt.PCTechBattleGroup,
            control_header: ctt.PCTechControlHeader,
            effect_headers: list[ctt.PCTechEffectHeader],
            effect_mps: list[int],
            menu_mp_reqs: typing.Optional[ctt.PCTechMenuMPReq],
            graphics_header: ctt.PCTechGfxHeader,
            target_data: ctt.PCTechTargetData,
            learn_reqs: typing.Optional[ctt.PCTechLearnRequirements],
            name: ctstrings.CTNameString,
            desc: ctstrings.CTString,
            atb_penalty: ctt.PCTechATBPenalty,
            rock_used: typing.Optional[RockType],
            menu_usable: bool,
            pc_target: typing.Optional[ctenums.CharID]
    ):
        self.battle_group = battle_group.get_copy()
        self.control_header = control_header.get_copy()
        self.graphics_header = graphics_header.get_copy()
        self.target_data = target_data.get_copy()
        self.learn_reqs: typing.Optional[ctt.PCTechLearnRequirements]
        self.atb_penalty = atb_penalty.get_copy()
        self.rock_used = rock_used
        self.menu_usable = menu_usable
        self.pc_target = pc_target

        if learn_reqs is not None:
            self.learn_reqs = learn_reqs.get_copy()
        else:
            self.learn_reqs = None

        # TODO: Are menu_mp_reqs needed?  Why not load the effect index in?
        self.menu_mp_reqs: typing.Optional[ctt.PCTechMenuMPReq]
        if menu_mp_reqs is not None:
            self.menu_mp_reqs = menu_mp_reqs.get_copy()
        else:
            self.menu_mp_reqs = None

        self._name = ctstrings.CTNameString(name)
        self._desc = ctstrings.CTString(desc)

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
    def name(self) -> str:
        return str(self._name)

    @name.setter
    def name(self, val: str):
        new_name = ctstrings.CTNameString.from_string(val, length=0xB)
        self._name = new_name

    @property
    def desc(self) -> str:
        return str(self._desc)

    @desc.setter
    def desc(self, val: str):
        new_desc = ctstrings.CTString.from_str(val, compress=True)
        self._desc = new_desc

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
            lrn_req_rw: typing.Optional[cty.RomRW] = None,
            atb_pen_rw: typing.Optional[cty.RomRW] = None
            ) -> PCTech:
        control_header = ctt.PCTechControlHeader.read_from_ctrom(
            ct_rom, tech_id)

        battle_group_index = control_header.battle_group_id
        battle_group = ctt.PCTechBattleGroup.read_from_ctrom(
            ct_rom, battle_group_index)

        eff_inds = [control_header.get_effect_index(eff_num)
                    for eff_num in range(battle_group.number_of_pcs)]
        effect_headers = [
            ctt.PCTechEffectHeader.read_from_ctrom(ct_rom, eff_ind)
            for eff_ind in eff_inds
        ]

        effect_mps = [
            int(ctt.PCEffectMP.read_from_ctrom(ct_rom, eff_ind)[0])
            for eff_ind in eff_inds
        ]

        graphics_header = ctt.PCTechGfxHeader.read_from_ctrom(
            ct_rom, tech_id)

        target_data = ctt.PCTechTargetData.read_from_ctrom(
            ct_rom, tech_id)

        if battle_group.number_of_pcs > 1:
            if lrn_req_rw is None:
                lrn_req_rw = ctt.PCTechLearnRequirements.ROM_RW

                # There are always 0x39 single tech entries: 1 fake +
                # 7*8 singles.
                lrn_req_index = tech_id - 0x39
                learn_reqs = ctt.PCTechLearnRequirements.read_from_ctrom(
                    ct_rom, lrn_req_index, None, lrn_req_rw
                )
        else:
            learn_reqs = None

        if battle_group.number_of_pcs > 1:
            menu_mps = ctt.PCTechMenuMPReq.read_from_ctrom(
                ct_rom, tech_id, battle_group.number_of_pcs
            )
        else:
            menu_mps = None

        name = ctt.read_tech_name_from_ctrom(ct_rom, tech_id)
        desc = ctt.read_tech_desc_from_ctrom(ct_rom, tech_id)

        if atb_pen_rw is None:
            num_dual_techs = ctt.get_dual_tech_count(ct_rom)
            num_triple_techs = ctt.get_triple_tech_count(ct_rom)
            atb_pen_rw = ctt.PCTechATBPenaltyRW(0x01BDF6, num_dual_techs,
                                                num_triple_techs)

        if battle_group.number_of_pcs == 3:
            num_atb_bytes = 2
        else:
            num_atb_bytes = 1

        atb_penalty = ctt.PCTechATBPenalty.read_from_ctrom(
            ct_rom, tech_id, num_atb_bytes, atb_pen_rw)

        rock_used = determine_rock_used(ct_rom, tech_id)
        menu_usable = get_menu_usable(ct_rom, tech_id)
        pc_target = get_pc_target_data(ct_rom, tech_id, target_data)

        return PCTech(battle_group, control_header, effect_headers,
                      effect_mps, menu_mps, graphics_header, target_data,
                      learn_reqs, name, desc, atb_penalty, rock_used,
                      menu_usable, pc_target)


class PCTechManagerTechGroup:
    def __init__(self, bitmask: ctt.PCTechMenuGroup):
        pass


class PCTechManager:
    '''Handle all PC tech data.'''

    def __init__(self, techs: typing.Iterable[PCTech]):
        pass
