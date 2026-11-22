#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.1.30: 向 pettypebig 图集新增属性图标 69（光·暗影）。

做法与 peticon 新增立绘一致：新增一张 RGBA32 贴图页 + Sprite + SpriteAtlas 条目。
"""
import sys, os, random, struct
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
sys.path.insert(0, '/workspace/work')
import warnings
warnings.filterwarnings('ignore')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
from UnityPy.files.ObjectReader import ObjectReader
from PIL import Image
import seer

BASE = '/workspace/work/pettypebig_cur.plain'
SRC_ENC = '/workspace/patch_v1.1.29/assets/aa/Android/pettypebig_assets_all_0eb3e7bdd008cc4dbfe3ad98711c92fc.bundle'
OUT_ENC = '/workspace/work/pettypebig_v1130.bundle'
ART = {'69': '/workspace/work/type69_icon.png'}
ATLAS_NAME = 'PetIconTypeBig'
TEX_W, TEX_H = 256, 256
PAD = 4


def load():
    env = UnityPy.load(BASE)
    bf = env.files[list(env.files.keys())[0]]
    sf = bf.files[[k for k in bf.files if not k.endswith('.resS')][0]]
    return env, bf, sf


def find(sf, name):
    for o in sf.objects.values():
        if o.type.name == 'Sprite' and o.read_typetree()['m_Name'] == name:
            return o
    raise KeyError(name)


def add_obj(sf, template, pid, typetree):
    from UnityPy.helpers import TypeTreeHelper
    from UnityPy.streams import EndianBinaryWriter
    node = template._get_typetree_node()
    w = EndianBinaryWriter(endian=sf.reader.endian)
    TypeTreeHelper.write_typetree(typetree, node, w, sf)
    data = w.bytes
    nr = ObjectReader.__new__(ObjectReader)
    nr.assets_file = sf
    nr.reader = sf.reader
    nr.data = data
    nr.version = sf.version
    nr.version2 = sf.header.version
    nr.platform = sf.target_platform
    nr.build_type = sf.build_type
    nr.path_id = pid
    nr.type_id = template.type_id
    nr.serialized_type = template.serialized_type
    nr.class_id = template.class_id
    nr.type = template.type
    nr.byte_size = len(data)
    sf.objects[pid] = nr
    return nr


def rnd_key():
    v = [random.getrandbits(32) for _ in range(4)]
    return {'data[0]': v[0], 'data[1]': v[1], 'data[2]': v[2], 'data[3]': v[3]}


def main():
    arts = {k: Image.open(p).convert('RGBA') for k, p in ART.items()}
    canvas = Image.new('RGBA', (TEX_W, TEX_H), (0, 0, 0, 0))
    x = PAD
    pos = {}
    for pid, im in arts.items():
        if x + im.width + PAD > TEX_W or im.height + PAD * 2 > TEX_H:
            raise SystemExit('too large')
        canvas.paste(im, (x, PAD), im)
        pos[pid] = (x, PAD)
        x += im.width + PAD
    raw = canvas.transpose(Image.FLIP_TOP_BOTTOM).tobytes()

    env, bf, sf = load()
    atlas_obj = next(o for o in sf.objects.values() if o.type.name == 'SpriteAtlas')
    atlas = atlas_obj.read_typetree()
    assert atlas['m_Name'] == ATLAS_NAME
    assert '69' not in atlas['m_PackedSpriteNamesToIndex']
    template_tex = next(o for o in sf.objects.values() if o.type.name == 'Texture2D')
    template_sprite = find(sf, '30')
    atlas_pid = atlas_obj.path_id

    tex_pid = -8200000000000000000 - random.getrandbits(40)
    while tex_pid in sf.objects:
        tex_pid -= 1
    tt = template_tex.read_typetree()
    tt['m_Name'] = 'petart-type-ext-%d' % random.getrandbits(32)
    tt['m_Width'] = TEX_W
    tt['m_Height'] = TEX_H
    tt['m_CompleteImageSize'] = len(raw)
    tt['m_TextureFormat'] = 4
    tt['m_MipCount'] = 1
    tt['m_StreamData'] = {'offset': 0, 'size': 0, 'path': ''}
    tt['image data'] = raw
    add_obj(sf, template_tex, tex_pid, tt)
    print('texture', tex_pid, len(raw))

    for pid, im in arts.items():
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
    out = bf.save(packer='lz4')
    open('/workspace/work/pettypebig_v1130.plain', 'wb').write(out)
    _, salt = seer.decrypt_bytes(open(SRC_ENC, 'rb').read())
    open(OUT_ENC, 'wb').write(seer.encrypt(out, salt))
    print('saved', OUT_ENC, len(out), 'salt', salt.hex())

    # 复核
    env2 = UnityPy.load(out)
    at2 = [o for o in env2.objects if o.type.name == 'SpriteAtlas'][0].read_typetree()
    print('atlas packed', len(at2['m_PackedSprites']), 'names', len(at2['m_PackedSpriteNamesToIndex']),
          'rdm', len(at2['m_RenderDataMap']), 'has69', '69' in at2['m_PackedSpriteNamesToIndex'])
    sp = [o for o in env2.objects if o.type.name == 'Sprite' and o.read_typetree()['m_Name'] == '69']
    assert len(sp) == 1
    im = sp[0].read().image
    print('sprite 69 image', im.size if im else None, 'bbox', im.getbbox() if im else None)
    if im:
        im.save('/tmp/added69.png')


if __name__ == '__main__':
    main()
