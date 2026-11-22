#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""深度自检 A：clip 时序 / sprite 尺寸 / trim 轨迹（无需解码贴图）。"""
import sys, os, json, warnings, collections
warnings.filterwarnings('ignore')
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
sys.path.insert(0, '/workspace/work')
import UnityPy, seer
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'


def load(path):
    raw = open(path, 'rb').read()
    if raw[:8] == b'SEERAB01':
        raw, _ = seer.decrypt_bytes(raw)
    env = UnityPy.load(raw)
    bf = env.files[list(env.files.keys())[0]]
    return bf.files[[k for k in bf.files if not k.endswith('.resS')][0]]


def analyze(sf, label, prefixes=('3040', '3041', '3042', '3043')):
    clips, sprites, trims = {}, {}, {}
    for o in sf.objects.values():
        t = o.type.name
        if t == 'AnimationClip':
            clips[o.read().m_Name] = o
        elif t == 'Sprite':
            sprites[o.path_id] = o
        elif t == 'TextAsset':
            tt = o.read_typetree()
            n = tt['m_Name']
            if n.endswith('.trim'):
                trims[n[:-5]] = json.loads(tt['m_Script'].lstrip('\ufeff'))
    print('\n########', label)
    for name in sorted(clips):
        pre = name.split('_')[0]
        if pre not in prefixes:
            continue
        d = clips[name].read_typetree()
        order = [p['m_PathID'] for p in d['m_ClipBindingConstant']['pptrCurveMapping']]
        n = len(order)
        sr = d.get('m_SampleRate')
        st = d['m_MuscleClip'].get('m_StopTime')
        sizes = []
        for pid in order:
            r = sprites[pid].read().m_Rect
            sizes.append((int(r.width), int(r.height)))
        ws = [s[0] for s in sizes]; hs = [s[1] for s in sizes]
        line = '%s keys=%d rate=%g stop=%.3f  W %d..%d H %d..%d' % (
            name, n, sr, st, min(ws), max(ws), min(hs), max(hs))
        if name in trims:
            fr = trims[name]['frames']
            tx = [f['trimX'] for f in fr]; ty = [f['trimY'] for f in fr]
            tw = [f['trimW'] for f in fr]; th = [f['trimH'] for f in fr]
            line += '  trim n=%d X %d..%d Y %d..%d W %d..%d H %d..%d' % (
                len(fr), min(tx), max(tx), min(ty), max(ty), min(tw), max(tw), min(th), max(th))
            # 帧间位移（按 trim 中心 x 与 trimY）
            cx = [tx[i] + tw[i] / 2.0 for i in range(len(fr))]
            dx = [round(cx[i + 1] - cx[i], 1) for i in range(len(cx) - 1)]
            dy = [round(ty[i + 1] - ty[i], 1) for i in range(len(ty) - 1)]
            dw = [tw[i + 1] - tw[i] for i in range(len(tw) - 1)]
            dh = [th[i + 1] - th[i] for i in range(len(th) - 1)]
            line += '\n    centerDX max|%g|  trimDY max|%g|  dW %d..%d dH %d..%d' % (
                max(abs(v) for v in dx), max(abs(v) for v in dy),
                min(dw), max(dw), min(dh), max(dh))
            big = [(i + 1, dx[i], dy[i]) for i in range(len(dx))
                   if abs(dx[i]) > 20 or abs(dy[i]) > 20]
            if big:
                line += '  JUMPS>20: %s' % big[:8]
        print(line)
    # 3040 官方 trim 详情
    for name in sorted(trims):
        if not name.startswith('3040'):
            continue
        fr = trims[name]['frames']
        print('   official %s frames=%d first5=%s' % (
            name, len(fr), [(f['trimX'], f['trimY'], f['trimW'], f['trimH']) for f in fr[:5]]))


if __name__ == '__main__':
    analyze(load('/workspace/work/fight3040.plain'), '官方 3040 (reference)')
    analyze(load('/workspace/work/fight3041_v1135.plain'), '当前 v1.1.35')
    analyze(load('/workspace/work/fight3041_v1134.plain'), '上一版 v1.1.34')
