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
    revive_mult = random.choice((1,2,3))
    tonic_mult = random.choice((1, 2))
    mid_tonic_mult = random.choice((3, 4, 5, 6, 7))
    full_tonic_mult = random.choice((8, 9, 10, 11, 12, 13, 14))

    item_db.base_hp_healing = base_hp_healing
    item_db[ItemID.TONIC].stats.heal_multiplier = tonic_mult
    item_db[ItemID.MID_TONIC].stats.heal_multiplier = mid_tonic_mult
    item_db[ItemID.FULL_TONIC].stats.heal_multiplier = full_tonic_mult
    item_db[ItemID.REVIVE].stats.heal_multiplier = revive_mult

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
    POWER_6 = 0x07
    HIT_10 = 0x08
    SPEED_3 = 0x09
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


def get_boost_dict(settings: rset.Settings, config: cfg.RandoConfig):

    # Potentially change depending on item difficulty
    Dist = treasuredata.TreasureDist
    ret_dist = dict()
    # Low gear has no weapons/armor with stat boosts, but does have some
    # accessories with various low boosts
    ret_dist[treasuredata.ItemTier.LOW_GEAR] = Dist(
        (80, [_BID.NOTHING]),
        (18, [_BID.MAGIC_2, _BID.STAMINA_2, _BID.POWER_2, _BID.HIT_2]),
        ( 2, [_BID.SPEED_1])
    )

    # Passable gear only has Mag+2 (Red Katana) and slightly better accessories.
    # So we'll make this a chance of the previous tier plus improved versions.
    ret_dist[treasuredata.ItemTier.PASSABLE_GEAR] = Dist(
        (75, [_BID.NOTHING]),
        ( 5, [_BID.MAGIC_2, _BID.STAMINA_2, _BID.POWER_2, _BID.HIT_2]),
        (20, [_BID.MAGIC_4, _BID.STAMINA_6, _BID.POWER_4, _BID.HIT_10,
              _BID.SPEED_1])
    )

    # Mid gear has Md+10 (TabanHelm), Sp+2 (TabanVest), and Md+5 (LuminRobe).
    # Also slightly better accessories.

    # Originally, there are 23 weapons/armors in this tier and only 1 sp+2.
    # I'm approximating this as 5% chance of that particular bonus.  
    ret_dist[treasuredata.ItemTier.MID_GEAR] = Dist(
        (70, [_BID.NOTHING]),
        (10, [_BID.MAGIC_4, _BID.STAMINA_6, _BID.POWER_4, _BID.HIT_10,
              _BID.SPEED_1, _BID.MDEF_5]),
        (15, [_BID.MAGIC_6, _BID.POWER_6, _BID.MDEF_10]),
        ( 5, [_BID.SPEED_2])
    )

    # Good Gear gets Sp+2 (Slasher), Mg+4 (Rune Blade).  The Sp+2 is 1/22.
    # For accessories, we're at Flea vest, seals
    ret_dist[treasuredata.ItemTier.GOOD_GEAR] = Dist(
        (70, [_BID.NOTHING]),
        (10, [_BID.MAGIC_6, _BID.POWER_6, _BID.HIT_10]),
        (15, [_BID.MAG_MDEF_5, _BID.POWER_STAMINA_10, _BID.MDEF_12]),
        ( 5, [_BID.SPEED_2])
    )

    # High Gear only has Sp+1 (Gloom Helm), Md+10 (ZodiacCape).
    # Accessories get Sp+3 from Dash Ring
    ret_dist[treasuredata.ItemTier.HIGH_GEAR] = Dist(
        (70, [_BID.NOTHING]),
        (25, [_BID.MAG_MDEF_5, _BID.POWER_STAMINA_10, _BID.MDEF_10,
              _BID.MDEF_12, _BID.SPEED_1]),
        (5, [_BID.SPEED_3]),
    )

    # The only stat boosts are Sp+3 (Taban Suit, Swallow) Md+9 (Prism Helm),
    # and Md+10 (Moon Armor).  Awesome Gear probably needs special casing.
    ret_dist[treasuredata.ItemTier.AWESOME_GEAR] = Dist(
        (50, [_BID.NOTHING]),
        (25, [_BID.MDEF_9, _BID.MDEF_10, _BID.MDEF_15, _BID.POWER_STAMINA_10]),
        (25, [_BID.SPEED_2, _BID.SPEED_3]),
    )

    return ret_dist


