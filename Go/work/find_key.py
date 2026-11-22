"""Brute force UnityFS custom key via known plaintext (system python + cryptography)."""
import sys
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

SIG = b'#$unity3dchina!@'

def find(meta_path, key_sig, data_sig, limit=None):
    with open(meta_path, 'rb') as f:
        data = f.read()
    n = len(data) - 16
    step = 1
    for i in range(0, n, step):
        key = data[i:i + 16]
        if not all(32 <= c < 127 for c in key):
            continue
        enc = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
        blk = enc.update(key_sig) + enc.finalize()
        if bytes(a ^ b for a, b in zip(data_sig, blk)) == SIG[:len(data_sig)]:
            return key
    return None

if __name__ == '__main__':
    k = find(sys.argv[1], sys.argv[2].encode(), sys.argv[3].encode())
    print('KEY', k.decode('utf-8', 'backslashreplace') if k else None)
    print('raw', k.hex() if k else None)
