from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Tuple, Type, TypeVar

import enemyai
import enemytechdb
from enemystats import EnemyStats

from ctenums import EnemyID, BossID, LocID

import piecewiselinear
import statcompute

import randosettings as rset

# Silly thing for typing classmethod return type from stackexchange
# https://stackoverflow.com/questions/44640479
T = TypeVar('T', bound='Boss')


# The BossScheme gives data for
#   1) What EnemyIDs make up the boss's parts (ids),
#   2) Where the boss's parts should be drawn relative to part 0 (disps).
#      The displacements are specified in pixels.
#   3) What enemy slots each part should use (slots).  This matters because
#      you can actually get crashes by putting enemies in the wrong slot.
@dataclass
class BossScheme:
    ids: list[EnemyID] = field(default_factory=list)
    disps: list[Tuple(int, int)] = field(default_factory=list)
    slots: list[int] = field(default_factory=list)

    # Some boss spots place the boss at the edge of the screen, and this
    # can lead some larger bosses to have parts go off screen.
    # This method will allow reordering of parts so that everything should
    # fit.  (Ex. GG in king's trial needs left arm to be in spot 0)
    def reorder(self, new_first_ind):

        for x in (self.ids, self.slots, self.disps):
            temp = x[0]
            x[0] = x[new_first_ind]
            x[new_first_ind] = temp

        # Shift displacements
        disp_0 = self.disps[0]
        for i in range(len(self.disps)):
            self.disps[i] = (self.disps[i][0] - disp_0[0],
                             self.disps[i][1] - disp_0[1])

    def reorder_horiz(self, left=True):

        x_coords = [x[0] for x in self.disps]
        if left:
            x_extr = min(x_coords)
        else:
            x_extr = max(x_coords)

        x_extr_ind = x_coords.index(x_extr)

        self.reorder(x_extr_ind)

    # Flip a boss's orientation so that bosses like guardian can fit when
    # they are located on the left/right edges of the screen.
    def flip_disps(self):

        for ind, disp in enumerate(self.disps):
            self.disps[ind] = (disp[1], disp[0])


