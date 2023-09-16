#!/usr/bin/env python3
'''
Presetimizer: script for convenient creation/validation of .preset.json files.

This script is a tool for building preset files without requiring a CT rom or needing to generate
a seed (like randomizer.py requires). It supports (almost) all of the arguments from randomizer.py which affect
generation of a seed and can go into a preset file. Cosmetic options, which can be set "post-generation"
in the web GUI, are not included in a preset file.

Presets can also be built from other presets (using the '--input-preset' argument), with additional
arguments passed in (similar to using '--preset' in randomizer.py).

Metadata can be passed in as a string in JSON format via the '--metadata' argument.

This script outputs the generated preset directly to stdout. Without errors, it does not output anything else to
stdout, so it's output can be re-directed to a file to create a .preset.json file.
'''
from __future__ import annotations
import argparse
import json
import types

from pathlib import Path
from typing import Any, Dict, Generator, List, Type

import arguments
import jotjson
import randosettings as rset


class PresetimizerOptionsAG(arguments.ArgumentGroup):
    _title = 'Presetimizer Options'

    @classmethod
    def arguments(cls) -> Generator[arguments.Argument, None, None]:
        yield arguments.Argument(
            '--metadata', help='metadata to add to preset (JSON) [{}]', default='{}', type=json.loads
        )
        yield arguments.Argument(
            '--input-preset',
            '-i',
            help='path to preset JSON file from which to load settings',
            default=None,
            type=Path,
        )


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(formatter_class=arguments.SmartFormatter)
    groups: List[Type[arguments.ArgumentGroup]] = [PresetimizerOptionsAG]
    groups.extend(arguments.ALL_GENERATION_AG)
    for ag in groups:
        ag.add_to_parser(parser)
    return parser


def build_preset(args: argparse.Namespace) -> Dict[str, rset.JSONType]:
    '''Build preset based on args.'''

    presettings = {}
    metadata: Dict[str, rset.JSONType] = {}
    if args.input_preset:
        data = json.loads(args.input_preset.read_text())
        presettings = data['settings']
        metadata = data.get('metadata', {})

        # add preset into arguments to let usual preset handling take place
        preset = arguments.GenerationOptionsAG.load_preset(args.input_preset)
        setattr(args, 'preset', preset)

    # override to_jot_json to minimize output for presets
    def _to_jot_json(self: rset.Settings) -> Dict[str, Any]:
        jot: Dict[str, Any] = {
            'game_mode': str(self.game_mode),
            'enemy_difficulty': str(self.enemy_difficulty),
            'item_difficulty': str(self.item_difficulty),
            'techorder': str(self.techorder),
            'shopprices': str(self.shopprices),
        }

        # only add gameflags when there are some
        if self.gameflags:
            jot['gameflags'] = self.gameflags

        # only include these self when args related were explicitly passed or from inherited preset
        # NOTE: no ro_setitngs as no means of setting with CLI/presetimizer at this time
        if 'mystery_settings' in presettings or 'mystery' in vars(args):
            jot['mystery_settings'] = self.mystery_settings
        if 'bucket_settings' in presettings or 'bucket_list' in vars(args):
            jot['bucket_settings'] = self.bucket_settings
        if 'char_settings' in presettings or any(
            f"{name.lower()}_choices" in vars(args) for name in rset.CharNames.default()
        ):
            jot['char_settings'] = {'choices': self.char_settings.choices}
        if 'tab_settings' in presettings or any(arg.arg in args for arg in arguments.TabSettingsAG.arguments()):
            jot['tab_settings'] = self.tab_settings
        return jot

    settings = arguments.args_to_settings(args)
    setattr(settings, 'to_jot_json', types.MethodType(_to_jot_json, settings))

    ret: Dict[str, Any] = {'settings': settings}

    if args.metadata:
        metadata.update(json.loads(args.metadata))
    ret['metadata'] = metadata

    return ret


if __name__ == '__main__':
    parser = get_parser()
    args = parser.parse_args()
    preset = build_preset(args)

    # write to stdout
    print(json.dumps(preset, cls=jotjson.JOTJSONEncoder, indent=2))