def get_weapon_effect_dict(settings: rset.Settings, config: cfg.RandoConfig):
    # Potentially change depending on item difficulty
    # Consider whether low gear might still have decent effects
    Dist = treasuredata.TreasureDist
    WE = itemdata.WeaponEffects
    ret_dist = dict()
    
    # Low gear has no effects.
    ret_dist[treasuredata.ItemTier.LOW_GEAR] = Dist(
        (1, [WE.NONE]),
    )

    # Passable has 4x Crit (PicoMagnum) and 80% Machine Stop (Plasma Gun)
    ret_dist[treasuredata.ItemTier.PASSABLE_GEAR] = Dist(
        (85, [WE.NONE]),
        (15, [WE.CRIT_4X, WE.STOP_80_MACHINES])
    )

    # Mid gear has 150% dmg to magic (Pearl Edge)
    # Keep the lower boosts around at a low percentage.
    ret_dist[treasuredata.ItemTier.MID_GEAR] = Dist(
        (80, [WE.NONE]),
        ( 5, [WE.CRIT_4X, WE.STOP_80_MACHINES]),
        (15, [WE.DMG_TO_MAG_150]),
    )

    # Good Gear gets 60% slow (SonicArrow), 200% Dmg to magic (Rune Blade), and
    # 50% hp damage (Graedus).  I'm going to add 60% Chaos here too.
    # Keep the lower effects around?
    ret_dist[treasuredata.ItemTier.GOOD_GEAR] = Dist(
        (75, [WE.NONE]),
        (20, [WE.HP_50_50, WE.DMG_TO_MAG_200, WE.SLOW_60, WE.CHAOS_60]),
        ( 5, [WE.CRIT_4X, WE.DMG_TO_MAG_150, WE.STOP_80_MACHINES])
    )

    # High Gear adds 60% stop (Valkerye, ShockWave) and Doom (Doomsickle).
    # Doom is part of the ultimate distribution, but I'll keep it here at a
    # low percentage.
    # I'm going to be a little crazy here and add some +Dmg effects too.
    ret_dist[treasuredata.ItemTier.HIGH_GEAR] = Dist(
        (70, [WE.NONE]),
        (10, [WE.SLOW_60, WE.CHAOS_60, WE.DMG_TO_MAG_150]),
        (15, [WE.STOP_60, WE.CRIT_4X]),
        ( 5, [WE.DOOMSICKLE, WE.CRISIS, WE.WONDERSHOT, WE.DMG_125]),
    )

    # Awesome Gear has 4x Crit (Shiva Edge), Wonder, and Crisis.  There is
    # only Swallow, Shiva Edge, and Slasher2 in this tier aside from the
    # ultimate weapons.
    ret_dist[treasuredata.ItemTier.AWESOME_GEAR] = Dist(
        (60, [WE.NONE]),
        (30, [WE.CRIT_4X, WE.STOP_60]),
        (10, [WE.DOOMSICKLE, WE.CRISIS, WE.WONDERSHOT, WE.DMG_125]),
    )

    return ret_dist


