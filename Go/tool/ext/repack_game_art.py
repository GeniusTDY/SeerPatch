#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把重新生成的资源包替换进游戏 APK。

用法：
  repack_game_art.py                      # 默认替换 peticon
  repack_game_art.py OUT NAME BUNDLE SALT  # 自定义单个替换项
"""
import sys, zipfile, os, shutil
sys.path.insert(0, '/workspace/tools')
import seer

# APK 未超过 4 GiB，禁止 zipfile 使用 ZIP64（部分 Android 工具不识别 ZIP64 尾记录）
zipfile.ZIP64_LIMIT = 0xFFFFFFFF

SRC = '/workspace/Seer_2.2_精灵美术修复.apk'
OUT = '/workspace/work/Seer_art_unsigned.apk'

DEFAULT = [(
    'assets/aa/Android/peticon_assets_all_051ca4e72be71ecbb6da4b41b3d7a753.bundle',
    '/workspace/work/peticon_new.bundle',
    '/workspace/work/peticon_cur.salt',
)]


def main():
    if len(sys.argv) == 5:
        items = [(sys.argv[2], sys.argv[3], sys.argv[4])]
        out = sys.argv[1]
    else:
        items = DEFAULT
        out = OUT

    repl = {}
    for name, bundle, salt in items:
        enc = seer.encrypt(open(bundle, 'rb').read(), open(salt, 'rb').read())
        print('replace', name, os.path.basename(bundle), len(enc))
        repl[name] = enc

    zin = zipfile.ZipFile(SRC)
    zout = zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED)
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
    zout.close()
    missing = set(repl) - done
    assert not missing, 'entries not found: %s' % missing
    print('OUT', out, os.path.getsize(out))


if __name__ == '__main__':
    main()
