import sys, os, re
sys.path.insert(0, '/workspace/tools')
import UnityPy
import seer

UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'


def load_plain(bundle, tag):
    p = '/workspace/work/build10/%s.plain' % tag
    os.makedirs('/workspace/work/build10', exist_ok=True)
    if not os.path.exists(p):
        plain, _ = seer.decrypt(bundle)
        open(p, 'wb').write(plain)
    return UnityPy.load(p)


def dump(env, pat):
    objs = {o.path_id: o for o in env.objects}
    go = {}
    rt = {}
    for pid, o in objs.items():
        if o.type.name == 'GameObject':
            go[pid] = o.read_typetree()
        elif o.type.name in ('RectTransform', 'Transform'):
            rt[pid] = o.read_typetree()
    go2tr = {}
    for pid, t in rt.items():
        go2tr[t['m_GameObject']['m_PathID']] = pid
    rx = re.compile(pat, re.I)

    def sprite_of(g):
        for c in g['m_Component']:
            pid = c['component']['m_PathID']
            o = objs.get(pid)
            if o is None or o.type.name != 'MonoBehaviour':
                continue
            try:
                tt = o.read_typetree()
            except Exception:
                continue
            if 'm_Sprite' in tt:
                sp = tt['m_Sprite']['m_PathID'] if tt.get('m_Sprite') else 0
                nm = None
                if sp:
                    so = objs.get(sp)
                    try:
                        nm = so.read().m_Name
                    except Exception:
                        nm = '?'
                return {'sprite': nm, 'preserveAspect': tt.get('m_PreserveAspect'),
                        'type': tt.get('m_Type')}
        return None

    def walk(pid, prefix, depth=0):
        t = rt.get(pid)
        if t is None:
            return
        g = go.get(t['m_GameObject']['m_PathID'])
        if g is None:
            return
        name = g['m_Name']
        p = prefix + '/' + name
        if rx.search(name):
            sd = t.get('m_SizeDelta', {})
            ap = t.get('m_AnchoredPosition', {})
            sc = t.get('m_LocalScale', {})
            print(f'{p}\n    size=({sd.get("x")},{sd.get("y")}) pos=({ap.get("x")},{ap.get("y")}) scale=({sc.get("x")},{sc.get("y")}) img={sprite_of(g)}')
        if depth < 40:
            for ch in t['m_Children']:
                walk(ch['m_PathID'], p, depth + 1)

    for pid, t in rt.items():
        if t['m_Father']['m_PathID'] == 0:
            walk(pid, '')


if __name__ == '__main__':
    bundle, pat = sys.argv[1], sys.argv[2]
    tag = os.path.basename(bundle).split('_')[0]
    dump(load_plain(bundle, tag), pat)
