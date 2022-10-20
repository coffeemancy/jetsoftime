from __future__ import annotations
import random

# from ctdecompress import compress, decompress, get_compressed_length
import bossscaler
import bossspot
import bossassign
import bossrandoscaling as roscale
import bossrandotypes as bt
from ctenums import LocID, EnemyID, CharID, Element, StatusEffect,\
    RecruitID
from ctrom import CTRom
import enemyrewards
import enemystats
from eventcommand import EventCommand as EC

import randosettings as rset
import randoconfig as cfg


class InsufficientSpotsException(Exception):
    pass


def get_alt_twin_slot(config: cfg.RandoConfig,
                      one_spot_boss: bt.BossID) -> int:
    '''
    Determine what the second slot should be when making the twin boss.
    '''
    base_boss = config.boss_data_dict[one_spot_boss]
    base_slot = base_boss.parts[0].slot
    base_id = base_boss.parts[0].enemy_id

    # The enemy slot for the twin is finnicky.  There is a general rule
    # that works based on the base boss's slot.
    if base_slot == 3:
        alt_slot = 7
    elif base_slot == 6:
        alt_slot = 3
    elif base_slot == 7:
        alt_slot = 9
    else:
        alt_slot = 7

    # But it doesn't always work.
    if base_id == EnemyID.GOLEM_BOSS:
        alt_slot = 8
    elif base_id == EnemyID.GOLEM:
        alt_slot = 6
    elif base_id in (EnemyID.NIZBEL, EnemyID.NIZBEL_II,
                     EnemyID.RUST_TYRANO):
        alt_slot = 6

    return alt_slot


def update_twin_boss(settings: rset.Settings,
                     config: cfg.RandoConfig):
    '''
    Use the assignment made in config.boss_assign_dict to update the twin
    boss's data (ai, animations, graphics, stats)
    '''
    twin_type = config.boss_assign_dict[bt.BossSpotID.OCEAN_PALACE_TWIN_GOLEM]
    set_twin_boss_data_in_config(twin_type, settings, config)


# Write the new EnemyID and slots into the Twin Boss data.
# This is also a convenient time to do the scaling, but it does make it weird
# when doing the rest of the scaling.
def set_twin_boss_data_in_config(one_spot_boss: bt.BossID,
                                 settings: rset.Settings,
                                 config: cfg.RandoConfig):
    # If the base boss is golem, then we don't have to do anything
    if one_spot_boss == bt.BossID.GOLEM:
        return

    twin_boss = config.boss_data_dict[bt.BossID.TWIN_BOSS]
    base_boss = config.boss_data_dict[one_spot_boss]

    base_id = base_boss.parts[0].enemy_id
    base_slot = base_boss.parts[0].slot

    alt_slot = get_alt_twin_slot(config, one_spot_boss)

    # Set the twin boss scheme
    # Note, we do not change the EnemyID from EnemyID.TWIN_BOSS.
    # The stats, graphics, etc will all be copies from the original boss
    # into the Twin spot.
    twin_boss.parts[0].slot = base_slot
    twin_boss.parts[1].slot = alt_slot

    # Give the twin boss the base boss's ai
    config.enemy_ai_db.change_enemy_ai(EnemyID.TWIN_BOSS, base_id)
    config.enemy_atk_db.copy_atk_gfx(EnemyID.TWIN_BOSS, base_id)

    twin_stats = config.enemy_dict[EnemyID.TWIN_BOSS]
    base_stats = config.enemy_dict[base_id].get_copy()

    base_stats.xp = twin_stats.xp
    base_stats.tp = twin_stats.tp
    base_stats.gp = twin_stats.gp

    config.enemy_dict[EnemyID.TWIN_BOSS] = base_stats
    base_power = roscale.get_base_boss_power(one_spot_boss, settings)
    twin_power = roscale.get_base_boss_power(bt.BossID.TWIN_BOSS, settings)

    # Scale the stats and write them to the twin boss spot in the config
    # TODO: Golem has bespoke twin scaling.  Maybe everyone should?
    scaled_stats = roscale.scale_boss_scheme_progessive(
        twin_boss, base_power, twin_power, config.enemy_dict,
        config.enemy_atk_db, config.enemy_ai_db,
        settings.game_mode
    )[EnemyID.TWIN_BOSS]

    if rset.GameFlags.BOSS_SPOT_HP in settings.gameflags:
        twin_hp = twin_stats.hp
        new_hp = bossspot.get_part_new_hps(
            base_boss.scheme, config.enemy_dict, twin_hp
        )[base_id]
        scaled_stats.hp = new_hp

    config.enemy_dict[EnemyID.TWIN_BOSS] = scaled_stats

    orig_sprite_data = config.enemy_sprite_dict[base_id].get_copy()
    orig_sprite_data.set_affect_layer_1(False)      # Just here for rusty.
    config.enemy_sprite_dict[EnemyID.TWIN_BOSS] = orig_sprite_data

    # Special case scaling in ai scripts
    if base_id == EnemyID.RUST_TYRANO:
        elem = random.choice(list(Element))
        set_rust_tyrano_element(EnemyID.TWIN_BOSS, elem,
                                config)
        set_rust_tyrano_script_mag(EnemyID.TWIN_BOSS, config)
    elif base_id == EnemyID.YAKRA_XIII:
        set_yakra_xiii_offense_boost(EnemyID.TWIN_BOSS, config)


