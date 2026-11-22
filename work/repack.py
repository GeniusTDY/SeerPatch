#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重打包 APK：替换 classes.dex，追加图鉴与技能数据资源。"""
import os
import zipfile

BASE = '/workspace/pdapp/out/base2.apk'
DEX = '/workspace/pdapp/out/dex_new/classes.dex'
OUT = '/workspace/pdapp/out/new_unsigned.apk'
ASSETS = '/workspace/pdapp/assets'

STORE_DIRS = ('pets/', 'pets_big/', 'types/')

zin = zipfile.ZipFile(BASE)
zout = zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED)
for info in zin.infolist():
    data = zin.read(info.filename)
    if info.filename == 'classes.dex':
        data = open(DEX, 'rb').read()
    ni = zipfile.ZipInfo(info.filename, date_time=info.date_time)
    ni.external_attr = info.external_attr
    ni.compress_type = info.compress_type
    zout.writestr(ni, data)

for name in ('dex.json', 'skills.json'):
    path = os.path.join(ASSETS, name)
    ni = zipfile.ZipInfo('assets/' + name, date_time=(2026, 11, 14, 0, 0, 0))
    ni.external_attr = 0o644 << 16
    ni.compress_type = zipfile.ZIP_DEFLATED
    zout.writestr(ni, open(path, 'rb').read())

count = 0
for sub in STORE_DIRS:
    d = os.path.join(ASSETS, sub)
    for fn in sorted(os.listdir(d)):
        if not fn.endswith('.webp'):
            continue
        path = os.path.join(d, fn)
        ni = zipfile.ZipInfo('assets/' + sub + fn, date_time=(2026, 11, 14, 0, 0, 0))
        ni.external_attr = 0o644 << 16
        ni.compress_type = zipfile.ZIP_STORED
        zout.writestr(ni, open(path, 'rb').read())
        count += 1

zout.close()
print('entries', len(zipfile.ZipFile(OUT).infolist()), 'images', count)
print('size', os.path.getsize(OUT))
