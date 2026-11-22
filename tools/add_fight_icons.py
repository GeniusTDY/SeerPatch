#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""向 fight 资源包的 PetFightIcon 图集新增 3041/3042/3043 战斗头像。

做法与 add_peticon_sprites.py 一致：新增一张独立 RGBA32 贴图页 + 3 个 Sprite，
并把它们登记进 SpriteAtlasV2 的打包表 / 名称索引 / 渲染表。
"""
import sys, os, random, struct
sys.path.insert(0, '/workspace/tools')
import UnityPy
from UnityPy.files.ObjectReader import ObjectReader
from PIL import Image

UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'

BASE = '/workspace/work/fight_cur.plain'
ART = '/workspace/work/petart'
OUT = '/workspace/work/fight_new.bundle'

ATLAS_NAME = 'PetFightIcon'
TEX_W, TEX_H = 1024, 256
MAX_H = 176
PAD = 4


def load():
    env = UnityPy.load(BASE)
    bf = env.files[list(env.files.keys())[0]]
    sf = bf.files[[k for k in bf.files if not k.endswith('.resS')][0]]
    return env, bf, sf


def add_obj(sf, template, pid, typetree):
    from UnityPy.helpers import TypeTreeHelper
    from UnityPy.streams import EndianBinaryWriter
    node = template._get_typetree_node()
    w = EndianBinaryWriter(endian=sf.reader.endian)
    TypeTreeHelper.write_typetree(typetree, node, w, sf)
    data = w.bytes
    nr = ObjectReader(sf, sf.reader, pid, template.type_id, template.serialized_type,
                      template.class_id, template.type, 0, len(data), None, None, data)
    sf.objects[pid] = nr
    return nr


def rnd_key():
    return {'data[0]': random.getrandbits(32), 'data[1]': random.getrandbits(32),
            'data[2]': random.getrandbits(32), 'data[3]': random.getrandbits(32)}


def main(ids):
    arts = {}
    for pid in ids:
        im = Image.open(f'{ART}/{pid}_raw.png').convert('RGBA')
        if im.height > MAX_H:
            s = float(MAX_H) / im.height
            im = im.resize((max(1, round(im.width * s)), MAX_H), Image.LANCZOS)
        arts[pid] = im

    canvas = Image.new('RGBA', (TEX_W, TEX_H), (0, 0, 0, 0))
    x = PAD
    pos = {}
    for pid in ids:
        im = arts[pid]
        if x + im.width + PAD > TEX_W:
            raise SystemExit('too wide')
        canvas.paste(im, (x, PAD), im)
        pos[pid] = (x, PAD)
        x += im.width + PAD
    raw = canvas.transpose(Image.FLIP_TOP_BOTTOM).tobytes()

    env, bf, sf = load()
    atlas_obj = None
    for o in sf.objects.values():
        if o.type.name == 'SpriteAtlas':
            if o.read_typetree()['m_Name'] == ATLAS_NAME:
                atlas_obj = o
                break
    assert atlas_obj is not None, 'atlas not found'
    atlas = atlas_obj.read_typetree()
    atlas_pid = atlas_obj.path_id

    template_tex = next(o for o in sf.objects.values() if o.type.name == 'Texture2D')
    template_sprite = None
    for o in sf.objects.values():
        if o.type.name == 'Sprite' and o.read_typetree()['m_Name'] == '3040':
            template_sprite = o
            break
    assert template_sprite is not None

    used = set(sf.objects.keys())
    tex_pid = -8200000000000000000 - random.getrandbits(40)
    while tex_pid in used:
        tex_pid -= 1
    tt = template_tex.read_typetree()
    tt['m_Name'] = 'fightart-ext-%d' % random.getrandbits(32)
    tt['m_Width'] = TEX_W
    tt['m_Height'] = TEX_H
    tt['m_CompleteImageSize'] = len(raw)
    tt['m_TextureFormat'] = 4  # RGBA32
    tt['m_MipCount'] = 1
    tt['m_StreamData'] = {'offset': 0, 'size': 0, 'path': ''}
    tt['image data'] = raw
    add_obj(sf, template_tex, tex_pid, tt)
    print('texture', tex_pid, len(raw))

    for pid in ids:
        im = arts[pid]
        w, h = im.size
        left, top = pos[pid]
        y_bl = TEX_H - (top + h)

        key = rnd_key()
        st = template_sprite.read_typetree()
        st['m_Name'] = pid
        st['m_Rect'] = {'x': 0.0, 'y': 0.0, 'width': float(w), 'height': float(h)}
        st['m_Offset'] = {'x': 0.0, 'y': 0.0}
        st['m_Border'] = {'x': 0.0, 'y': 0.0, 'z': 0.0, 'w': 0.0}
        st['m_PixelsToUnits'] = 100.0
        st['m_Pivot'] = {'x': 0.5, 'y': 0.5}
        st['m_Extrude'] = 1
        st['m_IsPolygon'] = False
        st['m_RenderDataKey'] = [key, 21300000]
        st['m_AtlasTags'] = [ATLAS_NAME]
        st['m_SpriteAtlas'] = {'m_FileID': 0, 'm_PathID': atlas_pid}
        st['m_PhysicsShape'] = []
        st['m_Bones'] = []

        rd = st['m_RD']
        rd['texture'] = {'m_FileID': 0, 'm_PathID': 0}
        rd['alphaTexture'] = {'m_FileID': 0, 'm_PathID': 0}
        rd['secondaryTextures'] = []
        rd['m_SubMeshes'] = [{
            'firstByte': 0, 'indexCount': 6, 'topology': 0, 'baseVertex': 0,
            'firstVertex': 0, 'vertexCount': 4,
            'localAABB': {'m_Center': {'x': 0.0, 'y': 0.0, 'z': 0.0},
                          'm_Extent': {'x': 0.0, 'y': 0.0, 'z': 0.0}}}]
        rd['m_IndexBuffer'] = list(struct.pack('<6H', 0, 1, 2, 0, 2, 3))
        vd = rd['m_VertexData']
        vd['m_VertexCount'] = 4
        vd['m_Channels'] = template_sprite.read_typetree()['m_RD']['m_VertexData']['m_Channels']
        hw, hh = w / 200.0, h / 200.0
        verts = [(-hw, -hh, 0.0), (hw, -hh, 0.0), (hw, hh, 0.0), (-hw, hh, 0.0)]
        data = b''.join(struct.pack('<3f', *v) for v in verts)
        data += b''.join(struct.pack('<2f', 0.0, 0.0) for _ in range(4))
        vd['m_DataSize'] = data
        rd['m_Bindpose'] = []
        rd['textureRect'] = {'x': 0.0, 'y': 0.0, 'width': float(w), 'height': float(h)}
        rd['textureRectOffset'] = {'x': 0.0, 'y': 0.0}
        rd['atlasRectOffset'] = {'x': -1.0, 'y': -1.0}
        rd['settingsRaw'] = 64
        rd['uvTransform'] = {'x': 100.0, 'y': w / 2.0, 'z': 100.0, 'w': h / 2.0}
        rd['downscaleMultiplier'] = 1.0

        spid = -8300000000000000000 - random.getrandbits(40)
        while spid in sf.objects:
            spid -= 1
        add_obj(sf, template_sprite, spid, st)
        print('sprite', pid, spid, (w, h), 'at', (left, y_bl))

        atlas['m_PackedSprites'].append({'m_FileID': 0, 'm_PathID': spid})
        atlas['m_PackedSpriteNamesToIndex'].append(pid)
        atlas['m_RenderDataMap'].append([[key, 21300000], {
            'texture': {'m_FileID': 0, 'm_PathID': tex_pid},
            'alphaTexture': {'m_FileID': 0, 'm_PathID': 0},
            'textureRect': {'x': float(left), 'y': float(y_bl), 'width': float(w), 'height': float(h)},
            'textureRectOffset': {'x': 0.0, 'y': 0.0},
            'atlasRectOffset': {'x': float(left), 'y': float(y_bl)},
            'uvTransform': {'x': 100.0, 'y': left + w / 2.0, 'z': 100.0, 'w': y_bl + h / 2.0},
            'downscaleMultiplier': 1.0,
            'settingsRaw': 67,
            'secondaryTextures': [],
        }])

    atlas_obj.save_typetree(atlas)
    raw_bundle = bf.save(packer='lz4')
    open(OUT, 'wb').write(raw_bundle)
    print('saved', OUT, len(raw_bundle))


if __name__ == '__main__':
    main(sys.argv[1:] or ['3041', '3042', '3043'])
