#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""移除零长度 .resS 目录节点并重新打包（对象数据保持不变）。"""
import sys, os
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
import warnings
warnings.filterwarnings('ignore')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
import seer

SRC = '/workspace/work/fight3041_v10.plain'
OUT = '/workspace/work/fight3041_v10b.plain'
ENC = '/workspace/work/fight3041_v10b.bundle'

env = UnityPy.load(SRC)
bf = env.file
print('nodes before', list(bf.files.keys()))
for k in [k for k in list(bf.files.keys()) if k.endswith('.resS')]:
    del bf.files[k]
print('nodes after ', list(bf.files.keys()))
out = bf.save(packer='lz4')
open(OUT, 'wb').write(out)
print('saved', len(out))

# 逐对象对比
env2 = UnityPy.load(SRC)
o1 = {o.path_id: (o.byte_size, o.get_raw_data() if hasattr(o, 'get_raw_data') else None) for o in env2.objects}
env3 = UnityPy.load(out)
objs3 = list(env3.objects)
print('objects', len(objs3))
diff = []
for o in objs3:
    sz, raw = o1[o.path_id]
    r3 = o.get_raw_data() if hasattr(o, 'get_raw_data') else None
    if o.byte_size != sz or (raw is not None and r3 != raw):
        diff.append((o.type.name, o.path_id, sz, o.byte_size))
print('diff objects', len(diff), diff[:5])

_, salt = seer.decrypt('/workspace/work/fight3041_v10.bundle')
enc = seer.encrypt(out, salt)
open(ENC, 'wb').write(enc)
print('encrypted', len(enc), 'salt', salt.hex())
