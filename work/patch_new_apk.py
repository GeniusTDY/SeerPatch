import struct, os, zlib, sys

p = '/workspace/Seer_2.2_战斗资源测试3_3041.apk'
CAT = 'assets/aa/catalog.json'
BUN = 'assets/aa/Android/fight3041_assets_all_64a25feae0a77a1241f236224fb3777b.bundle'
cat = open('/workspace/work/catalog_3041_v5.json', 'rb').read()
bun = open('/workspace/work/patch17/assets/aa/Android/fight3041_assets_all_64a25feae0a77a1241f236224fb3777b.bundle', 'rb').read()

f = open(p, 'r+b')
size = os.path.getsize(p)
base = max(0, size - 66000)
f.seek(base); buf = f.read()
i = buf.rfind(b'PK\x05\x06')
_, _, _, _, total, cd_size, cd_off, clen = struct.unpack('<IHHHHIIH', buf[i:i + 22])
print('entries', total, 'cd_off', cd_off, 'cd_size', cd_size)
f.seek(cd_off); cd = f.read(cd_size)
recs = []; q = 0; drop = []
while q < len(cd):
    nlen, elen, cl2 = struct.unpack('<HHH', cd[q + 28:q + 34]); ln = 46 + nlen + elen + cl2
    nm = cd[q + 46:q + 46 + nlen].decode()
    if nm == CAT or (nm.startswith('META-INF/') and (nm.endswith(('.SF', '.RSA', '.DSA')) or nm.endswith('MANIFEST.MF'))):
        drop.append(nm)
    else:
        recs.append(cd[q:q + ln])
    q += ln
print('dropped', drop, 'kept', len(recs))

pos = cd_off
new = []
for name, data in ((CAT, cat), (BUN, bun), ('META-INF/MANIFEST.MF', b'Manifest-Version: 1.0\r\nCreated-By: 1.0 (Android)\r\n\r\n')):
    nb = name.encode()
    need = (4 - (pos + 30 + len(nb)) % 4) % 4
    extra = struct.pack('<HH', 0xD935, need) + b'\x00' * need
    crc = zlib.crc32(data) & 0xffffffff
    lh = struct.pack('<IHHHHHIIIHH', 0x04034b50, 20, 0, 0, 0, 0x21, crc, len(data), len(data), len(nb), len(extra)) + nb + extra
    new.append((pos, lh + data, name, data, extra, crc))
    pos += len(lh) + len(data)

f.seek(cd_off)
for _, blob, _, _, _, _ in new:
    f.write(blob)

def cdrec(name, size_, extra, crc, off):
    nb = name.encode()
    return struct.pack('<IHHHHHHIIIHHHHHII', 0x02014b50, 20, 20, 0, 0, 0, 0x21, crc, size_, size_, len(nb), len(extra), 0, 0, 0, 0, off) + nb + extra

allrecs = b''.join(recs) + b''.join(cdrec(n, len(d), e, c, o) for o, _, n, d, e, c in new)
ncd = pos
f.seek(ncd); f.write(allrecs)
f.write(struct.pack('<IHHHHIIH', 0x06054b50, 0, 0, len(recs) + len(new), len(recs) + len(new), len(allrecs), ncd, 0))
f.truncate(ncd + len(allrecs) + 22)
f.close()
print('patched size', os.path.getsize(p), 'catalog', len(cat), 'bundle', len(bun))
