import json
import pytest

import jotjson
import randosettings as rset


@pytest.fixture(scope='session')
def settings():
    GF = rset.GameFlags
    settings = rset.Settings()
    settings.gameflags = GF.FIX_GLITCH | GF.EPOCH_FAIL
    settings.bucket_settings.objectives_win = True
    settings.char_settings.choices[5] == [5]
    settings.tab_settings.scheme = scheme = rset.TabRandoScheme.BINOMIAL
    return settings


def test_json_encode_settings(settings):
    data = json.dumps(settings, cls=jotjson.JOTJSONEncoder)
    assert data, 'Failed to encode settings into JSON.'


def test_json_decode_settings(settings):
    data = json.dumps({'configuration': {'test': 1}, 'settings': settings}, cls=jotjson.JOTJSONEncoder)
    decoded = json.loads(data, cls=jotjson.JOTJSONDecoder)
    assert decoded['settings'] == settings, 'Decoded settings do not match initial settings'

    # for now, we strip configuration out
    assert 'configuration' not in decoded, 'Unexpected configuration in decoded JSON'
