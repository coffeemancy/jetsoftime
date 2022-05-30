from __future__ import annotations
import random
import typing

import logicfactory
import logictypes

import ctenums
import randoconfig as cfg
import randosettings as rset

_LocType = typing.Union[logictypes.Location, logictypes.LinkedLocation]


class LogicIterationException(Exception):
    pass


class ImpossibleConfigurationException(Exception):
    pass


class KeyItemFiller(typing.Protocol):

    def get_key_item_locations(
            self,
            game_config: logicfactory.GameConfig
    ) -> list[_LocType]:
        '''
        Return a key item assignment for the given GameConfig
        '''
        pass


class RandomRejectionFiller:
    '''
    Assign KIs randomly and reject configurations that are not 100%able.
    '''

    def __init__(self, max_attempts: int = 5000):
        self.max_attempts = max_attempts

    def fill_key_item_locations(
            self,
            game_config: logicfactory.GameConfig
    ) -> list[_LocType]:
        '''
        Randomly fill in the key items until a valid configuration is reached.
        '''
        key_items_list = list(set(game_config.keyItemList))
        max_game = logictypes.Game(game_config.settings,
                                   game_config.config)
        max_game.keyItems = list(key_items_list)

        num_attempts = 0

        while True:
            available_locations = get_available_locations(game_config,
                                                          max_game, [])

            if len(available_locations) < len(key_items_list):
                raise ImpossibleConfigurationException(
                    'More key items than locations'
                )

            random.shuffle(available_locations)
            for ind, loc in enumerate(available_locations):
                loc.setKeyItem(key_items_list[ind])

            if is_placement_valid(game_config):
                return available_locations[0: len(key_items_list)]

            # Reset everything
            for loc in available_locations[0: len(key_items_list)]:
                loc.unsetKeyItem()

            num_attempts += 1
            if num_attempts >= self.max_attempts:
                raise LogicIterationException('Maximum Attempts Reached.')


class ALTTPRFiller:
    '''
    Mimic ALTTPR's AssumedFiller.
    '''
    def __init__(self, max_attempts: int = 1000):
        self.max_attempts = max_attempts

    def fill_key_item_locations(
            self,
            game_config: logicfactory.GameConfig
    ) -> list[_LocType]:
        '''
        Get key item locations using ALTTPR's AssumedFiller's algorithm.
        '''
        settings = game_config.settings
        config = game_config.config
        char_dict = {
            char: config.char_assign_dict[char].held_char
            for char in config.char_assign_dict
        }

        key_items_list = set(list(game_config.keyItemList))
        unassigned_key_items = list(key_items_list)
        assigned_locations: list[_LocType] = []

        failure_count = 0

        while True:

            if not unassigned_key_items:
                break

            random.shuffle(unassigned_key_items)
            next_item = unassigned_key_items.pop()

            collectable_key_items = get_collectable_key_items(game_config)
            assumed_key_items = unassigned_key_items + collectable_key_items

            max_game = logictypes.Game(settings, config)
            max_game.keyItems = assumed_key_items
            max_game.updateAvailableCharacters()

            avail_locs = get_available_locations(
                game_config, max_game, assigned_locations
            )

            if not avail_locs:
                failure_count += 1
                if failure_count > self.max_attempts:
                    raise LogicIterationException('Exceeded Maximum Failures')

                # Reset everything
                # A smarter system would only reset the previous placement.
                for loc in assigned_locations:
                    loc.unsetKeyItem()

                unassigned_key_items = list(key_items_list)
                assigned_locations = []
            else:
                loc = random.choice(avail_locs)
                assigned_locations.append(loc)
                loc.setKeyItem(next_item)

                # print(f'Assigned {next_item} to {loc.getName()} ')

        return assigned_locations


