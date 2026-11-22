import os, struct, sys
sys.path.insert(0, '/workspace/tools')
from PIL import Image
import UnityPy
from UnityPy.export import Texture2DConverter
import seer

UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
ART = '/tmp/f3577_frames/16.png'
WORK = '/tmp/b4work'
os.makedirs(WORK, exist_ok=True)


def open_bundle(enc_path, tag):
    plain, salt = seer.decrypt(enc_path)
    p = os.path.join(WORK, tag + '.plain')
    open(p, 'wb').write(plain)
    env = UnityPy.load(p)
    bf = env.files[list(env.files.keys())[0]]
    return env, bf, salt, p


def canvas_fill(w, h, thr=24, cx=0.5):
    """Render the art to completely fill a w*h rect; cx = horizontal crop center."""
    art = Image.open(ART).convert('RGBA')
    a = art.getchannel('A').point(lambda v: 255 if v >= thr else 0)
    bb = a.getbbox()
    if bb:
        art = art.crop(bb)
    ar = w / h
    if art.width / art.height > ar:
        nw = max(1, int(round(art.height * ar)))
        x0 = max(0, min(art.width - nw, int(art.width * cx) - nw // 2))
        art = art.crop((x0, 0, x0 + nw, art.height))
    else:
        nh = max(1, int(round(art.width / ar)))
        y0 = (art.height - nh) // 2
        art = art.crop((0, y0, art.width, y0 + nh))
    return art.resize((w, h), Image.LANCZOS)


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
    """rules: name -> (new_w or None, new_h or None, x_delta, factor)"""
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
    O = '/tmp/out4'
    os.makedirs(O, exist_ok=True)

    # 1. fight bundle: battle avatar art fill + name-row type icon bigger
    env, bf, salt, _ = open_bundle(
        '/tmp/p113/orig/fight_assets_all_c32312b91be3884937546802bfa190c8.bundle', 'fight')
    replace_sprite(env, bf, '3577', canvas_fill(127, 191, cx=0.62))
    edit_rects(env, {
        'Type': {'w': 120, 'h': 180, 'dx': 23.5},
        'typeIcon': {'factor': 1.3},
    })
    save_bundle(bf, salt, os.path.join(O, 'fight.bundle'), 'fight')

    # 2. uimain bundle: backpack left-list preview bigger
    env, bf, salt, _ = open_bundle(
        '/tmp/p113/uimain_assets_all_e0739de25e91db3ed1d223191202ae3c.bundle', 'uimain')
    edit_rects(env, {'petImg': {'w': 68, 'h': 82}})
    save_bundle(bf, salt, os.path.join(O, 'uimain.bundle'), 'uimain')


if __name__ == '__main__':
    main()
