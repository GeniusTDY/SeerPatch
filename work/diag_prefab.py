#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 UISeerFight.prefab 中找宠物立绘 Image 的 RectTransform（尺寸/枢轴/锚点）。"""
import sys, json
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
import warnings
warnings.filterwarnings('ignore')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'

P = sys.argv[1] if len(sys.argv) > 1 else '/tmp/fb/assets/aa/Android/fight_assets_all_c32312b91be3884937546802bfa190c8.bundle'
env = UnityPy.load(P)
objs = list(env.objects)
print('objects', len(objs))
from collections import Counter
print(Counter(o.type.name for o in objs))

go = {}
for o in objs:
    if o.type.name == 'GameObject':
        t = o.read_typetree()
        go[o.path_id] = t
print('GameObjects', len(go))

# 收集 RectTransform
rts = {}
for o in objs:
    if o.type.name == 'RectTransform':
        t = o.read_typetree()
        rts[o.path_id] = t
print('RectTransforms', len(rts))


def comps(go_t):
    return [(c['component']['m_PathID'], c['classID'] if 'classID' in c else None) for c in go_t.get('m_Component', [])]


names = {}
for pid, t in go.items():
    names[pid] = t.get('m_Name', '')

hits = []
for pid, t in rts.items():
    sd = t.get('m_SizeDelta', {})
    w, h = sd.get('x', 0), sd.get('y', 0)
    if 120 <= w <= 700 and 120 <= h <= 900:
        gopid = t.get('m_GameObject', {}).get('m_PathID', 0)
        hits.append((pid, names.get(gopid, '?'), w, h,
                     t.get('m_Pivot', {}), t.get('m_AnchoredPosition', {}), t.get('m_AnchorMin', {}), t.get('m_AnchorMax', {})))
print('candidate rects', len(hits))
for h in hits:
    print('  %-28s size=(%7.1f,%7.1f) pivot=%s pos=%s amin=%s amax=%s' % (
        h[1], h[2], h[3], h[4], h[5], h[6], h[7]))
