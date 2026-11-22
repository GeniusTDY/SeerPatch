#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 catalog_<id>.json 与 fight<id> 资源包写回游戏 APK。"""
import sys, zipfile, os, shutil

zipfile.ZIP64_LIMIT = 0xFFFFFFFF

SRC = '/workspace/Seer_2.2_精灵美术修复.apk'
OUT = '/workspace/work/Seer_petfight_unsigned.apk'
HASH = '64a25feae0a77a1241f236224fb3777b'
CAT = '/workspace/work/catalog_3041.json'


def main(pid='3041'):
    bname = 'assets/aa/Android/fight%s_assets_all_%s.bundle' % (pid, HASH)
    repl = {'assets/aa/catalog.json': open(CAT, 'rb').read()}
    add = {bname: open('/workspace/work/fight%s.enc' % pid, 'rb').read()}
    print('catalog', len(repl['assets/aa/catalog.json']), 'add', bname, len(add[bname]))

    zin = zipfile.ZipFile(SRC)
    zout = zipfile.ZipFile(OUT, 'w', zipfile.ZIP_STORED)
    done = set()
    for info in zin.infolist():
        ni = zipfile.ZipInfo(info.filename, date_time=info.date_time)
        ni.external_attr = info.external_attr
        ni.create_system = info.create_system
        ni.comment = info.comment
        ni.compress_type = info.compress_type
        ni.extra = info.extra
        if info.filename in repl:
            zout.writestr(ni, repl[info.filename])
            done.add(info.filename)
        else:
            with zin.open(info) as src, zout.open(ni, 'w') as dst:
                shutil.copyfileobj(src, dst, 1 << 20)
    for name, data in add.items():
        ni = zipfile.ZipInfo(name, date_time=(2026, 11, 15, 20, 0, 0))
        ni.compress_type = zipfile.ZIP_STORED
        zout.writestr(ni, data)
    zout.close()
    assert set(repl) <= done, 'catalog not found'
    print('OUT', OUT, os.path.getsize(OUT))


if __name__ == '__main__':
    main(*(sys.argv[1:] or ['3041']))
