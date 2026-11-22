#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分段（小幅/大幅）对齐映射评估。"""
import sys, os, io
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
import warnings
warnings.filterwarnings('ignore')
import UnityPy
import cairosvg
from PIL import Image
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'

env = UnityPy.load('/workspace/work/fight3041_v9.plain')
objs = list(env.objects)
sprites = {o.path_id: o.read_typetree() for o in objs if o.type.name == 'Sprite'}
clips = {o.read_typetree()['m_Name']: o.read_typetree() for o in objs if o.type.name == 'AnimationClip'}
MAP = [('3041_1', 'DefineSprite_139_pet'), ('3041_2', 'DefineSprite_113'),
       ('3041_3', 'DefineSprite_73'), ('3041_4', 'DefineSprite_136')]


def bboxes(sym):
    d = '/workspace/work/swfsvg/' + sym
    out = []
    for f in sorted(os.listdir(d), key=lambda x: int(x.split('.')[0])):
        png = cairosvg.svg2png(url=os.path.join(d, f), scale=1)
        im = Image.open(io.BytesIO(png)).convert('RGBA')
        bb = im.getbbox()
        out.append((bb[2] - bb[0], bb[3] - bb[1]))
    return out


def longest_run(flags):
    best = (0, -1, 0)
    i = 0
    while i < len(flags):
        if flags[i]:
            j = i
            while j + 1 < len(flags) and flags[j + 1]:
                j += 1
            if j - i + 1 > best[2]:
                best = (i, j, j - i + 1)
            i = j + 1
        else:
            i += 1
    return best


def seg_map(t, s):
    at_ = sorted(x[0] * x[1] for x in t)
    as_ = sorted(x[0] * x[1] for x in s)
    th_t = 1.6 * at_[max(0, len(at_) // 10)]
    th_s = 1.6 * as_[max(0, len(as_) // 10)]
    bt = longest_run([x[0] * x[1] > th_t for x in t])
    bs = longest_run([x[0] * x[1] > th_s for x in s])
    n, m = len(t), len(s)
    if bt[2] < 3 or bs[2] < 3:
        mp = [int(round(i * (m - 1) / float(n - 1))) if n > 1 else 0 for i in range(n)]
        return mp, ('linear', bt, bs)
    mp = [None] * n
    # head
    if bt[0] > 0 and bs[0] > 0:
        for i in range(bt[0]):
            mp[i] = int(round(i * (bs[0] - 1) / float(bt[0] - 1))) if bt[0] > 1 else 0
    elif bt[0] > 0:
        for i in range(bt[0]):
            mp[i] = 0
    # mid
    L = bt[1] - bt[0] + 1
    M = bs[1] - bs[0] + 1
    for k in range(L):
        mp[bt[0] + k] = bs[0] + (int(round(k * (M - 1) / float(L - 1))) if L > 1 else 0)
    # tail
    lt = n - 1 - bt[1]
    ls = m - 1 - bs[1]
    for k in range(lt):
        mp[bt[1] + 1 + k] = (bs[1] + 1 + (int(round(k * (ls - 1) / float(lt - 1))) if lt > 1 else 0)) if ls > 0 else bs[1]
    assert all(x is not None for x in mp)
    return mp, ('seg', bt, bs)


def pct(v, q):
    v = sorted(v)
    k = (len(v) - 1) * q
    f = int(k)
    c = min(f + 1, len(v) - 1)
    return v[f] + (v[c] - v[f]) * (k - f)


for clip, sym in MAP:
    t = [(int(sprites[p['m_PathID']]['m_Rect']['width']), int(sprites[p['m_PathID']]['m_Rect']['height']))
         for p in clips[clip]['m_ClipBindingConstant']['pptrCurveMapping']]
    s = bboxes(sym)
    mp, info = seg_map(t, s)
    assert all(mp[i] <= mp[i + 1] for i in range(len(mp) - 1)), (clip, mp)
    ratios = [min(t[i][0] / float(s[mp[i]][0]), t[i][1] / float(s[mp[i]][1])) for i in range(len(t))]
    runs = []
    cur = 1
    for k in range(1, len(mp)):
        if mp[k] == mp[k - 1]:
            cur += 1
        else:
            runs.append(cur); cur = 1
    runs.append(cur)
    print('==', clip, info[0], 'tbig', info[1], 'sbig', info[2])
    print('   ratios min %.2f p10 %.2f p50 %.2f  maxhold %d  <0.9:%d' % (
        pct(ratios, 0), pct(ratios, .1), pct(ratios, .5), max(runs),
        sum(1 for r in ratios if r < 0.9)))
    print('   map', mp)
