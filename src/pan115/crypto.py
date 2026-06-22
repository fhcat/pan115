"""
Port of acgotaku/115 secret.js — RSA-PKCS1 + XOR symmetric encryption.

All constants (kts, keyS, keyL, RSA modulus n) are copied verbatim from the
extension source and are unlikely to change.
"""
import hashlib
import math
import base64

# RSA public key constants from secret.js
_RSA_N = int(
    "8686980c0f5a24c4b9d43020cd2c22703ff3f450756529058b1cf88f09b8602136477198a6e2683"
    "149659bd122c33592fdb5ad47944ad1ea4d36c6b172aad6338c3bb6ac6227502d010993ac967d1"
    "aef00f0c8e038de2e4d3bc2ec368af2e9f10a6f1eda4f7262f136420c07c331b871bf139f74f30"
    "10e3c4fe57df3afb71683",
    16,
)
_RSA_E = 0x10001
_RSA_BLOCK = 128

# XOR key tables from secret.js
_KTS = bytes([
    240, 229, 105, 174, 191, 220, 191, 138, 26, 69, 232, 190, 125, 166, 115, 184,
    222, 143, 231, 196, 69, 218, 134, 196, 155, 100, 139, 20, 106, 180, 241, 170,
    56, 1, 53, 158, 38, 105, 44, 134, 0, 107, 79, 165, 54, 52, 98, 166, 42, 150,
    104, 24, 242, 74, 253, 189, 107, 151, 143, 77, 143, 137, 19, 183, 108, 142,
    147, 237, 14, 13, 72, 62, 215, 47, 136, 216, 254, 254, 126, 134, 80, 149, 79,
    209, 235, 131, 38, 52, 219, 102, 123, 156, 126, 157, 122, 129, 50, 234, 182,
    51, 222, 58, 169, 89, 52, 102, 59, 170, 186, 129, 96, 72, 185, 213, 129, 156,
    248, 108, 132, 119, 255, 84, 120, 38, 95, 190, 232, 30, 54, 159, 52, 128, 92,
    69, 44, 155, 118, 213, 27, 143, 204, 195, 184, 245,
])
_KEY_S = bytes([0x29, 0x23, 0x21, 0x5E])
_KEY_L = bytes([120, 6, 173, 76, 51, 134, 93, 24, 76, 1, 63, 70])


# ── RSA helpers ──────────────────────────────────────────────────────────────

def _pkcs1_pad(data: bytes, n_len: int) -> int:
    """PKCS#1 v1.5 type-2 padding (encrypt), returns big integer."""
    msg_len = len(data)
    if msg_len > n_len - 11:
        raise ValueError("Message too long for RSA block")
    pad_len = n_len - msg_len - 3
    # Use 0xff as deterministic pad (matches JS: ba[--n] = 0xff)
    padded = b"\x00\x02" + bytes([0xFF] * pad_len) + b"\x00" + data
    return int.from_bytes(padded, "big")


def _pkcs1_unpad(n: int) -> bytes:
    """PKCS#1 v1.5 unpad after RSA decrypt."""
    raw = n.to_bytes((_RSA_BLOCK), "big")
    # find the 0x00 separator after the 0x02 marker
    idx = raw.index(b"\x00", 2)
    return raw[idx + 1:]


def _rsa_encrypt_block(data: bytes) -> bytes:
    m = _pkcs1_pad(data, _RSA_BLOCK)
    c = pow(m, _RSA_E, _RSA_N)
    return c.to_bytes(_RSA_BLOCK, "big")


def _rsa_decrypt_block(data: bytes) -> bytes:
    m = int.from_bytes(data, "big")
    c = pow(m, _RSA_E, _RSA_N)
    return _pkcs1_unpad(c)


def _asym_encode(src: bytes) -> str:
    """Encrypt src in RSA blocks, return base64 string."""
    block = _RSA_BLOCK - 11
    out = b""
    for i in range(math.ceil(len(src) / block)):
        out += _rsa_encrypt_block(src[i * block: (i + 1) * block])
    return base64.b64encode(out).decode()


def _asym_decode(src: bytes) -> bytes:
    """Decrypt RSA-encrypted bytes block by block."""
    out = b""
    for i in range(math.ceil(len(src) / _RSA_BLOCK)):
        out += _rsa_decrypt_block(src[i * _RSA_BLOCK: (i + 1) * _RSA_BLOCK])
    return out


# ── XOR symmetric cipher ─────────────────────────────────────────────────────

def _get_key(length: int, key: bytes | None = None) -> bytes:
    if key is not None:
        return bytes(
            ((key[i] + _KTS[length * i]) & 0xFF) ^ _KTS[length * (length - 1 - i)]
            for i in range(length)
        )
    return _KEY_L if length == 12 else _KEY_S


def _xor_enc(src: bytes, key: bytes) -> bytearray:
    key_len = len(key)
    src_len = len(src)
    mod4 = src_len % 4
    out = bytearray(src_len)
    for i in range(mod4):
        out[i] = src[i] ^ key[i % key_len]
    for i in range(mod4, src_len):
        out[i] = src[i] ^ key[(i - mod4) % key_len]
    return out


def _sym_encode(src: bytes, key1: bytes, key2: bytes | None = None) -> bytes:
    k1 = _get_key(4, key1)
    k2 = _get_key(12, key2)
    ret = _xor_enc(src, k1)
    ret.reverse()
    return bytes(_xor_enc(bytes(ret), k2))


def _sym_decode(src: bytes, key1: bytes, key2: bytes) -> bytes:
    k1 = _get_key(4, key1)
    k2 = _get_key(12, key2)
    ret = _xor_enc(src, k2)
    ret.reverse()
    return bytes(_xor_enc(bytes(ret), k1))


# ── Public API ────────────────────────────────────────────────────────────────

def encode(plaintext: str, timestamp: int) -> tuple[str, bytes]:
    """
    Encode plaintext with timestamp-derived key.

    Returns (base64_ciphertext, raw_key) — the key is needed for decode().
    """
    key = hashlib.md5(f"!@###@#{timestamp}DFDR@#@#".encode()).digest()
    data = plaintext.encode()
    encrypted = _sym_encode(data, key)
    payload = key[:16] + encrypted
    return _asym_encode(payload), key


def decode(b64_ciphertext: str, key: bytes) -> str:
    """Decode a ProAPI response using the key returned by encode()."""
    raw = base64.b64decode(b64_ciphertext)
    decrypted = _asym_decode(raw)
    inner_key = decrypted[:16]
    body = decrypted[16:]
    return _sym_decode(body, key, inner_key).decode()
