#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.1.28: 待机改为矢量插值的连续呼吸循环（21 帧全部不同）。

依据（分析官方 SWF 9~30 帧得出的结论）：
- 官方待机并不是逐帧动画，而是 5 个姿势各停 2~3 帧：
    9,10,11=A  12,13=B  14,15=C  16,17,18=A  19,20=D  21,22=E
  （23~30 才是 A/F/G/F 的第三段）；也就是说官方本身就带停顿与段间硬切。
- 每个姿势的身体只是 12 个矢量部件各自做小角度旋转（A 全 0°，
  B 约 -2.8°，C 约 -5.5°，D 约 +3.3°，E 约 +6.8°），
  部件路径几何在各姿势间完全一致 → 可以在矢量层面插值，
  生成真正的中间姿势，不会像位图混合那样出现重影。
- 只有第 11 号部件（水花特效）逐姿势换图案（A 段 80 条路径、
  B/D 26 条、C/E 21 条），无法用变换插值；用原地交叉淡化处理，
  水花本身就是流动的透明效果，淡化看起来就是水在流。

本版做法：
- 21 帧全部由插值生成，不再有重复姿势：
    s(i) = sin(2π(i-1)/21)，s>0 走 A→D→E（右摆），s<0 走 A→B→C（左摆）；
  正弦相位让两端（最左/最右）自然减速、中间过零点速度最快，
  首尾无缝，0.70s / 30fps 周期不变。
- 身体 0~10 号部件：按角度/缩放/位移插值（piecewise 经过官方 B/D）；
- 水花 11 号部件：位置/旋转平滑插值，图案在两个端点之间交叉淡化；
- 画布 586x625、ART_SCALE 2.376 与 v1.1.26/27 完全一致，
  prefab 的 playerPet 框不变，待机显示尺寸不变。
