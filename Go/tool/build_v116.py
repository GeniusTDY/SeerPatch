import os, sys, shutil
sys.path.insert(0, '/workspace/tools')
from PIL import Image
import UnityPy
from UnityPy.export import Texture2DConverter
import seer

UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'

# v1.1.4 bundles are the baseline: they contain the good changes
# (clear pettypebig 223 icon, name-row Type icon enlarged, extra pet sprites).
SRC = '/tmp/v114p/assets/aa/Android'
WORK = '/tmp/b6work'
OUT = '/tmp/out6'
os.makedirs(WORK, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

BAG_ART = '/tmp/fr2/154_49.png'    # wings-spread pose, complete figure
FIGHT_ART = '/tmp/fr2/154_49.png'  # same pose, complete figure (no crop)

PETICON = SRC + '/peticon_assets_all_051ca4e72be71ecbb6da4b41b3d7a753.bundle'
FIGHT = SRC + '/fight_assets_all_c32312b91be3884937546802bfa190c8.bundle'
PETTYPEBIG = SRC + '/pettypebig_assets_all_0eb3e7bdd008cc4dbfe3ad98711c92fc.bundle'
UIMAIN = SRC + '/uimain_assets_all_e0739de25e91db3ed1d223191202ae3c.bundle'


def open_bundle(enc_path, tag):
    plain, salt = seer.decrypt(enc_path)
    p = os.path.join(WORK, tag + '.plain')
    open(p, 'wb').write(plain)
    env = UnityPy.load(p)
    bf = env.files[list(env.files.keys())[0]]
    return env, bf, salt, p


def canvas_fit(w, h, art_path, thr=8):
    """Fit the art inside w*h without cropping, aspect preserved, centered."""
    art = Image.open(art_path).convert('RGBA')
    a = art.getchannel('A').point(lambda v: 255 if v >= thr else 0)
    bb = a.getbbox()
    if bb and (bb[2] - bb[0]) * (bb[3] - bb[1]) < art.width * art.height * 0.92:
        art = art.crop(bb)
    sc = min(w / art.width, h / art.height)
    nw, nh = max(1, int(round(art.width * sc))), max(1, int(round(art.height * sc)))
    art2 = art.resize((nw, nh), Image.LANCZOS)
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    out.alpha_composite(art2, ((w - nw) // 2, (h - nh) // 2))
    return out, (nw, nh)


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
    print('sprite replaced', name, (x, y, w, h), '->', tex.m_Name)


def is_image(objs, obj):
    for c in obj.m_Components:
        ot = objs.get(c.path_id)
        if ot is not None and ot.type.name == 'MonoBehaviour':
            try:
                if ot.read().m_Script.read().m_ClassName == 'Image':
                    return True
            except Exception:
                pass
    return False


def edit_rects(env, rules):
    objs = {o.path_id: o for o in env.objects}
    hit = {}
    for o in env.objects:
        if o.type.name != 'GameObject':
            continue
        g = o.read()
        rule = rules.get(g.m_Name)
        if rule is None or not is_image(objs, g):
            continue
        for c in g.m_Components:
            ot = objs.get(c.path_id)
            if ot is not None and ot.type.name == 'RectTransform':
                t = ot.read_typetree()
                sd = t['m_SizeDelta']
                f = rule.get('factor', 1.0)
                sd['x'] = round(sd['x'] * f if rule.get('w') is None else rule['w'], 2)
                sd['y'] = round(sd['y'] * f if rule.get('h') is None else rule['h'], 2)
                t['m_AnchoredPosition']['x'] = round(t['m_AnchoredPosition']['x'] + rule.get('dx', 0), 2)
                ot.save_typetree(t)
                hit[g.m_Name] = hit.get(g.m_Name, 0) + 1
    print('rect edits', hit)


def save_bundle(bf, salt, out, tag):
    data = bf.save(packer='lz4')
    open(out, 'wb').write(seer.encrypt(data, salt))
    print('OUT', tag, len(data), os.path.getsize(out))


def main():
    # 1. peticon: restore wings-spread bag pose, complete figure, as large as possible
    env, bf, salt, _ = open_bundle(PETICON, 'peticon')
    bag, size = canvas_fit(145, 183, BAG_ART)
    bag.save('/tmp/out6/preview_bag_145x183.png')
    print('bag content', size, 'of 145x183')
    replace_sprite(env, bf, '3577', bag)
    save_bundle(bf, salt, os.path.join(OUT, 'peticon.bundle'), 'peticon')

    # 2. fight: complete figure, no cropping (user choice: slightly small but whole)
    env, bf, salt, _ = open_bundle(FIGHT, 'fight')
    fight, size = canvas_fit(127, 191, FIGHT_ART)
    fight.save('/tmp/out6/preview_fight_127x191.png')
    print('fight content', size, 'of 127x191')
    replace_sprite(env, bf, '3577', fight)
    save_bundle(bf, salt, os.path.join(OUT, 'fight.bundle'), 'fight')

    # 3. pettypebig: copy v1.1.4 as-is (restores the crisp 223 deity icon)
    shutil.copyfile(PETTYPEBIG, os.path.join(OUT, 'pettypebig.bundle'))
    print('pettypebig copied', os.path.getsize(os.path.join(OUT, 'pettypebig.bundle')))

    # 4. uimain: bag left-list preview node bigger (v1.1.5 size was fine)
    env, bf, salt, _ = open_bundle(UIMAIN, 'uimain')
    edit_rects(env, {'petImg': {'w': 86, 'h': 88}})
    save_bundle(bf, salt, os.path.join(OUT, 'uimain.bundle'), 'uimain')


if __name__ == '__main__':
    main()
