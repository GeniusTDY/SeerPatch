#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.1.26: 3041 待机按官方姿势重排，消除卡顿。

- 官方 SWF 第 9~30 帧共 22 帧，实际只有 7 个不同姿势：
  A=9~11/16~18/23~24, B=12~13, C=14~15, D=19~20, E=21~22, F=25~26/29~30, G=27~28。
- v1.1.25 用 22 帧等距取样到 21 个关键帧，把 E 姿势压成 1 帧，
  播放时出现一次 40ms 的“闪帧”，看起来卡顿。
- 本版按官方姿势序列重排 21 个关键帧：
  A×3,B×2,C×2,A×2,D×2,E×2,A×2,F×2,G×2,F×2（只比官方少 1 帧 A 停留），
  每个姿势稳定停留 80ms；
- 待机画布 469x500 -> 586x625（为 prefab 放大后的显示尺寸保留足够分辨率）；
- 3041_1 clip 仍为 25fps / 0.84s；
- 攻击 3 段（3041_2/3/4）贴图、trim、clip 保持 v1.1.23 原样。

21 帧直接从官方 SWF（seer.61.com/resource/fightResource/pet/swf/3041.swf）
导出的 SVG 逐帧矢量重绘。
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
import cairosvg
from PIL import Image

SRC_PLAIN = '/workspace/work/fight3041_v11.plain'
SRC_ENC = '/workspace/work/fight3041_v11.bundle'
OUT_PLAIN = '/workspace/work/fight3041_v1126.plain'
OUT_ENC = '/workspace/work/fight3041_v1126.bundle'
PREVIEW = '/workspace/work/v1126_frames'

IDLE_CLIP = '3041_1'
SRC_IDLE_SIZE = (328, 350)
TARGET_H = 625
TARGET_W = int(round(SRC_IDLE_SIZE[0] * TARGET_H / float(SRC_IDLE_SIZE[1])))
TRIM_NAME = '3041_1.trim'
TRIM_PATH = 'Assets/PetAnimation/FightAnimation/3041/3041_1/3041_1.trim.json'

SVG_DIR = '/workspace/work/swfout/sprites/DefineSprite_139_pet'
# 官方 SWF 的 30 帧里，6~8 是全屏蓝色爆发特效（遮住本体，v1.1.23 误采入待机）。
# 只取连续待机段 9~30（22 帧）均分到 21 帧，避免爆发帧，并保持 30→9 的循环连贯。
SVG_FIRST, SVG_LAST = 9, 30
RENDER_SCALE = 4
# v1.1.23 待机等价比 = BASE_SCALE(0.95) * IDLE_UP(1.40) = 1.33（328x350 画布）；
# 本版画布 459x490，保持同一显示尺寸，等价放大 459/328。
ART_SCALE = 0.95 * 1.40 * (TARGET_W / float(SRC_IDLE_SIZE[0]))

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
    srcs = sorted(os.listdir(SVG_DIR), key=lambda x: int(x.split('.')[0]))
    pool = list(range(SVG_FIRST, SVG_LAST + 1))
    # 官方 9~30 的 7 个不同姿势：A=9 B=12 C=14 D=19 E=21 F=25 G=27
    poses = [9, 12, 14, 16, 19, 21, 23, 25, 27, 29]
    pattern = [poses[0]] * 3 + [p for p in poses[1:] for _ in range(2)]
    assert len(pattern) == len(order) == 21, (len(pattern), len(order))
    jmap = [p - 1 for p in pattern]
    print('idle pose frames', poses, 'pattern', pattern)
    print('idle svg frames', len(srcs), 'pool', pool, 'map', jmap)

    frames = []
    for i, sid in enumerate(order):
        so = sprites[sid]
        st = so.read_typetree()
        W0 = int(st['m_Rect']['width'])
        H0 = int(st['m_Rect']['height'])
        assert (W0, H0) == SRC_IDLE_SIZE, (i, W0, H0)
        tex = by_id[st['m_RD']['texture']['m_PathID']]

        png = cairosvg.svg2png(url=os.path.join(SVG_DIR, srcs[jmap[i]]),
                               scale=RENDER_SCALE)
        im = Image.open(io.BytesIO(png)).convert('RGBA')
        bb = im.getbbox()
        assert bb is not None, (i, jmap[i])
        art = im.crop(bb)
        im.close()
        nw = max(1, int(round(art.width * ART_SCALE / RENDER_SCALE)))
        nh = max(1, int(round(art.height * ART_SCALE / RENDER_SCALE)))
        small = art.resize((nw, nh), Image.LANCZOS)
        art.close()
        out = Image.new('RGBA', (TARGET_W, TARGET_H), (0, 0, 0, 0))
        dx = (TARGET_W - nw) // 2
        dy = TARGET_H - nh
        sx, sy = max(0, -dx), max(0, -dy)
        ex, ey = min(nw, TARGET_W - dx), min(nh, TARGET_H - dy)
        if ex > sx and ey > sy:
            out.alpha_composite(small.crop((sx, sy, ex, ey)),
                                (max(0, dx), max(0, dy)))
        small.close()
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

    # 待机速度：离散 PPtr 关键帧时间 1/60 步长 -> 1/25 步长（官方 SWF 为 25fps）
    clip_obj = clips[IDLE_CLIP]
    ct = clip_obj.read_typetree()
    stream = ct['m_MuscleClip']['m_Clip']['data']['m_StreamedClip']['data']
    nk = len(order) - 1  # 20 个显式关键帧（第 0 帧由流头部隐含）
    for k in range(nk):
        stream[7 + 7 * k] = struct.unpack('<I', struct.pack('<f', (k + 1) / 25.0))[0]
    ct['m_MuscleClip']['m_Clip']['data']['m_StreamedClip']['data'] = stream
    ct['m_MuscleClip']['m_StopTime'] = len(order) / 25.0
    ct['m_MuscleClip']['m_Clip']['data']['m_DenseClip']['m_SampleRate'] = 25.0
    ct['m_SampleRate'] = 25.0
    clip_obj.save_typetree(ct)
    print('idle clip retimed: %d keys, stop %.2fs, 25fps' % (nk, len(order) / 25.0))

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
    cl = [o for o in objs2 if o.type.name == 'AnimationClip'
          and o.read_typetree()['m_Name'] == IDLE_CLIP][0].read_typetree()
    print('idle clip stop %.4f sample %.1f' % (cl['m_MuscleClip']['m_StopTime'], cl['m_SampleRate']))
    assert abs(cl['m_MuscleClip']['m_StopTime'] - len(order) / 25.0) < 1e-6
    assert cl['m_SampleRate'] == 25.0
    print('elapsed %.1fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