class ChronosanityFiller:
    '''
    Filler for Anguirel's original Chronosanity algorithm.
    '''
    def __init__(self):
        self.locationGroups = []

    
    #
    # Get a list of LocationGroups that are available for key item placement.
    #
    # param: game - Game object used to determine location access
    #
    # return: List of all available LocationGroups
    #
    def getAvailableLocations(
            self,
            game: logictypes.Game
    ) -> list[logicfactory.LocationGroup]:
        game.updateAvailableCharacters()

        # Get a list of all accessible location groups
        accessibleLocationGroups = []
        for locationGroup in self.locationGroups:
            if locationGroup.canAccess(game):
                if locationGroup.getAvailableLocationCount() > 0:
                    accessibleLocationGroups.append(locationGroup)

        return accessibleLocationGroups

    #
    # Given a weighted list of key items, get a shuffled
    # version of the list with only a single copy of each item.
    #
    # param: weightedList - Weighted key item list
    #
    # return: Shuffled list of key items with duplicates removed
    #
    @classmethod
    def getShuffledKeyItemList(cls, weightedList):
        tempList = weightedList.copy()

        # In the shuffle, higher weighted items have a better chance of
        # appearing before lower weighted items.
        random.shuffle(tempList)

        keyItemList = []
        for keyItem in tempList:
            if not (keyItem in keyItemList):
                keyItemList.append(keyItem)

        return keyItemList
    # end getShuffledKeyItemList

    #
    # Given a list of LocationGroups, get a random location.
    #
    # param: groups - List of LocationGroups
    #
    # return: The LocationGroup the Location was chosen from
    # return: A Location randomly chosen from the groups list
    #
    @classmethod
    def getRandomLocation(
            cls,
            groups: list[logicfactory.LocationGroup]):
        # get the max rand value from the combined weightings of the location
        # groups. This will be used to help select a location group
        weightTotal = 0
        for group in groups:
            weightTotal = weightTotal + group.getWeight()

        # Select a location group
        locationChoice = random.randint(1, weightTotal)
        counter = 0
        chosenGroup = None
        for group in groups:
            counter = counter + group.getWeight()
            if counter >= locationChoice:
                chosenGroup = group
                break

        # Select a random location from the chosen location group.
        location = random.choice(chosenGroup.getLocations())
        return chosenGroup, location

    # end getRandomLocation

    #
    # Randomly place key items.
    #
    # param: gameConfig A GameConfig object with the configuration information
    #                   necessary to place keys for the selected game type
    #
    # return: A list of locations with key items assigned.
    #
    # Raises ImpossibleConfigurationException if not successful.
    def fill_key_item_locations(self, gameConfig: logicfactory.GameConfig):
        self.locationGroups = gameConfig.getLocations()
        remainingKeyItems = gameConfig.getKeyItemList()
        chosenLocations = []
        success, key_item_locations = self.determineKeyItemPlacement_impl(
            chosenLocations, remainingKeyItems, gameConfig
        )

        if not success:
            # ChronosanityFiller will find a valid assignment if there is one.
            raise ImpossibleConfigurationException

        return key_item_locations

    #
    # NOTE: Do not call this function directly. This will be called
    #       by determineKeyItemPlacement after setting up the parameters
    #       needed by this function.
    #
    # This function will recursively determine key item locations
    # such that a seed can be 100% completed.  This uses a weighted random
    # approach to placement and will only consider logically accessible
    # locations.
    #
    # The algorithm for determining locations - For each recursion:
    #   If there are no key items remaining, unwind the recursion, otherwise
    #     Get a list of logically accessible locations
    #     Choose a location randomly (locations are weighted)
    #     Get a shuffled list of the remaining key items
    #     Loop through the key item list, trying each one in the chosen
    #     location
    #       Recurse and try the next location/key item
    #     
    #
    # param: chosenLocations - List of locations already chosen for key items
    # param: remainingKeyItems - List of key items remaining to be placed
    # param: gameConfig - GameConfig object used to determine logic.
    #                     In particular this contains a Game object which
    #                     determines the logic while the GameConfig itself
    #                     has rules for how the keyItem items may change over
    #                     time.
    # TODO:  Should this passtwo parameters? Game and updateKeyItems function?
    #        It's weird using the Game member of GameConfig.
    #
    # return: A tuple containing:
    #             A Boolean indicating whether or not key item placement was
    #             successful
    #
    #             A list of locations with key items assigned
    def determineKeyItemPlacement_impl(
            self,
            chosenLocations: list[_LocType],
            remainingKeyItems: list[ctenums.ItemID],
            gameConfig: logicfactory.GameConfig
    ) -> typing.Tuple[bool, list[_LocType]]:
        if len(remainingKeyItems) == 0:
            # We've placed all key items.  This is our breakout condition
            return True, chosenLocations
        else:
            # We still have key items to place.
            availableLocations = self.getAvailableLocations(
                gameConfig.getGame()
            )
            if len(availableLocations) == 0:
                # This item configuration is not completable.
                return False, chosenLocations
            else:
                # Continue placing key items.
                keyItemConfirmed = False
                returnedChosenLocations = None

                # Choose a random location
                locationGroup, location = \
                    self.getRandomLocation(availableLocations)
                locationGroup.removeLocation(location)
                locationGroup.decayWeight()
                chosenLocations.append(location)

                # Sometimes key item bias is removed after N checks
                gameConfig.updateKeyItems(remainingKeyItems)

                # Use the weighted key item list to get a list of key items
                # that we can loop through and attempt to place.
                localKeyItemList = \
                    self.getShuffledKeyItemList(remainingKeyItems)
                for keyItem in localKeyItemList:
                    # Try placing this key item and then recurse
                    location.setKeyItem(keyItem)
                    gameConfig.getGame().addKeyItem(keyItem)

                    newKeyItemList = [x for x in remainingKeyItems
                                      if x != keyItem]
                    # recurse and try to place the next key item.
                    keyItemConfirmed, returnedChosenLocations = \
                        self.determineKeyItemPlacement_impl(chosenLocations,
                                                            newKeyItemList,
                                                            gameConfig)

                    if keyItemConfirmed:
                        # We're unwinding the recursion here,
                        # all key items are placed.
                        return keyItemConfirmed, returnedChosenLocations
                    else:
                        gameConfig.getGame().removeKeyItem(keyItem)
                # end keyItem loop

                # If we get here, we failed to place an item.
                # Undo location modifications
                locationGroup.addLocation(location)
                locationGroup.undoWeightDecay()
                chosenLocations.remove(location)
                location.unsetKeyItem()

                return False, chosenLocations

