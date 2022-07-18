'''
Module for preconfiguring in-game options at compile time
'''

from ctenums import ActionMap, InputMap
from ctrom import CTRom

'''
TODO fill in explaination of controller remapping CT uses
'''

class ControllerBinds:
    def __init__(self, data: bytearray = None):

        self._mappings = self.get_vanilla()
        
        if data is None:
            return
    
        #only support 8 or 11 bytes
        if len(data) == 11:
            self.update_from_bytes(data[3:])
        elif len(data) == 8:
            self.update_from_bytes(data[:])
        else:
            raise ValueError('Button mappings must be either 8 or 11 bytes in length')
            exit()

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

    #return bytearray in order CT expects it in, suitable for writing back to CTRom
    def to_bytearray(self):
    
        ret = bytearray(8)
        
        for idx, button in enumerate(self._mappings.values()):
            ret[idx] = button
        
        return ret

    #updates button bindings given bytearray; bytearray assumed to be ordered in the same way as out
    def update_from_bytes(self, bytes: bytearray):

        if not len(bytes) == 8:
            raise ValueError('bytes must be 8 bytes long')
            return

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
            The in-use copy, used by 0x028585 and therefore everywhere that respects user binds; 7E2993
            
            The persistant user copy, saved from RAM to SRAM when the user saves the game; 7e0408
            
            A cache of the persistant user copy, exists when user is editing binds ; 7e9890
            
            User proposed copy, edited when user is rebinding and checked against the cached copy
            to prevent undesired lack of actions being bound to a button. ; 7e0f00
                
        To mimic reference functions at c2c5c7 (checks for overlap):
        
        Save the original state of target action
        Iterate over array, replace actions which match target action with original action.
        Write target action to target button
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
    CONFIG_LENGTH = 11
    
    def __init__(self):
                
        self._data = self.get_vanilla()
               
        #Controller bitmasks
        self.controller_binds = ControllerBinds(self._data)
        
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
    def from_rom(self, ct_rom: CTRom, offset: int = CONFIG_OFFSET):
        rom = ct_rom.rom_data
        
        orig_pos = rom.tell()
        
        rom.seek(offset)
        data = rom.read(self.CONFIG_LENGTH)
        rom.seek(orig_pos)
        
        return bytearray(data)

    #write current configuration to provided CTRom
    def write_to_ctrom(self, ct_rom: CTRom, offset: int = CONFIG_OFFSET):
        
        orig_pos = ct_rom.rom_data.tell()
        self.custom_control_pad = False # update the controller settings if different from vanilla
        
        out = self.to_bytearray()
        
        ct_rom.rom_data.seek(offset)
        ct_rom.rom_data.write(out)
                
        ct_rom.rom_data.seek(orig_pos)
    
    def update_from_bytes(self, data: bytearray):
        self._data[0:3] = data[0:3]
        
    #Returns all bytes of config, including current controller button bindings, suitable for writing back to CTRom
    def to_bytearray(self):
    
        options = bytearray(self._data[0:3])
        controls = self.controller_binds.to_bytearray()
        
        return options + controls
        
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
        #print(f'debug inside stereo_audio setter, before write: {bool(self.get_opt(0, 0x08))}')
        self.set_opt(0, 0x08, filt)
        #print(f'debug inside stereo_audio setter, after write: {bool(self.get_opt(0, 0x08))}')
        
    @property
    #Bit clear == standard controls, bit set == custom controls
    def custom_control_pad(self):
        return bool(self.get_opt(0, 0x10))
        
    @custom_control_pad.setter
    #Force the custom controller on if it deviates from vanilla settings
    #TODO: actually make CT respect this with some free bytes and editing c2c599 controller button mapping update function
    #current revision s/b no visible change from custom and default controls when toggling setting in game (unless, ofc, the player has rebound their controls previously)
    def custom_control_pad(self, val):
        if self.controller_binds.to_bytearray() != bytearray(self.controller_binds.get_vanilla().values()):
            #print(f'inside custom_control_pad setter, binds were not equal')
            #print(f'self.controller_binds.to_bytearray(): {self.controller_binds.to_bytearray()}')
            #print(f'bytearray(self.controller_binds.get_vanilla()): {bytearray([x for x in self.controller_binds.get_vanilla().values()])}')
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
        #print(f'debug inside save_menu_cursor setter, before write: {bool(self.get_opt(0, 0x20))}')
        self.set_opt(0, 0x20, filt)
        #print(f'debug inside save_menu_cursor setter, after write: {bool(self.get_opt(0, 0x20))}')

    @property
    #Bit clear == battle mode is Wait, bit set == battle mode is Active
    def active_battle(self):
        return bool(self.get_opt(0, 0x40))
        
    @active_battle.setter
    def active_battle(self, val):
        filt = bool(val)
        #print(f'debug inside active_battle setter, before write: {bool(self.get_opt(0, 0x40))}')
        self.set_opt(0, 0x40, filt)
        #print(f'debug inside active_battle setter, before write: {bool(self.get_opt(0, 0x40))}')
        
    @property
    #Bit clear == in battle, tech and item descriptions are not displayed, bit set == in battle, tech and item descriptions are displayed
    def skill_item_info(self):
        return bool(self.get_opt(0, 0x80))
        
    @skill_item_info.setter
    def skill_item_info(self, val):
        filt = bool(val)
        #print(f'debug inside active_battle setter, before write: {bool(self.get_opt(0, 0x40))}')
        self.set_opt(0, 0x80, filt)
        #print(f'debug inside active_battle setter, after write: {bool(self.get_opt(0, 0x40))}')

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
        #print(f'debug inside save_battle_cursor, before write: {bool(self.get_opt(1, 0x40))}')
        self.set_opt(1, 0x40, filt)
        #print(f'debug inside save_battle_cursor setter, after write: {bool(self.get_opt(1, 0x40))}')
        
    @property
    #Bit clear == tech and inventory cursors are not kept, bit set == tech cursors for each PC, and one for item inventory, are kept
    def save_tech_cursor(self):
        return bool(self.get_opt(1, 0x80))
        
    @save_tech_cursor.setter
    def save_tech_cursor(self, val):
        filt = bool(val)
        #print(f'debug inside save_tech_cursor setter, before write: {bool(self.get_opt(1, 0x80))}')
        self.set_opt(1, 0x80, filt)
        #print(f'debug inside save_tech_cursor setter, after write: {bool(self.get_opt(1, 0x80))}')

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
        
        #print(f'#~~~ inside set_opt, self._data[idx] before: {hex(self._data[idx])}')
        self._data[idx] = isolated | (val << shift)
        #print(f'#~~~ inside set_opt, self._data[idx] after: {hex(self._data[idx])}')
            
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

#TODO actually flesh this out
def add_user_binds_to_new_games():
    '''
    Add an event to new game setup to copy the button binds to persistant user storage
    '''
    pass

if __name__ == '__main__':
    pass