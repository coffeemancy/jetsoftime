from __future__ import annotations

import math
import struct as st
import random as rand

from ctenums import ItemID, ShopID
from ctrom import CTRom
import treasuredata as td

import randoconfig as cfg
import randosettings as rset


def write_shops_to_config(settings: rset.Settings,
                          config: cfg.RandoConfig):

    # Bunch of declarations.  They're here instead of in global scope after
    # the great shelling of November 2021.

    # Get short names for item lists for defining distributions later.
    ITier = td.ItemTier
    # no shop sells low gear
    # low_gear = td.get_item_list(ITier.LOW_GEAR)

    # power meals are not sellable
    low_cons = td.get_item_list(ITier.LOW_CONSUMABLE)
    low_cons.remove(ItemID.POWER_MEAL)

    pass_gear = td.get_item_list(ITier.PASSABLE_GEAR)
    pass_cons = td.get_item_list(ITier.PASSABLE_CONSUMABLE)
    mid_gear = td.get_item_list(ITier.MID_GEAR)
    mid_cons = td.get_item_list(ITier.MID_CONSUMABLE)

    # greendream is not sellable
    good_gear = td.get_item_list(ITier.GOOD_GEAR)
    good_gear.remove(ItemID.GREENDREAM)

    good_cons = td.get_item_list(ITier.GOOD_CONSUMABLE)
    high_gear = td.get_item_list(ITier.HIGH_GEAR)

    # Tabs are not sellable
    high_cons = td.get_item_list(ITier.HIGH_CONSUMABLE)
    for x in [ItemID.POWER_TAB, ItemID.MAGIC_TAB, ItemID.SPEED_TAB]:
        high_cons.remove(x)

    awe_gear = td.get_item_list(ITier.AWESOME_GEAR)
    awe_cons = td.get_item_list(ITier.AWESOME_CONSUMABLE)

    # Regular Shop Setup
    regular_shop_ids = [
        ShopID.TRUCE_MARKET_600, ShopID.ARRIS_DOME, ShopID.DORINO,
        ShopID.PORRE_600, ShopID.PORRE_1000, ShopID.CHORAS_INN_1000,
        ShopID.CHORAS_MARKET_600, ShopID.MILENNIAL_FAIR_ARMOR,
        ShopID.MILLENIAL_FAIR_ITEMS,
    ]

    regular_dist = td.TreasureDist(
        (6, low_cons + pass_cons),
        (4, pass_gear + mid_gear)
    )
    regular_guaranteed = []

    # Good Shop Setup.  Fiona and Fritz have lapis guaranteed.
    good_shop_ids = [
        ShopID.MELCHIORS_HUT, ShopID.IOKA_VILLAGE, ShopID.NU_NORMAL_KAJAR,
        ShopID.ENHASA, ShopID.EARTHBOUND_VILLAGE, ShopID.TRANN_DOME,
        ShopID.MEDINA_MARKET,
    ]

    good_lapis_shop_ids = [
        ShopID.FIONAS_SHRINE, ShopID.TRUCE_MARKET_1000,
    ]

    good_dist = td.TreasureDist(
        (5, pass_cons + mid_cons),
        (5, mid_gear + good_gear)
    )
    good_guaranteed = []
    good_lapis_guaranteed = [ItemID.LAPIS]

    # Best Shop Setup
    best_shop_ids = [
        ShopID.NU_SPECIAL_KAJAR,
        # ShopID.LAST_VILLAGE_UPDATED,  # This shop is actually unused
        ShopID.NU_BLACK_OMEN,
    ]

    best_dist = td.TreasureDist(
        (5, good_cons + high_cons + awe_cons),
        (5, good_gear + high_gear + awe_gear)
    )
    best_guaranteed = [ItemID.AMULET]

    # Unused Shop Setup
    unused_shop_ids = [
        ShopID.LAST_VILLAGE_UPDATED, ShopID.EMPTY_12, ShopID.EMPTY_14,
    ]

    # Melchior's special shop
    shop_manager = config.shop_manager
    shop_manager.set_shop_items(ShopID.MELCHIOR_FAIR,
                                get_melchior_shop_items())

    # Now write out the regular, good, best shops.
    # Parallel lists for type, dist, and guarantees.  This is a little ugly
    # and maybe each shop should get its own guarantee list instead of by tier.
    shop_types = [regular_shop_ids, good_shop_ids,
                  good_lapis_shop_ids, best_shop_ids]
    shop_dists = [regular_dist, good_dist, good_dist, best_dist]
    shop_guaranteed = [regular_guaranteed, good_guaranteed,
                       good_lapis_guaranteed, best_guaranteed]

    for i in range(len(shop_types)):
        for shop in shop_types[i]:
            guaranteed = shop_guaranteed[i]
            dist = shop_dists[i]
            items = get_shop_items(guaranteed, dist)

            shop_manager.set_shop_items(shop, items)

    for shop in unused_shop_ids:
        shop_manager.set_shop_items(shop, [ItemID.MOP])

    # With the whole shop list in hand, you can do some global guarantees
    # here if desired.  For example, guarantee ethers/midtonics in LW.


