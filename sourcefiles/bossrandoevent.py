from __future__ import annotations

import copy
from typing import Callable, Tuple
import functools
import random

from byteops import to_little_endian

# from ctdecompress import compress, decompress, get_compressed_length
from bossdata import BossScheme, get_default_boss_assignment
import bossscaler
import bossspot
import bossassign
from ctenums import LocID, BossID, EnemyID, CharID, Element, StatusEffect,\
    RecruitID
from ctevent import Event, free_event, get_loc_event_ptr
from ctrom import CTRom
import enemyrewards
from eventcommand import EventCommand as EC, get_command, FuncSync
from eventfunction import EventFunction as EF
# from eventscript import get_location_script, get_loc_event_ptr
from freespace import FreeSpace as FS
from mapmangler import LocExits, duplicate_heckran_map, duplicate_map, \
    duplicate_location_data

import randosettings as rset
import randoconfig as cfg


# When Giga Gaia and Mother Brain get put into the pool, Zenan Bridge will
# hit the sprite limit.  This function will copy Zenan Bridge to a new map
# and adjust the scripts to link them together appropriately.
def duplicate_zenan_bridge(ctrom: CTRom, dup_loc_id: LocID):

    fsrom = ctrom.rom_data
    script_man = ctrom.script_manager

    # Copy the exists of the original Zenan Bridge to the copy
    exits = LocExits.from_rom(fsrom)
    duplicate_map(fsrom, exits, LocID.ZENAN_BRIDGE, dup_loc_id)
    exits.write_to_fsrom(fsrom)

    # Copy the script of the original Zenan Bridge to the copy
    script = script_man.get_script(LocID.ZENAN_BRIDGE)
    new_script = copy.deepcopy(script)

    # In the original script, the party runs off the screen, the screen
    # scrolls left, and then the Zombor fight begins.  To avoid sprite limits
    # we are going to warp to the Zenan copy when the team runs off the screen.

    # The part where the team runs off the screen is in obj1, func1
    start = script.get_function_start(0x01, 0x00)
    end = script.get_function_end(0x01, 0x00)

    move_party = EC.move_party(0x86, 0x08, 0x88, 0x7, 0x89, 0x0A)
    pos = script.find_exact_command(move_party, start, end)

    if pos is None:
        print('Error finding move_party')
        raise SystemExit

    # Insert the transition commands after the party moves
    new_move_party = EC.move_party(0x8B, 0x08, 0x8B, 0x7, 0x8B, 0x0A)

    script.delete_commands(pos, 1)
    # pos += len(new_move_party)

    change_loc = EC.change_location(dup_loc_id, 0x08, 0x08)

    # Make the string of new commands.
    # After the party runs off, the screen fades out and we change location
    insert_cmds = EF()
    (
        insert_cmds
        .add(new_move_party)
        .add(EC.darken(1))
        .add(EC.fade_screen())
        .add(change_loc)
    )

    script.insert_commands(insert_cmds.get_bytearray(), pos)

    # after the move party in the normal script, each pc strikes a pose and the
    # screen scrolls (4 commands). We'll delete those commands because they'll
    # never get executed since we're changing location.
    pos += len(insert_cmds.get_bytearray())
    script.delete_commands(pos, 4)

    # Now, trim down the event for the duplicate map by removing the skeletons
    # other than the ones that make Zombor and the guards.
    unneeded_objs = sorted(
        (0x0D, 0x0E, 0x0F, 0x10, 0x11, 0x12, 0x15, 0x16, 0x17, 0x0F,
         0x0E, 0x0D),
        reverse=True
    )

    for obj in unneeded_objs:
        new_script.remove_object(obj)

    # Trim down obj0, func0 so that all it does is get the party in position
    # for the fight... and preserve the string index of course.  Nobody
    # would forget to preserve the string index, right?
    string_index = new_script.get_string_index()
    string_index_cmd = EC.set_string_index(string_index)

    new_startup_func = EF()
    (
        new_startup_func
        .add(string_index_cmd)
        .add(EC.return_cmd())
        .add(move_party)
        .add(EC.end_cmd())
    )

    # TODO: Instead of a move party command, get conditionals, etc working
    #       in eventcommand.py so that I can write a short script to set
    #       initial coordinates in startup functions of player objs

    # Finally, set the new function and set the new script.
    new_script.set_function(0, 0, new_startup_func)
    script_man.set_script(new_script, LocID.ZENAN_BRIDGE_BOSS)


