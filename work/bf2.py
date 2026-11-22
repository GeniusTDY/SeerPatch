import sys, time
from concurrent.futures import ProcessPoolExecutor
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

SIG = b'#$unity3dchina!@'
KSIG = bytes.fromhex('36663336616237663538333161633163')
DSIG = bytes.fromhex('41422d64303664386336653363313434')
TARGET = SIG[:len(DSIG)]


def work(args):
    path, lo, hi = args
    d = open(path, 'rb').read()
    for i in range(lo, hi):
        key = d[i:i + 16]
        enc = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
        blk = enc.update(KSIG) + enc.finalize()
        if bytes(a ^ b for a, b in zip(DSIG, blk)) == TARGET:
            return i, key.hex()
    return None


def scan(path, chunks=3):
    n = len(open(path, 'rb').read()) - 16
    size = n // chunks + 1
    t = time.time()
    jobs = [(path, i * size, min(n, (i + 1) * size)) for i in range(chunks)]
    with ProcessPoolExecutor(chunks) as ex:
        for r in ex.map(work, jobs):
            if r:
                print('FOUND', path, r[0], r[1], repr(bytes.fromhex(r[1])), flush=True)
                ex.shutdown(cancel_futures=True)
                return True
    print('miss', path, '%.0fs' % (time.time() - t), flush=True)
    return False


if __name__ == '__main__':
    for p in sys.argv[1:]:
        if scan(p):
            break
