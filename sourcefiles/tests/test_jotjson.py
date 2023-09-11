import json
import pytest

import jotjson
import randosettings as rset


@pytest.fixture(scope='session')
def settings():
    GF = rset.GameFlags
    settings = rset.Settings()
    settings.gameflags = GF.FIX_GLITCH | GF.EPOCH_FAIL
    return settings


def test_json_encode_settings(settings):
    data = json.dumps(settings, cls=jotjson.JOTJSONEncoder)
    assert data, 'Failed to encode settings into JSON.'
