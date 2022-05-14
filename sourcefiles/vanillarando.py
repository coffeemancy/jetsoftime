import bossrandoevent
import ctenums
import ctrom

import randoconfig as cfg
import randosettings as rset


def restore_scripts(ct_rom: ctrom.CTRom):
    script = ctrom.ctevent.Event.from_flux(
        './flux/orig_07E_geno_conveyor.Flux'
    )
    ct_rom.script_manager.set_script(script, ctenums.LocID.GENO_DOME_CONVEYOR)

    script = ctrom.ctevent.Event.from_flux(
        './flux/VR_0E6_RSeries.Flux'
    )
    ct_rom.script_manager.set_script(
        script,
        ctenums.LocID.FACTORY_RUINS_SECURITY_CENTER
    )

def restore_sos(ct_rom: ctrom.CTRom, config: cfg.RandoConfig):
    
    bossrandoevent.set_sun_palace_boss(
        ct_rom,
        config.boss_data_dict[ctenums.BossID.SON_OF_SUN].scheme
    )
    ct_rom.script_manager.write_script_to_rom(ctenums.LocID.SUN_PALACE)
        
    

def fix_item_data(config: cfg.RandoConfig):
    # Fix prices for normally unsellable things
    item_db = config.itemdb

    IID = ctenums.ItemID
    
    for item_id in (IID.BANDANA, IID.RIBBON, IID.POWERGLOVE, IID.DEFENDER,
                    IID.MAGICSCARF,IID.SIGHTSCOPE ):
        item_db[item_id].price = 100

    for item_id in (IID.HIT_RING, IID.BERSERKER, IID.POWERSCARF,
                    IID.MUSCLERING, IID.SERAPHSONG ):
        item_db[item_id].price = 1000

    for item_id in (IID.POWER_RING, IID.MAGIC_RING, IID.SILVERERNG):
        item_db[item_id].price = 5000

    item_db[IID.RAGE_BAND].price = 2000
    item_db[IID.THIRD_EYE].price = 2000
    item_db[IID.WALLET].price = 4000
    item_db[IID.WALL_RING].price = 4000
    item_db[IID.FRENZYBAND].price = 5500
    item_db[IID.PRISMSPECS].price = 62000
    item_db[IID.SUN_SHADES].price = 62000
    item_db[IID.GOLD_STUD].price = 60000
    item_db[IID.AMULET].price = 50000
    item_db[IID.DASH_RING].price = 40000
    item_db[IID.SILVERSTUD].price = 40000
    item_db[IID.GOLD_ERNG].price = 30000
    item_db[IID.CHARM_TOP].price = 20000
    item_db[IID.SPEED_BELT].price = 20000
    item_db[IID.MAGIC_SEAL].price = 20000
    item_db[IID.POWER_SEAL].price = 25000

    # Make things sellable

    #
    
    
    
    
    pass


def get_tyrano_nuke_dict():
    Element = ctenums.Element
    return {
        Element.FIRE: 0x37,  # Original
        Element.ICE: 0x04,
        Element.LIGHTNING: 0x1C,
        Element.NONELEMENTAL: 0x26,
        Element.SHADOW: 0x28
    }


def get_magus_nuke_dict():
    Element = ctenums.Element
    return {
        Element.FIRE: 0xA9,  # Original
        Element.ICE: 0x2D,
        Element.LIGHTNING: 0x3B,
        Element.NONELEMENTAL: 0x8E,  # Original
        Element.SHADOW: 0x6B  # Original
    }


def get_magus_char_nuke_dict():
    Element = ctenums.Element
    CharID = ctenums.CharID

    nuke_dict = get_magus_nuke_dict()
    ret_dict = dict()
    
    for char in list(CharID):
        if char in (CharID.CRONO, CharID.ROBO):
            ret_dict[char] = nuke_dict[Element.LIGHTNING]
        elif char == CharID.LUCCA:
            ret_dict[char] = nuke_dict[Element.FIRE]
        elif char in (CharID.MARLE, CharID.FROG):
            ret_dict[char] = nuke_dict[Element.ICE]
        elif char == CharID.MAGUS:
            ret_dict[char] = nuke_dict[Element.SHADOW]
        else:
            ret_dict[char] = nuke_dict[Element.NONELEMENTAL]

    return ret_dict


def randomize_midbosses(settings: rset.Settings, config: cfg.RandoConfig):
    CharID = ctenums.CharID
    EnemyID = ctenums.EnemyID

    # Magus
    magus_char = random.choice(list(CharID))

    magus_nukes = get_magus_char_nuke_dict()
    new_nuke = magus_nukes[magus_char]
    nuke_strs = {
        CharID.CRONO: 'Luminaire / Crono\'s strongest attack!',
        CharID.MARLE: 'Hexagon Mist /Marle\'s strongest attack!',
        CharID.LUCCA: 'Flare / Lucca\'s strongest attack!',
        CharID.ROBO: 'Luminaire /Robo\'s strongest attack!',
        CharID.FROG: 'Hexagon Mist /Frog\'s strongest attack.',
        CharID.AYLA: 'Energy Flare /Ayla\'s strongest attack!',
        CharID.MAGUS: 'Dark Matter / Magus\' strongest attack!',
    }

    # Vanilla so we know magus has the default Dark Matter 0x6B
    magus_ai = config.enemy_aidb.scripts[EnemyID.MAGUS]
    magus_stats = config.enemy_dict[EnemyID.MAGUS]

    magus_ai.change_tech_usage(0x6B, new_nuke)
    magus_stats.sprite_data.set_sprite_to_pc(magus_char)
    magus_stats.name = str(magus_char)

    battle_msgs = config.enemy_aidb.battle_msgs
    battle_msgs.set_msg_from_str(0x23, nuke_strs[magus_char])

    # Black Tyrano
    

