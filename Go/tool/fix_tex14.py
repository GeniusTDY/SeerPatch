#!/usr/bin/env python3
"""v1.1.14: 修正加载页贴图白边（使用正确的像素数据偏移 = 对象起点 + 104）"""
import os, shutil, numpy as np
import astc_encoder as A

SRC = '/workspace/work/startup/sharedassets0.assets'
OUTDIR = '/workspace/work/build14'
os.makedirs(OUTDIR, exist_ok=True)

OBJ_START = 51153296
IMG_OFF_IN_OBJ = 104          # m_ImageData 长度前缀之后
IMG_START = OBJ_START + IMG_OFF_IN_OBJ     # 51153400
W, H = 975, 573
IMG_SIZE = 250368
SPLIT = 1048576
BANDS = dict(left=10, right=12, top=7, bottom=15)

data = bytearray(open(SRC, 'rb').read())
assert len(data) == 86168356
# 尾部 m_StreamData 必须为全 0
assert data[OBJ_START + 250472: OBJ_START + 250488] == b'\x00' * 16
# m_CompleteImageSize
assert int.from_bytes(data[OBJ_START + 100:OBJ_START + 104], 'little') == IMG_SIZE

payload = bytes(data[IMG_START:IMG_START + IMG_SIZE])

cfg = A.ASTCConfig(A.ASTCProfile.LDR, 6, 6, 1, quality=A.ASTCQualityPreset.THOROUGH)
ctx = A.ASTCContext(cfg)
swz = A.ASTCSwizzle.from_str('rgba')
img = A.ASTCImage(A.ASTCType.U8, W, H)
ctx.decompress(payload, img, swz)
arr = np.frombuffer(bytes(img.data), dtype=np.uint8).reshape(H, W, 4).copy()

new = arr.copy()
changed = np.zeros((H, W), dtype=bool)
l, r, t, b = BANDS['left'], BANDS['right'], BANDS['top'], BANDS['bottom']
new[:, :l] = new[:, l:l + 1];        changed[:, :l] = True
new[:, W - r:] = new[:, W - r - 1:W - r]; changed[:, W - r:] = True
new[:t, :] = new[t:t + 1, :];        changed[:t, :] = True
new[H - b:, :] = new[H - b - 1:H - b, :]; changed[H - b:, :] = True

enc = ctx.compress(A.ASTCImage(A.ASTCType.U8, W, H, data=new.tobytes()), swz)
enc = bytes(enc)
assert len(enc) == IMG_SIZE, (len(enc), IMG_SIZE)

BX = (W + 5) // 6
BY = (H + 5) // 6
nb = 0
for by in range(BY):
    y0, y1 = by * 6, min(by * 6 + 6, H)
    for bx in range(BX):
        x0, x1 = bx * 6, min(bx * 6 + 6, W)
        if changed[y0:y1, x0:x1].any():
            off = (by * BX + bx) * 16
            data[IMG_START + off:IMG_START + off + 16] = enc[off:off + 16]
            nb += 1
print('changed blocks', nb, 'of', BX * BY)

out = os.path.join(OUTDIR, 'sharedassets0.assets')
open(out, 'wb').write(data)

# 切分并报告差异分片
old = open(SRC, 'rb').read()
diffs = [i for i in range(0, len(old), SPLIT) if old[i:i + SPLIT] != data[i:i + SPLIT]]
print('changed splits', [i // SPLIT for i in diffs])
print('size', len(data))
