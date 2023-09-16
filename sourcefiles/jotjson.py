from __future__ import annotations
import json

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import randosettings as rset


class JOTJSONEncoder(json.JSONEncoder):
    def default(self, obj) -> 'rset.JSONType':
        if hasattr(obj, '_jot_json'):
            return obj._jot_json()
        elif isinstance(obj, rset.GameFlags):
            return [str(flag) for flag in rset.GameFlags if flag in obj]
        elif isinstance(obj, rset.CosmeticFlags):
            return [str(flag) for flag in rset.CosmeticFlags if flag in obj]
        return json.JSONEncoder.default(self, obj)
