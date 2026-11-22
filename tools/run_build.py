import os, struct, sys
sys.path.insert(0, '/workspace/tools')
from PIL import Image
import UnityPy
from UnityPy.export import Texture2DConverter
import seer

UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
ART = '/tmp/f3577_frames/16.png'


def canvas_for(w, h, margin=2):
    art = Image.open(ART).convert('RGBA')
    # crop to solid content (ignore faint glow halo)
    a = art.getchannel('A').point(lambda v: 255 if v >= 24 else 0)
    bb = a.getbbox()
    if bb:
        art = art.crop(bb)
    bw = w - 2 * margin
    bh = h - 2 * margin
    sc = min(bw / art.width, bh / art.height)
    nw, nh = max(1, int(art.width * sc)), max(1, int(art.height * sc))
    art2 = art.resize((nw, nh), Image.LANCZOS)
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    out.alpha_composite(art2, ((w - nw) // 2, (h - nh) // 2))
    return out


def find_sprite(env, name):
    for o in env.objects:
        if o.type.name == 'Sprite' and o.read().m_Name == name:
            return o.read()
    raise KeyError(name)


def get_rd(sprite):
    if sprite.m_SpriteAtlas:
        a = sprite.m_SpriteAtlas.read()
        return a, next(v for k, v in a.m_RenderDataMap if k == sprite.m_RenderDataKey)
    return None, sprite.m_RD


def rebuild(base, out, sprite_name, canvas, resize_names=None, factor=1.3, packer='lz4'):
    plain, salt = seer.decrypt(base)
    p = '/tmp/rebuild_plain/' + os.path.basename(base) + '.plain'
    os.makedirs('/tmp/rebuild_plain', exist_ok=True)
    open(p, 'wb').write(plain)
    env = UnityPy.load(p)
    bf = env.files[list(env.files.keys())[0]]
    s = find_sprite(env, sprite_name)
    atlas, rd = get_rd(s)
    tr = rd.textureRect
    x, y, w, h = int(tr.x), int(tr.y), int(tr.width), int(tr.height)
    print('sprite', sprite_name, (x, y, w, h), 'atlas', atlas.m_Name if atlas else None)
    tex = rd.texture.read()
    sd = tex.m_StreamData
    res = sd.path.rsplit('/', 1)[-1]
    print('tex', tex.m_Name, tex.m_Width, tex.m_Height, tex.m_TextureFormat, res, int(sd.offset), int(sd.size))
    assert canvas.size == (w, h), (canvas.size, (w, h))
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

    changed = 0
    if resize_names:
        objs = {o.path_id: o for o in env.objects}
        for o in env.objects:
            if o.type.name != 'GameObject':
                continue
            d = o.read()
            if d.m_Name not in resize_names:
                continue
            has_img = False
            for c in d.m_Components:
                ot = objs[c.path_id]
                if ot.type.name == 'MonoBehaviour':
                    try:
                        if ot.read().m_Script.read().m_ClassName == 'Image':
                            has_img = True
                    except Exception:
                        pass
            if not has_img:
                continue
            for c in d.m_Components:
                ot = objs[c.path_id]
                if ot.type.name == 'RectTransform':
                    t = ot.read_typetree()
                    t['m_SizeDelta']['x'] = round(t['m_SizeDelta']['x'] * factor, 2)
                    t['m_SizeDelta']['y'] = round(t['m_SizeDelta']['y'] * factor, 2)
                    ot.save_typetree(t)
                    changed += 1
        print('resized nodes', changed)

    data = bf.save(packer=packer)
    if packer == 'none':
        data = data[:40] + struct.pack('>I', struct.unpack('>I', data[40:44])[0] | 0x40) + data[44:]
    open(out, 'wb').write(seer.encrypt(data, salt))
    print('OUT', out, len(data), os.path.getsize(out))
    return out


def main():
    os.makedirs('/tmp/out', exist_ok=True)
    # bag portrait (PetIconBig 3577, 145x183)
    peticon = '/tmp/p112/assets/aa/Android/peticon_assets_all_051ca4e72be71ecbb6da4b41b3d7a753.bundle'
    rebuild(peticon, '/tmp/out/peticon.bundle', '3577', canvas_for(145, 183))
    # battle hud/skill avatar (PetFightIcon 3577, 127x191) + enlarge type icons
    fight = '/tmp/fight.enc'
    rebuild(fight, '/tmp/out/fight.bundle', '3577', canvas_for(127, 191),
            resize_names={'Type', 'typeIcon'}, factor=1.3)


if __name__ == '__main__':
    main()
