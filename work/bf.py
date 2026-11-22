"""Brute force Unity CN key given raw signatures; parallel over metadata windows."""
import sys, time
from concurrent.futures import ProcessPoolExecutor
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

SIG = b'#$unity3dchina!@'

def work(args):
    meta, ksig, dsig, lo, hi = args
    d = open(meta, 'rb').read()
    n = len(dsig)
    target = SIG[:n]
    for i in range(lo, hi):
        key = d[i:i + 16]
        try:
            enc = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
            blk = enc.update(ksig) + enc.finalize()
        except Exception:
            continue
        if bytes(a ^ b for a, b in zip(dsig, blk)) == target:
            return i, key.hex()
    return None

if __name__ == '__main__':
    meta, ksig_h, dsig_h = sys.argv[1], sys.argv[2], sys.argv[3]
    ksig = bytes.fromhex(ksig_h)
    dsig = bytes.fromhex(dsig_h)
    n = len(open(meta, 'rb').read()) - 16
    chunks = 3
    size = n // chunks + 1
    t = time.time()
    jobs = [(meta, ksig, dsig, i * size, min(n, (i + 1) * size)) for i in range(chunks)]
    with ProcessPoolExecutor(chunks) as ex:
        for r in ex.map(work, jobs):
            if r:
                print('FOUND offset', r[0], 'key', r[1],
                      repr(bytes.fromhex(r[1])))
                ex.shutdown(cancel_futures=True)
                break
        else:
            print('not found')
    print('%.1fs' % (time.time() - t))
