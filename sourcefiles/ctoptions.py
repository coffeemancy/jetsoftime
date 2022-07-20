'''
Module for preconfiguring in-game options at compile time
'''

import byteops
from ctenums import ActionMap, InputMap, LocID
from ctrom import CTRom
import ctevent

class ControllerBinds:

    BUTTONS_OFFSET = 0x02FCA9
    BUTTONS_LENGTH = 8

    def __init__(self, data: bytearray = None):

        self._mappings = self.get_vanilla()
        
        if data is None:
            return

        self.update_from_bytes(data[-8:])

    @classmethod
    def get_vanilla(cls):

        ret = {
            ActionMap.CONFIRM: InputMap.A_BUTTON,
            ActionMap.CANCEL: InputMap.B_BUTTON,
            ActionMap.MENU: InputMap.X_BUTTON,
            ActionMap.DASH: InputMap.B_BUTTON,
            ActionMap.MAP: InputMap.SELECT_BUTTON,
            ActionMap.WARP: InputMap.Y_BUTTON,
            ActionMap.PG_UP: InputMap.R_SHOULDER,
            ActionMap.PG_DN: InputMap.L_SHOULDER
        }
        
        return ret

    def from_rom(self, ctrom: CTRom):
        rom = ctrom.rom_data
        
        rom.seek(BUTTONS_OFFSET)
        data = rom.read(BUTTONS_LENGTH)
       
        return self.to_bytearray(data)

    #return bytearray in order CT expects it in, suitable for writing back to CTRom
    #optionally, accept an iterable of ints to write in its stead, order not checked from input
    def to_bytearray(self, data = None):
    
        ret = bytearray(8)

        if not data:
            data = bytearray(self._mappings.values())
        
        for idx, button in enumerate(data):
            ret[idx] = button
                
        return ret

    #updates button bindings given bytearray; bytearray assumed to be ordered in the same way as out
    def update_from_bytes(self, bytes: bytearray):

        if not (8 <= len(bytes) <= 11):
            return

        bytes = bytes[-8:]

        for idx, byte in zip(ActionMap, bytes):
            for input in InputMap:
                if byte == input:
                    self._mappings[idx] = input
                    break


    #restore vanilla settings, in place
    def reset_to_vanilla(self):
        self._mappings = self.get_vanilla()

    #do not call directly; helper function to mimic functionality observed when rebinding buttons in-game
    def _replace_overlap(self, button: InputMap, cmd: ActionMap):
        '''
        CT uses bitmasks stored in a known order to implement button mapping.
        The action is controlled by the index in the array.
        The button to which the action is bound is controlled by the value of the indexed byte
        
        During vblank (and inside an NMI), the functions at 0x0284EC (rearranger) and 0x028545 (translator)
        rearrange the raw data from the SNES's joypad registers such that all buttons are on the low byte and all
        d-pad input is on the high byte, and additional addresses are written according to the user's bindings.
        These addresses are referenced depending on what the game needs to check for, actions or specific buttons,
        and whether the game needs to check for a held button, a pressed button that requires releasing before
        accepting more input, or how long the user has pressed the button.
        
        The Start button is never allowed to be rebound. All eight actions will still need to be mapped, thus
        one button will always trigger two actions (or conversely, two actions will always have the same button bound to them)
        
        CT uses four copies of the button mapping in RAM at any one time:
            The in-use copy, used by 0x028585 and therefore everywhere that respects user binds; 0x7E2993
            
            The persistent user copy, saved from RAM to SRAM when the user saves the game; 0x7E0408
            
            A cache of the persistent user copy, exists when user is editing binds ; 0x7E9890
            
            User proposed copy, edited when user is rebinding and checked against the cached copy
            to prevent undesired lack of actions being bound to a button. ; 0x7E0f00
                
        To mimic reference functions at 0x02C5C7 (checks for overlap):
        
        Save the original button of target action
        Iterate over array, replace actions which match target action with original button.
        Write target button to target action
        '''
        
        data = self._mappings
        
        orig_button = data[cmd]
        
        for key in data:
            if data[key] == button:
                data[key] = orig_button

        data[cmd] = button

    @property
    def confirm(self):
        return self._mappings[ActionMap.CONFIRM]
        
    @confirm.setter
    def confirm(self, button: InputMap):
        self._replace_overlap(button, ActionMap.CONFIRM)

    @property
    def cancel(self):
        return self._mappings[ActionMap.CANCEL]
        
    @cancel.setter
    def cancel(self, button: InputMap):
        self._replace_overlap(button, ActionMap.CANCEL)

    @property
    def menu(self):
        return self._mappings[ActionMap.MENU]
        
    @menu.setter
    def menu(self, button: InputMap):
        self._replace_overlap(button, ActionMap.MENU)

    @property
    def dash(self):
        return self._mappings[ActionMap.DASH]
        
    @dash.setter
    def dash(self, button: InputMap):
        self._replace_overlap(button, ActionMap.DASH)
        
    @property
    def map(self):
        return self._mappings[ActionMap.MAP]
        
    @map.setter
    def map(self, button: InputMap):
        self._replace_overlap(button, ActionMap.MAP)

    @property
    def warp(self):
        return self._mappings[ActionMap.WARP]
        
    @warp.setter
    def warp(self, button: InputMap):
        self._replace_overlap(button, ActionMap.WARP)
    
    @property
    def pg_up(self):
        return self._mappings[ActionMap.PG_UP]
        
    @pg_up.setter
    def pg_up(self, button: InputMap):
        self._replace_overlap(button, ActionMap.PG_UP)    

    @property
    def pg_dn(self):
        return self._mappings[ActionMap.PG_DN]
        
    @pg_dn.setter
    def pg_dn(self, button: InputMap):
        self._replace_overlap(button, ActionMap.PG_DN)
        
    def write_routine_offsets(self, ctrom: CTRom):
        '''
        Repoint routine to control default/custom user binds to point to saved copy of vanilla binds
        '''
        
        rom = ctrom.rom_data
        space_man = rom.space_manager

        binds = self.to_bytearray(self.get_vanilla().values())

        start = space_man.get_free_addr(len(binds))
        rom_start = byteops.to_rom_ptr(start)
        
        rom_start_addr = byteops.to_little_endian(rom_start & 0x00FFFF, 2)
        rom_start_bank = (rom_start >> 16).to_bytes(1, 'little')
        
        #source addr (LDX)
        rom.seek(0x02C558 + 1)
        rom.write(rom_start_addr)
        
        #source bank (MVN)
        rom.seek(0x02C561 + 2)
        rom.write(rom_start_bank)

        rom.seek(start)
        rom.write(binds, ctevent.FSWriteType.MARK_USED)

    def __str__(self):
        ret = ''
            
        ret += f'Confirm: {self.confirm}' + '\n'
        ret += f'Cancel: {self.cancel}' + '\n'
        ret += f'Menu: {self.menu}' + '\n'
        ret += f'Dash: {self.dash}' + '\n'
        ret += f'Map: {self.map}' + '\n'
        ret += f'Warp: {self.warp}' + '\n'
        ret += f'Pg Dn: {self.pg_dn}' + '\n'
        ret += f'Pg Up: {self.pg_up}'
        
        return ret

    def __iter__(self):
        return iter(self._mappings.items())
        

        
