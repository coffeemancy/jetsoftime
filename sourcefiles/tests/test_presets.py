from __future__ import annotations
import json

from pathlib import Path
from typing import Dict

import jsonschema
import pytest

from conftest import TestData


ValidatorImpl = jsonschema.validators.Draft202012Validator

# FIXTURES ###################################################################


@pytest.fixture(scope='session')
def schemas(paths) -> Dict[str, Path]:
    '''All schema names mapped to schema files.'''
    return {str(path.parts[-1]): path for path in paths['schemas'].rglob('*.json')}


@pytest.fixture(scope='session')
def validator(schemas) -> jsonschema.validators.Validator:
    preset_schema = schemas['preset.json']
    schema_data = json.loads(preset_schema.read_text())
    return ValidatorImpl(schema_data)


# TESTS ######################################################################


def test_preset_files_coherence(presets):
    '''Coherence check that preset files can be found.'''
    assert presets, 'Failed to find any .preset.json files'


@pytest.mark.parametrize('preset', TestData.presets, ids=TestData.presets_ids)
def test_preset_files_jsonschema(preset, validator):
    preset_data = json.loads(preset.read_text())
    errors = list(validator.iter_errors(preset_data))
    assert not errors, f"Schema errors found validating {preset}"


def test_schema_files_coherence(schemas):
    '''Coherence check that schema files can be found.'''
    assert schemas, 'Failed to find any schema .json files'


def test_schema_files_jsonschema(schemas):
    '''Check all schema files can be validated by jsonschema.'''
    for schema_name, schema in schemas.items():
        schema_data = json.loads(schema.read_text())
        assert ValidatorImpl.check_schema(schema_data) is None, f"Failed validating schema: {schema_name}"
