from __future__ import annotations

import random as rand

import ctenums
import treasuredata as td
import randoconfig as cfg
import randosettings as rset

TID = ctenums.TreasureID
ItemID = ctenums.ItemID


def write_treasures_to_config(settings: rset.Settings,
                              config: cfg.RandoConfig):

    assign = config.treasure_assign_dict

    # Do standard treasure chests
    for tier in td.TreasureLocTier:
        treasures = td.get_treasures_in_tier(tier)
        dist = td.get_treasure_distribution(settings, tier)

        for treasure in treasures:
            assign[treasure].held_item = dist.get_random_item()

    # Now do special treasures.  These don't have complicated distributions.
    # The distribution is just a random choice from the items associated with
    # the  treasure tier.

    # Build up list of special TIDs and parallel list of the items associated
    # with those spots.
    specials = [
        TID.TABAN_GIFT_HELM, TID.TABAN_GIFT_WEAPON,
        TID.TRADING_POST_ARMOR, TID.TRADING_POST_HELM,
        TID.TRADING_POST_ACCESSORY,
        TID.TRADING_POST_MELEE_WEAPON,
        TID.TRADING_POST_RANGED_WEAPON,
        TID.TRADING_POST_TAB,
        TID.JERKY_GIFT
    ]

    gil = td.get_item_list
    ITier = td.ItemTier
    item_lists = [
        gil(ITier.TABAN_HELM), gil(ITier.TABAN_WEAPON),
        gil(ITier.TRADE_ARMOR), gil(ITier.TRADE_HELM),
        gil(ITier.TRADE_ACCESSORY),
        gil(ITier.TRADE_MELEE),
        gil(ITier.TRADE_RANGED),
        gil(ITier.TRADE_TAB),
        gil(ITier.JERKY_REWARD)
    ]

    for ind, tid in enumerate(specials):
        items = item_lists[ind]
        assign[tid].held_item = rand.choice(items)

    # finally rocks
    rock_tids = [TID.DENADORO_ROCK, TID.GIANTS_CLAW_ROCK,
                 TID.LARUBA_ROCK, TID.KAJAR_ROCK, TID.BLACK_OMEN_TERRA_ROCK]

    rocks = [ItemID.GOLD_ROCK, ItemID.BLUE_ROCK,
             ItemID.SILVERROCK, ItemID.BLACK_ROCK, ItemID.WHITE_ROCK]
    rand.shuffle(rocks)

    for ind, tid in enumerate(rock_tids):
        assign[tid].held_item = rocks[ind]


def ptr_to_enum(ptr_list):
    # Turn old-style pointer lists into enum lists
    treasuretier = ptr_list
    chestid = set([(x-0x35f404)//4 for x in treasuretier])
    print(' '.join(f"{x:02X}" for x in chestid))

    config = cfg.RandoConfig()
    tdict = config.treasure_assign_dict

    treasureids = [x for x in tdict.keys()
                   if type(tdict[x]) == cfg.ChestTreasure
                   and tdict[x].chest_index in chestid]

    used_ids = [tdict[x].chest_index for x in treasureids]
    unused_ids = [x for x in chestid if x not in used_ids]

    # print(' '.join(f"{x:02X}" for x in used_ids))
    print(' '.join(f"{x:02X}" for x in unused_ids))
    input()

    for x in treasureids:
        y = repr(x)
        y = y.split(':')[0].replace('<', '').replace('TreasureID', 'TID')

        print(f"{y},")

    print(len(chestid), len(treasureids))


# Helper function just used when converting from old pointer lists to
# ItemID lists.
def item_num_to_enum(item_list):
    # Turn int list to ItemID list

    enum_list = []

    for x in item_list:
        y = ctenums.ItemID(x)
        enum_list.append(y)

    for x in enum_list:
        y = repr(x).split(':')[0].replace('<', '')
        print(f"{y},")


def find_script_ptrs(ptr_list):

    for ptr in ptr_list:
        chest_index = (ptr-0x35f404)//4
        if 0 > chest_index or chest_index > 0xF8:
            print(f"{ptr:06X}")


def main():
    pass


if __name__ == "__main__":
    main()
