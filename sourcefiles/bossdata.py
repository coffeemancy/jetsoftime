from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Tuple, Type, TypeVar

from enemystats import EnemyStats

from ctenums import EnemyID, BossID, LocID


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

    # Make a subclass to implement scaling styles
    # Stats are no longer stored inside of the Boss class, so we provide
    # a dict to look up/set the stats.
    def scale_relative_to(
            self, other: Boss,
            stat_dict: dict[EnemyID, EnemyStats]
    ) -> list[EnemyStats]:
        raise NotImplementedError

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
        return cls.generic_one_spot(EnemyID.ATROPOS_XR, 3, 20)

    @classmethod
    def BLACK_TYRANO(cls: Type[T]) -> T:
        ids = [EnemyID.AZALA, EnemyID.BLACKTYRANO]
        slots = [7, 3]
        disps = [(0, 0), (0, 0)]  # Not real b/c not randomizing
        power = 25

        return cls.generic_multi_spot(ids, disps, slots, power)

    @classmethod
    def DALTON_PLUS(cls: Type[T]) -> T:
        return cls.generic_one_spot(EnemyID.DALTON_PLUS, 3, 30)

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
        power = 40

        return cls.generic_multi_spot(ids, disps, slots, power)

    @classmethod
    def FLEA(cls: Type[T]) -> T:
        return cls.generic_one_spot(EnemyID.FLEA, 7, 15)

    @classmethod
    def FLEA_PLUS(cls: Type[T]) -> T:
        return cls.generic_one_spot(EnemyID.FLEA_PLUS, 7, 20)

    @classmethod
    def GIGA_GAIA(cls: Type[T]) -> T:
        ids = [EnemyID.GIGA_GAIA_HEAD, EnemyID.GIGA_GAIA_LEFT,
               EnemyID.GIGA_GAIA_RIGHT]
        slots = [6, 7, 9]
        # disps = [(0, 0), (0x40, 0x30), (-0x40, 0x30)]
        disps = [(0, 0), (0x20, 0x20), (-0x20, 0x20)]
        power = 25

        return cls.generic_multi_spot(ids, disps, slots, power)

    @classmethod
    def GIGA_MUTANT(cls: Type[T]) -> T:
        ids = [EnemyID.GIGA_MUTANT_HEAD, EnemyID.GIGA_MUTANT_BOTTOM]
        slots = [3, 9]
        disps = [(0, 0), (0, 0)]
        power = 40

        return cls.generic_multi_spot(ids, disps, slots, power)

    @classmethod
    def GOLEM(cls: Type[T]) -> T:
        return cls.generic_one_spot(EnemyID.GOLEM, 3, 20)

    @classmethod
    def GOLEM_BOSS(cls: Type[T]) -> T:
        return cls.generic_one_spot(EnemyID.GOLEM_BOSS, 3, 20)

    # This does virtually nothing since guardian sprite is built into the
    # background.  Eventually replace with lavos versions?
    @classmethod
    def GUARDIAN(cls: Type[T]) -> T:
        ids = [EnemyID.GUARDIAN, EnemyID.GUARDIAN_BIT,
               EnemyID.GUARDIAN_BIT]
        slots = [3, 7, 8]
        # disps = [(0, 0), (-0x50, -0x08), (0x40, -0x08)]
        disps = [(0, 0), (-0x3A, -0x08), (0x40, -0x08)]
        power = 20

        return cls.generic_multi_spot(ids, disps, slots, power)

    @classmethod
    def HECKRAN(cls: Type[T]) -> T:
        return cls.generic_one_spot(EnemyID.HECKRAN, 3, 12)

    # TODO: Check on this.  It should be the displacement is -8 but that
    #       doesn't work...sometimes?  It's weird.
    @classmethod
    def LAVOS_SPAWN(cls: Type[T]) -> T:
        ids = [EnemyID.LAVOS_SPAWN_SHELL,
               EnemyID.LAVOS_SPAWN_HEAD]
        slots = [3, 9]
        disps = [(0, 0), (-0x7, 0)]
        power = 20
        return cls.generic_multi_spot(ids, disps, slots, power)

    @classmethod
    def MASA_MUNE(cls: Type[T]) -> T:
        return cls.generic_one_spot(EnemyID.MASA_MUNE, 6, 15)

    @classmethod
    def MEGA_MUTANT(cls: Type[T]) -> T:
        ids = [EnemyID.MEGA_MUTANT_HEAD,
               EnemyID.MEGA_MUTANT_BOTTOM]
        slots = [3, 7]
        disps = [(0, 0), (0, 0)]
        power = 40

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
        power = 25

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
        return cls.generic_one_spot(EnemyID.NIZBEL, 3, 15)

    @classmethod
    def NIZBEL_II(cls: Type[T]) -> T:
        return cls.generic_one_spot(EnemyID.NIZBEL_II, 3, 18)

    @classmethod
    def RETINITE(cls: Type[T]) -> T:
        ids = [EnemyID.RETINITE_EYE, EnemyID.RETINITE_TOP,
               EnemyID.RETINITE_BOTTOM]
        slots = [3, 9, 6]
        disps = [(0, 0), (0, -0x8), (0, 0x28)]
        power = 15

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
        return cls.generic_one_spot(EnemyID.SLASH_SWORD, 3, 15)

    @classmethod
    def SUPER_SLASH(cls: Type[T]) -> T:
        return cls.generic_one_spot(EnemyID.SUPER_SLASH, 7, 20)

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
        power = 40

        return cls.generic_multi_spot(ids, disps, slots, power)

    @classmethod
    def TWIN_GOLEM(cls: Type[T]) -> T:
        ids = [EnemyID.TWIN_GOLEM, EnemyID.TWIN_GOLEM]
        slots = [3, 6]
        disps = [(0, 0), (0x20, 0)]
        power = 40  # Should match mutant power
        return cls.generic_multi_spot(ids, disps, slots, power)

    @classmethod
    def YAKRA(cls: Type[T]) -> T:
        return cls.generic_one_spot(EnemyID.YAKRA, 3, 5)

    @classmethod
    def YAKRA_XIII(cls: Type[T]) -> T:
        return cls.generic_one_spot(EnemyID.YAKRA_XIII, 3, 15)

    @classmethod
    def ZOMBOR(cls: Type[T]) -> T:
        return cls.generic_multi_spot([EnemyID.ZOMBOR_TOP,
                                       EnemyID.ZOMBOR_BOTTOM],
                                      [(0, 0), (0, 0x20)],
                                      [9, 3],
                                      10)
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
        LocID.OCEAN_PALACE_TWIN_GOLEM: BossID.TWIN_GOLEM,
        LocID.MANORIA_COMMAND: BossID.YAKRA,
        LocID.KINGS_TRIAL_NEW: BossID.YAKRA_XIII,
        LocID.ZENAN_BRIDGE_BOSS: BossID.ZOMBOR,
        LocID.FACTORY_RUINS_SECURITY_CENTER: BossID.R_SERIES
    }


