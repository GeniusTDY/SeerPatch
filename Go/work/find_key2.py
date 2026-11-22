"""Parse UnityFS header of the decrypted bundle, then brute-force the custom key."""
import sys, struct
from concurrent.futures import ProcessPoolExecutor
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

SIG = b'#$unity3dchina!@'


def cstr(b, p):
    e = b.index(b'\0', p)
    return b[p:e].decode('utf-8', 'replace'), e + 1


def parse(path):
    d = open(path, 'rb').read()
    p = 0
    magic, p = cstr(d, p)
    version, = struct.unpack_from('>I', d, p); p += 4
    uver, p = cstr(d, p)
    urev, p = cstr(d, p)
    size, = struct.unpack_from('>q', d, p); p += 8
    ci, ui, flags = struct.unpack_from('>II I', d, p); p += 12
    print('magic', magic, 'v', version, uver, urev, 'flags', hex(flags))
    if not flags & 0x80:
        print('not encrypted')
        return None
    unk, = struct.unpack_from('>I', d, p); p += 4
    vec_data = d[p:p + 16]; p += 16
    vec_key = d[p:p + 16]; p += 16
    p += 1
    data_sig = d[p:p + 16]; p += 16
    key_sig = d[p:p + 16]; p += 16
    return key_sig, data_sig


def work(args):
    meta, key_sig, data_sig, lo, hi = args
    d = open(meta, 'rb').read()
    for i in range(lo, hi):
        key = d[i:i + 16]
        enc = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
        blk = enc.update(key_sig) + enc.finalize()
        if bytes(a ^ b for a, b in zip(data_sig, blk)) == SIG:
            return i, key
    return None


if __name__ == '__main__':
    key_sig, data_sig = parse(sys.argv[1])
    print('key_sig', key_sig.hex(), 'data_sig', data_sig.hex())
    meta = sys.argv[2]
    n = len(open(meta, 'rb').read()) - 16
    chunks = 8
    size = n // chunks + 1
    jobs = [(meta, key_sig, data_sig, i * size, min(n, (i + 1) * size)) for i in range(chunks)]
    with ProcessPoolExecutor(chunks) as ex:
        for r in ex.map(work, jobs):
            if r:
                print('FOUND', r[0], r[1], r[1].decode('utf-8', 'backslashreplace'))
                ex.shutdown(cancel_futures=True)
                break
