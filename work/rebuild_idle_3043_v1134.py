#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.1.34: 重建 3043 待机 —— 立绘尺寸由贴图画布本身决定，
不再缩小，改为把画布加宽到能完整容纳翼展。

依据：对战里左右同名精灵显示尺寸相同（playerPet 412.5x486.25 与
enemy 330x389 并不决定大小），官方「古代机械巨人」等大立绘也远超
该框——说明游戏按贴图原尺寸显示。3043 翼展 988x656，按 98% 画布
高度（约 617px）绘制需要约 929px 宽，因此画布改为约 938x625。
"""
import sys, os, io, warnings
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
PLAIN = '/workspace/work/fight3041_v1133.plain'
ENC = '/workspace/patch_v1.1.33/assets/aa/Android/fight3041_assets_all_6b19939c69def5b7c66c3cc84ce44beb.bundle'
OUT_PLAIN = '/workspace/work/fight3041_v1134.plain'
OUT_ENC = '/workspace/work/fight3041_v1134.bundle'
PREVIEW = '/workspace/work/v1134_3043_idle'
H = 625
SS = 2
MARGIN_X, MARGIN_Y = 4, 4
ALPHA_TH = 16


def render(url, scale):
    return Image.open(io.BytesIO(cairosvg.svg2png(url=url, scale=scale))).convert('RGBA')


def frames_of(d):
    return [os.path.join(d, f) for f in sorted(os.listdir(d), key=lambda x: int(x.split('.')[0]))]


def paste_clipped(canvas, im, dx, dy):
    W, Hh = canvas.size
    sx, sy = max(0, -dx), max(0, -dy)
    ex, ey = min(im.width, W - dx), min(im.height, Hh - dy)
    if ex > sx and ey > sy:
        canvas.alpha_composite(im.crop((sx, sy, ex, ey)), (max(0, dx), max(0, dy)))


def main():
    os.makedirs(PREVIEW, exist_ok=True)
    fs = frames_of(SRC)
    assert len(fs) == 25, len(fs)

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
    ux0, uy0 = u[0] / 0.25, u[1] / 0.25
    uw, uh = (u[2] - u[0]) / 0.25, (u[3] - u[1]) / 0.25
    S = (H - 2 * MARGIN_Y) / uh
    W = int(-(-(uw * S) // 1)) + 2 * MARGIN_X
    dx = MARGIN_X - ux0 * S
    dy = H - MARGIN_Y - (uy0 + uh) * S
    print('union %.1fx%.1f  S %.4f  canvas %dx%d  art %.1fx%.1f  dx %.1f dy %.1f'
          % (uw, uh, S, W, H, uw * S, uh * S, dx, dy))

    env = UnityPy.load(open(PLAIN, 'rb').read())
    bf = env.files[list(env.files.keys())[0]]
    sf = bf.files[[k for k in bf.files if not k.endswith('.resS')][0]]
    by = {o.path_id: o for o in sf.objects.values()}
    clip = next(o for o in sf.objects.values()
                if o.type.name == 'AnimationClip' and o.read_typetree()['m_Name'] == '3043_1')
    order = [p['m_PathID'] for p in clip.read_typetree()['m_ClipBindingConstant']['pptrCurveMapping']]
    assert len(order) == 21, len(order)
    m = 24

    for i, sid in enumerate(order):
        j = min(m, max(0, int(round(i * m / float(len(order))))))
        im = render(fs[j], S * SS)
        im = im.resize((max(1, int(round(im.width / SS))),
                        max(1, int(round(im.height / SS)))), Image.LANCZOS)
        canvas = Image.new('RGBA', (W, H), (0, 0, 0, 0))
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

    data = bf.save(packer='lz4')
    open(OUT_PLAIN, 'wb').write(data)
    _, salt = seer.decrypt(ENC)
    open(OUT_ENC, 'wb').write(seer.encrypt(data, salt))
    print('plain %d -> %s  enc %d -> %s'
          % (len(data), OUT_PLAIN, os.path.getsize(OUT_ENC), OUT_ENC))


if __name__ == '__main__':
    main()
