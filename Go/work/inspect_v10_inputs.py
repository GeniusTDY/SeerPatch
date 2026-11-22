#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查 v9 plain 的 clip->sprite 顺序、sprite->texture、尺寸。"""
import sys, json, collections
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
import warnings
warnings.filterwarnings('ignore')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'

env = UnityPy.load('/workspace/work/fight3041_v9.plain')
objs = list(env.objects)
by_id = {o.path_id: o for o in objs}

sprites = {}
textures = {}
for o in objs:
    if o.type.name == 'Sprite':
        sprites[o.path_id] = o.read_typetree()
    elif o.type.name == 'Texture2D':
        textures[o.path_id] = o.read_typetree()

print('sprites', len(sprites), 'textures', len(textures))
for pid, t in list(textures.items())[:3]:
    print('TEX', pid, t['m_Name'], t['m_Width'], t['m_Height'], t['m_TextureFormat'], t['m_MipCount'], t['m_CompleteImageSize'], t.get('m_StreamData'))
print()

clips = [o for o in objs if o.type.name == 'AnimationClip']
for o in sorted(clips, key=lambda x: x.read_typetree()['m_Name']):
    t = o.read_typetree()
    pptr = t['m_ClipBindingConstant']['pptrCurveMapping']
    print('CLIP', t['m_Name'], 'frames', len(pptr), 'sampleRate', t['m_SampleRate'])
    seq = []
    for p in pptr:
        sid = p['m_PathID']
        st = sprites.get(sid)
        if st is None:
            seq.append((sid, None, None, None))
            continue
        texid = st['m_RD']['texture']['m_PathID']
        tt = textures.get(texid, {})
        seq.append((sid, st['m_Name'], (tt.get('m_Width'), tt.get('m_Height')), (st['m_Rect']['width'], st['m_Rect']['height'])))
    # 统计
    sizes = collections.Counter(x[2] for x in seq)
    rects = collections.Counter(x[3] for x in seq)
    print('  texsizes', dict(sizes))
    print('  rects', dict(rects))
    print('  first5', seq[:5])
    print('  last2', seq[-2:])
    names = [x[1] for x in seq]
    print('  unique names', len(set(names)))
    print()

# 全部 sprite 的 texture 是否 1:1
tex_of_sprite = collections.Counter()
for sid, st in sprites.items():
    tex_of_sprite[st['m_RD']['texture']['m_PathID']] += 1
print('texture refs per texture', collections.Counter(tex_of_sprite.values()))

# trim JSON 概览
for o in objs:
    if o.type.name == 'TextAsset':
        t = o.read_typetree()
        js = json.loads(t['m_Script'].lstrip('\ufeff'))
        print('TRIM', t['m_Name'], 'frameCount', js['frameCount'], 'keys', list(js.keys()))
        print('  frame0', js['frames'][0])
        print('  sourceW/H', js.get('sourceW'), js.get('sourceH'))
