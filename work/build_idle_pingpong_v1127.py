#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.1.27: 待机改为“无跳变”的呼吸循环，30fps。

问题定位（用官方 v10 的 3041_1 21 帧贴图与 SWF 逐帧比对确认）：
- 官方 SWF 的 pet 时间轴 9~30 帧其实是 3 段独立动画拼接：
  9-15（A→B→C 左摆）、16-22（A→D→E）、23-30（A→F→G→F）；
- 段与段之间是硬切换（C→A、E→A），官方 Unity 贴图也是逐帧居中后
  拼接，所以官方待机本身就带两次“闪回”；
- v1.1.24~26 沿用这个拼接序列，所以看起来不连贯；另外 v1.1.26 的
  586 宽画布会把 C 姿势（281 源像素宽 ×2.376 = 668）左右各裁掉 41px。

本版做法：
- 只用 A/B/C/D/E 五个姿势做一个完整呼吸循环（左摆再回正、轻微右倾再回正），
  去掉所有段间硬切换：
      A A A | B B | C C C | B B | A A A | D D | E E | D D | A A
  首尾都是 A，循环无缝；
- 每帧单独裁 bbox、按 2.376 倍缩放、水平居中、底边对齐到 586x625 画布，
  位置固定不漂移，只保留姿势本身的旋转与鳍/水花运动；
- 画布与 v1.1.26 完全相同，prefab 框（playerPet 412.5x486.25）不需要再改，
  3041 待机显示尺寸与 v1.1.26 一致；
- clip 保持 v1.1.27 的 30fps / 0.70s（60Hz 下每帧 2 次刷新，节奏均匀）。
"""
import sys, os, io, json, time, gc
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

SRC_PLAIN = '/workspace/work/fight3041_v1127.plain'
SRC_ENC = '/workspace/work/fight3041_v1127.bundle'
OUT_PLAIN = '/workspace/work/fight3041_v1127c.plain'
OUT_ENC = '/workspace/work/fight3041_v1127c.bundle'
SVG_DIR = '/workspace/work/swfout/sprites/DefineSprite_139_pet'
PREVIEW = '/workspace/work/v1127c_frames'
IDLE_CLIP = '3041_1'
TRIM_NAME = '3041_1.trim'
ART_SCALE = 0.95 * 1.40 * (586.0 / 328.0)   # 2.376，与 v1.1.26 相同
CANVAS = (586, 625)   # 与 v1.1.26 相同：显示尺寸完全不变，只改动画序列
# A=9, B=12, C=14, D=19, E=21
PATTERN = [9] * 3 + [12] * 2 + [14] * 3 + [12] * 2 + [9] * 3 + \
          [19] * 2 + [21] * 2 + [19] * 2 + [9] * 2
R = v11.RENDER_SCALE

os.makedirs(PREVIEW, exist_ok=True)
W, H = CANVAS


def main():
    t0 = time.time()
    assert len(PATTERN) == 21, len(PATTERN)
    plain = open(SRC_PLAIN, 'rb').read()
    env = UnityPy.load(plain)
    objs = list(env.objects)
    idle = [o for o in objs if o.type.name == 'AnimationClip' and
            o.read_typetree()['m_Name'] == IDLE_CLIP][0].read_typetree()
    order = [p['m_PathID'] for p in idle['m_ClipBindingConstant']['pptrCurveMapping']]
    assert len(order) == 21, len(order)
    sprites = {o.path_id: o for o in objs if o.type.name == 'Sprite'}
    tex = {o.path_id: o for o in objs if o.type.name == 'Texture2D'}
    trim_o = [o for o in objs if o.type.name == 'TextAsset' and
              o.read_typetree()['m_Name'] == TRIM_NAME][0]
    js = json.loads(trim_o.read_typetree()['m_Script'].lstrip('\ufeff'))
    assert abs(idle['m_SampleRate'] - 30.0) < 1e-6
    print('idle fps', idle['m_SampleRate'], 'stop', idle['m_MuscleClip']['m_StopTime'],
          'canvas', W, H, 'pattern', PATTERN)

    cache = {}
    for p in sorted(set(PATTERN)):
        png = cairosvg.svg2png(url=os.path.join(SVG_DIR, '%d.svg' % p), scale=R)
        cache[p] = Image.open(io.BytesIO(png)).convert('RGBA')

    for i, sid in enumerate(order):
        p = PATTERN[i]
        im = cache[p]
        bb = im.getbbox()
        assert bb is not None, (i, p)
        art = im.crop(bb)
        nw = max(1, int(round(art.width * ART_SCALE / R)))
        nh = max(1, int(round(art.height * ART_SCALE / R)))
        small = art.resize((nw, nh), Image.LANCZOS)
        art.close()
        out = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        dx = (W - nw) // 2
        dy = H - nh
        sx, sy = max(0, -dx), max(0, -dy)
        ex, ey = min(nw, W - dx), min(nh, H - dy)
        if ex > sx and ey > sy:
            out.alpha_composite(small.crop((sx, sy, ex, ey)),
                                (max(0, dx), max(0, dy)))
        small.close()
        out.save(os.path.join(PREVIEW, 'idle_%03d.png' % (i + 1)))
        data = v11.encode_astc(out)
        out.close()
        expect = ((W + 7) // 8) * ((H + 7) // 8) * 16
        assert len(data) == expect, (len(data), expect)

        st = sprites[sid].read_typetree()
        tx = tex[st['m_RD']['texture']['m_PathID']]
        tt = tx.read_typetree()
        tt['m_Width'] = W
        tt['m_Height'] = H
        tt['m_CompleteImageSize'] = len(data)
        tt['m_TextureFormat'] = 51
        tt['m_MipCount'] = 1
        tt['image data'] = data
        tt['m_StreamData'] = {'offset': 0, 'size': 0, 'path': ''}
        tx.save_typetree(tt)

        st = v11.patch_sprite(st, W, H, tx.path_id)
        sprites[sid].save_typetree(st)

        f = js['frames'][i]
        assert st['m_Name'] == f['spriteName'], (st['m_Name'], f['spriteName'])
        f['sourceW'] = W
        f['sourceH'] = H
        f['trimX'] = 0
        f['trimY'] = 0
        f['trimW'] = W
        f['trimH'] = H
        print('  idle %2d/21 pose %d  art %dx%d -> %dx%d  %.1fs'
              % (i + 1, p, bb[2] - bb[0], bb[3] - bb[1], nw, nh, time.time() - t0))
        gc.collect()

    t = trim_o.read_typetree()
    t['m_Script'] = '\ufeff' + json.dumps(js, ensure_ascii=False, indent=4)
    trim_o.save_typetree(t)

    out = list(env.files.values())[0].save(packer='lz4')
    open(OUT_PLAIN, 'wb').write(out)
    _, salt = seer.decrypt(SRC_ENC)
    enc = seer.encrypt(out, salt)
    open(OUT_ENC, 'wb').write(enc)
    print('plain %d enc %d salt %s' % (len(out), len(enc), salt.hex()))

    env2 = UnityPy.load(out)
    o2 = [o for o in env2.objects if o.type.name == 'Sprite' and o.path_id == order[0]][0]
    r = o2.read_typetree()['m_Rect']
    print('check sprite', r['width'], r['height'])
    print('elapsed %.1fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