def get_random_assignment(
        spots: list[bt.BossSpotID],
        bosses: list[bt.BossID]
        ) -> dict[bt.BossSpotID, bt.BossID]:

    if len(spots) > len(bosses):
        raise InsufficientSpotsException

    random.shuffle(bosses)

    # Zip only goes through the smaller of the two.
    return {spot: boss for spot, boss in zip(spots, bosses)}


def get_legacy_assignment(
        available_spots: list[bt.BossSpotID],
        available_bosses: list[bt.BossID]
) -> dict[bt.BossSpotID, bt.BossID]:
    '''
    Produce a random assignment where one/two-part bosses are paired with
    one/two-part spots.  No assignment is made in other spots.
    '''
    all_one_part_bosses = bt.get_one_part_bosses()
    one_part_bosses = [
        boss_id for boss_id in available_bosses
        if boss_id in all_one_part_bosses
    ]

    all_one_part_spots = bt.get_one_part_boss_spots()
    one_part_spots = [
        boss_spot_id for boss_spot_id in available_spots
        if boss_spot_id in all_one_part_spots
    ]

    all_two_part_bosses = bt.get_two_part_bosses()
    two_part_bosses = [
        boss_id for boss_id in available_bosses
        if boss_id in all_two_part_bosses
    ]

    all_two_part_spots = bt.get_two_part_boss_spots()
    two_part_spots = [
        boss_spot_id for boss_spot_id in available_spots
        if boss_spot_id in all_two_part_spots
    ]
    try:
        boss_assignment = get_random_assignment(one_part_spots,
                                                one_part_bosses)
    except InsufficientSpotsException as e:
        raise InsufficientSpotsException(
            'Error in one spot legacy assignment.'
        ) from e

    try:
        two_part_assignment = get_random_assignment(two_part_spots,
                                                    two_part_bosses)
    except InsufficientSpotsException as e:
        raise InsufficientSpotsException(
            'Error in two spot legacy assignment.'
        ) from e

    boss_assignment.update(two_part_assignment)
    return boss_assignment


def write_assignment_to_config(settings: rset.Settings,
                               config: cfg.RandoConfig):
    '''
    Write boss assignment to config.
    '''
    if rset.GameFlags.BOSS_RANDO not in settings.gameflags:
        return

    # Restrict default assignment to the provided spots.
    boss_assignment = bt.get_default_boss_assignment()
    boss_assignment = {
        spot: boss for (spot, boss) in boss_assignment.items()
        if spot in settings.ro_settings.spots
    }

    # Use fixed order.  Ordering in the ROSettings won't change assignment.
    available_spots = [spot for spot in bt.BossSpotID
                       if spot in settings.ro_settings.spots]
    available_bosses = bt.get_assignable_bosses()
    available_bosses = [boss for boss in available_bosses
                        if boss in settings.ro_settings.bosses]

    # Don't randomize Giga Gaia/Woe in Ice Age
    if settings.game_mode == rset.GameMode.ICE_AGE:
        if bt.BossID.GIGA_GAIA in available_bosses:
            available_bosses.remove(bt.BossID.GIGA_GAIA)

        if bt.BossSpotID.MT_WOE in available_spots:
            available_spots.remove(bt.BossSpotID.MT_WOE)

    # Make a twin spot assignment. whenever the twin spot is in the pool.
    if bt.BossSpotID.OCEAN_PALACE_TWIN_GOLEM in available_spots:
        all_one_part_bosses = bt.get_one_part_bosses()
        available_one_part_bosses = [
            boss_id for boss_id in available_bosses
            if boss_id in all_one_part_bosses
        ]
        twin_choice = random.choice(available_one_part_bosses)
        # set_twin_boss_data_in_config(twin_choice, settings, config)
        # default assignment already has twin boss assigned to ocean palace.
        # Just make sure nothing new is done with this spot.
        available_spots.remove(bt.BossSpotID.OCEAN_PALACE_TWIN_GOLEM)

        # We're going to write the one-part BossID into the assignment dict.
        # Otherwise plando cannot set this reasonably.
        boss_assignment[bt.BossSpotID.OCEAN_PALACE_TWIN_GOLEM] = twin_choice


    if rset.ROFlags.PRESERVE_PARTS in settings.ro_settings.flags:
        legacy_assignments = get_legacy_assignment(available_spots,
                                                   available_bosses)
        boss_assignment.update(legacy_assignments)
    else:
        assignments = get_random_assignment(available_spots, available_bosses)
        boss_assignment.update(assignments)

    config.boss_assign_dict = boss_assignment


