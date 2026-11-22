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
go = {}
for o in objs:
    if o.type.name == 'GameObject':
        go[o.path_id] = o.read_typetree()
rt = {}
for o in objs:
    if o.type.name == 'RectTransform':
        rt[o.path_id] = o.read_typetree()
crid = {}
for o in objs:
    if o.type.name == 'CanvasRenderer':
        crid[o.path_id] = True
imgs = {}
for o in objs:
    if o.type.name == 'MonoBehaviour':
        t = o.read_typetree()
        if t.get('m_Script') and t.get('m_GameObject'):
            imgs[o.path_id] = t
print('MonoScripts:')
for o in objs:
    if o.type.name == 'MonoScript':
        t = o.read_typetree()
        print('   ', t.get('m_Name'), t.get('m_ClassName'), t.get('m_Namespace'))

# build parent->children
children = {}
for pid, t in go.items():
    for c in t.get('m_Component', []):
        pass
byname = {}
for pid, t in go.items():
    byname.setdefault(t['m_Name'], []).append(pid)

def dump(pid, depth=0, maxdepth=4):
    t = go[pid]
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
    print('  ' * depth + '%-30s%s' % (t['m_Name'], s))
    if depth >= maxdepth:
        return
    for c in t.get('m_Component', []):
        cp = c['component']['m_PathID']
        # Transform children: m_Children in Transform
        pass

# Transform children map
tr = {}
for o in objs:
    if o.type.name in ('Transform',):
        tr[o.path_id] = o

# use RectTransform m_Children and parent
kids = {}
roots = []
for pid, t in rt.items():
    p = t.get('m_Father', {}).get('m_PathID', 0)
    kids.setdefault(p, []).append(pid)
    if p not in rt:
        roots.append(pid)
all_pid = set(rt)

def walk(pid, depth):
    t = rt[pid]
    gopid = t['m_GameObject']['m_PathID']
    nm = go[gopid]['m_Name']
    if any(k in nm for k in ('pet', 'Pet', 'enemy', 'Enemy', 'statue', 'Statue', 'ani', 'Ani')):
        sd = t['m_SizeDelta']
        print('  '*depth + '%-26s size=(%.1f,%.1f) pivot=(%.2f,%.2f) pos=(%.1f,%.1f)' % (
            nm, sd['x'], sd['y'], t['m_Pivot']['x'], t['m_Pivot']['y'],
            t['m_AnchoredPosition']['x'], t['m_AnchoredPosition']['y']))
    for k in kids.get(pid, []):
        walk(k, depth + 1)

print('---- hierarchy filtered ----')
for r in roots:
    walk(r, 0)
