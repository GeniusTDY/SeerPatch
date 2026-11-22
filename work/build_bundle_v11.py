#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v11: 把 3041 战斗立绘放大到与官方 3040 同样的视觉尺寸。

依据（il2cpp 反汇编 libil2cpp.so + UISeerFight.prefab）：
- 待机 clip 3041_1 没有 trim 资源 -> FightAnimTrimApplier.LateUpdate 不生效，
  RectTransform 保持 prefab 的 330x389（pivot 0.5/0），Image(Simple, 不保持比例)
  把整张贴图拉伸填满这个框。所以待机立绘的屏幕尺寸完全由“画面占贴图的比例”决定。
- 攻击 clip 3041_2/3/4 有 trim -> ApplyCurrent 里
  SetSizeWithCurrentAnchors(trimW/spu, trimH/spu)，spu = trimW/spriteW*Image.ppu = 1，
  即显示尺寸 = trimW x trimH（1 源像素 = 1 UI 单位），位置 = base + trim 底边/中心偏移
  （首帧归零）。

因此：
- 待机：统一画布 328x350，美术按 1.33 倍（自然像素）底边居中绘制，填满画布；
  贴图被拉伸进 330x389 的框后，可见高度由 284 提升到约 377（+33%）。
- 攻击：每帧画布 = 该帧美术 bbox * 1.30（美术填满画布）；trim 的 trimW/H 改成新画布，
  trimX 保持中心、trimY 保持底边、sourceW/H 不变 -> 显示尺寸与官方 3040 一致，
  帧间位移沿用官方数据。
