from __future__ import annotations

from ctenums import ItemID, CharID, RecruitID, TreasureID
from treasuredata import TreasureLocTier
import randosettings as rset
import randoconfig as cfg
#
# This file holds various classes/types used by the logic placement code.
#


#
# The Game class is used to keep track of game state
# as the randomizer places key items.  It:
#   - Tracks key items obtained
#   - Tracks characters obtained
#   - Keeps track of user selected flags
#   - Provides logic convenience functions
#
class Game:
    def __init__(self, settings: rset.Settings,
                 config: cfg.RandoConfig):
        self.characters = set()
        self.keyItems = set()
        self.earlyPendant = rset.GameFlags.FAST_PENDANT in settings.gameflags
        self.lockedChars = rset.GameFlags.LOCKED_CHARS in settings.gameflags
        self.lostWorlds = rset.GameMode.LOST_WORLDS == settings.game_mode
        self.charLocations = config.char_assign_dict
        self.legacyofcyrus = \
            rset.GameMode.LEGACY_OF_CYRUS == settings.game_mode

        # In case we need to look something else up
        self.settings = settings

    #
    # Get the number of key items that have been acquired by the player.
    #
    # return: Number of obtained key items
    #

    def getKeyItemCount(self):
        return len(self.keyItems)

    #
    # Set whether or not this seed is using the early pendant flag.
    # This is used to determine when sealed chests and sealed doors become
    # available.
    #
    # param: pflag - boolean, whether or not the early pendant flag is on
    #
    def setEarlyPendant(self, pflag):
        print('Warning: setEarlyPendant() ignored.\n'
              'Class logictypes.Game can not change game settings.'
              'Please supply the correct randosettings.Settings object at '
              'object creation.')
        # self.earlyPendant = pflag

    #
    # Set whether or not this seed is using the Locked Characters flag.
    # This is used to determine when characters become available to unlock
    # further checks.
    #
    # param cflag - boolean, whether or not the locked characters flag is on
    #
    def setLockedCharacters(self, cflag):
        print('Warning: setLockedCharacters() ignored.\n'
              'Class logictypes.Game can not change game settings.'
              'Please supply the correct randosettings.Settings object at '
              'object creation.')
        # self.lockedChars = cflag

    #
    # Set whether or not this seed is using the Lost Worlds flag.
    # This is used to determine time period access in Lost Worlds games.
    #
    # param lFlag - boolean, whether or not the Lost Worlds flag is on
    #
    def setLostWorlds(self, lFlag):
        print('Warning: setLostWorlds() ignored.\n'
              'Class logictypes.Game can not change game settings.'
              'Please supply the correct randosettings.Settings object at '
              'object creation.')
        # self.lostWorlds = lFlag

    #
    # Check if the player has the specified character
    #
    # param: character - Name of a character
    # return: true if the character has been acquired, false if not
    #
    def hasCharacter(self, character):
        return character in self.characters

    #
    # Add a character to the set of characters acquired
    #
    # param: character - The character to add
    #
    def addCharacter(self, character):
        self.characters.add(character)

    #
    # Remove a character from the set of characters acquired
    #
    # param: character: The character to remove
    #
    def removeCharacter(self, character):
        self.characters.discard(character)

    #
    # Check if the player has a given key item.
    #
    # param: item - The key item to check for
    # returns: True if the player has the key item, false if not
    #
    def hasKeyItem(self, item):
        return item in self.keyItems

    #
    # Add a key item to the set of key items acquired
    #
    # param: item - The Key Item to add
    #
    def addKeyItem(self, item):
        self.keyItems.add(item)

    #
    # Remove a key item from the set of key items acquired
    #
    # param: item: The Key Item to remove
    #
    def removeKeyItem(self, item):
        self.keyItems.discard(item)

    #
    # Determine which characters are available based on what key items/time
    # periods are available to the player.
    #
    # Character locations are provided elsewhere by a cfg.RandoConfig object.
    #
    def updateAvailableCharacters(self):
        # charLocations is a dictionary from cfg.RandoConfig whose keys come
        # from ctenums.RecruitID.  The corresponding value gives the held
        # character in a held_char field

        # Empty the set just in case the placement algorithm had to
        # backtrack and a character is no longer available.
        self.characters.clear()

        # The first four characters are always available.
        self.addCharacter(self.charLocations[RecruitID.STARTER_1].held_char)
        self.addCharacter(self.charLocations[RecruitID.STARTER_2].held_char)
        self.addCharacter(self.charLocations[RecruitID.CATHEDRAL].held_char)
        self.addCharacter(self.charLocations[RecruitID.CASTLE].held_char)

        # The remaining three characters are progression gated.
        if self.canAccessFuture():
            self.addCharacter(
                self.charLocations[RecruitID.PROTO_DOME].held_char
            )
        if self.canAccessDactylCharacter():
            self.addCharacter(
                self.charLocations[RecruitID.DACTYL_NEST].held_char
            )
        if self.hasMasamune():
            self.addCharacter(
                self.charLocations[RecruitID.FROGS_BURROW].held_char
            )
    # end updateAvailableCharacters function

    #
    # Logic convenience functions.  These can be used to
    # quickly check if particular eras or locations are
    # logically accessible.
    #
    def canAccessDactylCharacter(self):
        # If character locking is on, dreamstone is required to get the
        # Dactyl Nest character in addition to prehistory access.
        return (self.canAccessPrehistory() and
                ((not self.lockedChars) or
                 self.hasKeyItem(ItemID.DREAMSTONE)))

    def canAccessFuture(self):
        return not self.legacyofcyrus and \
            (self.hasKeyItem(ItemID.PENDANT) or self.lostWorlds)

    def canAccessPrehistory(self):
        return self.hasKeyItem(ItemID.GATE_KEY) or self.lostWorlds

    def canAccessTyranoLair(self):
        return self.canAccessPrehistory() and \
            self.hasKeyItem(ItemID.DREAMSTONE)

    def hasMasamune(self):
        return (self.hasKeyItem(ItemID.BENT_HILT) and
                self.hasKeyItem(ItemID.BENT_SWORD))

    def canAccessMagusCastle(self):
        return (self.hasMasamune() and
                self.hasCharacter(CharID.FROG))

    def canAccessDarkAges(self):
        return (self.lostWorlds or
                self.canAccessPrehistory() or
                self.canAccessFuture())

    def canAccessOceanPalace(self):
        return (self.canAccessDarkAges() and
                self.hasKeyItem(ItemID.RUBY_KNIFE))

    def canAccessBlackOmen(self):
        return (self.canAccessFuture() and
                self.hasKeyItem(ItemID.CLONE) and
                self.hasKeyItem(ItemID.C_TRIGGER))

    def canGetSunstone(self):
        return (self.canAccessFuture() and
                self.canAccessPrehistory() and
                self.hasKeyItem(ItemID.MOON_STONE))

    def canAccessKingsTrial(self):
        return (self.hasCharacter(CharID.MARLE) and
                self.hasKeyItem(ItemID.PRISMSHARD))

    def canAccessMelchiorsRefinements(self):
        return (self.canAccessKingsTrial() and
                self.canGetSunstone())

    def canAccessGiantsClaw(self):
        return self.hasKeyItem(ItemID.TOMAS_POP)

    def canAccessRuins(self):
        return self.hasKeyItem(ItemID.MASAMUNE_2)

    def canAccessSealedChests(self):
        return (self.hasKeyItem(ItemID.PENDANT) and
                (self.earlyPendant or self.canAccessDarkAges()))

    def canAccessBurrowItem(self):
        return self.hasKeyItem(ItemID.HERO_MEDAL)

    def canAccessFionasShrine(self):
        return self.hasCharacter(CharID.ROBO)
    # End Game class