def change_enemy_sprite(
        from_enemy_id: EnemyID,
        to_enemy_id: EnemyID,
        sprite_dict: dict[EnemyID, enemystats.EnemySpriteData],
        keep_palette: bool = True
        ):
    '''
    Change an enemy's sprite data to a copy of another enemy, possibly keeping
    the original palette.
    '''
    new_sprite = sprite_dict[to_enemy_id].get_copy()

    if keep_palette:
        orig_data = sprite_dict[from_enemy_id]
        new_sprite.palette = orig_data.palette

    sprite_dict[from_enemy_id] = new_sprite


def make_boss_rando_sprite_fixes(
        assign_dict: dict[bt.BossSpotID, bt.BossID],
        sprite_dict: dict[EnemyID, enemystats.EnemyStats]
        ):
    '''
    Make sprite edits depending on boss assignments,
    - Make Guardian a Nu outside of Arris dome.
    - Make the Red/Blue beast Nus in some spots.
    - Make Giga Gaia/Rust Tyrano not affect layer1 outside of vanilla spots.
    '''

    if assign_dict[bt.BossSpotID.ARRIS_DOME] != bt.BossID.GUARDIAN:
        change_enemy_sprite(EnemyID.GUARDIAN, EnemyID.NU, sprite_dict)

    if assign_dict[bt.BossSpotID.MT_WOE] != bt.BossID.GIGA_GAIA:
        gg_data = sprite_dict[EnemyID.GIGA_GAIA_HEAD]
        gg_data.set_affect_layer_1(False)

    if assign_dict[bt.BossSpotID.GIANTS_CLAW] != bt.BossID.RUST_TYRANO:
        rusty_data = sprite_dict[EnemyID.RUST_TYRANO]
        rusty_data.set_affect_layer_1(False)

    # This is likely incomplete.  The beast sprites seem to use an incredible
    # amount of space.
    bad_mud_imp_spots = (
        bt.BossSpotID.KINGS_TRIAL, bt.BossSpotID.MAGUS_CASTLE_SLASH
    )

    bad_spots_assigned_bosses = [
        assign_dict[spot] for spot in bad_mud_imp_spots
    ]

    if bt.BossID.MUD_IMP in bad_spots_assigned_bosses:
        change_enemy_sprite(EnemyID.RED_BEAST, EnemyID.NU, sprite_dict)
        change_enemy_sprite(EnemyID.BLUE_BEAST, EnemyID.NU, sprite_dict)


