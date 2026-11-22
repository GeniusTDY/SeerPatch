#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.1.27: 攻击 3 段同步放大 1.25 倍 + 待机 30fps 均匀节奏。

背景：
- 待机（3041_1）没有可用的 trim，显示尺寸由 prefab 的 playerPet 框决定；
  v1.1.26 已把该框改为 412.5x486.25（1.25 倍）。
- 攻击（3041_2/3/4）有 trim，显示尺寸 = trimW x trimH（1 源像素 = 1 UI 单位），
  仍是 v1.1.23 的 1.30 倍美术比例，导致放技能时明显缩小。
- 本版把攻击美术比例 1.30 -> 1.625（正好 1.25 倍），trim 尺寸/偏移同步更新，
  保持 v1.1.23 里“待机:攻击”的官方比例不变。
- 待机 21 帧改用 30fps（0.70 秒循环），关键帧间隔与 60Hz/30Hz 刷新都整除，
  消除 25fps 在 60Hz 下的 2/3 帧抖动。

映射沿用 v11 的算法：用 v10 的目标尺寸 + SVG bbox 计算 jmap（与 v11 完全一致）。
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

V10 = '/workspace/work/fight3041_v10.plain'
SRC_PLAIN = '/workspace/work/fight3041_v1126.plain'
SRC_ENC = '/workspace/work/fight3041_v1126.bundle'
OUT_PLAIN = '/workspace/work/fight3041_v1127.plain'
OUT_ENC = '/workspace/work/fight3041_v1127.bundle'
PREVIEW = '/workspace/work/v1127_frames'
SVG_ROOT = '/workspace/work/swfout/sprites'
v11.SVG_ROOT = SVG_ROOT
CLIPS = [('3041_2', 'DefineSprite_113'),
         ('3041_3', 'DefineSprite_73'),
         ('3041_4', 'DefineSprite_136')]
NEW_SCALE = 1.30 * 1.25
IDLE_FPS = 30.0
IDLE_CLIP = '3041_1'

os.makedirs(PREVIEW, exist_ok=True)


def mapping_from_v10(env):
    out = {}
    by = {o.path_id: o for o in env.objects}
    sprites = {o.path_id: o for o in env.objects if o.type.name == 'Sprite'}
    for clip_name, sym in CLIPS:
        clip = [o for o in env.objects if o.type.name == 'AnimationClip' and
                o.read_typetree()['m_Name'] == clip_name][0].read_typetree()
        order = [p['m_PathID'] for p in clip['m_ClipBindingConstant']['pptrCurveMapping']]
        tgt = []
        for sid in order:
            st = sprites[sid].read_typetree()
            tgt.append((int(st['m_Rect']['width']), int(st['m_Rect']['height'])))
        sb = v11.src_bboxes(sym)
        jmap, info = v11.seg_map(tgt, sb)
        d = os.path.join(SVG_ROOT, sym)
        srcs = sorted(os.listdir(d), key=lambda x: int(x.split('.')[0]))
        assert len(jmap) == len(order)
        out[clip_name] = (order, jmap, srcs, info)
        print('map', clip_name, 'frames', len(order), 'src', len(srcs), info[0])
    return out


