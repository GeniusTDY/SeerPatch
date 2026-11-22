import os, sys, shutil
sys.path.insert(0, '/workspace/tools')
from PIL import Image
import UnityPy
from UnityPy.export import Texture2DConverter
import seer

UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
SRC = '/workspace/work/v7/assets/aa/Android'
WORK = '/workspace/work/build10'
OUT = '/workspace/work/out10'
V9 = '/workspace/work/out9'
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


def save_bundle(bf, salt, name):
    data = bf.save(packer='lz4')
    out = os.path.join(OUT, name)
    open(out, 'wb').write(seer.encrypt(data, salt))
    print('OUT', name, len(data), os.path.getsize(out))


def go_name(objs, t):
    o = objs.get(t['m_GameObject']['m_PathID'])
    return o.read().m_Name if o else ''


def main():
    # 1) fight 3577: keep 94% (needed to re-centre horizontally) but move down 4px
    env, bf, salt = open_bundle(os.path.join(SRC, FIGHT), 'fight')
    art = find_sprite(env, '3577').image.convert('RGBA')
    small = art.resize((int(round(art.width * 0.94)), int(round(art.height * 0.94))), Image.LANCZOS)
    canvas = Image.new('RGBA', art.size, (0, 0, 0, 0))
    canvas.alpha_composite(small, (8, 6))
    bb = canvas.getchannel('A').getbbox()
    print('fight 3577 new bbox', bb, 'center y', (bb[1] + bb[3]) / 2)
    replace_sprite(env, bf, '3577', canvas)
    save_bundle(bf, salt, FIGHT)

    # 2) uimain: pet detail art down 12px
    env, bf, salt = open_bundle(os.path.join(SRC, UIMAIN), 'uimain')
    objs = {o.path_id: o for o in env.objects}
    n = 0
    for o in env.objects:
        if o.type.name != 'RectTransform':
            continue
        t = o.read_typetree()
        if go_name(objs, t) != 'petIcon':
            continue
        # path check: walk up to confirm it sits in UIPetInfoView/root/middle/root
        pid = o.path_id
        chain = []
        cur = t
        for _ in range(6):
            f = cur['m_Father']['m_PathID']
            if not f:
                break
            fo = objs.get(f)
            if fo is None:
                break
            cur = fo.read_typetree()
            chain.append(go_name(objs, cur))
        if 'middle' not in chain:
            continue
        t['m_AnchoredPosition']['y'] -= 12.0
        o.save_typetree(t)
        n += 1
        print('  petIcon ->', chain[:4], t['m_AnchoredPosition'])
    print('petIcon edited', n)
    save_bundle(bf, salt, UIMAIN)

    for n in (PETICON, PETSTORAGE, PETTYPEBIG):
        shutil.copyfile(os.path.join(V9, n), os.path.join(OUT, n))
        print('COPY', n, os.path.getsize(os.path.join(OUT, n)))


if __name__ == '__main__':
    main()
