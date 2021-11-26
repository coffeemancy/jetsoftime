from shutil import copyfile
import struct as st
import os
from os import stat
import pathlib
import pickle

import treasurewriter
import shopwriter
import characterwriter as char_slots
import logicwriter as keyitems
import logicwriter_chronosanity as logicwriter
import random as rand
import ipswriter as bigpatches
import patcher as patches
import enemywriter as enemystuff
import bossrandoevent as bossrando
import bossscaler
import techwriter as tech_order
import randomizergui as gui
import tabchange as tabwriter
import fastmagic
import charrando
import roboribbon
import techrandomizer
import qolhacks

import ctenums
import ctevent
from ctrom import CTRom
import ctstrings
import enemyrewards

# from freespace import FSWriteType
import randoconfig as cfg
import randosettings as rset


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

    # This would be used by a plando to set a non-random config.
    # Should this exist now that config is a property?
    def set_config(self, config: cfg.RandoConfig):
        self.config = config

        # TODO: Are there any sanity checks to apply to the config?

    # Given the settings passed to the randomizer, give the randomizer a
    # random RandoConfig object.
    def set_random_config(self):
        if self.settings is None:
            raise NoSettingsException

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

        rand.seed(self.settings.seed)

        # Character config.  Includes tech randomization.
        charrando.write_pcs_to_config(self.settings, self.config)
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

        # Shops
        shopwriter.write_shops_to_config(self.settings, self.config)

        # Item Prices
        shopwriter.write_item_prices_to_config(self.settings, self.config)

        # Boss Rando
        bossrando.write_assignment_to_config(self.settings, self.config)

        # This updates the enemy dict in the config with new stats.
        bossrando.scale_bosses_given_assignment(self.settings, self.config)

        # Key item Boss scaling (done after boss rando).  Also updates stats.
        bossscaler.set_boss_power(self.settings, self.config)

        # Black Tyrano/Magus boss randomization
        bossrando.randomize_midbosses(self.settings, self.config)

        # Tabs
        tabwriter.write_tabs_to_config(self.settings, self.config)

    def rescale_bosses(self):
        '''Reset enemy stats and redo boss scaling.'''
        if self.settings is None:
            raise NoSettingsException

        if self.config is None:
            raise NoConfigException

        config = self.get_base_config_from_settings(
            self.base_ctrom.rom_data.getbuffer(),
            self.settings
        )

        for loc in self.config.boss_assign_dict:
            boss = self.config.boss_assign_dict[loc]
            scheme = self.config.boss_data_dict[boss].scheme

            for part in set(scheme.ids):
                stats = self.config.enemy_dict[part]
                charm = stats.charm_item
                drop = stats.drop_item

                config.enemy_dict[part].charm_item = charm
                config.enemy_dict[part].drop_item = drop

                self.config.enemy_dict[part] = config.enemy_dict[part]

        bossrando.scale_bosses_given_assignment(self.settings, self.config)
        bossscaler.set_boss_power(self.settings, self.config)

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
        if self.settings is None:
            raise NoSettingsException

        if self.config is None:
            raise NoConfigException

        if self.has_generated:
            return

        # With valid config and settings, we can write generate the rom
        self.__write_out_rom()

    def __write_config_to_out_rom(self):

        config = self.config
        ctrom = self.out_rom

        # Write enemies out
        for enemy_id, stats in config.enemy_dict.items():
            stats.write_to_stream(ctrom.rom_data, enemy_id)

        # Write treasures out -- this includes key items
        # for treasure in config.treasure_assign_dict.values():
        for tid in config.treasure_assign_dict:
            treasure = config.treasure_assign_dict[tid]
            treasure.write_to_ctrom(ctrom)

        # Write shops out
        config.shop_manager.write_to_ctrom(ctrom)

        # Write prices out
        config.price_manager.write_to_ctrom(ctrom)

        # Write characters out
        # Recruitment spots
        for character in config.char_assign_dict.values():
            character.write_to_ctrom(ctrom)

        # Stats
        config.char_manager.write_stats_to_ctrom(ctrom)

        # Write out the rest of the character data (incl. techs)
        charrando.reassign_characters_on_ctrom(ctrom, config)

        # Write out the bosses and midbossses
        bossrando.write_bosses_to_ctrom(ctrom, config)
        bossrando.write_midbosses_to_ctrom(ctrom, config)

        # tabs
        tabwriter.rewrite_tabs_on_ctrom(ctrom, config)

    def __write_out_rom(self):
        '''Given config and settings, write to self.out_rom'''
        self.out_rom = CTRom(self.base_ctrom.rom_data.getvalue(), True)
        self.__apply_basic_patches(self.out_rom)
        self.__apply_settings_patches(self.out_rom, self.settings)

        # This makes copies of heckran cave passagesways and king's trial
        # so that bosses can go there.  There's no reason not do just do this
        # regardless of whether boss rando is on.

        bossrando.duplicate_maps_on_ctrom(self.out_rom)

        # Script changes which can always be made
        Event = ctevent.Event
        # Some dc flag patches can be added regardless.  No reason not to.

        # 1) Set magic learning at game start depending on character assignment
        telepod_event = Event.from_flux('./flux/cr_telepod_exhibit.flux')

        # 2) Allows left chest when medal is on non-Frog Frogs
        burrow_event = Event.from_flux('./flux/cr_burrow.Flux')

        # 3) Start Ruins quest when Grand Leon is on non-Frog Frogs
        choras_cafe_event = Event.from_flux('./flux/cr_choras_cafe.Flux')

        script_manager = self.out_rom.script_manager
        script_manager.set_script(telepod_event,
                                  ctenums.LocID.TELEPOD_EXHIBIT)
        script_manager.set_script(burrow_event,
                                  ctenums.LocID.FROGS_BURROW)
        script_manager.set_script(choras_cafe_event,
                                  ctenums.LocID.CHORAS_CAFE)

        # Flag specific script changes:
        #   - Locked characters changes to proto dome and dactyl nest
        #   - Duplicate characters changes to Spekkio when not in LW
        flags = self.settings.gameflags
        dup_chars = rset.GameFlags.DUPLICATE_CHARS in flags
        locked_chars = rset.GameFlags.LOCKED_CHARS in flags
        lost_worlds = rset.GameFlags.LOST_WORLDS in flags

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
            lc_proto_dome_event = Event.from_flux('./flux/lc_proto_dome.Flux')
            script_manager.set_script(lc_proto_dome_event,
                                      ctenums.LocID.PROTO_DOME)
        self.__try_proto_dome_fix()

        self.__write_config_to_out_rom()

        self.out_rom.write_all_scripts_to_rom()
        self.has_generated = True

    def get_generated_rom(self) -> bytearray:
        if not self.has_generated:
            self.generate_rom()

        return self.out_rom.rom_data.getvalue()

    def write_spoiler_log(self, filename):
        with open(filename, 'w') as outfile:
            self.write_key_item_spoilers(outfile)
            self.write_character_spoilers(outfile)
            self.write_boss_rando_spoilers(outfile)
            self.write_boss_stat_spoilers(outfile)
            self.write_treasure_spoilers(outfile)
            self.write_drop_charm_spoilers(outfile)
            self.write_shop_spoilers(outfile)
            self.write_price_spoilers(outfile)

    def write_key_item_spoilers(self, file_object):
        file_object.write("Key Item Locations\n")
        file_object.write("------------------\n")

        # We have to use the logicwriter's Location class only because
        # of Chronosanity's linked locations needing to be handled properly.

        width = max(len(x.getName()) for x in self.config.key_item_locations)

        for location in self.config.key_item_locations:
            file_object.write(str.ljust(f"{location.getName()}", width+8) +
                              str(location.getKeyItem()) + '\n')
        file_object.write('\n')

    def write_character_spoilers(self, file_object):
        char_man = self.config.char_manager
        char_assign = self.config.char_assign_dict

        file_object.write("Character Locations\n")
        file_object.write("-------------------\n")
        for recruit_spot in char_assign.keys():
            held_char = char_assign[recruit_spot].held_char
            reassign_char = \
                self.config.char_manager.pcs[held_char].assigned_char
            file_object.write(str.ljust(f"{recruit_spot}", 20) +
                              f"{char_assign[recruit_spot].held_char}"
                              f" reassigned {reassign_char}\n")
        file_object.write('\n')

        file_object.write("Character Stats\n")
        file_object.write("---------------\n")

        CharID = ctenums.CharID
        dup_chars = rset.GameFlags.DUPLICATE_CHARS in self.settings.gameflags
        techdb = self.config.techdb

        for char_id in range(7):
            file_object.write(f"{CharID(char_id)}:")
            if dup_chars:
                file_object.write(
                    f" assigned to {char_man.pcs[char_id].assigned_char}"
                )
            file_object.write('\n')
            file_object.write(char_man.pcs[char_id].stats.get_stat_string())

            file_object.write('Tech Order:\n')
            for tech_num in range(8):
                # TODO:  Is it OK to randomize the DB early?  We're trying it.
                # tech_num = char_man.pcs[char_id].tech_permutation[tech_num]
                tech_id = 1 + 8*char_id + tech_num
                tech = techdb.get_tech(tech_id)
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
            file_object.write(str.ljust(str(treasure), width+8) +
                              str(treasure_dict[treasure].held_item) +
                              '\n')
        file_object.write('\n')

    def write_shop_spoilers(self, file_object):
        file_object.write("Shop Assigmment\n")
        file_object.write("---------------\n")
        file_object.write(
            self.config.shop_manager.__str__(self.config.price_manager)
        )
        file_object.write('\n')

    def write_price_spoilers(self, file_object):
        file_object.write("Item Prices\n")
        file_object.write("-----------\n")

        width = max(len(str(x)) for x in list(ctenums.ItemID)) + 8

        item_ids = [x for x in list(ctenums.ItemID)
                    if x in range(1, ctenums.ItemID(0xD0))]

        for item_id in item_ids:
            file_object.write(
                str.ljust(str(ctenums.ItemID(item_id)), width) +
                str(self.config.price_manager.get_price(item_id)) +
                '\n'
            )
        file_object.write('\n')

    def write_boss_rando_spoilers(self, file_object):
        file_object.write("Boss Locations\n")
        file_object.write("--------------\n")

        boss_dict = self.config.boss_assign_dict
        width = max(len(str(x)) for x in boss_dict.keys()) + 8

        for location in boss_dict.keys():
            file_object.write(
                str.ljust(str(location), width) +
                str(boss_dict[location]) +
                '\n'
            )

        file_object.write('\n')

    def write_boss_stat_spoilers(self, file_object):

        scale_dict = self.config.boss_rank

        file_object.write("Boss Stats\n")
        file_object.write("----------\n")
        for boss_id in self.config.boss_assign_dict.values():
            file_object.write(str(boss_id)+':')
            if boss_id in scale_dict.keys():
                file_object.write(
                    f" Key Item scale rank = {scale_dict[boss_id]}"
                )
            file_object.write('\n')

            boss = self.config.boss_data_dict[boss_id]
            part_ids = list(dict.fromkeys(boss.scheme.ids))
            for part_id in part_ids:
                if len(part_ids) > 1:
                    file_object.write(f"Part: {part_id}\n")
                part_str = str(self.config.enemy_dict[part_id])
                # put the string one tab out
                part_str = '\t' + str.replace(part_str, '\n', '\n\t')
                file_object.write(part_str+'\n')
            file_object.write('\n')

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

        for ind, tier in enumerate(tiers):
            file_object.write(labels[ind] + '\n')
            for enemy_id in tier:
                file_object.write(
                    '\t' +
                    str.ljust(f"{enemy_id}", width) +
                    " Drop: "
                    f"{self.config.enemy_dict[enemy_id].drop_item}\n")
                file_object.write(
                    '\t' +
                    str.ljust("", width) +
                    "Charm: "
                    f"{self.config.enemy_dict[enemy_id].charm_item}\n")

        file_object.write('\n')

    @classmethod
    def __apply_basic_patches(cls, ctrom: CTRom):
        '''Apply patches that are always applied to a jets rom.'''
        rom_data = ctrom.rom_data

        # Apply the patches that always are applied for jets
        # patch.ips makes sure that we have
        #   - Stats/stat growths for characters for CharManager
        #   - Tech data for TechDB
        #   - Item data (including prices) for shops
        # patch_codebase.txt may not be needed
        rom_data.patch_ips_file('./patch.ips')
        rom_data.patch_txt_file('./patches/patch_codebase.txt')

        # I verified that the following convenience patches which are now
        # always applied are disjoint from the glitch fix patches, so it's
        # safe to move them here.
        rom_data.patch_txt_file('./patches/fast_overworld_walk_patch.txt')
        rom_data.patch_txt_file('./patches/faster_epoch_patch.txt')
        rom_data.patch_txt_file('./patches/faster_menu_dpad.txt')

        # It should be safe to move the robo's ribbon code here since it
        # also doesn't depend on flags and should be applied prior to anything
        # else that messes with the items because it shuffles effects
        roboribbon.robo_ribbon_speed(rom_data.getbuffer())

    @classmethod
    def __apply_settings_patches(cls, ctrom: CTRom,
                                 settings: rset.Settings):
        '''Apply patches to a vanilla ctrom based on randomizer settings.  '''
        '''These are patches not handled by writing the config.'''

        rom_data = ctrom.rom_data
        flags = settings.gameflags

        if rset.GameFlags.FIX_GLITCH in flags:
            rom_data.patch_txt_file('./patches/save_anywhere_patch.txt')
            rom_data.patch_txt_file('./patches/unequip_patch.txt')
            rom_data.patch_txt_file('./patches/fadeout_patch.txt')
            rom_data.patch_txt_file('./patches/hp_overflow_patch.txt')

        if rset.GameFlags.QUIET_MODE in flags:
            rom_data.patch_ips_file('./patches/nomusic.ips')

        # TODO:  I'd like to do this with .Flux event changes
        if rset.GameFlags.ZEAL_END in flags:
            rom_data.patch_txt_file('./patches/zeal_end_boss.txt')

        # Patching with lost.ips does not give a valid event for
        # mystic mountains.  I could fix the event by applying a flux file,
        # but I'm worried about what might happen when the invalid event is
        # marked free space.  For now we keep with 3.1 and apply the
        # mysticmtnfix.ips to restore the event.
        if rset.GameFlags.LOST_WORLDS in flags:
            rom_data.patch_ips_file('./patches/lost.ips')
            rom_data.patch_ips('./patches/mysticmtnfix.ips')

        if rset.GameFlags.FAST_PENDANT in flags:
            rom_data.patch_txt_file('./patches/fast_charge_pendant.txt')

        # Big TODO:  Unwrap the hard patch into its component changes.
        #            As far as I can tell it's just enemies and starting GP.
        if settings.enemy_difficulty == rset.Difficulty.HARD:
            rom_data.patch_ips_file('./patches/hard.ips')

        if rset.GameFlags.VISIBLE_HEALTH in flags:
            qolhacks.force_sightscope_on(ctrom, settings)

        if rset.GameFlags.UNLOCKED_MAGIC in flags:
            fastmagic.write_ctrom(ctrom, settings)

        qolhacks.fast_tab_pickup(ctrom, settings)


    @classmethod
    def dump_default_config(cls, ct_vanilla: bytearray):
        '''Turn vanilla ct rom into default objects for a config.'''
        '''Should run whenever a big patch (patch.ips, hard.ips) changes.'''
        ctrom = CTRom(ct_vanilla, ignore_checksum=False)
        cls.__apply_basic_patches(ctrom)

        RC = cfg.RandoConfig
        config = RC.get_config_from_rom(ctrom.rom_data.getbuffer())

        with open('./pickles/default_randoconfig.pickle', 'wb') as outfile:
            pickle.dump(config, outfile)

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
          - techdb: patch.ips changes the basic techs (i.e. Antilife)
        '''

        # It's a little wasteful copying the rom data to partially patch it
        # to extract the base values for the above.

        # I do have a pickle with a default config and normal/hard enemy dicts
        # which can be used instead if this is an issue.  The problem with
        # using those is the need to update them with every patch.
        ctrom = CTRom(ct_vanilla, True)
        Randomizer.__apply_basic_patches(ctrom)
        return cfg.RandoConfig.get_config_from_rom(
            bytearray(ctrom.rom_data.getvalue())
        )

    @classmethod
    def get_randmomized_rom(cls,
                            rom: bytearray,
                            settings: rset.Settings) -> bytearray:
        rando = Randomizer(rom, settings)
        rando.set_random_config()
        rando.generate_rom()
        return rando.get_generated_rom()


def read_names():
        p = open("names.txt","r")
        names = p.readline()
        names = names.split(",")
        p.close()
        return names

# Script variables
flags = ""
sourcefile = ""
outputfolder = ""
difficulty = ""
glitch_fixes = ""
#fast_move = ""
#sense_dpad = ""
lost_worlds = ""
boss_scaler = ""
zeal_end = ""
quick_pendant = ""
locked_chars = ""
tech_list = ""
seed = ""
tech_list = ""
unlocked_magic = ""
quiet_mode = ""
chronosanity = ""
tab_treasures = ""
boss_rando = ""
shop_prices = ""
duplicate_chars = ""
#
# Handle the command line interface for the randomizer.
#   
def command_line():
     global flags
     global sourcefile
     global outputfolder
     global difficulty
     global glitch_fixes
#     global fast_move
#     global sense_dpad
     global lost_worlds
     global boss_scaler
     global zeal_end
     global quick_pendant
     global locked_chars
     global tech_list
     global seed
     global tech_list_balanced
     global unlocked_magic
     global quiet_mode
     global chronosanity
     global tab_treasures
     global boss_rando
     global shop_prices
     global duplicate_chars
     global same_char_techs
     global char_choices
     
     flags = ""
     sourcefile = input("Please enter ROM name or drag it onto the screen.")
     sourcefile = sourcefile.strip("\"")
     if sourcefile.find(".sfc") == -1:
         if sourcefile.find(".smc") == - 1:
             input("Invalid File Name. Try placing the ROM in the same folder as the randomizer. Also, try writing the extension(.sfc/smc).")
             exit()
     outputfolder = os.path.dirname(sourcefile)
     seed = input("Enter seed(or leave blank if you want to randomly generate one).")
     if seed is None or seed == "":
        names = read_names()
        seed = "".join(rand.choice(names) for i in range(2))
     rand.seed(seed)
     difficulty = input(f"Choose your difficulty \nEasy(e)/Normal(n)/Hard(h)")
     if difficulty == "n":
         difficulty = "normal"
     elif difficulty == "e":
         difficulty = "easy"
     else:
         difficulty = "hard"
     flags = flags + difficulty[0]
     glitch_fixes = input("Would you like to disable (most known) glitches(g)? Y/N ")
     glitch_fixes = glitch_fixes.upper()
     if glitch_fixes == "Y":
        flags = flags + "g" 
     #fast_move = input("Would you like to move faster on the overworld/Epoch(s)? Y/N ")
     #fast_move = fast_move.upper()
     #if fast_move == "Y":
     #   flags = flags + "s"
     #sense_dpad = input("Would you like faster dpad inputs in menus(d)? Y/N ")
     #sense_dpad = sense_dpad.upper()
     #if sense_dpad == "Y":
     #   flags = flags + "d"
     lost_worlds = input("Would you want to activate Lost Worlds(l)? Y/N ")
     lost_worlds = lost_worlds.upper()
     if lost_worlds == "Y":
         flags = flags + "l"
     boss_scaler = input("Do you want bosses to scale with progression(b)? Y/N ")
     boss_scaler = boss_scaler.upper()
     if boss_scaler == "Y":
        flags = flags + "b"
     boss_rando = input("Do you want randomized bosses(ro)? Y/N ")
     boss_rando = boss_rando.upper()
     if boss_rando == "Y":
        flags = flags + "ro"     
     zeal_end = input("Would you like Zeal 2 to be a final boss? Note that defeating Lavos still ends the game(z). Y/N ")
     zeal_end = zeal_end.upper()
     if zeal_end == "Y":
        flags = flags + "z"
     if lost_worlds == "Y":
        pass
     else:
         quick_pendant = input("Do you want the pendant to be charged earlier(p)? Y/N ")
         quick_pendant = quick_pendant.upper()
         if quick_pendant == "Y":
            flags = flags + "p"
     locked_chars = input("Do you want characters to be further locked(c)? Y/N ")
     locked_chars = locked_chars.upper()
     if locked_chars == "Y":
        flags = flags + "c"
     tech_list = input("Do you want to randomize techs(te)? Y/N ")
     tech_list = tech_list.upper()
     if tech_list == "Y":
         flags = flags + "te"
         tech_list = "Fully Random"
         tech_list_balanced = input("Do you want to balance the randomized techs(tex)? Y/N ")
         tech_list_balanced = tech_list_balanced.upper()
         if tech_list_balanced == "Y":
            flags = flags + "x"
            tech_list = "Balanced Random"
     unlocked_magic = input("Do you want the ability to learn all techs without visiting Spekkio(m)? Y/N")
     unlocked_magic = unlocked_magic.upper()
     if unlocked_magic == "Y":
         flags = flags + "m"
     quiet_mode = input("Do you want to enable quiet mode (No music)(q)? Y/N")
     quiet_mode = quiet_mode.upper()
     if quiet_mode == "Y":
         flags = flags + "q"
     chronosanity = input("Do you want to enable Chronosanity (key items can appear in chests)? (cr)? Y/N")
     chronosanity = chronosanity.upper()
     if chronosanity == "Y":
         flags = flags + "cr"
     duplicate_chars = input("Do you want to allow duplicte characters?")
     duplicate_chars = duplicate_chars.upper()
     if duplicate_chars == "Y":
         flags = flags + "dc"
         same_char_techs = \
             input("Should duplicate characters learn dual techs? Y/N ")
     else:
         same_char_techs = "N"

     tab_treasures = input("Do you want all treasures to be tabs(tb)? Y/N ")
     tab_treasures = tab_treasures.upper()
     if tab_treasures == "Y":
        flags = flags + "tb"
     shop_prices = input("Do you want shop prices to be Normal(n), Free(f), Mostly Random(m), or Fully Random(r)?")
     shop_prices = shop_prices.upper()
     if shop_prices == "F":
        shop_prices = "Free"
        flags = flags + "spf"
     elif shop_prices == "M":
        shop_prices = "Mostly Random"
        flags = flags + "spm"
     elif shop_prices == "R":
        shop_prices = "Fully Random"
        flags = flags + "spr"
     else:
        shop_prices = "Normal"
    

#
# Given a tk IntVar, convert it to a Y/N value for use by the randomizer.
#
def get_flag_value(flag_var):
  if flag_var.get() == 1:
    return "Y"
  else:
    return "N"
  
#
# Handle seed generation from the GUI.
# Convert all of the GUI datastore values internal values
# for the randomizer and then generate the ROM.
#  
def handle_gui(datastore):
  global flags
  global sourcefile
  global outputfolder
  global difficulty
  global glitch_fixes
#  global fast_move
#  global sense_dpad
  global lost_worlds
  global boss_scaler
  global zeal_end
  global quick_pendant
  global locked_chars
  global tech_list
  global seed
  global unlocked_magic
  global quiet_mode
  global chronosanity
  global tab_treasures
  global boss_rando
  global shop_prices
  global duplicate_chars
  global same_char_techs
  global char_choices
  
  # Get the user's chosen difficulty
  difficulty = datastore.difficulty.get()

  # Get the user's chosen tech randomization
  tech_list = datastore.techRando.get()
  
  # Get the user's chosen shop price settings
  shop_prices = datastore.shopPrices.get()
  
  # build the flag string from the gui datastore vars
  flags = difficulty[0]
  for flag, value in datastore.flags.items():
    if value.get() == 1:
      flags = flags + flag
  if tech_list == "Fully Random":
      flags = flags + "te"
  elif tech_list == "Balanced Random":
      flags = flags + "tex"
      
  if shop_prices == "Free":
    flags = flags + "spf"
  elif shop_prices == "Mostly Random":
    flags = flags + "spm"
  elif shop_prices == "Fully Random":
    flags = flags + "spr"
  
  # Set the flag variables based on what the user chose
  glitch_fixes = get_flag_value(datastore.flags['g'])
  #fast_move = get_flag_value(datastore.flags['s'])
  #sense_dpad = get_flag_value(datastore.flags['d'])
  lost_worlds = get_flag_value(datastore.flags['l'])
  boss_scaler = get_flag_value(datastore.flags['b'])
  boss_rando = get_flag_value(datastore.flags['ro'])
  zeal_end = get_flag_value(datastore.flags['z'])
  quick_pendant = get_flag_value(datastore.flags['p'])
  locked_chars = get_flag_value(datastore.flags['c'])
  unlocked_magic = get_flag_value(datastore.flags['m'])
  quiet_mode = get_flag_value(datastore.flags['q'])
  chronosanity = get_flag_value(datastore.flags['cr'])
  tab_treasures = get_flag_value(datastore.flags['tb'])
  duplicate_chars = get_flag_value(datastore.flags['dc'])

  # dc settings
  if datastore.char_choices is None:
      char_choices = [[1 for i in range(0,7)] for j in range(0,7)]
      same_char_techs = "N"
  else:
      char_choices = []
      for i in range(7):
          char_choices.append([])
          for j in range(7):
              if datastore.char_choices[i][j].get() == 1:
                  char_choices[i].append(j)

      same_char_techs = get_flag_value(datastore.dup_techs)
  
  
  # source ROM
  sourcefile = datastore.inputFile.get()
  
  # output folder
  outputfolder = datastore.outputFolder.get()
  
  # seed
  seed = datastore.seed.get()
  if seed is None or seed == "":
    names = read_names()
    seed = "".join(rand.choice(names) for i in range(2))
  rand.seed(seed)
  datastore.seed.set(seed)
  
  # GUI values have been converted, generate the ROM.
  generate_rom()
   
#
# Generate the randomized ROM.
#    
def generate_rom():
     global flags
     global sourcefile
     global outputfolder
     global difficulty
     global glitch_fixes
     global fast_move
     global sense_dpad
     global lost_worlds
     global boss_rando
     global boss_scaler
     global zeal_end
     global quick_pendant
     global locked_chars
     global tech_list
     global seed
     global unlocked_magic
     global quiet_mode
     global chronosanity
     global tab_treasures
     global shop_prices
     global duplicate_chars
     global same_char_techs
     global char_choices
     
     # isolate the ROM file name
     inputPath = pathlib.Path(sourcefile)
     outfile = inputPath.name
     
     # Create the output file name
     outfile = outfile.split(".")
     outfile = str(outfile[0])
     if flags == "":
       outfile = "%s.%s.sfc"%(outfile,seed)
     else:
       outfile = "%s.%s.%s.sfc"%(outfile,flags,seed)
       
     # Append the output file name to the selected directory
     # If there is no selected directory, use the input path
     if outputfolder == None or outputfolder == "":
       outfile = str(inputPath.parent.joinpath(outfile))
     else:
       outfile = str(pathlib.Path(outputfolder).joinpath(outfile))
       
     size = stat(sourcefile).st_size
     if size % 0x400 == 0:
        copyfile(sourcefile, outfile)
     elif size % 0x200 == 0:
        print("SNES header detected. Removing header from output file.")
        f = open(sourcefile, 'r+b')
        data = f.read()
        f.close()
        data = data[0x200:]
        open(outfile, 'w+').close()
        f = open(outfile, 'r+b')
        f.write(data)
        f.close()
     print("Applying patch. This might take a while.")
     bigpatches.write_patch_alt("patch.ips",outfile)
     patches.patch_file("patches/patch_codebase.txt",outfile)
     if glitch_fixes == "Y":
        patches.patch_file("patches/save_anywhere_patch.txt",outfile)
        patches.patch_file("patches/unequip_patch.txt",outfile)
        patches.patch_file("patches/fadeout_patch.txt",outfile)
        patches.patch_file("patches/hp_overflow_patch.txt",outfile)
     patches.patch_file("patches/fast_overworld_walk_patch.txt",outfile)
     patches.patch_file("patches/faster_epoch_patch.txt",outfile)
     patches.patch_file("patches/faster_menu_dpad.txt",outfile)
     if zeal_end == "Y":
        patches.patch_file("patches/zeal_end_boss.txt",outfile)
     if lost_worlds == "Y":
        bigpatches.write_patch_alt("patches/lost.ips",outfile)
     if lost_worlds == "Y":
         pass
     elif quick_pendant == "Y":
             patches.patch_file("patches/fast_charge_pendant.txt",outfile)
     if unlocked_magic == "Y":
        fastmagic.set_fast_magic_file(outfile)
        # bigpatches.write_patch_alt("patches/fastmagic.ips",outfile)
     if difficulty == "hard":
         bigpatches.write_patch_alt("patches/hard.ips",outfile)
     tabwriter.rewrite_tabs(outfile)#Psuedoarc's code to rewrite Power and Magic tabs and make them more impactful
     roboribbon.robo_ribbon_speed_file(outfile)
     print("Randomizing treasures...")
     treasures.randomize_treasures(outfile,difficulty,tab_treasures)
     hardcoded_items.randomize_hardcoded_items(outfile,tab_treasures)
     print("Randomizing enemy loot...")
     enemystuff.randomize_enemy_stuff(outfile,difficulty)
     print("Randomizing shops...")
     shops.randomize_shops(outfile)
     shops.modify_shop_prices(outfile, shop_prices)
     print("Randomizing character locations...")
     char_locs = char_slots.randomize_char_positions(outfile,locked_chars,lost_worlds)
     print("Now placing key items...")
     if chronosanity == "Y":
       chronosanity_logic.writeKeyItems(
           outfile, char_locs, (locked_chars == "Y"), (quick_pendant == "Y"), lost_worlds == "Y")
     elif lost_worlds == "Y":
       keyitemlist = keyitems.randomize_lost_worlds_keys(char_locs,outfile)
     else:
       keyitemlist = keyitems.randomize_keys(char_locs,outfile,locked_chars)
     if boss_scaler == "Y" and chronosanity != "Y":
         print("Rescaling bosses based on key items..")
         boss_scale.scale_bosses(char_locs,keyitemlist,locked_chars,outfile)
     #print("Boss rando: " + boss_rando)
     if boss_rando == "Y":
         boss_shuffler.randomize_bosses(outfile,difficulty)
         boss_shuffler.randomize_dualbosses(outfile,difficulty)
     # going to handle techs differently for dup chars
     if duplicate_chars == "Y":
         charrando.reassign_characters_file(outfile, char_choices,
                                            same_char_techs == "Y",
                                            tech_list,
                                            lost_worlds == "Y")
     else:
         if tech_list == "Fully Random":
             tech_order.take_pointer(outfile)
         elif tech_list == "Balanced Random":
             tech_order.take_pointer_balanced(outfile)

     if quiet_mode == "Y":
         bigpatches.write_patch_alt("patches/nomusic.ips",outfile)
     # Tyrano Castle chest hack
     f = open(outfile,"r+b")
     f.seek(0x35F6D5)
     f.write(st.pack("B",1))
     f.close()
     #Mystic Mtn event fix in Lost Worlds
     if lost_worlds == "Y":         
       f = open(outfile,"r+b")
       bigpatches.write_patch_alt("patches/mysticmtnfix.ips",outfile)
     #Bangor Dome event fix if character locks are on
 #      if locked_chars == "Y":
 #        bigpatches.write_patch_alt("patches/bangorfix.ips",outfile)
       f.close()
     print("Randomization completed successfully.")


def main():

    with open('./roms/ct.sfc', 'rb') as infile:
        rom = infile.read()

    settings = rset.Settings.get_race_presets()
    settings.gameflags |= rset.GameFlags.DUPLICATE_CHARS
    settings.char_choices = [[i for i in range(7)] for j in range(7)]
    # settings.char_choices = [[j] for j in range(7)]
    # settings.gameflags |= rset.GameFlags.BOSS_SCALE
    settings.gameflags |= rset.GameFlags.CHRONOSANITY
    settings.gameflags |= rset.GameFlags.VISIBLE_HEALTH
    settings.gameflags |= rset.GameFlags.LOCKED_CHARS
    settings.gameflags |= rset.GameFlags.UNLOCKED_MAGIC

    settings.ro_settings.enable_sightscope = True

    settings.seed = 'franklin_1'
    rando = Randomizer(rom, is_vanilla=True,
                       settings=settings,
                       config=None)
    rando.set_random_config()

    '''
    # Force a given boss in cathedral for testing
    LocID = ctenums.LocID
    BossID = ctenums.BossID
    cath_boss = rando.config.boss_assign_dict[LocID.MANORIA_COMMAND]

    boss_dict = rando.config.boss_assign_dict

    target_boss = BossID.MUD_IMP

    for key in boss_dict:
        if boss_dict[key] == target_boss:
            boss_dict[key] = cath_boss

    rando.config.boss_assign_dict[LocID.MANORIA_COMMAND] = target_boss
    rando.rescale_bosses()
    '''

    out_rom = rando.get_generated_rom()
    seed = settings.seed
    # rando.out_rom.rom_data.space_manager.print_blocks()
    rando.write_spoiler_log(f'spoiler_log_{seed}.txt')

    with open(f'./roms/ct_out_{seed}.sfc', 'wb') as outfile:
        outfile.write(out_rom)


if __name__ == "__main__":
    main()
