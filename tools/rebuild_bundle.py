#!/usr/bin/env python3
"""Rebuild a SEERAB01 bundle: replace one atlas sprite's pixels and optionally resize UI nodes."""
import struct, sys, os
import UnityPy
from UnityPy.export import Texture2DConverter
from PIL import Image
import seer

UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'


def find_sprite(env, name):
    for o in env.objects:
        if o.type.name == 'Sprite':
            s = o.read()
            if s.m_Name == name:
                return o, s
    raise KeyError(name)


def get_render_data(env, sprite):
    atlas = sprite.m_SpriteAtlas.read() if sprite.m_SpriteAtlas else None
    if atlas:
        d = next(v for k, v in atlas.m_RenderDataMap if k == sprite.m_RenderDataKey)
        return atlas, d
    return None, sprite.m_RD


def replace_sprite_pixels(base_bundle, out_bundle, sprite_name, canvas):
    plain, salt = seer.decrypt(base_bundle)
    os.makedirs('/tmp/rebuild_plain', exist_ok=True)
    plain_path = '/tmp/rebuild_plain/' + os.path.basename(base_bundle) + '.plain'
    open(plain_path, 'wb').write(plain)

    env = UnityPy.load(plain_path)
    bf = env.files[list(env.files.keys())[0]]
    o, s = find_sprite(env, sprite_name)
    atlas, rd = get_render_data(env, s)
    tr = rd.textureRect
    print('sprite', sprite_name, 'rect', tr, 'atlas', atlas.m_Name if atlas else None)
    x, y, w, h = int(tr.x), int(tr.y), int(tr.width), int(tr.height)
    tex = rd.texture.read()
    fmt = tex.m_TextureFormat
    sd = tex.m_StreamData
    res_name = sd.path.rsplit('/', 1)[-1]
    print('tex', tex.m_Name, tex.m_Width, tex.m_Height, 'fmt', fmt, 'stream', res_name, int(sd.offset), int(sd.size))

    img = tex.image.convert('RGBA')
    art = canvas.convert('RGBA')
    assert art.size == (w, h), (art.size, (w, h))
    img.paste(art, (x, img.height - y - h, x + w, img.height - y))

    page, out_fmt = Texture2DConverter.image_to_texture2d(img, fmt)
    old = bf.files[res_name]
    raw = bytearray(old.bytes)
    assert len(page) == int(sd.size), (len(page), int(sd.size))
    raw[int(sd.offset):int(sd.offset) + int(sd.size)] = page
    from UnityPy.streams import EndianBinaryReader
    nr = EndianBinaryReader(bytes(raw))
    nr.flags = old.flags
    bf.files[res_name] = nr

    data = bf.save(packer='none')
    data = data[:40] + struct.pack('>I', struct.unpack('>I', data[40:44])[0] | 0x40) + data[44:]
    enc = seer.encrypt(data, salt)
    open(out_bundle, 'wb').write(enc)
    print('bundle', len(data), 'enc', len(enc))
    return plain_path


if __name__ == '__main__':
    print('import module')
