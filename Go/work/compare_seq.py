#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对比目标画布尺寸序列与源 bbox 序列。"""
import sys, os, io, json
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
texs = {o.path_id: o.read_typetree() for o in objs if o.type.name == 'Texture2D'}
clips = {o.read_typetree()['m_Name']: o.read_typetree() for o in objs if o.type.name == 'AnimationClip'}

MAP = {'3041_2': 'DefineSprite_113', '3041_3': 'DefineSprite_73', '3041_4': 'DefineSprite_136'}

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
    n = len(seq)
    m = len(sb)
    print('==', clip, 'target', n, 'src', m)
    print(' target:', [seq[i] for i in range(n)])
    print(' srcmap:', [sb[min(m - 1, i * m // n)] for i in range(n)])
