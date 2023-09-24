from __future__ import annotations
import json
import pytest

from conftest import TestData

import validators as vld

# TESTS ######################################################################


def test_invalid_presets_coherence():
    assert TestData.invalid_presets, 'Failed to find invalid presets'


@pytest.mark.parametrize('preset', TestData.invalid_presets, ids=TestData.invalid_presets_ids)
def test_invalid_presets_errors(preset):
    preset_data = json.loads(preset.read_text())
    results = vld.PresetValidator.validate_from_data(preset_data)
    assert not results.valid, f"Unexpected valid preset: {preset}"

    # assure that invalid preset has an "tests.expected_errors" mapping in it
    expected_errors = preset_data.get('tests', {}).get('expected_errors', [])
    assert expected_errors, f"Missing expected_errors section in invalid preset: {preset}"

    # check that all errors were expected
    for error in results.errors:
        # find first matching error in expected using key that is validation error type and key
        ve = error.to_dict()
        expected = f"{ve['type']}.{ve['key']}"
        assert expected in expected_errors, f"Missing expected error: {error}"
        expected_errors.remove(expected)

    assert not expected_errors, 'Leftover expected_errors missing from validation results'


@pytest.mark.parametrize('preset', TestData.presets, ids=TestData.presets_ids)
def test_preset_files(preset):
    preset_data = json.loads(preset.read_text())
    results = vld.PresetValidator.validate_from_data(preset_data)
    assert results.valid, f"Validation of preset found errors: {preset}"