def duplicate_maps_on_ctrom(ctrom: CTRom):

    fsrom = ctrom.rom_data
    script_man = ctrom.script_manager

    # First do Heckran's Cave Passageways
    exits = LocExits.from_rom(fsrom)
    duplicate_heckran_map(fsrom, exits, LocID.HECKRAN_CAVE_NEW)

    exits.write_to_fsrom(fsrom)

    script = script_man.get_script(LocID.HECKRAN_CAVE_PASSAGEWAYS)

    # Notes for Hecrkan editing:
    #   - Remove 1, 2, 0xC, 0xE, 0xF, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16,
    #         0x17, 0x18
    #   - Heckran's object was 0xD, now 0xA (3 removed prior)
    #   - Can clean up object 0 because it controls multiple encounters, but
    #     There's no real value to doing so.

    new_script = copy.deepcopy(script)
    del_objs = [0x18, 0x17, 0x16, 0x15, 0x14, 0x13, 0x12, 0x11, 0x10, 0xF,
                0xE, 0xC, 2, 1]
    for x in del_objs:
        new_script.remove_object(x)

    script_man.set_script(new_script, LocID.HECKRAN_CAVE_NEW)

    # Now do King's Trial
    #   - In location 0x1B9 (Courtroom Lobby) change the ChangeLocation
    #     command of Obj8, Activate.  It's after a 'If Marle in party' command.

    script = script_man.get_script(LocID.COURTROOM_LOBBY)

    # Find the if Marle is in party command
    (pos, cmd) = script.find_command([0xD2],
                                     script.get_function_start(8, 1),
                                     script.get_function_end(8, 1))
    if pos is None or cmd.args[0] != 1:
        print("Error finding command (kings trial 1)")
        print(pos)
        print(cmd.args[1])
        exit()

    # Find the changelocation in this conditional block
    jump_target = pos + cmd.args[-1] - 1
    (pos, cmd) = script.find_command([0xDC, 0xDD, 0xDE,
                                      0xDF, 0xE0, 0xE1],
                                     pos, jump_target)

    if pos is None:
        print("Error finding command (kings trial 2)")
    else:
        loc = cmd.args[0]
        # The location is in bits 0x01FF of the argument.
        # Keep whatever the old bits have in 0xFE00 put put in the new location
        loc = (loc & 0xFE00) + int(LocID.KINGS_TRIAL_NEW)
        script.data[pos+1:pos+3] = to_little_endian(loc, 2)

    # Note, the script manager hands the actual object, so when edited there's
    # no need to script_man.set_script it

    # Duplicate King's Trial location, 0x1B6, to 0xC1
    duplicate_location_data(fsrom, LocID.KINGS_TRIAL, LocID.KINGS_TRIAL_NEW)

    # Copy and edit script to remove objects
    script = script_man.get_script(LocID.KINGS_TRIAL)
    new_script = copy.deepcopy(script)

    # Can delete:
    #   - Object 0xB: The false witness against the king
    #   - Object 0xC: The paper the chancellor holds up in trial (small)
    #   - Object 0xD: The blue sparkle left by the Yakra key
    # This might not be enough.  Maybe the soldiers can go too?  The scene will
    # be changed, but it's worth it?

    del_objs = [0x19, 0x0C, 0x0B]
    for x in del_objs:
        new_script.remove_object(x)

    # New Yakra XII object is 0xB for boss rando purposes
    script_man.set_script(new_script, LocID.KINGS_TRIAL_NEW)