"""
import sys, os, io, json, time, gc, math, struct
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
import warnings
warnings.filterwarnings('ignore')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
import astc_encoder
from UnityPy.export.Texture2DConverter import pad_image
import cairosvg
from PIL import Image
import seer

SRC_PLAIN = '/workspace/work/fight3041_v10.plain'
SRC_ENC = '/workspace/work/fight3041_v10.bundle'
OUT_PLAIN = '/workspace/work/fight3041_v11.plain'
OUT_ENC = '/workspace/work/fight3041_v11.bundle'
SVG_ROOT = '/workspace/work/swfsvg'
PREVIEW = '/workspace/work/v11_frames'

CLIPS = [
    ('3041_1', 'DefineSprite_139_pet'),
    ('3041_2', 'DefineSprite_113'),
    ('3041_3', 'DefineSprite_73'),
    ('3041_4', 'DefineSprite_136'),
]
RENDER_SCALE = 4
BASE_SCALE = 0.95          # v10 的美术比例（自然像素的 0.95）
IDLE_UP = 1.40             # 待机画布上采样（只为清晰，不改变显示尺寸）
IDLE_CANVAS = (234, 250)   # 待机统一画布（BASE_SCALE 下的像素）
ATT_SCALE = 1.30           # 攻击帧美术比例（自然像素的 1.30 倍）
CANVAS_CLIP = 1.0          # 攻击帧画布 = 美术 bbox * ATT_SCALE（精确贴合）

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
    """分幅对齐（与 v10 相同）。"""
    n, m = len(t), len(s)
    at_ = sorted(x[0] * x[1] for x in t)
    as_ = sorted(x[0] * x[1] for x in s)
    th_t = 1.6 * at_[max(0, len(at_) // 10)]
    th_s = 1.6 * as_[max(0, len(as_) // 10)]
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
    t_start = time.time()
    env = UnityPy.load(SRC_PLAIN)
    bf = env.file
    objs = list(env.objects)
    by_id = {o.path_id: o for o in objs}
    sprites = {o.path_id: o for o in objs if o.type.name == 'Sprite'}
    clips = {o.read_typetree()['m_Name']: o for o in objs if o.type.name == 'AnimationClip'}
    trims = {}
    for o in objs:
        if o.type.name == 'TextAsset':
            t = o.read_typetree()
            trims[t['m_Name'][:-5]] = (o, json.loads(t['m_Script'].lstrip('\ufeff')))
    print('objects', len(objs), 'sprites', len(sprites), 'clips', sorted(clips), 'trims', sorted(trims))

    patched = 0
    stat = {}
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
        is_idle = clip_name not in trims
        print('== %s <- %s : target %d src %d %s  %s'
              % (clip_name, sym, n, m, info[0], 'IDLE(fixed box)' if is_idle else 'TRIM(native)'))
        if is_idle:
            IDLE_W = int(round(IDLE_CANVAS[0] * IDLE_UP))
            IDLE_H = int(round(IDLE_CANVAS[1] * IDLE_UP))
            art_scale = BASE_SCALE * IDLE_UP
        else:
            trim_obj, tri = trims[clip_name]
            tmap = {f['spriteName']: f for f in tri['frames']}
        for i, sid in enumerate(order):
            so = sprites[sid]
            st = so.read_typetree()
            W0 = int(st['m_Rect']['width'])
            H0 = int(st['m_Rect']['height'])
            tex = by_id[st['m_RD']['texture']['m_PathID']]
            tt = tex.read_typetree()
            assert (tt['m_Width'], tt['m_Height']) == (W0, H0), ((tt['m_Width'], tt['m_Height']), (W0, H0))

            j = jmap[i]
            svg = os.path.join(d, srcs[j])
            png = cairosvg.svg2png(url=svg, scale=RENDER_SCALE)
            im = Image.open(io.BytesIO(png)).convert('RGBA')
            bb = im.getbbox()
            if bb is None:
                raise SystemExit('empty frame %s %d' % (clip_name, i))
            art = im.crop(bb)
            im.close()
            del im

            if is_idle:
                W, H = IDLE_W, IDLE_H
                nw = max(1, int(round(art.width * art_scale / RENDER_SCALE)))
                nh = max(1, int(round(art.height * art_scale / RENDER_SCALE)))
                small = art.resize((nw, nh), Image.LANCZOS)
                canvas = Image.new('RGBA', (W, H), (0, 0, 0, 0))
                dx = (W - nw) // 2
                dy = H - nh
                sx, sy = max(0, -dx), max(0, -dy)
                ex, ey = min(nw, W - dx), min(nh, H - dy)
                if ex > sx and ey > sy:
                    canvas.alpha_composite(small.crop((sx, sy, ex, ey)), (max(0, dx), max(0, dy)))
                small.close()
            else:
                W = max(1, int(round(art.width * ATT_SCALE / RENDER_SCALE)))
                H = max(1, int(round(art.height * ATT_SCALE / RENDER_SCALE)))
                canvas = art.resize((W, H), Image.LANCZOS)
            art.close()

            canvas.save(os.path.join(PREVIEW, '%s_%03d.png' % (clip_name, i + 1)))
            data = encode_astc(canvas)
            canvas.close()
            expect = ((W + 7) // 8) * ((H + 7) // 8) * 16
            assert len(data) == expect, (len(data), expect)

            tt['m_Width'] = W
            tt['m_Height'] = H
            tt['m_CompleteImageSize'] = len(data)
            tt['m_TextureFormat'] = 51
            tt['m_MipCount'] = 1
            tt['image data'] = data
            tt['m_StreamData'] = {'offset': 0, 'size': 0, 'path': ''}
            tex.save_typetree(tt)

            st = patch_sprite(st, W, H, tex.path_id)
            so.save_typetree(st)

            if not is_idle:
                f = tmap.get(st['m_Name'])
                assert f is not None, (clip_name, st['m_Name'])
                f['trimX'] = int(round(f['trimX'] + (f['trimW'] - W) / 2.0))
                f['trimW'] = W
                f['trimH'] = H
                stat[clip_name] = stat.get(clip_name, [])
                stat[clip_name].append((f['spriteName'], W, H, f['trimX'], f['trimY'],
                                        f['sourceW'], f['sourceH']))

            patched += 1
            if (i + 1) % 10 == 0 or i + 1 == n:
                print('   %s %d/%d  src#%d  canvas %dx%d  astc %d  %.1fs'
                      % (clip_name, i + 1, n, j + 1, W, H, len(data), time.time() - t_start))
            gc.collect()

    assert patched == 218, patched

    # 写回 trim JSON（保持原有键顺序与格式）
    for clip_name, (o, js) in trims.items():
        js['frameCount'] = len(js['frames'])
        txt = '\ufeff' + json.dumps(js, ensure_ascii=False, indent=4)
        t = o.read_typetree()
        t['m_Script'] = txt
        o.save_typetree(t)
        print('trim updated', clip_name, 'frames', js['frameCount'])

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

    json.dump({k: v for k, v in stat.items()}, open('/workspace/work/v11_trim_stat.json', 'w'), indent=1)

    env2 = UnityPy.load(out)
    objs2 = list(env2.objects)
    print('reload objects', len(objs2))
    assert len(objs2) == 445
    texs = [o for o in objs2 if o.type.name == 'Texture2D']
    nonempty = 0
    tot = 0
    for t in texs:
        tr = t.read_typetree()
        tot += tr['m_CompleteImageSize']
        im = t.read().image
        if im is not None and im.getbbox() is not None:
            nonempty += 1
    print('textures non-empty', nonempty, '/', len(texs), 'astc total %.2f MB' % (tot / 1048576.0))
    print('elapsed %.1fs' % (time.time() - t_start))


if __name__ == '__main__':
    main()
