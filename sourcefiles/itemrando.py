import math
import random

import itemdata
import ctenums
import ctstrings

import treasuredata

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
            ' Lapis-M', 11
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


_BID = _BoostID
_WE = cfg.itemdata.WeaponEffects
_AE = cfg.itemdata.ArmorEffects

_low_boosts = (
    _BID.SPEED_1,  _BID.HIT_2, _BID.STAMINA_2, _BID.POWER_2, _BID.MAGIC_2
)

_mid_boosts = (
    _BID.SPEED_1, _BID.MDEF_5, _BID.POWER_4, _BID.STAMINA_6, _BID.MAGIC_4,
    _BID.MDEF_10
)

_good_boosts = (
    _BID.SPEED_2, _BID.MDEF_12, _BID.POWER_6, _BID.MAGIC_6, _BID.HIT_10
)

_high_boosts = (
    _BID.SPEED_3, _BID.MDEF_15, _BID.POWER_STAMINA_10, _BID.MAG_MDEF_5
)


def randomize_weapon_armor_stats(settings: rset.Settings,
                                 config: cfg.RandoConfig):

    if rset.GameFlags.GEAR_RANDO not in settings.gameflags:
        return

    IID = ctenums.ItemID
    Tier = treasuredata.ItemTier
    item_db = config.itemdb

    gear_tiers = (Tier.LOW_GEAR, Tier.PASSABLE_GEAR, Tier.MID_GEAR,
                  Tier.GOOD_GEAR, Tier.HIGH_GEAR)
    gear_in_tier = {
        tier: treasuredata.get_item_list(tier)
        for tier in gear_tiers
    }

    for tier in gear_tiers:
        gear_in_tier[tier] = [x for x in gear_in_tier[tier] if x < 0x94]

    for gear_id in gear_in_tier[Tier.LOW_GEAR]:
        x = random.random()
        item = item_db[gear_id]
        if x < 0.1:
            item.secondary_stats.stat_boost_index = random.choice(_low_boosts)
        else:
            item.secondary_stats.stat_boost_index = 0

    # we're cheating here because treasuredist can be any kind of dist
    # I could make a dict of dists and assign that way.  Eventually there will
    # be more logic for gear of different tiers, so I'm leaving it expanded.
    GearDist = treasuredata.TreasureDist
    pass_dist = GearDist(
        (90, [_BoostID.NOTHING]),
        (7, _low_boosts),
        (3, _mid_boosts)
    )

    for gear_id in gear_in_tier[Tier.PASSABLE_GEAR]:
        item = item_db[gear_id]
        item.secondary_stats.stat_boost_index = pass_dist.get_random_item()

    mid_dist = GearDist(
        (85, [_BoostID.NOTHING]),
        (15, _mid_boosts)
    )

    WE = itemdata.WeaponEffects
    AE = itemdata.ArmorEffects

    for gear_id in gear_in_tier[Tier.MID_GEAR]:
        item = item_db[gear_id]
        boost = mid_dist.get_random_item()
        item.secondary_stats.stat_boost_index = boost

        if boost == _BoostID.NOTHING:
            x = random.random()
            if x < 0.1:
                item.stats.has_effect = True
                if item.is_weapon():
                    item.stats.effect_id = WE.DMG_TO_MAG_150
                elif item.is_armor():
                    item.stats.effect_id = random.choice(
                        (AE.ABSORB_FIR_25, AE.ABSORB_LIT_25, AE.ABSORB_SHD_25,
                         AE.ABSORB_WAT_25, AE.IMMUNE_SLOW_STOP,
                         AE.IMMUNE_CHAOS, AE.IMMUNE_LOCK, AE.IMMUNE_LOCK)
                    )
            else:
                item.stats.has_effect = False
                item.stats.effect_id = 0

    good_dist = GearDist(
        (80, [_BoostID.NOTHING]),
        (10, _mid_boosts),
        (10, _good_boosts)
    )

    good_wpn_effects = (
        WE.SLOW_60, WE.DMG_TO_MAG_150, WE.HP_50_50
    )

    no_effect_change_ids = (
        IID.RED_MAIL, IID.BLUE_MAIL, IID.WHITE_MAIL, IID.BLACK_MAIL
    )

    for gear_id in gear_in_tier[Tier.GOOD_GEAR]:
        item = item_db[gear_id]
        boost = good_dist.get_random_item()
        item.secondary_stats.stat_boost_index = boost

        if boost == _BoostID.NOTHING and gear_id not in no_effect_change_ids:
            x = random.random()
            if x < 0.1 and item.is_weapon():
                item.stats.has_effect = True
                item.stats.effect_id = random.choice(good_wpn_effects)
            else:
                item.stats.has_effect = False
                item.stats.effect_id = 0

    # high gear is a little weird.
    # Gloom helm has a great effect (status prot) and a low boost, so
    # we need to have that as an option.  Other items have names that are
    # descrpitive (safe helm, sight cap) that should only gets stat boosts.

    high_wpn_effects = (
        WE.CHAOS_60, WE.CRIT_4X, WE.STOP_60,
        WE.DMG_TO_MAG_200
    )
    high_arm_effects = (
        AE.IMMUNE_ALL, AE.SHIELD, AE.BARRIER
    )

    # High gear without descriptive names
    for gear_id in (IID.STAR_SWORD, IID.VEDICBLADE, IID.KALI_BLADE,
                    IID.SIREN, IID.SHOCK_WAVE, IID.ZODIACCAPE,
                    IID.GIGA_ARM, IID.TERRA_ARM, IID.BRAVESWORD,
                    IID.GLOOM_HELM, IID.RUBY_ARMOR):
        item = item_db[gear_id]
        x = random.random()

        if x < 0.25:  # Low Boost + Good Effect
            item.secondary_stats.stat_boost_index = random.choice(_low_boosts)
            item.stats.has_effect = True
            if item.is_armor():
                item.stats.effect_id = random.choice(high_arm_effects)
            elif item.is_weapon():
                item.stats.effect_id = random.choice(high_wpn_effects)
        elif x < 0.5:  # High boost + No Effect
            item.secondary_stats.stat_boost_index = \
                random.choice(_high_boosts)
            item.stats.has_effect = False
            item.stats.effect_id = 0
        else:
            item.secondary_stats.stat_boost_index = 0
            item.stats.has_effect = False
            item.stats.effect_id = 0

    awesome_arm_effects = (
        AE.IMMUNE_ALL, AE.SHIELD, AE.BARRIER, AE.HASTE
    )
    for gear_id in (IID.TABAN_SUIT, IID.NOVA_ARMOR, IID.MOON_ARMOR,
                    IID.SWALLOW, IID.SLASHER_2, IID.SHIVA_EDGE,
                    IID.PRISMDRESS):
        item = item_db[gear_id]
        x = random.random()

        if x < 0.5:  # 50% high stat boost
            item.secondary_stats.stat_boost_index = \
                random.choice(_high_boosts)
            item.stats.has_effect = False
            item.stats.effect_id = 0
        else:  # 50% high effect
            item.secondary_stats.stat_boost_index = _BoostID.NOTHING
            item.stats.has_effect = True
            if item.is_weapon():
                item.stats.effect_id = random.choice(high_wpn_effects)
            elif item.is_armor():
                item.stats.effect_id = random.choice(awesome_arm_effects)

    # Prism Helm always good.  Always gets a good status and a good boost
    item = item_db[IID.PRISM_HELM]
    item.secondary_stats.stat_boost_index = random.choice(
        (_BoostID.SPEED_2, _BoostID.MDEF_9, _BoostID.MAG_MDEF_5,
         _BoostID.POWER_STAMINA_10)
    )
    item.stats.has_effect = True
    item.stats.effect_id = random.choice(awesome_arm_effects)

    # Ultimate Gear needs something good.
    # See ultimate effects as
    #   - High dmg + crit rate (rainbow)
    #   - 0 dmg + crisis effect  (crisis arm)
    #   - random damage (wondershot)
    #   - Doom (+dmg for fallen)

    ultimate_wpns = (IID.RAINBOW, IID.VALKERYE, IID.WONDERSHOT,
                     IID.CRISIS_ARM, IID.MASAMUNE_2, IID.DOOMSICKLE)

    crit_names = {
        IID.RAINBOW: '{sword}Rainbow',
        IID.VALKERYE: '{bow}Valkerye',
        IID.WONDERSHOT: '{gun}RainbowGun',
        IID.CRISIS_ARM: '{arm}RainbowArm',
        IID.MASAMUNE_2: '{blade}Crit Leon',
        IID.DOOMSICKLE: '{scythe}RbowSickle'
    }

    crisis_names = {
        IID.RAINBOW: '{sword}Crisis Swd',
        IID.VALKERYE: '{bow}Crisis Bow',
        IID.WONDERSHOT: '{gun}Crisis Gun',
        IID.CRISIS_ARM: '{arm}Crisis Arm',
        IID.MASAMUNE_2: '{blade}CrisisMune',
        IID.DOOMSICKLE: '{scythe}Crisis Scy'
    }

    wonder_names = {
        IID.RAINBOW: '{sword}WonderSwd',
        IID.VALKERYE: '{bow}WonderBow',
        IID.WONDERSHOT: '{gun}Wondershot',
        IID.CRISIS_ARM: '{arm}WonderArm',
        IID.MASAMUNE_2: '{blade}WonderMune',
        IID.DOOMSICKLE: '{scythe}Wndrsickle'
    }

    doom_names = {
        IID.RAINBOW: '{sword}Doom Sword',
        IID.VALKERYE: '{bow}Doom Bow',
        IID.WONDERSHOT: '{gun}Doomshot',
        IID.CRISIS_ARM: '{arm}Doom Arm',
        IID.MASAMUNE_2: '{blade}Doom Blade',
        IID.DOOMSICKLE: '{scythe}Doomsickle'
    }

    for item_id in ultimate_wpns:
        mode = random.choice((0, 1, 2, 3))

        item = item_db[item_id]
        if mode == 0:  # critical_rate
            if item_id in (IID.RAINBOW, IID.VALKERYE, IID.MASAMUNE_2):
                pass
            else:
                item.stats.critical_rate = 70
                item.stats.attack = 220
                item.stats.has_effect = False
                item.stats.effect_id = WE.NONE
                item.name = ctstrings.CTNameString.from_string(
                    crit_names[item_id], 11
                )
        elif mode == 1:  # crisis mode
            item.stats.critical_rate = 30
            item.stats.attack = 0
            item.stats.has_effect = True
            item.stats.effect_id = WE.CRISIS
            item.name = ctstrings.CTNameString.from_string(
                crisis_names[item_id], 11
            )
        elif mode == 2:  # wonder mode
            item.stats.critical_rate = 40
            item.stats.attack = 250
            item.stats.has_effect = True
            item.stats.effect_id = WE.WONDERSHOT
            item.name = ctstrings.CTNameString.from_string(
                wonder_names[item_id], 11
            )
        elif mode == 3:  # doom mode
            item.stats.critical_rate = 180
            item.stats.attack = 180
            item.stats.has_effect = True
            item.stats.effect_id = WE.DOOMSICKLE
            item.name = ctstrings.CTNameString.from_string(
                doom_names[item_id], 11
            )

    ayla_fists = (IID.FIST, IID.FIST_2, IID.FIST_3)
    modes = (
        (_BID.NOTHING, _BID.SPEED_1, _BID.SPEED_2),
        (_BID.MAGIC_2, _BID.MAGIC_4, _BID.MAGIC_6),
        (_BID.NOTHING, _BID.HIT_2, _BID.HIT_10),
        (_BID.POWER_2, _BID.POWER_4, _BID.POWER_6),
        (_BID.MDEF_5, _BID.MDEF_10, _BID.MDEF_15),
        (_BID.NOTHING, _BID.STAMINA_2, _BID.STAMINA_6),
        (_BID.NOTHING, _BID.NOTHING, _BID.NOTHING)
    )

    mode = random.choice(modes)
    for ind, fist_id in enumerate(ayla_fists):
        fist = config.itemdb[fist_id]
        boost = mode[ind]
        fist.secondary_stats.stat_boost_index = boost