# end determineKeyItemPlacement_impl recursive function


# These maybe should be methods of logicfactory.GameConfig?
def is_placement_valid(
        game_config: logicfactory.GameConfig
) -> bool:
    '''
    Determines whether all key items are reachable in a GameConfig.
    '''
    key_items_list = list(set(game_config.getKeyItemList()))
    accessible_keys = get_collectable_key_items(game_config)

    inaccessible_keys = [x for x in key_items_list
                         if x not in accessible_keys]

    return not inaccessible_keys


def get_available_locations(
        game_config: logicfactory.GameConfig,
        game: logictypes.Game,
        assigned_locs: list[_LocType]
) -> list[_LocType]:
    '''
    Find reachable locations that have not already been assigned key items.
    '''

    locations = []
    game.updateAvailableCharacters()
    for group in game_config.locationGroups:
        if group.accessRule(game):
            locations.extend(
                [loc for loc in group.locations if loc not in assigned_locs]
            )

    return locations


def get_collectable_key_items(
        game_config: logicfactory.GameConfig
) -> typing.Iterable[ctenums.ItemID]:
    '''
    Traverse the game config to determine what can be collected.
    '''

    settings = game_config.settings
    config = game_config.config

    cur_game = logictypes.Game(settings, config)
    cur_game.keyItems = []
    cur_game.updateAvailableCharacters()

    key_items = set(list(game_config.getKeyItemList()))

    groups = list(game_config.locationGroups)
    while True:
        new_keys = []
        exhausted_groups = []
        for group in groups:
            if group.accessRule(cur_game):
                for location in group.locations:
                    item = location.getKeyItem()
                    if item in key_items:
                        new_keys.append(item)
                exhausted_groups.append(group)

        for group in exhausted_groups:
            groups.remove(group)

        if new_keys:
            cur_game.keyItems.extend(new_keys)
            cur_game.updateAvailableCharacters()
        else:
            break

    return cur_game.keyItems


def getFiller(settings: rset.Settings) -> KeyItemFiller:
    if rset.GameFlags.CHRONOSANITY in settings.gameflags:
        filler = ChronosanityFiller()
    else:
        filler = RandomRejectionFiller(max_attempts=5000)

    return filler


def commitKeyItems(settings: rset.Settings,
                   config: cfg.RandoConfig):
    '''Add Key Items to the config.'''
    gameConfig = logicfactory.getGameConfig(settings, config)
    filler = getFiller(settings)

    try:
        chosenLocations = filler.fill_key_item_locations(gameConfig)
    except LogicIterationException:
        # Chronosanity is guaranteed to return a valid assignment in the
        # exceedingly rare case that another filler fails.
        print(f'{filler.__class__.__name__} failed. '
              'Falling back to ChronosanityFiller.')
        filler = ChronosanityFiller()
        chosenLocations = filler.fill_key_item_locations(gameConfig)

    for location in chosenLocations:
        location.writeKeyItem(config)

    additional_locs = []

    for locationGroup in gameConfig.locationGroups:
        for location in locationGroup.getLocations():
            if type(location) == logictypes.BaselineLocation and \
               (location not in chosenLocations):

                # This is a baseline location without a key item.
                # Assign a piece of treasure if it has none.
                if location.getKeyItem() in (None,
                                             ctenums.ItemID.NONE,
                                             ctenums.ItemID.MOP):
                    location.writeRandomItem(config)

                # Always list the BaselineLocations for spoiler purposes
                additional_locs.append(location)

    config.key_item_locations = chosenLocations + additional_locs