# The Boss class combines a BossScheme with whatever data is needed to scale
# the boss.  Subclasses can define alternate scaling methods.
@dataclass
class Boss:

    scheme: BossScheme
    power: int = 0

    @classmethod
    def scale_stats(cls,
                    enemy_id: EnemyID,
                    stats: EnemyStats,
                    atk_db: enemytechdb.EnemyAttackDB,
                    ai_db: enemyai.EnemyAIDB,
                    from_power: int, to_power: int) -> EnemyStats:
        raise NotImplementedError

    def scale_to_power(
            self, new_power,
            stat_dict: dict[EnemyID, EnemyStats],
            atk_db: enemytechdb.EnemyAttackDB,
            ai_db: enemyai.EnemyAIDB,
    ) -> dict[EnemyID: EnemyStats]:
        return {
            part: self.scale_stats(part, stat_dict[part],
                                   atk_db, ai_db,
                                   self.power, new_power)
            for part in list(set(self.scheme.ids))
        }

    # Make a subclass to implement scaling styles
    # Need stats, atk/tech, ai to fully scale.
    def scale_relative_to(
            self, other: Boss,
            stat_dict: dict[EnemyID, EnemyStats],
            atk_db: enemytechdb.EnemyAttackDB,
            ai_db: enemyai.EnemyAIDB
    ) -> dict[EnemyID: EnemyStats]:
        return {
            part: self.scale_stats(part, stat_dict[part],
                                   atk_db, ai_db,
                                   self.power, other.power)
            for part in list(set(self.scheme.ids))
        }

    @classmethod
    def generic_one_spot(cls: Type[T], boss_id, slot, power) -> T:

        ids = [boss_id]
        disps = [(0, 0)]
        slots = [slot]

        scheme = BossScheme(ids, disps, slots)
        power = power

        return cls(scheme, power)

    @classmethod
    def generic_multi_spot(cls: Type[T], boss_ids, disps,
                           slots, power) -> T:

        ids = boss_ids[:]
        disps = disps[:]
        slots = slots[:]

        scheme = BossScheme(ids, disps, slots)
        power = power

        return cls(scheme, power)

    @classmethod
    def ATROPOS_XR(cls: Type[T]) -> T:
        return cls.generic_one_spot(EnemyID.ATROPOS_XR, 3, 14)

    @classmethod
    def BLACK_TYRANO(cls: Type[T]) -> T:
        ids = [EnemyID.AZALA, EnemyID.BLACKTYRANO]
        slots = [7, 3]
        disps = [(0, 0), (0, 0)]  # Not real b/c not randomizing
        power = 25

        return cls.generic_multi_spot(ids, disps, slots, power)

    @classmethod
    def DALTON_PLUS(cls: Type[T]) -> T:
        return cls.generic_one_spot(EnemyID.DALTON_PLUS, 3, 20)

    # Note to self: Extra grinder objects at end of script?
    @classmethod
    def DRAGON_TANK(cls: Type[T]) -> T:
        ids = [EnemyID.DRAGON_TANK, EnemyID.TANK_HEAD, EnemyID.GRINDER]
        slots = [3, 9, 0xA]
        disps = [(0, 0), (0, 0), (0, 0)]
        power = 15

        return cls.generic_multi_spot(ids, disps, slots, power)

    # Shell goes first for pushing on death's peak.  The first object will
    # be the static, pushable one.
    @classmethod
    def ELDER_SPAWN(cls: Type[T]) -> T:
        ids = [EnemyID.ELDER_SPAWN_SHELL,
               EnemyID.ELDER_SPAWN_HEAD]
        slots = [3, 9]
        disps = [(0, 0), (-8, 1)]
        power = 30

        return cls.generic_multi_spot(ids, disps, slots, power)

    @classmethod
    def FLEA(cls: Type[T]) -> T:
        return cls.generic_one_spot(EnemyID.FLEA, 7, 14)

    @classmethod
    def FLEA_PLUS(cls: Type[T]) -> T:
        return cls.generic_one_spot(EnemyID.FLEA_PLUS, 7, 14)

    @classmethod
    def GIGA_GAIA(cls: Type[T]) -> T:
        ids = [EnemyID.GIGA_GAIA_HEAD, EnemyID.GIGA_GAIA_LEFT,
               EnemyID.GIGA_GAIA_RIGHT]
        slots = [6, 7, 9]
        # disps = [(0, 0), (0x40, 0x30), (-0x40, 0x30)]
        disps = [(0, 0), (0x20, 0x20), (-0x20, 0x20)]
        power = 20

        return cls.generic_multi_spot(ids, disps, slots, power)

    @classmethod
    def GIGA_MUTANT(cls: Type[T]) -> T:
        ids = [EnemyID.GIGA_MUTANT_HEAD, EnemyID.GIGA_MUTANT_BOTTOM]
        slots = [3, 9]
        disps = [(0, 0), (0, 0)]
        power = 30

        return cls.generic_multi_spot(ids, disps, slots, power)

    @classmethod
    def GOLEM(cls: Type[T]) -> T:
        return cls.generic_one_spot(EnemyID.GOLEM, 3, 18)

    @classmethod
    def GOLEM_BOSS(cls: Type[T]) -> T:
        return cls.generic_one_spot(EnemyID.GOLEM_BOSS, 3, 15)

    @classmethod
    def GUARDIAN(cls: Type[T]) -> T:
        ids = [EnemyID.GUARDIAN, EnemyID.GUARDIAN_BIT,
               EnemyID.GUARDIAN_BIT]
        slots = [3, 7, 8]
        # disps = [(0, 0), (-0x50, -0x08), (0x40, -0x08)]
        disps = [(0, 0), (-0x3A, -0x08), (0x40, -0x08)]
        power = 12

        return cls.generic_multi_spot(ids, disps, slots, power)

    @classmethod
    def HECKRAN(cls: Type[T]) -> T:
        return cls.generic_one_spot(EnemyID.HECKRAN, 3, 8)

    @classmethod
    def LAVOS_SHELL(cls: Type[T]) -> T:
        return cls.generic_one_spot(
            EnemyID.LAVOS_OCEAN_PALACE, 5, 100
        )

    @classmethod
    def INNER_LAVOS(cls: type[T]) -> T:
        return cls.generic_multi_spot(
            [EnemyID.LAVOS_2_HEAD, EnemyID.LAVOS_2_LEFT,
             EnemyID.LAVOS_2_RIGHT],
            [(0, 0), (-0x32, 0xE), (0x32, 0xE)],
            [0xA, 0x6, 0x3],
            100
        )

    # Fake disps for now.
    @classmethod
    def LAVOS_CORE(cls: type[T]) -> T:
        return cls.generic_multi_spot(
            [EnemyID.LAVOS_3_CORE, EnemyID.LAVOS_3_LEFT,
             EnemyID.LAVOS_3_RIGHT],
            [(0, 0), (0, 0), (0, 0)],
            [3, 7, 9],
            100
        )

    @classmethod
    def LAVOS_SPAWN(cls: Type[T]) -> T:
        ids = [EnemyID.LAVOS_SPAWN_SHELL,
               EnemyID.LAVOS_SPAWN_HEAD]
        slots = [3, 9]
        # The "True" displacement matches ELDER_SPAWN with [(0,0), (-8, 1)]
        # For whatever reason the lavos spawn head drops down a pixel at the
        # start of a battle.
        disps = [(0, 0), (-0x8, 0)]
        power = 18
        return cls.generic_multi_spot(ids, disps, slots, power)

    @classmethod
    def MAMMON_MACHINE(cls: Type[T]) -> T:
        return cls.generic_one_spot(EnemyID.MAMMON_M, 3, 35)

    @classmethod
    def MASA_MUNE(cls: Type[T]) -> T:
        return cls.generic_one_spot(EnemyID.MASA_MUNE, 6, 12)

    @classmethod
    def MEGA_MUTANT(cls: Type[T]) -> T:
        ids = [EnemyID.MEGA_MUTANT_HEAD,
               EnemyID.MEGA_MUTANT_BOTTOM]
        slots = [3, 7]
        disps = [(0, 0), (0, 0)]
        power = 30

        return cls.generic_multi_spot(ids, disps, slots, power)

    @classmethod
    def MAGUS(cls: Type[T]) -> T:
        return cls.generic_one_spot(EnemyID.MAGUS, 3, 25)

    # For own notes:  real screens are 0x20, 0x21, 0x22.  0x23 never shows
    @classmethod
    def MOTHER_BRAIN(cls: Type[T]) -> T:
        ids = [EnemyID.MOTHERBRAIN,
               EnemyID.DISPLAY, EnemyID.DISPLAY, EnemyID.DISPLAY]
        slots = [3, 6, 7, 8]
        # disps = [(0, 0), (-0x50, -0x1F), (-0x20, -0x2F), (0x40, -0x1F)]
        # Tighten up coords to fit better.  AoE still hits screens the same
        disps = [(0, 0), (-0x40, -0xF), (-0x8, -0x1F), (0x38, -0xF)]
        power = 14

        return cls.generic_multi_spot(ids, disps, slots, power)

    @classmethod
    def MUD_IMP(cls: Type[T]) -> T:
        ids = [EnemyID.MUD_IMP, EnemyID.BLUE_BEAST, EnemyID.RED_BEAST]
        slots = [9, 3, 7]
        disps = [(0, 0), (30, 10), (0, 20)]
        power = 15

        return cls.generic_multi_spot(ids, disps, slots, power)

    @classmethod
    def NIZBEL(cls: Type[T]) -> T:
        return cls.generic_one_spot(EnemyID.NIZBEL, 3, 14)

    @classmethod
    def NIZBEL_II(cls: Type[T]) -> T:
        return cls.generic_one_spot(EnemyID.NIZBEL_II, 3, 16)

    @classmethod
    def RETINITE(cls: Type[T]) -> T:
        ids = [EnemyID.RETINITE_EYE, EnemyID.RETINITE_TOP,
               EnemyID.RETINITE_BOTTOM]
        slots = [3, 9, 6]
        disps = [(0, 0), (0, -0x8), (0, 0x28)]
        power = 12  # With water magic, retinite is 0 threat

        return cls.generic_multi_spot(ids, disps, slots, power)

    @classmethod
    def R_SERIES(cls: Type[T]) -> T:
        ids = [EnemyID.R_SERIES, EnemyID.R_SERIES, EnemyID.R_SERIES,
               EnemyID.R_SERIES]
        slots = [3, 4, 7, 8]
        disps = [(0, 0), (0, 0x20), (0x20, 0), (0x20, 0x20)]  # maybe wrong
        power = 15

        return cls.generic_multi_spot(ids, disps, slots, power)

    @classmethod
    def RUST_TYRANO(cls: Type[T]) -> T:
        return cls.generic_one_spot(EnemyID.RUST_TYRANO, 3, 15)

    @classmethod
    def SLASH_SWORD(cls: Type[T]) -> T:
        return cls.generic_one_spot(EnemyID.SLASH_SWORD, 3, 14)

    @classmethod
    def SUPER_SLASH(cls: Type[T]) -> T:
        return cls.generic_one_spot(EnemyID.SUPER_SLASH, 7, 14)

    @classmethod
    def SON_OF_SUN(cls: Type[T]) -> T:
        ids = [EnemyID.SON_OF_SUN_EYE,
               EnemyID.SON_OF_SUN_FLAME,
               EnemyID.SON_OF_SUN_FLAME,
               EnemyID.SON_OF_SUN_FLAME,
               EnemyID.SON_OF_SUN_FLAME]
        slots = [3, 4, 5, 6, 7]
        disps = [(0, 0), (-0x20, 0), (0x20, 0), (-0x10, 0x10), (0x10, 0x10)]
        power = 18
        return cls.generic_multi_spot(ids, disps, slots, power)

    @classmethod
    def TERRA_MUTANT(cls: Type[T]) -> T:
        ids = [EnemyID.TERRA_MUTANT_HEAD, EnemyID.TERRA_MUTANT_BOTTOM]
        slots = [3, 9]
        disps = [(0, 0), (0, 0)]
        power = 30

        return cls.generic_multi_spot(ids, disps, slots, power)

    @classmethod
    def TWIN_BOSS(cls: Type[T]) -> T:
        ids = [EnemyID.TWIN_BOSS, EnemyID.TWIN_BOSS]
        slots = [3, 6]
        disps = [(-0x20, 0), (0x20, 0)]
        power = 25  # This is the power of a SINGLE twin.
        return cls.generic_multi_spot(ids, disps, slots, power)

    @classmethod
    def YAKRA(cls: Type[T]) -> T:
        return cls.generic_one_spot(EnemyID.YAKRA, 3, 1)

    @classmethod
    def YAKRA_XIII(cls: Type[T]) -> T:
        return cls.generic_one_spot(EnemyID.YAKRA_XIII, 3, 12)

    @classmethod
    def ZEAL(cls: Type[T]) -> T:
        return cls.generic_one_spot(EnemyID.ZEAL, 9, 100)

    # fake disps, slots
    @classmethod
    def ZEAL_2(cls: Type[T]) -> T:
        return cls.generic_multi_spot(
            [EnemyID.ZEAL_2_CENTER, EnemyID.ZEAL_2_LEFT,
             EnemyID.ZEAL_2_RIGHT],
            [(0, 0), (0, 0), (0, 0)],
            [3, 6, 9],
            100
        )

    @classmethod
    def ZOMBOR(cls: Type[T]) -> T:
        return cls.generic_multi_spot([EnemyID.ZOMBOR_TOP,
                                       EnemyID.ZOMBOR_BOTTOM],
                                      [(0, 0), (0, 0x20)],
                                      [9, 3],
                                      5)
