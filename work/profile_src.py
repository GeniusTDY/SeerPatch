#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""源 SWF 逐帧运动剖析：bbox / alpha 覆盖率 / 帧间 32x32 签名差。
用法：python profile_src.py <dir> [label]
"""
import sys, os, io, warnings, statistics
warnings.filterwarnings('ignore')
import cairosvg
from PIL import Image

DIR = sys.argv[1]
LABEL = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(DIR)
SCALE = 0.12


def sig(im):
    return list(im.split()[3].resize((32, 32), Image.BILINEAR).getdata())


def mad(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) / float(len(a))


def main():
    files = sorted(os.listdir(DIR), key=lambda x: int(x.split('.')[0]))
    prev = None
    rows = []
    for i, f in enumerate(files):
        png = cairosvg.svg2png(url=os.path.join(DIR, f), scale=SCALE)
        im = Image.open(io.BytesIO(png)).convert('RGBA')
        bb = im.getbbox()
        if bb is None:
            rows.append((i + 1, None, 0, None))
            prev = None
            im.close()
            continue
        cov = sum(1 for v in im.split()[3].getdata() if v > 16) / float(im.width * im.height)
        s = sig(im)
        d = mad(prev, s) if prev is not None else None
        rows.append((i + 1, bb, cov, d))
        prev = s
        im.close()
    ds = [r[3] for r in rows if r[3] is not None]
    med = statistics.median(ds) if ds else 0
    print('### %s  frames=%d  diff median %.2f  max %.2f' % (LABEL, len(files), med, max(ds) if ds else 0))
    line = []
    for r in rows:
        idx, bb, cov, d = r
        if bb is None:
            line.append('%d:EMPTY' % idx)
        else:
            line.append('%d:%dx%d,c%.2f,d%s' % (
                idx, bb[2] - bb[0], bb[3] - bb[1], cov, '-' if d is None else '%.1f' % d))
        if len(line) == 5:
            print('  ' + ' | '.join(line)); line = []
    if line:
        print('  ' + ' | '.join(line))
    # 静止段
    holds = [r[0] for r in rows if r[3] is not None and r[3] < 0.5]
    print('  near-static frames:', holds)


if __name__ == '__main__':
    main()
