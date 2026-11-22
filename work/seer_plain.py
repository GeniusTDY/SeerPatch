"""Persistent helper: decrypt SEERAB01 bundles using `cryptography` (system python)."""
import sys, os, types
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# ---- minimal pycryptodome-compatible shim ----
class _AES:
    MODE_CBC = 2

    def __init__(self, key, mode, iv):
        self.key, self.iv = key, iv

    @staticmethod
    def new(key, mode, iv):
        return _AES(key, mode, iv)

    def decrypt(self, data):
        d = Cipher(algorithms.AES(self.key), modes.CBC(self.iv)).decryptor()
        return d.update(data) + d.finalize()

    def encrypt(self, data):
        e = Cipher(algorithms.AES(self.key), modes.CBC(self.iv)).encryptor()
        return e.update(data) + e.finalize()


def _pad(b, n):
    k = n - len(b) % n
    return b + bytes([k]) * k


def _unpad(b, n):
    k = b[-1]
    assert 1 <= k <= n and b[-k:] == bytes([k]) * k
    return b[:-k]


crypto = types.ModuleType('Crypto')
cipher = types.ModuleType('Crypto.Cipher')
util = types.ModuleType('Crypto.Util')
padding = types.ModuleType('Crypto.Util.Padding')
cipher.AES = _AES
padding.pad = _pad
padding.unpad = _unpad
crypto.Cipher = cipher
crypto.Util = util
util.Padding = padding
sys.modules.update({'Crypto': crypto, 'Crypto.Cipher': cipher,
                    'Crypto.Util': util, 'Crypto.Util.Padding': padding})

sys.path.insert(0, '/workspace/tools')

if __name__ == '__main__':
    import seer
    src, dst = sys.argv[1], sys.argv[2]
    plain, salt = seer.decrypt(src)
    with open(dst, 'wb') as f:
        f.write(plain)
    print('plain', len(plain), '->', dst)
