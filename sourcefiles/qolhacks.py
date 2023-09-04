'''Module for quality of life hacks'''
from typing import Optional, Callable
import bossrandotypes as rotypes

import ctevent
import ctenums

from treasures import treasuretypes as ttypes

from ctrom import CTRom
import randoconfig as cfg
import randosettings as rset


class ScriptTabTreasure(ttypes.ScriptTreasure):
    '''ScriptTreasure with extra method for removing exploremode offs.'''

    def remove_pause(self, ctrom: CTRom):
        '''
        Removes the exploremode off/on from the script.  Moves the pickup
        flag before the textbox if needed.
        '''

        script = ctrom.script_manager.get_script(self.location)
        start = script.get_function_start(self.object_id, self.function_id)
        end = script.get_function_end(self.object_id, self.function_id)

        pos: Optional[int] = start
        num_removed = 0
        while True:
            # exploremode toggle commands are 0xE3.  We're nuking them
            pos, _ = script.find_command_opt([0xE3], start, end)

            if pos is None:
                break

            script.delete_commands(pos, 1)
            num_removed += 1

        # Now make sure that the flag set is after the textbox.  Otherwise
        # it's possible to pick the same tab up multiple times.

        # Bit setting is in command 0x65
        pos_flag, flag_cmd = script.find_command([0x65], start, end)

        # 0xBB, 0xC1, 0xC2 are the basic textbox commands
        pos_text, _ = script.find_command([0xBB, 0xC1, 0xC2],
                                          start, end)

        # If the item looted flag is set after the texbox, then the player
        # can keep the textbox up, leave the screen, and avoid setting the
        # flag, so the tab can be picked up again.
        if pos_flag > pos_text:
            # In this case, put the flag right before the item is added.
            pos_add_item, _ = script.find_command([0xCA], start, end)

            script.delete_commands(pos_flag, 1)
            script.insert_commands(flag_cmd.to_bytearray(), pos_add_item)


# Toma's grave's speed tab is annoying because the same function covers
# the pop turn-in and the speed tab.
# We need to
#  1) Remove the exploremode off from the start of the function
#  2) Add an exploremode on command after checking for pop, etc
#  3) Pray calling exploremode on when it's already on doesn't break things.
class TomasGraveTreasure(ScriptTabTreasure):
    '''
    Special class to handle the tab behind Toma's grave.

    Since this tab is tied to the activate function of the grave, we have to
    ensure that the normal activation of the grave works.
    '''

    def remove_pause(self, ctrom: CTRom):

        script = ctrom.script_manager.get_script(self.location)
        start = script.get_function_start(self.object_id, self.function_id)
        end = script.get_function_end(self.object_id, self.function_id)

        pos = start

        # remove initial exploremode off
        if script.data[pos] == 0xE3:
            script.delete_commands(pos, 1)
        else:
            raise ctevent.CommandNotFoundException(
                "Couldn't find initial exploremode command."
            )

        # insert an exploremode off after checks for pop
        # marker is scrollscreen (0xE7) 00 00
        scroll_screen = ctevent.EC.generic_two_arg(0xE7, 0, 0)
        pos = script.find_exact_command(scroll_screen, pos, end)

        if pos is None:
            raise ctevent.CommandNotFoundException(
                "Couldn't find scroll screen"
            )

        explore_off = ctevent.EC.generic_one_arg(0xE3, 0)
        script.insert_commands(explore_off.to_bytearray(), pos)


def force_sightscope_on(ctrom: CTRom):
    '''
    Trick the game into thinking P1 has the SightScope equipped, for enemy
    health to always be visible.
    '''

    # Seek to the location in the ROM after the game checks if P1's
    # accessory is a SightScope
    ctrom.rom_data.seek(0x0CF039)
    # Ignore the result of that comparison and evaluate to always true, by
    # overwriting the BEQ (branch-if-equal) to BRA (branch-always)
    ctrom.rom_data.write(bytes([0x80]))


