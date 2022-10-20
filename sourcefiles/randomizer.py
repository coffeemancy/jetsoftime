from __future__ import annotations

import os
import random
import pickle
import sys
import json

import charassign
import enemystats
import itemdata
import itemrando
from characters import pcrecruit, ctpcstats
from maps import mapmangler
from treasures import treasurewriter, treasuretypes
from shops import shopwriter
import logicwriters as logicwriter
import bossrandoevent as bossrando
import bossrandotypes as rotypes
import bossscaler
import tabchange as tabwriter
import fastmagic
import fastpendant
import charrando
import roboribbon
import techrandomizer
import qolhacks
import cosmetichacks
import bucketfragment
import iceage
import legacyofcyrus
import mystery
from vanillarando import vanillarando
import epochfail
import flashreduce
import seedhash
import prismshard

import byteops
import ctenums
import ctevent
from ctrom import CTRom
import ctstrings
import enemyrewards

# from freespace import FSWriteType
import randoconfig as cfg
import randosettings as rset

from jotjson import JOTJSONEncoder


class NoSettingsException(Exception):
    pass


class NoConfigException(Exception):
    pass


class Randomizer:

    def __init__(self, rom: bytearray, is_vanilla: bool = True,
                 settings: rset.Settings = None,
                 config: cfg.RandoConfig = None):

        # We want to keep a copy of the base rom around so that we can
        # generate many seeds from it.
        self.base_ctrom = CTRom(rom, ignore_checksum=not is_vanilla)
        self.out_rom = None
        self.has_generated = False

        self.settings = settings
        self.config = config

    # The randomizer will hold onto its last generated rom in self.out_rom
    # The settings and config are made properties so that I can update
    # whether out_rom correctly reflects the settings/config.
    @property
    def settings(self):
        return self._settings

    @settings.setter
    def settings(self, new_settings: rset.Settings):
        self._settings = new_settings
        self.has_generated = False

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, new_config: cfg.RandoConfig):
        self._config = new_config
        self.has_generated = False

    # Given the settings passed to the randomizer, give the randomizer a
    # random RandoConfig object.
    def set_random_config(self):
        if self.settings is None:
            raise NoSettingsException

        random.seed(self.settings.seed)

        if rset.GameFlags.MYSTERY in self.settings.gameflags:
            self.settings = mystery.generate_mystery_settings(self.settings)

        # Some of the config defaults (prices, techdb, enemy stats) are
        # read from the rom.  This routine partially patches a copy of the
        # base rom, gets the data, and builds the base config.
        self.config = Randomizer.get_base_config_from_settings(
            bytearray(self.base_ctrom.rom_data.getvalue()),
            self.settings
        )

        # An alternate approach is to build the base config with the pickles
        # provided.  You just have to make sure to redump any time time that
        # patch.ips or hard.ips change.  Below is how you would use pickles.
        '''
        with open('./pickles/default_randoconfig.pickle', 'rb') as infile:
            self.config = pickle.load(infile)

        if self.settings.enemy_difficulty == rset.Difficulty.HARD:
            with open('./pickles/enemy_dict_hard.pickle', 'rb') as infile:
                self.config.enemy_dict = pickle.load(infile)
        '''

        # Character config.  Includes tech randomization and who can equip
        # which items.
        charrando.write_config(self.settings, self.config)
        techrandomizer.write_tech_order_to_config(self.settings,
                                                  self.config)

        # Fast Magic.  Should be fine before or after charrando.
        # Safest after.
        fastmagic.write_config(self.settings, self.config)

        # Treasure config.
        treasurewriter.write_treasures_to_config(self.settings, self.config)

        # Enemy rewards
        enemyrewards.write_enemy_rewards_to_config(self.settings, self.config)

        # Key item config.  Important that this goes after treasures because
        # otherwise the treasurewriter can overwrite key items placed by
        # Chronosanity
        logicwriter.commitKeyItems(self.settings, self.config)

        # Now go write LW extra items if need be
        treasurewriter.add_lw_key_item_gear(self.settings, self.config)

        # Shops
        shopwriter.write_shops_to_config(self.settings, self.config)

        # Robo's Ribbon in itemdb
        roboribbon.set_robo_ribbon_in_config(self.config)

        # Item Rando
        # Important this is done after roboribbon or itemrando gets confused
        # over which stat boost is +3 speed
        itemrando.write_item_prices_to_config(self.settings, self.config)
        itemrando.randomize_healing(self.settings, self.config)
        itemrando.randomize_accessories(self.settings, self.config)
        itemrando.randomize_weapon_armor_stats(self.settings, self.config)
        self.config.item_db.update_all_descriptions()

        # Boss Rando
        bossrando.write_assignment_to_config(self.settings, self.config)

        # We need the boss rando assignment to determine which bosses need
        # additional bossscaler scaling.  That is accomplished by the above
        # bossrando.write_assignment_to_config.

        # Then, scale based on ranking.
        # This has to come before boss rando scaling  because some boss scaling
        # changes are defined absolutely instead of relatively, so they would
        # just overwrite the boss rando scaling.
        bossscaler.determine_boss_rank(self.settings, self.config)

        # Finally, scale based on new location.
        bossrando.scale_bosses_given_assignment(self.settings, self.config)

        # Black Tyrano/Magus boss randomization
        bossrando.randomize_midbosses(self.settings, self.config)

        # Tabs
        tabwriter.write_tabs_to_config(self.settings, self.config)

        # Bucket
        bucketfragment.write_fragments_to_config(self.settings, self.config)

        # Omen elevator
        self.__update_key_item_descs()
        self.__set_omen_elevators_config()

        # Ice age GG buffs if IA flag is present in settings.
        iceage.write_config(self.settings, self.config)


    @classmethod
    def __set_fast_zeal_teleporters(cls, ct_rom: CTRom):
        '''
        Warp straight from the bottom of the mountain to the top.
        '''

        EC = ctevent.EC

        script = ct_rom.script_manager.get_script(
            ctenums.LocID.ZEAL_TELEPORTERS
        )
        bot_loc_cmd = EC.change_location(ctenums.LocID.ZEAL_TELEPORTERS,
                                         0x1F, 0x0E,
                                         3, 1, False)
        new_bot_loc_cmd = EC.change_location(ctenums.LocID.ZEAL_TELEPORTERS,
                                             0x35, 0x0E,
                                             3, 1, False)

        pos = script.find_exact_command(bot_loc_cmd)
        script.data[pos:pos+len(bot_loc_cmd)] = new_bot_loc_cmd.to_bytearray()

        top_loc_cmd = EC.change_location(ctenums.LocID.ZEAL_TELEPORTERS,
                                         0x0A, 0x26,
                                         3, 1, False)
        new_top_loc_cmd =EC.change_location(ctenums.LocID.ZEAL_TELEPORTERS,
                                            0x0A, 0xE,
                                            3, 1, False)

        pos = script.find_exact_command(top_loc_cmd)
        script.data[pos:pos+len(bot_loc_cmd)] = new_top_loc_cmd.to_bytearray()


    @classmethod
    def __set_fast_magus_castle(cls, ct_rom: CTRom):
        '''
        Do not require the player to visit the Flea and Slash room in castle
        Magus.

        This function sets the flags for visiting the Flea and Slash rooms
        in the telepod exhibit script.  The flags 0x7F00A3 & 0x10/0x20 are
        unused in other events.
        '''
        script = ct_rom.script_manager.get_script(
            ctenums.LocID.TELEPOD_EXHIBIT
        )
        EC = ctevent.EC

        # Just put it at the start of the animation.  No reason to be fancy
        hook_pos = script.get_function_start(0x0E, 4)

        # Slash's Room: Set 0x7F00A3 & 0x10
        # Flea's Room: Set 0x7F00A3 & 0x20
        set_flags_cmd = EC.assign_val_to_mem(0x30, 0x7F00A3, 1)
        script.insert_commands(set_flags_cmd.to_bytearray(), hook_pos)

    @classmethod
    def __add_cat_pet_flag(cls, ct_rom: CTRom, addr: int, bit: int):
        '''
        Uses the bit (addr & bit) to determine whether a player has pet the
        cat in Crono's house.
        '''
        script = ct_rom.script_manager.get_script(
            ctenums.LocID.CRONOS_KITCHEN
        )
        pos = script.get_function_start(0x09, 0x01)

        EC = ctevent.EC
        cmd = EC.set_bit(addr, bit)

        script.insert_commands(cmd.to_bytearray(), pos)

    @classmethod
    def __set_initial_gold(cls, ct_rom: CTRom, gold: int):
        script = ct_rom.script_manager.get_script(ctenums.LocID.LOAD_SCREEN)

        # Cmd 4E (copy) to 0x7E2C53
        cmd_b = bytes.fromhex('4E532C7E0500')
        payload = gold.to_bytes(3, 'little')

        pos = script.data.find(cmd_b)
        pos += len(cmd_b)
        script.data[pos:pos+3] = payload[:]

    def __update_key_item_descs(self):
        config = self.config
        IID = ctenums.ItemID

        item_db = config.item_db
        item_db[IID.GATE_KEY].set_desc_from_str(
            'Unlocks 65m BC (Medina imp closet)'
        )

        item_db[IID.PENDANT].set_desc_from_str(
            'Unlocks future (Castle 1000 Lawyer)'
        )

        item_db[IID.DREAMSTONE].set_desc_from_str(
            'Opens Tyrano Lair (Kino cell switch)'
        )

        item_db[IID.RUBY_KNIFE].set_desc_from_str(
            'Opens Zeal Throneroom'
        )

        item_db[IID.BENT_SWORD].set_desc_from_str(
            'Forge Masa w/ Hilt (Melchior\'s Hut)'
        )

        item_db[IID.BENT_HILT].set_desc_from_str(
            'Forge Masa w/ Blade (Melchior\'s Hut)'
        )

        item_db[IID.PRISMSHARD].set_desc_from_str(
            'Start Shell Trial (King 600 w/ Marle)'
        )

        item_db[IID.TOMAS_POP].set_desc_from_str(
            'Open GiantsClaw (Choras 1000 grave)'
        )

        item_db[IID.CLONE].set_desc_from_str(
            'Go DthPeak (KeeperDome w/ CT)'
        )

        item_db[IID.C_TRIGGER].set_desc_from_str(
            'Go DthPeak (KeeperDome w/ Clone)'
        )

        item_db[IID.JERKY].set_desc_from_str(
            'Unlock Porre Mayor (Porre Elder)'
        )

        medal_desc = item_db[IID.HERO_MEDAL].get_desc_as_str()
        medal_desc += ' (Frog\'s Chest)'
        item_db[IID.HERO_MEDAL].set_desc_from_str(medal_desc)

        if self.settings.game_mode == rset.GameMode.VANILLA_RANDO or \
           rset.GameFlags.USE_EXTENDED_KEYS in self.settings.gameflags:
            item_db[IID.C_TRIGGER].set_desc_from_str(
                'Go DthPeak (KeeperDome), Bekkler'
            )
            item_db[IID.TOOLS].set_desc_from_str(
                'Repair Ruins (Choras Cafe)'
            )
            item_db[IID.JETSOFTIME].set_desc_from_str(
                'Upgrade Epoch (Blackbird)'
            )
            item_db[IID.SEED].set_desc_from_str(
                'Give to Doan after CPU (Arris)'
            )
            item_db[IID.BIKE_KEY].set_desc_from_str(
                'Walk Lab32 + RaceLog Box'
            )
            item_db[IID.SUN_STONE].set_desc_from_str(
                'Give to Melchior after King\'s Trial'
            )
        else:
            grandleon_desc = item_db[IID.MASAMUNE_2].get_desc_as_str()
            grandleon_desc += ' (Tools)'
            item_db[IID.MASAMUNE_2].set_desc_from_str(grandleon_desc)

    def __accelerate_carpenter_quest(self, ct_rom: CTRom):
        '''
        Just repair the whole ruins on the first visit.
        '''

        script = ct_rom.script_manager.get_script(
            ctenums.LocID.CHORAS_CARPENTER_600
        )

        EC = ctevent.EC
        EF = ctevent.EF

        hook_cmd = EC.set_bit(0x7F019F, 0x2)

        hook_pos = script.find_exact_command(
            hook_cmd,
            script.get_function_start(8, 1)
        ) + len(hook_cmd)

        func = (
            EF()
            .add(EC.set_bit(0x7F019F, 0x04))
            .add(EC.set_bit(0x7F019F, 0x08))
        )


        script.insert_commands(func.get_bytearray(), hook_pos)


    def __fix_northern_ruins_sealed(self, ct_rom: CTRom):
        # In Vanilla 0x7F01A3 & 0x10 is set for 600AD ruins
        #            0x7F01A3 & 0x08 is set for 1000AD ruins

        # In Jets 0x7F01A3 & 0x20 is set for 1000AD ruins
        #         0x7F01A3 & 0x10 is set for 600AD ruins

        # In 0x44 Northern Ruins Antechamber, Object 0x10
        #   Past obtained - 0x7F01A6 & 0x01
        #   Present obtained - 0x7F01A9 & 0x20
        #   Charged - 0x7F01A6 & 0x08  (Freed up)
        # Jets does some different things, but we'll use the vanilla values b/c
        # they seem to not have been repurposed.
        # Note: This frees up 0x7F01A6 & 0x08 for other use.
        # Note to note.  We're using 0x7F01A6 for the cat counter.
        script = ctevent.Event.from_flux(
            './flux/VR_044_Northern_Ruins_Ante.Flux'
        )
        ct_rom.script_manager.set_script(
            script,
            ctenums.LocID.NORTHERN_RUINS_ANTECHAMBER
        )

        # In 0x46 Northern Ruins Back Room, there two chests:
        # 1) Object 0x10
        #      Past obtained - 0x7F01A6 & 0x02
        #      Present obtained - 0x7F01A9 & 0x40
        #      Charged - 0x7F01A6 & 0x10  (Freed up)
        # 1) Object 0x11
        #      Past obtained - 0x7F01A6 & 0x04
        #      Present obtained - 0x7F01A9 & 0x80
        #      Charged - 0x7F01A6 & 0x20  (Freed up)
        script = ctevent.Event.from_flux(
            './flux/VR_046_Northern_Ruins_Back.Flux'
        )
        ct_rom.script_manager.set_script(
            script,
            ctenums.LocID.NORTHERN_RUINS_BACK_ROOM
        )

    def __update_trading_post_string(self, ct_rom: CTRom,
                                     config: cfg.RandoConfig):
        script_man = ct_rom.script_manager

        script = script_man.get_script(ctenums.LocID.IOKA_TRADING_POST)

        # Petal, Fang -> Ranged
        # Petal, Horn -> Accessory
        # Petal, Feather -> Tab
        # Fang, Horn -> Melee
        # Fang, Feather -> Armor
        # Horn, Feather -> Helm

        TID = ctenums.TreasureID
        tp_spots = (TID.TRADING_POST_RANGED_WEAPON,
                    TID.TRADING_POST_ACCESSORY,
                    TID.TRADING_POST_TAB,
                    TID.TRADING_POST_MELEE_WEAPON,
                    TID.TRADING_POST_ARMOR,
                    TID.TRADING_POST_HELM)

        tp_name_dict = dict()

        item_db = config.item_db
        CTName = ctstrings.CTNameString
        for treasure_id in tp_spots:
            item_id = config.treasure_assign_dict[treasure_id].reward
            name_b = CTName(item_db[item_id].name[1:])
            name = str(name_b)
            tp_name_dict[treasure_id] = name

        new_str = \
            'Many things for trade!{line break}'\
            f'Petal, Fang: {tp_name_dict[TID.TRADING_POST_RANGED_WEAPON]}'\
            '{line break}'\
            f'Petal, Horn: {tp_name_dict[TID.TRADING_POST_ACCESSORY]}'\
            '{line break}'\
            f'Petal, Feather: {tp_name_dict[TID.TRADING_POST_TAB]}'\
            '{page break}'\
            f'Fang, Horn: {tp_name_dict[TID.TRADING_POST_MELEE_WEAPON]}'\
            '{line break}'\
            f'Fang, Feather: {tp_name_dict[TID.TRADING_POST_ARMOR]}'\
            '{line break}'\
            f'Horn, Feather: {tp_name_dict[TID.TRADING_POST_HELM]}'\
            '{null}'

        new_ct_str = ctstrings.CTString.from_str(new_str)
        new_ct_str.compress()
        script.strings[2] = new_ct_str
        script.modified_strings = True

    def __disable_xmenu_charlocks(self, ct_rom):
        '''Ignore the charlock byte when in the X-menu but not Y-menu.'''

        rom = ct_rom.rom_data
        space_man = rom.space_manager

        rt = bytearray.fromhex(
            'AD 36 0D'     # LDA $0D36  [$7E:0D36]  (will be FF in Y-menu, 0 X)
            '10 04'        # BPL foo
            'A9 00'        # LDA #$00 (no charlock byte)
            '80 04'        # BRA bar
            'AF DF 01 7F'  # LDA $7F01DF[$7F:01DF] (charlock byte) [foo]
            '6B'           # RTL [bar]
        )

        start = space_man.get_free_addr(len(rt))
        rom_start = byteops.to_rom_ptr(start)
        rom_start_b = rom_start.to_bytes(3, 'little')
        jsl = b'\x22' + rom_start_b

        rom.seek(0x02CD55)
        rom.write(jsl)

        mark_used = ctevent.FSWriteType.MARK_USED
        rom.seek(start)
        rom.write(rt, mark_used)

    def __set_omen_elevators_config(self):
        '''Determine which omen elevator encounters a seed gets.'''
        # Ruminators, goons, cybots
        fight_thresh_up = [0xA0, 0x60, 0x80]
        fight_thresh_down = [0x80, 0x60, 0xA0]
        fights_up = [ind for ind, thresh in enumerate(fight_thresh_up)
                     if random.randrange(0, 0x100) < thresh]
        fights_down = [ind for ind, thresh in enumerate(fight_thresh_down)
                       if random.randrange(0, 0x100) < thresh]

        self.config.omen_elevator_fights_up = fights_up
        self.config.omen_elevator_fights_down = fights_down

    def __set_omen_elevator_ctrom(self, ctrom: CTRom,
                                  fights: list[int],
                                  loc_id: ctenums.LocID):
        '''Write an omen elevator encounters to the rom.'''
        script_man = ctrom.script_manager
        script = script_man.get_script(loc_id)

        start = script.get_function_start(0, 0)
        end = script.get_function_end(0, 0)

        # There are three commands (0x7F) that load a random number.
        # These random numbers are then compared to some thresholds to
        # determine whether a fight occurs.
        pos = start
        for i in range(3):
            pos, cmd = script.find_command([0x7F], pos, end)
            offset = cmd.args[0]

            # Get a val to local mem command
            new_cmd = ctevent.EC.get_blank_command(0x4F)
            new_cmd.args[1] = offset

            # If we determined that fight i should occur, store a 0 to the
            # location that would have held the random number.  It will pass
            # any threshold.  Otherwise, assign 0xFF to fail any threshold.
            if i in fights:
                val = 0
            else:
                val = 0xFF

            new_cmd.args[0] = val

            # delete the get random command.  Put in the val-to-mem command.
            script.delete_commands(pos, 1)
            script.insert_commands(new_cmd.to_bytearray(),  pos)

            pos += len(new_cmd)

    def __set_omen_elevators_ctrom(self, ctrom: CTRom,
                                   config: cfg.RandoConfig):
        '''Set both omen elevators'''
        fights = [config.omen_elevator_fights_down,
                  config.omen_elevator_fights_up]
        loc_ids = [ctenums.LocID.BLACK_OMEN_ELEVATOR_DOWN,
                   ctenums.LocID.BLACK_OMEN_ELEVATOR_UP]

        for x in list(zip(loc_ids, fights)):
            elev_fights = x[1]
            elev_loc_id = x[0]

            self.__set_omen_elevator_ctrom(ctrom, elev_fights, elev_loc_id)

    def __lavos_ngplus(self):
        '''Removes a check for dead Mammon Machine on Lavos NG+'''
        script_man = self.out_rom.script_manager
        script = script_man.get_script(ctenums.LocID.TESSERACT)

        start = script.get_function_start(0, 0)
        end = script.get_function_end(0, 0)

        pos, cmd = script.find_command([0x16], start, end)
        if cmd.args[0:3] == [0xA8, 0x80, 0x86]:
            script.delete_commands(pos, 1)
        else:
            print('failed to find mm flag')

    def __try_supervisors_office_recruit_fix(self):
        '''
        Removes a premature ExploreMode On to prevent losing a recruit.
        '''
        loc_id = ctenums.LocID.PRISON_SUPERVISORS_OFFICE
        script = ctevent.Event.from_flux(
            './flux/jot_01D_Prison_Supervisor.Flux'
        )

        self.out_rom.script_manager.set_script(script, loc_id)

    def __try_mystic_mtn_portal_fix(self):
        '''
        Removes touch == activate from dactyl portal.  Maybe this fixes?
        '''
        loc_id = ctenums.LocID.MYSTIC_MTN_PORTAL
        script = self.out_rom.script_manager.get_script(loc_id)

        EF = ctevent.EF
        EC = ctevent.EC

        # Make a function that's just a return
        func = EF()
        func.add(EC.return_cmd())

        # Set the touch (0x02) function of the portal activation obj (0x0A)
        # to just return.
        script.set_function(0x0A, 0x02, func)

    def __try_proto_dome_fix(self):
        '''Removes touch == activate from proto recruit.  Maybe this fixes?'''
        script_man = self.out_rom.script_manager
        script = script_man.get_script(ctenums.LocID.PROTO_DOME)

        EF = ctevent.EF
        EC = ctevent.EC

        # Make a function that's just a return
        func = EF()
        func.add(EC.return_cmd())

        # Set the touch (0x02) function of the recruit obj (0x18) to the
        # return function.
        script.set_function(0x18, 0x02, func)

    def generate_rom(self):
        '''
        Turns settings + config into self.out_rom.
        '''
        if self.settings is None:
            raise NoSettingsException

        if self.config is None:
            raise NoConfigException

        if self.has_generated:
            return

        # With valid config and settings, we can write generate the rom
        self.__write_out_rom()

    # There are no good tools for working with animation scripts.  The
    # change is small, so we're doing it directly
    def __modify_bh_script(self):
        ct_rom = self.out_rom

        # Replace a weird unknown command (bh-specfic) with show damage
        ct_rom.rom_data.seek(0x0E3191)
        ct_rom.rom_data.write(b'\x50')

        # Change the hit effect with dark matter's
        ct_rom.rom_data.seek(0x0E319C)
        ct_rom.rom_data.write(
            bytearray.fromhex(
                '2402' +
                '6900' +
                '2014' +
                '6A' +
                # '36' +
                '00'
            )
        )

    def __write_config_to_out_rom(self):
        '''
        Writes elements of the config to self.out_rom
        '''
        config = self.config
        ctrom = self.out_rom

        # We can always do this, even if not reverting to black hole because
        # antilife just uses life2's script, not black hole's....
        # ...unless we're in vanilla mode.
        if self.settings.game_mode != rset.GameMode.VANILLA_RANDO:
            self.__modify_bh_script()

        # Subtle Bug Alert:
        # AtkDB needs to count the number of attacks when determining whether
        # it needs to reallocate.  To do this, it reads enemy data.  If the
        # new enemy data is written first, it will read the wrong number of
        # attacks and free too much.  So the ai/atks are written first.
        config.enemy_ai_db.write_to_ctrom(ctrom)
        config.enemy_atk_db.write_to_ctrom(ctrom)

        # Write enemies out
        for enemy_id, stats in config.enemy_dict.items():
            stats.write_to_ctrom(ctrom, enemy_id)

        # Write treasures out -- this includes key items
        # for treasure in config.treasure_assign_dict.values():
        for tid in config.treasure_assign_dict:
            treasure = config.treasure_assign_dict[tid]
            treasure.write_to_ctrom(ctrom)

        # Write shops out
        config.shop_manager.write_to_ctrom(ctrom)

        # Write items out
        config.item_db.write_to_ctrom(ctrom)

        # Write characters out
        # Recruitment spots
        for character in config.char_assign_dict.values():
            character.write_to_ctrom(ctrom)

        charassign.fix_cursed_recruit_spots(config, ctrom)

        # Stats
        config.pcstats.write_to_ctrom(ctrom)

        # Write out the rest of the character data (incl. techs)
        charrando.reassign_characters_on_ctrom(ctrom, config)

        # Write out the bosses
        bossrando.write_bosses_to_ctrom(ctrom, config)

        # tabs
        tabwriter.rewrite_tabs_on_ctrom(ctrom, config)

        # Omen elevator
        self.__set_omen_elevators_ctrom(ctrom, config)

        # Disabling xmenu character locks is only relevant in LoC and IA, but
        # there's no reason not to just do it always.
        self.__disable_xmenu_charlocks(ctrom)

    def __write_out_rom(self):
        '''Given config and settings, write to self.out_rom'''
        self.out_rom = CTRom(self.base_ctrom.rom_data.getvalue(), True)

        # TODO:  Consider working some of the always-applied script changes
        #        Into patch.ips to improve generation speed.
        self.__apply_basic_patches(self.out_rom, self.settings)

        self.__apply_settings_patches(self.out_rom, self.settings)

        # This makes copies of heckran cave passagesways, king's trial,
        # and now Zenan Bridge so that all bosses can go there.
        # There's no reason not do just do this regardless of whether
        # boss rando is on.
        mapmangler.duplicate_maps_on_ctrom(self.out_rom)
        mapmangler.duplicate_zenan_bridge(self.out_rom,
                                          ctenums.LocID.ZENAN_BRIDGE_BOSS)

        # Script changes which can always be made
        Event = ctevent.Event
        script_manager = self.out_rom.script_manager

        # Three dc flag patches can be added regardless.  No reason not to.

        # 1) Set magic learning at game start depending on character assignment
        #    unless LW...because telepod exhibit now has the LW portal change.

        if self.settings.game_mode != rset.GameMode.LOST_WORLDS:
            telepod_event = Event.from_flux('./flux/cr_telepod_exhibit.flux')

            # 3.1.1 Change:
            # The only relevant script change with 3.1.1 is setting the
            # 0x80 bit of 0x7f0057 for the skyway logic in the Telepod
            # Exhibit script.
            EC = ctevent.EC

            # set flag cmd -- too lazy to make an EC function for this
            cmd = EC.generic_two_arg(0x65, 0x07, 0x57)
            start = telepod_event.get_function_start(0x0E, 0x04)
            end = telepod_event.get_function_end(0x0E, 0x04)

            # Set the flag right before the screen darkens
            pos = telepod_event.find_exact_command(EC.fade_screen(),
                                                   start, end)
            telepod_event.insert_commands(cmd.to_bytearray(), pos)

            script_manager.set_script(telepod_event,
                                      ctenums.LocID.TELEPOD_EXHIBIT)
        else:
            # The LW mode sets the magic-learned bits on the load screen.
            # We will just set them all.
            load_screen_event = script_manager.get_script(
                ctenums.LocID.LOAD_SCREEN
                )

            cmd = ctevent.EC.set_bit(0x7F01E0, 0x01)
            pos = load_screen_event.find_exact_command(cmd)

            new_cmd = ctevent.EC.assign_val_to_mem(0x7F, 0x7F01E0, 1)
            load_screen_event.insert_commands(new_cmd.to_bytearray(),
                                              pos)

        # 2) Allows left chest when medal is on non-Frog Frogs
        burrow_event = Event.from_flux('./flux/cr_burrow.Flux')

        # 3) Start Ruins quest when Grand Leon is on non-Frog Frogs
        choras_cafe_event = Event.from_flux('./flux/cr_choras_cafe.Flux')

        script_manager.set_script(burrow_event,
                                  ctenums.LocID.FROGS_BURROW)
        script_manager.set_script(choras_cafe_event,
                                  ctenums.LocID.CHORAS_CAFE)

        # 4) Fixed trading post script
        tp_event = Event.from_flux('./flux/jot_trading_post.Flux')
        script_manager.set_script(tp_event, ctenums.LocID.IOKA_TRADING_POST)

        # Flag specific script changes:
        #   - Locked characters changes to proto dome and dactyl nest
        #   - Duplicate characters changes to Spekkio when not in LW
        flags = self.settings.gameflags
        mode = self.settings.game_mode
        dup_chars = rset.GameFlags.DUPLICATE_CHARS in flags
        locked_chars = rset.GameFlags.LOCKED_CHARS in flags
        lost_worlds = rset.GameMode.LOST_WORLDS == mode
        vanilla = rset.GameMode.VANILLA_RANDO == mode
        epoch_fail = rset.GameFlags.EPOCH_FAIL in flags

        if dup_chars and not lost_worlds:
            # Lets Spekkio give magic properly to duplicates
            dc_spekkio_event = Event.from_flux('./flux/charrando-eot.flux')
            script_manager.set_script(dc_spekkio_event,
                                      ctenums.LocID.SPEKKIO)

        if locked_chars:
            lc_dactyl_upper_event = \
                Event.from_flux('./flux/lc_dactyl_upper.Flux')
            script_manager.set_script(lc_dactyl_upper_event,
                                      ctenums.LocID.DACTYL_NEST_UPPER)

            # Note: This changes the Proto Dome script, but it does not change
            #       which objects/functions have the char recruit data, so the
            #       randomization doesn't break.  If a script does change that
            #       data then self.config.char_assign_dict would change.
            # TODO: Just do surgery on the script instead of loading flux.
            lc_proto_dome_event = Event.from_flux('./flux/lc_proto_dome.Flux')
            script_manager.set_script(lc_proto_dome_event,
                                      ctenums.LocID.PROTO_DOME)

        # Proto fix, Mystic Mtn fix, and Lavos NG+ are candidates for being
        # rolled into patch.ips.

        prismshard.update_prismshard_quest(self.out_rom)

        if epoch_fail:
            epochfail.apply_epoch_fail(self.out_rom, self.settings)

        if vanilla:
            vanillarando.restore_scripts(self.out_rom)

        if mode == rset.GameMode.STANDARD and \
           rset.GameFlags.USE_EXTENDED_KEYS in self.settings.gameflags:
            vanillarando.apply_vanilla_keys_scripts(self.out_rom)

        if rset.GameFlags.UNLOCKED_MAGIC in self.settings.gameflags:
            fastmagic.add_tracker_hook(self.out_rom)

        # Don't require visiting Flea/Slash rooms for Magus's Castle
        if self.settings.game_mode != rset.GameMode.LOST_WORLDS:
            # The Telepod script is different in LW.  Just ignore.
            self.__set_fast_magus_castle(self.out_rom)

        self.__set_fast_zeal_teleporters(self.out_rom)

        # Use 0x7F01A6 for the cat counter.
        self.__add_cat_pet_flag(self.out_rom, 0x7F01A6, 0x08)

        # Split the NR "sealed" chests and make the quest a little faster.
        self.__fix_northern_ruins_sealed(self.out_rom)
        self.__accelerate_carpenter_quest(self.out_rom)

        # Update the trading post descriptions
        self.__update_trading_post_string(self.out_rom, self.config)

        # Two potential softlocks caused by (presumably) touch == activate.
        self.__try_proto_dome_fix()
        self.__try_mystic_mtn_portal_fix()

        # Potential recruit loss when characters rescue in prison
        self.__try_supervisors_office_recruit_fix()

        # Enable NG+ by defeating Lavos without doing Omen.
        self.__lavos_ngplus()

        # Everything prior was purely based on settings, not the randomization.
        # Now, write the information from the config to the rom.
        self.__write_config_to_out_rom()

        # Ice Age/LoC script changes need to go after the config is written
        # because the recruit spot works by changing all character recruit
        # commands into the recruit's version.  The code inserted by theen
        # recruit locks would get incorrectly changed by this.
        mode = self.settings.game_mode
        if mode == rset.GameMode.ICE_AGE:
            iceage.set_ice_age_recruit_locks(self.out_rom,
                                             self.config)
            iceage.set_ice_age_dungeon_locks(self.out_rom, self.config)
            iceage.set_ending_after_woe(self.out_rom)
        elif mode == rset.GameMode.LEGACY_OF_CYRUS:
            legacyofcyrus.write_loc_recruit_locks(self.out_rom,
                                                  self.config)
            legacyofcyrus.write_loc_dungeon_locks(self.out_rom)
            legacyofcyrus.set_ending_after_ozzies_fort(self.out_rom)
        elif mode == rset.GameMode.VANILLA_RANDO:
            vanillarando.restore_sos(self.out_rom, self.config)

        # Write and remove all scripts
        self.out_rom.write_all_scripts_to_rom(clear_scripts=True)

        # Put the seed hash on the active/wait screen
        seedhash.write_hash_string(self.out_rom)

        # Apply post-randomization changes
        self.__apply_cosmetic_patches(self.out_rom, self.settings)

        # Rewrite any scripts changed by post-randomization
        self.out_rom.write_all_scripts_to_rom()
        self.out_rom.fix_snes_checksum()
        self.has_generated = True

    def get_generated_rom(self) -> bytearray:
        if not self.has_generated:
            self.generate_rom()

        return self.out_rom.rom_data.getvalue()

    def write_spoiler_log(self, outfile):
        if isinstance(outfile, str):
            with open(outfile, 'w') as real_outfile:
                self.write_spoiler_log(real_outfile)
        else:
            self.write_settings_spoilers(outfile)
            self.write_tab_spoilers(outfile)
            self.write_consumable_spoilers(outfile)
            self.write_key_item_spoilers(outfile)
            self.write_boss_rando_spoilers(outfile)
            self.write_character_spoilers(outfile)
            self.write_boss_stat_spoilers(outfile)
            self.write_treasure_spoilers(outfile)
            self.write_drop_charm_spoilers(outfile)
            self.write_shop_spoilers(outfile)
            self.write_item_stat_spoilers(outfile)

    def write_json_spoiler_log(self, outfile):
        if isinstance(outfile, str):
            with open(outfile, 'w') as real_outfile:
                self.write_json_spoiler_log(real_outfile)
        else:
            json.dump(
                {"configuration": self.config,
                 "settings": self.settings},
                outfile, cls=JOTJSONEncoder
            )

    def _summarize_dupes(self):
        CharID = ctenums.CharID

        def summarize_single(choicelist):
            if len(choicelist) < 4:
                return "Only " + \
                    ", ".join([str(CharID(i)) for i in choicelist])
            elif len(choicelist) == 7:
                return "Any"
            else:
                return "No " + \
                    ", ".join([str(CharID(i))
                               for i in (set(range(7)) - set(choicelist))])

        chars = {c: summarize_single(self.settings.char_choices[c])
                 for c in range(len(self.settings.char_choices))}
        rv = ""
        for c in sorted(chars.keys()):
            if chars[c] != "Any":
                rv = rv + "\n\t" + str(CharID(c)) + ": " + chars[c]
        return rv

    def write_settings_spoilers(self, file_object):
        file_object.write(f"Game Mode: {self.settings.game_mode}\n")
        file_object.write(f"Enemies: {self.settings.enemy_difficulty}\n")
        file_object.write(f"Items: {self.settings.item_difficulty}\n")
        if self.settings.tab_settings != rset.TabSettings():
            tab_set = self.settings.tab_settings
            file_object.write(
                f"Tabs: Power {tab_set.power_min}-{tab_set.power_max}, "
                f"Magic {tab_set.magic_min}-{tab_set.magic_max}, "
                f"Speed {tab_set.speed_min}-{tab_set.speed_max}\n"
            )
        if rset.GameFlags.DUPLICATE_CHARS in self.settings.gameflags and \
           self.settings.char_choices != rset.Settings().char_choices:

            dupes = self._summarize_dupes()
            file_object.write(f"Characters: {dupes}\n")
        file_object.write(f"Techs: {self.settings.techorder}\n")
        file_object.write(f"Shops: {self.settings.shopprices}\n")
        file_object.write(f"Flags: {self.settings.gameflags}\n")
        file_object.write(f"Cosmetic: {self.settings.cosmetic_flags}\n\n")

    def write_consumable_spoilers(self, file_object):
        file_object.write("Consumable Properties\n")
        file_object.write("---------------------\n")

        IID = ctenums.ItemID
        consumables = (
            IID.TONIC, IID.MID_TONIC, IID.FULL_TONIC,
            IID.ETHER, IID.MID_ETHER, IID.FULL_ETHER,
            IID.LAPIS, IID.REVIVE
        )

        for item_id in consumables:
            item = self.config.item_db[item_id]
            name = ctstrings.CTNameString(item.name)
            name_str = str(name).ljust(15, ' ')
            desc = ctstrings.CTString(item.desc[:-1])  # Remove {null}
            desc_str = desc.to_ascii()

            file_object.write(name_str+desc_str+'\n')
        file_object.write('\n')

    def write_tab_spoilers(self, file_object):
        file_object.write("Tab Properties\n")
        file_object.write("--------------\n")

        tab_names = [
            'Power Tab',
            'Magic Tab',
            'Speed Tab'
        ]

        tab_magnitudes = [
            self.config.power_tab_amt,
            self.config.magic_tab_amt,
            self.config.speed_tab_amt
        ]

        for i in range(len(tab_names)):
            file_object.write(f'{tab_names[i]}: +{tab_magnitudes[i]}\n')

        file_object.write('\n')

    def write_key_item_spoilers(self, file_object):
        file_object.write("Key Item Locations\n")
        file_object.write("------------------\n")

        # We have to use the logicwriter's Location class only because
        # of Chronosanity's linked locations needing to be handled properly.

        width = max(len(x.getName()) for x in self.config.key_item_locations)

        for location in self.config.key_item_locations:
            item_id = location.lookupKeyItem(self.config)
            item_name = self.config.item_db[item_id].get_name_as_str(True)
            file_object.write(str.ljust(f"{location.getName()}", width+8) +
                              item_name + '\n')
        file_object.write('\n')
        file_object.write('Completion by Spheres:\n')
        spheres = logicwriter.get_proof_string_from_settings_config(
            self.settings, self.config
        )
        file_object.write(spheres + '\n')

    def write_character_spoilers(self, file_object):
        pcstats = self.config.pcstats
        char_assign = self.config.char_assign_dict

        file_object.write("Character Locations\n")
        file_object.write("-------------------\n")
        for recruit_spot in char_assign.keys():
            held_char = char_assign[recruit_spot].held_char
            reassign_char = \
                pcstats.get_character_assignment(held_char)
            file_object.write(str.ljust(f"{recruit_spot}", 20) +
                              f"{char_assign[recruit_spot].held_char}"
                              f" reassigned {reassign_char}\n")
        file_object.write('\n')

        file_object.write("Character Stats\n")
        file_object.write("---------------\n")

        CharID = ctenums.CharID
        dup_chars = rset.GameFlags.DUPLICATE_CHARS in self.settings.gameflags
        tech_db = self.config.tech_db

        for char_id in range(7):
            pc_id = CharID(char_id)
            file_object.write(f"{CharID(char_id)}:")
            if dup_chars:
                file_object.write(
                    f" assigned to {pcstats.get_character_assignment(pc_id)}"
                )
            file_object.write('\n')
            file_object.write(pcstats.pc_stat_dict[pc_id].__str__(self.config.item_db))

            file_object.write('Tech Order:\n')
            for tech_num in range(8):
                tech_id = 1 + 8*char_id + tech_num
                tech = tech_db.get_tech(tech_id)
                name = ctstrings.CTString.ct_bytes_to_techname(tech['name'])
                file_object.write(f"\t{name}\n")
            file_object.write('\n')

    def write_treasure_spoilers(self, file_object):
        # Where should the location groupings go?
        width = max(len(str(x))
                    for x in self.config.treasure_assign_dict.keys())

        file_object.write("Treasure Assignment\n")
        file_object.write("-------------------\n")
        treasure_dict = self.config.treasure_assign_dict
        for treasure in treasure_dict.keys():
            reward = treasure_dict[treasure].reward
            if isinstance(reward, ctenums.ItemID):
                name = self.config.item_db[reward].get_name_as_str(True)
            else:
                name = f'{reward}G'

            file_object.write(str.ljust(str(treasure), width+8) +
                              name + '\n')
        file_object.write('\n')

    def write_shop_spoilers(self, file_object):
        file_object.write("Shop Assigmment\n")
        file_object.write("---------------\n")
        file_object.write(
            self.config.shop_manager.__str__(self.config.item_db)
        )
        file_object.write('\n')

    def write_item_stat_spoilers(self, file_object):
        file_object.write("Item Stats\n")
        file_object.write("----------\n")

        # width = max(len(str(x)) for x in list(ctenums.ItemID)) + 8

        item_ids = [x for x in list(ctenums.ItemID)
                    if x in range(1, ctenums.ItemID(0xD0))]

        for item_id in item_ids:
            item = self.config.item_db[item_id]
            name = str(ctstrings.CTNameString(item.name[1:])).ljust(15, ' ')
            desc = ctstrings.CTString(item.desc[:-1]).to_ascii()
            price = str(item.price).rjust(5, ' ') + 'G'

            file_object.write(name + ' ' + price + ' ' + desc + '\n')
        file_object.write('\n')

    def write_boss_rando_spoilers(self, file_object):
        file_object.write("Boss Locations\n")
        file_object.write("--------------\n")

        boss_dict = self.config.boss_assign_dict
        boss_data_dict = self.config.boss_data_dict
        twin_type = boss_data_dict[rotypes.BossID.TWIN_BOSS].parts[0].enemy_id
        twin_name = self.config.enemy_dict[twin_type].name
        width = max(len(str(x)) for x in boss_dict.keys()) + 8

        for location in boss_dict.keys():
            if boss_dict[location] == rotypes.BossID.TWIN_BOSS:
                boss_name = 'Twin ' + str(twin_name)
            else:
                boss_name = str(boss_dict[location])

            file_object.write(
                str.ljust(str(location), width) +
                boss_name +
                '\n'
            )

        file_object.write('\n')

    def write_boss_stat_spoilers(self, file_object):

        scale_dict = self.config.boss_rank_dict
        BossID = rotypes.BossID

        file_object.write("Boss Stats\n")
        file_object.write("----------\n")

        endboss_ids = [
            BossID.LAVOS_SHELL, BossID.INNER_LAVOS, BossID.LAVOS_CORE,
            BossID.MAMMON_M, BossID.ZEAL, BossID.ZEAL_2
        ]

        boss_ids = list(self.config.boss_assign_dict.values()) + \
            [BossID.MAGUS, BossID.BLACK_TYRANO] + endboss_ids

        for boss_id in boss_ids:
            file_object.write(str(boss_id)+':')
            if boss_id in scale_dict.keys():
                file_object.write(
                    f" Key Item scale rank = {scale_dict[boss_id]}"
                )
            if boss_id == BossID.BLACK_TYRANO:
                tyrano_elem = bossrando.get_black_tyrano_element(self.config)
                file_object.write(
                    f" Element is {tyrano_elem}"
                )
            elif boss_id == BossID.RUST_TYRANO:
                tyrano_elem = bossrando.get_rust_tyrano_element(
                    ctenums.EnemyID.RUST_TYRANO, self.config
                )
                file_object.write(
                    f" Element is {tyrano_elem}"
                )
            elif boss_id == BossID.TWIN_BOSS:
                name = self.config.enemy_dict[ctenums.EnemyID.TWIN_BOSS].name
                if name == 'Rust Tyrano':
                    tyrano_elem = bossrando.get_rust_tyrano_element(
                        ctenums.EnemyID.TWIN_BOSS, self.config
                    )
                    file_object.write(
                        f" Element is {tyrano_elem}"
                    )
            elif boss_id == BossID.MEGA_MUTANT:
                part = ctenums.EnemyID.MEGA_MUTANT_BOTTOM
                obstacle_id = bossrando.get_obstacle_id(part, self.config)
                obstacle = self.config.enemy_atk_db.get_tech(obstacle_id)
                obstacle_status = obstacle.effect.status_effect
                status_string = ', '.join(str(x) for x in obstacle_status)
                file_object.write(f' Obstacle is {status_string}')
            elif boss_id == BossID.TERRA_MUTANT:
                part = ctenums.EnemyID.TERRA_MUTANT_HEAD
                obstacle_id = bossrando.get_obstacle_id(part, self.config)
                obstacle = self.config.enemy_atk_db.get_tech(obstacle_id)
                obstacle_status = obstacle.effect.status_effect
                status_string = ', '.join(str(x) for x in obstacle_status)
                file_object.write(f' Obstacle is {status_string}')

            file_object.write('\n')

            boss_scheme = self.config.boss_data_dict[boss_id]
            part_ids = [part.enemy_id for part in boss_scheme.parts]
            for part_id in part_ids:
                if len(part_ids) > 1:
                    file_object.write(f"Part: {part_id}\n")
                part_str = self.config.enemy_dict[part_id].__str__(
                    self.config.item_db
                )
                # put the string one tab out
                part_str = '\t' + str.replace(part_str, '\n', '\n\t')
                file_object.write(part_str+'\n')
            file_object.write('\n')

        obstacle = self.config.enemy_atk_db.get_tech(0x58)
        obstacle_status = obstacle.effect.status_effect
        status_string = ', '.join(str(x) for x in obstacle_status)
        file_object.write(f"Endgame obstacle is {status_string}\n\n")

    def write_drop_charm_spoilers(self, file_object):
        file_object.write("Enemy Drop and Charm\n")
        file_object.write("--------------------\n")

        EnTier = enemyrewards.RewardGroup
        get_enemies = enemyrewards.get_enemy_tier
        tiers = [
            get_enemies(EnTier.COMMON_ENEMY),
            get_enemies(EnTier.UNCOMMON_ENEMY),
            get_enemies(EnTier.RARE_ENEMY),
            get_enemies(EnTier.RAREST_ENEMY),
            (
                get_enemies(EnTier.EARLY_BOSS) +
                get_enemies(EnTier.MIDGAME_BOSS) +
                get_enemies(EnTier.LATE_BOSS)
            )
        ]

        labels = ['Common Enemies',
                  'Uncommon Enemies',
                  'Rare Enemies',
                  'Rarest Enemies',
                  'Bosses']

        ids = [x for tier in tiers for x in tier]
        width = max(len(str(x)) for x in ids) + 8

        item_db = self.config.item_db

        for ind, tier in enumerate(tiers):
            file_object.write(labels[ind] + '\n')
            for enemy_id in tier:
                drop_id = self.config.enemy_dict[enemy_id].drop_item
                drop_str = item_db[drop_id].get_name_as_str(True)
                charm_id = self.config.enemy_dict[enemy_id].charm_item
                charm_str = item_db[charm_id].get_name_as_str(True)
                file_object.write(
                    '\t' +
                    str.ljust(f"{enemy_id}", width) +
                    " Drop: " + drop_str + '\n'
                )
                file_object.write(
                    '\t' +
                    str.ljust("", width) +
                    "Charm: " + charm_str + '\n'
                )

        file_object.write('\n')

    # Because switching logic is a feature now, we need a settings object.
    # Ugly.  BETA_LOGIC flag is gone now, but keeping it as-is in case of
    # logic changes to test.
    @classmethod
    def __apply_basic_patches(cls, ctrom: CTRom,
                              settings: rset.Settings = None):
        '''Apply patches that are always applied to a jets rom.'''
        rom_data = ctrom.rom_data

        if settings is None:
            # Will give non-beta patch.  Outside of normal randomization,
            # where a settings object is provided, this function is only
            # called for dumping a basic config, and this won't change
            # depending on beta or not.
            settings = rset.Settings.get_race_presets()

        # Apply the patches that always are applied for jets
        # patch.ips makes sure that we have
        #   - Stats/stat growths for characters for CharManager
        #   - Tech data for TechDB
        #   - Item data (including prices) for shops
        # patch_codebase.txt may not be needed
        rom_data.patch_ips_file('./patch.ips')

        # 99.9% sure this patch is redundant now
        rom_data.patch_txt_file('./patches/patch_codebase.txt')

        # I verified that the following convenience patches which are now
        # always applied are disjoint from the glitch fix patches, so it's
        # safe to move them here.
        rom_data.patch_txt_file('./patches/fast_overworld_walk_patch.txt')
        rom_data.patch_txt_file('./patches/faster_epoch_patch.txt')
        rom_data.patch_txt_file('./patches/faster_menu_dpad.txt')

        # Add qwertymodo's MSU-1 patch
        # rom_data.patch_ips_file('./patches/chrono_msu1.ips')

    @classmethod
    def __apply_settings_patches(cls, ctrom: CTRom,
                                 settings: rset.Settings):
        '''Apply patches to a vanilla ctrom based on randomizer settings.  '''
        '''These are patches not handled by writing the config.'''

        rom_data = ctrom.rom_data
        flags = settings.gameflags
        mode = settings.game_mode

        if rset.GameFlags.FIX_GLITCH in flags:
            rom_data.patch_txt_file('./patches/save_anywhere_patch.txt')
            rom_data.patch_txt_file('./patches/unequip_patch.txt')
            rom_data.patch_txt_file('./patches/fadeout_patch.txt')
            rom_data.patch_txt_file('./patches/hp_overflow_patch.txt')

        # TODO:  I'd like to do this with .Flux event changes
        if rset.GameFlags.ZEAL_END in flags:
            rom_data.patch_txt_file('./patches/zeal_end_boss.txt')

        # Patching with lost.ips does not give a valid event for
        # mystic mountains.  I could fix the event by applying a flux file,
        # but I'm worried about what might happen when the invalid event is
        # marked free space.  For now we keep with older versions and apply the
        # mysticmtnfix.ips to restore the event.
        if rset.GameMode.LOST_WORLDS == mode:
            rom_data.patch_ips_file('./patches/lost.ips')
            rom_data.patch_ips_file('./patches/mysticmtnfix.ips')

        if rset.GameFlags.FAST_PENDANT in flags:
            if mode in (rset.GameMode.LOST_WORLDS,
                        rset.GameMode.LEGACY_OF_CYRUS):
                # Game modes where there is no pendant trial need to enforce
                # fast pendant by changing scripts.
                fastpendant.apply_fast_pendant_script(ctrom, settings)
            else:
                rom_data.patch_txt_file('./patches/fast_charge_pendant.txt')

        # Big TODO:  Unwrap the hard patch into its component changes.
        #            As far as I can tell it's just enemies and starting GP.
        # The only thing the hard.ips would do is set the initial gold.
        # We already read the enemy data with get_base_config_from_settings().
        if settings.item_difficulty == rset.Difficulty.HARD:
            cls.__set_initial_gold(ctrom, 10000)

        if rset.GameFlags.VISIBLE_HEALTH in flags:
            qolhacks.force_sightscope_on(ctrom, settings)

        qolhacks.set_guaranteed_drops(ctrom)

        if rset.GameFlags.FREE_MENU_GLITCH in flags:
            qolhacks.set_free_menu_glitch(ctrom, settings)

        if rset.GameFlags.UNLOCKED_MAGIC in flags:
            fastmagic.write_ctrom(ctrom, settings)

        if rset.GameFlags.FAST_TABS in flags:
            qolhacks.fast_tab_pickup(ctrom, settings)

        if rset.GameFlags.BUCKET_FRAGMENTS in flags and \
           settings.game_mode != rset.GameMode.LOST_WORLDS:
            # Apparently, LW really changes up the EoT event, so the bucket
            # function can't work.  It's ok because bucket should be disabled
            # in LW.
            bucketfragment.set_bucket_function(ctrom, settings)

    @classmethod
    def __apply_cosmetic_patches(cls, ctrom: CTRom,
                                 settings: rset.Settings):
        cos_flags = settings.cosmetic_flags

        if rset.CosmeticFlags.QUIET_MODE in cos_flags:
            cosmetichacks.apply_quiet_mode(ctrom, settings)

        if rset.CosmeticFlags.ZENAN_ALT_MUSIC in cos_flags:
            cosmetichacks.zenan_bridge_alt_battle_music(ctrom, settings)

        if rset.CosmeticFlags.DEATH_PEAK_ALT_MUSIC in cos_flags:
            cosmetichacks.death_peak_singing_mountain_music(ctrom, settings)

        cosmetichacks.set_pc_names(
            ctrom, *settings.char_names
        )

        if rset.CosmeticFlags.REDUCE_FLASH in cos_flags:
            flashreduce.apply_all_flash_hacks(ctrom)

        settings.ctoptions.write_to_ctrom(ctrom)

    @classmethod
    def dump_default_config(cls, ct_vanilla: bytearray):
        '''Turn vanilla ct rom into default objects for a config.
        Should run whenever a big patch (patch.ips, hard.ips) changes.'''
        ct_rom = CTRom(ct_vanilla, ignore_checksum=False)
        cls.__apply_basic_patches(ct_rom)

        RC = cfg.RandoConfig
        config = RC()
        cls.fill_default_config_entries(config)
        config.update_from_ct_rom(ct_rom)

        with open('./pickles/default_randoconfig.pickle', 'wb') as outfile:
            pickle.dump(config, outfile)


    @classmethod
    def fill_default_config_entries(cls, config: cfg.RandoConfig):
        config.boss_assign_dict = rotypes.get_default_boss_assignment()
        config.treasure_assign_dict = treasuretypes.get_base_treasure_dict()
        config.char_assign_dict = pcrecruit.get_base_recruit_dict()
        config.boss_rank_dict = {}

    @classmethod
    def get_base_config_from_settings(cls,
                                      ct_vanilla: bytearray,
                                      settings: rset.Settings):
        '''Gets an rset.RandoConfig object with the correct initial values.

        RandoConfig members which are read from rom_data after patches:
          - enemy_dict: holds stats depending on hard mode or not
          - shop_manager: This shouldn't be strictly needed, but at present
                          ShopManager objects read the initial shop data from
                          the rom.
          - price_manager: patch.ips changes the default prices.  Potentially
                           the difficulty patch could too.
          - char_manager: patch.ips changes character stat growths and base
                          stats.
          - tech_db: patch.ips changes the basic techs (i.e. Antilife)
          - enemy_atk_db: Various enemy techs are changed by patch.ips.
          - enemy_ai_db: Various enemy attack scripts are changed by patch.ips.
        '''

        # It's a little wasteful copying the rom data to partially patch it
        # to extract the base values for the above.

        # I do have a pickle with a default config and normal/hard enemy dicts
        # which can be used instead if this is an issue.  The problem with
        # using those is the need to update them with every patch.
        ct_rom = CTRom(ct_vanilla, True)
        Randomizer.__apply_basic_patches(ct_rom)
        config = cfg.RandoConfig()
        cls.fill_default_config_entries(config)
        config.boss_data_dict = rotypes.get_boss_data_dict()

        if settings.game_mode == rset.GameMode.VANILLA_RANDO:
            config.update_from_ct_rom(ct_vanilla)
            vanillarando.fix_config(config)

        else:
            config.update_from_ct_rom(ct_rom)

            if rset.GameFlags.USE_EXTENDED_KEYS in settings.gameflags:
                vanillarando.apply_vanilla_keys_to_config(config)

            # Get hard versions of config items if needed.
            # We're done with the rom at this point, so it's OK to patch
            # regardless.
            ct_rom.rom_data.patch_ips_file('./patches/hard.ips')
            if settings.enemy_difficulty == rset.Difficulty.HARD:
                config.enemy_dict = \
                    enemystats.get_stat_dict_from_ctrom(ct_rom)

            if settings.item_difficulty == rset.Difficulty.HARD:
                config.item_db = itemdata.ItemDB.from_rom(
                    ct_rom.rom_data.getvalue()
                )

            # Why is Dalton worth so few TP?
            config.enemy_dict[ctenums.EnemyID.DALTON_PLUS].tp = 50

            # Give Rusty a few more HP, like avg hp of old boss rando
            enemy_id = ctenums.EnemyID.RUST_TYRANO
            rt_stats = config.enemy_dict[enemy_id]

            rt_stats.hp = int(rt_stats.hp * 1.75)

            # Lower the base magic/lvl so that the party is likely to survive
            # the initial nuke.
            rt_stats.magic = int(rt_stats.magic * 0.6)
            rt_stats.level = int(rt_stats.level * 0.6)

            # Fix Falcon Hit to use Spincut as a prerequisite
            tech_db = config.tech_db
            falcon_hit = tech_db.get_tech(ctenums.TechID.FALCON_HIT)
            falcon_hit['lrn_req'][0] = int(ctenums.TechID.SPINCUT)
            tech_db.set_tech(falcon_hit, ctenums.TechID.FALCON_HIT)

            # Change Cure to ReRaise, Speed to 9 for Marle
            cure = tech_db.get_tech(ctenums.TechID.CURE)
            reraise = tech_db.get_tech(ctenums.TechID.LIFE_2_M)
            reraise['gfx'][0] = 0x87
            reraise['gfx'][6] = 0xFF
            reraise['control'][5] = 0x3E
            reraise['name'] = ctstrings.CTNameString.from_string(
                '*Reraise'
            )
            reraise['desc_ptr'] = None
            new_desc = ctstrings.CTString.from_str(
                'Greendream effect on one ally.{null}'
            )
            reraise['desc'] = new_desc
            reraise['target'] = bytearray(cure['target'])
            tech_db.mps[ctenums.TechID.CURE] = 15
            tech_db.set_tech(reraise, ctenums.TechID.CURE)
            tech_db.menu_usable_ids[ctenums.TechID.CURE] = False

            pcstats = config.pcstats
            pcstats.set_current_stat(ctenums.CharID.MARLE,
                                     ctpcstats.PCStat.SPEED,
                                     9)

            pcstats.pc_stat_dict[ctenums.CharID.FROG]\
                   .tp_threshholds[3] = 100

            # Reduce Robo tackle to 24 power (follow +15% rule)
            tackle_id = int(ctenums.TechID.ROBO_TACKLE)
            power_byte = tackle_id*tech_db.effect_size + 9
            tech_db.effects[power_byte] = 24

            # Now, the flag keeps tackle effects on (do nothing vs patch.ips)
            # If the flag is not present, reset the on-hit byte.
            if rset.GameFlags.TACKLE_EFFECTS_ON not in settings.gameflags:
                on_hit_byte = tackle_id*tech_db.effect_size + 8
                tech_db.effects[on_hit_byte] = 0

            # Revert antilife to black hole
            if rset.GameFlags.USE_ANTILIFE not in settings.gameflags:
                TechDB = charrando.TechDB
                vanilla_db = TechDB.get_default_db(ct_vanilla)
                black_hole = vanilla_db.get_tech(ctenums.TechID.ANTI_LIFE)

                anti_life = tech_db.get_tech(ctenums.TechID.ANTI_LIFE)
                anti_life['control'][8] = 0x16  # +Atk for down allies
                anti_life['effects'][0][9] = 0x20  # Megabomb power
                al_eff_id = anti_life['control'][5]

                # A note here that set_tech needs the effects to be set
                # correctly.
                # TODO: get_tech needs to be fixed to supply mp values so that
                #   set_tech can work as it ought.  Really fix the whole
                #   techdb.
                byteops.set_record(tech_db.effects, anti_life['effects'][0],
                                   al_eff_id,
                                   tech_db.effect_size)

                black_hole['control'] = anti_life['control']
                tech_db.set_tech(black_hole, ctenums.TechID.ANTI_LIFE)

                tech_db.pc_target[int(ctenums.TechID.ANTI_LIFE)] = 6

            # Make X-Strike use Spincut+Leapslash
            # Also buff 3d-attack and triple raid
            x_strike = tech_db.get_tech(ctenums.TechID.X_STRIKE)
            x_strike['control'][5] = int(ctenums.TechID.SPINCUT)
            x_strike['control'][6] = int(ctenums.TechID.LEAP_SLASH)

            # Crono's techlevel = 4 (spincut)
            # Frog's techlevel = 5 (leapslash)
            x_strike['lrn_req'] = [4, 5, 0xFF]

            x_strike['mmp'][0] = int(ctenums.TechID.SPINCUT)
            x_strike['mmp'][1] = int(ctenums.TechID.LEAP_SLASH)
            tech_db.set_tech(x_strike, ctenums.TechID.X_STRIKE)

            # 3d-atk
            three_d_atk = tech_db.get_tech(ctenums.TechID.THREE_D_ATTACK)
            three_d_atk['control'][6] = int(ctenums.TechID.SPINCUT)
            three_d_atk['control'][7] = int(ctenums.TechID.LEAP_SLASH)

            three_d_atk['mmp'][0] = int(ctenums.TechID.SPINCUT)
            three_d_atk['mmp'][1] = int(ctenums.TechID.LEAP_SLASH)

            three_d_atk['lrn_req'] = [4, 5, 8]
            tech_db.set_tech(three_d_atk, ctenums.TechID.THREE_D_ATTACK)

            # Triple Raid
            triple_raid = tech_db.get_tech(ctenums.TechID.TRIPLE_RAID)
            triple_raid['control'][5] = int(ctenums.TechID.SPINCUT)
            triple_raid['control'][7] = int(ctenums.TechID.LEAP_SLASH)

            triple_raid['mmp'][0] = int(ctenums.TechID.SPINCUT)
            triple_raid['mmp'][2] = int(ctenums.TechID.LEAP_SLASH)

            triple_raid['lrn_req'] = [4, 4, 5]
            tech_db.set_tech(triple_raid, ctenums.TechID.TRIPLE_RAID)

            # Ayla changes
            combo_tripkick_effect_id = 0x3D
            rock_tech_effect_id = int(ctenums.TechID.ROCK_THROW)

            effects = tech_db.effects
            power_byte = 9
            # Triple Kick combo power set to 0x2B=43 to match single
            # tech power
            trip_pwr = combo_tripkick_effect_id*tech_db.effect_size + \
                power_byte
            effects[trip_pwr] = 0x2B

            # Rock throw getting the 15% boost that tripkick got
            # From 0x1E=30 to 0x23=35
            rock_pwr = rock_tech_effect_id*tech_db.effect_size + power_byte
            effects[rock_pwr] = 0x23

        # The following changes can happen regardless of mode.
        if rset.GameFlags.EPOCH_FAIL in settings.gameflags:
            epochfail.update_config(config)

        # Add grandleon lowering magus's mdef
        # Editing AI is ugly right now, so just use raw binary
        magus_ai = config.enemy_ai_db.scripts[ctenums.EnemyID.MAGUS]
        magus_ai_b = magus_ai.get_as_bytearray()
        masa_hit = bytearray.fromhex(
            '18 3D 04 29 FE'
            '0B 3C 14 00 2E FE'
        )

        masa_hit_loc = magus_ai_b.find(masa_hit)
        masa_hit[1] = 0x42  # Change MM (0x3D) to GL (0x42)
        magus_ai_b[masa_hit_loc:masa_hit_loc] = masa_hit
        new_magus_ai = cfg.enemyai.AIScript(magus_ai_b)

        config.enemy_ai_db.scripts[ctenums.EnemyID.MAGUS] = new_magus_ai

        # Allow combo tech confuse to use on-hit effects
        tech_db = config.tech_db
        combo_confuse_id = 0x3C
        on_hit_byte = combo_confuse_id*tech_db.effect_size + 8
        tech_db.effects[on_hit_byte] = 0x80

        if rset.GameFlags.BOSS_SIGHTSCOPE in settings.gameflags:
            qolhacks.enable_boss_sightscope(config)

        return config

    @classmethod
    def get_randmomized_rom(cls,
                            rom: bytearray,
                            settings: rset.Settings) -> bytearray:
        '''
        Generate a random rom from the given (maybe not vanilla) rom.
        Uses the seed in settings.seed.
        '''
        rando = Randomizer(rom,
                           is_vanilla=False,
                           settings=settings,
                           config=None)
        rando.set_random_config()
        rando.generate_rom()
        return rando.get_generated_rom()


