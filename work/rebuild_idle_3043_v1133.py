#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.1.33: 重建 3043 待机动画 —— 按「整体等比放进 586x625 画布」的方式缩放。

旧逻辑只按高度适配（0.98 画布高），3043 翼展 1.49 倍高，
宽度需要约 932px，超出 586px 画布，左右各被裁掉约 173px。
新逻辑与官方大翅膀精灵一致：取 25 帧并集包围盒，等比缩放到画布内
（左右各留 4px、底 1px），整只完整显示、不变形、无硬切边。
"""
import sys, os, io, json, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
sys.path.insert(0, '/workspace/work')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
import cairosvg
from PIL import Image
import seer
import build_bundle_v11 as v11

SRC = '/workspace/work/svg3043/DefineSprite_62'
PLAIN = '/workspace/work/fight3041_v1132.plain'
ENC = '/workspace/patch_v1.1.32/assets/aa/Android/fight3041_assets_all_6b19939c69def5b7c66c3cc84ce44beb.bundle'
OUT_PLAIN = '/workspace/work/fight3041_v1133.plain'
OUT_ENC = '/workspace/work/fight3041_v1133.bundle'
PREVIEW = '/workspace/work/v1133_3043_idle'
CANVAS = (586, 625)
SS = 2
MARGIN_X, MARGIN_TOP, MARGIN_BOTTOM = 4, 4, 1
ALPHA_TH = 16


def render(url, scale):
    return Image.open(io.BytesIO(cairosvg.svg2png(url=url, scale=scale))).convert('RGBA')


def frames_of(d):
    return [os.path.join(d, f) for f in sorted(os.listdir(d), key=lambda x: int(x.split('.')[0]))]


def paste_clipped(canvas, im, dx, dy):
    W, H = canvas.size
    sx, sy = max(0, -dx), max(0, -dy)
    ex, ey = min(im.width, W - dx), min(im.height, H - dy)
    if ex > sx and ey > sy:
        canvas.alpha_composite(im.crop((sx, sy, ex, ey)), (max(0, dx), max(0, dy)))


def main():
    os.makedirs(PREVIEW, exist_ok=True)
    fs = frames_of(SRC)
    assert len(fs) == 25, len(fs)

    # 1) 25 帧并集包围盒（自然像素）
    u = None
    for f in fs:
        im = render(f, 0.25)
        m = im.split()[3].point(lambda v: 255 if v >= ALPHA_TH else 0).getbbox()
        im.close()
        if not m:
            continue
        u = list(m) if u is None else [min(u[0], m[0]), min(u[1], m[1]),
                                       max(u[2], m[2]), max(u[3], m[3])]
    assert u, 'empty union'
    uw, uh = (u[2] - u[0]) / 0.25, (u[3] - u[1]) / 0.25
    usable_w = CANVAS[0] - 2 * MARGIN_X
    usable_h = CANVAS[1] - MARGIN_TOP - MARGIN_BOTTOM
    S = min(usable_w / uw, usable_h / uh)
    W = int(round(CANVAS[0]))
    H = int(round(CANVAS[1]))
    dx = MARGIN_X - u[0] / 0.25 * S
    dy = CANVAS[1] - MARGIN_BOTTOM - u[3] / 0.25 * S
    print('union natural %.1fx%.1f  S %.4f  art %.1fx%.1f  dx %.1f dy %.1f'
          % (uw, uh, S, uw * S, uh * S, dx, dy))

    # 2) 载入合并包，定位 3043_1 的 21 帧
    env = UnityPy.load(open(PLAIN, 'rb').read())
    bf = env.files[list(env.files.keys())[0]]
    sf = bf.files[[k for k in bf.files if not k.endswith('.resS')][0]]
    by = {o.path_id: o for o in sf.objects.values()}
    clip = next(o for o in sf.objects.values()
                if o.type.name == 'AnimationClip' and o.read_typetree()['m_Name'] == '3043_1')
    order = [p['m_PathID'] for p in clip.read_typetree()['m_ClipBindingConstant']['pptrCurveMapping']]
    assert len(order) == 21, len(order)
    m = 24

    # 3) 逐帧渲染 + 写回
    for i, sid in enumerate(order):
        j = min(m, max(0, int(round(i * m / float(len(order))))))
        im = render(fs[j], S * SS)
        im = im.resize((max(1, int(round(im.width / SS))),
                        max(1, int(round(im.height / SS)))), Image.LANCZOS)
        canvas = Image.new('RGBA', CANVAS, (0, 0, 0, 0))
        paste_clipped(canvas, im, int(round(dx)), int(round(dy)))
        im.close()
        canvas.save(os.path.join(PREVIEW, '%03d.png' % (i + 1)))

        so = by[sid]
        st = so.read_typetree()
        tex = by[st['m_RD']['texture']['m_PathID']]
        data = v11.encode_astc(canvas)
        expect = ((W + 7) // 8) * ((H + 7) // 8) * 16
        assert len(data) == expect, (len(data), expect)
        tt = tex.read_typetree()
        tt['m_Width'] = W
        tt['m_Height'] = H
        tt['m_CompleteImageSize'] = len(data)
        tt['m_TextureFormat'] = 51
        tt['m_MipCount'] = 1
        tt['image data'] = data
        tt['m_StreamData'] = {'offset': 0, 'size': 0, 'path': ''}
        tex.save_typetree(tt)
        so.save_typetree(v11.patch_sprite(st, W, H, tex.path_id))
        canvas.close()
        if (i + 1) % 7 == 0 or i + 1 == len(order):
            print('   idle %d/%d src#%d' % (i + 1, len(order), j + 1))

    # 4) 保存 + 加密（沿用原 salt）
    data = bf.save(packer='lz4')
    open(OUT_PLAIN, 'wb').write(data)
    _, salt = seer.decrypt(ENC)
    open(OUT_ENC, 'wb').write(seer.encrypt(data, salt))
    print('plain %d -> %s  enc %d -> %s  salt %s'
          % (len(data), OUT_PLAIN, os.path.getsize(OUT_ENC), OUT_ENC, salt.hex()))


if __name__ == '__main__':
    main()