# Duplicate maps which run into sprite limits for boss rando
def duplicate_maps(fsrom: FS):

    exits = LocExits.from_rom(fsrom)
    duplicate_heckran_map(fsrom, exits, 0xC0)
    exits.write_to_fsrom(fsrom)

    # While we're here let's clean up the script.  Separate that from the
    # boss randomization part.

    # Notes for Hecrkan editing:
    #   - Remove 1, 2, 0xC, 0xE, 0xF, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16,
    #         0x17, 0x18
    #   - Heckran's object was 0xD, now 0xA (3 removed prior)
    #   - Can clean up object 0 because it controls multiple encounters, but
    #     There's no real value to doing so.

    loc_id = 0x2F  # Orig Heckran location id
    loc_ptr = get_loc_event_ptr(fsrom.getbuffer(), loc_id)
    script = Event.from_rom(fsrom.getbuffer(), loc_ptr)

    del_objs = [0x18, 0x17, 0x16, 0x15, 0x14, 0x13, 0x12, 0x11, 0x10, 0xF,
                0xE, 0xC, 2, 1]
    for x in del_objs:
        script.remove_object(x)

    free_event(fsrom, 0xC0)  # New Heckran location id
    Event.write_to_rom_fs(fsrom, 0xC0, script)

    # Now do King's Trial
    #   - In location 0x1B9 (Courtroom Lobby) change the ChangeLocation
    #     command of Obj8, Activate.  It's after a 'If Marle in party' command.

    loc_id = 0x1B9
    loc_ptr = get_loc_event_ptr(fsrom.getbuffer(), loc_id)
    script = Event.from_rom(fsrom.getbuffer(), loc_ptr)

    # Find the if Marle is in party command
    (pos, cmd) = script.find_command([0xD2],
                                     script.get_function_start(8, 1),
                                     script.get_function_end(8, 1))
    if pos is None or cmd.args[0] != 1:
        print("Error finding command (kings trial 1)")
        print(pos)
        print(cmd.args[1])
        exit()

    # Find the changelocation in this conditional block
    jump_target = pos + cmd.args[-1] - 1
    (pos, cmd) = script.find_command([0xDC, 0xDD, 0xDE,
                                      0xDF, 0xE0, 0xE1],
                                     pos, jump_target)

    if pos is None:
        print("Error finding command (kings trial 2)")
    else:
        loc = cmd.args[0]
        # print(f"{loc:04X}")
        loc = (loc & 0xFE00) + 0xC1
        # print(f"{loc:04X}")
        script.data[pos+1:pos+3] = to_little_endian(loc, 2)
        # input()

    free_event(fsrom, 0x1B9)
    Event.write_to_rom_fs(fsrom, 0x1B9, script)

    # duplicate the King's Trial, 0x1B6, to 0xC1 (unused)
    duplicate_location_data(fsrom, 0x1B6, 0xC1)

    loc_ptr = get_loc_event_ptr(fsrom.getbuffer(), 0x1B6)
    script = Event.from_rom(fsrom.getbuffer(), loc_ptr)

    # Can delete:
    #   - Object 0xB: The false witness against the king
    #   - Object 0xC: The paper the chancellor holds up in trial (small)
    #   - Object 0xD: The blue sparkle left by the Yakra key
    # This might not be enough.  Maybe the soldiers can go too?  The scene will
    # be changed, but it's worth it?

    del_objs = [0x19, 0x0C, 0x0B]
    for x in del_objs:
        script.remove_object(x)

    # New Yakra XII object is 0xB

    free_event(fsrom, 0xC1)
    Event.write_to_rom_fs(fsrom, 0xC1, script)


def get_alt_twin_slot(config: cfg.RandoConfig,
                      one_spot_boss: BossID) -> int:
    base_boss = config.boss_data_dict[one_spot_boss]
    base_slot = base_boss.scheme.slots[0]
    base_id = base_boss.scheme.ids[0]

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