# end Boss class


def get_default_boss_assignment():
    return {
        LocID.PRISON_CATWALKS: BossID.DRAGON_TANK,
        LocID.BLACK_OMEN_ELDER_SPAWN: BossID.ELDER_SPAWN,
        LocID.MAGUS_CASTLE_FLEA: BossID.FLEA,
        LocID.OZZIES_FORT_FLEA_PLUS: BossID.FLEA_PLUS,
        LocID.MT_WOE_SUMMIT: BossID.GIGA_GAIA,
        LocID.BLACK_OMEN_GIGA_MUTANT: BossID.GIGA_MUTANT,
        LocID.ZEAL_PALACE_THRONE_NIGHT: BossID.GOLEM,
        LocID.ARRIS_DOME_GUARDIAN_CHAMBER: BossID.GUARDIAN,
        LocID.HECKRAN_CAVE_NEW: BossID.HECKRAN,
        LocID.DEATH_PEAK_GUARDIAN_SPAWN: BossID.LAVOS_SPAWN,
        LocID.CAVE_OF_MASAMUNE: BossID.MASA_MUNE,
        LocID.GENO_DOME_MAINFRAME: BossID.MOTHER_BRAIN,
        LocID.REPTITE_LAIR_AZALA_ROOM: BossID.NIZBEL,
        LocID.TYRANO_LAIR_NIZBEL: BossID.NIZBEL_2,
        LocID.SUNKEN_DESERT_DEVOURER: BossID.RETINITE,
        LocID.GIANTS_CLAW_TYRANO: BossID.RUST_TYRANO,
        LocID.MAGUS_CASTLE_SLASH: BossID.SLASH_SWORD,
        LocID.SUN_PALACE: BossID.SON_OF_SUN,
        LocID.OZZIES_FORT_SUPER_SLASH: BossID.SUPER_SLASH,
        LocID.BLACK_OMEN_TERRA_MUTANT: BossID.TERRA_MUTANT,
        LocID.OCEAN_PALACE_TWIN_GOLEM: BossID.TWIN_BOSS,
        LocID.MANORIA_COMMAND: BossID.YAKRA,
        LocID.KINGS_TRIAL_NEW: BossID.YAKRA_XIII,
        LocID.ZENAN_BRIDGE_BOSS: BossID.ZOMBOR,
        LocID.FACTORY_RUINS_SECURITY_CENTER: BossID.R_SERIES
    }