#
# This class represents a location within the game.
# It is the parent class for the different location types
#


class Location:
    def __init__(self, treasure_id: TreasureID):
        self.treasure_id = treasure_id
        self.keyItem = None

    def _jot_json(self):
        return {self.getName(): str(self.getKeyItem())}

    #
    # Get the name of this location.
    #
    # return: The name of this location
    #
    def getName(self):
        return str(self.treasure_id)

    #
    # Set the key item at this location.
    #
    # param: keyItem The key item to be placed at this location
    #
    def setKeyItem(self, keyItem):
        self.keyItem = keyItem

    #
    # Get the key item placed at this location.
    #
    # return: The key item being held in this location
    #
    def getKeyItem(self):
        return self.keyItem

    #
    # Unset the key item from this location.
    #
    def unsetKeyItem(self):
        self.keyItem = None

    #
    # Write the key item set to this location to a RandoConfig object
    #
    # param: config - The randoconfig.RandoConfig object which holds the
    #                 treasure assignment dictionary
    #
    def writeKeyItem(self, config: cfg.RandoConfig):
        config.treasure_assign_dict[self.treasure_id].held_item = self.keyItem

# End Location class


#
# This class represents a normal check in the randomizer.  Since it does not
# have a treasure associated with it, the appropriate loot tier (specified in
# treasurewriter.TreasureLocTier) must be provided in the case that a normal
# treasure is assigned instead of  akey item.
#
class BaselineLocation(Location):
    def __init__(self, treasure_id: TreasureID,
                 lootTier: TreasureLocTier):
        Location.__init__(self, treasure_id)
        self.lootTier = lootTier

    #
    # Get the loot tier associated with this check.
    #
    # return: The loot tier associated with this check
    #
    def getLootTier(self):
        return self.lootTier

    def writeTreasure(self, treasure: ItemID, config: cfg.RandoConfig):
        config.treasure_assign_dict[self.treasure_id].held_item = treasure