# Write the new EnemyID and slots into the Twin Boss data.
# This is also a convenient time to do the scaling, but it does make it weird
# when doing the rest of the scaling.
def set_twin_boss_in_config(one_spot_boss: BossID,
                            settings: rset.Settings,
                            config: cfg.RandoConfig):
    # If the base boss is golem, then we don't have to do anything because
    # patch.ips writes a super-golem in to the twin boss slot.

    # print(f'Writing {one_spot_boss} to twin boss.')
    if one_spot_boss != BossID.GOLEM:
        twin_boss = config.boss_data_dict[BossID.TWIN_BOSS]
        base_boss = config.boss_data_dict[one_spot_boss]
        base_id = base_boss.scheme.ids[0]
        base_slot = base_boss.scheme.slots[0]

        config.twin_boss_type = base_id

        alt_slot = get_alt_twin_slot(config, one_spot_boss)

        # Set the twin boss scheme
        # Note, we do not change the EnemyID from EnemyID.TWIN_BOSS.
        # The stats, graphics, etc will all be copies from the original boss
        # into the Twin spot.
        twin_boss.scheme.slots = [base_slot, alt_slot]

        # Give the twin boss the base boss's ai
        config.enemy_ai_db.change_enemy_ai(EnemyID.TWIN_BOSS, base_id)
        config.enemy_atk_db.copy_atk_gfx(EnemyID.TWIN_BOSS, base_id)

        twin_stats = config.enemy_dict[EnemyID.TWIN_BOSS]

        base_stats = config.enemy_dict[base_id].get_copy()

        base_stats.xp = twin_stats.xp
        base_stats.tp = twin_stats.tp
        base_stats.gp = twin_stats.gp

        config.enemy_dict[EnemyID.TWIN_BOSS] = base_stats
        orig_twin_power = config.boss_data_dict[BossID.TWIN_BOSS].power
        orig_power = config.boss_data_dict[one_spot_boss].power
        twin_boss.power = orig_power

        # Scale the stats and write them to the twin boss spot in the config
        # TODO: Golem has bespoke twin scaling.  Maybe everyone should?
        scaled_stats = twin_boss.scale_to_power(
            orig_twin_power,
            config.enemy_dict,
            config.enemy_atk_db,
            config.enemy_ai_db
        )[EnemyID.TWIN_BOSS]

        if rset.GameFlags.BOSS_SPOT_HP in settings.gameflags:
            twin_hp = twin_stats.hp
            new_hp = bossspot.get_part_new_hps(
                base_boss.scheme,
                config.enemy_dict,
                twin_hp
            )[base_id]

            # This may be configurable in RO settings eventually
            additional_power_scaling = False
            if additional_power_scaling:
                hp_mod = bossspot.get_power_scale_factor(
                    base_boss.power, twin_boss.power
                )
                new_hp *= hp_mod

            scaled_stats.hp = new_hp

        # Just here for rusty.
        scaled_stats.sprite_data.set_affect_layer_1(False)

        twin_boss.power = orig_power
        config.enemy_dict[EnemyID.TWIN_BOSS] = scaled_stats

        # Special case scaling
        if base_id == EnemyID.RUST_TYRANO:
            elem = random.choice(list(Element))
            set_rust_tyrano_element(EnemyID.TWIN_BOSS, elem,
                                    config)
            set_rust_tyrano_script_mag(EnemyID.TWIN_BOSS, config)

        if base_id == EnemyID.YAKRA_XIII:
            set_yakra_xiii_offense_boost(EnemyID.TWIN_BOSS, config)


