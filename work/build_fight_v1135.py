#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.1.35: 把三段攻击动画放大到与待机同一像素比例；3042/3043 待机调快到 60fps。

依据（官方 3040 对照 + 当前包实测）：
- 官方 3040 待机贴图 234x332、攻击首帧 238x331 —— 待机与攻击的角色像素比例一致，
  所以放技能时精灵不会突然变小。
- 我们当前 3041/3042/3043 待机美术高 605/612/614，攻击首帧只有 414/407/402（约 0.67），
  放技能瞬间整只精灵缩小三分之一，这就是观感上的“变形”。
- 显示尺寸由贴图像素决定（Image Simple 不保持比例，整块拉伸），因此按比例放大攻击贴图即可。
- 待机官方 3040_1 为 21 帧 @60fps/0.35s，当前 30fps/0.70s，慢一倍。

做法：
- 逐帧重渲染 SVG（放大比例 = 旧比例 * 待机美术高 / 攻击首帧高），保持原帧映射不变：
  * 3041 沿用 v1.1.27 的 seg_map（v10 目标尺寸 + SVG bbox），与线上完全一致；
  * 3042/3043 沿用 v1.1.30 的非空帧线性映射。
- trim 只做“保持中心、底边不动”的尺寸同步：trimX += (旧宽-新宽)/2，trimY 不变，
  trimW/H = 新画布，帧间运动与原来完全一致。
- 3042_1 / 3043_1 关键帧时间改为 60fps（21 帧 / 0.35s），3041_1 不动。
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

SRC_PLAIN = '/workspace/work/fight3041_v1134.plain'
SRC_ENC = ('/workspace/patch_v1.1.34/assets/aa/Android/'
           'fight3041_assets_all_6b19939c69def5b7c66c3cc84ce44beb.bundle')
OUT_PLAIN = '/workspace/work/fight3041_v1135.plain'
OUT_ENC = '/workspace/work/fight3041_v1135.bundle'
V10 = '/workspace/work/fight3041_v10.plain'
SVG41 = '/workspace/work/swfout/sprites'
SS = 2
FPS_IDLE = 60.0

PETS = {
    '3041': dict(scale=2.3744, mode='v10', root=SVG41, clips=[
        ('3041_2', 'DefineSprite_113'),
        ('3041_3', 'DefineSprite_73'),
        ('3041_4', 'DefineSprite_136')]),
    '3042': dict(scale=1.0526, mode='linear', root='/workspace/work/svg3042', clips=[
        ('3042_2', 'DefineSprite_212'),
        ('3042_3', 'DefineSprite_193'),
        ('3042_4', 'DefineSprite_216')]),
    '3043': dict(scale=0.9473, mode='linear', root='/workspace/work/svg3043', clips=[
        ('3043_2', 'DefineSprite_141'),
        ('3043_3', 'DefineSprite_97'),
        ('3043_4', 'DefineSprite_159')]),
}
IDLE_60 = ['3042_1', '3043_1']


def render(url, scale):
    return Image.open(io.BytesIO(cairosvg.svg2png(url=url, scale=scale))).convert('RGBA')


def frames_of(d):
    return [os.path.join(d, f) for f in sorted(os.listdir(d), key=lambda x: int(x.split('.')[0]))]


def mapping_v10(env):
    """与 v1.1.27 完全一致：用 v10（官方 3040 尺寸模板）计算 jmap。"""
    v11.SVG_ROOT = SVG41
    sprites = {o.path_id: o for o in env.objects if o.type.name == 'Sprite'}
    out = {}
    for clip_name, sym in PETS['3041']['clips']:
        clip = next(o for o in env.objects if o.type.name == 'AnimationClip' and
                    o.read_typetree()['m_Name'] == clip_name).read_typetree()
        order = [p['m_PathID'] for p in clip['m_ClipBindingConstant']['pptrCurveMapping']]
        tgt = []
        for sid in order:
            st = sprites[sid].read_typetree()
            tgt.append((int(st['m_Rect']['width']), int(st['m_Rect']['height'])))
        sb = v11.src_bboxes(sym)
        jmap, info = v11.seg_map(tgt, sb)
        assert len(jmap) == len(order)
        out[clip_name] = jmap
        print('map %s keys %d src %d %s' % (clip_name, len(order), len(sb), info[0]))
    return out


def mapping_linear(order, src_dir):
    fs = frames_of(src_dir)
    good = []
    for f in fs:
        im = render(f, 0.25)
        if im.getbbox() is not None:
            good.append(f)
        im.close()
    T, S = len(order), len(good)
    jmap = [int(round(i * (S - 1) / float(T - 1))) if T > 1 else 0 for i in range(T)]
    print('map src %d frames, non-empty %d -> keys %d' % (len(fs), S, T))
    return jmap, good


def retime(clip_obj, n, fps):
    t = clip_obj.read_typetree()
    stream = t['m_MuscleClip']['m_Clip']['data']['m_StreamedClip']['data']
    for k in range(n - 1):
        stream[7 + 7 * k] = struct.unpack('<I', struct.pack('<f', (k + 1) / fps))[0]
    t['m_MuscleClip']['m_Clip']['data']['m_StreamedClip']['data'] = stream
    t['m_MuscleClip']['m_StopTime'] = n / fps
    t['m_MuscleClip']['m_Clip']['data']['m_DenseClip']['m_SampleRate'] = fps
    t['m_SampleRate'] = fps
    clip_obj.save_typetree(t)


