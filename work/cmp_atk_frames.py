#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对比 3040（官方）与 3041/3042/3043 攻击 clip 的逐帧贴图尺寸 + trim。"""
import sys, os, json, collections, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
sys.path.insert(0, '/workspace/work')
import UnityPy, seer
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'


def load(path):
    raw = open(path, 'rb').read()
    if raw[:8] == b'SEERAB01':
        raw, salt = seer.decrypt_bytes(raw)
    else:
        salt = None
    env = UnityPy.load(raw)
    bf = env.files[list(env.files.keys())[0]]
    sf = bf.files[[k for k in bf.files if not k.endswith('.resS')][0]]
    return sf


def show(sf, label):
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
            if n.endswith('.trim.json'):
                trims[n[:-10]] = json.loads(tt['m_Script'].lstrip('\ufeff'))
    print('\n#####', label, 'clips', sorted(clips), 'trims', sorted(trims))
    for name in sorted(clips):
        if not name.split('_')[0].isdigit():
            continue
        d = clips[name].read_typetree()
        order = [p['m_PathID'] for p in d['m_ClipBindingConstant']['pptrCurveMapping']]
        print('\n=== %s rate=%s stop=%s frames=%d hasMotionFloat=%s' % (
            name, d['m_SampleRate'], d['m_MuscleClip'].get('m_StopTime'), len(order),
            d.get('m_HasMotionFloatCurves')))
        if name.endswith('_1'):
            continue
        seq = []
        for pid in order:
            so = sprites.get(pid)
            if so is None:
                seq.append(('?', '?'))
                continue
            r = so.read().m_Rect
            seq.append((int(r.width), int(r.height)))
        print(' sizes(first12):', seq[:12])
        c = collections.Counter(seq)
        print(' distinct sizes:', len(c), 'top:', c.most_common(5))
        ws = [s[0] for s in seq]; hs = [s[1] for s in seq]
        print(' W %d..%d  H %d..%d' % (min(ws), max(ws), min(hs), max(hs)))
        ars = [w / float(h) for w, h in seq if h]
        print(' aspect %.3f..%.3f' % (min(ars), max(ars)))
        tri = trims.get(name)
        if tri:
            fr = tri['frames']
            tw = [f['trimW'] for f in fr]; th = [f['trimH'] for f in fr]
            tx = [f['trimX'] for f in fr]; ty = [f['trimY'] for f in fr]
            print(' trim n=%d spriteName0=%s W %d..%d H %d..%d X %d..%d Y %d..%d' % (
                len(fr), fr[0].get('spriteName'), min(tw), max(tw), min(th), max(th),
                min(tx), max(tx), min(ty), max(ty)))
            print(' trim first3:', [(f['trimX'], f['trimY'], f['trimW'], f['trimH']) for f in fr[:3]])
        # sprite names of first few
        names = [sprites[pid].read().m_Name if pid in sprites else '?' for pid in order[:4]]
        print(' sprite names first4:', names)


if __name__ == '__main__':
    for p, lab in [('/workspace/work/fight3040.plain', '官方 3040'),
                   ('/workspace/patch_v1.1.34/assets/aa/Android/fight3041_assets_all_6b19939c69def5b7c66c3cc84ce44beb.bundle', '当前 v1.1.34')]:
        try:
            show(load(p), lab)
        except Exception as e:
            print('ERR', lab, e)