def fast_tab_pickup(ctrom: CTRom):
    '''
    Remove pauses from all tabs except death peak swag tab.
    '''
    TID = ctenums.TreasureID
    LocID = ctenums.LocID
    ItemID = ctenums.ItemID

    # Eventually, this might make it into a part of the randoconfig.
    # For now, the held_item and such don't matter.  We just want the
    # location, object, function to nuke the exploremode commands.
    slow_tabs = {
        TID.GUARDIA_FOREST_POWER_TAB_600: ScriptTabTreasure(
            location=LocID.GUARDIA_FOREST_600,
            object_id=0x3F-6,
            function_id=0x01,
            item_num=0,
            reward=ItemID.POWER_TAB
        ),
        TID.GUARDIA_FOREST_POWER_TAB_1000: ScriptTabTreasure(
            location=LocID.GUARDIA_FOREST_1000,
            object_id=0x26,
            function_id=0x01,
            item_num=1,
            reward=ItemID.POWER_TAB
        ),
        TID.PORRE_MARKET_600_POWER_TAB: ScriptTabTreasure(
            location=LocID.PORRE_MARKET_600,
            object_id=0x0C,
            function_id=0x01,
            item_num=1,
            reward=ItemID.POWER_TAB
        ),
        TID.MANORIA_CONFINEMENT_POWER_TAB: ScriptTabTreasure(
            location=LocID.MANORIA_CONFINEMENT,
            object_id=0x0A,
            function_id=0x01,
            item_num=0,
            reward=ItemID.POWER_TAB
        ),
        TID.TOMAS_GRAVE_SPEED_TAB: TomasGraveTreasure(
            location=LocID.WEST_CAPE,
            object_id=0x08,
            function_id=0x01,
            item_num=0,
            reward=ItemID.SPEED_TAB
        ),
        TID.DENADORO_MTS_SPEED_TAB: ScriptTabTreasure(
            location=LocID.DENADORO_WEST_FACE,
            object_id=0x09,
            function_id=0x01,
            item_num=0,
            reward=ItemID.SPEED_TAB
        ),
        TID.GIANTS_CLAW_CAVERNS_POWER_TAB: ScriptTabTreasure(
            location=LocID.GIANTS_CLAW_CAVERNS,
            object_id=0x0D,
            function_id=0x01,
            item_num=0,
            reward=ItemID.POWER_TAB
        ),
        TID.GIANTS_CLAW_ENTRANCE_POWER_TAB: ScriptTabTreasure(
            location=LocID.GIANTS_CLAW_ENTRANCE,
            object_id=0x0B,
            function_id=0x01,
            item_num=0,
            reward=ItemID.POWER_TAB
        ),
        TID.GIANTS_CLAW_TRAPS_POWER_TAB: ScriptTabTreasure(
            location=LocID.ANCIENT_TYRANO_LAIR_TRAPS,
            object_id=0x15,
            function_id=0x01,
            item_num=0,
            reward=ItemID.POWER_TAB
        ),
        TID.MAGUS_CASTLE_DUNGEONS_MAGIC_TAB: ScriptTabTreasure(
            location=LocID.MAGUS_CASTLE_DUNGEONS,
            object_id=0x08,
            function_id=0x01,
            item_num=0,
            reward=ItemID.MAGIC_TAB
        ),
        TID.MAGUS_CASTLE_FLEA_MAGIC_TAB: ScriptTabTreasure(
            location=LocID.MAGUS_CASTLE_FLEA,
            object_id=0x0D,
            function_id=0x01,
            item_num=0,
            reward=ItemID.SPEED_TAB
        ),
        TID.ARRIS_DOME_SEALED_POWER_TAB: ScriptTabTreasure(
            location=LocID.ARRIS_DOME_SEALED_ROOM,
            object_id=0x08,
            function_id=0x01,
            item_num=0,
            reward=ItemID.SPEED_TAB
        ),
        TID.TRANN_DOME_SEALED_MAGIC_TAB: ScriptTabTreasure(
            location=LocID.TRANN_DOME_SEALED_ROOM,
            object_id=0x08,
            function_id=0x01,
            item_num=0,
            reward=ItemID.SPEED_TAB
        )
    }

    for tab in slow_tabs:
        # print(f"Made {tab} fast.")
        slow_tabs[tab].remove_pause(ctrom)


def enable_boss_sightscope(config: cfg.RandoConfig):
    '''
    Make all bosses able to be sightscoped.
    '''
    for boss in list(rotypes.BossID):
        boss_data = config.boss_data_dict[boss]
        for part in set(boss_data.parts):
            config.enemy_dict[part.enemy_id].can_sightscope = True


def set_guaranteed_drops(ctrom: CTRom):
    '''
    If charm == drop, item drops are guaranteed.  However, when the charm and
    drop are different, there is a chance of no drop.  This function makes the
    drop always happen regardless of the charm.
    '''

    # It looks like CT checks (random_num % 100) < 90
    # The check is:
    # $FD/AC27 C9 5A       CMP #$5A
    # $FD/AC29 B0 20       BCS $20
    # Note BCS will branch when the value in >= 0x5A
    # I don't think it works out to exactly 90% chance of a drop because the
    # random numbers look to be random in [0, 0xFF].  So it's actually a bit
    # higher than 90%.

    # Changing 0x5A = 90 to 0x64 = 100 would do it
    # But let's go for overkill and make it 0xFF.
    rom = ctrom.rom_data
    rom.seek(0x3DAC28)
    rom.write(bytes([0xFF]))


def set_free_menu_glitch(ct_rom: CTRom):
    '''
    Adds a few seconds of pause to allow menu access when transitioning from
    (1) Zeal1 to Mammon M and (2) Lavos2 to Lavos3.
    '''
    EF = ctevent.EF
    EC = ctevent.EC

    func = EF()
    (
        func
        .add(EC.assign_val_to_mem(0, 0x7E0110, 1))
        .add(EC.set_explore_mode(True))
        .add(EC.pause(2))
    )

    script = ct_rom.script_manager.get_script(ctenums.LocID.BLACK_OMEN_ZEAL)
    st = script.get_function_start(8, 0)
    end = script.get_function_end(8, 0)
    pos, _ = script.find_command([0xDF], st, end)

    script.insert_commands(func.get_bytearray(), pos)

    script = ct_rom.script_manager.get_script(ctenums.LocID.LAVOS_2)
    pos = script.get_function_start(8, 0)
    end = script.get_function_end(8, 0)

    while True:
        pos, cmd = script.find_command([0xDF], pos, end)

        if cmd.args[0] & 0x1FF == 0x1DF:
            break

        pos += len(cmd)

    script.insert_commands(func.get_bytearray(), pos)


# After writing additional hacks, put them here. Based on the settings, they
# will or will not modify the ROM.
def attempt_all_qol_hacks(ct_rom: CTRom, settings: rset.Settings):
    '''
    Apply all qol hacks permitted by the settings.
    '''
    set_guaranteed_drops(ct_rom)

    GF = rset.GameFlags
    flag_fn_dict: dict[rset.GameFlags, Callable[[CTRom], None]] = {
        GF.VISIBLE_HEALTH: force_sightscope_on,
        GF.FAST_TABS: fast_tab_pickup,
        GF.FREE_MENU_GLITCH: set_free_menu_glitch
    }

    for flag, func in flag_fn_dict.items():
        if flag in settings.gameflags:
            func(ct_rom)