def main():
    t0 = time.time()
    plain = open(SRC_PLAIN, 'rb').read()
    env = UnityPy.load(plain)
    bf = list(env.files.values())[0]
    objs = list(env.objects)
    by = {o.path_id: o for o in objs}
    sprites = {o.path_id: o for o in objs if o.type.name == 'Sprite'}
    clips = {o.read_typetree()['m_Name']: o for o in objs if o.type.name == 'AnimationClip'}
    trims = {}
    for o in objs:
        if o.type.name == 'TextAsset':
            t = o.read_typetree()
            if t['m_Name'].endswith('.trim'):
                trims[t['m_Name'][:-5]] = (o, json.loads(t['m_Script'].lstrip('\ufeff')))
    assert len(objs) == 1334, len(objs)

    maps41 = mapping_v10(UnityPy.load(V10))

    for pid, cfg in PETS.items():
        s = cfg['scale']
        for clip_name, sym in cfg['clips']:
            root = cfg['root']
            src_dir = os.path.join(root, sym)
            clip = clips[clip_name].read_typetree()
            order = [p['m_PathID'] for p in clip['m_ClipBindingConstant']['pptrCurveMapping']]
            if cfg['mode'] == 'v10':
                jmap = maps41[clip_name]
                srcs = frames_of(src_dir)
                pick = lambda i: srcs[jmap[i]]
            else:
                jmap, good = mapping_linear(order, src_dir)
                pick = lambda i: good[jmap[i]]
            trim_obj, tri = trims[clip_name]
            tmap = {f['spriteName']: f for f in tri['frames']}
            for i, sid in enumerate(order):
                so = sprites[sid]
                st = so.read_typetree()
                tex = by[st['m_RD']['texture']['m_PathID']]
                im = render(pick(i), s * SS)
                bb = im.getbbox()
                assert bb is not None, (clip_name, i)
                art = im.crop(bb)
                im.close()
                W = max(1, int(round(art.width / float(SS))))
                H = max(1, int(round(art.height / float(SS))))
                canvas = art.resize((W, H), Image.LANCZOS)
                art.close()

                data = v11.encode_astc(canvas)
                canvas.close()
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

                f = tmap[st['m_Name']]
                f['trimX'] = int(round(f['trimX'] + (f['trimW'] - W) / 2.0))
                f['trimW'] = W
                f['trimH'] = H
                gc.collect()
                if (i + 1) % 20 == 0 or i + 1 == len(order):
                    print('  %s %d/%d canvas %dx%d  %.1fs'
                          % (clip_name, i + 1, len(order), W, H, time.time() - t0))

    for clip_name, _ in PETS['3041']['clips'] + PETS['3042']['clips'] + PETS['3043']['clips']:
        o, js = trims[clip_name]
        js['frameCount'] = len(js['frames'])
        t = o.read_typetree()
        t['m_Script'] = '\ufeff' + json.dumps(js, ensure_ascii=False, indent=4)
        o.save_typetree(t)
        print('trim %s frames %d first %dx%d' % (clip_name, js['frameCount'],
                                                 js['frames'][0]['trimW'], js['frames'][0]['trimH']))

    for name in IDLE_60:
        n = len(clips[name].read_typetree()['m_ClipBindingConstant']['pptrCurveMapping'])
        retime(clips[name], n, FPS_IDLE)
        print('idle %s %d keys @%.0ffps stop %.3fs' % (name, n, FPS_IDLE, n / FPS_IDLE))

    out = bf.save(packer='lz4')
    open(OUT_PLAIN, 'wb').write(out)
    _, salt = seer.decrypt(SRC_ENC)
    open(OUT_ENC, 'wb').write(seer.encrypt(out, salt))
    print('plain %d  enc %d  salt %s' % (len(out), os.path.getsize(OUT_ENC), salt.hex()))

    # 自检
    env2 = UnityPy.load(out)
    objs2 = list(env2.objects)
    assert len(objs2) == 1334, len(objs2)
    by2 = {o.path_id: o for o in objs2}
    sp2 = {o.path_id: o for o in objs2 if o.type.name == 'Sprite'}
    cl2 = {o.read_typetree()['m_Name']: o for o in objs2 if o.type.name == 'AnimationClip'}
    for pid, cfg in PETS.items():
        i0 = sp2[next(iter(cl2[pid + '_1'].read_typetree()['m_ClipBindingConstant']
                           ['pptrCurveMapping']))['m_PathID']].read_typetree()
        for clip_name, _ in cfg['clips']:
            ids = [p['m_PathID'] for p in
                   cl2[clip_name].read_typetree()['m_ClipBindingConstant']['pptrCurveMapping']]
            st0 = sp2[ids[0]].read_typetree()
            print('check %s f0 %dx%d  (idle canvas %dx%d)' %
                  (clip_name, int(st0['m_Rect']['width']), int(st0['m_Rect']['height']),
                   int(i0['m_Rect']['width']), int(i0['m_Rect']['height'])))
    for name in IDLE_60:
        c = cl2[name].read_typetree()
        print('check %s rate %.0f stop %.3f' % (name, c['m_SampleRate'], c['m_MuscleClip']['m_StopTime']))
    print('elapsed %.1fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
