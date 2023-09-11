from __future__ import annotations
import json
from typing import Any, Dict


class JOTJSONEncoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        kwargs['indent'] = 2
        json.JSONEncoder.__init__(self, *args, **kwargs)

    def default(self, obj) -> Dict[str, Any]:
        if hasattr(obj, 'to_jot_json'):
            return obj.to_jot_json()
        return json.JSONEncoder.default(self, obj)