def main():
    t0 = time.time()
    maps = mapping_from_v10(UnityPy.load(V10))

    plain = open(SRC_PLAIN, 'rb').read()
    env = UnityPy.load(plain)
    objs = list(env.objects)
    by = {o.path_id: o for o in objs}
    sprites = {o.path_id: o for o in objs if o.type.name == 'Sprite'}
    clips = {o.read_typetree()['m_Name']: o for o in objs if o.type.name == 'AnimationClip'}
    trims = {}
    for o in objs:
        if o.type.name == 'TextAsset':
            t = o.read_typetree()
            trims[t['m_Name'][:-5]] = (o, json.loads(t['m_Script'].lstrip('\ufeff')))

    for clip_name, sym in CLIPS:
        order0, jmap, srcs, info = maps[clip_name]
        order = [p['m_PathID'] for p in
                 clips[clip_name].read_typetree()['m_ClipBindingConstant']['pptrCurveMapping']]
        assert order == order0, clip_name
        d = os.path.join(SVG_ROOT, sym)
        trim_obj, tri = trims[clip_name]
        tmap = {f['spriteName']: f for f in tri['frames']}
        for i, sid in enumerate(order):
            so = sprites[sid]
            st = so.read_typetree()
            tex = by[st['m_RD']['texture']['m_PathID']]
            png = cairosvg.svg2png(url=os.path.join(d, srcs[jmap[i]]), scale=v11.RENDER_SCALE)
            im = Image.open(io.BytesIO(png)).convert('RGBA')
            bb = im.getbbox()
            assert bb is not None, (clip_name, i)
            art = im.crop(bb)
            im.close()
            W = max(1, int(round(art.width * NEW_SCALE / v11.RENDER_SCALE)))
            H = max(1, int(round(art.height * NEW_SCALE / v11.RENDER_SCALE)))
            canvas = art.resize((W, H), Image.LANCZOS)
            art.close()
            canvas.save(os.path.join(PREVIEW, '%s_%03d.png' % (clip_name, i + 1)))
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

            st = v11.patch_sprite(st, W, H, tex.path_id)
            so.save_typetree(st)

            f = tmap[st['m_Name']]
            f['trimX'] = int(round(f['trimX'] + (f['trimW'] - W) / 2.0))
            f['trimW'] = W
            f['trimH'] = H
            if (i + 1) % 20 == 0 or i + 1 == len(order):
                print('   %s %d/%d canvas %dx%d  %.1fs' %
                      (clip_name, i + 1, len(order), W, H, time.time() - t0))
            gc.collect()

    # 攻击 trim 写回
    for clip_name, _ in CLIPS:
        o, js = trims[clip_name]
        js['frameCount'] = len(js['frames'])
        t = o.read_typetree()
        t['m_Script'] = '\ufeff' + json.dumps(js, ensure_ascii=False, indent=4)
        o.save_typetree(t)
        print('trim updated', clip_name, 'frames', js['frameCount'],
              'first', js['frames'][0]['trimW'], js['frames'][0]['trimH'])

    # 待机 30fps：21 keys，1/30 步长，0.70s
    idle = clips[IDLE_CLIP].read_typetree()
    order = [p['m_PathID'] for p in idle['m_ClipBindingConstant']['pptrCurveMapping']]
    n = len(order)
    stream = idle['m_MuscleClip']['m_Clip']['data']['m_StreamedClip']['data']
    for k in range(n - 1):
        stream[7 + 7 * k] = struct.unpack('<I', struct.pack('<f', (k + 1) / IDLE_FPS))[0]
    idle['m_MuscleClip']['m_Clip']['data']['m_StreamedClip']['data'] = stream
    idle['m_MuscleClip']['m_StopTime'] = n / IDLE_FPS
    idle['m_MuscleClip']['m_Clip']['data']['m_DenseClip']['m_SampleRate'] = IDLE_FPS
    idle['m_SampleRate'] = IDLE_FPS
    clips[IDLE_CLIP].save_typetree(idle)
    print('idle %d keys @ %.0ffps stop %.2fs' % (n, IDLE_FPS, n / IDLE_FPS))

    out = list(env.files.values())[0].save(packer='lz4')
    open(OUT_PLAIN, 'wb').write(out)
    print('plain saved', len(out))

    _, salt = seer.decrypt(SRC_ENC)
    enc = seer.encrypt(out, salt)
    open(OUT_ENC, 'wb').write(enc)
    print('encrypted', len(enc), 'salt', salt.hex())

    # 自检
    env2 = UnityPy.load(out)
    objs2 = list(env2.objects)
    assert len(objs2) == len(objs), (len(objs2), len(objs))
    by2 = {o.path_id: o for o in objs2}
    for clip_name, sym in CLIPS:
        cl = [o for o in objs2 if o.type.name == 'AnimationClip' and
              o.read_typetree()['m_Name'] == clip_name][0].read_typetree()
        ids = [p['m_PathID'] for p in cl['m_ClipBindingConstant']['pptrCurveMapping']]
        wr = sorted({(int(by2[i].read_typetree()['m_Rect']['width']),
                      int(by2[i].read_typetree()['m_Rect']['height'])) for i in ids})
        print('check', clip_name, len(ids), 'sizes', wr[:3], '...')
    cl = [o for o in objs2 if o.type.name == 'AnimationClip' and
          o.read_typetree()['m_Name'] == IDLE_CLIP][0].read_typetree()
    print('idle sample %.0f stop %.3f' % (cl['m_SampleRate'],
                                          cl['m_MuscleClip']['m_StopTime']))
    print('elapsed %.1fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
