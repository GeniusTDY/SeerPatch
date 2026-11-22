import os, sys, shutil
sys.path.insert(0, '/workspace/tools')
import UnityPy
import seer

UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
SRC = '/workspace/work/v7/assets/aa/Android'
WORK = '/workspace/work/build11'
OUT = '/workspace/work/out11'
V10 = '/workspace/work/out10'
os.makedirs(WORK, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

PETICON = 'peticon_assets_all_051ca4e72be71ecbb6da4b41b3d7a753.bundle'
FIGHT = 'fight_assets_all_c32312b91be3884937546802bfa190c8.bundle'
PETTYPEBIG = 'pettypebig_assets_all_0eb3e7bdd008cc4dbfe3ad98711c92fc.bundle'
UIMAIN = 'uimain_assets_all_e0739de25e91db3ed1d223191202ae3c.bundle'
PETSTORAGE = 'petstorage_assets_all_fabfa71a1ffb344bd3e0c2574efdade4.bundle'


def open_bundle(path, tag):
    plain, salt = seer.decrypt(path)
    p = os.path.join(WORK, tag + '.plain')
    open(p, 'wb').write(plain)
    env = UnityPy.load(p)
    bf = env.files[list(env.files.keys())[0]]
    return env, bf, salt


def index(env):
    objs = {o.path_id: o for o in env.objects}
    go, rt = {}, {}
    for pid, o in objs.items():
        if o.type.name == 'GameObject':
            go[pid] = o.read_typetree()
        elif o.type.name in ('RectTransform', 'Transform'):
            rt[pid] = o.read_typetree()
    return objs, go, rt


def gname(rt, go, pid):
    t = rt.get(pid)
    if not t:
        return '?'
    o = go.get(t['m_GameObject']['m_PathID'])
    return o['m_Name'] if o else '?'


def chain(rt, go, pid, n=8):
    out, cur = [], pid
    for _ in range(n):
        t = rt.get(cur)
        if not t:
            break
        out.append(gname(rt, go, cur))
        f = t['m_Father']['m_PathID']
        if not f:
            break
        cur = f
    return out


def save_bundle(bf, salt, name):
    data = bf.save(packer='lz4')
    out = os.path.join(OUT, name)
    open(out, 'wb').write(seer.encrypt(data, salt))
    print('OUT', name, len(data), os.path.getsize(out))


def main():
    # detail art (bag right panel): move down 15 units
    env, bf, salt = open_bundle(os.path.join(SRC, UIMAIN), 'uimain')
    objs, go, rt = index(env)
    n = 0
    for pid, o in list(objs.items()):
        if o.type.name != 'RectTransform':
            continue
        t = o.read_typetree()
        if gname(rt, go, pid) != 'petIcon':
            continue
        ch = chain(rt, go, pid, 8)
        if 'petInfoPage' in ch and 'UISeerBgRoot' in ch:
            t['m_AnchoredPosition']['y'] -= 15.0
            o.save_typetree(t)
            n += 1
            print('  detail petIcon', ch[:5], t['m_AnchoredPosition'])
    print('detail nodes edited', n)
    save_bundle(bf, salt, UIMAIN)

    # skill card art: enlarge petImg under PetBottomItem (no crop, keep aspect ratio of node)
    env, bf, salt = open_bundle(os.path.join(V10, FIGHT), 'fight')
    objs, go, rt = index(env)
    m = 0
    for pid, o in list(objs.items()):
        if o.type.name != 'RectTransform':
            continue
        t = o.read_typetree()
        if gname(rt, go, pid) != 'petImg':
            continue
        ch = chain(rt, go, pid, 8)
        if not any(c.startswith('PetBottomItem') for c in ch):
            continue
        sd = t['m_SizeDelta']
        sd['x'] = round(sd['x'] * 1.35, 2)
        sd['y'] = round(sd['y'] * 1.35, 2)
        o.save_typetree(t)
        m += 1
        print('  skill petImg', ch[:4], sd)
    print('skill nodes edited', m)
    save_bundle(bf, salt, FIGHT)

    for nm in (PETICON, PETSTORAGE, PETTYPEBIG):
        shutil.copyfile(os.path.join(V10, nm), os.path.join(OUT, nm))
        print('COPY', nm, os.path.getsize(os.path.join(OUT, nm)))


if __name__ == '__main__':
    main()
