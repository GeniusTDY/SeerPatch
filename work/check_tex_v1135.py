#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""深度自检 B：解码当前 v1.1.35 全部战斗贴图，检查空帧/重复帧/循环接缝/尺寸连续性。"""
import sys, os, json, warnings, statistics
warnings.filterwarnings('ignore')
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
sys.path.insert(0, '/workspace/work')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
from PIL import Image

PLAIN = '/workspace/work/fight3041_v1135.plain'
CLIPS = [f'304{p}_{i}' for p in (1, 2, 3) for i in (1, 2, 3, 4)]


def sig(im):
    a = im.split()[3].resize((32, 32), Image.BILINEAR)
    return list(a.getdata())


def mad(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) / float(len(a))


def main():
    env = UnityPy.load(open(PLAIN, 'rb').read())
    bf = env.files[list(env.files.keys())[0]]
    sf = bf.files[[k for k in bf.files if not k.endswith('.resS')][0]]
    by = {o.path_id: o for o in sf.objects.values()}
    clips, trims = {}, {}
    for o in sf.objects.values():
        t = o.type.name
        if t == 'AnimationClip':
            clips[o.read().m_Name] = o
        elif t == 'TextAsset':
            tt = o.read_typetree()
            if tt['m_Name'].endswith('.trim'):
                trims[tt['m_Name'][:-5]] = json.loads(tt['m_Script'].lstrip('\ufeff'))

    sigs = {}
    for name in CLIPS:
        d = clips[name].read_typetree()
        order = [p['m_PathID'] for p in d['m_ClipBindingConstant']['pptrCurveMapping']]
        tri = trims.get(name)
        tframes = tri['frames'] if tri else []
        print('\n=== %s keys=%d rate=%g stop=%.3f trim=%d' %
              (name, len(order), d['m_SampleRate'],
               d['m_MuscleClip']['m_StopTime'], len(tframes)))
        tmap = {f['spriteName']: f for f in tframes}
        prev = None
        first = last = None
        diffs = []
        blank = []
        dup = []
        bad_bbox = []
        bad_trim = []
        sizes = []
        for i, pid in enumerate(order):
            st = by[pid].read_typetree()
            W, H = int(st['m_Rect']['width']), int(st['m_Rect']['height'])
            sizes.append((W, H))
            tex = by[st['m_RD']['texture']['m_PathID']].read()
            im = tex.image.convert('RGBA')
            bb = im.getbbox()
            if bb is None:
                blank.append(i + 1)
                prev = None
                im.close()
                continue
            cov = sum(1 for v in im.split()[3].getdata() if v > 16) / float(W * H)
            if cov < 0.005:
                blank.append(i + 1)
            if bb[0] > 2 or bb[1] > 2 or bb[2] < W - 2 or bb[3] < H - 2:
                bad_bbox.append((i + 1, bb, (W, H)))
            s = sig(im)
            im.close()
            if first is None:
                first = s
            last = s
            if prev is not None:
                v = mad(prev, s)
                diffs.append(v)
                if v < 1.0:
                    dup.append(i + 1)
            prev = s
            f = tmap.get(st['m_Name'])
            if f is not None:
                if (int(f['trimW']), int(f['trimH'])) != (W, H):
                    bad_trim.append((i + 1, f['trimW'], f['trimH'], W, H))
        ws = [s[0] for s in sizes]; hs = [s[1] for s in sizes]
        dmax = max(diffs) if diffs else 0
        med = statistics.median(diffs) if diffs else 0
        big = [(i + 2, round(diffs[i], 1)) for i in range(len(diffs)) if diffs[i] > 4 * (med + 0.01)]
        print('  size W %d..%d H %d..%d  first=%dx%d last=%dx%d' %
              (min(ws), max(ws), min(hs), max(hs), sizes[0][0], sizes[0][1], sizes[-1][0], sizes[-1][1]))
        print('  motion diff median %.2f max %.2f  dup(<1.0) %d %s' %
              (med, dmax, len(dup), dup[:12]))
        if big:
            print('  SPIKES(x4 median):', big[:12])
        print('  blank frames:', blank, '  loose bbox:', bad_bbox[:5], '  trim mismatch:', bad_trim[:5])
        sigs[name] = (first, last)
        if name.endswith('_1'):
            print('  idle loop: first-vs-last %.2f  avg step %.2f  step range %.2f..%.2f'
                  % (mad(first, last), statistics.mean(diffs), min(diffs), max(diffs)))
    # 攻击首帧 / 末帧 与各自的待机首帧对比（拉伸到 32x32 的轮廓距离）
    print('\n=== attack <-> idle pose distance (32x32 silhouette MAD)')
    for p in (1, 2, 3):
        i0 = sigs['304%d_1' % p][0]
        for k in (2, 3, 4):
            n = '304%d_%d' % (p, k)
            a, b = sigs[n]
            print('  %s first-idle %.2f  last-idle %.2f' % (n, mad(a, i0), mad(b, i0)))


if __name__ == '__main__':
    main()
