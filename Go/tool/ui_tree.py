import sys, re
sys.path.insert(0, '/workspace/tools')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2021.3.16f1'


def load(path):
    env = UnityPy.load(path)
    objs = {}
    for o in env.objects:
        objs[o.path_id] = o
    return env, objs


def tree(path, pat, maxdepth=40):
    env, objs = load(path)
    go = {}
    rt = {}
    for pid, o in objs.items():
        if o.type.name == 'GameObject':
            go[pid] = o.read_typetree()
        elif o.type.name in ('RectTransform', 'Transform'):
            rt[pid] = o.read_typetree()
    # gameobject -> transform
    go2tr = {}
    for pid, t in rt.items():
        gid = t['m_GameObject']['m_PathID']
        go2tr[gid] = pid
    rx = re.compile(pat, re.I)

    def sprite_name(pid):
        o = objs.get(pid)
        if o is None:
            return None
        try:
            return o.read().m_Name
        except Exception:
            return None

    def image_info(go_tree):
        for c in go_tree['m_Component']:
            pid = c['component']['m_PathID']
            o = objs.get(pid)
            if o is None or o.type.name != 'MonoBehaviour':
                continue
            try:
                tt = o.read_typetree()
            except Exception:
                continue
            if 'm_Sprite' in tt or 'm_PreserveAspect' in tt:
                sp = tt['m_Sprite']['m_PathID'] if tt.get('m_Sprite') else 0
                return {
                    'sprite_pid': sp,
                    'sprite': sprite_name(sp) if sp else None,
                    'preserveAspect': tt.get('m_PreserveAspect'),
                    'type': tt.get('m_Type'),
                    'raycast': tt.get('m_RaycastTarget'),
                }
        return None

    def walk(tpid, prefix, depth=0):
        t = rt.get(tpid)
        if t is None:
            return
        gid = t['m_GameObject']['m_PathID']
        g = go.get(gid)
        if g is None:
            return
        name = g['m_Name']
        p = prefix + '/' + name
        if rx.search(name):
            sd = t.get('m_SizeDelta', {})
            ap = t.get('m_AnchoredPosition', {})
            am = t.get('m_AnchorMin', {})
            ax = t.get('m_AnchorMax', {})
            im = image_info(g)
            print(f'{p}\n    size=({sd.get("x")},{sd.get("y")}) anchorMin=({am.get("x")},{am.get("y")}) anchorMax=({ax.get("x")},{ax.get("y")}) pos=({ap.get("x")},{ap.get("y")}) img={im}')
        if depth < maxdepth:
            for ch in t['m_Children']:
                walk(ch['m_PathID'], p, depth + 1)

    seen = 0
    for pid, t in rt.items():
        if t['m_Father']['m_PathID'] == 0:
            walk(pid, '')
            seen += 1
    print('roots', seen)


if __name__ == '__main__':
    tree(sys.argv[1], sys.argv[2])