# Associate BossID with the Boss data structure.
def get_boss_data_dict(settings: rset.Settings) -> dict[BossID, Boss]:

    if settings.game_mode == rset.GameMode.VANILLA_RANDO:
        NormalType = VRScaleBoss
        SoSType = VRScaleSonOfSon
    else:
        NormalType = ProgressiveScaleBoss
        SoSType = SonOfSunScaleBoss

    return {
        BossID.ATROPOS_XR: NormalType.ATROPOS_XR(),
        BossID.DALTON_PLUS: NormalType.DALTON_PLUS(),
        BossID.DRAGON_TANK: NormalType.DRAGON_TANK(),
        BossID.ELDER_SPAWN: NormalType.ELDER_SPAWN(),
        BossID.FLEA: NormalType.FLEA(),
        BossID.FLEA_PLUS: NormalType.FLEA_PLUS(),
        BossID.GIGA_GAIA: NormalType.GIGA_GAIA(),
        BossID.GIGA_MUTANT: NormalType.GIGA_MUTANT(),
        BossID.GOLEM: NormalType.GOLEM(),
        BossID.GOLEM_BOSS: NormalType.GOLEM_BOSS(),
        BossID.GUARDIAN: NormalType.GUARDIAN(),
        BossID.HECKRAN: NormalType.HECKRAN(),
        BossID.LAVOS_SPAWN: NormalType.LAVOS_SPAWN(),
        BossID.MASA_MUNE: NormalType.MASA_MUNE(),
        BossID.MEGA_MUTANT: NormalType.MEGA_MUTANT(),
        BossID.MOTHER_BRAIN: NormalType.MOTHER_BRAIN(),
        BossID.MUD_IMP: NormalType.MUD_IMP(),
        BossID.NIZBEL: NormalType.NIZBEL(),
        BossID.NIZBEL_2: NormalType.NIZBEL_II(),
        BossID.RETINITE: NormalType.RETINITE(),
        BossID.R_SERIES: NormalType.R_SERIES(),
        BossID.RUST_TYRANO: NormalType.RUST_TYRANO(),
        BossID.SLASH_SWORD: NormalType.SLASH_SWORD(),
        BossID.SON_OF_SUN: SoSType.SON_OF_SUN(),
        BossID.SUPER_SLASH: NormalType.SUPER_SLASH(),
        BossID.TERRA_MUTANT: NormalType.TERRA_MUTANT(),
        BossID.TWIN_BOSS: NormalType.TWIN_BOSS(),
        BossID.YAKRA: NormalType.YAKRA(),
        BossID.YAKRA_XIII: NormalType.YAKRA_XIII(),
        BossID.ZOMBOR: NormalType.ZOMBOR(),
        BossID.MAGUS: NormalType.MAGUS(),
        BossID.BLACK_TYRANO: NormalType.BLACK_TYRANO(),
        BossID.LAVOS_SHELL: Boss.LAVOS_SHELL(),
        BossID.INNER_LAVOS: Boss.INNER_LAVOS(),
        BossID.LAVOS_CORE: Boss.LAVOS_CORE(),
        BossID.MAMMON_M: Boss.MAMMON_MACHINE(),
        BossID.ZEAL: Boss.ZEAL(),
        BossID.ZEAL_2: Boss.ZEAL_2()
    }


