#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.1.27: 待机用“公共画布”重建，保留官方左右摆动，消除逐帧居中造成的跳变。

v1.1.24~26 的待机是把每一帧单独裁 bbox 后水平居中，结果把官方待机里
本体左右摆动的动作抹掉了（各姿势本体中心相差最多 103 源像素），
看起来像逐帧幻灯片，用户反馈“不连贯”。

本版做法：
- 10 个官方姿势的并集 bbox 为 (42,380,407,650)；以 v1.1.26 逐帧居中的
  平均位置（各姿势 bbox 中心的加权均值 ≈ 253）为画布中轴，左右对称取
  (42,380,464,650)，所有帧裁同一矩形、同一位置贴入画布，完整保留摆动；
- 画布 1003x642，待机 prefab 框同步改为 781x500，
  使 1 纹理像素 ≈ 0.779 UI 单位（等比，不再有 10% 纵向拉伸）；
- 本体在屏幕上约 438x472，与 v1.1.26 的 396x471 高度一致、宽度恢复正确比例。
"""
import sys, os, io, json, time
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
OUT_PLAIN = '/workspace/work/fight3041_v1127b.plain'
OUT_ENC = '/workspace/work/fight3041_v1127b.bundle'
SVG_DIR = '/workspace/work/swfout/sprites/DefineSprite_139_pet'
PREVIEW = '/workspace/work/v1127b_frames'
POSES = [9, 12, 14, 16, 19, 21, 23, 25, 27, 29]
PATTERN = [POSES[0]] * 3 + [p for p in POSES[1:] for _ in range(2)]
UNION = (42, 380, 464, 650)          # scale-1 公共画布：并集 bbox 以 253 为中轴左右对称
ART_SCALE = 0.95 * 1.40 * (586.0 / 328.0)   # 2.376
R = v11.RENDER_SCALE

os.makedirs(PREVIEW, exist_ok=True)
uw, uh = UNION[2] - UNION[0], UNION[3] - UNION[1]
W = int(round(uw * ART_SCALE))
H = int(round(uh * ART_SCALE))
print('union', uw, uh, 'canvas', W, H)


def main():
    t0 = time.time()
    plain = open(SRC_PLAIN, 'rb').read()
    env = UnityPy.load(plain)
    objs = list(env.objects)
    by = {o.path_id: o for o in objs}
    idle = [o for o in objs if o.type.name == 'AnimationClip' and
            o.read_typetree()['m_Name'] == '3041_1'][0].read_typetree()
    order = [p['m_PathID'] for p in idle['m_ClipBindingConstant']['pptrCurveMapping']]
    assert len(order) == len(PATTERN) == 21
    sprite = {o.path_id: o for o in objs if o.type.name == 'Sprite'}
    tex = {o.path_id: o for o in objs if o.type.name == 'Texture2D'}
    trim_o = [o for o in objs if o.type.name == 'TextAsset' and
              o.read_typetree()['m_Name'] == '3041_1.trim'][0]
    js = json.loads(trim_o.read_typetree()['m_Script'].lstrip('\ufeff'))

    cache = {}
    for p in POSES:
        png = cairosvg.svg2png(url=os.path.join(SVG_DIR, '%d.svg' % p), scale=R)
        cache[p] = Image.open(io.BytesIO(png)).convert('RGBA')
    u = tuple(v * R for v in UNION)
    print('render union at %dx', u)

    for i, sid in enumerate(order):
        p = PATTERN[i]
        im = cache[p].crop(u).resize((W, H), Image.LANCZOS)
        im.save(os.path.join(PREVIEW, 'idle_%03d.png' % (i + 1)))
        data = v11.encode_astc(im)
        im.close()
        expect = ((W + 7) // 8) * ((H + 7) // 8) * 16
        assert len(data) == expect, (len(data), expect)

        st = sprite[sid].read_typetree()
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
        sprite[sid].save_typetree(st)

        f = js['frames'][i]
        assert st['m_Name'] == f['spriteName']
        f['sourceW'] = W
        f['sourceH'] = H
        f['trimX'] = 0
        f['trimY'] = 0
        f['trimW'] = W
        f['trimH'] = H
        if (i + 1) % 5 == 0 or i == 20:
            print('  idle %d/21  %.1fs' % (i + 1, time.time() - t0))

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
    print('check sprite', o2.read_typetree()['m_Rect']['width'], o2.read_typetree()['m_Rect']['height'])
    print('elapsed %.1fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