def reassign_charms_drops(settings: rset.Settings,
                          config: cfg.RandoConfig):
    '''
    When bosses get moved around, their rewards are no longer appropriate for
    that part of the game.  This function calls out to enemyrewards to redo
    the drop/charm assignment after the boss randomization.
    '''
    BSID = bt.BossSpotID
    RG = enemyrewards.RewardGroup
    spot_rgs = {
        BSID.MANORIA_CATHERDAL: RG.EARLY_BOSS,
        BSID.HECKRAN_CAVE: RG.EARLY_BOSS,
        BSID.DENADORO_MTS: RG.EARLY_BOSS,
        BSID.ZENAN_BRIDGE: RG.EARLY_BOSS,
        BSID.REPTITE_LAIR: RG.MIDGAME_BOSS,
        BSID.GIANTS_CLAW: RG.MIDGAME_BOSS,
        BSID.SUNKEN_DESERT: RG.MIDGAME_BOSS,
        BSID.ARRIS_DOME: RG.MIDGAME_BOSS,
        BSID.FACTORY_RUINS: RG.MIDGAME_BOSS,
        BSID.PRISON_CATWALKS: RG.MIDGAME_BOSS,
        BSID.KINGS_TRIAL: RG.MIDGAME_BOSS,
        BSID.MAGUS_CASTLE_FLEA: RG.MIDGAME_BOSS,
        BSID.MAGUS_CASTLE_SLASH: RG.MIDGAME_BOSS,
        BSID.OZZIES_FORT_FLEA_PLUS: RG.MIDGAME_BOSS,
        BSID.OZZIES_FORT_SUPER_SLASH: RG.MIDGAME_BOSS,
        BSID.TYRANO_LAIR_NIZBEL: RG.MIDGAME_BOSS,
        BSID.EPOCH_REBORN: RG.MIDGAME_BOSS,
        BSID.SUN_PALACE: RG.LATE_BOSS,
        BSID.ZEAL_PALACE: RG.LATE_BOSS,
        BSID.DEATH_PEAK: RG.LATE_BOSS,
        BSID.BLACK_OMEN_GIGA_MUTANT: RG.LATE_BOSS,
        BSID.BLACK_OMEN_TERRA_MUTANT: RG.LATE_BOSS, 
        BSID.BLACK_OMEN_ELDER_SPAWN: RG.LATE_BOSS,
        BSID.OCEAN_PALACE_TWIN_GOLEM: RG.LATE_BOSS,
        BSID.GENO_DOME: RG.LATE_BOSS,
        BSID.MT_WOE: RG.LATE_BOSS,
    }

    if settings.game_mode == rset.GameMode.VANILLA_RANDO:
        spot_rgs[BSID.KINGS_TRIAL] = RG.LATE_BOSS
        spot_rgs[BSID.SUNKEN_DESERT] = RG.LATE_BOSS

    for spot, boss_id in config.boss_assign_dict.items():
        scheme =  config.boss_data_dict[boss_id]
        reward_group = spot_rgs[spot]

        part_ids = list(set(part.enemy_id for part in scheme.parts))
        
        for part_id in part_ids:
            stats = config.enemy_dict[part_id]
            enemyrewards.set_enemy_charm_drop(stats, reward_group,
                                              settings.item_difficulty)


# Scale the bosses given (the game settings) and the current assignment of
# the bosses.  This is to be differentiated from the boss scaling flag which
# scales based on the key item assignment.
def scale_bosses_given_assignment(settings: rset.Settings,
                                  config: cfg.RandoConfig):

    make_boss_rando_sprite_fixes(config.boss_assign_dict,
                                 config.enemy_sprite_dict)
    update_twin_boss(settings, config)
    reassign_charms_drops(settings, config)
    roscale.make_weak_obstacle_copies(config)

    # Store hp, xp, tp, gp data before messing with stats
    hp_dict = bossspot.get_initial_hp_dict(settings, config)
    reward_dict = bossspot.get_spot_reward_dict(settings, config)

    # Now it's safe to put the boss scaling ranked stats in
    if rset.GameFlags.BOSS_SCALE in settings.gameflags:
        for boss_id in config.boss_rank:
            rank = config.boss_rank[boss_id]
            stats = bossscaler.get_ranked_boss_stats(boss_id, rank, config)
            config.enemy_dict.update(stats)

    default_assignment = bt.get_default_boss_assignment()

    # Store the scaled stats in a new dict which then gets merged into config.
    scaled_stat_dict = {}
    for spot in settings.ro_settings.spots:
        if spot == bt.BossSpotID.OCEAN_PALACE_TWIN_GOLEM:
            # This is handled by update_twin_boss() above
            continue

        assigned_boss_id = config.boss_assign_dict[spot]
        orig_boss_id = default_assignment[spot]

        spot_power = roscale.get_base_boss_power(orig_boss_id,
                                                          settings)
        assigned_boss_power = roscale.get_base_boss_power(
            assigned_boss_id, settings
        )

        from_scheme = config.boss_data_dict[orig_boss_id]
        to_scheme = config.boss_data_dict[assigned_boss_id]

        scaled_stats = roscale.scale_boss_scheme_progessive(
            to_scheme, assigned_boss_power, spot_power,
            config.enemy_dict, config.enemy_atk_db, config.enemy_ai_db,
            settings.game_mode
        )

        bossspot.distribute_rewards(reward_dict[spot], to_scheme, scaled_stats)
        if rset.GameFlags.BOSS_SPOT_HP in settings.gameflags:
            bossspot.distribute_hp(
                from_scheme, to_scheme, hp_dict, scaled_stats
            )

        # Put the stats in scaled_dict
        scaled_stat_dict.update(scaled_stats)

    # Write all of the scaled stats back to config's dict
    config.enemy_dict.update(scaled_stat_dict)

    # Update Rust Tyrano's magic boost in script
    set_rust_tyrano_script_mag(EnemyID.RUST_TYRANO, config)

    # Update Yakra XIII's attack boost
    set_yakra_xiii_offense_boost(EnemyID.YAKRA_XIII, config)