def get_hp(level: int):
    # copying Frog as a middle of the road hp
    base_hp = 80
    # hp_growth = bytearray.fromhex('0A 0D 15 0F 30 15 63 0A')
    hp_growth = bytearray.fromhex('0A 0C 15 0E 1D 13 63 14')
    return statcompute.compute_hpmp_growth(hp_growth, level) + base_hp


def get_mdef(level: int):
    # These are Frog's stats (also Crono's)
    BASE_MDEF = 15
    MDEF_GROWTH = 0.46

    return min(BASE_MDEF + (level-1)*MDEF_GROWTH, 100)


def get_phys_def(level: int, max_level):
    BASE_STM = 8
    STM_GROWTH = 1.65

    # In practice, jets has weird armor curve.  You can get about 80% of
    # endgame armor in the early game.
    LV1_ARMOR_DEF = 3 + 5  # hide cap + hide armor
    MID_ARMOR = 45 + 20  # ruby vest + rock helm
    LATE_ARMOR = 75 + 35  # aeon suit + mermaid cap

    # This is calibrated for lv12, lv30 for normal jets cap of 35
    mid_level = round(4*max_level/10)
    late_level = max_level

    pwl = piecewiselinear.PiecewiseLinear(
        (1, LV1_ARMOR_DEF),
        (mid_level, MID_ARMOR),
        (late_level, LATE_ARMOR)
    )

    armor = pwl(level)
    stamina = BASE_STM + STM_GROWTH*(level-1)

    return min(stamina + armor, 256)


def get_eff_phys_hp(level: int, max_level: int = 35):
    hp = get_hp(level)
    defense = get_phys_def(level, max_level)
    def_reduction = defense/256

    return hp/(1-def_reduction)


def get_eff_mag_hp(level: int):
    hp = get_hp(level)
    mdef = get_mdef(level)

    mag_reduction = 10*mdef/1024

    return hp/(1-mag_reduction)