# Associate BossID with the Boss data structure.
def get_boss_data_dict():
    return {
        BossID.ATROPOS_XR: LinearScaleBoss.ATROPOS_XR(),
        BossID.DALTON_PLUS: LinearScaleBoss.DALTON_PLUS(),
        BossID.DRAGON_TANK: LinearScaleBoss.DRAGON_TANK(),
        BossID.ELDER_SPAWN: LinearScaleBoss.ELDER_SPAWN(),
        BossID.FLEA: LinearScaleBoss.FLEA(),
        BossID.FLEA_PLUS: LinearScaleBoss.FLEA_PLUS(),
        BossID.GIGA_GAIA: LinearScaleBoss.GIGA_GAIA(),
        BossID.GIGA_MUTANT: LinearScaleBoss.GIGA_MUTANT(),
        BossID.GOLEM: LinearScaleBoss.GOLEM(),
        BossID.GOLEM_BOSS: LinearScaleBoss.GOLEM_BOSS(),
        BossID.GUARDIAN: LinearScaleBoss.GUARDIAN(),
        BossID.HECKRAN: LinearScaleBoss.HECKRAN(),
        BossID.LAVOS_SPAWN: LinearScaleBoss.LAVOS_SPAWN(),
        BossID.MASA_MUNE: LinearScaleBoss.MASA_MUNE(),
        BossID.MEGA_MUTANT: LinearScaleBoss.MEGA_MUTANT(),
        BossID.MOTHER_BRAIN: LinearScaleBoss.MOTHER_BRAIN(),
        BossID.MUD_IMP: LinearScaleBoss.MUD_IMP(),
        BossID.NIZBEL: LinearScaleBoss.NIZBEL(),
        BossID.NIZBEL_2: LinearScaleBoss.NIZBEL_II(),
        BossID.RETINITE: LinearScaleBoss.RETINITE(),
        BossID.R_SERIES: LinearScaleBoss.R_SERIES(),
        BossID.RUST_TYRANO: LinearScaleBoss.RUST_TYRANO(),
        BossID.SLASH_SWORD: LinearScaleBoss.SLASH_SWORD(),
        BossID.SON_OF_SUN: SonOfSunScaleBoss.SON_OF_SUN(),
        BossID.SUPER_SLASH: LinearScaleBoss.SUPER_SLASH(),
        BossID.TERRA_MUTANT: LinearScaleBoss.TERRA_MUTANT(),
        BossID.TWIN_GOLEM: LinearScaleBoss.TWIN_GOLEM(),
        BossID.YAKRA: LinearScaleBoss.YAKRA(),
        BossID.YAKRA_XIII: LinearScaleBoss.YAKRA_XIII(),
        BossID.ZOMBOR: LinearScaleBoss.ZOMBOR(),
        BossID.MAGUS: LinearScaleBoss.MAGUS(),
        BossID.BLACK_TYRANO: LinearScaleBoss.BLACK_TYRANO()
    }


