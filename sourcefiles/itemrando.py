import math
import random
import ctenums
import ctstrings

import randoconfig as cfg
import randosettings as rset


def getRandomPrice():
    r1 = random.uniform(0, 1)
    r2 = random.uniform(0, 1)
    return math.floor(abs(r1 - r2) * 65000 + 1)


def write_item_prices_to_config(settings: rset.Settings,
                                config: cfg.RandoConfig):
    ItemID = ctenums.ItemID
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

        config.itemdb[item].price = price


def randomize_healing(settings: rset.Settings, config: cfg.RandoConfig):

    if rset.GameFlags.HEALING_ITEM_RANDO not in settings.gameflags:
        return

    ItemID = ctenums.ItemID
    item_db = config.itemdb

    base_hp_healing = random.choice(range(30, 51, 5))
    tonic_mult = random.choice((1, 2))
    mid_tonic_mult = random.choice((3, 4, 5, 6, 7))
    full_tonic_mult = random.choice((8, 9, 10, 11, 12, 13, 14))

    item_db.base_hp_healing = base_hp_healing
    item_db[ItemID.TONIC].stats.heal_multiplier = tonic_mult
    item_db[ItemID.MID_TONIC].stats.heal_multiplier = mid_tonic_mult
    item_db[ItemID.FULL_TONIC].stats.heal_multiplier = full_tonic_mult

    base_mp_healing = random.choice(range(7, 14, 1))
    ether_mult = 1
    mid_ether_mult = random.choice((2, 3, 4))
    full_ether_mult = random.choice((5, 6, 7))

    item_db.base_mp_healing = base_mp_healing
    item_db[ItemID.ETHER].stats.heal_multiplier = ether_mult
    item_db[ItemID.MID_ETHER].stats.heal_multiplier = mid_ether_mult
    item_db[ItemID.FULL_ETHER].stats.heal_multiplier = full_ether_mult

    lapis_is_hp = random.choice((True, False))

    lapis = item_db[ItemID.LAPIS]
    if lapis_is_hp:
        lapis.stats.heals_hp = True
        lapis.stats.heals_mp = False
        lapis.stats.base_healing = base_hp_healing
        lapis.stats.heal_multiplier = random.choice((3, 4, 5, 6, 7))
    else:
        lapis.stats.heals_hp = False
        lapis.stats.heals_mp = True
        lapis.stats.base_healing = base_mp_healing
        lapis.stats.heal_multiplier = random.choice((2, 3, 4))
        lapis.name = ctstrings.CTNameString.from_string(
            ' Lapis-M'
        )