def write_item_prices_to_config(settings: rset.Settings,
                                config: cfg.RandoConfig):
    items_to_modify = list(ItemID)

    # Set up the list of items to randomize
    if settings.shopprices == rset.ShopPrices.MOSTLY_RANDOM:
        excluded_items = [ItemID.MID_TONIC, ItemID.ETHER, ItemID.HEAL,
                          ItemID.REVIVE, ItemID.SHELTER]
        items_to_modify = [item for item in items_to_modify
                           if item not in excluded_items]
    elif settings.shopprices == rset.ShopPrices.NORMAL:
        items_to_modify = []

    # Actually modify the prices
    for item in items_to_modify:
        if settings.shopprices in (rset.ShopPrices.FULLY_RANDOM,
                                   rset.ShopPrices.MOSTLY_RANDOM):
            price = getRandomPrice()
        elif settings.shopprices == rset.ShopPrices.FREE:
            price = 0

        config.price_manager.set_price(item, price)


def get_melchior_shop_items():

    swords = [ItemID.FLASHBLADE, ItemID.PEARL_EDGE,
              ItemID.RUNE_BLADE, ItemID.DEMON_HIT]
    robo_arms = [ItemID.STONE_ARM, ItemID.DOOMFINGER, ItemID.MAGMA_HAND]
    guns = [ItemID.RUBY_GUN, ItemID.DREAM_GUN, ItemID.MEGABLAST]
    bows = [ItemID.SAGE_BOW, ItemID.DREAM_BOW, ItemID.COMETARROW]
    katanas = [ItemID.FLINT_EDGE, ItemID.DARK_SABER, ItemID.AEON_BLADE]

    item_list = [
        rand.choice(swords),
        rand.choice(robo_arms),
        rand.choice(guns),
        rand.choice(bows),
        rand.choice(katanas),
        ItemID.REVIVE,
        ItemID.SHELTER
    ]

    return item_list


def get_shop_items(guaranteed_items: list[ItemID], item_dist):
    shop_items = guaranteed_items[:]

    # potentially shop size should be passed in.  Keep the random isolated.
    item_count = rand.randrange(3, 9) - len(shop_items)

    for item_index in range(item_count):
        item = item_dist.get_random_item()

        # Avoid duplicate items.
        while item in shop_items:
            item = item_dist.get_random_item()

        shop_items.append(item)

    # Typically better items have a higher index.  The big exception is
    # that consumables are at the very top.  That's ok though.
    # TODO: Write a custom sort for ItemIDs
    return sorted(shop_items, reverse=True)


def pick_items(shop,rand_num):
    if shop in regular_shops:
        if rand_num > 4:
            item = rand.choice(llvlconsumables+plvlconsumables)
        else: 
            item = rand.choice(plvlitems+mlvlitems)
    elif shop in good_shops:
        if rand_num < 5:
            item = rand.choice(plvlconsumables + mlvlconsumables)
        else:
            item = rand.choice(mlvlitems+glvlitems)
    elif shop in best_shops:
        if rand_num < 5:
            item = rand.choice(glvlconsumables + hlvlconsumables + alvlconsumables)
        else:
            item = rand.choice(glvlitems + hlvlitems + alvlitems)
    return item
def write_slots(file_pointer,shop_start,items,shop_address):
    buffer = []
    item_count = items
    while items > 0:
       if items == 1:
            item = 0x00
       else:
            rand_num = rand.randrange(0,10,1)	
            item = pick_items(shop_start,rand_num)
       #Guarantee for Lapises from Fritz's and Fiona's shop
       if shop_start == 0xC2C71 or shop_start == 0xC2C99:
          if items == item_count:
             item = 0xCA
       #Guarantee for Amulets from shops in Kajar and the Black Omen
       if shop_start == 0xC2C7B or shop_start == 0xC2C9B:
          if items == item_count:
             item = 0x9A
       if item in buffer:
            continue
       buffer.append(item)
       file_pointer.seek(shop_address)
       file_pointer.write(st.pack("B",item))
       shop_address += 1
       items -= 1
    return shop_address
def warranty_shop(file_pointer):
    shop_address = 0x1AFC29
    guaranteed_items = [0x0,0xC8,0xC7,rand.choice([0x6,0x7,0x8]),rand.choice([0x15,0x16,0x17]),rand.choice([0x24,0x25,
    0x26]),rand.choice([0x31,0x32,0x33]),rand.choice([0x3E,0x3F,0x40,0x43])]
    shop_size = len(guaranteed_items) - 1
    while shop_size > -1:
            shop_address = write_guarantee(file_pointer,shop_address,guaranteed_items[shop_size])
            shop_size -= 1