def fix_enemy_techs(config: cfg.RandoConfig):
    # Magus/Tyrano randomization requires making new versions of nukes
    # Need to alter the normal ones and then make copies for other enemies
    # to use.
    Element = ctenums.Element
    enemy_techdb = config.techdb
    enemy_aidb = config.enemy_aidb
    # Tyrano has a power 23 flame breath
    # Will need copies of Luminaire (0xBB), Mist (0x91), Dark Matter (0x6B),
    # and Energy Release (0x8E)
    tyrano_nuke_dict = get_tyrano_nuke_dict()
    new_elems = (Element.ICE, Element.LIGHTNING, Element.NONELEMENTAL,
                 Element.SHADOW)
    base_tech_ids = (0x91, 0xBB, 0x8E, 0x6B)

    tyrano_spell_power = 23
    for pair in zip(new_elems, base_tech_ids):
        elem = pair[0]
        base_id = pair[1]
        new_id = tyrano_nuke_dict[elem]

        tech = enemy_techdb.get_tech(base_id)
        tech.effect.power = 23
        enemy_techdb.set_tech(tech, new_id)
        
    
    # Magus has an 18 power Dark Matter
    # Flare (0xA9 - 20) and Energy Release (0x8E - 18) are good as-is
    # Luminaire (0xBB) and Mist (0x91) need a new copy.
    magus_nuke_dict = get_magus_nuke_dict()
    new_elems = (Element.ICE, Element.LIGHTNING)
    base_tech_ids = (0x91, 0xBB)
    for pair in zip(new_elems, base_tech_ids):
        elem = pair[0]
        base_id = pair[1]
        new_id = tyrano_nuke_dict[elem]

        tech = enemy_techdb.get_tech(base_id)
        tech.effect.power = 18
        enemy_techdb.set_tech(tech, new_id)


def scale_enemy_xp_tp(config: cfg.RandoConfig,
                      xp_scale_factor: float = 4.0,
                      tp_scale_factor: float = 2.0):

    enemy_dict = config.enemy_dict
    for enemy_id in enemy_dict:
        enemy = enemy_dict[enemy_id]
        enemy.xp = round(enemy.xp * xp_scale_factor)
        enemy.tp = round(enemy.tp * tp_scale_factor)


def fix_required_tp(config: cfg.RandoConfig):
    
    CharID = ctenums.CharID

    # Crono, Lucca, Marle, and Frog have no TP for 3rd tech
    for char_id in (CharID.CRONO, CharID.MARLE, CharID.LUCCA, CharID.FROG):
        char = config.char_manager.pcs[char_id]
        char.stats.tp_thresh[2] = 100

    # Robo has no TP for first two techs and 5 TP for Laser Spin
    robo = config.char_manager.pcs[CharID.ROBO]
    robo.stats.tp_thresh[0:3] = [5, 50, 100]

    # Magus has no TP for first three techs
    magus = config.char_manager.pcs[CharID.MAGUS]
    magus.stats.tp_thresh[0:3] = [100, 100, 100]


def fix_magic_learning(config: cfg.RandoConfig):
    CharID = ctenums.CharID
    magic_learners = (CharID.CRONO, CharID.MARLE, CharID.LUCCA, CharID.FROG)
    for char_id in magic_learners:
        for tech_num in range(3):
            tech_id = 1 + char_id*8 + tech_num
            magic_byte = tech_id*0xB
            config.techdb.controls[magic_byte] &= 0x7F
        for tech_num in range(3, 8):
            tech_id = 1 + char_id*8 + tech_num
            magic_byte = tech_id*0xB
            config.techdb.controls[magic_byte] |= 0x80

def restore_son_of_sun_flame(config: cfg.RandoConfig):
    
    EID = ctenums.EnemyID
    sos_scheme = cfg.bossdata.BossScheme(
        [EID.SON_OF_SUN_EYE, EID.SON_OF_SUN_FLAME, EID.SON_OF_SUN_FLAME,
         EID.SON_OF_SUN_FLAME, EID.SON_OF_SUN_FLAME, EID.SON_OF_SUN_FLAME],
        [(0, 0), (0x18, -0x8), (0xC, 0x17), (-0xC, 0x17), (-0x18, -0x8),
         (0, -0x16)],
        [3, 4, 5, 6, 7, 8]
    )

    config.boss_data_dict[ctenums.BossID.SON_OF_SUN].scheme = sos_scheme
    

def fix_config(config: cfg.RandoConfig):
    fix_item_data(config)
    scale_enemy_xp_tp(config)
    fix_required_tp(config)
    fix_magic_learning(config)
    restore_son_of_sun_flame(config)
