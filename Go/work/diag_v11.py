#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诊断：v10 中各 clip 的 Sprite 尺寸/枢轴/PPU/trim，以及官方 3040(v9) 对照。"""
import sys, json, struct
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
import warnings
warnings.filterwarnings('ignore')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'

for tag, path in (('v9', '/workspace/work/fight3041_v9.plain'),
                  ('v10', '/workspace/work/fight3041_v10.plain')):
    env = UnityPy.load(path)
    objs = list(env.objects)
    sprites = {o.path_id: o for o in objs if o.type.name == 'Sprite'}
    clips = {o.read_typetree()['m_Name']: o for o in objs if o.type.name == 'AnimationClip'}
    print('=====', tag, 'objects', len(objs))
    for cn in sorted(clips):
        order = [p['m_PathID'] for p in clips[cn].read_typetree()['m_ClipBindingConstant']['pptrCurveMapping']]
        rows = []
        for sid in order:
            st = sprites[sid].read_typetree()
            r = st['m_Rect']
            ds = st['m_RD']['m_VertexData']['m_DataSize']
            nv = st['m_RD']['m_VertexData']['m_VertexCount']
            pos = struct.unpack('<%df' % (nv * 5), ds[:nv * 20])
            xs = pos[0::5]; ys = pos[1::5]
            rows.append((int(r['width']), int(r['height']),
                         st['m_Pivot']['x'], st['m_Pivot']['y'], st['m_PixelsToUnits'],
                         round(min(xs), 3), round(max(xs), 3), round(min(ys), 3), round(max(ys), 3),
                         nv))
        ws = [x[0] for x in rows]; hs = [x[1] for x in rows]
        print(' %s frames=%d  W %d..%d med=%d   H %d..%d med=%d' % (
            cn, len(rows), min(ws), max(ws), sorted(ws)[len(ws)//2],
            min(hs), max(hs), sorted(hs)[len(hs)//2]))
        print('   pivots', sorted(set((x[2], x[3]) for x in rows)), 'ppu', sorted(set(x[4] for x in rows)),
              'vtx', sorted(set((x[5], x[6], x[7], x[8], x[9]) for x in rows))[:3])
        print('   first4', rows[:4])
    for o in objs:
        if o.type.name == 'TextAsset':
            t = o.read_typetree()
            js = json.loads(t['m_Script'].lstrip('\ufeff'))
            fr = js['frames']
            print(' trim', t['m_Name'], 'frameCount', js['frameCount'],
                  'source', sorted(set((f['sourceW'], f['sourceH']) for f in fr)),
                  'trim', sorted(set((f['trimX'], f['trimY'], f['trimW'], f['trimH']) for f in fr))[:3],
                  'first', fr[0], 'keys', sorted(js.keys()))
    env = None