"""
import sys, os, io, re, json, math, time, gc
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
OUT_PLAIN = '/workspace/work/fight3041_v1128.plain'
OUT_ENC = '/workspace/work/fight3041_v1128.bundle'
SVG_DIR = '/workspace/work/swfout/sprites/DefineSprite_139_pet'
PREVIEW = '/workspace/work/v1128_frames'
IDLE_CLIP = '3041_1'
TRIM_NAME = '3041_1.trim'
ART_SCALE = 0.95 * 1.40 * (586.0 / 328.0)   # 2.376，与 v1.1.26/27 相同
CANVAS = (586, 625)
R = v11.RENDER_SCALE
N = 21

os.makedirs(PREVIEW, exist_ok=True)
W, H = CANVAS

_tpl = open(os.path.join(SVG_DIR, '9.svg'), encoding='utf-8').read()


def _span(s):
    m = re.search(r'<g id="sprite1">.*?</g>', s, re.S)
    return m.start(), m.end(), m.group(0)


def _load(f):
    return open(os.path.join(SVG_DIR, '%d.svg' % f), encoding='utf-8').read()


def _uses(f):
    s = _load(f)
    a, b, body = _span(s)
    return re.findall(r'<use\b[^>]*?/>', body)


def _shape11(f):
    s = _load(f)
    d = re.search(r'<defs>(.*)</defs>', s, re.S).group(1)
    return re.search(r'<g id="shape11">.*?</g>', d, re.S).group(0)


def _mats(f):
    return [[float(x) for x in re.search(r'transform="matrix\(([^)]*)\)"', u)
             .group(1).split(',')] for u in _uses(f)]


def _dec(m):
    a, b, c, d, e, f = m
    return math.atan2(b, a), math.hypot(a, b), e, f


def _cm(th, sc, e, f):
    return ('matrix(%.6f,%.6f,%.6f,%.6f,%.4f,%.4f)'
            % (sc * math.cos(th), sc * math.sin(th),
               -sc * math.sin(th), sc * math.cos(th), e, f))


def _lerp(p, q, t):
    out = []
    for m, n in zip(p, q):
        t1, s1, e1, f1 = _dec(m)
        t2, s2, e2, f2 = _dec(n)
        dt = (t2 - t1 + math.pi) % (2 * math.pi) - math.pi
        out.append(_cm(t1 + dt * t, s1 + (s2 - s1) * t,
                       e1 + (e2 - e1) * t, f1 + (f2 - f1) * t))
    return out


U9 = _uses(9)
M = {f: _mats(f) for f in (9, 12, 14, 19, 21)}
S11 = {f: _shape11(f) for f in (9, 12, 14, 19, 21)}


def _splash(tag, href, op, mat):
    x = re.sub(r'transform="matrix\([^)]*\)"', 'transform="%s"' % mat, tag)
    if href != 'shape11':
        x = x.replace('xlink:href="#shape11"', 'xlink:href="#%s"' % href)
    # cairosvg 会忽略 <use opacity>，必须包一层 <g opacity>
    return '<g opacity="%.4f">%s</g>' % (op, x)


def build_svg(fp, fq, u):
    # 淡出的水花必须用起点姿势 fp 的图案（此前固定用 A 的 80 路径水花，
    # 在 D->E / B->C 段会让水花在摆到半程时突然回跳到 A 的大水花）。
    s = _tpl.replace(S11[9], S11[fp], 1)
    a, b, body = _span(s)
    mats = _lerp(M[fp], M[fq], u)
    parts = []
    for k in range(11):
        parts.append(re.sub(r'transform="matrix\([^)]*\)"',
                            'transform="%s"' % mats[k], U9[k]))
    parts.append(_splash(U9[11], 'shape11', 1.0 - u, mats[11]))
    if u > 0.0005:
        parts.append(_splash(_uses(fq)[11], 'shape11b', u, mats[11]))
    s = s[:a] + '<g id="sprite1">\n' + '\n'.join(parts) + '\n    </g>' + s[b:]
    if u > 0.0005:
        s = s.replace(S11[fp], S11[fp] + '\n    ' +
                      S11[fq].replace('<g id="shape11">', '<g id="shape11b">', 1), 1)
    return s


def main():
    t0 = time.time()
    plain = open(SRC_PLAIN, 'rb').read()
    env = UnityPy.load(plain)
    objs = list(env.objects)
    idle = [o for o in objs if o.type.name == 'AnimationClip' and
            o.read_typetree()['m_Name'] == IDLE_CLIP][0].read_typetree()
    order = [p['m_PathID'] for p in idle['m_ClipBindingConstant']['pptrCurveMapping']]
    assert len(order) == N, len(order)
    sprites = {o.path_id: o for o in objs if o.type.name == 'Sprite'}
    tex = {o.path_id: o for o in objs if o.type.name == 'Texture2D'}
    trim_o = [o for o in objs if o.type.name == 'TextAsset' and
              o.read_typetree()['m_Name'] == TRIM_NAME][0]
    js = json.loads(trim_o.read_typetree()['m_Script'].lstrip('\ufeff'))
    assert abs(idle['m_SampleRate'] - 30.0) < 1e-6
    print('idle fps', idle['m_SampleRate'], 'stop', idle['m_MuscleClip']['m_StopTime'],
          'canvas', W, H)

    for i, sid in enumerate(order):
        s = math.sin(2 * math.pi * i / N)
        if s >= 0:
            p0, p1, p2, t = 9, 19, 21, s
        else:
            p0, p1, p2, t = 9, 12, 14, -s
        if t <= 0.5:
            fp, fq, u = p0, p1, 2.0 * t
        else:
            fp, fq, u = p1, p2, 2.0 * t - 1.0
        svg = build_svg(fp, fq, u)
        png = cairosvg.svg2png(bytestring=svg.encode('utf-8'), scale=R)
        im = Image.open(io.BytesIO(png)).convert('RGBA')
        bb = im.getbbox()
        assert bb is not None, (i, fp, fq, u)
        art = im.crop(bb)
        im.close()
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
        # 用 alpha>=32 的可见内容做最终对齐：底边极淡水花在 ASTC 量化后
        # 可能掉到 16 以下，用 32 让底行多留 1px alpha 余量。
        mask = out.split()[3].point(lambda v: 255 if v >= 32 else 0)
        vb = mask.getbbox()
        if vb is not None:
            sdx = int(round((W - (vb[0] + vb[2])) / 2.0))
            sdy = H - vb[3]
            if sdx or sdy:
                shifted = Image.new('RGBA', (W, H), (0, 0, 0, 0))
                shifted.paste(out, (sdx, sdy))
                out.close()
                out = shifted
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
        print('  idle %2d/21 %s->%s u=%.2f  art %dx%d -> %dx%d  %.1fs'
              % (i + 1, fp, fq, u, bb[2] - bb[0], bb[3] - bb[1], nw, nh,
                 time.time() - t0))
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
    o2 = [o for o in env2.objects if o.type.name == 'Sprite' and
          o.path_id == order[0]][0]
    r = o2.read_typetree()['m_Rect']
    print('check sprite', r['width'], r['height'])
    print('elapsed %.1fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
