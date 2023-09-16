from __future__ import annotations

import json
import subprocess

import pytest

import jotjson
from randosettings import GameFlags as GF


@pytest.fixture
def presetimizer(paths):
    script = paths['sourcefiles'] / 'presetimizer.py'

    def _sp(args):
        return subprocess.run([script] + args, stdout=subprocess.PIPE, cwd=str(paths['sourcefiles']))

    return _sp


@pytest.mark.parametrize(
    'args, expected',
    [
        # make sure certain keys always show up in preset, regardless if explicilty set
        ([], []),
        # gameflags should only be in preset when there is at least one
        ('--mode loc -gzpmq -ef -cr -rc'.split(' '), ['gameflags']),
        # bucket_settings should only be in preset when used
        (
            '-k -obj1=Random -obj2=boss_nogo -obj3=recruit_3'.split(' '),
            ['gameflags', 'bucket_settings'],
        ),
        # char_settings should only be in preset when at least one char choice is made
        (['--crono-choices=not crono'], ['char_settings']),
        # mystery_settings should only be in preset when mystery flag is used
        (['--mystery'], ['gameflags', 'mystery_settings']),
        # tab_settings should only be in preset when a tab option is specified
        (['--max-power-tab=6'], ['tab_settings']),
    ],
    ids=('default', 'gameflags', 'bucket', 'char', 'mystery', 'tab'),
)
def test_presetimizer(args, expected, presetimizer):
    '''Check presetimizer output only includes expected settings.'''
    sp = presetimizer(args)
    assert sp.returncode == 0, f"Presetimizer issued non-zero exit code: {sp.returncode}"

    stdout = sp.stdout.decode('utf-8')
    preset = json.loads(stdout)
    assert preset, 'Empty preset'

    # these should always be included in a preset, regardless if explicitly passed
    always = ['game_mode', 'item_difficulty', 'enemy_difficulty', 'techorder', 'shopprices']
    # make sure expected keys are in settings
    for key in always + expected:
        assert key in preset['settings'], f"Missing expected key in preset: '{key}'"

    # make sure these only show up when explicit
    optional = ['gameflags', 'char_settings', 'bucket_settings', 'mystery_settings', 'tab_settings']
    for key in optional:
        if key not in expected:
            assert key not in preset['settings'], f"Unexpected key in preset: '{key}'"


def test_presetimizer_preset(paths, presetimizer):
    '''Check can pass an input preset to prestimizer, add flags, and load preset into Settings.'''
    preset = paths['presets'] / 'race.preset.json'
    sp = presetimizer(['-i', str(preset), '-cr', '--ayla-choices=ayla'])
    assert sp.returncode == 0, f"Presetimizer issued non-zero exit code: {sp.returncode}"

    stdout = sp.stdout.decode('utf-8')
    preset = json.loads(stdout, cls=jotjson.JOTJSONDecoder)['settings']

    assert preset.char_settings.choices[5] == [5]
    assert GF.CHRONOSANITY in preset.gameflags
