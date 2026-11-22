#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对比线性映射与 DTW 映射的画布/素材尺寸匹配度。"""
import sys, os, io, math
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


def src_bboxes(sym, cache={}):
    if sym in cache:
        return cache[sym]
    d = '/workspace/work/swfsvg/' + sym
    out = []
    for f in sorted(os.listdir(d), key=lambda x: int(x.split('.')[0])):
        png = cairosvg.svg2png(url=os.path.join(d, f), scale=1)
        im = Image.open(io.BytesIO(png)).convert('RGBA')
        bb = im.getbbox()
        out.append((bb[2] - bb[0], bb[3] - bb[1]))
    cache[sym] = out
    return out


def dtw_map(t, s, pen=0.15):
    n, m = len(t), len(s)
    INF = 1e18
    D = [[INF] * m for _ in range(n)]
    B = [[0] * m for _ in range(n)]
    c = [[abs(math.log(t[i][0] / float(s[j][0]))) + abs(math.log(t[i][1] / float(s[j][1])))
          for j in range(m)] for i in range(n)]
    D[0][0] = c[0][0]
    for i in range(1, n):
        D[i][0] = D[i - 1][0] + c[i][0] + pen
        B[i][0] = 0
    for j in range(1, m):
        D[0][j] = D[0][j - 1] + c[0][j] + pen
        B[0][j] = 1
    for i in range(1, n):
        for j in range(1, m):
            opts = [(D[i - 1][j - 1], 2), (D[i - 1][j] + pen, 0), (D[i][j - 1] + pen, 1)]
            D[i][j], B[i][j] = min(opts)
            D[i][j] += c[i][j]
    mp = [0] * n
    i, j = n - 1, m - 1
    mp[i] = j
    while i > 0 or j > 0:
        b = B[i][j]
        if b == 2:
            i, j = i - 1, j - 1
        elif b == 0:
            i -= 1
        else:
            j -= 1
        if i >= 0 and j >= 0:
            mp[i] = j
    return mp


def stats(name, ratios):
    ratios = sorted(ratios)
    def p(q):
        k = (len(ratios) - 1) * q
        f = int(k)
        c = min(f + 1, len(ratios) - 1)
        return ratios[f] + (ratios[c] - ratios[f]) * (k - f)
    print('  %-6s min %.2f p10 %.2f p25 %.2f p50 %.2f | <0.7: %d/%d' % (
        name, ratios[0], p(.1), p(.25), p(.5),
        sum(1 for x in ratios if x < 0.7), len(ratios)))


for clip, sym in MAP:
    t = [(int(sprites[p['m_PathID']]['m_Rect']['width']), int(sprites[p['m_PathID']]['m_Rect']['height']))
         for p in clips[clip]['m_ClipBindingConstant']['pptrCurveMapping']]
    s = src_bboxes(sym)
    n, m = len(t), len(s)
    lin = [min(t[i][0] / float(s[min(m - 1, int(round(i * (m - 1) / float(n - 1))))][0]),
               t[i][1] / float(s[min(m - 1, int(round(i * (m - 1) / float(n - 1))))][1])) for i in range(n)]
    mp = dtw_map(t, s)
    dt = [min(t[i][0] / float(s[mp[i]][0]), t[i][1] / float(s[mp[i]][1])) for i in range(n)]
    print('==', clip, 'target', n, 'src', m)
    stats('linear', lin)
    stats('dtw', dt)
    print('  dtw map first 12:', mp[:12], '... last 8:', mp[-8:])
