#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修正 3041 bundle 内 trim.json 的 animKey（3040_x -> 3041_x），并重新加密。"""
import sys, json
import UnityPy
sys.path.insert(0, '/workspace/tools')
import seer

SRC = '/workspace/work/fight3041_new.bundle'
OUT = '/workspace/work/fight3041_v8.bundle'
UnityPy.config.FALLBACK_UNITY_VERSION = '5.6.7f1'

plain, salt = seer.decrypt(SRC)
env = UnityPy.load(plain)

changed = []
for obj in env.objects:
    if obj.type.name != 'TextAsset':
        continue
    d = obj.read()
    s = d.m_Script
    if isinstance(s, bytes):
        s = s.decode('utf-8')
    if '3040_' in s:
        new = s.replace('3040_', '3041_')
        d.m_Script = new
        d.save()
        changed.append((d.m_Name, s.count('3040_'), len(new) - len(s)))

print('changed texts:', changed)
assert len(changed) == 3, changed

raw = env.file.save(packer='lz4')
enc = seer.encrypt(raw, salt)
open(OUT, 'wb').write(enc)
print('bundle out', len(enc), 'plain', len(raw))

# ---- 复核：解密、容器、animKey、spriteName 与 Sprite 名称一致性
plain2, salt2 = seer.decrypt(OUT)
assert salt2 == salt
env2 = UnityPy.load(plain2)
assert env2.file.save(packer='lz4') is not None
sprite_names = set()
for obj in env2.objects:
    if obj.type.name == 'Sprite':
        sprite_names.add(obj.read().m_Name)
print('sprites', len(sprite_names), sorted(sprite_names)[:5])
for obj in env2.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read()
        sc = d.m_Script
        if isinstance(sc, bytes):
            sc = sc.decode('utf-8-sig', 'replace')
        txt = sc.lstrip('\ufeff')
        js = json.loads(txt)
        missing = [f['spriteName'] for f in js['frames'] if f['spriteName'] not in sprite_names]
        print('TEXT', d.m_Name, 'animKey', js['animKey'], 'frameCount',
              js['frameCount'], 'frames', len(js['frames']), 'missing sprites', len(missing))
        assert js['animKey'].startswith('3041_'), js['animKey']
        assert js['frameCount'] == len(js['frames'])
    if obj.type.name == 'AssetBundle':
        tt = obj.read_typetree()
        print('AB', tt['m_Name'], 'container', len(tt['m_Container']))
        assert all('/3041/' in p for p, _ in tt['m_Container'])