# Scale boss depending on stat progression of players
def progressive_scale_stats(
        enemy_id: EnemyID,
        stats: EnemyStats,
        atk_db: enemytechdb.EnemyAttackDB,
        ai_db: enemyai.EnemyAIDB,
        from_power: int, to_power: int,
        max_power: int = 30,
        scale_hp: bool = True,
        scale_level: bool = True,
        scale_speed: bool = True,
        scale_magic: bool = True,
        scale_mdef: bool = False,
        scale_offense: bool = True,
        scale_defense: bool = False,
        scale_xp: bool = False,
        scale_gp: bool = False,
        scale_tp: bool = False,
        scale_techs: bool = True,
        scale_atk: bool = True) -> EnemyStats:

    new_stats = stats.get_copy()

    off_scale_factor = \
        get_eff_phys_hp(to_power, max_power) / \
        get_eff_phys_hp(from_power, max_power)
    mag_scale_factor = get_eff_mag_hp(to_power)/get_eff_mag_hp(from_power)

    if scale_offense:
        new_offense = stats.offense * off_scale_factor
        set_stats_offense(enemy_id, new_stats, new_offense, atk_db,
                          ai_db, scale_techs, scale_atk)

    if scale_techs:
        scale_enemy_techs(enemy_id, stats,
                          off_scale_factor, mag_scale_factor,
                          atk_db, ai_db)

    if scale_magic:
        new_stats.magic = \
            int(max(1, min(stats.magic*mag_scale_factor, 0xFF)))

    if scale_level:
        new_stats.level = \
            int(max(1, min(stats.level*mag_scale_factor, 0xFF)))

    # Player attack scales superlinearly.  Atk scales roughly linearly with
    # level, but tech power scales too, we need to do something extra.
    # TODO:  Be a little more accurate and model tech power growth.
    def get_hp_scale_factor(
            from_power: float, to_power: float, max_power: float
    ) -> float:

        # This is super contrived.  It just scales from 1 to about 15 with
        # steeper scaling at the higher end.
        def hp_marker(level: float, max_level: float):
            return 1+15*(level/max_level)**1.5

        # print(f'from, marker: {from_power}, {hp_marker(from_power)}')
        # print(f'  to, marker: {to_power}, {hp_marker(to_power)}')
        if from_power*to_power == 0:
            return 0
        return (
            hp_marker(to_power, max_power) /
            hp_marker(from_power, max_power)
        )

    hp_scale_factor = get_hp_scale_factor(from_power, to_power, max_power)
    if scale_hp:
        new_stats.hp = int(min(stats.hp*hp_scale_factor, 0x7FFF))

        if new_stats.hp < 1:
            new_stats.hp = 1

    # Going to add 1 speed for every  power doubling.
    # At present, the biggest swing is 5 to 40 which is 3 doublings for
    # +3 speed.
    if scale_speed:
        if from_power*to_power == 0:
            add_speed = 0
        else:
            add_speed = math.log(to_power/from_power, 2)
            add_speed = round(add_speed)
            # print(f'{enemy_id}: adding {add_speed} speed')

        new_stats.speed = min(new_stats.speed + add_speed, 16)

    # xp to next level is approximately quadratic.  Scale all rewards
    # quadratically.
    def xp_mark(level: float):
        return 5.62*(level**2) + 11.31*level

    if from_power*to_power == 0:
        reward_scale = 0
    else:
        reward_scale = xp_mark(to_power)/xp_mark(from_power)

    orig_stats = (stats.xp, stats.tp, stats.gp)

    # Observed that gp, tp scale roughly with hp.  So for now we're lazy
    # and reusing that scale factor.
    # TODO: Fixed rewards in a given spot.
    scales = (hp_scale_factor, hp_scale_factor, hp_scale_factor)
    is_scaled = (scale_xp, scale_tp, scale_gp)
    reward_max = (0x7FFF, 0xFF, 0x7FFF)

    new_stats.xp, new_stats.tp, new_stats.gp = \
        (int(min(orig_stats[i]*scales[i], reward_max[i]))
         if is_scaled[i] else orig_stats[i]
         for i in range(len(orig_stats)))

    return new_stats


def scale_enemy_techs(enemy_id: EnemyID,
                      orig_stats: EnemyStats,
                      off_scale_factor: float,
                      mag_scale_factor: float,
                      atk_db: enemytechdb.EnemyAttackDB,
                      ai_db: enemyai.EnemyAIDB):

    # Need to copy the list.  Otherwise duplicated techs get readded to
    # the list and scaled twice.
    enemy_techs = list(ai_db.scripts[enemy_id].tech_usage)
    # print(f'Scaling techs for {enemy_id}')
    # print(f'  mag scale: {mag_scale_factor}')
    # print(f'  off scale: {off_scale_factor}')
    # print(f'  used: {enemy_techs}')
    # unused_tech_count = len(ai_db.unused_techs)
    # print(f'num unused_techs: {unused_tech_count}')

    new_offense = orig_stats.offense*off_scale_factor
    effective_new_offense = min(new_offense, 0xFF)

    if orig_stats.offense == 0:
        effective_scale_factor = 1
    else:
        effective_scale_factor = effective_new_offense/orig_stats.offense
    overflow_scale = new_offense/0xFF

    for tech_id in enemy_techs:
        tech = atk_db.get_tech(tech_id)
        effect = tech.effect

        new_power = effect.power
        if effect.damage_formula_id == 4:  # physical damage formulas
            if effect.defense_byte == 0x3E:  # Defended by phys def (normal)
                # print(f'Tech {tech_id:02X} is normal')
                if overflow_scale > 1.05:
                    new_power = round(effect.power*overflow_scale)
            elif effect.defense_byte == 0x3C:  # Defended by mdef (weird)
                # print(f'Tech {tech_id:02X} is weird')
                rescale = mag_scale_factor/effective_scale_factor
                new_power = round(effect.power*rescale)
        elif effect.damage_formula_id == 3 and effect.defense_byte == 0x3E:
            # Magic calculated attack defended by physical defense
            rescale = effective_scale_factor/mag_scale_factor
            new_power = round(effect.power*rescale)

        new_power = min(0xFF, new_power)
        if new_power != effect.power:  # Need to scale
            # print(f'Scaling tech {tech_id:02X} from {effect.power} to '
            #       f'{new_power}')

            tech.effect.power = new_power
            usage = ai_db.tech_to_enemy_usage[tech_id]
            new_id = None
            if len(usage) > 1:
                # print(f'\t{usage}')
                # print('\tNeed to duplicate.')
                if ai_db.unused_techs:
                    new_id = ai_db.unused_techs[-1]
                    # print(f'\tNew ID: {new_id:02X}')
                    ai_db.change_tech_in_ai(enemy_id, tech_id, new_id)
                else:
                    print('Warning: No unused techs remaining.')
            else:
                new_id = tech_id

            if new_id is not None:
                atk_db.set_tech(tech, new_id)
            else:
                print(f'Skipped scaling {tech_id} because no unused techs.')


