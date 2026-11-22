#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 v1.1.30 战斗动画预览 GIF（按游戏 trim 位移合成）。"""
import sys, json, os
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
sys.path.insert(0, '/workspace/work')
import warnings
warnings.filterwarnings('ignore')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
import seer
from PIL import Image

SCALE = 0.24
FPS = 20


def load(pid):
    raw, _ = seer.decrypt_bytes(open('/workspace/work/fight%s_v1130.bundle' % pid, 'rb').read())
    env = UnityPy.load(raw)
    objs = list(env.objects)
    by = {o.path_id: o for o in objs}
    cl = {o.read_typetree()['m_Name']: o for o in objs if o.type.name == 'AnimationClip'}
    tri = {}
    for o in objs:
        if o.type.name == 'TextAsset':
            t = o.read_typetree()
            tri[t['m_Name'][:-5]] = json.loads(t['m_Script'].lstrip('\ufeff'))
    return by, cl, tri


def build(pid):
    by, cl, tri = load(pid)
    frames = []       # (RGBA frame at final canvas, seconds)
    meta = []
    for cn in (pid + '_1', pid + '_2', pid + '_3', pid + '_4'):
        ids = [x['m_PathID'] for x in cl[cn].read_typetree()['m_ClipBindingConstant']['pptrCurveMapping']]
        fr = tri[cn]['frames']
        meta.append((cn, ids, fr))
    # 统一画布
    xs0 = []; xs1 = []; ys0 = []; ys1 = []
    for cn, ids, fr in meta:
        f0 = fr[0]
        for f in fr:
            ox = (f['trimX'] + f['trimW'] / 2) - (f0['trimX'] + f0['trimW'] / 2)
            oy = f['trimY'] - f0['trimY']
            xs0.append(-f['trimW'] / 2 + ox); xs1.append(f['trimW'] / 2 + ox)
            ys0.append(oy); ys1.append(oy + f['trimH'])
        break  # 用 _1 的锚点即可；攻击帧可能更宽，下面再扩
    # 重新用全部 clip 的绝对范围（各自首帧锚点相同）
    xs0 = []; xs1 = []; ys0 = []; ys1 = []
    for cn, ids, fr in meta:
        f0 = fr[0]
        for f in fr:
            ox = (f['trimX'] + f['trimW'] / 2) - (f0['trimX'] + f0['trimW'] / 2)
            oy = f['trimY'] - f0['trimY']
            xs0.append(-f['trimW'] / 2 + ox); xs1.append(f['trimW'] / 2 + ox)
            ys0.append(oy); ys1.append(oy + f['trimH'])
    X0, X1 = min(xs0) - 30, max(xs1) + 30
    Y0, Y1 = min(ys0) - 30, max(ys1) + 30
    W = max(2, int((X1 - X0) * SCALE)); H = max(2, int((Y1 - Y0) * SCALE))
    print(pid, 'canvas', (W, H), 'world', (round(X0), round(X1), round(Y0), round(Y1)))

    out = []
    idx = 0
    for cn, ids, fr in meta:
        f0 = fr[0]
        n = len(ids)
        keep = max(1, int(round(30.0 / FPS)))
        for i in range(n):
            if i % keep:
                continue
            f = fr[i]
            sprite = by[ids[i]].read()
            im = sprite.image
            if im is None:
                continue
            im = im.convert('RGBA')
            ox = (f['trimX'] + f['trimW'] / 2) - (f0['trimX'] + f0['trimW'] / 2)
            oy = f['trimY'] - f0['trimY']
            cv = Image.new('RGBA', (W, H), (250, 246, 236, 255))
            tw = max(1, int(f['trimW'] * SCALE)); th = max(1, int(f['trimH'] * SCALE))
            sm = im.resize((tw, th), Image.LANCZOS)
            px = int((-f['trimW'] / 2 + ox - X0) * SCALE)
            py = int((Y1 - (oy + f['trimH'])) * SCALE)
            cv.alpha_composite(sm, (px, py))
            out.append(cv.convert('P', palette=Image.ADAPTIVE, colors=128))
            idx += 1
    dur = int(1000 / FPS)
    path = '/workspace/work/preview_%s_v1130.gif' % pid
    out[0].save(path, save_all=True, append_images=out[1:], duration=dur, loop=0, disposal=2)
    print(pid, 'gif', path, len(out), 'frames', os.path.getsize(path))


if __name__ == '__main__':
    for pid in (sys.argv[1:] or ['3042', '3043']):
        build(pid)
