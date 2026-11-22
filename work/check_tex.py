#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用战斗动画贴图审计：python check_tex.py <plain> [clipPrefix...]"""
import sys, os, json, warnings, statistics
warnings.filterwarnings('ignore')
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
sys.path.insert(0, '/workspace/work')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'


def sig(im):
    return list(im.split()[3].resize((32, 32), Image.BILINEAR).getdata())


def mad(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) / float(len(a))


if __name__ == '__main__':
    from PIL import Image
    path = sys.argv[1]
    prefixes = sys.argv[2:] or ['3040']
    env = UnityPy.load(open(path, 'rb').read())
    bf = env.files[list(env.files.keys())[0]]
    sf = bf.files[[k for k in bf.files if not k.endswith('.resS')][0]]
    by = {o.path_id: o for o in sf.objects.values()}
    clips, trims = {}, {}
    for o in sf.objects.values():
        if o.type.name == 'AnimationClip':
            clips[o.read().m_Name] = o
        elif o.type.name == 'TextAsset':
            tt = o.read_typetree()
            if tt['m_Name'].endswith('.trim'):
                trims[tt['m_Name'][:-5]] = json.loads(tt['m_Script'].lstrip('\ufeff'))
    sigs = {}
    for name in sorted(clips):
        if name.split('_')[0] not in prefixes:
            continue
        d = clips[name].read_typetree()
        order = [p['m_PathID'] for p in d['m_ClipBindingConstant']['pptrCurveMapping']]
        prev = None; first = last = None; diffs = []; sizes = []; dups = 0
        for pid in order:
            st = by[pid].read_typetree()
            W, H = int(st['m_Rect']['width']), int(st['m_Rect']['height'])
            sizes.append((W, H))
            im = by[st['m_RD']['texture']['m_PathID']].read().image.convert('RGBA')
            s = sig(im); im.close()
            if first is None:
                first = s
            last = s
            if prev is not None:
                v = mad(prev, s); diffs.append(v)
                if v < 1.0:
                    dups += 1
            prev = s
        med = statistics.median(diffs) if diffs else 0
        print('=== %s keys=%d rate=%g stop=%.3f  W %d..%d H %d..%d first %dx%d last %dx%d' % (
            name, len(order), d['m_SampleRate'], d['m_MuscleClip']['m_StopTime'],
            min(s[0] for s in sizes), max(s[0] for s in sizes),
            min(s[1] for s in sizes), max(s[1] for s in sizes),
            sizes[0][0], sizes[0][1], sizes[-1][0], sizes[-1][1]))
        print('    diff median %.2f max %.2f dup %d   loop first-last %.2f' % (
            med, max(diffs) if diffs else 0, dups, mad(first, last)))
        sigs[name] = (first, last)
    for n in sorted(sigs):
        if n.endswith('_1'):
            i0 = sigs[n][0]
            for k in (2, 3, 4):
                m = n[:-1] + str(k)
                if m in sigs:
                    print('  %s first-idle %.2f last-idle %.2f' % (m, mad(sigs[m][0], i0), mad(sigs[m][1], i0)))
