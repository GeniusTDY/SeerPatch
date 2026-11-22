#!/usr/bin/env python3
"""Patch startup: disable Unity splash screen + remove white frame from loading background."""
import os, sys, math, shutil
import numpy as np
import astc_encoder as A
from PIL import Image

SRC = '/workspace/work/startup'
OUT = '/workspace/work/build12'
os.makedirs(OUT, exist_ok=True)

# ---------- 1. splash screen flags in globalgamemanagers ----------
gm = bytearray(open(os.path.join(SRC, 'assets/bin/Data/globalgamemanagers'), 'rb').read())
PS_OBJ = 291168          # PlayerSettings object byte_start
SPLASH_OFF = PS_OBJ + 0x48 + 16  # m_SplashScreenBackgroundColor is 16B
print('flags before:', gm[SPLASH_OFF], gm[SPLASH_OFF + 1])
assert gm[SPLASH_OFF] == 1 and gm[SPLASH_OFF + 1] == 1
gm[SPLASH_OFF] = 0      # m_ShowUnitySplashScreen
gm[SPLASH_OFF + 1] = 0  # m_ShowUnitySplashLogo
open(os.path.join(OUT, 'globalgamemanagers'), 'wb').write(gm)
print('splash flags after:', gm[SPLASH_OFF], gm[SPLASH_OFF + 1])

# ---------- 2. loading background texture (975x573 ASTC 6x6) ----------
SRC_FILE = os.path.join(SRC, 'sharedassets0.assets')
TEX_OFF = 51153296 + 120
TEX_SIZE = 250368
W, H = 975, 573
BANDS = dict(left=10, right=12, top=7, bottom=15)

data = bytearray(open(SRC_FILE, 'rb').read())
payload = bytes(data[TEX_OFF:TEX_OFF + TEX_SIZE])

cfg = A.ASTCConfig(A.ASTCProfile.LDR, 6, 6, 1, quality=A.ASTCQualityPreset.THOROUGH)
ctx = A.ASTCContext(cfg)
img = A.ASTCImage(A.ASTCType.U8, W, H)
ctx.decompress(payload, img, A.ASTCSwizzle.from_str('rgba'))
arr = np.frombuffer(bytes(img.data), dtype=np.uint8).reshape(H, W, 4).copy()

new = arr.copy()
l, r, t, b = BANDS['left'], BANDS['right'], BANDS['top'], BANDS['bottom']
changed = np.zeros((H, W), dtype=bool)
# horizontal edge extend
new[:, :l] = new[:, l:l + 1]
new[:, W - r:] = new[:, W - r - 1:W - r]
changed[:, :l] = True
changed[:, W - r:] = True
# vertical edge extend (uses already extended rows)
new[:t, :] = new[t:t + 1, :]
new[H - b:, :] = new[H - b - 1:H - b, :]
changed[:t, :] = True
changed[H - b:, :] = True

img2 = A.ASTCImage(A.ASTCType.U8, W, H, data=new.tobytes())
enc = ctx.compress(img2, A.ASTCSwizzle.from_str('rgba'))
assert len(enc) == TEX_SIZE, (len(enc), TEX_SIZE)

bw, bh = 6, 6
bw_n = math.ceil(W / bw)
bh_n = math.ceil(H / bh)
out_payload = bytearray(payload)
replaced = 0
for by in range(bh_n):
    for bx in range(bw_n):
        y0, y1 = by * bh, min(H, by * bh + bh)
        x0, x1 = bx * bw, min(W, bx * bw + bw)
        if changed[y0:y1, x0:x1].any():
            k = (by * bw_n + bx) * 16
            out_payload[k:k + 16] = enc[k:k + 16]
            replaced += 1
print('blocks replaced:', replaced, 'of', bw_n * bh_n)
data[TEX_OFF:TEX_OFF + TEX_SIZE] = out_payload
open(os.path.join(OUT, 'sharedassets0.assets'), 'wb').write(data)

# decode patched payload back for verification / preview
chk = A.ASTCImage(A.ASTCType.U8, W, H)
ctx.decompress(bytes(out_payload), chk, A.ASTCSwizzle.from_str('rgba'))
out_arr = np.frombuffer(bytes(chk.data), dtype=np.uint8).reshape(H, W, 4)
Image.fromarray(out_arr, 'RGBA').save(os.path.join(OUT, 'loading_bg_fixed.png'))
diff = np.abs(out_arr.astype(int) - arr.astype(int))
print('changed pixels max diff (non-border):', diff[changed == False].max())
print('border now mean RGB:', out_arr[:t, :, :3].mean(axis=(0, 1)),
      out_arr[:, :l, :3].mean(axis=(0, 1)))

# ---------- 3. split sharedassets0.assets like the APK ----------
CHUNK = 1048576
raw = bytes(data)
n = math.ceil(len(raw) / CHUNK)
print('total', len(raw), 'chunks', n)
for i in range(n):
    part = raw[i * CHUNK:(i + 1) * CHUNK]
    open(os.path.join(OUT, f'sharedassets0.assets.split{i}'), 'wb').write(part)

# report which chunks differ from originals in apk dir
orig = {}
for i in range(n):
    p = os.path.join(SRC, 'sa0/assets/bin/Data', f'sharedassets0.assets.split{i}')
    orig[i] = open(p, 'rb').read()
changed_chunks = [i for i in range(n) if raw[i * CHUNK:(i + 1) * CHUNK] != orig[i]]
print('changed chunks:', changed_chunks)
