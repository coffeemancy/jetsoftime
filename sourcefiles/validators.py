'''
Validators: An interface for validating Settings from files or other data.

The intention of Validators is to provide an externally-useable interface for running
checks against files or data used to build settings objects which drive seed generation, to
identify potential errors and give the user useful hints/tips on how to address them,
before attempting to build a seed which is expected to fail (preventing randomization code
from erroring out).

This is used to:
    * Validate preset files passed to the randomizer CLI
    * Validate preset files created by presetimizer
    * Validate API requests containing preset JSON data in the web API/UI (ctjot_web_generator repo)
    * Validate preset files that live in this repo (via pytest)

The validation process invovles building a Validator object (typically PresetValidator) from 
file or JSON-decoded data, and then running validations and iterating over the ValidationResults,
which provides a list of ValidationError (VE) subtypes. The VE subtype indicates the class of error,
and a key indicates a more specific error (which can be used by an error handler, e.g. in the web UI,
to provide context to the user).

Example:

    decoded_data = json.loads(preset_data)
    results = PresetValidator.validate_from_data(decoded_data)
    for error in results:
        handle_error(error)
'''
from __future__ import annotations

import json

from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Protocol

import jsonschema

import jotjson
import objectivehints as obhint
import randosettings as rset

# VALIDATION ERRORS ##########################################################


@dataclass
class ValidationError(Exception):
    '''Exception for indicating a validation error with useful information and context.

    :param key: short lowercase+underscores string used to differentiate errors of this subtype
    :param message: string indicating details about this error (intended to deliver directly to UI)
    :param context: optional mapping of extra useful info for debugging (not intended to typically go to UI)
    '''

    key: str = 'validation_error'
    message: str = 'Validation error'
    context: Dict[str, rset.JSONType] = field(default_factory=dict)

    @classmethod
    def from_exc(cls, ex: Exception, key: Optional[str] = None, message: Optional[str] = None, **kwargs):
        '''Create validation error from exception.

        :param ex: exception from which to build validation error (added to VE context)
        :param key: optional VE key override (default: VE class key)
        :param message: optional VE message (default: stringified exception passed)
        :param **kwargs: any other data to add to VE context
        :return: validation error with exception and kwargs in context
        :rtype: ValidationError subtype from this class
        '''
        return cls(key or cls.key, context={'ex': str(ex), **kwargs}, message=message or str(ex))

    def to_dict(self) -> Dict[str, rset.JSONType]:
        '''Convert to simple dict to allow for easy JSON parseabilty.'''
        results = {field.name: getattr(self, field.name) for field in fields(self)}
        results['type'] = str(self.__class__.__name__)
        return results

    def __repr__(self) -> str:
        return str(self.to_dict())


class BucketSettingsVE(ValidationError):
    key = 'bucket_settings_error'


class ROSettingsVE(ValidationError):
    key = 'ro_settings_error'


class SchemaVE(ValidationError):
    key = 'json_schema_error'


class SettingsVE(ValidationError):
    key = 'settings_error'


@dataclass
class ValidationResults:
    '''JSON-friendly container for validation errors and results.'''

    errors: List[ValidationError]

    @property
    def valid(self) -> bool:
        '''Indicates that no errors where found when validation was processed.

        This can be overridden on class basis, but by default, if no errors, then it's valid.
        '''
        return not self.errors

    def to_dict(self) -> Dict[str, rset.JSONType]:
        '''Convert to simple dict to allow for easy JSON parseabilty.'''
        return {'valid': self.valid, 'errors': [error.to_dict() for error in self.errors]}

    def report(self, delim: str = '\n', verbose: bool = False) -> str:
        '''Prettifier of results into string.'''
        fmt = "type: {cls}\nkey: {key}\nmessage: {message}"
        if verbose:
            fmt += "\ncontext: {context}"
        return delim.join([fmt.format(cls=ve.__class__.__name__, **ve.to_dict()) for ve in self.errors])

    def __repr__(self) -> str:
        return f"ValidationResults[{self.to_dict()}]"


# VALIDATORS #################################################################


class Validator(Protocol):
    '''Protocol for finding errors and producing validation results from objects or JSON data.'''

    @staticmethod
    def find_errors(Any) -> Generator[ValidationError, None, None]:
        '''Yield all errors found validating object.'''
        raise NotImplementedError('Missing required .find_errors')

    @classmethod
    def find_errors_from_data(cls, data: Dict[str, rset.JSONType]) -> Generator[ValidationError, None, None]:
        '''Yield all errors found validating JSON data loaded into object.'''
        raise NotImplementedError('Missing required .find_errors_from_data')

    @staticmethod
    def json_reload(obj: Any) -> rset.JSONType:
        '''Dump and re-load JSON for JS-usable representation for handleValidationErrors in web UI.'''
        try:
            return json.loads(json.dumps(obj, cls=jotjson.JOTJSONEncoder))
        except Exception as ex:
            raise ValidationError.from_exc(ex, 'json_encode_error', f"Failed to encode to JSON: {ex}")

    @classmethod
    def validate(cls, obj: Any) -> ValidationResults:
        '''Produce validation results from all errors found validating object.'''
        return ValidationResults(list(cls.find_errors(obj)))

    @classmethod
    def validate_from_data(cls, data: Dict[str, rset.JSONType]) -> ValidationResults:
        '''Produce validation results from all errors found validating JSON data loaded into object.'''
        return ValidationResults(list(cls.find_errors_from_data(data)))


