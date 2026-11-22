#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.1.30: 为 3042 / 3043 重建全部战斗贴图（待机 21 帧 + 攻击 88/53/56）。

做法与 3041 一致：
- 待机：官方 SWF 身体 sprite 的 25 帧呼吸循环（1==25），固定变换贴入 586x625 画布，
  底边对齐、水平居中，超出部分裁掉；clip 降为 30fps / 0.70s。
- 攻击：源动画逐帧 -> 美术 bbox 画布（自然像素 x ATT_FACTOR），trim 同步改宽高、
  保持中心（trimX += (oldW-newW)/2）；clip 统一 30fps。
- 贴图 ASTC 8x8，同 salt 加密。
"""
import sys, os, io, json, time, gc, struct
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
sys.path.insert(0, '/workspace/work')
import warnings
warnings.filterwarnings('ignore')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
import cairosvg
from PIL import Image
import seer
import build_bundle_v11 as v11

R = 1.0                # 用于缩放的比例基准（cairosvg scale 倍率）
SS = 2                 # 超采样倍数（相对最终画布）
IDLE_CANVAS = (586, 625)
IDLE_FILL = 0.98       # 待机美术高度占画布比例
FPS = 30.0

CFG = {
    '3042': {
        'src_bundle': '/workspace/work/fight3042_v9.bundle',
        'plain': '/workspace/work/fight3042_v9.plain',
        'out_plain': '/workspace/work/fight3042_v1130.plain',
        'out_enc': '/workspace/work/fight3042_v1130.bundle',
        'idle': ('/workspace/work/svg3042/DefineSprite_74', '3042_1'),
        'atk_factor': 0.70,
        'clips': {
            '3042_2': '/workspace/work/svg3042/DefineSprite_212',
            '3042_3': '/workspace/work/svg3042/DefineSprite_193',
            '3042_4': '/workspace/work/svg3042/DefineSprite_216',
        },
        'preview': '/workspace/work/v1130_3042',
    },
    '3043': {
        'src_bundle': '/workspace/work/fight3043_v9.bundle',
        'plain': '/workspace/work/fight3043_v9.plain',
        'out_plain': '/workspace/work/fight3043_v1130.plain',
        'out_enc': '/workspace/work/fight3043_v1130.bundle',
        'idle': ('/workspace/work/svg3043/DefineSprite_62', '3043_1'),
        'atk_factor': 0.62,
        'clips': {
            '3043_2': '/workspace/work/svg3043/DefineSprite_141',
            '3043_3': '/workspace/work/svg3043/DefineSprite_97',
            '3043_4': '/workspace/work/svg3043/DefineSprite_159',
        },
        'preview': '/workspace/work/v1130_3043',
    },
}


def render(url, scale):
    png = cairosvg.svg2png(url=url, scale=scale)
    im = Image.open(io.BytesIO(png)).convert('RGBA')
    return im


def frames_of(d):
    return [os.path.join(d, f) for f in sorted(os.listdir(d), key=lambda x: int(x.split('.')[0]))]


def bbox_alpha(im, th=0):
    if th == 0:
        return im.getbbox()
    a = im.split()[3].point(lambda v: 255 if v >= th else 0)
    return a.getbbox()


def paste_clipped(canvas, im, dx, dy):
    W, H = canvas.size
    sx, sy = max(0, -dx), max(0, -dy)
    ex, ey = min(im.width, W - dx), min(im.height, H - dy)
    if ex > sx and ey > sy:
        canvas.alpha_composite(im.crop((sx, sy, ex, ey)), (max(0, dx), max(0, dy)))


def build_idle(env, by, sprites, clips, trims, cfg, preview):
    d, clip_name = cfg['idle']
    fs = frames_of(d)
    assert len(fs) == 25, len(fs)
    s0 = 0.5
    ref = render(fs[0], s0)
    b0 = ref.getbbox()
    ref.close()
    assert b0, 'empty idle ref'
    nat_w, nat_h = (b0[2] - b0[0]) / s0, (b0[3] - b0[1]) / s0
    target_h = IDLE_CANVAS[1] * IDLE_FILL
    S = target_h * SS / nat_h
    print('idle source natural %.1fx%.1f  scale %.4f  S %.4f' % (nat_w, nat_h, target_h / nat_h, S))

    # 参考帧在最终像素下的 bbox，用于固定平移
    ref = render(fs[0], S)
    rb = ref.getbbox()
    ref.close()
    rb_final = [v / SS for v in rb]
    cx = (rb_final[0] + rb_final[2]) / 2.0
    by_ = rb_final[3]
    dx = IDLE_CANVAS[0] / 2.0 - cx
    dy = IDLE_CANVAS[1] - by_
    print('idle anchor dx %.2f dy %.2f' % (dx, dy))

    clip = clips[clip_name].read_typetree()
    order = [p['m_PathID'] for p in clip['m_ClipBindingConstant']['pptrCurveMapping']]
    n = len(order)
    assert n == 21, n
    m = 24  # 25 帧循环，第 25 帧 == 第 1 帧
    for i, sid in enumerate(order):
        j = int(round(i * m / float(n)))
        j = min(m, max(0, j))
        im = render(fs[j], S)
        im = im.resize((max(1, int(round(im.width / SS))),
                        max(1, int(round(im.height / SS)))), Image.LANCZOS)
        canvas = Image.new('RGBA', IDLE_CANVAS, (0, 0, 0, 0))
        paste_clipped(canvas, im, int(round(dx)), int(round(dy)))
        im.close()
        canvas.save(os.path.join(preview, '%s_%03d.png' % (clip_name, i + 1)))

        so = sprites[sid]
        st = so.read_typetree()
        tex = by[st['m_RD']['texture']['m_PathID']]
        data = v11.encode_astc(canvas)
        W, H = canvas.size
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
        st = v11.patch_sprite(st, W, H, tex.path_id)
        so.save_typetree(st)
        canvas.close()
        gc.collect()
        if (i + 1) % 7 == 0 or i + 1 == n:
            print('   idle %d/%d src#%d' % (i + 1, n, j + 1))
    return clip_name


def build_attack(env, by, sprites, clips, trims, cfg, preview, clip_name, src_dir):
    factor = cfg['atk_factor']
    fs = frames_of(src_dir)
    # 过滤空帧（官方 SWF 里角色离场的帧）
    good = []
    for f in fs:
        im = render(f, 0.25)
        if im.getbbox() is not None:
            good.append(f)
        im.close()
    print('%s source %d frames, non-empty %d' % (clip_name, len(fs), len(good)))

    clip = clips[clip_name].read_typetree()
    order = [p['m_PathID'] for p in clip['m_ClipBindingConstant']['pptrCurveMapping']]
    T, S_ = len(order), len(good)
    trim_obj, tri = trims[clip_name]
    tmap = {f['spriteName']: f for f in tri['frames']}
    base = None
    for i, sid in enumerate(order):
        j = int(round(i * (S_ - 1) / float(T - 1))) if T > 1 else 0
        im = render(good[j], factor * SS)
        stage_w, stage_h = im.size
        bb = im.getbbox()
        assert bb is not None, (clip_name, i, j)
        # 源舞台内相对第一帧的真实位移（1 UI 单位 = 1 源像素 x factor）
        ui_left = bb[0] / SS
        ui_bottom = (stage_h - bb[3]) / SS
        art = im.crop(bb)
        im.close()
        W = max(1, int(round(art.width / SS)))
        H = max(1, int(round(art.height / SS)))
        canvas = art.resize((W, H), Image.LANCZOS)
        art.close()
        canvas.save(os.path.join(preview, '%s_%03d.png' % (clip_name, i + 1)))

        so = sprites[sid]
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

        name = st['m_Name']
        st = v11.patch_sprite(st, W, H, tex.path_id)
        so.save_typetree(st)

        f = tmap[name]
        if base is None:
            # 以模板首帧的 trim 位置为锚点，只叠加源舞台内的真实位移
            base = (f['trimX'], f['trimY'], ui_left, ui_bottom)
        f['trimX'] = int(round(base[0] + (ui_left - base[2])))
        f['trimY'] = int(round(base[1] + (ui_bottom - base[3])))
        f['trimW'] = W
        f['trimH'] = H
        canvas.close()
        gc.collect()
        if (i + 1) % 20 == 0 or i + 1 == T:
            print('   %s %d/%d canvas %dx%d' % (clip_name, i + 1, T, W, H))


def retime(clip_obj, n, fps=FPS):
    t = clip_obj.read_typetree()
    stream = t['m_MuscleClip']['m_Clip']['data']['m_StreamedClip']['data']
    for k in range(n - 1):
        stream[7 + 7 * k] = struct.unpack('<I', struct.pack('<f', (k + 1) / fps))[0]
    t['m_MuscleClip']['m_Clip']['data']['m_StreamedClip']['data'] = stream
    t['m_MuscleClip']['m_StopTime'] = n / fps
    t['m_MuscleClip']['m_Clip']['data']['m_DenseClip']['m_SampleRate'] = fps
    t['m_SampleRate'] = fps
    clip_obj.save_typetree(t)


def main(pid):
    cfg = CFG[pid]
    os.makedirs(cfg['preview'], exist_ok=True)
    t0 = time.time()
    env = UnityPy.load(open(cfg['plain'], 'rb').read())
    objs = list(env.objects)
    by = {o.path_id: o for o in objs}
    sprites = {o.path_id: o for o in objs if o.type.name == 'Sprite'}
    clips = {o.read_typetree()['m_Name']: o for o in objs if o.type.name == 'AnimationClip'}
    trims = {}
    for o in objs:
        if o.type.name == 'TextAsset':
            t = o.read_typetree()
            trims[t['m_Name'][:-5]] = (o, json.loads(t['m_Script'].lstrip('\ufeff')))
    assert set(clips) == {'%s_%d' % (pid, i) for i in (1, 2, 3, 4)}, sorted(clips)

    build_idle(env, by, sprites, clips, trims, cfg, cfg['preview'])
    for clip_name, src in cfg['clips'].items():
        build_attack(env, by, sprites, clips, trims, cfg, cfg['preview'], clip_name, src)

    for clip_name in ('%s_2' % pid, '%s_3' % pid, '%s_4' % pid):
        o, js = trims[clip_name]
        js['frameCount'] = len(js['frames'])
        t = o.read_typetree()
        t['m_Script'] = '\ufeff' + json.dumps(js, ensure_ascii=False, indent=4)
        o.save_typetree(t)
        print('trim %s frames %d first %dx%d' % (clip_name, js['frameCount'],
                                                 js['frames'][0]['trimW'], js['frames'][0]['trimH']))

    for name in ('%s_1' % pid, '%s_2' % pid, '%s_3' % pid, '%s_4' % pid):
        n = len(clips[name].read_typetree()['m_ClipBindingConstant']['pptrCurveMapping'])
        retime(clips[name], n)
        print('clip %s %d keys @%.0ffps stop %.2fs' % (name, n, FPS, n / FPS))

    out = list(env.files.values())[0].save(packer='lz4')
    open(cfg['out_plain'], 'wb').write(out)
    _, salt = seer.decrypt_bytes(open(cfg['src_bundle'], 'rb').read())
    open(cfg['out_enc'], 'wb').write(seer.encrypt(out, salt))
    print('saved', cfg['out_plain'], len(out), 'salt', salt.hex())

    # 自检
    env2 = UnityPy.load(out)
    objs2 = list(env2.objects)
    assert len(objs2) == 445, len(objs2)
    by2 = {o.path_id: o for o in objs2}
    nonempty = 0
    for o in objs2:
        if o.type.name == 'Texture2D':
            im = o.read().image
            if im is not None and im.getbbox() is not None:
                nonempty += 1
    print('textures non-empty', nonempty, '/', sum(1 for o in objs2 if o.type.name == 'Texture2D'))
    for name in ('%s_2' % pid, '%s_3' % pid, '%s_4' % pid):
        tri = json.loads([o for o in objs2 if o.type.name == 'TextAsset' and
                          o.read_typetree()['m_Name'] == name + '.trim'][0]
                         .read_typetree()['m_Script'].lstrip('\ufeff'))
        print(' verify', name, 'frames', tri['frameCount'], 'sizes',
              sorted({(f['trimW'], f['trimH']) for f in tri['frames']})[:3])
    print('elapsed %.1fs' % (time.time() - t0))


if __name__ == '__main__':
    for pid in (sys.argv[1:] or ['3042', '3043']):
        print('=====', pid)
        main(pid)