# This function needs to write the boss assignment to the config respecting
# the provided settings.
def write_assignment_to_config(settings: rset.Settings,
                               config: cfg.RandoConfig):

    if rset.GameFlags.BOSS_RANDO not in settings.gameflags:
        config.boss_assign_dict = get_default_boss_assignment()
        return

    boss_settings = settings.ro_settings

    if boss_settings.preserve_parts:
        # Do some checks to make sure that the lists are ok.
        # TODO:  Make these sets to avoid repeat element errors.

        for boss in [BossID.SON_OF_SUN, BossID.RETINITE]:
            if boss in boss_settings.boss_list:
                print(f"Legacy Boss Randomization: Removing {boss} from the "
                      'boss pool')
                boss_settings.boss_list.remove(boss)

        for loc in [LocID.SUNKEN_DESERT_DEVOURER, LocID.SUN_PALACE]:
            if loc in boss_settings.loc_list:
                print(f"Legacy Boss Randomization: Removing {loc} from the "
                      'location pool')
                boss_settings.loc_list.remove(loc)

        # Make sure that there are enough one/two partbosses to distribute to
        # the one/two part locations
        one_part_bosses = [boss for boss in boss_settings.boss_list
                           if boss in BossID.get_one_part_bosses()]

        one_part_locations = [loc for loc in boss_settings.loc_list
                              if loc in LocID.get_one_spot_boss_locations()]

        # Now, we're allowing a repeat assignment to ocean palace, so it does
        # not require a unique boss to go there.
        if LocID.OCEAN_PALACE_TWIN_GOLEM in one_part_locations:
            has_twin_spot = True
            num_one_part_locs = len(one_part_locations) - 1
        else:
            has_twin_spot = False
            num_one_part_locs = len(one_part_locations)

        if len(one_part_bosses) < num_one_part_locs:
            print("Legacy Boss Randomization Error: "
                  f"{len(one_part_locations)} "
                  "one part locations provided but "
                  f"only {len(one_part_bosses)} one part bosses provided.")
            exit()

        two_part_bosses = [boss for boss in boss_settings.boss_list
                           if boss in BossID.get_two_part_bosses()]

        two_part_locations = [loc for loc in boss_settings.loc_list
                              if loc in LocID.get_two_spot_boss_locations()]

        if len(two_part_bosses) < len(two_part_locations):
            print("Legacy Boss Randomization Error: "
                  f"{len(two_part_locations)} "
                  "two part locations provided but "
                  f"only {len(two_part_locations)} two part bosses provided.")
            exit()

        # Now do the assignment

        # First make an assignment to the twin spot and remove that location
        # from the list.
        if has_twin_spot:
            twin_boss = random.choice(one_part_bosses)
            set_twin_boss_in_config(twin_boss, settings, config)
            config.boss_assign_dict[LocID.OCEAN_PALACE_TWIN_GOLEM] = \
                BossID.TWIN_BOSS
            one_part_locations.remove(LocID.OCEAN_PALACE_TWIN_GOLEM)

        # Shuffle the bosses and assign the head of the list to the remaining
        # locations.
        random.shuffle(one_part_bosses)
        for i in range(len(one_part_locations)):
            boss = one_part_bosses[i]
            location = one_part_locations[i]
            config.boss_assign_dict[location] = boss

        random.shuffle(two_part_bosses)

        for i in range(len(two_part_locations)):
            boss = two_part_bosses[i]
            location = two_part_locations[i]
            config.boss_assign_dict[location] = boss
    else:  # Ignore part count, just randomize!
        locations = boss_settings.loc_list
        bosses = boss_settings.boss_list

        # Why sort before shuffling?
        # Because the order in which the settings file specifies the bosses
        # and locations should not change the randomized output.
        # Boss/location enums IntEnums so it's fine to sort.
        bosses = sorted(bosses)
        locations = list(sorted(locations))  # Copy because we'll edit it

        # Make a special assignment for Twin Golem Spot
        if LocID.OCEAN_PALACE_TWIN_GOLEM in locations:
            # Make a decision on how frequently to see a multi-part boss
            # in the twin spot.  For now, always choose a one-parter if
            # there is one.
            one_part_bosses = [boss for boss in bosses if
                               boss in BossID.get_one_part_bosses()]

            if one_part_bosses:
                twin_boss = random.choice(one_part_bosses)
                set_twin_boss_in_config(twin_boss, settings, config)
                config.boss_data_dict[LocID.OCEAN_PALACE_TWIN_GOLEM] = \
                    BossID.TWIN_BOSS

                # Remove twin spot from the list.
                # Do not remove the boss.  It can be assigned elsewhere too.
                locations.remove(LocID.OCEAN_PALACE_TWIN_GOLEM)

            # If no one part bosses have been provided, then make no special
            # assignment.  Just proceed as usual.

        if len(bosses) < len(locations):
            print('RO Error: Fewer bosses than locations given.')
            exit()

        random.shuffle(bosses)
        for i in range(len(locations)):
            config.boss_assign_dict[locations[i]] = bosses[i]

    # Force GG on Woe for Ice Age
    if settings.game_mode == rset.GameMode.ICE_AGE:
        woe_boss = config.boss_assign_dict[LocID.MT_WOE_SUMMIT]
        if woe_boss != BossID.GIGA_GAIA:
            if BossID.GIGA_GAIA in config.boss_assign_dict.values():
                gg_loc = next(
                    x for x in config.boss_assign_dict
                    if config.boss_assign_dict[x] == BossID.GIGA_GAIA
                )
                config.boss_assign_dict[LocID.MT_WOE_SUMMIT] = \
                    BossID.GIGA_GAIA
                config.boss_assign_dict[gg_loc] = woe_boss
            else:
                config.boss_assign_dict[LocID.MT_WOE_SUMMIT] = \
                    BossID.GIGA_GAIA

    # Sprite data changes
    # Guardian is given Nu's appearance outside of Arris Dome
    arris_boss = config.boss_assign_dict[LocID.ARRIS_DOME_GUARDIAN_CHAMBER]
    if arris_boss != BossID.GUARDIAN:
        nu_sprite = config.enemy_dict[EnemyID.NU].sprite_data.get_copy()
        guardian_data = config.enemy_dict[EnemyID.GUARDIAN]
        guardian_data.sprite_data = nu_sprite

    # GG needs to not affect Layer1 when it is outside of Woe
    woe_boss = config.boss_assign_dict[LocID.MT_WOE_SUMMIT]
    if woe_boss != BossID.GIGA_GAIA:
        gg_data = config.enemy_dict[EnemyID.GIGA_GAIA_HEAD]
        gg_data.sprite_data.set_affect_layer_1(False)

    # Same for rusty outside of giant's claw
    claw_boss = config.boss_assign_dict[LocID.GIANTS_CLAW_TYRANO]
    if claw_boss != BossID.RUST_TYRANO:
        rusty_data = config.enemy_dict[EnemyID.RUST_TYRANO]
        rusty_data.sprite_data.set_affect_layer_1(False)