def get_obstacle_id(enemy_id: EnemyID, config: cfg.RandoConfig) -> int:
    obstacle_msg_ids = (0xBA, 0x92)  # Only covers Terra, Mega

    ai_script = config.enemy_ai_db.scripts[enemy_id]
    ai_script_b = ai_script.get_as_bytearray()
    tech_offsets = ai_script.find_command(ai_script_b, 0x02)

    for pos in tech_offsets:
        msg = ai_script_b[pos+5]

        if msg in obstacle_msg_ids:
            return ai_script_b[pos+1]

    return None


# getting/setting tyrano element share this data, so I'm putting here in a
# private global.
_tyrano_nukes = {
    Element.FIRE: 0x37,
    Element.ICE: 0x91,
    Element.LIGHTNING: 0xBB,
    Element.NONELEMENTAL: 0x8E,
    Element.SHADOW: 0x6B
}

_tyrano_minor_techs = {
    Element.FIRE: 0x0A,
    Element.ICE: 0x2A,
    Element.LIGHTNING: 0x2B,
    Element.NONELEMENTAL: 0x14,
    Element.SHADOW: 0x15  # Weird both 0x14 and 0x15 are lasers
}


def get_magus_nuke_id(config: cfg.RandoConfig):
    '''
    Get the tech id of Magus's big spell based on message id on cast.
    '''
    magus_ai = config.enemy_ai_db.scripts[EnemyID.MAGUS]
    magus_ai_b = magus_ai.get_as_bytearray()

    AI = cfg.enemyai.AIScript
    tech_cmd_len = 6
    tech_cmd_locs = AI.find_command(magus_ai_b, 2)

    for loc in tech_cmd_locs:
        msg = magus_ai_b[loc+tech_cmd_len-1]
        if msg == 0x23:
            tech_id = magus_ai_b[loc+1]
            break

    return tech_id


def set_magus_character(new_char: CharID, config: cfg.RandoConfig):

    magus_stats = config.enemy_dict[EnemyID.MAGUS]
    magus_sprite = config.enemy_sprite_dict[EnemyID.MAGUS]

    magus_nukes = {
        CharID.CRONO: 0xBB,  # Luminaire
        CharID.MARLE: 0x91,  # Hexagon Mist
        CharID.LUCCA: 0xA9,  # Flare
        CharID.ROBO: 0xBB,   # Luminaire
        CharID.FROG: 0x91,   # Hexagon Mist
        CharID.AYLA: 0x8E,   # Energy Release
        CharID.MAGUS: 0x6B   # Dark Matter
    }

    nuke_strs = {
        CharID.CRONO: 'Luminaire / Crono\'s strongest attack!',
        CharID.MARLE: 'Hexagon Mist /Marle\'s strongest attack!',
        CharID.LUCCA: 'Flare / Lucca\'s strongest attack!',
        CharID.ROBO: 'Luminaire /Robo\'s strongest attack!',
        CharID.FROG: 'Hexagon Mist /Frog\'s strongest attack.',
        CharID.AYLA: 'Energy Flare /Ayla\'s strongest attack!',
        CharID.MAGUS: 'Dark Matter / Magus\' strongest attack!',
    }

    orig_nuke_id = get_magus_nuke_id(config)
    orig_nuke = config.enemy_atk_db.get_tech(orig_nuke_id)

    new_nuke_id = magus_nukes[new_char]
    new_nuke = config.enemy_atk_db.get_tech(new_nuke_id)

    if new_nuke.effect != orig_nuke.effect:
        new_nuke.effect = orig_nuke.effect
        new_nuke_id = config.enemy_ai_db.unused_techs[-1]
        config.enemy_atk_db.set_tech(new_nuke, new_nuke_id)

    config.enemy_ai_db.change_tech_in_ai(
        EnemyID.MAGUS, orig_nuke_id, new_nuke_id
    )

    magus_sprite.set_sprite_to_pc(new_char)
    magus_stats.name = str(new_char)

    battle_msgs = config.enemy_ai_db.battle_msgs
    battle_msgs.set_msg_from_str(0x23, nuke_strs[new_char])