def get_armor_effect_dict(settings: rset.Settings, config: cfg.RandoConfig):
    # Potentially change depending on item difficulty
    # Consider whether low gear might still have decent effects
    Dist = treasuredata.TreasureDist
    AE = itemdata.ArmorEffects
    ret_dist = dict()
    
    # Low gear has no effects.
    ret_dist[treasuredata.ItemTier.LOW_GEAR] = Dist(
        (1, [AE.NONE]),
    )

    # Passable gear has no effects.  But consider adding elem resist.
    ret_dist[treasuredata.ItemTier.PASSABLE_GEAR] = Dist(
        (1, [AE.NONE])
    )

    # Mid gear has elem absorb 25%.  We're not shuffling those effects.
    ret_dist[treasuredata.ItemTier.MID_GEAR] = Dist(
        (1, [AE.NONE]),
    )

    # Good gear gets elem absorb 100%.  We're not shuffling those effects
    ret_dist[treasuredata.ItemTier.GOOD_GEAR] = Dist(
        (1, [AE.NONE]),
    )

    # High gear gets all sorts of status protection, shield, and we might as
    # We aren't randomizing the safe helm or weak status hats.  This leaves
    # only gloom helm, zodiaccape, ruby armor, gloom cape
    # Consider adding elem absorb in this group.
    ret_dist[treasuredata.ItemTier.HIGH_GEAR] = Dist(
        (75, [AE.NONE]),
        (25, [AE.SHIELD, AE.BARRIER, AE.IMMUNE_ALL])
    )

    # Awesome gear just adds haste on top of other effects.
    # This tier is haste helm, prism helm, prismdress, taban suit, moon armor,
    # and nova armor
    ret_dist[treasuredata.ItemTier.AWESOME_GEAR] = Dist(
        (50, [AE.NONE]),
        (40, [AE.SHIELD, AE.BARRIER, AE.IMMUNE_ALL]),
        (10, [AE.HASTE])
    )

    return ret_dist


_stat_price_dict: dict[int, int] = {
    _BID.NOTHING: 0,
    _BID.SPEED_1: 80,
    _BID.SPEED_2: 16000,
    _BID.SPEED_3: 30000,
    _BID.STAMINA_2: 80,
    _BID.STAMINA_6: 800,
    _BID.POWER_2: 80,
    _BID.POWER_4: 800,
    _BID.POWER_6: 4000,
    _BID.POWER_STAMINA_10: 20000,
    _BID.HIT_2: 0,
    _BID.HIT_10: 800,
    _BID.MAGIC_2: 80,
    _BID.MAGIC_4: 800,
    _BID.MAGIC_6: 4000,
    _BID.MAG_MDEF_5: 15000,
    _BID.MDEF_10: 3000,
    _BID.MDEF_9: 2500,
    _BID.MDEF_5: 800,
    _BID.MDEF_5_DUP: 800,
    _BID.MDEF_12: 5000,
    _BID.MDEF_15: 8000,
}

_AE = itemdata.ArmorEffects
_WE = itemdata.WeaponEffects
_effect_price_dict: dict[int, int] = {
    _AE.NONE: 0,
    _AE.BARRIER: 20000,
    _AE.SHIELD: 20000,
    _AE.HASTE: 40000,
    _AE.IMMUNE_ALL: 40000,
    _AE.IMMUNE_CHAOS: 7000,
    _AE.IMMUNE_LOCK: 7000,
    _AE.IMMUNE_SLOW_STOP: 7000,
    _AE.ABSORB_LIT_25: 5000,
    _AE.ABSORB_FIR_25: 5000,
    _AE.ABSORB_SHD_25: 5000,
    _AE.ABSORB_WAT_25: 5000,
    _AE.ABSORB_LIT_100: 15000,
    _AE.ABSORB_FIR_100: 15000,
    _AE.ABSORB_SHD_100: 15000,
    _AE.ABSORB_WAT_100: 15000,
    _WE.NONE: 0,
    _WE.STOP_80_MACHINES: 1000,
    _WE.CRIT_4X: 5000,
    _WE.DMG_TO_MAG_150: 5000,
    _WE.DMG_TO_MAG_200: 7500,
    _WE.HP_50_50: 5000,
    _WE.SLOW_60: 7000,
    _WE.CHAOS_60: 5000,
    _WE.STOP_60: 10000,
    _WE.DOOMSICKLE: 30000,
    _WE.CRISIS: 50000,
    _WE.WONDERSHOT: 50000,
    _WE.DMG_125: 50000
}