def read_names():
    p = open("names.txt", "r")
    names = p.readline()
    names = names.split(",")
    p.close()
    return names


#
# Handle the command line interface for the randomizer.
#
def generate_from_command_line():

    sourcefile, outputfolder = get_input_file_from_command_line()

    # note ext contains the '.'
    _, ext = os.path.splitext(sourcefile)

    with open(sourcefile, 'rb') as infile:
        rom = infile.read()

    if not CTRom.validate_ct_rom_bytes(rom):
        print(
            'Warning: File provided is not a vanilla CT ROM.  Proceed '
            'anyway?  Randomization is likely to fail. (Y/N)'
        )
        proceed = (input().upper() == 'Y')

        if not proceed:
            raise SystemExit()

    settings = get_settings_from_command_line()
    rando = Randomizer(rom, is_vanilla=False,
                       settings=settings,
                       config=None)

    rando.set_random_config()
    out_rom = rando.get_generated_rom()

    base_name = os.path.basename(sourcefile)
    flag_string = settings.get_flag_string()
    out_name = f"{base_name}.{flag_string}.{settings.seed}{ext}"
    out_path = os.path.join(outputfolder, out_name)

    with open(out_path, 'wb') as outfile:
        outfile.write(out_rom)

    print(f"generated: {out_path}")


