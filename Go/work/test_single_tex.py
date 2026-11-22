#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单贴图端到端测试：渲染->ASTC8x8->typetree->保存->重载解码。"""
import sys, os, time, io
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
import warnings
warnings.filterwarnings('ignore')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
import astc_encoder
from UnityPy.enums import TextureFormat
from UnityPy.streams import EndianBinaryReader
from UnityPy.export.Texture2DConverter import pad_image
import cairosvg
from PIL import Image, ImageDraw

SRC = '/workspace/work/fight3041_v9.plain'
OUT = '/workspace/work/test_single.bundle'

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


def render_frame(svg, scale, canvas, S):
    png = cairosvg.svg2png(url=svg, scale=scale)
    im = Image.open(io.BytesIO(png)).convert('RGBA')
    bb = im.getbbox()
    art = im.crop(bb)
    nw = max(1, int(round(art.width * S / scale)))
    nh = max(1, int(round(art.height * S / scale)))
    art = art.resize((nw, nh), Image.LANCZOS)
    out = Image.new('RGBA', canvas, (0, 0, 0, 0))
    x = (canvas[0] - nw) // 2
    y = canvas[1] - nh
    out.alpha_composite(art, (x, y))
    return out


env = UnityPy.load(SRC)
bf = env.file
resS_name = [k for k in bf.files if k.endswith('.resS')][0]

tex = [o for o in env.objects if o.type.name == 'Texture2D'][0]
tt = tex.read_typetree()
canvas = (tt['m_Width'], tt['m_Height'])
print('texture', tt['m_Name'], canvas)

t0 = time.time()
img = render_frame('/workspace/work/swfsvg/DefineSprite_113/1.svg', 4, canvas, 0.95)
print('render', time.time() - t0, img.size)
img.save('/workspace/work/inspect_img/test_canvas.png')

t0 = time.time()
data = encode_astc(img)
print('encode', len(data), 'expect', ((canvas[0] + 7) // 8) * ((canvas[1] + 7) // 8) * 16,
      'time', time.time() - t0)

tt['m_CompleteImageSize'] = len(data)
tt['m_TextureFormat'] = 51
tt['m_MipCount'] = 1
tt['image data'] = data
tt['m_StreamData'] = {'offset': 0, 'size': 0, 'path': ''}
tex.save_typetree(tt)

_r = EndianBinaryReader(b'')
_r.flags = 0
bf.files[resS_name] = _r
out = bf.save(packer='lz4')
open(OUT, 'wb').write(out)
print('saved', len(out))

env2 = UnityPy.load(out)
tex2 = [o for o in env2.objects if o.type.name == 'Texture2D'][0]
im2 = tex2.read().image.convert('RGBA')
im2.save('/workspace/work/inspect_img/test_decoded.png')
print('decoded', im2.size, 'bbox', im2.getbbox())
print('alpha sum', sum(im2.getchannel('A').getdata()))
