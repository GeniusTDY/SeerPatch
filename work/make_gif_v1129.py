#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 v1.1.28 / v1.1.29 待机对比 GIF 与 v1.1.29 预览 GIF。"""
import sys
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
import warnings
warnings.filterwarnings('ignore')
import UnityPy
import seer
from PIL import Image, ImageDraw, ImageFont

UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'

OLD = '/workspace/patch_v1.1.28/assets/aa/Android/fight3041_assets_all_6b19939c69def5b7c66c3cc84ce44beb.bundle'
NEW = '/workspace/work/fight3041_v1128.bundle'
BG = (240, 242, 246)
SIZE = (280, 299)
DUR = 30


def idle_frames(path):
    plain, _ = seer.decrypt_bytes(open(path, 'rb').read())
    env = UnityPy.load(plain)
    objs = list(env.objects)
    clip = [o for o in objs if o.type.name == 'AnimationClip' and
            o.read_typetree()['m_Name'] == '3041_1'][0].read_typetree()
    order = [p['m_PathID'] for p in clip['m_ClipBindingConstant']['pptrCurveMapping']]
    spr = {o.path_id: o for o in objs if o.type.name == 'Sprite'}
    tex = {o.path_id: o for o in objs if o.type.name == 'Texture2D'}
    out = []
    for sid in order:
        st = spr[sid].read_typetree()
        im = tex[st['m_RD']['texture']['m_PathID']].read().image.convert('RGBA')
        out.append(im)
    return out


def panel(im):
    p = Image.new('RGB', SIZE, BG)
    p.paste(im.resize(SIZE, Image.LANCZOS), (0, 0), im.resize(SIZE, Image.LANCZOS))
    return p


def main():
    old = idle_frames(OLD)
    new = idle_frames(NEW)
    assert len(old) == len(new) == 21, (len(old), len(new))

    # 预览：只有新版
    prev = [panel(im) for im in new]
    prev[0].save('/workspace/preview_v1129.gif', save_all=True,
                 append_images=prev[1:], duration=DUR, loop=0,
                 disposal=2, optimize=True)

    # 对比：左旧右新
    W, H, HEAD, GAP = 572, 325, 26, 12
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 12)
    cmp_frames = []
    for i in range(21):
        c = Image.new('RGB', (W, H), (255, 255, 255))
        c.paste(prev[i], (0, HEAD))
        c.paste(panel(new[i]), (280 + GAP, HEAD))
        d = ImageDraw.Draw(c)
        d.text((8, 7), 'v1.1.28 (splash jumps)', font=font, fill=(70, 70, 78))
        d.text((288 + GAP, 7), 'v1.1.29 (continuous)', font=font, fill=(40, 90, 60))
        cmp_frames.append(c)
    cmp_frames[0].save('/workspace/compare_v1128_v1129.gif', save_all=True,
                       append_images=cmp_frames[1:], duration=DUR, loop=0,
                       disposal=2, optimize=True)
    print('done')


if __name__ == '__main__':
    main()
