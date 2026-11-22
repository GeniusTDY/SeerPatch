#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 v10 预览拼图（每个 clip 一张）。"""
import os, glob
from PIL import Image, ImageDraw

PREV = '/workspace/work/v10_frames'
OUT = '/workspace/work/inspect_img'
os.makedirs(OUT, exist_ok=True)

for clip in ('3041_1', '3041_2', '3041_3', '3041_4'):
    files = sorted(glob.glob(os.path.join(PREV, clip + '_*.png')))
    sel = [files[int(i * (len(files) - 1) / 11.0)] for i in range(12)]
    cell = 260
    sheet = Image.new('RGBA', (cell * 4, (cell + 20) * 3), (25, 25, 25, 255))
    d = ImageDraw.Draw(sheet)
    for k, f in enumerate(sel):
        im = Image.open(f).convert('RGBA')
        im.thumbnail((cell - 6, cell - 6))
        x = (k % 4) * cell
        y = (k // 4) * (cell + 20)
        d.text((x + 4, y + 3), os.path.basename(f)[:-4], fill=(255, 255, 0, 255))
        sheet.alpha_composite(im, (x + 3, y + 20))
    p = os.path.join(OUT, 'v10_sheet_%s.png' % clip)
    sheet.convert('RGB').save(p)
    print('saved', p, sheet.size)