def set_rust_tyrano_element(tyrano_id: EnemyID,
                            tyrano_element: Element,
                            config: cfg.RandoConfig):

    nuke_id = get_rust_tyrano_nuke_id(tyrano_id, config)
    nuke = config.enemy_atk_db.get_tech(nuke_id)

    new_nuke_id = _tyrano_nukes[tyrano_element]
    new_nuke = config.enemy_atk_db.get_tech(new_nuke_id)

    if nuke.effect != new_nuke.effect:
        new_nuke.effect = nuke.effect
        new_nuke_id = config.enemy_ai_db.unused_techs[-1]
        config.enemy_atk_db.set_tech(new_nuke, new_nuke_id)

    if tyrano_element != Element.FIRE:
        power_string = 'Magic Pwr Up!'
        # String goes in 6D
        config.enemy_ai_db.battle_msgs.set_msg_from_str(0x6D, power_string)

    config.enemy_ai_db.change_tech_in_ai(tyrano_id, nuke_id, new_nuke_id)


def get_rust_tyrano_nuke_id(tyrano_id: EnemyID,
                            config: cfg.RandoConfig) -> int:
    tyrano_ai_b = config.enemy_ai_db.scripts[tyrano_id].get_as_bytearray()
    AI = cfg.enemyai.AIScript

    tech_cmd_locs = AI.find_command(tyrano_ai_b, 0x02)
    tech_cmd_len = 6

    for loc in tech_cmd_locs:
        msg = tyrano_ai_b[loc+tech_cmd_len-1]
        if msg == 0x33:
            tech_id = tyrano_ai_b[loc+1]
            break

    return tech_id


def get_rust_tyrano_element(tyrano_id: EnemyID,
                            config: cfg.RandoConfig) -> Element:
    nuke_id = get_rust_tyrano_nuke_id(tyrano_id, config)
    nuke = config.enemy_atk_db.get_tech(nuke_id)
    return nuke.control.element


def set_yakra_xiii_offense_boost(
        yakra_id: EnemyID,
        config: cfg.RandoConfig
):
    '''
    Update Yakra XIII AI script to boost atk by 1.5x instead of to 0xFD.
    '''
    yakra_ai = config.enemy_ai_db.scripts[yakra_id]
    yakra_ai_b = yakra_ai.get_as_bytearray()

    AI = cfg.enemyai.AIScript

    base_offense = config.enemy_dict[yakra_id].offense
    boosted_offense = round(min(base_offense * 1.5, 0xFF))

    loc = AI.find_command(yakra_ai_b, 0x12)[0]
    cmd = yakra_ai_b[loc: loc+16]

    stats_boosted = [cmd[x] for x in range(5, 14, 2)]
    if 0x3D in stats_boosted:
        # Jets actually removes the offense boost, so we should only find
        # this in vanilla mode.
        stat_ind = stats_boosted.index(0x3D)
        cmd_ind = 5 + 2*stat_ind
        ai_ind = loc + cmd_ind + 1
        yakra_ai_b[ai_ind] = boosted_offense

        config.enemy_ai_db.scripts[yakra_id] = AI(yakra_ai_b)


# Rust Tyrano magic stat scales
# grows 30 (init), 65, 100, 175, 253.
# cumulative factors: 13/6, 10/3, 35/6, 253/30
def set_rust_tyrano_script_mag(tyrano_id: EnemyID,
                               config: cfg.RandoConfig):
    tyrano_ai = config.enemy_ai_db.scripts[tyrano_id]
    tyrano_ai_b = tyrano_ai.get_as_bytearray()

    base_mag = config.enemy_dict[tyrano_id].magic
    factors = [13/6, 10/3, 35/6, 253/30]
    new_magic_vals = [min(round(x*base_mag), 255) for x in factors]

    # There should be four set magic commands of the form
    # 0B 39 XX 00 6D
    # 0B - Change Stat, 39 - Stat offset (magic), XX - Magnitude
    # 00 - Mode = set, 6D - message to display

    AI = cfg.enemyai.AIScript
    stat_set_cmd_locs = AI.find_command(tyrano_ai_b, 0x0B)

    stat_num = 0
    for ind in stat_set_cmd_locs:
        if tyrano_ai_b[ind] == 0x0B and tyrano_ai_b[ind+4] == 0x6D:
            tyrano_ai_b[ind+2] = new_magic_vals[stat_num]
            stat_num += 1
        else:
            print('Warning: Found other stat mod')

    config.enemy_ai_db.scripts[tyrano_id] = AI(tyrano_ai_b)


