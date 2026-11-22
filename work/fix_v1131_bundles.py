#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.1.31 修复：SerializedFile 对象表必须按 path_id 升序（Unity 二分查找）。

v1.1.30 里新增对象用了极大负数 path_id 并追加在末尾，导致对象表失序：
  - fight3042/3043 -> 对战资源加载失败
  - pettypebig     -> 全部属性图标消失

修复方式：
  - 新增对象改用 max(path_id)+1 / +2 ...（与 3041 的既有做法一致）；
  - 保存前对 sf.objects 按 path_id 排序，确保对象表升序；
  - fight 包同时删除无引用的残留 .resS（与 3041 结构一致）。
"""
import sys, os, json, struct
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
sys.path.insert(0, '/workspace/work')
import warnings
warnings.filterwarnings('ignore')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
from UnityPy.files.ObjectReader import ObjectReader
from UnityPy.helpers import TypeTreeHelper
from UnityPy.streams import EndianBinaryWriter
from PIL import Image
import seer

PAT30 = '/workspace/patch_v1.1.30/assets/aa/Android'
PAT29 = '/workspace/patch_v1.1.29/assets/aa/Android'
WORK = '/workspace/work'


def load_enc(path):
    plain, salt = seer.decrypt_bytes(open(path, 'rb').read())
    env = UnityPy.load(plain)
    bf = env.files[list(env.files.keys())[0]]
    sf = bf.files[[k for k in bf.files if not k.endswith('.resS')][0]]
    return env, bf, sf, salt


def sort_objects(sf):
    sf.objects = dict(sorted(sf.objects.items()))


def assert_ascending(sf, tag):
    ids = [o.path_id for o in sf.objects.values()]
    assert all(ids[i] < ids[i + 1] for i in range(len(ids) - 1)), '%s not ascending' % tag


def fix_fight(pid):
    src = '%s/fight%s_assets_all_%s.bundle' % (
        PAT30, pid,
        '1412028bff7706fa6934d681d51371c7' if pid == '3042' else 'bb699851f51aee2a4c5a8520a83b293d')
    env, bf, sf, salt = load_enc(src)
    trim_name = '%s_1.trim' % pid
    trim = None
    for o in sf.objects.values():
        if o.type.name == 'TextAsset' and o.read_typetree()['m_Name'] == trim_name:
            trim = o
            break
    assert trim is not None, trim_name
    old_pid = trim.path_id
    new_pid = max(sf.objects) + 1
    print('[%s] idle trim path_id %d -> %d' % (pid, old_pid, new_pid))

    # AB 里所有指向该 TextAsset 的 PPtr
    ab_obj = next(o for o in sf.objects.values() if o.type.name == 'AssetBundle')
    ab = ab_obj.read_typetree()
    n_pre = 0
    for p in ab['m_PreloadTable']:
        if p['m_PathID'] == old_pid:
            p['m_PathID'] = new_pid
            n_pre += 1
    n_con = 0
    for path, inf in ab['m_Container']:
        if inf['asset']['m_PathID'] == old_pid:
            inf['asset']['m_PathID'] = new_pid
            n_con += 1
    assert n_pre == 1 and n_con == 1, (n_pre, n_con)
    ab_obj.save_typetree(ab)

    del sf.objects[old_pid]
    trim.path_id = new_pid
    sf.objects[new_pid] = trim

    # 删除无引用的残留 resS
    for k in [k for k in bf.files if k.endswith('.resS')]:
        print('  drop', k)
        del bf.files[k]

    sort_objects(sf)
    assert_ascending(sf, pid)
    out = bf.save(packer='lz4')
    open('%s/fight%s_v1131.plain' % (WORK, pid), 'wb').write(out)
    open('%s/fight%s_v1131.bundle' % (WORK, pid), 'wb').write(seer.encrypt(out, salt))
    print('  saved plain %d B  enc %d B  salt %s' % (
        len(out), os.path.getsize('%s/fight%s_v1131.bundle' % (WORK, pid)), salt.hex()))
    return len(out)


def add_obj(sf, template, pid, typetree):
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
    import random
    v = [random.getrandbits(32) for _ in range(4)]
    return {'data[0]': v[0], 'data[1]': v[1], 'data[2]': v[2], 'data[3]': v[3]}


def fix_pettypebig():
    src = '%s/pettypebig_assets_all_0eb3e7bdd008cc4dbfe3ad98711c92fc.bundle' % PAT29
    plain, salt = seer.decrypt_bytes(open(src, 'rb').read())
    env = UnityPy.load(plain)
    bf = env.files[list(env.files.keys())[0]]
    sf = bf.files[[k for k in bf.files if not k.endswith('.resS')][0]]

    atlas_obj = next(o for o in sf.objects.values() if o.type.name == 'SpriteAtlas')
    atlas = atlas_obj.read_typetree()
    assert atlas['m_Name'] == 'PetIconTypeBig'
    assert '69' not in atlas['m_PackedSpriteNamesToIndex'], 'base already has 69'
    assert len(atlas['m_PackedSprites']) == 62

    template_tex = next(o for o in sf.objects.values() if o.type.name == 'Texture2D')
    template_sprite = None
    for o in sf.objects.values():
        if o.type.name == 'Sprite' and o.read_typetree()['m_Name'] == '30':
            template_sprite = o
            break
    assert template_sprite is not None

    im = Image.open('%s/type69_icon.png' % WORK).convert('RGBA')
    TEX_W, TEX_H, PAD = 256, 256, 4
    canvas = Image.new('RGBA', (TEX_W, TEX_H), (0, 0, 0, 0))
    canvas.paste(im, (PAD, PAD), im)
    raw = canvas.transpose(Image.FLIP_TOP_BOTTOM).tobytes()
    left, top = PAD, PAD
    y_bl = TEX_H - (top + im.height)

    base = max(sf.objects)
    tex_pid = base + 1
    spid = base + 2
    print('pettypebig new tex_pid', tex_pid, 'sprite_pid', spid)

    tt = template_tex.read_typetree()
    tt['m_Name'] = 'petart-type-ext-%d' % rnd_key()['data[0]']
    tt['m_Width'] = TEX_W
    tt['m_Height'] = TEX_H
    tt['m_CompleteImageSize'] = len(raw)
    tt['m_TextureFormat'] = 4
    tt['m_MipCount'] = 1
    tt['m_StreamData'] = {'offset': 0, 'size': 0, 'path': ''}
    tt['image data'] = raw
    add_obj(sf, template_tex, tex_pid, tt)

    w, h = im.size
    key = rnd_key()
    st = template_sprite.read_typetree()
    st['m_Name'] = '69'
    st['m_Rect'] = {'x': 0.0, 'y': 0.0, 'width': float(w), 'height': float(h)}
    st['m_Offset'] = {'x': 0.0, 'y': 0.0}
    st['m_Border'] = {'x': 0.0, 'y': 0.0, 'z': 0.0, 'w': 0.0}
    st['m_PixelsToUnits'] = 100.0
    st['m_Pivot'] = {'x': 0.5, 'y': 0.5}
    st['m_Extrude'] = 1
    st['m_IsPolygon'] = False
    st['m_RenderDataKey'] = [key, 21300000]
    st['m_AtlasTags'] = ['PetIconTypeBig']
    st['m_SpriteAtlas'] = {'m_FileID': 0, 'm_PathID': atlas_obj.path_id}
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
    data = b''.join(struct.pack('<3f', *v) for v in
                    [(-hw, -hh, 0.0), (hw, -hh, 0.0), (hw, hh, 0.0), (-hw, hh, 0.0)])
    data += b''.join(struct.pack('<2f', 0.0, 0.0) for _ in range(4))
    vd['m_DataSize'] = data
    rd['m_Bindpose'] = []
    rd['textureRect'] = {'x': 0.0, 'y': 0.0, 'width': float(w), 'height': float(h)}
    rd['textureRectOffset'] = {'x': 0.0, 'y': 0.0}
    rd['atlasRectOffset'] = {'x': -1.0, 'y': -1.0}
    rd['settingsRaw'] = 64
    rd['uvTransform'] = {'x': 100.0, 'y': w / 2.0, 'z': 100.0, 'w': h / 2.0}
    rd['downscaleMultiplier'] = 1.0
    add_obj(sf, template_sprite, spid, st)

    atlas['m_PackedSprites'].append({'m_FileID': 0, 'm_PathID': spid})
    atlas['m_PackedSpriteNamesToIndex'].append('69')
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

    sort_objects(sf)
    # 按对象表顺序重建 preload（除 AssetBundle 外全部预载，与 v1.1.29 一致）
    ab_obj = next(o for o in sf.objects.values() if o.type.name == 'AssetBundle')
    ab = ab_obj.read_typetree()
    pre = [{'m_FileID': 0, 'm_PathID': o.path_id}
           for o in sf.objects.values() if o.type.name != 'AssetBundle']
    ab['m_PreloadTable'] = pre
    for path, inf in ab['m_Container']:
        inf['preloadIndex'] = 0
        inf['preloadSize'] = len(pre)
    ab_obj.save_typetree(ab)
    assert_ascending(sf, 'pettypebig')
    print('  preload', len(pre), 'container size', len(pre))

    out = bf.save(packer='lz4')
    open('%s/pettypebig_v1131.plain' % WORK, 'wb').write(out)
    open('%s/pettypebig_v1131.bundle' % WORK, 'wb').write(seer.encrypt(out, salt))
    print('  saved plain %d B  enc %d B' % (
        len(out), os.path.getsize('%s/pettypebig_v1131.bundle' % WORK)))
    return len(out)


def verify(path, tag):
    plain = seer.decrypt_bytes(open(path, 'rb').read())[0]
    env = UnityPy.load(plain)
    ids = [o.path_id for o in env.objects]
    asc = all(ids[i] < ids[i + 1] for i in range(len(ids) - 1))
    print('VERIFY %-14s objs=%d ascending=%s' % (tag, len(ids), asc))
    assert asc, tag


if __name__ == '__main__':
    os.makedirs(WORK, exist_ok=True)
    s2 = fix_fight('3042')
    s3 = fix_fight('3043')
    sp = fix_pettypebig()
    json.dump({'3042': s2, '3043': s3, 'pettypebig': sp},
              open('%s/v1131_sizes.json' % WORK, 'w'))
    print('sizes', s2, s3, sp)
    verify('%s/fight3042_v1131.bundle' % WORK, 'fight3042')
    verify('%s/fight3043_v1131.bundle' % WORK, 'fight3043')
    verify('%s/pettypebig_v1131.bundle' % WORK, 'pettypebig')