class CTOpts:

    CONFIG_OFFSET = 0x02FCA6
    CONFIG_LENGTH = 3
    
    def __init__(self,  data: bytearray = None):
                
        self._data = self.get_vanilla()[:3]

        self.controller_binds = ControllerBinds()
        
        self.consistent_paging = False
        
        if data is None:
            return
        
        self.update_from_bytes(data)
        
        self.controller_binds.update_from_bytes(data)

        
    @classmethod
    def get_vanilla(cls):
    
        ret = bytearray([
            0x84, #Battle Speed 4, Stereo Audio, Standard Controls, Save Menu Cursor off, Wait Battle Mode, Skill/Item Info On
            0xa0, #Menu Background 0, Battle Message Speed 4, Save Battle Cursor off, Save Skill/Item Cursor on
            0x01, #Battle Gauge Style 1
            0x80, #Confirm, A
            0x08, #Cancel, B
            0x40, #Menu, X
            0x08, #Dash, B
            0x02, #Map, Select
            0x04, #Warp, Y
            0x10, #Pg Dn, R
            0x20  #Pg Dn, L
        ])
        
        return ret
    
    #Read provided CTRom, get config
    def from_rom(self, ctrom: CTRom, offset: int = CONFIG_OFFSET):
        rom = ctrom.rom_data

        rom.seek(offset)
        data = rom.read(self.CONFIG_LENGTH)
    
        return bytearray(data)

    #write current configuration to provided CTRom
    def write_to_ctrom(self, ctrom: CTRom, offset: int = CONFIG_OFFSET):
        
        self.custom_control_pad = False # update the custom controller option if different from vanilla
        
        out = self.to_bytearray()
        binds = self.controller_binds.to_bytearray()
        
        ctrom.rom_data.seek(offset)
        ctrom.rom_data.write(out + binds)

        if self.menu_background != 0:
            self.set_save_slot_background_hook(ctrom)
        
        if self.custom_control_pad:
            self.controller_binds.write_routine_offsets(ctrom)
            
        if self.consistent_paging:
            self.make_page_up_down_consistent(ctrom)
    
    
    def update_from_bytes(self, data: bytearray):
        self._data[:3] = data[:3]
        
    #Returns all bytes of config, suitable for writing back to CTRom
    def to_bytearray(self):
        return bytearray(self._data[0:3])
        
    #Properties, byte 0
    @property
    #Range, 0-7
    def battle_speed(self):
        return self.get_opt(0, 0x07)
        
    @battle_speed.setter
    def battle_speed(self, val: int):
        clamped = sorted((0, val, 7))[1]
        self.set_opt(0, 0x07, clamped)
    
    @property
    #Bit clear == stereo output, bit set == mono output
    #weird because description in game uses that text, should remain consistent
    def stereo_audio(self):
        return not(bool(self.get_opt(0, 0x08)))
        
    @stereo_audio.setter
    def stereo_audio(self, val):
        filt = not(bool(val))
        self.set_opt(0, 0x08, filt)
        
    @property
    #Bit clear == standard controls, bit set == custom controls
    def custom_control_pad(self):
        return bool(self.get_opt(0, 0x10))
        
    @custom_control_pad.setter
    #Force the custom controller on if it deviates from vanilla settings
    def custom_control_pad(self, val):
        if self.controller_binds.to_bytearray() != self.controller_binds.to_bytearray(self.controller_binds.get_vanilla().values()):
            self.set_opt(0, 0x10, True)
            return
            
        filt = bool(val)
        self.set_opt(0, 0x10, filt)
        
    @property
    #Bit clear == Menu always starts on equipment, bit set == Menu saves position
    def save_menu_cursor(self):
        return bool(self.get_opt(0, 0x20))
        
    @save_menu_cursor.setter
    def save_menu_cursor(self, val):
        filt = bool(val)
        self.set_opt(0, 0x20, filt)

    @property
    #Bit clear == battle mode is Wait, bit set == battle mode is Active
    def active_battle(self):
        return bool(self.get_opt(0, 0x40))
        
    @active_battle.setter
    def active_battle(self, val):
        filt = bool(val)
        self.set_opt(0, 0x40, filt)
        
    @property
    #Bit clear == in battle, tech and item descriptions are not displayed, bit set == in battle, tech and item descriptions are displayed
    def skill_item_info(self):
        return bool(self.get_opt(0, 0x80))
        
    @skill_item_info.setter
    def skill_item_info(self, val):
        filt = bool(val)
        self.set_opt(0, 0x80, filt)

    #Byte 1
    @property
    #Index, 0-7
    def menu_background(self):
        return self.get_opt(1, 0x07)
    
    @menu_background.setter
    def menu_background(self, val: int):
        clamped = sorted((0, val, 7))[1]
        self.set_opt(1, 0x07, clamped)
        
    @property
    #Range, 0-7
    def battle_msg_speed(self):
        return self.get_opt(1, 0x38)
    
    @battle_msg_speed.setter
    def battle_msg_speed(self, val: int):
        clamped = sorted((0, val, 7))[1]
        self.set_opt(1, 0x38, clamped)
        
    @property
    #Bit clear == in battle, cursor always starts on Att. for each PC, bit set == cursor position is saved for each PC
    def save_battle_cursor(self):
        return bool(self.get_opt(1, 0x40))
    
    @save_battle_cursor.setter
    def save_battle_cursor(self, val):
        filt = bool(val)
        self.set_opt(1, 0x40, filt)
        
    @property
    #Bit clear == tech and inventory cursors are not kept, bit set == tech cursors for each PC, and one for item inventory, are kept
    def save_tech_cursor(self):
        return bool(self.get_opt(1, 0x80))
        
    @save_tech_cursor.setter
    def save_tech_cursor(self, val):
        filt = bool(val)
        self.set_opt(1, 0x80, filt)

    #Byte 2
    @property
    #Range, 0-2
    def battle_gauge_style(self):
        return self.get_opt(2, 0x03)
        
    @battle_gauge_style.setter
    def battle_gauge_style(self, val: int):
        clamped = sorted((0, val, 2))[1]
        self.set_opt(2, 0x03, clamped)
    
    '''
    Get a value from the byte, taking into account how many shifts are required to isolate the value
    Unpredictable behavior if non-sequential bits are specified in clear.
    Params:
        idx: Index from zero along the bytearray
        clear: bits in which the value is stored
    '''
    def get_opt(self, idx, clear):
        shift = 0
        val = self._data[idx] & clear
        
        while clear & 0x01 == 0:
            clear >>= 1
            shift += 1
            
        return val >> shift
    
    '''
    Overwrite old value with new value, while preserving other variables in byte
    Unpredictable behavior if non-sequential bits are specified in clear.
    Params:
        idx: Index from zero along the bytearray
        clear: bits in which the value is stored
        val: value to write, not previously bit shifted
    '''
    def set_opt(self, idx, clear, val):
        shift = 0
        isolated = self._data[idx] & (0xFF - clear)
               
        while clear & 0x01 == 0:
            clear >>= 1
            shift += 1
        
        self._data[idx] = isolated | (val << shift)
        
    def set_save_slot_background_hook(self, ctrom: CTRom):

        '''
        Add hook to include empty save slots in default menu background.
        '''
        
        '''
        The subroutine to clear memory for entering the menu zeroes out the memory region used to store the menu background index of each save slot.
        
        The subroutine to render the save slots on the boot menu and save menus only reads SRAM for save data if the checksum passes.
        
        If the checksum for a save slot fails, the index remains at 0, causing the renderer subroutine to read 00 as the menu background index
        resulting in the default grey background.
        
        Entry condition from 0x02D2A6, save slot render subroutine:
            A and X/Y are 16 bits wide
            X and Y both contain nothing we want to keep
            $79 contains current save slot
            Z and C are clear
        '''
        
        val = self.menu_background
        rom = ctrom.rom_data
        space_man = rom.space_manager

        vanilla = bytearray.fromhex(
            'A5 78'            # LDA $78
            '29 00 03'         # AND #$0300
        )

        rom.seek(0x02D2A6)
        
        hooked = rom.read(5) != vanilla

        #TODO: allow editing of already-extant hooked subroutine; use case: reconfiguring a ROM for which one does not have the settings object and seed / sharelink
        
        if hooked:
            return
        
        bg = bytearray.fromhex(
            'E2 30'            # SEP #$30 ; set A and X/Y to 8 bits; clears high byte of X/Y
            'AD 0C 02'         # LDA $020C ; check if slot has no data, will be 1A if there is no data or invalid data in the save slot
            'C9 1A'            # CMP #$1A ; known value
            'D0 07'            # BNE exit
           f'A9 {val:02x}'     # LDA #${new_value} ; Could do LDA $C2FCA7 and then AND #$07 here, but that consumes runtime clocks for no extra benefit
            'A6 79'            # LDX $79 ; get current save slot from memory, 16 bits wide
            '9D 79 0D'         # STA $0D79, X
            'C2 33'            # REP #$33 [exit]; reset A and X/Y to 16 bits, clear carry and zero flags, same as entry condition
            'A5 78'            # LDA $78
            '29 00 03'         # AND #$0300
            '6B'               # RTL
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
        
    def __str__(self):
        
        ret = ''
        ret += f'Battle Speed: {self.battle_speed + 1}' + '\n'
        ret += f'Stereo Audio: {self.stereo_audio}' + '\n'
        ret += f'Custom Controls: {self.custom_control_pad}' + '\n'
        ret += f'Save Menu Cursor: {self.save_menu_cursor}' + '\n'
        ret += f'Active Battle: {self.active_battle}' + '\n'
        ret += f'Skill/Item Info: {self.skill_item_info}' + '\n'
        ret += f'Menu Background: {self.menu_background + 1}' + '\n'
        ret += f'Battle Message Speed: {self.battle_msg_speed + 1}' + '\n'
        ret += f'Save Battle Cursor: {self.save_battle_cursor}' + '\n'
        ret += f'Save Skill/Item Cursor: {self.save_tech_cursor}' + '\n'
        ret += f'Battle Gauge Style: {self.battle_gauge_style}'
        
        return ret

    def __iter__(self):
        
        ret = {
            'battle_speed': self.battle_speed,
            'stereo_audio': self.stereo_audio,
            'custom_control_pad': self.custom_control_pad,
            'save_menu_cursor': self.save_menu_cursor,
            'active_battle': self.active_battle,
            'skill_item_info': self.skill_item_info,
            'menu_background': self.menu_background,
            'battle_msg_speed': self.battle_msg_speed,
            'save_battle_cursor': self.save_battle_cursor,
            'save_tech_cursor': self.save_tech_cursor,
            'battle_gauge_style': self.battle_gauge_style
        }
        

        return iter(ret.items())

    def make_page_up_down_consistent(self, ctrom: CTRom):
        '''
        Modify bit checks to test the opposite bits in inventory scrolls to flip effects of Pg Dn/Up

        Default behavior of Pg Up/Dn is inconsistent. In most scrollable menus (inventory, shops),
        and in the battle inventory menu, Pg Up pages up, and Pg Dn pages down. With them being bound
        to R and L, respectively, by default, it produces L to page down and R to page up. This hurts
        my brain, so go fix it to make it consistent with other uses of Pg Dn and Pg Up.
        
        Trivia: This would result in having to rename ActionMap keys, but ActionMap is as vanilla.
        '''

        rom = ctrom.rom_data
        
        '''
        The menu program does not directly read the input rearrange and translate bytes
        Input collator function c2e987 collates Confirm, Cancel, Pg Dn and Pg Up into 0x7E0D1D ,
        for use with BMI and BVS opcodes for efficient checking of the two most common inputs.

        #Used for basically everywhere inside shops, menu (including techs), and inventory.
        '''
        rom.seek(0x0293C9 + 1) # BIT $02
        rom.write(0x01.to_bytes(1, 'little'))

        '''
        Battle inventory scrolling is handled by a different subroutine than menu inventory scrolling.
        It does not collate input like the menu program, and instead isolates bitmasks of translated input
        sourced from $fb and $fc. The function of note 0x01143D controls input during Item menu.
        Overwrite the checks to reverse their effects.
        '''
        rom.seek(0x011477 + 1) # AND #$20
        rom.write(0x10.to_bytes(1, 'little'))
        
        rom.seek(0x011483 + 1) # AND #$10
        rom.write(0x20.to_bytes(1, 'little'))
        

if __name__ == '__main__':
    pass