# End BaselineLocation class


#
# This class represents a set of linked locations.  The key item will
# be set in both of the locations.  This is used for the blue pyramid
# where there are two chests but the player can only get one.
#

# Decided not to have LinkedLocation inherit from Location.
# Location is a TID with an item assignment, but there are no TIDs to assign
# to the linked locations.
# Just make it implement the same behavior as Location.
#
class LinkedLocation():
    def __init__(self, location1: Location, location2: Location):
        self.location1 = location1
        self.location2 = location2

    def getName(self):
        return (f"Linked: {self.location1.getName()} + "
                f"{self.location2.getName()}")
    #
    # Set the key item for both locations in this linked location.
    #

    def setKeyItem(self, keyItem):
        self.location1.setKeyItem(keyItem)
        self.location2.setKeyItem(keyItem)

    #
    # Get the key item placed at this location.
    #
    # return: The key item being held in this location
    #

    def getKeyItem(self):
        if self.location1.getKeyItem() == self.location2.getKeyItem():
            return self.location1.keyItem
        else:
            raise ValueError('Linked locations do not match.')

    #
    # Unset the key item from this location.
    #
    def unsetKeyItem(self):
        self.location1.unsetKeyItem()
        self.location2.unsetKeyItem()

    #
    # Write the key item to both of the linked locations
    #
    def writeKeyItem(self, config: cfg.RandoConfig):
        self.location1.writeKeyItem(config)
        self.location2.writeKeyItem(config)
# end LinkedLocation class

#
# This class represents a group of locations controlled by
# the same access rule.
#


class LocationGroup:
    #
    # Constructor for a LocationGroup.
    #
    # param: name - The name of this LocationGroup
    # param: weight - The initial weighting factor of this LocationGroup
    # param: accessRule - A function used to determine if this LocationGroup
    #                     is accessible
    # param: weightDecay - Optional function to define weight decay of this
    #                      LocationGroup
    #
    def __init__(self, name, weight, accessRule, weightDecay=None):
        self.name = name
        self.locations = []
        self.weight = weight
        self.accessRule = accessRule
        self.weightDecay = weightDecay
        self.weightStack = []

    #
    # Return whether or not this location group is accessible.
    #
    # param: game - The game object with current game state
    # return: True if this location is accessible, false if not
    #
    def canAccess(self, game):
        return self.accessRule(game)

    #
    # Get the name of this location.
    #
    # return: The name of this location
    #
    def getName(self):
        return self.name

    #
    # Get the weight value being used to select locations from this group.
    #
    # return: Weight value used by this location group
    #
    def getWeight(self):
        return self.weight

    #
    # Set the weight used when selecting locations from this group.
    # The weight cannot be set less than 1.
    #
    # param: weight - Weight value to set
    #
    def setWeight(self, weight):
        if weight < 1:
            weight = 1
        self.weight = weight

    #
    # This function is used to decay the weight value of this
    # LocationGroup when a location is chosen from it.
    #
    def decayWeight(self):
        self.weightStack.append(self.weight)
        if self.weightDecay is None:
            # If no weight decay function was given, reduce the weight of this
            # LocationGroup to 1 to make it unlikely to get any other items.
            self.setWeight(1)
        else:
            self.setWeight(self.weightDecay(self.weight))

    #
    # Undo a previous weight decay of this LocationGroup.
    # The previous weight values are stored in the weightStack.
    #
    def undoWeightDecay(self):
        if len(self.weightStack) > 0:
            self.setWeight(self.weightStack.pop())

    #
    # Get the number of available locations in this group.
    #
    # return: The number of locations in this group
    #
    def getAvailableLocationCount(self):
        return len(self.locations)

    #
    # Add a location to this location group. If the location is
    # already part of this location group then nothing happens.
    #
    # param: location - A location object to add to this location group
    #
    def addLocation(self, location):
        if location not in self.locations:
            self.locations.append(location)
        return self

    #
    # Remove a location from this group.
    #
    # param: location - Location to remove from this group
    #
    def removeLocation(self, location):
        self.locations.remove(location)

    #
    # Get a list of all locations that are part of this location group.
    #
    # return: List of locations associated with this location group
    #
    def getLocations(self):
        return self.locations.copy()
# End LocationGroup class
