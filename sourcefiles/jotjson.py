import json
import randoconfig as cfg
import randosettings as rset

class JOTJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, cfg.RandoConfig) or isinstance(obj, rset.Settings):
            return obj.json_dict()
        elif isinstance(obj, rset.GameFlags):
            return [str(flag) for flag in rset.GameFlags if flag in obj]
        elif isinstance(obj, rset.CosmeticFlags):
            return [str(flag) for flag in rset.CosmeticFlags if flag in obj]
        return json.JSONEncoder.default(self, obj)
