"""Tests for pan115.aria2 output formatting."""
import sys, pathlib, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from pan115.aria2 import format_entry, write


_SAMPLE = {
    "name": "Movies/test.mkv",
    "link": "https://cdndown.115.com/file/xxxx",
    "size": 1234567890,
    "sha1": "aabbccddeeff00112233445566778899aabbccdd",
    "cookie": "acw_tc=abc123",
    "pickcode": "abc123",
}


def test_format_entry_contains_url():
    out = format_entry(_SAMPLE)
    assert _SAMPLE["link"] in out


def test_format_entry_contains_out():
    out = format_entry(_SAMPLE)
    assert "out=Movies/test.mkv" in out


def test_format_entry_contains_cookie():
    out = format_entry(_SAMPLE)
    assert "header=Cookie: acw_tc=abc123" in out


def test_format_entry_contains_checksum():
    out = format_entry(_SAMPLE)
    assert "checksum=sha-1=aabbccddeeff00112233445566778899aabbccdd" in out


def test_format_entry_no_cookie():
    info = {**_SAMPLE, "cookie": ""}
    out = format_entry(info)
    assert "Cookie" not in out


def test_write_creates_file():
    with tempfile.TemporaryDirectory() as tmp:
        p = pathlib.Path(tmp) / "out.conf"
        count = write([_SAMPLE, _SAMPLE], p)
        assert count == 2
        text = p.read_text()
        assert text.count(_SAMPLE["link"]) == 2
        assert "\n\n" in text
