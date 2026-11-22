#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.1.24: 3041 待机立绘改走 trim 路径。

v1.1.23 待机 21 帧固定在 328x350 画布，靠 prefab 的 330x389 框拉伸显示；
本版给 3041_1 也加上 trim 资源，让 FightAnimTrimApplier 直接按 trimW x trimH
设置显示尺寸，不再受 330x389 框限制。

- 21 帧贴图统一放大到目标画布（trimH ≈ 490），保持水平中心 + 底边对齐；
- 新增 TextAsset `3041_1.trim`，AB 容器路径与 PreloadTable 同步补一条；
- 攻击 3 段（3041_2/3/4）贴图与 trim 数据保持 v1.1.23 原样。

注意：本次包内没有 swfsvg 原始 SVG 素材，21 帧由 v1.1.23 已渲染的 328x350
贴图放大得到（LANCZOS + 预乘 alpha），不是从矢量源重绘。
"""
import sys, os, io, json, time, gc, struct
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
import warnings
warnings.filterwarnings('ignore')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
from UnityPy.helpers import CompressionHelper, TypeTreeHelper
from UnityPy.helpers.TypeTreeHelper import write_typetree
from UnityPy.export.Texture2DConverter import pad_image
from UnityPy.streams import EndianBinaryWriter
from UnityPy.files.ObjectReader import ObjectReader
from UnityPy.enums import ClassIDType
import astc_encoder
import seer
import numpy as np
from PIL import Image, ImageFilter

SRC_PLAIN = '/workspace/work/fight3041_v11.plain'
SRC_ENC = '/workspace/work/fight3041_v11.bundle'
OUT_PLAIN = '/workspace/work/fight3041_v1124.plain'
OUT_ENC = '/workspace/work/fight3041_v1124.bundle'
PREVIEW = '/workspace/work/v1124_frames'

IDLE_CLIP = '3041_1'
SRC_IDLE_SIZE = (328, 350)
TARGET_H = 490
TARGET_W = int(round(SRC_IDLE_SIZE[0] * TARGET_H / float(SRC_IDLE_SIZE[1])))
TRIM_NAME = '3041_1.trim'
TRIM_PATH = 'Assets/PetAnimation/FightAnimation/3041/3041_1/3041_1.trim.json'

os.makedirs(PREVIEW, exist_ok=True)

cfg = astc_encoder.ASTCConfig(
    astc_encoder.ASTCProfile.LDR_SRGB, 8, 8, block_z=1,
    quality=astc_encoder.ASTCQualityPreset.MEDIUM,
    flags=astc_encoder.ASTCConfigFlags.USE_DECODE_UNORM8
    | astc_encoder.ASTCConfigFlags.USE_APLHA_WEIGHT
    | astc_encoder.ASTCConfigFlags.USE_PERCEPTUAL)
ctx = astc_encoder.ASTCContext(cfg, threads=3)
sw = astc_encoder.ASTCSwizzle.from_str('RGBA')


def encode_astc(img):
    img = img.transpose(Image.FLIP_TOP_BOTTOM)
    w = (img.width + 7) // 8 * 8
    h = (img.height + 7) // 8 * 8
    img = pad_image(img, w, h)
    ai = astc_encoder.ASTCImage(astc_encoder.ASTCType.U8, w, h, 1, img.tobytes('raw', 'RGBA'))
    return ctx.compress(ai, sw)


def resize_rgba(im, W, H):
    """预乘 alpha 后 LANCZOS 缩放，避免透明边缘出现黑边。"""
    arr = np.asarray(im, dtype=np.float32)
    a = arr[..., 3:4] / 255.0
    pre = np.concatenate([arr[..., :3] * a, arr[..., 3:4]], axis=2)
    pre_img = Image.fromarray(pre.clip(0, 255).astype(np.uint8), 'RGBA')
    out = pre_img.resize((W, H), Image.LANCZOS)
    o = np.asarray(out, dtype=np.float32)
    oa = o[..., 3:4]
    rgb = np.where(oa > 0, o[..., :3] * 255.0 / np.maximum(oa, 1), 0)
    o[..., :3] = rgb
    res = Image.fromarray(o.clip(0, 255).astype(np.uint8), 'RGBA')
    return res.filter(ImageFilter.UnsharpMask(radius=1.0, percent=35, threshold=2))


def patch_sprite(st, W, H, tex_pid):
    """把 Sprite 改成“整块四边形”贴图，尺寸 = W x H。"""
    st['m_Rect'] = {'x': 0.0, 'y': 0.0, 'width': float(W), 'height': float(H)}
    st['m_Offset'] = {'x': 0.0, 'y': 0.0}
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
    hw, hh = W / 200.0, H / 200.0
    verts = [(-hw, -hh, 0.0), (hw, -hh, 0.0), (hw, hh, 0.0), (-hw, hh, 0.0)]
    data = b''.join(struct.pack('<3f', *v) for v in verts)
    data += b''.join(struct.pack('<2f', 0.0, 0.0) for _ in range(4))
    vd['m_DataSize'] = data
    rd['Bindpose'] = []
    rd['textureRect'] = {'x': 0.0, 'y': 0.0, 'width': float(W), 'height': float(H)}
    rd['textureRectOffset'] = {'x': 0.0, 'y': 0.0}
    rd['atlasRectOffset'] = {'x': -1.0, 'y': -1.0}
    rd['settingsRaw'] = 64
    rd['uvTransform'] = {'x': 100.0, 'y': W / 2.0, 'z': 100.0, 'w': H / 2.0}
    rd['downscaleMultiplier'] = 1.0
    return st


def main():
    t0 = time.time()
    env = UnityPy.load(SRC_PLAIN)
    bf = env.file
    sf = list(bf.files.values())[0]
    objs = list(env.objects)
    by_id = {o.path_id: o for o in objs}
    sprites = {o.path_id: o for o in objs if o.type.name == 'Sprite'}
    texs = {o.path_id: o for o in objs if o.type.name == 'Texture2D'}
    clips = {o.read_typetree()['m_Name']: o for o in objs if o.type.name == 'AnimationClip'}
    trims = {}
    for o in objs:
        if o.type.name == 'TextAsset':
            t = o.read_typetree()
            trims[t['m_Name'][:-5]] = (o, t)

    order = [p['m_PathID'] for p in
             clips[IDLE_CLIP].read_typetree()['m_ClipBindingConstant']['pptrCurveMapping']]
    assert len(order) == 21, len(order)
    print('idle frames', len(order), 'target', TARGET_W, 'x', TARGET_H)

    frames = []
    for i, sid in enumerate(order):
        so = sprites[sid]
        st = so.read_typetree()
        W0 = int(st['m_Rect']['width'])
        H0 = int(st['m_Rect']['height'])
        assert (W0, H0) == SRC_IDLE_SIZE, (i, W0, H0)
        tex = by_id[st['m_RD']['texture']['m_PathID']]
        im = tex.read().image.convert('RGBA')
        out = resize_rgba(im, TARGET_W, TARGET_H)
        im.close()
        out.save(os.path.join(PREVIEW, 'idle_%03d.png' % (i + 1)))
        data = encode_astc(out)
        out.close()
        expect = ((TARGET_W + 7) // 8) * ((TARGET_H + 7) // 8) * 16
        assert len(data) == expect, (len(data), expect)

        tt = tex.read_typetree()
        tt['m_Width'] = TARGET_W
        tt['m_Height'] = TARGET_H
        tt['m_CompleteImageSize'] = len(data)
        tt['m_TextureFormat'] = 51
        tt['m_MipCount'] = 1
        tt['image data'] = data
        tt['m_StreamData'] = {'offset': 0, 'size': 0, 'path': ''}
        tex.save_typetree(tt)

        st = patch_sprite(st, TARGET_W, TARGET_H, tex.path_id)
        so.save_typetree(st)

        frames.append({
            'spriteName': st['m_Name'],
            'sourceW': TARGET_W,
            'sourceH': TARGET_H,
            'trimX': 0,
            'trimY': 0,
            'trimW': TARGET_W,
            'trimH': TARGET_H,
        })
        print('  idle %d/21  astc %d  %.1fs' % (i + 1, len(data), time.time() - t0))
        gc.collect()

    trim_js = {'animKey': IDLE_CLIP, 'frameCount': len(frames), 'frames': frames}
    trim_txt = '\ufeff' + json.dumps(trim_js, ensure_ascii=False, indent=4)

    # 新增 TextAsset 对象（复用 3041_2.trim 的类型节点）
    tmpl = trims['3041_2'][0]
    new_pid = max(by_id) + 1
    wt = EndianBinaryWriter(endian=sf.header.endian)
    write_typetree({'m_Name': TRIM_NAME, 'm_Script': trim_txt},
                   tmpl.serialized_type.node, wt, sf)
    raw = wt.bytes
    new_obj = object.__new__(ObjectReader)
    new_obj.assets_file = sf
    new_obj.reader = sf.reader
    new_obj.data = raw
    new_obj.version = sf.version
    new_obj.version2 = sf.header.version
    new_obj.platform = sf.target_platform
    new_obj.build_type = sf.build_type
    new_obj.path_id = new_pid
    new_obj.byte_start = 0
    new_obj.byte_size = len(raw)
    new_obj.type_id = tmpl.type_id
    new_obj.serialized_type = tmpl.serialized_type
    new_obj.class_id = tmpl.class_id
    new_obj.type = ClassIDType.TextAsset
    sf.objects[new_pid] = new_obj
    print('inject TextAsset', TRIM_NAME, 'path_id', new_pid, 'bytes', len(raw))

    # AB 容器 + PreloadTable
    ab_obj = [o for o in objs if o.type.name == 'AssetBundle'][0]
    ab = ab_obj.read_typetree()
    pre_idx = len(ab['m_PreloadTable'])
    ab['m_PreloadTable'].append({'m_FileID': 0, 'm_PathID': new_pid})
    ab['m_Container'].append((TRIM_PATH, {
        'preloadIndex': pre_idx,
        'preloadSize': 1,
        'asset': {'m_FileID': 0, 'm_PathID': new_pid},
    }))
    ab_obj.save_typetree(ab)
    print('AB container/preload updated', pre_idx, len(ab['m_PreloadTable']))

    for k in [k for k in bf.files if k.endswith('.resS')]:
        del bf.files[k]
        print('dropped node', k)

    out = bf.save(packer='lz4')
    open(OUT_PLAIN, 'wb').write(out)
    print('plain saved', len(out))

    _, salt = seer.decrypt(SRC_ENC)
    enc = seer.encrypt(out, salt)
    open(OUT_ENC, 'wb').write(enc)
    print('encrypted', len(enc), 'salt', salt.hex())

    # 自检
    env2 = UnityPy.load(out)
    objs2 = list(env2.objects)
    print('reload objects', len(objs2))
    assert len(objs2) == 446, len(objs2)
    by2 = {o.path_id: o for o in objs2}
    tr = by2[new_pid].read_typetree()
    assert tr['m_Name'] == TRIM_NAME
    js = json.loads(tr['m_Script'].lstrip('\ufeff'))
    assert js['frameCount'] == 21 and js['animKey'] == IDLE_CLIP
    print('trim reload ok', js['frames'][0])
    sizes = {(int(by2[i].read_typetree()['m_Rect']['width']),
              int(by2[i].read_typetree()['m_Rect']['height'])) for i in order}
    print('idle sizes', sizes)
    print('elapsed %.1fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
