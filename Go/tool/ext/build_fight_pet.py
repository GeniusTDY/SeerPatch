#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为缺失战斗资源的精灵生成 fight<id> 资源包，并在 Addressables 目录里登记。

用法: build_fight_pet.py 3041 [3042 ...]
输出: /workspace/work/fight<id>.enc  +  /workspace/work/catalog_<id>.json
"""
import sys, os, json, base64, struct, random
sys.path.insert(0, '/workspace/tools')
import UnityPy
from UnityPy.files.ObjectReader import ObjectReader
from UnityPy.helpers import TypeTreeHelper
from UnityPy.streams import EndianBinaryWriter
from PIL import Image
import seer

UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'

BASE = '/workspace/work/fight3040.plain'
SRC_ENC = '/workspace/work/fight3040.enc'
CATALOG = '/workspace/work/catalog.json'
ART_DIR = '/workspace/work/petart'
BUNDLE_HASH = '64a25feae0a77a1241f236224fb3777b'
MAX_H = 360


def add_obj(sf, template, pid, typetree):
    node = template._get_typetree_node()
    w = EndianBinaryWriter(endian=sf.reader.endian)
    TypeTreeHelper.write_typetree(typetree, node, w, sf)
    data = w.bytes
    nr = ObjectReader(sf, sf.reader, pid, template.type_id, template.serialized_type,
                      template.class_id, template.type, 0, len(data), None, None, data)
    sf.objects[pid] = nr
    return nr


def build_bundle(pid):
    im = Image.open(f'{ART_DIR}/{pid}_raw.png').convert('RGBA')
    if im.height > MAX_H:
        s = float(MAX_H) / im.height
        im = im.resize((max(1, round(im.width * s)), MAX_H), Image.LANCZOS)
    w, h = im.size
    raw = im.transpose(Image.FLIP_TOP_BOTTOM).tobytes()
    print('art', pid, (w, h), len(raw))

    env = UnityPy.load(BASE)
    bf = env.files[list(env.files.keys())[0]]
    sf = bf.files[[k for k in bf.files if not k.endswith('.resS')][0]]

    template_tex = next(o for o in sf.objects.values() if o.type.name == 'Texture2D')
    tex_pid = -8400000000000000000 - random.getrandbits(40)
    while tex_pid in sf.objects:
        tex_pid -= 1
    tt = template_tex.read_typetree()
    tt['m_Name'] = 'fightart-%s' % pid
    tt['m_Width'] = w
    tt['m_Height'] = h
    tt['m_CompleteImageSize'] = len(raw)
    tt['m_TextureFormat'] = 4  # RGBA32
    tt['m_MipCount'] = 1
    tt['m_StreamData'] = {'offset': 0, 'size': 0, 'path': ''}
    tt['image data'] = raw
    add_obj(sf, template_tex, tex_pid, tt)

    n = 0
    for o in list(sf.objects.values()):
        if o.type.name != 'Sprite':
            continue
        st = o.read_typetree()
        st['m_Rect'] = {'x': 0.0, 'y': 0.0, 'width': float(w), 'height': float(h)}
        st['m_Offset'] = {'x': 0.0, 'y': 0.0}
        st['m_Pivot'] = {'x': 0.5, 'y': 0.5}
        st['m_IsPolygon'] = False
        st['m_PhysicsShape'] = []
        rd = st['m_RD']
        rd['texture'] = {'m_FileID': 0, 'm_PathID': tex_pid}
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
        hw, hh = w / 200.0, h / 200.0
        verts = [(-hw, -hh, 0.0), (hw, -hh, 0.0), (hw, hh, 0.0), (-hw, hh, 0.0)]
        data = b''.join(struct.pack('<3f', *v) for v in verts)
        data += b''.join(struct.pack('<2f', 0.0, 0.0) for _ in range(4))
        vd['m_DataSize'] = data
        rd['Bindpose'] = []
        rd['textureRect'] = {'x': 0.0, 'y': 0.0, 'width': float(w), 'height': float(h)}
        rd['textureRectOffset'] = {'x': 0.0, 'y': 0.0}
        rd['atlasRectOffset'] = {'x': -1.0, 'y': -1.0}
        rd['settingsRaw'] = 64
        rd['uvTransform'] = {'x': 100.0, 'y': w / 2.0, 'z': 100.0, 'w': h / 2.0}
        rd['downscaleMultiplier'] = 1.0
        o.save_typetree(st)
        n += 1
    print('sprites patched', n)

    data = bf.save(packer='lz4')
    _, salt = seer.decrypt(SRC_ENC)
    out = '/workspace/work/fight%s.enc' % pid
    open(out, 'wb').write(seer.encrypt(data, salt))
    print('bundle', len(data), '->', out, os.path.getsize(out))
    return w, h


def patch_catalog(pid):
    c = json.load(open(CATALOG))
    ids = c['m_InternalIds']
    kb = base64.b64decode(c['m_KeyDataString'])
    bd = base64.b64decode(c['m_BucketDataString'])
    ed = base64.b64decode(c['m_EntryDataString'])

    b_name = 'fight%s_assets_all_%s.bundle' % (pid, BUNDLE_HASH)
    ids.append('{UnityEngine.AddressableAssets.Addressables.RuntimePath}/Android/' + b_name)
    bundle_id = len(ids) - 1

    ec = struct.unpack_from('<i', ed, 0)[0]
    rows = [list(struct.unpack_from('<7i', ed, 4 + i * 28)) for i in range(ec)]
    base_row = rows[354]
    new_entry = [bundle_id, base_row[1], base_row[2], base_row[3], base_row[4], bundle_id, base_row[6]]
    rows.append(new_entry)
    new_eidx = len(rows) - 1

    def keystr(off):
        if kb[off] != 0:
            return None
        ln = struct.unpack_from('<i', kb, off + 1)[0]
        return kb[off + 5:off + 5 + ln].decode('utf-8', 'replace')

    cnt = struct.unpack_from('<i', bd, 0)[0]
    o = 4
    old = []
    for i in range(cnt):
        k, n = struct.unpack_from('<2i', bd, o); o += 8
        ents = list(struct.unpack_from('<%di' % n, bd, o)); o += 4 * n
        old.append((k, ents))

    bundle_key = 'fight3040_assets_all_%s.bundle' % BUNDLE_HASH

    def related(s):
        return (s == bundle_key
                or s.startswith('Assets/PetAnimation/FightAnimation/3040/')
                or s.startswith('Assets/Materials/Sprites/Mat_3040')
                or s.startswith('FightAnimTrim/3040_'))

    merged = {}
    for k, ents in old:
        s = keystr(k)
        if not s or '3040' not in s or not related(s):
            continue
        if s == bundle_key:
            merged[b_name] = [new_eidx]
            continue
        dst = merged.setdefault(s.replace('3040', pid), [])
        for e in ents:
            r = list(rows[e])
            if r[2] == 354:
                r[2] = new_eidx
                rows.append(r)
                dst.append(len(rows) - 1)
            else:
                dst.append(e)
    new_keys = list(merged.items())
    print('new keys:')
    for s, es in new_keys:
        print('  ', s, es)

    add_kb = b''
    add_bd = b''
    for s, es in new_keys:
        off = len(kb) + len(add_kb)
        bs = s.encode('utf-8')
        add_kb += b'\x00' + struct.pack('<i', len(bs)) + bs
        add_bd += struct.pack('<2i', off, len(es)) + b''.join(struct.pack('<i', e) for e in es)

    kb2 = struct.pack('<i', struct.unpack_from('<i', kb, 0)[0] + len(new_keys)) + kb[4:] + add_kb
    bd2 = struct.pack('<i', cnt + len(new_keys)) + bd[4:] + add_bd
    ed2 = struct.pack('<i', len(rows)) + b''.join(struct.pack('<7i', *r) for r in rows)

    c['m_KeyDataString'] = base64.b64encode(kb2).decode()
    c['m_BucketDataString'] = base64.b64encode(bd2).decode()
    c['m_EntryDataString'] = base64.b64encode(ed2).decode()
    out = '/workspace/work/catalog_%s.json' % pid
    json.dump(c, open(out, 'w'), ensure_ascii=False, separators=(',', ':'))
    print('catalog ->', out, 'keys+%d entries+%d' % (len(new_keys), len(rows) - ec))
    print('bundle name', b_name)


if __name__ == '__main__':
    for pid in (sys.argv[1:] or ['3041']):
        build_bundle(pid)
        patch_catalog(pid)