def linear_scale_stats(stats: EnemyStats,
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
    max_stats = [0xFFFF, 0xFF, 0x10, 0xFF, 0xFF, 0xFF, 0xFF, 0xFFFF,
                 0xFFFF, 0xFF]

    [hp, level, speed, magic, mdef, offense, defense, xp, gp, tp] = \
        [int(min(base_stats[i] + is_scaled[i]*base_stats[i]*scale_factor,
             max_stats[i]))
         for i in range(len(base_stats))]

    # Mother Brain screens go to 0 with some scalings
    if hp < 1:
        hp = 1

    return replace(stats, hp=hp, level=level, speed=speed, magic=magic,
                   mdef=mdef, offense=offense, defense=defense, xp=xp,
                   gp=gp, tp=tp)


class LinearScaleBoss(Boss):

    def scale_relative_to(
            self, other: Boss,
            stat_dict: dict[EnemyID, EnemyStats]
    ) -> list[EnemyStats]:
        # All this really uses is the other boss's power
        # Arguably, the HP will be set based on the other boss_obj

        scaled_stats = [
            linear_scale_stats(stat_dict[part], self.power, other.power)
            for part in self.scheme.ids
        ]

        return scaled_stats


class SonOfSunScaleBoss(Boss):

    # Scale like a linear boss, but then reset the hps to default
    def scale_relative_to(
            self, other: Boss,
            stat_dict: dict[EnemyID, EnemyStats]
    ) -> list[EnemyStats]:

        scaled_stats = [
            # Scaling SoS Flame offense makes the damage from hitting the
            # correct flame change.  So neither hp nor offense are scaled.
            linear_scale_stats(stat_dict[part], self.power, other.power,
                               scale_hp=False, scale_offense=False)
            for part in self.scheme.ids
        ]

        return scaled_stats
