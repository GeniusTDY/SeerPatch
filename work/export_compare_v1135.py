#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 v1.1.35 包中导出关键帧对比图（白底，等高排列）。"""
import sys, json, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
sys.path.insert(0, '/workspace/work')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
from PIL import Image

env = UnityPy.load(open('/workspace/work/fight3041_v1135.plain', 'rb').read())
bf = env.files[list(env.files.keys())[0]]
sf = bf.files[[k for k in bf.files if not k.endswith('.resS')][0]]
by = {o.path_id: o for o in sf.objects.values()}
clips = {o.read().m_Name: o for o in sf.objects.values() if o.type.name == 'AnimationClip'}


def frames(name):
    d = clips[name].read_typetree()
    order = [p['m_PathID'] for p in d['m_ClipBindingConstant']['pptrCurveMapping']]
    out = []
    for pid in order:
        st = by[pid].read_typetree()
        im = by[st['m_RD']['texture']['m_PathID']].read().image.convert('RGBA')
        out.append(im)
    return out


def sheet(items, path, H=420, pad=8):
    ims = []
    for im in items:
        s = H / float(im.height)
        ims.append(im.resize((max(1, int(im.width * s)), H), Image.LANCZOS))
    W = sum(i.width for i in ims) + pad * (len(ims) + 1)
    out = Image.new('RGB', (W, H + 2 * pad), (250, 250, 250))
    x = pad
    for i in ims:
        out.paste(i, (x, pad), i)
        x += i.width + pad
    out.save(path)
    print(path, out.size)


i1 = frames('3041_1')
sheet([i1[0], i1[5], i1[10], i1[14], i1[17], i1[20]], '/tmp/v35_3041_idle.png')
a2 = frames('3041_2')
a3 = frames('3041_3')
a4 = frames('3041_4')
sheet([i1[0], a2[0], a2[-1], a3[0], a3[-1], a4[0], a4[-1]], '/tmp/v35_3041_atk.png')

i2 = frames('3042_1')
b2 = frames('3042_2')
b3 = frames('3042_3')
b4 = frames('3042_4')
sheet([i2[0], b2[0], b2[43], b2[-1], b3[0], b3[26], b3[-1], b4[-1]], '/tmp/v35_3042.png')

i3 = frames('3043_1')
c2 = frames('3043_2')
c3 = frames('3043_3')
c4 = frames('3043_4')
sheet([i3[0], c2[0], c2[43], c2[-1], c3[0], c3[26], c3[-1], c4[-1]], '/tmp/v35_3043.png')
