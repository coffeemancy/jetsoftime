# This module makes classes for storing a configuration of the randomizer.
# Each module of the randomizer will get passed the GameConfig object and the
# flags and update the GameConfig.  Then, the randomizer will write the
# GameConfig out to the rom.
from __future__ import annotations
import dataclasses
import typing
import json

from treasures import treasuretypes
from characters import ctpcstats, pcrecruit

import byteops
import bossdata
import bossrandoevent as bossrando
import enemyai
import enemytechdb
import enemystats
import itemdata
import logictypes
import ctenums
import ctrom
import ctstrings
import statcompute
import techdb

import randosettings as rset


class ShopManager:

    shop_ptr = 0x02DAFD
    shop_data_bank_ptr = 0x02DB09

    def __init__(self, rom: bytearray):

        shop_data_bank, shop_ptr_start = ShopManager.__get_shop_pointers(rom)

        # print(f"Shop data bank = {self.shop_data_bank:06X}")
        # print(f"Shop ptr start = {self.shop_ptr_start:06X}")

        # We're using some properties of ShopID here.
        #  1) ShopID starts from 0x00, and
        #  2) ShopID contains all values from 0x00 to N-1 where N is
        #     the number of shops.

        self.shop_dict = dict()

        # The sort shouldn't be necessary, but be explicit.
        for shop in sorted(list(ctenums.ShopID)):
            index = int(shop)
            ptr_start = shop_ptr_start + 2*index
            shop_ptr_local = byteops.get_value_from_bytes(
                rom[ptr_start:ptr_start+2]
            )
            shop_ptr = shop_ptr_local + shop_data_bank
            shop_ptr = shop_ptr

            pos = shop_ptr
            self.shop_dict[shop] = []

            # Items in the shop are a 0-terminated list
            while rom[pos] != 0:
                # print(ctenums.ItemID(rom[pos]))
                self.shop_dict[shop].append(ctenums.ItemID(rom[pos]))
                pos += 1

    # Returns start of shop pointers, start of bank of shop data
    @classmethod
    def __get_shop_pointers(cls, rom: bytearray):
        shop_data_bank = byteops.to_file_ptr(rom[cls.shop_data_bank_ptr] << 16)
        shop_ptr_start = \
            byteops.to_file_ptr(
                byteops.get_value_from_bytes(rom[cls.shop_ptr:cls.shop_ptr+3])
            )
        return shop_data_bank, shop_ptr_start

    def write_to_ctrom(self, ct_rom: ctrom.CTRom):
        # The space used/freed by TF isn't available to me.  I just have to
        # assume that the space currently allotted is enough.

        shop_data_bank, shop_ptr_start = \
            ShopManager.__get_shop_pointers(ct_rom.rom_data.getbuffer())

        rom = ct_rom.rom_data

        ptr_loc = shop_ptr_start
        rom.seek(ptr_loc)
        data_loc = byteops.get_value_from_bytes(rom.read(2)) + shop_data_bank

        max_index = max(self.shop_dict.keys())

        for shop_id in range(max_index+1):
            shop = ctenums.ShopID(shop_id)

            rom.seek(ptr_loc)
            ptr = data_loc % 0x010000
            ptr_loc += rom.write(byteops.to_little_endian(ptr, 2))

            if shop in self.shop_dict.keys():
                items = bytearray(self.shop_dict[shop]) + b'\x00'
            else:
                items = bytearray([ctenums.ItemID.MOP]) + b'\x00'

            rom.seek(data_loc)
            data_loc += rom.write(items)

    def set_shop_items(self, shop: ctenums.ShopID,
                       items: list[ctenums.ItemID]):
        self.shop_dict[shop] = items[:]

    def print_with_prices(self,
                          item_db: itemdata.ItemDB):
        print(self.__str__(item_db))

    def _jot_json(self):
        shops_ignored = [
            ctenums.ShopID.EMPTY_12, ctenums.ShopID.EMPTY_14,
            ctenums.ShopID.LAST_VILLAGE_UPDATED
        ]
        return {str(k): [str(i) for i in v]
                for (k,v) in self.shop_dict.items()
                if k not in shops_ignored }

    def __str__(self, item_db: itemdata.ItemDB):
        ret = ''
        for shop in sorted(self.shop_dict.keys()):
            if shop in [ctenums.ShopID.EMPTY_12, ctenums.ShopID.EMPTY_14,
                        ctenums.ShopID.LAST_VILLAGE_UPDATED]:
                continue

            ret += str(shop)
            ret += ':\n'
            for item in self.shop_dict[shop]:
                ret += ('    ' + str(item))

                if item_db is not None:
                    price = item_db.item_dict[item].secondary_stats.price
                    ret += f": {price}"

                ret += '\n'

        return ret