def randomize_weapon_armor(item_id: ctenums.ItemID,
                           item_db: itemdata.ItemDB,
                           stat_dist: treasuredata.TreasureDist = None,
                           effect_dist: treasuredata.TreasureDist = None):
    item = item_db[item_id]

    orig_stats = item.stats.get_copy()
    orig_sec_stats = item.secondary_stats.get_copy()

    if stat_dist is not None:
        new_stat_boost = stat_dist.get_random_item()
        item.secondary_stats.stat_boost_index = new_stat_boost

    none_effects = (itemdata.WeaponEffects.NONE, itemdata.ArmorEffects.NONE)

    if effect_dist is not None:
        new_effect = effect_dist.get_random_item()
        item.stats.effect_id = new_effect

        if new_effect in none_effects:
            item.stats.has_effect = False
        else:
            item.stats.has_effect = True

        if new_effect == _WE.CRISIS:
            item.stats.attack = 0

    orig_price_mod = _effect_price_dict[orig_stats.effect_id] + \
        _stat_price_dict[orig_sec_stats.stat_boost_index]

    new_price_mod = _effect_price_dict[item.stats.effect_id] + \
        _stat_price_dict[item.secondary_stats.stat_boost_index]

    price_mod = new_price_mod - orig_price_mod

    new_price = item.price + price_mod
    if new_price < item.price // 10:
        item.price = item.price // 10
    elif new_price > 65000:
        item_price = 65000
    else:
        item.price = new_price

    if item.stats != orig_stats or item.secondary_stats != orig_sec_stats:
        orig_boost = item_db.stat_boosts[orig_sec_stats.stat_boost_index]
        cur_boost = item_db.stat_boosts[
            item.secondary_stats.stat_boost_index
        ]

        orig_effect = orig_stats.effect_id
        cur_effect = item.stats.effect_id

        
        if (
                (
                    cur_boost > orig_boost and
                    (cur_effect == orig_effect or
                     orig_effect in none_effects)
                )
                or
                (
                    cur_boost == orig_boost and
                    orig_effect in none_effects
                )
        ):
            append_str = '+'
        elif (
                (
                    cur_boost < orig_boost and
                    (cur_effect == orig_effect or cur_effect in none_effects)
                )
                or
                (
                    cur_boost == orig_boost and
                    (cur_effect in none_effects and
                     orig_effect not in none_effects)
                )
        ):
            append_str = '-'
        else:
            append_str = '?'

        append_to_item_name(item, append_str)

    # Special cases for naming.
    # Currently only Haste Helm
    AE = itemdata.ArmorEffects
    if item_id == ctenums.ItemID.HASTE_HELM:
        if new_effect == AE.SHIELD:
            new_str = '{helm}ShieldHelm'
        elif new_effect == AE.BARRIER:
            new_str = '{helm}Wall Helm'
        elif new_effect == AE.IMMUNE_ALL:
            new_str = '{helm}ImmuneHelm'
        elif new_effect == AE.HASTE:
            new_str = '{helm}Haste Helm'
        else:
            new_str = '{helm}Waste Helm'

        item.set_name_from_str(new_str)