# This needs some explaining.
# patch.ips sets BlackTyrano to Water with a jets-specific hex mist copy.
# Vanilla rando mode can't use that tech.  It could be added, but in general
# vanilla rando needs to make a new copy with a different power anyway.
# Vanilla mode is going to need multiple copies of some of the elemental
# spells with different powers because of Magus anyway.

# This method of setting does the following
# 1) Identify the nuke id based on corresponding battle message.  This works
#    regardless standard or vanilla rando.
# 2) Identify the element of the nuke by inspecting the tech.
# 3) Identify the minor tech by the element.  By happenstance, the minor tech
#    ids do not need to change between vanilla and standard.
# 4) Identify the new nuke and new minor tech based on the desired element,
#    and make the switch.
def set_black_tyrano_element(element: Element, config: cfg.RandoConfig):
    nuke_id = get_black_tyrano_nuke_id(config)
    nuke = config.enemy_atk_db.get_tech(nuke_id)

    orig_elem = nuke.control.element
    minor_tech_id = _tyrano_minor_techs[orig_elem]
    new_minor_tech_id = _tyrano_minor_techs[element]

    new_nuke_id = _tyrano_nukes[element]
    new_nuke = config.enemy_atk_db.get_tech(new_nuke_id)

    if nuke.effect != new_nuke.effect:
        new_nuke.effect = nuke.effect
        new_nuke_id = config.enemy_ai_db.unused_techs[-1]
        config.enemy_atk_db.set_tech(new_nuke, new_nuke_id)

    config.enemy_ai_db.change_tech_in_ai(
        EnemyID.BLACKTYRANO, nuke_id, new_nuke_id
    )
    config.enemy_ai_db.change_tech_in_ai(
        EnemyID.BLACKTYRANO, minor_tech_id, new_minor_tech_id
    )


def get_black_tyrano_element(config: cfg.RandoConfig) -> Element:
    nuke_id = get_black_tyrano_nuke_id(config)
    nuke = config.enemy_atk_db.get_tech(nuke_id)
    return nuke.control.element


def get_black_tyrano_nuke_id(config: cfg.RandoConfig) -> int:
    # Find tyrano nuke by looking for the tech that has the "0" msg.
    tyrano_ai = config.enemy_ai_db.scripts[EnemyID.BLACKTYRANO]
    tyrano_ai_b = tyrano_ai.get_as_bytearray()

    AI = cfg.enemyai.AIScript
    stat_cmd_len = 16

    stat_set_cmd_locs = AI.find_command(tyrano_ai_b, 0x12)

    for loc in stat_set_cmd_locs:
        msg = tyrano_ai_b[loc+stat_cmd_len-1]
        if msg == 0x33:
            tech_id = tyrano_ai_b[loc+1]
            break

    return tech_id


# Magus gets random hp and a random character sprite (ctenums.CharID)
# Black Tyrano gets random hp and a random element (ctenums.Element)
def randomize_midbosses(settings: rset.Settings, config: cfg.RandoConfig):

    if settings.game_mode != rset.GameMode.VANILLA_RANDO:
        # Random hp from 10k to 15k
        magus_stats = config.enemy_dict[EnemyID.MAGUS]
        magus_stats.hp = random.randrange(10000, 15001, 1000)

    if settings.game_mode == rset.GameMode.LEGACY_OF_CYRUS:
        magus_char = config.char_assign_dict[RecruitID.PROTO_DOME].held_char
    else:
        magus_char = random.choice(list(CharID))

    set_magus_character(magus_char, config)

    if settings.game_mode != rset.GameMode.VANILLA_RANDO:
        config.enemy_dict[EnemyID.BLACKTYRANO].hp = \
            random.randrange(8000, 13001, 1000)

    tyrano_element = random.choice(list(Element))
    set_black_tyrano_element(tyrano_element, config)
    set_rust_tyrano_element(EnemyID.RUST_TYRANO, tyrano_element, config)

    # We're going to jam obstacle randomization here
    SE = StatusEffect
    rand_num = random.randrange(0, 10, 1)

    #  if rand_num < 2:
    #      status_effect = rand.choice(1,0x40) #Blind, Poison
    if rand_num < 8:
        status_effect = random.choice(
            [SE.SLEEP, SE.LOCK, SE.SLOW])
    else:
        status_effect = random.choice([SE.CHAOS, SE.STOP])     # Chaos, Stop

    obstacle = config.enemy_atk_db.get_tech(0x58)
    obstacle.effect.status_effect = status_effect
    config.enemy_atk_db.set_tech(obstacle, 0x58)


