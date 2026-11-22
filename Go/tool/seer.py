#!/usr/bin/env python3
"""SEERAB01 container encrypt/decrypt for Seer APK assets/aa/Android/*.bundle."""
import struct, hmac, hashlib, sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

MAGIC = b'SEERAB01'
MASTER = bytes.fromhex('6b0c00b22f31491c2dd2b8e337f006a28039fa7296a94d84a60ccf22aa340996')
BLOCK = 65536


def _h(data, key):
    return hmac.new(key, data, hashlib.sha256).digest()


def _keys(salt):
    return _h(salt + b'\x01', MASTER), _h(salt + b'\x02', MASTER), _h(salt + b'\x03', MASTER)


def is_encrypted(data):
    return data[:8] == MAGIC


def decrypt_bytes(data):
    assert data[:8] == MAGIC, 'not SEERAB01'
    salt = data[8:24]
    size = struct.unpack('<Q', data[24:32])[0]
    k_enc, k_mac, k_iv = _keys(salt)
    out = bytearray()
    off = 64
    i = 0
    while len(out) < size:
        blen = min(BLOCK, size - len(out))
        clen = blen - (blen % 16) + 16
        ct = data[off:off + clen]
        mac = data[off + clen:off + clen + 32]
        iv = _h(struct.pack('<q', i), k_iv)[:16]
        pt = unpad(AES.new(k_enc, AES.MODE_CBC, iv).decrypt(ct), 16)
        assert len(pt) == blen
        assert hmac.new(k_mac, struct.pack('<q', i) + ct, hashlib.sha256).digest() == mac
        out += pt
        off += clen + 32
        i += 1
    return bytes(out), salt


def decrypt(path):
    data = open(path, 'rb').read()
    plain, salt = decrypt_bytes(data)
    return plain, salt


def encrypt(plain, salt):
    k_enc, k_mac, k_iv = _keys(salt)
    hdr = MAGIC + salt + struct.pack('<Q', len(plain))
    hdr += _h(hdr, k_mac)
    assert len(hdr) == 64
    out = bytearray(hdr)
    i = 0
    for pos in range(0, len(plain), BLOCK):
        chunk = plain[pos:pos + BLOCK]
        iv = _h(struct.pack('<q', i), k_iv)[:16]
        ct = AES.new(k_enc, AES.MODE_CBC, iv).encrypt(pad(chunk, 16))
        mac = hmac.new(k_mac, struct.pack('<q', i) + ct, hashlib.sha256).digest()
        assert len(ct) == len(chunk) - len(chunk) % 16 + 16
        out += ct + mac
        i += 1
    return bytes(out)


def main():
    if len(sys.argv) < 4:
        print('usage: seer.py d|e in out [salthex]')
        return
    mode = sys.argv[1]
    if mode == 'd':
        plain, salt = decrypt(sys.argv[2])
        open(sys.argv[3], 'wb').write(plain)
        print('decrypted', len(plain), 'salt', salt.hex())
    else:
        plain = open(sys.argv[2], 'rb').read()
        salt = bytes.fromhex(sys.argv[4]) if len(sys.argv) > 4 else decrypt(sys.argv[5])[1]
        open(sys.argv[3], 'wb').write(encrypt(plain, salt))
        print('encrypted', len(plain))


if __name__ == '__main__':
    main()
