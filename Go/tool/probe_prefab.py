import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
env = UnityPy.load('/tmp/fight.plain')
objs = {o.path_id: o for o in env.objects}
trs = {o.path_id: o.read() for o in env.objects if o.type.name in ('RectTransform', 'Transform')}
spr = {}
for o in env.objects:
    if o.type.name == 'Sprite':
        spr[o.path_id] = o.read().m_Name


def path(pid):
    parts = []
    t = trs[pid]
    while True:
        parts.append(objs[t.m_GameObject.path_id].read().m_Name)
        f = t.m_Father.path_id if t.m_Father else 0
        if not f:
            break
        t = trs[f]
    return ' > '.join(reversed(parts))


rows = []
for o in env.objects:
    if o.type.name != 'GameObject':
        continue
    d = o.read()
    tr = [c.path_id for c in d.m_Components if objs[c.path_id].type.name == 'RectTransform']
    if not tr:
        continue
    for c in d.m_Components:
        ot = objs[c.path_id]
        if ot.type.name != 'MonoBehaviour':
            continue
        try:
            cls = ot.read().m_Script.read().m_ClassName
        except Exception:
            continue
        if cls not in ('Image', 'RawImage', 'UniSwfGraphic', 'MaskableGraphic'):
            continue
        tt = ot.read_typetree()
        r = trs[tr[0]]
        rows.append((d.m_Name, cls, spr.get(tt.get('m_Sprite', {}).get('m_PathID', 0)) if isinstance(tt.get('m_Sprite'), dict) else None,
                     round(r.m_SizeDelta.x, 1), round(r.m_SizeDelta.y, 1), path(tr[0])))
for r in rows:
    if 'type' in r[0].lower() or 'Type' in r[5]:
        print(r)
