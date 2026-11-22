import sys, struct, zipfile, re
sys.path.insert(0, '/workspace/work')
import seer_plain  # installs Crypto shim
sys.path.insert(0, '/workspace/tools')
import seer

APK = '/workspace/Seer_patched_signed.apk'
zf = zipfile.ZipFile(APK)
names = [n for n in zf.namelist() if re.search(r'/fight\d+_assets_all_', n)]

def head_flags(name):
    with zf.open(name) as f:
        raw = f.read(200000)
    if not seer.is_encrypted(raw):
        pt = raw
    else:
        salt = raw[8:24]
        size = struct.unpack('<Q', raw[24:32])[0]
        k_enc, k_mac, k_iv = seer._keys(salt)
        blen = min(seer.BLOCK, size)
        clen = blen - (blen % 16) + 16
        ct = raw[64:64 + clen]
        from Crypto.Cipher import AES
        iv = seer._h(struct.pack('<q', 0), k_iv)[:16]
        pt = AES.new(k_enc, AES.MODE_CBC, iv).decrypt(ct)
    p = pt.index(b'\0') + 1
    p += 4
    p = pt.index(b'\0', p) + 1
    p = pt.index(b'\0', p) + 1
    p += 8
    ci, ui, flags = struct.unpack_from('>III', pt, p)
    return hex(flags), len(raw)

ids = [int(x) for x in sys.argv[1:]]
for pid in ids:
    cand = [n for n in names if re.search(r'/fight%d_assets_all_' % pid, n)]
    if not cand:
        print(pid, 'missing')
        continue
    print(pid, head_flags(cand[0]))
