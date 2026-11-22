#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v10: 用 3041_fight.swf 的真实逐帧矢量动画重建 218 张贴图。

- 以 v9 明文 bundle 为基线（结构/精灵/动画/trim 全部不动）
- 每个 clip 的 Sprite 顺序来自 m_ClipBindingConstant.pptrCurveMapping
- 目标帧 -> 源帧用「分幅对齐」映射：先按宽度识别两侧的连续大画幅段并对应起来，
  其余首/尾段各自线性映射；避免线性拉伸把宽特效压到窄画布上，也避免 DTW 长时间定格
- 每帧渲染 -> alpha bbox 裁剪 -> 固定全局缩放(0.95) -> 底边居中贴入原画布
- 贴图重新编码为 ASTC 8x8（与原格式一致），内联 image data，清空 StreamData
- 最终去掉无用的 .resS 节点，lz4 打包，SEERAB01 同 salt 加密
"""
import sys, os, io, json, time, gc
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
import warnings
warnings.filterwarnings('ignore')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
import astc_encoder
from UnityPy.streams import EndianBinaryReader
from UnityPy.export.Texture2DConverter import pad_image
import cairosvg
from PIL import Image, ImageDraw
import seer

SRC_PLAIN = '/workspace/work/fight3041_v9.plain'
SRC_ENC = '/workspace/work/fight3041_v9.bundle'
OUT_PLAIN = '/workspace/work/fight3041_v10.plain'
OUT_ENC = '/workspace/work/fight3041_v10.bundle'
SVG_ROOT = '/workspace/work/swfsvg'
PREVIEW = '/workspace/work/v10_frames'

CLIPS = [
    ('3041_1', 'DefineSprite_139_pet'),
    ('3041_2', 'DefineSprite_113'),
    ('3041_3', 'DefineSprite_73'),
    ('3041_4', 'DefineSprite_136'),
]
RENDER_SCALE = 4
SCALE = 0.95  # 固定全局缩放

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


def src_bboxes(sym):
    d = os.path.join(SVG_ROOT, sym)
    out, files = [], sorted(os.listdir(d), key=lambda x: int(x.split('.')[0]))
    for f in files:
        png = cairosvg.svg2png(url=os.path.join(d, f), scale=1)
        im = Image.open(io.BytesIO(png)).convert('RGBA')
        bb = im.getbbox()
        out.append((bb[2] - bb[0], bb[3] - bb[1]))
        im.close()
    return out


def longest_run(flags):
    best = (0, -1, 0)
    i = 0
    while i < len(flags):
        if flags[i]:
            j = i
            while j + 1 < len(flags) and flags[j + 1]:
                j += 1
            if j - i + 1 > best[2]:
                best = (i, j, j - i + 1)
            i = j + 1
        else:
            i += 1
    return best


def seg_map(t, s):
    """分幅对齐：把两侧的连续「大画幅」段对应起来，首尾段线性映射。"""
    n, m = len(t), len(s)
    at_ = sorted(x[0] * x[1] for x in t)
    as_ = sorted(x[0] * x[1] for x in s)
    th_t = 1.6 * at_[len(at_) // 10]
    th_s = 1.6 * as_[len(as_) // 10]
    bt = longest_run([x[0] * x[1] > th_t for x in t])
    bs = longest_run([x[0] * x[1] > th_s for x in s])
    if bt[2] < 3 or bs[2] < 3:
        return [int(round(i * (m - 1) / float(n - 1))) if n > 1 else 0 for i in range(n)], \
            ('linear', bt, bs)
    mp = [None] * n
    if bt[0] > 0:
        for i in range(bt[0]):
            mp[i] = int(round(i * (bs[0] - 1) / float(bt[0] - 1))) if bt[0] > 1 and bs[0] > 1 else 0
    L = bt[1] - bt[0] + 1
    M = bs[1] - bs[0] + 1
    for k in range(L):
        mp[bt[0] + k] = bs[0] + (int(round(k * (M - 1) / float(L - 1))) if L > 1 else 0)
    lt = n - 1 - bt[1]
    ls = m - 1 - bs[1]
    for k in range(lt):
        mp[bt[1] + 1 + k] = (bs[1] + 1 +
                            (int(round(k * (ls - 1) / float(lt - 1))) if lt > 1 else 0)) if ls > 0 else bs[1]
    assert all(x is not None for x in mp)
    assert all(mp[i] <= mp[i + 1] for i in range(n - 1))
    return mp, ('seg', bt, bs)


def main():
    t_start = time.time()
    env = UnityPy.load(SRC_PLAIN)
    bf = env.file
    objs = list(env.objects)
    by_id = {o.path_id: o for o in objs}
    sprites = {o.path_id: o for o in objs if o.type.name == 'Sprite'}
    clips = {o.read_typetree()['m_Name']: o for o in objs if o.type.name == 'AnimationClip'}
    print('objects', len(objs), 'sprites', len(sprites), 'clips', sorted(clips))

    patched = 0
    split = {}
    for clip_name, sym in CLIPS:
        order = [p['m_PathID'] for p in
                 clips[clip_name].read_typetree()['m_ClipBindingConstant']['pptrCurveMapping']]
        d = os.path.join(SVG_ROOT, sym)
        srcs = sorted(os.listdir(d), key=lambda x: int(x.split('.')[0]))
        n, m = len(order), len(srcs)
        tgt = []
        for sid in order:
            st0 = sprites[sid].read_typetree()
            tgt.append((int(st0['m_Rect']['width']), int(st0['m_Rect']['height'])))
        sb = src_bboxes(sym)
        jmap, info = seg_map(tgt, sb)
        print('== %s <- %s : target %d, src %d, %s tbig=%s sbig=%s'
              % (clip_name, sym, n, m, info[0], info[1], info[2]))
        split[clip_name] = (n, m)
        for i, sid in enumerate(order):
            so = sprites[sid]
            st = so.read_typetree()
            W = int(st['m_Rect']['width'])
            H = int(st['m_Rect']['height'])
            tex = by_id[st['m_RD']['texture']['m_PathID']]
            tt = tex.read_typetree()
            assert (tt['m_Width'], tt['m_Height']) == (W, H), ((tt['m_Width'], tt['m_Height']), (W, H))

            j = jmap[i]
            svg = os.path.join(d, srcs[j])
            png = cairosvg.svg2png(url=svg, scale=RENDER_SCALE)
            im = Image.open(io.BytesIO(png)).convert('RGBA')
            bb = im.getbbox()
            if bb is None:
                raise SystemExit('empty frame %s %d' % (clip_name, i))
            art = im.crop(bb)
            nw = max(1, int(round(art.width * SCALE / RENDER_SCALE)))
            nh = max(1, int(round(art.height * SCALE / RENDER_SCALE)))
            art = art.resize((nw, nh), Image.LANCZOS)
            canvas = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            # 底边居中，显式裁剪溢出部分
            dx = (W - nw) // 2
            dy = H - nh
            sx, sy = max(0, -dx), max(0, -dy)
            ex, ey = min(nw, W - dx), min(nh, H - dy)
            if ex > sx and ey > sy:
                canvas.alpha_composite(art.crop((sx, sy, ex, ey)), (max(0, dx), max(0, dy)))
            im.close()
            del im
            canvas.save(os.path.join(PREVIEW, '%s_%03d.png' % (clip_name, i + 1)))

            data = encode_astc(canvas)
            canvas.close()
            expect = ((W + 7) // 8) * ((H + 7) // 8) * 16
            assert len(data) == expect, (len(data), expect)

            tt['m_CompleteImageSize'] = len(data)
            tt['m_TextureFormat'] = 51
            tt['m_MipCount'] = 1
            tt['image data'] = data
            tt['m_StreamData'] = {'offset': 0, 'size': 0, 'path': ''}
            tex.save_typetree(tt)
            patched += 1
            if (i + 1) % 10 == 0 or i + 1 == n:
                print('   %s %d/%d  src#%d  canvas %dx%d  astc %d  %.1fs'
                      % (clip_name, i + 1, n, j + 1, W, H, len(data), time.time() - t_start))
            gc.collect()

    assert patched == 218, patched

    # 去掉已无引用的 resS 节点
    resS = [k for k in bf.files if k.endswith('.resS')]
    for k in resS:
        del bf.files[k]
        print('dropped node', k)
    out = bf.save(packer='lz4')
    open(OUT_PLAIN, 'wb').write(out)
    print('plain saved', len(out))

    _, salt = seer.decrypt(SRC_ENC)
    enc = seer.encrypt(out, salt)
    open(OUT_ENC, 'wb').write(enc)
    print('encrypted', len(enc), 'salt', salt.hex())

    # 复核
    env2 = UnityPy.load(out)
    objs2 = list(env2.objects)
    print('reload objects', len(objs2))
    assert len(objs2) == 445
    texs = [o for o in objs2 if o.type.name == 'Texture2D']
    nonempty = 0
    for t in texs:
        im = t.read().image
        if im is not None and im.getbbox() is not None:
            nonempty += 1
    print('textures non-empty', nonempty, '/', len(texs))
    print('elapsed %.1fs' % (time.time() - t_start))


if __name__ == '__main__':
    main()
