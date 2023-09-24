from __future__ import annotations


def test_preset_files_coherence(presets):
    '''Coherence check that preset files can be found.'''
    assert presets, 'Failed to find any .preset.json files'
