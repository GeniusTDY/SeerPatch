#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""计算逐帧 contain 比例分布，辅助选择缩放策略。"""
import sys, os, io, statistics
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

MAP = {'3041_1': 'DefineSprite_139_pet', '3041_2': 'DefineSprite_113',
       '3041_3': 'DefineSprite_73', '3041_4': 'DefineSprite_136'}


def pct(v, p):
    v = sorted(v)
    k = (len(v) - 1) * p / 100.0
    f = int(k)
    c = min(f + 1, len(v) - 1)
    return v[f] + (v[c] - v[f]) * (k - f)


for clip, sym in MAP.items():
    t = clips[clip]
    seq = []
    for p in t['m_ClipBindingConstant']['pptrCurveMapping']:
        st = sprites[p['m_PathID']]
        seq.append((int(st['m_Rect']['width']), int(st['m_Rect']['height'])))
    d = '/workspace/work/swfsvg/' + sym
    files = sorted(os.listdir(d), key=lambda x: int(x.split('.')[0]))
    sb = []
    for f in files:
        png = cairosvg.svg2png(url=os.path.join(d, f), scale=1)
        im = Image.open(io.BytesIO(png)).convert('RGBA')
        bb = im.getbbox()
        sb.append((bb[2] - bb[0], bb[3] - bb[1]))
    n, m = len(seq), len(sb)
    ratios = []
    for i in range(n):
        w, h = sb[min(m - 1, i * m // n)]
        tw, th = seq[i]
        ratios.append(min(tw / float(w), th / float(h)))
    print(clip, 'contain ratios: p0=%.2f p10=%.2f p25=%.2f p50=%.2f p75=%.2f p90=%.2f max=%.2f' % (
        pct(ratios, 0), pct(ratios, 10), pct(ratios, 25), pct(ratios, 50),
        pct(ratios, 75), pct(ratios, 90), pct(ratios, 100)),
        'mean=%.2f' % statistics.mean(ratios))
    hratios = [seq[i][1] / float(sb[min(m - 1, i * m // n)][1]) for i in range(n)]
    print('   height ratios p10=%.2f p50=%.2f p90=%.2f' % (pct(hratios, 10), pct(hratios, 50), pct(hratios, 90)))
