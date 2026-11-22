import sys
sys.path.insert(0, '/workspace/tools')
import UnityPy

UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'


def main(plain, root_name, maxdepth=10):
    objs = {o.path_id: o for o in UnityPy.load(plain).objects}
    go = {}
    rt = {}
    for pid, o in objs.items():
        if o.type.name == 'GameObject':
            go[pid] = o.read_typetree()
        elif o.type.name in ('RectTransform', 'Transform'):
            rt[pid] = o.read_typetree()
    go2tr = {t['m_GameObject']['m_PathID']: pid for pid, t in rt.items()}

    def sprite_name(pid):
        o = objs.get(pid)
        try:
            return o.read().m_Name
        except Exception:
            return None

    def img_info(g):
        for c in g['m_Component']:
            o = objs.get(c['component']['m_PathID'])
            if o is None or o.type.name != 'MonoBehaviour':
                continue
            try:
                tt = o.read_typetree()
            except Exception:
                continue
            if 'm_Sprite' in tt or 'm_PreserveAspect' in tt:
                sp = tt['m_Sprite']['m_PathID'] if tt.get('m_Sprite') else 0
                nm = sprite_name(sp) if sp else None
                if nm and sp in objs:
                    try:
                        s = objs[sp].read()
                        nm = '%s[%d,%d]' % (nm, round(s.m_Rect.width), round(s.m_Rect.height))
                    except Exception:
                        pass
                return dict(sprite=nm, preserveAspect=tt.get('m_PreserveAspect'), type=tt.get('m_Type'))
        return None

    def walk(tpid, d):
        t = rt.get(tpid)
        if t is None or d > maxdepth:
            return
        g = go.get(t['m_GameObject']['m_PathID'])
        if g is None:
            return
        sd = t.get('m_SizeDelta', {})
        ap = t.get('m_AnchoredPosition', {})
        print('  ' * d + '%s size=(%.1f,%.1f) pos=(%.1f,%.1f) sc=%s img=%s' % (
            g['m_Name'], sd.get('x', 0), sd.get('y', 0), ap.get('x', 0), ap.get('y', 0),
            t.get('m_LocalScale', {}).get('x'), img_info(g)))
        for ch in t.get('m_Children', []):
            walk(ch['m_PathID'], d + 1)

    for pid, t in rt.items():
        g = go.get(t['m_GameObject']['m_PathID'])
        if g and g['m_Name'] == root_name:
            walk(pid, 0)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 10)
