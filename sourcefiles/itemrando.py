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

# Note:  This is done after roboribbon swaps stat boosts.


class _BoostID(ctenums.StrIntEnum):
    NOTHING = 0x00
    SPEED_1 = 0x01
    HIT_2 = 0x02
    POWER_2 = 0x03
    STAMINA_2 = 0x04
    MAGIC_2 = 0x05
    MDEF_5 = 0x06
    SPEED_3 = 0x07
    HIT_10 = 0x08
    POWER_6 = 0x09
    MAGIC_6 = 0x0A
    MDEF_10 = 0x0B
    POWER_4 = 0x0C
    SPEED_2 = 0x0D
    MDEF_15 = 0x0E
    STAMINA_6 = 0x0F
    MAGIC_4 = 0x10
    MDEF_12 = 0x11
    MAG_MDEF_5 = 0x12
    POWER_STAMINA_10 = 0x13
    MDEF_5_DUP = 0x14
    MDEF_9 = 0x15


def randomize_weapon_armor_stats(settings: rset.Settings,
                                 config: cfg.RandoConfig):
    BID = _BoostID
    low_boosts = (
        BID.HIT_2, BID.STAMINA_2, BID.POWER_2, BID.MAGIC_2
    )

    mid_boosts = (
        BID.SPEED_1, BID.MDEF_5, BID.POWER_4, BID.STAMINA_6, BID.MAGIC_4
    )

    good_boosts = (
        BID.SPEED_2, BID.MDEF_9, BID.POWER_6, BID.MAGIC_6, BID.HIT_10
    )

    high_boosts = (
        BID.SPEED_3, BID.MDEF_15, BID.POWER_STAMINA_10, BID.MAG_MDEF_5
    )
        

# This doesn't do much!  Most accessories are going to stay as-is because
# their name says what they do.
def randomize_accessories(settings: rset.Settings,
                          config: cfg.RandoConfig):
    IID = ctenums.ItemID

    # Randomize counter mode of rage/frenzy
    counter_accs = (IID.RAGE_BAND, IID.FRENZYBAND)

    for item_id in counter_accs:
        item = config.itemdb[item_id]
        normal_counter = random.choice((True, False))
        item.stats.has_normal_counter_mode = normal_counter

