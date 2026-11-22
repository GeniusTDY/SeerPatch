import os, sys, shutil
sys.path.insert(0, '/workspace/tools')
from PIL import Image
import UnityPy
from UnityPy.export import Texture2DConverter
import seer

UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
SRC = '/tmp/b7/v6/assets/aa/Android'
WORK = '/tmp/b7/work'
OUT = '/tmp/b7/out7'
ART = '/tmp/art7/r1xsqf2nestfyp90edb7ad3xmj7b2dv.png'
os.makedirs(WORK, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

PETICON = 'peticon_assets_all_051ca4e72be71ecbb6da4b41b3d7a753.bundle'
FIGHT = 'fight_assets_all_c32312b91be3884937546802bfa190c8.bundle'
PETTYPEBIG = 'pettypebig_assets_all_0eb3e7bdd008cc4dbfe3ad98711c92fc.bundle'
UIMAIN = 'uimain_assets_all_e0739de25e91db3ed1d223191202ae3c.bundle'


def open_bundle(enc_path, tag):
    plain, salt = seer.decrypt(enc_path)
    p = os.path.join(WORK, tag + '.plain')
    open(p, 'wb').write(plain)
    env = UnityPy.load(p)
    bf = env.files[list(env.files.keys())[0]]
    return env, bf, salt


def canvas_fit(w, h):
    """Whole art scaled to fit w*h, aspect preserved, centered. No cropping."""
    art = Image.open(ART).convert('RGBA')
    sc = min(w / art.width, h / art.height)
    nw, nh = max(1, int(round(art.width * sc))), max(1, int(round(art.height * sc)))
    art2 = art.resize((nw, nh), Image.LANCZOS)
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    out.alpha_composite(art2, ((w - nw) // 2, (h - nh) // 2))
    print('fit', (w, h), 'art', art.size, '->', (nw, nh))
    return out


def find_sprite(env, name):
    for o in env.objects:
        if o.type.name == 'Sprite' and o.read().m_Name == name:
            return o.read()
    raise KeyError(name)


def replace_sprite(env, bf, name, canvas):
    s = find_sprite(env, name)
    if s.m_SpriteAtlas:
        atlas = s.m_SpriteAtlas.read()
        rd = next(v for k, v in atlas.m_RenderDataMap if k == s.m_RenderDataKey)
    else:
        rd = s.m_RD
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
    print('replaced sprite', name, (x, y, w, h), '->', tex.m_Name)


def save_bundle(bf, salt, out, tag):
    data = bf.save(packer='lz4')
    open(out, 'wb').write(seer.encrypt(data, salt))
    print('OUT', tag, len(data), os.path.getsize(out))


def main():
    # bag preview
    env, bf, salt = open_bundle(os.path.join(SRC, PETICON), 'peticon')
    replace_sprite(env, bf, '3577', canvas_fit(145, 183))
    save_bundle(bf, salt, os.path.join(OUT, PETICON), 'peticon')

    # battle avatar / skill panel
    env, bf, salt = open_bundle(os.path.join(SRC, FIGHT), 'fight')
    replace_sprite(env, bf, '3577', canvas_fit(127, 191))
    save_bundle(bf, salt, os.path.join(OUT, FIGHT), 'fight')

    # untouched
    for n in (PETTYPEBIG, UIMAIN):
        shutil.copyfile(os.path.join(SRC, n), os.path.join(OUT, n))
        print('COPY', n, os.path.getsize(os.path.join(OUT, n)))


if __name__ == '__main__':
    main()
