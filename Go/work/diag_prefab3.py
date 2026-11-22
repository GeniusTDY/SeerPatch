#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
import warnings
warnings.filterwarnings('ignore')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'

env = UnityPy.load('/workspace/work/fight.plain')
objs = list(env.objects)
byid = {o.path_id: o for o in objs}
go = {}
for o in objs:
    if o.type.name == 'GameObject':
        go[o.path_id] = o.read_typetree()
rt = {}
for o in objs:
    if o.type.name == 'RectTransform':
        rt[o.path_id] = o.read_typetree()
kids = {}
for pid, t in rt.items():
    p = t.get('m_Father', {}).get('m_PathID', 0)
    kids.setdefault(p, []).append(pid)

TARGETS = ('playerPet', 'playerPet 2', 'playerPet 3', 'playerPet 4', 'enemy', 'enemy 2', 'enemy 3', 'enemy 4')


def info(gopid, depth=0):
    t = go[gopid]
    rtt = None
    for c in t.get('m_Component', []):
        cp = c['component']['m_PathID']
        if cp in rt:
            rtt = rt[cp]
    s = ''
    if rtt:
        sd = rtt['m_SizeDelta']
        s = ' size=(%.1f,%.1f) pivot=(%.2f,%.2f) pos=(%.1f,%.1f)' % (
            sd['x'], sd['y'], rtt['m_Pivot']['x'], rtt['m_Pivot']['y'],
            rtt['m_AnchoredPosition']['x'], rtt['m_AnchoredPosition']['y'])
    print('  ' * depth + '[%s]%s' % (t['m_Name'], s))
    for c in t.get('m_Component', []):
        cp = c['component']['m_PathID']
        o = byid.get(cp)
        if o is None:
            continue
        tn = o.type.name
        extra = ''
        if tn == 'MonoBehaviour':
            try:
                mt = o.read_typetree()
                extra = ' keys=' + ','.join(k for k in mt.keys() if k != 'm_GameObject')
                ms = mt.get('m_Script', {})
                if ms and ms.get('m_PathID', 0) in byid:
                    mso = byid[ms['m_PathID']]
                    try:
                        st = mso.read_typetree()
                        extra += ' SCRIPT=%s' % st.get('m_ClassName')
                    except Exception:
                        pass
            except Exception as e:
                extra = ' <%s>' % e
        elif tn == 'Image':
            try:
                it = o.read_typetree()
                extra = ' sprite=%s type=%s preserve=%s color.a=%.2f' % (
                    it.get('m_Sprite', {}).get('m_PathID'), it.get('m_Type'),
                    it.get('m_PreserveAspect'), it.get('m_Color', {}).get('a', -1))
            except Exception as e:
                extra = ' <%s>' % e
        print('  ' * (depth + 1) + '<%s>%s' % (tn, extra))
    for ch in kids.get(rtt['m_Children'][0]['m_PathID'] if False else 0, []):
        pass
    # children
    if rtt:
        for c in rtt.get('m_Children', []):
            cp = c['m_PathID']
            if cp in rt:
                info(rt[cp]['m_GameObject']['m_PathID'], depth + 1)


for pid, t in rt.items():
    gopid = t['m_GameObject']['m_PathID']
    nm = go[gopid]['m_Name']
    if nm in TARGETS:
        print('=========', nm)
        info(gopid)
