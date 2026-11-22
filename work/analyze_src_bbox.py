#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统计 SWF 各帧 alpha bbox（scale=1），用于确定缩放策略。"""
import sys, os
import cairosvg
from PIL import Image
import io, statistics

MAP = {
    '3041_1': ('DefineSprite_139_pet', 21),
    '3041_2': ('DefineSprite_113', 88),
    '3041_3': ('DefineSprite_73', 53),
    '3041_4': ('DefineSprite_136', 56),
}
BASE = '/workspace/work/swfsvg'

for clip, (sym, n) in MAP.items():
    d = os.path.join(BASE, sym)
    files = sorted(os.listdir(d), key=lambda x: int(x.split('.')[0]))
    bbs = []
    for f in files:
        png = cairosvg.svg2png(url=os.path.join(d, f), scale=1)
        im = Image.open(io.BytesIO(png)).convert('RGBA')
        bb = im.getbbox()
        bbs.append((im.size, bb, (bb[2] - bb[0], bb[3] - bb[1]) if bb else (0, 0)))
    ws = [b[2][0] for b in bbs]
    hs = [b[2][1] for b in bbs]
    print(clip, sym, 'frames', len(bbs))
    print('  canvas sizes', sorted(set(b[0] for b in bbs)))
    print('  w min/med/max', min(ws), statistics.median(ws), max(ws))
    print('  h min/med/max', min(hs), statistics.median(hs), max(hs))
    for i, b in enumerate(bbs[:6]):
        print('   f%d' % (i + 1), b)
