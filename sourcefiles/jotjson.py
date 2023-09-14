from __future__ import annotations
import json

from typing import Any, Dict, Union

import randosettings as rset

DecodedJOTJSON = Dict[str, Union[rset.Settings, rset.JSONType]]

class JOTJSONEncoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        kwargs['indent'] = 2
        json.JSONEncoder.__init__(self, *args, **kwargs)

    def default(self, obj) -> rset.JSONType:
        if hasattr(obj, 'to_jot_json'):
            return obj.to_jot_json()
        return json.JSONEncoder.default(self, obj)


class JOTJSONDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj: Dict[str, Any]) -> DecodedJOTJSON:
        # for now, strip out configuration, as not needed for presets
        # in future, if needed, can add decoding for it
        if 'configuration' in obj:
            obj.pop('configuration')
        if 'settings' in obj:
            settings = rset.Settings.from_jot_json(obj['settings'])
            obj['settings'] = settings
        return obj
