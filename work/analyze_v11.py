#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统计：每帧原图 bbox 与官方 3040 trim 的关系，用于确定 v11 放大比例。"""
import sys, os, io, json
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
import warnings
warnings.filterwarnings('ignore')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
import cairosvg
from PIL import Image

sys.path.insert(0, '/workspace/work')
from build_bundle_v10 import CLIPS, SVG_ROOT, seg_map, src_bboxes

env = UnityPy.load('/workspace/work/fight3041_v10.plain')
objs = list(env.objects)
sprites = {o.path_id: o for o in objs if o.type.name == 'Sprite'}
clips = {o.read_typetree()['m_Name']: o for o in objs if o.type.name == 'AnimationClip'}
trims = {}
for o in objs:
    if o.type.name == 'TextAsset':
        t = o.read_typetree()
        trims[t['m_Name'][:-5]] = json.loads(t['m_Script'].lstrip('\ufeff'))

for clip_name, sym in CLIPS:
    order = [p['m_PathID'] for p in clips[clip_name].read_typetree()['m_ClipBindingConstant']['pptrCurveMapping']]
    d = os.path.join(SVG_ROOT, sym)
    srcs = sorted(os.listdir(d), key=lambda x: int(x.split('.')[0]))
    tgt = []
    for sid in order:
        st = sprites[sid].read_typetree()
        tgt.append((int(st['m_Rect']['width']), int(st['m_Rect']['height'])))
    sb = src_bboxes(sym)
    jmap, info = seg_map(tgt, sb)
    print('==== %s  frames=%d src=%d %s' % (clip_name, len(order), len(srcs), info))
    tr = trims.get(clip_name)
    tm = {}
    if tr:
        tm = {f['spriteName']: f for f in tr['frames']}
    rows = []
    for i, sid in enumerate(order):
        st = sprites[sid].read_typetree()
        nm = st['m_Name']
        bw, bh = sb[jmap[i]]
        rH = int(st['m_Rect']['height']); rW = int(st['m_Rect']['width'])
        if tr:
            f = tm.get(nm)
            tH = f['trimH'] if f else None
            tW = f['trimW'] if f else None
            tY = f['trimY'] if f else None
            tX = f['trimX'] if f else None
            sY = f['sourceH'] if f else None
            sX = f['sourceW'] if f else None
        else:
            tH = tW = tY = tX = sY = sX = None
        rows.append((i + 1, nm, bw, bh, rW, rH, tW, tH, tX, tY, sX, sY))
    q = [r for r in rows if r[7]]
    if q:
        ratios = [r[7] / float(r[3]) for r in q]
        ratios.sort()
        print('  trimH/bh: min %.3f p10 %.3f med %.3f p90 %.3f max %.3f' % (
            ratios[0], ratios[len(ratios) // 10], ratios[len(ratios) // 2],
            ratios[9 * len(ratios) // 10], ratios[-1]))
        wr = sorted(r[6] / float(r[2]) for r in q)
        print('  trimW/bw: min %.3f med %.3f max %.3f' % (wr[0], wr[len(wr) // 2], wr[-1]))
    print('  bh: min %d med %d max %d' % (min(r[3] for r in rows), sorted(r[3] for r in rows)[len(rows) // 2], max(r[3] for r in rows)))
    print('  bw: min %d med %d max %d' % (min(r[2] for r in rows), sorted(r[2] for r in rows)[len(rows) // 2], max(r[2] for r in rows)))
    for r in rows[:6] + rows[-3:]:
        print('   #%d %-12s bbox %dx%d rect %dx%d trim %sx%s @(%s,%s) src %sx%s' % (
            r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], r[10], r[11]))
