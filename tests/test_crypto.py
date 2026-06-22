"""
Tests for pan115.crypto.

NOTE: encode() encrypts with 115.com's PUBLIC RSA key (client→server).
      decode() applies the same public key to SERVER responses (server signs with
      its private key; client verifies with public key). These are NOT inverses —
      a round-trip encode→decode is mathematically impossible with only the public key.

      We test:
        - encode(): symmetric (XOR) layer round-trips correctly
        - encode(): output is valid base64, correct length
        - decode(): sym_decode/encode round-trip (the symmetric inner layer)
"""
import json
import base64
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from pan115.crypto import encode, _sym_encode, _sym_decode, _get_key
import hashlib


def _derive_key(ts: int) -> bytes:
    return hashlib.md5(f"!@###@#{ts}DFDR@#@#".encode()).digest()


def test_encode_returns_valid_base64():
    plaintext = json.dumps({"pickcode": "abc123XYZ"})
    ts = 1718000000
    ciphertext, key = encode(plaintext, ts)
    # Must be valid base64
    decoded = base64.b64decode(ciphertext)
    # RSA output: each 117-byte block → 128 bytes; payload = 16 (key) + len(plaintext)
    # So at minimum we get 128 bytes out
    assert len(decoded) >= 128


def test_encode_key_is_md5_of_timestamp():
    ts = 1718000000
    _, key = encode("test", ts)
    expected = _derive_key(ts)
    assert key == expected


def test_encode_different_timestamps_produce_different_ciphertext():
    plaintext = json.dumps({"pickcode": "sameCode"})
    c1, _ = encode(plaintext, 1000000)
    c2, _ = encode(plaintext, 1000001)
    assert c1 != c2


def test_symmetric_roundtrip():
    """The XOR symmetric layer (sym_encode/sym_decode) must round-trip correctly."""
    import os
    data = b"Hello, 115.com! This is a test payload."
    key1 = os.urandom(4)
    key2 = os.urandom(12)
    encrypted = _sym_encode(data, key1, key2)
    # sym_decode with same keys should recover original
    from pan115.crypto import _sym_decode
    recovered = _sym_decode(encrypted, key1, key2)
    assert recovered == data


def test_symmetric_encode_decode_same_keys():
    """sym_decode reverses sym_encode when given the same keys."""
    import os
    from pan115.crypto import _sym_decode
    data = json.dumps({"pickcode": "testPickCode123"}).encode()
    key1 = os.urandom(4)
    key2 = os.urandom(12)
    encrypted = _sym_encode(data, key1, key2)
    recovered = _sym_decode(encrypted, key1, key2)
    assert recovered == data