@dataclasses.dataclass
class TabStats:
    power_tab_amt: int = 1
    magic_tab_amt: int = 1
    speed_tab_amt: int = 1


class RandoConfig:
    '''
    RandoConfig is a class which stores all of the data needed to write out
    a randomized rom.
    '''
    def __init__(
            self,
            treasure_assign_dict: dict[ctenums.TreasureID,
                                       treasuretypes.Treasure] = None,
            char_assign_dict: dict[ctenums.RecruitID,
                                   pcrecruit.RecruitSpot] = None,
            pcstats: ctpcstats.PCStatsManager = None,
            tech_db: techdb.TechDB = None,
            enemy_dict: dict[ctenums.EnemyID,
                             enemystats.EnemyStats] = None,
            enemy_atk_db: enemytechdb.EnemyAttackDB = None,
            enemy_ai_db: enemyai.EnemyAIDB = None,
            boss_assign_dict: dict[ctenums.LocID, ctenums.BossID] = None,
            boss_data_dict: dict[ctenums.BossID,
                                 bossdata.Boss] = None,
            tab_stats: TabStats = TabStats(1, 1, 1),
            omen_elevator_fights_up: typing.Container[int] = None,  # 0,1,2
            omen_elevator_fights_down: typing.Container[int] = None,
            # stuff that's getting replaced
            shop_manager: ShopManager = None,
            boss_rank_dict: dict[ctenums.BossID, int] = None,
            key_item_locations: typing.Container[logictypes.Location] = None,
    ):
        '''
        A RandoConfig consists of the following elements:
        - treasure_assign_dict:  Mapping of TreasureIDs to Treasure Objects
        - char_assign_dict:  Mapping of CharIDs to RecruitSpot Objects
        - pcstats: Stat data for all player characters (incl. DC)
        - tech_db: Tech data for all player characters
        - enemy_dict: Stat data for all enemies
        - enemy_atk_db: Attack/Tech data for all enemies
        - boss_assign_dict: Mapping of BossSpot (LocID?) to BossID
        - boss_data_dict: Mapping of BossID to the parts/layout of each boss.
        - tab_stats: magnitude of each tab effect
        - item_db: Holds all item data
              TODO: store the tab stats in the item_db instead.  By default, CT
                    ignores item data for tabs and uses hard-coded values.
        - omen_elevator_fights_up/down: Which fights one encounters on the
              Black Omen elevators.  These should be a container with the
              values 0, 1, and 2 present to indicate that a fight is taken.
        - shop_manager: Stores all items sold by all shops.
        - boss_rank_dict: Stores the rank of each boss according to the
              boss scaling (b) flag.  This doesn't need to be here except for
              spoiler purposes.  Writing to this has no effect on the final
              rom output.
        - key_item_locations: Stores the logictypes.Location objects where
              key items are.  This is like boss_rank_dict in that it's not
              a part of the rom output.  It's just information generated by
              the logic that gets merged into the treasure_assign_dict.
        Notes:
        - boss_rank_dict and key_item_locations are on the chopping block b/c
          they should be recomputable given the other items of the config.
        - There's coupling between pcstats and tech_db.  The DC assignment
          given in pcstats gives rise to a particular tech_db.  The changes
          made are destructive (no Cronos -> no Crono tech data in tech_db).
          So once pcstats has been used to compute the tech_db, then you can
          not make changes to the DC assignment.
        '''
        self.treasure_assign_dict = treasure_assign_dict
        self.char_assign_dict = char_assign_dict
        self.pcstats = pcstats
        self.tech_db = tech_db
        self.enemy_dict = enemy_dict
        self.enemy_atk_db = enemy_atk_db
        self.enemy_ai_db = enemy_ai_db
        self.boss_assign_dict = boss_assign_dict
        self.boss_data_dict = boss_data_dict
        self.tab_stats = tab_stats
        self.omen_elevator_fights_up = omen_elevator_fights_up
        self.omen_elevator_fights_down = omen_elevator_fights_down
        # stuff that's getting replaced possibly
        self.shop_manager = shop_manager
        self.boss_rank_dict = boss_rank_dict
        self.key_item_locations = key_item_locations

    def _jot_json(self):
        def enum_key_dict(d):
            "Properly uses str(key) for dicts with StrIntEnum keys."
            return { str(k): v for (k,v) in d.items() }

        def merged_list_dict(l):
            """For things that are a list of objects, each having a _jot_json
            method that returns a single-key dict, this merges those dicts into
            one."""
            return {k: v for d in l for k, v in d._jot_json().items()}

        def enum_enum_dict(d):
            "For dicts with both keys and values that are StrIntEnums"
            return { str(k): str(v) for (k,v) in d.items() }

        # make boss details dict
        # stats can be gotten from the enemies dict
        BossID = ctenums.BossID
        boss_ids = list(self.boss_assign_dict.values()) + \
                [BossID.MAGUS, BossID.BLACK_TYRANO, BossID.LAVOS_SHELL, BossID.INNER_LAVOS, BossID.LAVOS_CORE, BossID.MAMMON_M, BossID.ZEAL, BossID.ZEAL_2]
        boss_details_dict = {
                str(boss_id): {
                    'scale': self.boss_rank_dict[boss_id] if boss_id in self.boss_rank_dict else None,
                    'parts': [str(part_id) for part_id in list(dict.fromkeys(self.boss_data_dict[boss_id].scheme.ids))]
                }
                for boss_id in boss_ids
        }

        boss_details_dict[str(BossID.MAGUS)]['character'] = self.enemy_dict[ctenums.EnemyID.MAGUS].name.strip()
        boss_details_dict[str(BossID.BLACK_TYRANO)]['element'] = str(bossrando.get_black_tyrano_element(self))

        chars = self.pcstats._jot_json()
        # the below is ugly, would be nice to have tech lists on PlayerChar objects maybe
        for char_id in range(7):
            chars[str(ctenums.CharID(char_id))]['techs'] = [ctstrings.CTString.ct_bytes_to_techname(self.tech_db.get_tech(1 + 8*char_id + i)['name']).strip(' *') for i in range(8)]

        obstacle = self.enemy_atk_db.get_tech(0x58)
        obstacle_status = ", ".join(str(x) for x in obstacle.effect.status_effect)

        return {
            'key_items': merged_list_dict(self.key_item_locations),
            'characters': {
                'locations': enum_key_dict(self.char_assign_dict),
                'details': chars
            },
            'enemies': {
                'details': enum_key_dict(self.enemy_dict),
                # The boss in the twin golem spot will always be "Twin Boss"
                # This can still be looked up in the boss details and enemy
                # details structures, the latter of which can provide its name.
                'bosses': {
                    'locations': enum_enum_dict(self.boss_assign_dict),
                    'details': boss_details_dict,
                },
                'obstacle_status': obstacle_status
            },
            'treasures': {
                'assignments': enum_key_dict(self.treasure_assign_dict),
                'tabs': {
                    'power': self.tab_stats.power_tab_amt,
                    'magic': self.tab_stats.magic_tab_amt,
                    'speed': self.tab_stats.speed_tab_amt
                }
            },
            'shops': self.shop_manager,
            'items': self.item_db
        }

    # It's actually not feasible to generate one of these entirely from
    # a rom.
    #   - boss_rank_dict is hard to recover because you can't quickly
    #     compute rank from stats.  Enemy difficulty and RO complicate it.
    #   - boss_data_dict is hard to recover, especially in the annoying
    #     case of SoS having variable flame counts.
    #   - boss_assign_dict is hard to recvoer because in theory the BossID
    #     to Boss relationship can change (Guardian with Flea bits please)
    # All of the components that have from_ctrom methods can be used
    # independently.  It's ok to lump all of those together in one method.
    def update_from_ct_rom(self, ct_rom: ctrom.CTRom):
        '''
        Uses the data on the ct_rom to update the parts of the config that can
        be read easily from the rom: enemy_dict, itemdb, pcstats, tech_db,
          enemy_ai_db, enemy_atk_db, shop_manager.
        '''
        rom_data = ct_rom.rom_data  # Some types work on bytearrays
        self.enemy_dict = enemystats.get_stat_dict_from_ctrom(ct_rom)
        self.item_db = itemdata.ItemDB.from_rom(rom_data.getbuffer())
        self.pcstats = ctpcstats.PCStatsManager.from_ctrom(ct_rom)
        self.tech_db = techdb.TechDB.get_default_db(rom_data.getbuffer())
        self.enemy_ai_db = enemyai.EnemyAIDB.from_ctrom(ct_rom)
        self.enemy_atk_db = enemytechdb.EnemyAttackDB.from_rom(
            rom_data.getbuffer()
        )
        self.shop_manager = ShopManager(rom_data.getbuffer())


def main():
    pass


if __name__ == '__main__':
    main()
