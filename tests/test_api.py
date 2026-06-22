"""Tests for pan115.api — mocked HTTP responses."""
import json
import sys
import pathlib
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

import pytest

try:
    import responses as resp_mock
    HAS_RESPONSES = True
except ImportError:
    HAS_RESPONSES = False

from pan115.crypto import encode


SKIP = pytest.mark.skipif(not HAS_RESPONSES, reason="responses library not installed")

_SAMPLE_COOKIE = """\
# Netscape HTTP Cookie File
#HttpOnly_.115.com\tTRUE\t/\tFALSE\t9999999999\tUID\t12345_A1_0
.115.com\tTRUE\t/\tFALSE\t9999999999\tacw_tc\ttestvalue
"""


def _make_cookie_file(tmp_dir: str) -> pathlib.Path:
    p = pathlib.Path(tmp_dir) / "cookies.txt"
    p.write_text(_SAMPLE_COOKIE, encoding="utf-8")
    return p


@SKIP
def test_get_download_url_calls_proapi():
    import responses as rm
    from pan115.api import Client115

    ts = int(time.time())
    pickcode = "testpickcode123"
    plaintext = json.dumps({"pickcode": pickcode})
    _, key = encode(plaintext, ts)

    # Build a valid encrypted response
    from pan115.crypto import encode as enc, decode as dec
    ct, key = enc(json.dumps({
        pickcode: {
            "file_name": "test.mkv",
            "file_size": 12345,
            "url": {"url": "https://cdn.115.com/test.mkv"},
            "pick_code": pickcode,
        }
    }), ts)

    with rm.RequestsMock() as rsps:
        rsps.add(
            rm.POST,
            "https://proapi.115.com/app/chrome/downurl",
            json={"state": True, "data": ct},
        )
        with tempfile.TemporaryDirectory() as tmp:
            cookie_path = _make_cookie_file(tmp)
            client = Client115(cookie_path)
            # Patch timestamp so decode key matches
            import unittest.mock as mock
            with mock.patch("pan115.api.time.time", return_value=ts):
                with mock.patch("pan115.api.encode", return_value=(ct, key)):
                    entry = {"pick_code": pickcode, "sha1": "abc", "path": "", "file_name": "test.mkv"}
                    info = client.get_download_url(entry)
            assert "test.mkv" in info["name"]
            assert info["link"] == "https://cdn.115.com/test.mkv"
