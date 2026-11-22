#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.1.36: 三只精灵对战动画深度优化。

自检发现（v1.1.35）：
1) 3042/3043 的 3 段攻击仍是 30fps（2.933/1.767/1.867 秒），
   而 3041 与官方 3040 均为 60fps（1.467/0.883/0.933 秒）——
   同屏技能时长相差近一倍，3042/3043 明显拖沓。
2) 3042/3043 待机 21 帧几乎完全静止（帧间差 0.43 / 1.07，
   官方 3040 为 1.43），在 60fps 下看不出呼吸。
   源 SWF 的待机本身就近乎静止，这里在重绘时叠加极轻微的
   整体呼吸缩放（锚定脚底/中心，幅度 <1.2%），使待机有生命感。
3) 3043_1.trim 元数据仍是旧画布 586x625（游戏不读取，仅为一致性），
   同步为 938x625。

只改贴图内容、clip 采样率/时长与 trim 元数据，不改对象数量、
容器、帧数、帧映射与 trim 的帧间位移。
"""
import sys, os, io, json, time, gc, struct, math, warnings
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

SRC_PLAIN = '/workspace/work/fight3041_v1135.plain'
SRC_ENC = '/workspace/patch_v1.1.35/assets/aa/Android/fight3041_assets_all_6b19939c69def5b7c66c3cc84ce44beb.bundle'
OUT_PLAIN = '/workspace/work/fight3041_v1136.plain'
OUT_ENC = '/workspace/work/fight3041_v1136.bundle'
PREVIEW = '/workspace/work/v1136_idle'
SS = 2
ALPHA_TH = 16

# 待机源与几何参数（沿用 v1.1.30 / v1.1.34 的画布与锚点）
IDLE = {
    '3042': dict(src='/workspace/work/svg3042/DefineSprite_74', canvas=(586, 625),
                 geom='v1130', sx=0.003, sy=0.012, anchor='bottom'),
    '3043': dict(src='/workspace/work/svg3043/DefineSprite_62', canvas=(938, 625),
                 geom='v1134', sx=0.003, sy=0.010, anchor='center'),
}
RETIME = [(f'304{p}_{k}', 60.0) for p in (2, 3) for k in (2, 3, 4)]
TWO_PI = 6.283185307179586


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


def breathe(canvas, cx, cy, sx, sy):
    """绕 (cx,cy) 做 (sx,sy) 缩放；输出->输入仿射。"""
    a, e = 1.0 / sx, 1.0 / sy
    return canvas.transform(canvas.size, Image.AFFINE,
                            (a, 0.0, cx * (1.0 - a), 0.0, e, cy * (1.0 - e)),
                            resample=Image.BICUBIC)


def geometry(cfg):
    fs = frames_of(cfg['src'])
    assert len(fs) == 25, len(fs)
    W, H = cfg['canvas']
    if cfg['geom'] == 'v1130':
        ref = render(fs[0], 0.5)
        b = ref.getbbox()
        ref.close()
        nat_h = (b[3] - b[1]) / 0.5
        S_render = H * 0.98 * SS / nat_h   # 已含 SS
        ref = render(fs[0], S_render)
        rb = [v / SS for v in ref.getbbox()]
        ref.close()
        dx = W / 2.0 - (rb[0] + rb[2]) / 2.0
        dy = H - rb[3]
    else:  # v1134：25 帧并集 bbox，左右各留 4px；S 为最终像素比例
        u = None
        for f in fs:
            im = render(f, 0.25)
            m = im.split()[3].point(lambda v: 255 if v >= ALPHA_TH else 0).getbbox()
            im.close()
            if not m:
                continue
            u = list(m) if u is None else [min(u[0], m[0]), min(u[1], m[1]),
                                           max(u[2], m[2]), max(u[3], m[3])]
        ux0, uy0 = u[0] / 0.25, u[1] / 0.25
        uw, uh = (u[2] - u[0]) / 0.25, (u[3] - u[1]) / 0.25
        S = (H - 8) / uh
        calc_w = int(-(-(uw * S) // 1)) + 8
        assert calc_w == W, (calc_w, W)
        dx = 4 - ux0 * S
        dy = H - 4 - (uy0 + uh) * S
        S_render = S * SS
    return fs, S_render, dx, dy


def rebuild_idle(by, clips, pet, cfg, preview):
    os.makedirs(preview, exist_ok=True)
    fs, S_render, dx, dy = geometry(cfg)
    W, H = cfg['canvas']
    print('%s idle geom renderScale=%.4f dx=%.2f dy=%.2f canvas=%dx%d' % (pet, S_render, dx, dy, W, H))
    cleaner = clips[pet + '_1'].read_typetree()
    order = [p['m_PathID'] for p in cleaner['m_ClipBindingConstant']['pptrCurveMapping']]
    n = len(order)
    assert n == 21, n
    m = 24
    cx = dx + W / 2.0 if cfg['anchor'] == 'bottom' else W / 2.0
    cy = H if cfg['anchor'] == 'bottom' else H / 2.0
    for i, sid in enumerate(order):
        j = min(m, max(0, int(round(i * m / float(n)))))
        im = render(fs[j], S_render)
        im = im.resize((max(1, int(round(im.width / SS))),
                        max(1, int(round(im.height / SS)))), Image.LANCZOS)
        canvas = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        paste_clipped(canvas, im, int(round(dx)), int(round(dy)))
        im.close()

        phase = TWO_PI * i / float(n)
        sxv = 1.0 + cfg['sx'] * math.sin(phase)
        syv = 1.0 + cfg['sy'] * math.sin(phase)
        canvas = breathe(canvas, cx, cy, sxv, syv)
        canvas.save(os.path.join(preview, '%s_%03d.png' % (pet, i + 1)))

        so = by[sid]
        st = so.read_typetree()
        tex = by[st['m_RD']['texture']['m_PathID']]
        data = v11.encode_astc(canvas)
        expect = ((W + 7) // 8) * ((H + 7) // 8) * 16
        assert len(data) == expect, (len(data), expect)
        tt = tex.read_typetree()
        if i == 0:
            old = tex.read().image.convert('RGBA')
            ov = list(old.split()[3].getdata())
            nv = list(canvas.split()[3].getdata())
            diff = sum(abs(a - b) for a, b in zip(ov, nv)) / float(len(ov))
            print('   %s frame1 vs v1135 mean|alpha diff| %.2f' % (pet, diff))
            old.close()
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
        if (i + 1) % 7 == 0 or i + 1 == n:
            print('   %s idle %d/%d src#%d' % (pet, i + 1, n, j + 1))
        gc.collect()


def retime(clip_obj, fps):
    d = clip_obj.read_typetree()
    n = len(d['m_ClipBindingConstant']['pptrCurveMapping'])
    stream = d['m_MuscleClip']['m_Clip']['data']['m_StreamedClip']['data']
    for k in range(n - 1):
        stream[7 + 7 * k] = struct.unpack('<I', struct.pack('<f', (k + 1) / fps))[0]
    d['m_MuscleClip']['m_Clip']['data']['m_StreamedClip']['data'] = stream
    d['m_MuscleClip']['m_StopTime'] = n / fps
    d['m_MuscleClip']['m_Clip']['data']['m_DenseClip']['m_SampleRate'] = fps
    d['m_SampleRate'] = fps
    clip_obj.save_typetree(d)
    return n, n / fps


def main():
    t0 = time.time()
    env = UnityPy.load(open(SRC_PLAIN, 'rb').read())
    bf = env.files[list(env.files.keys())[0]]
    sf = bf.files[[k for k in bf.files if not k.endswith('.resS')][0]]
    objs = list(sf.objects.values())
    by = {o.path_id: o for o in objs}
    clips = {o.read().m_Name: o for o in objs if o.type.name == 'AnimationClip'}
    trims = {}
    for o in objs:
        if o.type.name == 'TextAsset':
            t = o.read_typetree()
            if t['m_Name'].endswith('.trim'):
                trims[t['m_Name'][:-5]] = (o, json.loads(t['m_Script'].lstrip('\ufeff')))

    for pet, cfg in IDLE.items():
        rebuild_idle(by, clips, pet, cfg, os.path.join(PREVIEW, pet))

    for name, fps in RETIME:
        n, dur = retime(clips[name], fps)
        print('retime %s %d frames @ %g -> %.3fs' % (name, n, fps, dur))

    # 3043_1 trim 元数据同步为 938x625
    o, js = trims['3043_1']
    for f in js['frames']:
        f['sourceW'], f['sourceH'] = 938, 625
        f['trimX'] = f['trimY'] = 0
        f['trimW'], f['trimH'] = 938, 625
    t = o.read_typetree()
    t['m_Script'] = '\ufeff' + json.dumps(js, ensure_ascii=False, indent=4)
    o.save_typetree(t)
    print('3043_1.trim -> 938x625 x%d' % len(js['frames']))

    out = bf.save(packer='lz4')
    open(OUT_PLAIN, 'wb').write(out)
    print('plain saved', len(out))
    _, salt = seer.decrypt(SRC_ENC)
    enc = seer.encrypt(out, salt)
    open(OUT_ENC, 'wb').write(enc)
    print('encrypted', len(enc), 'salt', salt.hex())

    # 自检
    env2 = UnityPy.load(out)
    sf2 = env2.files[list(env2.files.keys())[0]]
    sf2 = sf2.files[[k for k in sf2.files if not k.endswith('.resS')][0]]
    objs2 = list(sf2.objects.values())
    assert len(objs2) == len(objs), (len(objs2), len(objs))
    by2 = {o.path_id: o for o in objs2}
    clips2 = {o.read().m_Name: o for o in objs2 if o.type.name == 'AnimationClip'}
    print('\nself-check:')
    for p in (1, 2, 3):
        for k in (1, 2, 3, 4):
            nm = '304%d_%d' % (p, k)
            d = clips2[nm].read_typetree()
            n = len(d['m_ClipBindingConstant']['pptrCurveMapping'])
            ids = [x['m_PathID'] for x in d['m_ClipBindingConstant']['pptrCurveMapping']]
            W, H = by2[ids[0]].read_typetree()['m_Rect']['width'], by2[ids[0]].read_typetree()['m_Rect']['height']
            print('  %s rate=%g stop=%.3fs frames=%d first=%dx%d' %
                  (nm, d['m_SampleRate'], d['m_MuscleClip']['m_StopTime'], n, W, H))
    print('elapsed %.1fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
