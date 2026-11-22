#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.1.36 一致性校验：攻击贴图/trim 不得变化，只有时序变化；待机重新生成。"""
import sys, json, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
sys.path.insert(0, '/workspace/work')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'

OLD = '/workspace/work/fight3041_v1135.plain'
NEW = '/workspace/work/fight3041_v1136.plain'


def load(path):
    env = UnityPy.load(open(path, 'rb').read())
    bf = env.files[list(env.files.keys())[0]]
    sf = bf.files[[k for k in bf.files if not k.endswith('.resS')][0]]
    by = {o.path_id: o for o in sf.objects.values()}
    clips = {o.read().m_Name: o for o in sf.objects.values() if o.type.name == 'AnimationClip'}
    trims = {}
    for o in sf.objects.values():
        if o.type.name == 'TextAsset':
            t = o.read_typetree()
            if t['m_Name'].endswith('.trim'):
                trims[t['m_Name'][:-5]] = json.loads(t['m_Script'].lstrip('\ufeff'))
    return by, clips, trims


def main():
    bo, co, to = load(OLD)
    bn, cn, tn = load(NEW)
    assert len(bo) == len(bn), (len(bo), len(bn))
    assert sorted(bo) == sorted(bn), 'object ids changed'
    print('objects', len(bo), 'ids identical, count identical')
    fails = []
    for p in (1, 2, 3):
        for k in (1, 2, 3, 4):
            nm = '304%d_%d' % (p, k)
            do, dn = co[nm].read_typetree(), cn[nm].read_typetree()
            oo = [x['m_PathID'] for x in do['m_ClipBindingConstant']['pptrCurveMapping']]
            on = [x['m_PathID'] for x in dn['m_ClipBindingConstant']['pptrCurveMapping']]
            if oo != on:
                fails.append((nm, 'pptr map changed'))
            so = [(int(bo[i].read_typetree()['m_Rect']['width']),
                   int(bo[i].read_typetree()['m_Rect']['height'])) for i in oo]
            sn = [(int(bn[i].read_typetree()['m_Rect']['width']),
                   int(bn[i].read_typetree()['m_Rect']['height'])) for i in on]
            if so != sn:
                fails.append((nm, 'sprite sizes changed'))
            tro = [(f['trimX'], f['trimY'], f['trimW'], f['trimH']) for f in to[nm]['frames']]
            trn = [(f['trimX'], f['trimY'], f['trimW'], f['trimH']) for f in tn[nm]['frames']]
            if tro != trn and k != 1:
                fails.append((nm, 'trim changed'))
            for f, s in zip(tn[nm]['frames'], sn):
                if (int(f['trimW']), int(f['trimH'])) != s:
                    fails.append((nm, 'trim!=sprite', f['trimW'], f['trimH'], s))
            print('  %s  old %g/%.3fs -> new %g/%.3fs  frames %d  trim %d  first %dx%d'
                  % (nm, do['m_SampleRate'], do['m_MuscleClip']['m_StopTime'],
                     dn['m_SampleRate'], dn['m_MuscleClip']['m_StopTime'],
                     len(on), len(tn[nm]['frames']), sn[0][0], sn[0][1]))
    # 待机画布与 trim
    for pet in ('3042', '3043'):
        nm = pet + '_1'
        sz = {(int(bn[i].read_typetree()['m_Rect']['width']),
               int(bn[i].read_typetree()['m_Rect']['height']))
              for i in [x['m_PathID'] for x in cn[nm].read_typetree()['m_ClipBindingConstant']['pptrCurveMapping']]}
        print('  %s idle canvas %s trim %s' % (nm, sz,
              {(f['sourceW'], f['sourceH'], f['trimW'], f['trimH']) for f in tn[nm]['frames']}))
    # 攻击时长跨精灵一致性
    durs = {(co['304%d_%d' % (p, k)].read_typetree()['m_ClipBindingConstant'] is not None,
             k): cn['304%d_%d' % (p, k)].read_typetree()['m_MuscleClip']['m_StopTime']
            for p in (1, 2, 3) for k in (2, 3, 4)}
    for k in (2, 3, 4):
        vals = [durs[(True, k)]]
        names = ['304%d_%d' % (p, k) for p in (1, 2, 3)]
        vals = [cn[n].read_typetree()['m_MuscleClip']['m_StopTime'] for n in names]
        if max(vals) - min(vals) > 1e-4:
            fails.append(('duration', k, vals))
    # 贴图像素：攻击必须完全一致
    for p in (1, 2, 3):
        for k in (2, 3, 4):
            nm = '304%d_%d' % (p, k)
            for i in [x['m_PathID'] for x in cn[nm].read_typetree()['m_ClipBindingConstant']['pptrCurveMapping']][::7]:
                st = bn[i].read_typetree()
                tid = st['m_RD']['texture']['m_PathID']
                if bo[tid].read().image.tobytes() != bn[tid].read().image.tobytes():
                    fails.append((nm, 'attack texture changed', i))
                    break
    print('FAILS', len(fails))
    for f in fails[:20]:
        print('  ', f)


if __name__ == '__main__':
    main()
