#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诊断：dump 304x_1..4 clip 结构与逐帧 sprite 尺寸。"""
import sys, os, json, collections, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
sys.path.insert(0, '/workspace/work')
import UnityPy, seer
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'

BUNDLE = sys.argv[1] if len(sys.argv) > 1 else '/workspace/patch_v1.1.34/assets/aa/Android/fight3041_assets_all_6b19939c69def5b7c66c3cc84ce44beb.bundle'
plain, salt = seer.decrypt_bytes(open(BUNDLE, 'rb').read())
env = UnityPy.load(plain)
bf = env.files[list(env.files.keys())[0]]
sf = bf.files[[k for k in bf.files if not k.endswith('.resS')][0]]

clips = {}
sprites = {}
for o in sf.objects.values():
    t = o.type.name
    if t == 'AnimationClip':
        clips[o.read().m_Name] = o
    elif t == 'Sprite':
        sprites[o.path_id] = o

print('clips:', len(clips), 'sprites:', len(sprites))

def key_times(curve):
    return [k.time for k in curve['m_Curve']]

for name in sorted(clips):
    if not (name.startswith('304') and name.split('_')[-1] in ('1', '2', '3', '4')):
        continue
    o = clips[name]
    d = o.read_typetree()
    sr = d.get('m_SampleRate')
    ln = d.get('m_Length')
    fc = d.get('m_FloatCurves') or []
    pc = d.get('m_PPtrCurves') or []
    ec = d.get('m_EditorCurves') or []
    maxt = 0.0
    nk = 0
    paths = collections.Counter()
    for c in fc:
        ts = key_times(c)
        if ts:
            maxt = max(maxt, max(ts))
            nk += len(ts)
        paths[c.get('path', '')] += 1
    print('\n===', name, 'rate', sr, 'len', ln,
          'floatCurves', len(fc), 'pptrCurves', len(pc), 'editor', len(ec),
          'keys', nk, 'maxT', round(maxt, 4), 'pptrMap', len(d.get('m_PPtrCurveMapping') or []))
    print('   paths:', dict(paths))
    for c in pc[:4]:
        cnt = len(c.get('m_Curve') or [])
        print('   pptr', c.get('path'), c.get('attribute'), 'keys', cnt)
    # sprites referenced
    seen = []
    for c in pc:
        for k in (c.get('m_Curve') or []):
            pid = k['value']['m_PathID']
            if pid:
                seen.append(pid)
    uniq = list(dict.fromkeys(seen))
    if uniq:
        sizes = collections.Counter()
        missing = 0
        for pid in uniq:
            so = sprites.get(pid)
            if so is None:
                missing += 1
                continue
            sd = so.read()
            r = sd.m_Rect
            sizes[(r.width, r.height)] += 1
        print('   spriteRefs', len(seen), 'uniq', len(uniq), 'missing', missing,
              'sizes', dict(sizes))
        if len(sizes) > 1:
            # 打印前 8 帧尺寸序列
            seq = []
            for pid in seen:
                so = sprites.get(pid)
                if so:
                    r = so.read().m_Rect
                    seq.append(f'{r.width:g}x{r.height:g}')
                else:
                    seq.append('?')
            print('   seq(first10):', seq[:10])