# Scale the bosses given (the game settings) and the current assignment of
# the bosses.  This is to be differentiated from the boss scaling flag which
# scales based on the key item assignment.
def scale_bosses_given_assignment(settings: rset.Settings,
                                  config: cfg.RandoConfig):
    # dictionaries: location --> BossID
    default_assignment = get_default_boss_assignment()
    current_assignment = config.boss_assign_dict

    # dictionaries: BossID --> Boss data
    orig_data = config.boss_data_dict

    endgame_locs = [
        LocID.ZEAL_PALACE_THRONE_NIGHT, LocID.OCEAN_PALACE_TWIN_GOLEM,
        LocID.BLACK_OMEN_ELDER_SPAWN, LocID.BLACK_OMEN_GIGA_MUTANT,
        LocID.BLACK_OMEN_TERRA_MUTANT
    ]

    # Get the new obstacle (if needed) before tech scaling.  If further
    # obstacle duplicates are made, they will inherit the right status.
    enemy_aidb = config.enemy_ai_db
    early_obstacle_bosses = []
    obstacle_bosses = [BossID.MEGA_MUTANT, BossID.TERRA_MUTANT]
    for loc in current_assignment:
        if current_assignment[loc] in obstacle_bosses and \
           loc not in endgame_locs:

            boss = current_assignment[loc]
            early_obstacle_bosses.append(boss)

    if early_obstacle_bosses:
        # Make a new obstacle
        atk_db = config.enemy_atk_db
        new_obstacle = atk_db.get_tech(0x58)
        # Choose a status that doesn't incapacitate the team.
        # But also no point choosing poison because mega has shadow slay
        new_status = random.choice(
            (StatusEffect.LOCK, StatusEffect.SLOW)
        )
        new_obstacle.effect.status_effect = new_status

        new_id = enemy_aidb.unused_techs[-1]
        atk_db.set_tech(new_obstacle, new_id)

        for boss in early_obstacle_bosses:
            boss_data = orig_data[boss]
            scheme = boss_data.scheme

            for part in list(set(scheme.ids)):
                enemy_aidb.change_tech_in_ai(part, 0x58, new_id)

    # We want to avoid a potential chain of assignments such as:
    #    A is scaled relative to B
    #    C is scaled relative to A
    # In the second scaling we want to scale relative to A's original stats,
    # not the stats that arose from the first scaling.

    # So here's a dict to store the scaled stats before writing them back
    # to the config at the very end.
    scaled_dict = dict()
    new_power_values = dict()
    hp_dict = bossspot.get_initial_hp_dict(settings, config)

    # Now it's safe to put the boss scaling ranked stats in
    if rset.GameFlags.BOSS_SCALE in settings.gameflags:
        for boss_id in config.boss_rank:
            rank = config.boss_rank[boss_id]
            stats = bossscaler.get_ranked_boss_stats(boss_id, rank, config)
            config.enemy_dict.update(stats)

    for location in settings.ro_settings.loc_list:
        orig_boss = orig_data[default_assignment[location]]
        new_boss = orig_data[current_assignment[location]]
        scaled_stats = new_boss.scale_relative_to(orig_boss,
                                                  config.enemy_dict,
                                                  config.enemy_atk_db,
                                                  config.enemy_ai_db)

        # Update rewards to match original boss
        # TODO: This got too big.  Break into own function?
        # orig_id = default_assignment[location]
        # new_id = current_assignment[location]
        # print(f'{orig_id} ({orig_boss.power}) --> '
        #       f'{new_id} ({new_boss.power})')
        spot_xp = sum(config.enemy_dict[part].xp
                      for part in orig_boss.scheme.ids)
        spot_tp = sum(config.enemy_dict[part].tp
                      for part in orig_boss.scheme.ids)
        spot_gp = sum(config.enemy_dict[part].gp
                      for part in orig_boss.scheme.ids)
        spot_reward_group = enemyrewards.get_tier_of_enemy(
            orig_boss.scheme.ids[0]
        )

        boss_xp = sum(config.enemy_dict[part].xp
                      for part in new_boss.scheme.ids)
        boss_tp = sum(config.enemy_dict[part].tp
                      for part in new_boss.scheme.ids)
        boss_gp = sum(config.enemy_dict[part].gp
                      for part in new_boss.scheme.ids)

        for ind, part in enumerate(scaled_stats.keys()):
            part_count = sum(
                part_id == part for part_id in new_boss.scheme.ids
            )
            part_xp = sum(
                config.enemy_dict[part_id].xp
                for part_id in new_boss.scheme.ids
                if part_id == part
            )

            part_tp = sum(
                config.enemy_dict[part_id].tp
                for part_id in new_boss.scheme.ids
                if part_id == part
            )

            part_gp = sum(
                config.enemy_dict[part_id].gp
                for part_id in new_boss.scheme.ids
                if part_id == part
            )

            if boss_xp == 0:
                scaled_stats[part].xp = 0
            else:
                scaled_stats[part].xp = \
                    round(part_xp/(part_count*boss_xp)*spot_xp)

            if boss_tp == 0:
                scaled_stats[part].tp = 0
            else:
                scaled_stats[part].tp = \
                    round(part_tp/(part_count*boss_tp)*spot_tp)

            if boss_gp == 0:
                scaled_stats[part].gp = 0
            else:
                scaled_stats[part].gp = \
                    round(part_gp/(part_count*boss_gp)*spot_gp)

            enemyrewards.set_enemy_charm_drop(
                scaled_stats[part],
                spot_reward_group,
                settings.item_difficulty
            )

        new_power_values[location] = orig_boss.power

        if rset.GameFlags.BOSS_SPOT_HP in settings.gameflags:
            new_hps = bossspot.get_scaled_hp_dict(
                orig_boss, new_boss, hp_dict,
                additional_power_scaling=False
            )
            for part in new_hps:
                scaled_stats[part].hp = new_hps[part]

        # Put the stats in scaled_dict
        scaled_dict.update(scaled_stats)

    # In case of multiple power adjustments, make sure that the boss powers
    # are properly updated.
    for loc in new_power_values:
        boss = config.boss_assign_dict[loc]
        config.boss_data_dict[boss].power = new_power_values[loc]

    # Write all of the scaled stats back to config's dict
    config.enemy_dict.update(scaled_dict)

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

    magus_stats.sprite_data.set_sprite_to_pc(new_char)
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
        LocID.OZZIES_FORT_SUPER_SLASH: ba.set_ozzies_fort_super_slash_spot_boss,
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

    default_assignment = get_default_boss_assignment()
    current_assignment = config.boss_assign_dict

    for loc in current_assignment.keys():
        if current_assignment[loc] == default_assignment[loc] and \
           loc != LocID.OCEAN_PALACE_TWIN_GOLEM:
            # print(f"Not assigning to {loc}.  No change from default.")
            pass
        else:
            if loc not in assign_fn_dict:
                raise ValueError(
                    f"Error: Tried assigning to {loc}.  Location not "
                    "supported for boss randomization."
                )
            else:
                assign_fn = assign_fn_dict[loc]
                boss_id = current_assignment[loc]
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
