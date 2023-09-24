from __future__ import annotations
from enum import Flag, IntEnum
from typing import Callable, Dict, List, Union, Mapping, Optional, Sequence, Type, TypeVar


# TYPE DEFINITIONS ###########################################################

JSONPrimitive = Optional[Union[int, float, bool, str]]
JSONType = Union[JSONPrimitive, Mapping[str, "JSONType"], Sequence["JSONType"]]
SIE = TypeVar('SIE', bound='StrIntEnum')


# CLASSES ####################################################################


class SerializableFlag(Flag):
    def __add__(self, other: Flag):
        return self | other

    def __sub__(self, other: Flag):
        return self & ~other

    @classmethod
    def get(cls, key: str):
        return cls[key.partition('.')[-1].upper()]

    def to_jot_json(self) -> List[str]:
        return [str(flag) for flag in type(self) if flag in self]


class StrIntEnum(IntEnum):
    def __str__(self) -> str:
        return self.__repr__().split('.')[1].split(':')[0].lower().title().replace('_', ' ')

    @classmethod
    def default(cls):
        raise NotImplementedError(f"No .default implemented for {cls}")

    @classmethod
    def get(cls, key: str):
        '''Lookup enum value from string key.

        The key string is used to lookup enum value, by converting it to fully
        uppercase and replacing all spaces and hyphens with underscores.

        Essentially, this means that lookup of enum values via key can be
        case insensitive as well as allowing spaces, hyphens, or underscores
        to separate words.
        '''
        try:
            return cls[key.upper().replace(' ', '_').replace('-', '_')]
        except KeyError as ex:
            key = str(ex).strip("'")
            raise KeyError(f"Invalid {cls.__name__}: {key}")

    @classmethod
    def str_dict(cls: Type[SIE]) -> Dict[SIE, str]:
        return {x: str(x) for x in list(cls)}

    @classmethod
    def inv_str_dict(cls: Type[SIE], formatter: Callable[[str], str] = lambda x: x) -> Dict[str, SIE]:
        return {formatter(str(x)): x for x in list(cls)}