def get_input_file_from_command_line() -> (str, str):
    sourcefile = input("Please enter ROM name or drag it onto the screen.")

    # When dragging, bash puts \' around the path.  Remove if present.
    quotes = ('\'', '\"')
    print(sourcefile[0], sourcefile[-2])
    if sourcefile[0] in quotes and sourcefile[-2] in quotes:
        sourcefile = sourcefile[1:-2]

    _, extension = os.path.splitext(sourcefile)

    if not os.path.isfile(sourcefile):
        input("Error: File does not exist.")
        exit()

    print(extension)
    if extension not in ('.sfc', '.smc'):
        input(
            "Invalid File Name. "
            "Try placing the ROM in the same folder as the randomizer. "
            "Also, try writing the extension(.sfc/smc)."
        )
        exit()

    # In theory ask for alternate output folder, but for now just place in
    # the same one.
    outputfolder = os.path.dirname(sourcefile)
    print(
        "The output ROM will be placed in the same folder:"
        f"\n\t{outputfolder}"
    )

    return sourcefile, outputfolder


def get_settings_from_command_line() -> rset.Settings:
    settings = rset.Settings()
    settings.gameflags = rset.GameFlags(False)

    seed = input(
            "Enter seed(or leave blank if you want to randomly generate one)."
    )
    if seed is None or seed == "":
        names = read_names()
        seed = "".join(random.choice(names) for i in range(2))

    settings.seed = seed

    # Difficulty (now separated between item/enemy but only in gui)
    difficulty = input("Choose your difficulty \nEasy(e)/Normal(n)/Hard(h) ")
    difficulty = difficulty.lower()
    if difficulty == "n":
        settings.item_difficulty = rset.Difficulty.NORMAL
        settings.enemy_difficulty = rset.Difficulty.NORMAL
    elif difficulty == "e":
        settings.item_difficulty = rset.Difficulty.EASY
        settings.enemy_difficulty = rset.Difficulty.NORMAL
    elif difficulty == 'h':
        settings.item_difficulty = rset.Difficulty.HARD
        settings.enemy_difficulty = rset.Difficulty.HARD
    else:
        print('Invalid selection.  Defaulting to normal')
        settings.item_difficulty = rset.Difficulty.NORMAL
        settings.enemy_difficulty = rset.Difficulty.NORMAL

    glitch_fixes = input(
        "Would you like to disable (most known) glitches(g)? Y/N "
    )
    glitch_fixes = glitch_fixes.upper()
    if glitch_fixes == "Y":
        settings.gameflags |= rset.GameFlags.FIX_GLITCH

    lost_worlds = input("Would you want to activate Lost Worlds(l)? Y/N ")
    lost_worlds = lost_worlds.upper()
    if lost_worlds == "Y":
        settings.game_mode = rset.GameMode.LOST_WORLDS

    boss_scaler = input(
        "Do you want bosses to scale with progression(b)? Y/N "
    )
    boss_scaler = boss_scaler.upper()
    if boss_scaler == "Y":
        settings.gameflags |= rset.GameFlags.BOSS_SCALE

    boss_rando = input("Do you want randomized bosses(ro)? Y/N ")
    boss_rando = boss_rando.upper()
    if boss_rando == "Y":
        settings.gameflags |= rset.GameFlags.BOSS_RANDO

    zeal_end = input(
        "Would you like Zeal 2 to be a final boss? "
        "Note that defeating Lavos still ends the game(z). Y/N "
    )
    zeal_end = zeal_end.upper()
    if zeal_end == "Y":
        settings.gameflags |= rset.GameFlags.ZEAL_END

    if lost_worlds == "Y":
        # At the moment, LW is not compatible with fast pendant
        pass
    else:
        quick_pendant = input(
            "Do you want the pendant to be charged upon entering the "
            "future(p)? Y/N "
        )
        quick_pendant = quick_pendant.upper()
        if quick_pendant == "Y":
            settings.gameflags |= rset.GameFlags.FAST_PENDANT

    locked_chars = input(
        "Do you want characters to be further locked(c)? Y/N "
    )
    locked_chars = locked_chars.upper()
    if locked_chars == "Y":
        settings.gameflags |= rset.GameFlags.LOCKED_CHARS

    tech_list = input("Do you want to randomize techs(te)? Y/N ")
    tech_list = tech_list.upper()
    if tech_list == "Y":
        settings.techorder = rset.TechOrder.FULL_RANDOM
        tech_list_balanced = input(
            "Do you want tech order randomziation to be biased so that "
            "less useful techs are more likely to appear earlier in the "
            "tech list (tex)? Y/N "
        )
        tech_list_balanced = tech_list_balanced.upper()
        if tech_list_balanced == "Y":
            settings.techorder = rset.TechOrder.BALANCED_RANDOM
    else:
        settings.techorder = rset.TechOrder.NORMAL

    unlocked_magic = input(
        "Do you want the ability to learn all techs without visiting "
        "Spekkio(m)? Y/N "
    )
    unlocked_magic = unlocked_magic.upper()
    if unlocked_magic == "Y":
        settings.gameflags |= rset.GameFlags.UNLOCKED_MAGIC

    quiet_mode = input("Do you want to enable quiet mode (No music)(q)? Y/N ")
    quiet_mode = quiet_mode.upper()
    if quiet_mode == "Y":
        settings.cosmetic_flags |= rset.CosmeticFlags.QUIET_MODE

    chronosanity = input(
        "Do you want to enable Chronosanity "
        "(key items can appear in chests)? (cr)? Y/N "
    )
    chronosanity = chronosanity.upper()
    if chronosanity == "Y":
        settings.gameflags |= rset.GameFlags.CHRONOSANITY

    duplicate_chars = input("Do you want to allow duplicte characters? ")
    duplicate_chars = duplicate_chars.upper()
    if duplicate_chars == "Y":
        settings.gameflags |= rset.GameFlags.DUPLICATE_CHARS
        same_char_techs = input(
            "Should duplicate characters learn dual techs? Y/N "
        ).upper()
        if same_char_techs == 'Y':
            settings.gameflags |= rset.GameFlags.DUPLICATE_TECHS

    tab_treasures = input("Do you want all treasures to be tabs(tb)? Y/N ")
    tab_treasures = tab_treasures.upper()
    if tab_treasures == "Y":
        settings.gameflags |= rset.GameFlags.TAB_TREASURES

    shop_prices = input(
        "Do you want shop prices to be Normal(n), Free(f), Mostly Random(m), "
        "or Fully Random(r)? "
    )
    shop_prices = shop_prices.upper()
    if shop_prices == "F":
        settings.shopprices = rset.ShopPrices.FREE
    elif shop_prices == "M":
        settings.shopprices = rset.ShopPrices.MOSTLY_RANDOM
    elif shop_prices == "R":
        settings.shopprices = rset.ShopPrices.FULLY_RANDOM
    elif shop_prices == 'N':
        settings.shopprices = rset.ShopPrices.NORMAL
    else:
        print('Invalid Entry.  Defaulting to Normal prices.')
        settings.shopprices = rset.ShopPrices.NORMAL

    return settings


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "-c":
        generate_from_command_line()
    else:
        print("Please run randomizergui.py for a graphical interface. \n"
              "Either randomizer.py or randomizergui.py can be run with the "
              "-c option to use\nthe command line.")


if __name__ == "__main__":
    main()