def write_guarantee(file_pointer,shop_address,item):
    file_pointer.seek(shop_address)
    file_pointer.write(st.pack("B",item))
    shop_address += 1
    return shop_address
def randomize_shops(outfile):
   shop_pointer = 0xFC31
   shop_address = 0x1AFC31
   f = open(outfile,"r+b")
   warranty_shop(f)
   for start in shop_starts:
     if start in forbid_shops:
        f.seek(start)
        f.write(st.pack("H",shop_pointer + 1))
        continue
     shop_items = rand.randrange(4,10)
     f.seek(start)
     f.write(st.pack("H",shop_pointer))
     shop_pointer += shop_items
     shop_address = write_slots(f,start,shop_items,shop_address)
   f.close()

#
# Get a random price from 1-65000.  This function tends to 
# bias lower numbers to avoid everything being prohibitively expensive.
#
def getRandomPrice():
  r1 = rand.uniform(0, 1)
  r2 = rand.uniform(0, 1)
  return math.floor(abs(r1 - r2) * 65000 + 1)
   
#
# Modify shop prices based on the selected flags.
#
def modify_shop_prices(outfile, flag):
  if flag == "Normal":
    return
    
  f = open(outfile, "r+b")

  # Items
  # The first 147 (0x93) items are 6 bytes each.
  # Item price is 16 bits in bytes 2 and 3.
  # The price bytes are the same for all types of items.
  item_base_address = 0x0C06A4
  for index in range(0, 0x94):
    f.seek(item_base_address + (index * 6) + 1)
    price = 0
    if flag != "Free":
      price = getRandomPrice()
    f.write(st.pack("H", price))
    
  # Accessories
  # The next 39 (0x27) items are 4 bytes each.
  accessory_base_address = 0x0C0A1C
  for index in range(0, 0x28):
    f.seek(accessory_base_address + (index * 4) + 1)
    price = 0
    if flag != "Free":
      price = getRandomPrice()
    f.write(st.pack("H", price))
    
  # Key Items and Consumables
  # The final 53 (0x35) item definitions are 3 bytes each.
  consumables_base_address = 0x0C0ABC
  # In "Mostly Random" mode, exlclude midtonics, ethers, heals, 
  # revives, and shelters.
  exclusion_list = [2, 4, 10, 11, 12]
  for index in range(0, 0x36):
    f.seek(consumables_base_address + (index * 3) + 1)
    price = 0
    if flag == "Mostly Random":
      if not index in exclusion_list:
        f.write(st.pack("H", getRandomPrice()))
    elif flag == "Fully Random":
      f.write(st.pack("H", getRandomPrice()))
    else:
      # Free shops
      f.write(st.pack("H", 0))
  
  f.close()


def main():

    with open('./roms/jets_test.sfc', 'rb') as infile:
        rom = bytearray(infile.read())

    # Do a test shop writing.
    ctrom = CTRom(rom, ignore_checksum=True)
    # space_manager = ctrom.rom_data.space_manager

    # Set up some safe free blocks.
    # space_manager.mark_block((0, 0x40FFFF),
    #                          FSWriteType.MARK_USED)
    # space_manager.mark_block((0x411007, 0x5B8000),
    #                          FSWriteType.MARK_FREE)
    config = cfg.RandoConfig(rom)

    settings = rset.Settings.get_race_presets()
    settings.shopprices = rset.ShopPrices.MOSTLY_RANDOM

    process_rom(ctrom, settings, config)

    config.shop_manager.print_with_prices(config.price_manager)
    quit()

    # Turn shop pointers into ShopIDs

    print('best shops:')
    for x in best_shops:
        shop_id = (x - 0xC2C6D)//2
        name = repr(ShopID(shop_id))[1:].split(':')[0]
        print(f"    {name}")

    print('unused shops:')
    for x in shop_starts:
        shop_id = (x - 0xC2C6D)//2
        if shop_id not in (regular_shop_ids+good_shop_ids+best_shop_ids):
            name = repr(ShopID(shop_id))[1:].split(':')[0]
            print(f"    {name}")
    quit()

    # Checking to make sure the definitions are common across the files
    tw_items = tw.plvlitems
    sw_items = plvlitems

    tw_minus_sw = [x for x in tw_items if x not in sw_items]
    sw_minus_tw = [x for x in sw_items if x not in tw_items]

    print("Treasure but not enemy drop/charm:")
    for x in tw_minus_sw:
        print(f"    {ItemID(x)}")

    print("Enemy drop/charm but not item:")
    for x in sw_minus_tw:
        print(f"    {ItemID(x)}")

    # Results:
    # low_lvl_consumables: tw has powermeal but not sw
    # good_lvl_items: tw has greendream but not sw
    # hlvlconsumables: tw has tabs but not sw


if __name__ == "__main__":
    main()
    # randomize_shops("Project.sfc")