# Helper method for setting offense and scaling techs if needed.
def set_stats_offense(enemy_id: EnemyID,
                      stats: EnemyStats,
                      new_offense: float,
                      atk_db: enemytechdb.EnemyAttackDB,
                      ai_db: enemyai.EnemyAIDB,
                      scale_techs: bool = True,
                      scale_atk: bool = True):

    if new_offense/0xFF > 1.05:
        remaining_scale = new_offense/0xFF

        # Scale atk 01
        if scale_atk:
            atk_1_id = stats.secondary_attack_id
            atk_1 = atk_db.get_atk(atk_1_id)
            new_power = int(min(atk_1.effect.power * remaining_scale, 0xFF))
            atk_1.effect.power = new_power
            new_atk_id = atk_db.append_attack(atk_1)
            stats.secondary_attack_id = new_atk_id

        stats.offense = 0xFF
    else:
        stats.offense = int(new_offense)


def linear_scale_stats(enemy_id: EnemyID,
                       stats: EnemyStats,
                       atk_db: enemytechdb.EnemyAttackDB,
                       ai_db: enemyai.EnemyAIDB,
                       from_power: int, to_power: int,
                       scale_hp: bool = True,
                       scale_level: bool = True,
                       scale_speed: bool = False,
                       scale_magic: bool = True,
                       scale_mdef: bool = False,
                       scale_offense: bool = True,
                       scale_defense: bool = False,
                       scale_xp: bool = True,
                       scale_gp: bool = True,
                       scale_tp: bool = True) -> EnemyStats:
    try:
        # rewrite x -> kx as x -> x + (k-1)x so that the second term can
        # be conditioned on the scale_stat variables
        scale_factor = to_power/from_power - 1
    except ZeroDivisionError:
        print('Warning: from_power == 0.  Not scaling')
        return stats

    base_stats = [stats.hp, stats.level, stats.speed, stats.magic,
                  stats.mdef, stats.offense, stats.defense, stats.xp,
                  stats.gp, stats.tp]
    is_scaled = [scale_hp, scale_level, scale_speed, scale_magic,
                 scale_mdef, scale_offense, scale_defense, scale_xp,
                 scale_gp, scale_tp]
    max_stats = [0x7FFF, 0xFF, 0x10, 0xFF, 0xFF, 0xFF, 0xFF, 0x7FFF,
                 0x7FFF, 0xFF]

    [hp, level, speed, magic, mdef, offense, defense, xp, gp, tp] = \
        [int(min(base_stats[i] + is_scaled[i]*base_stats[i]*scale_factor,
             max_stats[i]))
         for i in range(len(base_stats))]

    # Mother Brain screens go to 0 with some scalings
    if hp < 1:
        hp = 1

    new_stats = stats.get_copy()
    new_stats.hp = hp
    new_stats.level = level
    new_stats.speed = speed
    new_stats.magic = magic
    new_stats.mdef = mdef
    new_stats.offense = offense
    new_stats.defense = defense
    new_stats.xp = xp
    new_stats.gp = gp
    new_stats.tp = tp

    return new_stats


# New scaling that's supposed to be based on how quickly player stats are
# progressing.
class ProgressiveScaleBoss(Boss):

    MAX_LEVEL = 30

    @classmethod
    def scale_stats(cls,
                    enemy_id: EnemyID,
                    stats: EnemyStats,
                    atk_db: enemytechdb.EnemyAttackDB,
                    ai_db: enemyai.EnemyAIDB,
                    from_power: int, to_power: int) -> EnemyStats:
        return progressive_scale_stats(enemy_id, stats,
                                       atk_db, ai_db,
                                       from_power, to_power, cls.MAX_LEVEL)


class VRScaleBoss(ProgressiveScaleBoss):
    MAX_LEVEL = 50