class BucketSettingsValidator(Validator):
    '''Validator for randosettings.BucketSettings objects for Bucket List settings.'''

    @staticmethod
    def find_errors(bset: rset.BucketSettings) -> Generator[BucketSettingsVE, None, None]:
        '''Find all validation errors in bucket settings.'''
        # check that bucket settings could be encoded back into JSON, mostly for adding context to results
        try:
            bset_js = Validator.json_reload(bset)
        except ValidationError as ex:
            yield BucketSettingsVE.from_exc(ex, ex.key, ex.message)
            return

        if bset.num_objectives_needed > bset.num_objectives:
            yield BucketSettingsVE(
                'too_many_needed',
                f"{bset.num_objectives_needed} objectives needed > {bset.num_objectives} objectives",
                context={'bucket_settings': bset_js},
            )

        # check that each hint is valid
        for index, hint in enumerate(bset.hints):
            valid, message = obhint.is_hint_valid(hint)
            if not valid:
                yield BucketSettingsVE(
                    'invalid_hint',
                    message or 'Invalid hint',
                    context={'bucket_settings': bset_js, 'hint': hint, 'index': index},
                )


class ROSettingsValidator(Validator):
    '''Validator for randosettings.ROSettings objects for Boss Rando settings.'''

    @staticmethod
    def find_errors(roset: rset.ROSettings) -> Generator[ROSettingsVE, None, None]:
        '''Find all validation errors in boss rando settings.'''
        if False:
            yield ROSettingsVE()
        return


class SettingsValidator(Validator):
    '''Validator for randosettings.Settings objects.'''

    @staticmethod
    def find_errors(settings: rset.Settings) -> Generator[ValidationError, None, None]:
        '''Find all validation errors in settings.'''
        try:
            settings.fix_flag_conflicts()
        except Exception as ex:
            yield SettingsVE.from_exc(ex, 'fix_flag_conflicts')

        for ro_error in ROSettingsValidator.find_errors(settings.ro_settings):
            yield ro_error

        for bs_error in BucketSettingsValidator.find_errors(settings.bucket_settings):
            yield bs_error

    @classmethod
    def find_errors_from_data(cls, data: Dict[str, Any]) -> Generator[ValidationError, None, None]:
        '''Find all errors in settings data building a Settings object.'''
        # first check if data can be encoded into Settings object
        try:
            settings = rset.Settings.from_jot_json(data)
        except Exception as ex:
            yield SettingsVE.from_exc(
                ex,
                'json_encode_error',
                f"Failed to encode into Settings: {ex}",
                data=data,
            )
            return

        # if data can be encoded into Settings object, run further validations
        for ve in cls.find_errors(settings):
            yield ve


class PresetValidator(Validator):
    '''Validator for .preset.json files.

    The first validations that happen for preset data are running jsonschema validation. This checks for
    a lot of types of errors (wrong data types, missing or erroneous keys, regex checking, min/max values, etc.).
    All errors found during jsonschema validation are included in the results.

    If jsonschema validation succeeds, further validations are run which can do more extensive checking which
    is beyond the scope of jsonschema (relationships between data, making sure values map to known settings
    objects/flags when decoded), e.g. objective hints are valid, flags can be fixed by fix_flag_conflicts, etc.
    '''

    _jsonschema: Path = Path(__file__).parent / 'schemas/preset.json'

    @classmethod
    def find_errors_from_data(cls, data: Dict[str, Any]) -> Generator[ValidationError, None, None]:
        '''Find all errors in preset data.'''
        # perform JSON schema validation on data
        jsv = cls._get_schema_validator()
        schema_errors = list(jsv.iter_errors(data))
        for error in schema_errors:
            key = error.json_path.partition('$.')[-1] or 'schema_error'
            yield SchemaVE(key, error.message, context={'error': str(error)})

        # no schema errors, go on to processing settings errors
        if not schema_errors:
            for ve in SettingsValidator.find_errors_from_data(data['settings']):
                yield ve

    @classmethod
    def _get_schema_validator(cls) -> jsonschema.validators.Validator:
        '''Get JSON Schema validator.'''
        schema_data = json.loads(cls._jsonschema.read_text())
        return jsonschema.validators.Draft202012Validator(schema_data)