def write_bosses_to_ctrom(ctrom: CTRom, config: cfg.RandoConfig):

    # Config should have a list of what bosses are to be placed where, so
    # now it's just a matter of writing them to the ctrom.

    # Associate each boss location with the function which sets that
    # location's boss.
    ba = bossassign
    assign_fn_dict = {
        LocID.MANORIA_COMMAND: ba.set_manoria_boss,
        LocID.CAVE_OF_MASAMUNE: ba.set_denadoro_boss,
        LocID.REPTITE_LAIR_AZALA_ROOM: ba.set_reptite_lair_boss,
        LocID.MAGUS_CASTLE_FLEA: ba.set_magus_castle_flea_spot_boss,
        LocID.MAGUS_CASTLE_SLASH: ba.set_magus_castle_slash_spot_boss,
        LocID.GIANTS_CLAW_TYRANO: ba.set_giants_claw_boss,
        LocID.TYRANO_LAIR_NIZBEL: ba.set_tyrano_lair_midboss,
        LocID.ZEAL_PALACE_THRONE_NIGHT: ba.set_zeal_palace_boss,
        LocID.ZENAN_BRIDGE_BOSS: ba.set_zenan_bridge_boss,
        LocID.DEATH_PEAK_GUARDIAN_SPAWN: ba.set_death_peak_boss,
        LocID.BLACK_OMEN_GIGA_MUTANT: ba.set_giga_mutant_spot_boss,
        LocID.BLACK_OMEN_TERRA_MUTANT: ba.set_terra_mutant_spot_boss,
        LocID.BLACK_OMEN_ELDER_SPAWN: ba.set_elder_spawn_spot_boss,
        LocID.HECKRAN_CAVE_NEW: ba.set_heckrans_cave_boss,
        LocID.KINGS_TRIAL_NEW: ba.set_kings_trial_boss,
        LocID.OZZIES_FORT_FLEA_PLUS: ba.set_ozzies_fort_flea_plus_spot_boss,
        LocID.OZZIES_FORT_SUPER_SLASH:
        ba.set_ozzies_fort_super_slash_spot_boss,
        LocID.SUN_PALACE: ba.set_sun_palace_boss,
        LocID.SUNKEN_DESERT_DEVOURER: ba.set_desert_boss,
        LocID.OCEAN_PALACE_TWIN_GOLEM: ba.set_twin_golem_spot,
        LocID.GENO_DOME_MAINFRAME: ba.set_geno_dome_boss,
        LocID.MT_WOE_SUMMIT: ba.set_mt_woe_boss,
        LocID.ARRIS_DOME_GUARDIAN_CHAMBER: ba.set_arris_dome_boss,
        LocID.REBORN_EPOCH: ba.set_epoch_boss
    }

    # Now do the writing. Only to locations in the above dict.  Only if the
    # assignment differs from default.

    default_assignment = bt.get_default_boss_assignment()
    current_assignment = config.boss_assign_dict

    for spot in current_assignment.keys():
        if current_assignment[spot] == default_assignment[spot] and \
           spot != LocID.OCEAN_PALACE_TWIN_GOLEM:
            # print(f"Not assigning to {loc}.  No change from default.")
            pass
        else:
            if spot not in assign_fn_dict:
                raise ValueError(
                    f"Error: Tried assigning to {spot}.  Location not "
                    "supported for boss randomization."
                )

            assign_fn = assign_fn_dict[spot]
            boss_id = current_assignment[spot]
            boss_scheme = config.boss_data_dict[boss_id].scheme
            # print(f"Writing {boss_id} to {loc}")
            # print(f"{boss_scheme}")
            assign_fn(ctrom, boss_scheme)

    # New fun sprite bug:  Enemy 0x4F was a frog before it was turned into
    # the twin golem.  Turning it into other bosses can make for pink screens
    # in the LW credits.

    # Put a different frog sprite in there.
    script = ctrom.script_manager.get_script(LocID.CREDITS_4)
    frog1_load = EC.load_enemy(0x4F, 9, False)
    frog2_load = EC.load_enemy(0x4F, 8, False)

    pos = script.find_exact_command(frog1_load)
    script.data[pos+1] = int(EnemyID.T_POLE)

    pos = script.find_exact_command(frog2_load)
    script.data[pos+1] = int(EnemyID.T_POLE)
