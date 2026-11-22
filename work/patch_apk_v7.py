#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""尾部追加 + 重写中央目录：替换 catalog.json、加入新 bundle、补最小 MANIFEST。"""
import struct, sys, os, shutil, zlib

SRC = '/workspace/Seer_2.2_精灵美术修复.apk'
DST = '/workspace/work/Seer_v1122_unsigned.apk'
CAT = '/workspace/work/catalog_3041_v9.json'
BUN = '/workspace/work/fight3041_v9.bundle'
BUN_NAME = 'assets/aa/Android/fight3041_assets_all_6b19939c69def5b7c66c3cc84ce44beb.bundle'

DROP = {'assets/aa/catalog.json', BUN_NAME}


def stored(name, data):
    return name.encode(), data, zlib.crc32(data) & 0xFFFFFFFF


def main():
    if not os.path.exists(DST) or os.path.getsize(DST) != os.path.getsize(SRC):
        shutil.copyfile(SRC, DST)
    f = open(DST, 'r+b')
    size = os.path.getsize(DST)
    f.seek(max(0, size - 70000))
    tail = f.read()
    i = tail.rfind(b'PK\x05\x06')
    assert i >= 0, 'no EOCD'
    cdsz, cdoff = struct.unpack('<II', tail[i + 12:i + 20])
    f.seek(cdoff)
    cd = f.read(cdsz)
    assert cd[:4] == b'PK\x01\x02'
    kept = []
    q = 0
    while q < len(cd):
        v = struct.unpack('<IHHHHHHIIIHHHHHII', cd[q:q + 46])
        nl, el, cl = v[10], v[11], v[12]
        name = cd[q + 46:q + 46 + nl].decode()
        rec = cd[q:q + 46 + nl + el + cl]
        if name not in DROP and not (name.startswith('META-INF/') and name.split('/')[-1].split('.')[-1] in ('SF', 'RSA', 'DSA', 'MF')):
            kept.append(rec)
        q += 46 + nl + el + cl

    items = [stored('assets/aa/catalog.json', open(CAT, 'rb').read()),
             stored(BUN_NAME, open(BUN, 'rb').read()),
             stored('META-INF/MANIFEST.MF', b'Manifest-Version: 1.0\r\nCreated-By: SeerPatch\r\n\r\n')]

    pos = cdoff
    f.seek(pos)
    newrecs = []
    for name, data, crc in items:
        nb = name
        need = (4 - (pos + 30 + len(nb)) % 4) % 4
        extra = struct.pack('<HH', 0xD935, need) + b'\x00' * need
        lh = struct.pack('<IHHHHHIIIHH', 0x04034b50, 20, 0, 0, 0, 0x21, crc,
                         len(data), len(data), len(nb), len(extra)) + nb + extra
        f.write(lh)
        f.write(data)
        newrecs.append(struct.pack('<IHHHHHHIIIHHHHHII', 0x02014b50, 20, 20, 0, 0, 0, 0x21,
                                   crc, len(data), len(data), len(nb), len(extra),
                                   0, 0, 0, 0, pos) + nb + extra)
        pos += len(lh) + len(data)

    newcd = b''.join(kept) + b''.join(newrecs)
    f.write(newcd)
    f.write(struct.pack('<IHHHHIIH', 0x06054b50, 0, 0, len(kept) + len(newrecs),
                        len(kept) + len(newrecs), len(newcd), pos, 0))
    f.truncate(pos + len(newcd) + 22)
    f.close()
    print('entries', len(kept) + len(newrecs), 'cd_off', cdoff, 'size', os.path.getsize(DST))


if __name__ == '__main__':
    main()