@dataclass
class _Stats:
    hp: float = 0.0
    level: float = 0.0
    speed: float = 0.0
    magic: float = 0.0
    hit: float = 0.0
    evade: float = 0.0
    mdef: float = 0.0
    offense: float = 0.0
    defense: float = 0.0

    @classmethod
    def from_enemystats(cls, enemy_stats: EnemyStats):
        es = enemy_stats
        return _Stats(
            es.hp, es.level, es.speed, es.magic, es.hit, es.evade,
            es.mdef, es.offense, es.defense
        )

    def __add__(self, other: _Stats):
        return _Stats(
            self.hp+other.hp,
            self.level+other.level,
            self.speed+other.speed,
            self.magic+other.magic,
            self.hit+other.hit,
            self.evade+other.evade,
            self.mdef+other.mdef,
            self.offense+other.offense,
            self.defense+other.defense
        )

    def __radd__(self, other: _Stats):
        return self.__add__(other)


# Incomplete, may never get used.
class CopyStatsScaleBoss(Boss):

    def gather_stats(self,
                     stat_dict: dict[EnemyID, EnemyStats]) -> _Stats:
        '''
        Gather total hp and average of other stats.
        '''
        enemy_ids = self.scheme.ids

        if len(enemy_ids) == 1:
            stats = stat_dict[enemy_ids[0]]
            ret_stats = _Stats.from_enemystats(stats)
        elif EnemyID.LAVOS_SPAWN_HEAD in enemy_ids:
            stats = stat_dict[EnemyID.LAVOS_SPAWN_HEAD]
            ret_stats = _Stats.from_enemystats(stats)
        elif EnemyID.ELDER_SPAWN_HEAD in enemy_ids:
            stats = stat_dict[EnemyID.ELDER_SPAWN_HEAD]
            ret_stats = _Stats.from_enemystats(stats)
        elif EnemyID.SON_OF_SUN_EYE in enemy_ids:
            stats = stat_dict[EnemyID.SON_OF_SUN_EYE]
            ret_stats = _Stats.from_enemystats(stats)
        elif EnemyID.MOTHERBRAIN in enemy_ids:
            stats = stat_dict[EnemyID.MOTHERBRAIN]
            ret_stats = _Stats.from_enemystats(stats)

            display_mag = stat_dict[EnemyID.DISPLAY].magic
            ret_stats.magic += 3*display_mag
            ret_stats.magic /= 4
        elif EnemyID.TERRA_MUTANT_HEAD in enemy_ids:
            stats = stat_dict[EnemyID.TERRA_MUTANT_HEAD]
            ret_stats = _Stats.from_enemystats(stats)

        return ret_stats


# This isn't used anymore, but we'll keep it around
class LinearScaleBoss(Boss):

    @classmethod
    def scale_stats(cls,
                    enemy_id: EnemyID,
                    stats: EnemyStats,
                    atk_db: enemytechdb.EnemyAttackDB,
                    ai_db: enemyai.EnemyAIDB,
                    from_power: int, to_power: int) -> EnemyStats:
        return linear_scale_stats(enemy_id, stats, atk_db, ai_db,
                                  from_power, to_power)


class SonOfSunScaleBoss(Boss):

    MAX_LEVEL = 30

    @classmethod
    def scale_stats(cls,
                    enemy_id: EnemyID,
                    stats: EnemyStats,
                    atk_db: enemytechdb.EnemyAttackDB,
                    ai_db: enemyai.EnemyAIDB,
                    from_power: int, to_power: int) -> EnemyStats:

        # If you scale SoS's flame atk, then it will do more/less damage to
        # the eyeball.  Counterintuitively, you'd want to reduce the flame's
        # atk to make SoS harder.
        return progressive_scale_stats(enemy_id, stats,
                                       atk_db, ai_db,
                                       from_power, to_power,
                                       cls.MAX_LEVEL,
                                       scale_offense=False,
                                       scale_hp=False)


class VRScaleSonOfSon(SonOfSunScaleBoss):
    MAX_LEVEL = 50

    def update_scheme(self, new_power):
        '''
        Remove flames when SoS is lower level.
        '''
        if new_power < 15:
            flames_removed = 2
        elif new_power < 30:
            flames_removed = 1
        else:
            flames_removed = 0

        # There's a bug where removing more than 2 flames will make any hit
        # on a flame count.  No idea why.
        last_ind = len(self.scheme.ids)-flames_removed
        del self.scheme.ids[last_ind:]
        del self.scheme.slots[last_ind:]
        del self.scheme.disps[last_ind:]

    def scale_to_power(
            self, new_power,
            stat_dict: dict[EnemyID, EnemyStats],
            atk_db: enemytechdb.EnemyAttackDB,
            ai_db: enemyai.EnemyAIDB,
    ) -> dict[EnemyID: EnemyStats]:
        self.update_scheme(new_power)

        return SonOfSunScaleBoss.scale_to_power(
            self, new_power, stat_dict, atk_db, ai_db
        )

    def scale_relative_to(
            self, other: Boss,
            stat_dict: dict[EnemyID, EnemyStats],
            atk_db: enemytechdb.EnemyAttackDB,
            ai_db: enemyai.EnemyAIDB
    ) -> dict[EnemyID: EnemyStats]:
        self.update_scheme(other.power)

        return SonOfSunScaleBoss.scale_relative_to(
            self, other, stat_dict, atk_db, ai_db
        )