def randomize_weapon_armor_stats(settings: rset.Settings,
                                 config: cfg.RandoConfig):

    if rset.GameFlags.GEAR_RANDO not in settings.gameflags:
        return

    IID = ctenums.ItemID
    Tier = treasuredata.ItemTier
    WE = itemdata.WeaponEffects
    AE = itemdata.ArmorEffects

    item_db = config.itemdb

    gear_tiers = (Tier.LOW_GEAR, Tier.PASSABLE_GEAR, Tier.MID_GEAR,
                  Tier.GOOD_GEAR, Tier.HIGH_GEAR, Tier.AWESOME_GEAR)
    gear_in_tier = {
        tier: treasuredata.get_item_list(tier)
        for tier in gear_tiers
    }

    stat_boost_dict = get_boost_dict(settings, config)
    weapon_effect_dict = get_weapon_effect_dict(settings, config)
    armor_effect_dict = get_armor_effect_dict(settings, config)


    ignored_effect_ids = (
        IID.WHITE_VEST, IID.BLUE_VEST, IID.BLACK_VEST, IID.RED_VEST,
        IID.WHITE_MAIL, IID.BLACK_MAIL, IID.BLACK_MAIL, IID.RED_MAIL,
        IID.SIGHT_CAP, IID.MEMORY_CAP, IID.TIME_HAT, IID.VIGIL_HAT
    )

    ignored_ids = (
        IID.RAINBOW, IID.WONDERSHOT, IID.VALKERYE, IID.DOOMSICKLE
    )
    
    for tier in gear_tiers:
        gear_in_tier[tier] = [x for x in gear_in_tier[tier] if x < 0x94
                              and x not in ignored_ids]

    gear_in_tier[Tier.AWESOME_GEAR].append(IID.MASAMUNE_1)
        
    for tier in gear_tiers:
        boost_dist = stat_boost_dict[tier]
        weapon_effect_dist = weapon_effect_dict[tier]
        armor_effect_dist = armor_effect_dict[tier]

        for item_id in gear_in_tier[tier]:
            item = item_db[item_id]

            if item_id in ignored_effect_ids:
                effect_dist = None
            elif item.is_weapon():
                effect_dist = weapon_effect_dist
            elif item.is_armor():
                effect_dist = armor_effect_dist
            else:
                raise ValueError('Item is not a weapon or armor.')

            randomize_weapon_armor(item_id, item_db,
                                   boost_dist, effect_dist)

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
            if item_id in (IID.WONDERSHOT, IID.VALKERYE):
                item.stats.attack = 250
            else:
                item.stats.attack = 200
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
        (_BID.HIT_2, _BID.HIT_10, _BID.HIT_10),
        (_BID.POWER_2, _BID.POWER_4, _BID.POWER_6),
        (_BID.MDEF_5, _BID.MDEF_10, _BID.MDEF_15),
        (_BID.STAMINA_2, _BID.STAMINA_6, _BID.POWER_STAMINA_10),
        (_BID.NOTHING, _BID.NOTHING, _BID.NOTHING)
    )

    mode = random.choice(modes)
    for ind, fist_id in enumerate(ayla_fists):
        fist = config.itemdb[fist_id]
        boost = mode[ind]
        fist.secondary_stats.stat_boost_index = boost


def append_to_item_name(item: itemdata.Item, append_str: str):

    def ctstr_used_len(ctstr: bytearray) -> int:
        if 0xEF in ctstr:
            return ctstr.index(0xEF)
        else:
            return len(ctstr)

    append_ctstr = ctstrings.CTNameString.from_string(append_str)
    append_size = ctstr_used_len(append_ctstr)
    append_ctstr = append_ctstr[0:append_size]

    name_used_size = ctstr_used_len(item.name)

    append_start = min(len(item.name) - append_size, name_used_size)
    item.name[append_start:append_start+append_size] = append_ctstr

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
            append_to_item_name(rock, '+')
            
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
            append_to_item_name(rock, '+')

    # randomize specs as specs or haste charm
    item_id = IID.PRISMSPECS
    x = random.random()
    if x < 0.5:
        item = config.itemdb[item_id]
        item.stats.battle_buffs = [T8.HASTE]
        item.name = ctstrings.CTNameString.from_string(
            '{acc}HasteSpecs'
        )
