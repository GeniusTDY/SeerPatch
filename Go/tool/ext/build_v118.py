import os, sys, shutil
sys.path.insert(0, '/workspace/tools')
from PIL import Image
import UnityPy
from UnityPy.export import Texture2DConverter
import seer

UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
SRC = '/workspace/work/v7/assets/aa/Android'
WORK = '/workspace/work/build8'
OUT = '/workspace/work/out8'
ART_FIGHT = '/workspace/work/fight3577_v7.png'
os.makedirs(WORK, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

PETICON = 'peticon_assets_all_051ca4e72be71ecbb6da4b41b3d7a753.bundle'
FIGHT = 'fight_assets_all_c32312b91be3884937546802bfa190c8.bundle'
PETTYPEBIG = 'pettypebig_assets_all_0eb3e7bdd008cc4dbfe3ad98711c92fc.bundle'
UIMAIN = 'uimain_assets_all_e0739de25e91db3ed1d223191202ae3c.bundle'
PETSTORAGE = 'petstorage_assets_all_fabfa71a1ffb344bd3e0c2574efdade4.bundle'
STORAGE_ENC = '/workspace/work/petstorage.enc'


def open_bundle(path, tag):
    raw = open(path, 'rb').read()
    plain, salt = seer.decrypt(path)
    p = os.path.join(WORK, tag + '.plain')
    open(p, 'wb').write(plain)
    env = UnityPy.load(p)
    bf = env.files[list(env.files.keys())[0]]
    return env, bf, salt


def find_sprite(env, name):
    for o in env.objects:
        if o.type.name == 'Sprite' and o.read().m_Name == name:
            return o.read()
    raise KeyError(name)


def replace_sprite(env, bf, name, canvas):
    s = find_sprite(env, name)
    rd = s.m_RD if not s.m_SpriteAtlas else next(v for k, v in s.m_SpriteAtlas.read().m_RenderDataMap if k == s.m_RenderDataKey)
    tr = rd.textureRect
    x, y, w, h = int(tr.x), int(tr.y), int(tr.width), int(tr.height)
    assert canvas.size == (w, h), (canvas.size, (w, h))
    tex = rd.texture.read()
    sd = tex.m_StreamData
    res = sd.path.rsplit('/', 1)[-1]
    img = tex.image.convert('RGBA')
    img.paste(canvas, (x, img.height - y - h, x + w, img.height - y))
    page, _ = Texture2DConverter.image_to_texture2d(img, tex.m_TextureFormat)
    old = bf.files[res]
    raw = bytearray(old.bytes)
    assert len(page) == int(sd.size)
    raw[int(sd.offset):int(sd.offset) + int(sd.size)] = page
    from UnityPy.streams import EndianBinaryReader
    nr = EndianBinaryReader(bytes(raw)); nr.flags = old.flags
    bf.files[res] = nr


def go_name_of(objs, t):
    o = objs.get(t['m_GameObject']['m_PathID'])
    return o.read().m_Name if o else ''


def full_path(rts, objs, pid, depth=0, cache={}):
    o = rts.get(pid)
    if o is None or depth > 20:
        return ''
    if pid not in cache:
        cache[pid] = o.read_typetree()
    t = cache[pid]
    f = t['m_Father']['m_PathID']
    return (full_path(rts, objs, f, depth + 1) + '/' if f else '') + go_name_of(objs, t)


def edit_uimain(env, bf):
    objs = {o.path_id: o for o in env.objects}
    rts = {o.path_id: o for o in env.objects if o.type.name == 'RectTransform'}
    n = 0
    for pid, o in rts.items():
        t = o.read_typetree()
        nm = go_name_of(objs, t)
        if nm != 'petImg':
            continue
        path = full_path(rts, objs, pid)
        if 'bgRoot' not in path:
            continue
        sd = t['m_SizeDelta']
        if abs(sd['x'] - 86) > 0.5 or abs(sd['y'] - 88) > 0.5:
            continue
        t['m_AnchoredPosition']['y'] += 6.0
        o.save_typetree(t)
        n += 1
        print('  bag petImg', path, '-> y', t['m_AnchoredPosition']['y'])
    print('uimain petImg edited', n)


def edit_storage(env, bf):
    objs = {o.path_id: o for o in env.objects}
    n = 0
    for o in env.objects:
        if o.type.name != 'RectTransform':
            continue
        t = o.read_typetree()
        sd = t.get('m_SizeDelta', {})
        sc = t.get('m_LocalScale', {}).get('x', 1)
        if abs(sd.get('x', 0) - 121) < 0.5 and abs(sd.get('y', 0) - 118) < 0.5 and abs(sc - 0.5263) < 0.01:
            t['m_LocalScale']['x'] = 0.85
            t['m_LocalScale']['y'] = 0.85
            o.save_typetree(t)
            n += 1
    print('storage avatar nodes edited', n)


def save_bundle(bf, salt, name):
    data = bf.save(packer='lz4')
    out = os.path.join(OUT, name)
    open(out, 'wb').write(seer.encrypt(data, salt))
    print('OUT', name, len(data), os.path.getsize(out))


def main():
    # fight: re-center + slight shrink of portrait art
    env, bf, salt = open_bundle(os.path.join(SRC, FIGHT), 'fight')
    art = Image.open(ART_FIGHT).convert('RGBA')
    small = art.resize((int(round(art.width * 0.94)), int(round(art.height * 0.94)), ), Image.LANCZOS)
    canvas = Image.new('RGBA', art.size, (0, 0, 0, 0))
    canvas.alpha_composite(small, (8, 2))
    replace_sprite(env, bf, '3577', canvas)
    save_bundle(bf, salt, FIGHT)

    # uimain: bag previews up
    env, bf, salt = open_bundle(os.path.join(SRC, UIMAIN), 'uimain')
    edit_uimain(env, bf)
    save_bundle(bf, salt, UIMAIN)

    # petstorage: fill cells
    env, bf, salt = open_bundle(STORAGE_ENC, 'petstorage')
    edit_storage(env, bf)
    save_bundle(bf, salt, PETSTORAGE)

    for n in (PETICON, PETTYPEBIG):
        shutil.copyfile(os.path.join(SRC, n), os.path.join(OUT, n))
        print('COPY', n, os.path.getsize(os.path.join(OUT, n)))


if __name__ == '__main__':
    main()