# This doesn't do much!  Most accessories are going to stay as-is because
# their name says what they do.
def randomize_accessories(settings: rset.Settings,
                          config: cfg.RandoConfig):

    if rset.GameFlags.GEAR_RANDO not in settings.gameflags:
        return

    IID = ctenums.ItemID

    # Randomize counter mode of rage/frenzy
    counter_accs = (IID.RAGE_BAND, IID.FRENZYBAND)

    for item_id in counter_accs:
        item = config.itemdb[item_id]
        normal_counter = random.choice((True, False))
        item.stats.has_normal_counter_mode = normal_counter

    # Put Random effects on rocks
    rocks = (IID.GOLD_ROCK, IID.SILVERROCK, IID.WHITE_ROCK,
             IID.BLUE_ROCK, IID.BLACK_ROCK)

    T5 = itemdata.Type_05_Buffs
    T6 = itemdata.Type_06_Buffs
    T8 = itemdata.Type_08_Buffs
    T9 = itemdata.Type_09_Buffs

    # arbitrary buff distribution
    rock_buff_dist = {
        (T5.GREENDREAM): 10,
        (T6.PROT_STOP): 10,
        (T8.HASTE): 2,
        (T9.BARRIER): 10,
        (T9.SHIELD): 10,
        (T9.BARRIER, T9.SHIELD): 5,
        (T9.SHADES): 5,
        (T9.SPECS): 2
    }

    rock_boosts = (_BID.SPEED_2, _BID.MDEF_12, _BID.HIT_10,
                   _BID.MAG_MDEF_5, _BID.POWER_STAMINA_10)

    for rock_id in rocks:
        rock = config.itemdb[rock_id]

        rock_bonus = random.random()
        if rock_bonus < 0.45:
            rock.stats.has_stat_boost = True
            rock.stats.has_battle_buff = False
            rock.stats.stat_boost_index = random.choice(rock_boosts)
        elif rock_bonus < 0.9:
            rock.stats.has_battle_buff = True
            rock.stats.has_stat_boost = False
            buffs = list(rock_buff_dist.keys())
            weights = (rock_buff_dist[buff] for buff in buffs)
            battle_buffs = random.choices(
                buffs,
                weights=weights,
                k=1)[0]

            rock.stats.battle_buffs = battle_buffs

    # randomize specs as specs or haste charm
    item_id = IID.PRISMSPECS
    x = random.random()
    if x < 0.5:
        item = config.itemdb[item_id]
        item.stats.battle_buffs = [T8.HASTE]
        item.name = ctstrings.CTNameString.from_string(
            '{acc}HasteSpecs'
        )
