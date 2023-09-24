from __future__ import annotations
import os
import subprocess

from pathlib import Path

import pytest

from conftest import TestData

import randomizer
from ctrom import CTRom


@pytest.fixture(scope='session')
def ctrom() -> Path:
    '''Path to CT ROM based on $CTROM env var.'''
    rompath = os.getenv('CTROM', '')
    assert rompath, 'CTROM env var is not set.'

    ctrom = Path(rompath)
    assert ctrom.exists(), f"CTROM does not exist: {rompath}"

    return ctrom


@pytest.fixture(scope='session')
def rando(ctrom, paths, tmp_path_factory):
    '''Randomizer CLI subprocess fixture.'''
    script = paths['sourcefiles'] / 'randomizer.py'
    outdir = tmp_path_factory.mktemp('output')

    def _sp(args):
        return subprocess.run(
            [script] + ['-i', str(ctrom), '-o', str(outdir), '--spoilers', '--json-spoilers'] + args,
            stdout=subprocess.PIPE,
            cwd=str(paths['sourcefiles']),
        )

    return _sp


@pytest.mark.ctrom
def test_ctrom(ctrom):
    '''Coherence check that CTROM is correct rom.'''
    rom = ctrom.read_bytes()
    assert CTRom.validate_ct_rom_bytes(rom), f"Not a vanilla CT ROM: {ctrom}"


def test_noop():
    assert randomizer


@pytest.mark.ctrom
@pytest.mark.parametrize('preset', TestData.presets, ids=TestData.presets_ids)
def test_randomizer(preset, rando):
    '''Test randomizer creating seeds based on preset.

    NOTE: This currently requires local access to CT ROM, specified
    via environment variable $CTROM. As such, it is skipped on Github
    Actions workflows, which does not specify the --run-ctrom option
    to pytest.
    '''
    sp = rando(f"--preset {preset}".split(' '))
    assert sp.returncode == 0, f"Randomizer issued non-zero exit code: {sp.returncode}"
