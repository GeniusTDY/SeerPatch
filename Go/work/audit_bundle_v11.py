#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v11 bundle 深度审计：以 v10 明文为基线，验证 3041 立绘放大改动。

用法: audit_bundle_v11.py [bundle] [baseline_plain]
"""
import sys, struct, json
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
import warnings
warnings.filterwarnings('ignore')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
from UnityPy.helpers import CompressionHelper
import seer

BUNDLE = sys.argv[1] if len(sys.argv) > 1 else '/workspace/work/fight3041_v11.bundle'
BASE_PLAIN = sys.argv[2] if len(sys.argv) > 2 else '/workspace/work/fight3041_v10.plain'
NEW_HASH = '6b19939c69def5b7c66c3cc84ce44beb'
FAIL = []
OK = []


def check(cond, msg, detail=''):
    (OK if cond else FAIL).append(msg + ((' | ' + str(detail)) if detail and not cond else ''))
    print(('PASS ' if cond else 'FAIL ') + msg + ((' | ' + str(detail)) if detail else ''))


def parse_container(plain):
    q = 12
    e = plain.index(b'\0', q); uv = plain[q:e].decode(); q = e + 1
    e = plain.index(b'\0', q); ue = plain[q:e].decode(); q = e + 1
    total, cbs, ubs, flags = struct.unpack('>qIII', plain[q:q + 20]); q += 20
    header_end = q + (-q) % 16
    if flags & 0x80:
        info_off = len(plain) - cbs
        data_start = header_end
    else:
        info_off = header_end
        data_start = info_off + cbs
        if flags & 0x200:
            data_start += (-data_start) % 16
    raw = plain[info_off:info_off + cbs]
    if (flags & 0x3F) == 1:
        info = CompressionHelper.decompress_lzma(raw)
    elif (flags & 0x3F) in (2, 3):
        info = CompressionHelper.decompress_lz4(raw, ubs)
    else:
        info = raw
    nb = struct.unpack('>I', info[16:20])[0]
    k = 20
    blocks = []
    for _ in range(nb):
        u, c, f = struct.unpack('>IIH', info[k:k + 10]); k += 10
        blocks.append((u, c, f))
    nn = struct.unpack('>I', info[k:k + 4])[0]; k += 4
    nodes = []
    for _ in range(nn):
        off, sz, nf = struct.unpack('>qqI', info[k:k + 20]); k += 20
        e = info.index(b'\0', k); nm = info[k:e].decode(); k = e + 1
        nodes.append((nm, off, sz, nf))
    start = data_start
    data = bytearray()
    for u, c, f in blocks:
        blob = plain[start:start + c]; start += c
        if (f & 0x3F) == 0:
            data += blob
        elif (f & 0x3F) == 1:
            data += CompressionHelper.decompress_lzma(blob)
        elif (f & 0x3F) in (2, 3):
            data += CompressionHelper.decompress_lz4(blob, u)
    return dict(total=total, cbs=cbs, ubs=ubs, flags=flags, info=info, blocks=blocks,
                nodes=nodes, data=bytes(data), start=start, data_start=data_start, uv=uv, ue=ue)


def collect_pptrs(obj, out, path=''):
    if isinstance(obj, dict):
        if 'm_FileID' in obj and 'm_PathID' in obj and len(obj) == 2:
            out.append((obj['m_FileID'], obj['m_PathID'], path))
        else:
            for k, v in obj.items():
                collect_pptrs(v, out, path + '/' + str(k))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            collect_pptrs(v, out, path + '[%d]' % i)


def main():
    enc = open(BUNDLE, 'rb').read()
    check(enc[:8] == b'SEERAB01', 'SEERAB01 magic')
    plain, salt = seer.decrypt_bytes(enc)
    check(seer.encrypt(plain, salt) == enc, 'SEERAB01 可复现加密（同一 salt）')
    check(plain[:7] == b'UnityFS', 'UnityFS 签名')
    c = parse_container(plain)
    check(c['total'] == len(plain), 'header total == 文件长度', (c['total'], len(plain)))
    check(c['flags'] & 0x40 != 0, 'flags 含 blocksInfo 压缩(0x40)', hex(c['flags']))
    check((c['flags'] & 0x3F) in (2, 3), 'blocks 压缩类型 LZ4', hex(c['flags']))
    check(all(b[2] & 0x3F == 2 or b[2] & 0x3F == 3 for b in c['blocks']),
          '全部数据块为 LZ4/LZ4HC', [hex(b[2]) for b in c['blocks']])
    check(len(c['info']) == c['ubs'], 'blocksInfo 解压长度', (len(c['info']), c['ubs']))
    check(sum(b[0] for b in c['blocks']) == len(c['data']), 'blocks 解压总长 == 数据区',
          (sum(b[0] for b in c['blocks']), len(c['data'])))
    expect_size = len(plain) - c['data_start'] - (c['cbs'] if c['flags'] & 0x80 else 0)
    check(sum(b[1] for b in c['blocks']) == expect_size, 'blocks 压缩总长 == 数据区长度',
          (sum(b[1] for b in c['blocks']), expect_size))
    nodes = c['nodes']
    check(len(nodes) == 1, '节点数量 1（resS 已移除）', [n[0] for n in nodes])
    check(nodes[0][0].startswith('CAB-'), '节点名 CAB', nodes[0][0])
    check(nodes[0][1] == 0 and nodes[0][2] == len(c['data']), 'CAB 节点覆盖全部数据区',
          (nodes[0][1], nodes[0][2], len(c['data'])))

    env = UnityPy.load(plain)
    sf = list(env.file.files.values())[0]
    objs = list(env.objects)
    objs_by_id = {o.path_id: o for o in objs}
    cab = c['data'][nodes[0][1]:nodes[0][1] + nodes[0][2]]
    check(len(cab) == sf.header.file_size, 'SerializedFile file_size == CAB 节点长度',
          (len(cab), sf.header.file_size))
    check(cab.count(b'3040') == 0, 'CAB 内无 3040 残留', cab.count(b'3040'))
    check(cab.count(b'3041') == 27, 'CAB 内 3041 出现 27 次', cab.count(b'3041'))

    from collections import Counter
    cnt = Counter(o.type.name for o in objs)
    check(len(objs) == 445, '对象总数 445', len(objs))
    check(cnt == Counter({'Sprite': 218, 'Texture2D': 218, 'AnimationClip': 4,
                          'TextAsset': 3, 'AssetBundle': 1, 'MonoScript': 1}),
          '对象类型分布正确', dict(cnt))
    ranges = sorted((o.byte_start, o.byte_start + o.byte_size) for o in objs)
    check(all(0 <= a < b <= len(cab) for a, b in ranges), '所有对象区间位于 CAB 内')
    check(all(ranges[i][1] <= ranges[i + 1][0] for i in range(len(ranges) - 1)), '对象区间互不重叠')

    # ---- 与 v10 基线逐对象对比 ----
    env0 = UnityPy.load(BASE_PLAIN)
    objs0 = list(env0.objects)
    p0 = parse_container(open(BASE_PLAIN, 'rb').read())
    cab0 = p0['data'][p0['nodes'][0][1]:p0['nodes'][0][1] + p0['nodes'][0][2]]
    raw0 = {o.path_id: cab0[o.byte_start:o.byte_start + o.byte_size] for o in objs0}
    check(len(objs0) == 445, '基线 v10 445 对象', len(objs0))
    check({o.path_id for o in objs} == set(raw0), '对象 path_id 集合与 v10 一致')
    diffs = []
    for o in objs:
        b = cab[o.byte_start:o.byte_start + o.byte_size]
        if b != raw0.get(o.path_id):
            diffs.append((o.type.name, o.path_id, o.byte_size, len(raw0.get(o.path_id, b''))))
    check(len(diffs) == 439, '与 v10 raw 不同的对象恰为 439 个', len(diffs))
    check(Counter(d[0] for d in diffs) == Counter({'Sprite': 218, 'Texture2D': 218,
                                                   'TextAsset': 3}),
          '差异对象类型恰为 218 Texture2D + 218 Sprite + 3 TextAsset',
          Counter(d[0] for d in diffs))
    check(all(d[1] in {o.path_id for o in objs} for d in diffs), '差异对象 path_id 均存在')

    # ---- 结构一致性：clip / trim / AB ----
    ab = [o for o in objs if o.type.name == 'AssetBundle'][0].read_typetree()
    check(ab['m_Name'] == NEW_HASH + '.bundle', 'AB m_Name = 新哈希.bundle', ab['m_Name'])
    check(ab['m_AssetBundleName'] == NEW_HASH + '.bundle', 'AB m_AssetBundleName 正确', ab['m_AssetBundleName'])
    check(ab['m_Dependencies'] == [], 'AB 依赖为空', ab['m_Dependencies'])
    conts = [p for p, _ in ab['m_Container']]
    exp = {f'Assets/PetAnimation/FightAnimation/3041/3041_{i}.anim' for i in range(1, 5)}
    exp |= {f'Assets/PetAnimation/FightAnimation/3041/3041_{i}/3041_{i}.trim.json' for i in (2, 3, 4)}
    check(set(conts) == exp, 'AB 容器路径集合完全正确', sorted(set(conts) ^ exp))
    ab0 = [o for o in objs0 if o.type.name == 'AssetBundle'][0].read_typetree()
    check(ab['m_PreloadTable'] == ab0['m_PreloadTable'], 'PreloadTable 与 v10 完全一致',
          len(ab['m_PreloadTable']))
    check(len(ab['m_PreloadTable']) == 447, 'PreloadTable 447 条', len(ab['m_PreloadTable']))

    clips = {}
    for o in objs:
        if o.type.name == 'AnimationClip':
            t = o.read_typetree()
            clips[t['m_Name']] = t
    clips0 = {o.read_typetree()['m_Name']: o.read_typetree()
              for o in objs0 if o.type.name == 'AnimationClip'}
    check(set(clips) == {f'3041_{i}' for i in range(1, 5)}, 'clip 名称 = 3041_1..4', sorted(clips))
    for name in clips:
        check(clips[name] == clips0[name], name + ' 整棵 typetree 与 v10 一致')
        pptr = clips[name]['m_ClipBindingConstant']['pptrCurveMapping']
        check(all(objs_by_id[p['m_PathID']].type.name == 'Sprite' for p in pptr),
              name + ' pptrCurveMapping 全为 Sprite')

    # ---- trim ----
    trims = {}
    for o in objs:
        if o.type.name == 'TextAsset':
            t = o.read_typetree()
            raw = t['m_Script']
            js = json.loads(raw.lstrip('\ufeff'))
            trims[t['m_Name']] = (raw, js)
            check(t['m_Name'].endswith('.trim') and js['animKey'] == t['m_Name'][:-5],
                  'TextAsset 名 xxx.trim 且 animKey == xxx', (t['m_Name'], js['animKey']))
            check(raw.startswith('\ufeff') and raw == '\ufeff' + json.dumps(js, ensure_ascii=False, indent=4),
                  'trim JSON 为 BOM + indent=4', t['m_Name'])
            check(js['frameCount'] == len(js['frames']), 'trim frameCount == frames 长度', t['m_Name'])
    check(set(trims) == {'3041_2.trim', '3041_3.trim', '3041_4.trim'}, 'TextAsset 名正确', sorted(trims))
    exp_frames = {'3041_2.trim': 88, '3041_3.trim': 53, '3041_4.trim': 56}
    check({k: v[1]['frameCount'] for k, v in trims.items()} == exp_frames, 'trim 帧数 88/53/56',
          {k: v[1]['frameCount'] for k, v in trims.items()})
    trims0 = {}
    for o in objs0:
        if o.type.name == 'TextAsset':
            t = o.read_typetree()
            trims0[t['m_Name']] = json.loads(t['m_Script'].lstrip('\ufeff'))

    tex_by_id = {o.path_id: o for o in objs if o.type.name == 'Texture2D'}
    spr_by_id = {o.path_id: o for o in objs if o.type.name == 'Sprite'}
    bad_trim = []
    for tname, (raw, js) in trims.items():
        clip = tname[:-5]
        ids = [p['m_PathID'] for p in clips[clip]['m_ClipBindingConstant']['pptrCurveMapping']]
        if len(ids) != js['frameCount']:
            bad_trim.append((tname, 'clip/frames', len(ids), js['frameCount']))
            continue
        old = trims0[tname]
        for i, f in enumerate(js['frames']):
            sid = ids[i]
            st = spr_by_id[sid].read_typetree()
            W, H = int(st['m_Rect']['width']), int(st['m_Rect']['height'])
            t = tex_by_id[st['m_RD']['texture']['m_PathID']].read_typetree()
            o = old['frames'][i]
            if st['m_Name'] != f['spriteName']:
                bad_trim.append((tname, i, 'spriteName', st['m_Name'], f['spriteName']))
            if not (f['trimW'] == W and f['trimH'] == H and t['m_Width'] == W and t['m_Height'] == H):
                bad_trim.append((tname, i, 'size', (f['trimW'], f['trimH']), (W, H),
                                 (t['m_Width'], t['m_Height'])))
            if abs((f['trimX'] + f['trimW'] / 2.0) - (o['trimX'] + o['trimW'] / 2.0)) > 1:
                bad_trim.append((tname, i, 'centerX', f['trimX'] + f['trimW'] / 2.0,
                                 o['trimX'] + o['trimW'] / 2.0))
            if f['trimY'] != o['trimY']:
                bad_trim.append((tname, i, 'trimY', f['trimY'], o['trimY']))
            if (f['sourceW'], f['sourceH']) != (o['sourceW'], o['sourceH']):
                bad_trim.append((tname, i, 'source', (f['sourceW'], f['sourceH']),
                                 (o['sourceW'], o['sourceH'])))
    check(not bad_trim, 'trim 全部帧：尺寸/中心/底边/源尺寸与 v10 及 Sprite 对齐', bad_trim[:5])

    # ---- Sprite ----
    sprites = [o for o in objs if o.type.name == 'Sprite']
    texs = [o for o in objs if o.type.name == 'Texture2D']
    check(len(sprites) == 218 and len(texs) == 218, 'Sprite/Texture 数量 218/218',
          (len(sprites), len(texs)))
    sprites0 = {o.path_id: o.read_typetree() for o in objs0 if o.type.name == 'Sprite'}
    bad_spr = []
    tex_ref = Counter()
    for o in sprites:
        t = o.read_typetree()
        rd = t['m_RD']
        pid = rd['texture']['m_PathID']
        tex_ref[pid] += 1
        if pid not in tex_by_id:
            bad_spr.append((o.path_id, 'texture missing', pid))
            continue
        tt = tex_by_id[pid].read_typetree()
        W, H = tt['m_Width'], tt['m_Height']
        t0 = sprites0[o.path_id]
        if t['m_Pivot'] != t0['m_Pivot']:
            bad_spr.append((o.path_id, 'pivot', t['m_Pivot'], t0['m_Pivot']))
        if (t['m_Rect']['x'], t['m_Rect']['y'], t['m_Rect']['width'], t['m_Rect']['height']) != (0.0, 0.0, float(W), float(H)):
            bad_spr.append((o.path_id, 'm_Rect', t['m_Rect'], (W, H)))
        if rd['textureRect'] != {'x': 0.0, 'y': 0.0, 'width': float(W), 'height': float(H)}:
            bad_spr.append((o.path_id, 'textureRect', rd['textureRect']))
        if t['m_IsPolygon'] is not False or t['m_PhysicsShape'] != []:
            bad_spr.append((o.path_id, 'polygon', t['m_IsPolygon'], t['m_PhysicsShape']))
        if rd['m_SubMeshes'] != [{
                'firstByte': 0, 'indexCount': 6, 'topology': 0, 'baseVertex': 0,
                'firstVertex': 0, 'vertexCount': 4,
                'localAABB': {'m_Center': {'x': 0.0, 'y': 0.0, 'z': 0.0},
                              'm_Extent': {'x': 0.0, 'y': 0.0, 'z': 0.0}}}]:
            bad_spr.append((o.path_id, 'submesh', rd['m_SubMeshes']))
        if bytes(rd['m_IndexBuffer']) != struct.pack('<6H', 0, 1, 2, 0, 2, 3):
            bad_spr.append((o.path_id, 'indexbuf', list(bytes(rd['m_IndexBuffer']))))
        vd = rd['m_VertexData']
        if vd['m_VertexCount'] != 4:
            bad_spr.append((o.path_id, 'vertexCount', vd['m_VertexCount']))
        data = bytes(vd['m_DataSize'])
        if len(data) != 80:
            bad_spr.append((o.path_id, 'datasize', len(data)))
        else:
            hw, hh = W / 200.0, H / 200.0
            want = [(-hw, -hh, 0.0), (hw, -hh, 0.0), (hw, hh, 0.0), (-hw, hh, 0.0)]
            got = [struct.unpack('<3f', data[i * 12:(i + 1) * 12]) for i in range(4)]
            for g, w in zip(got, want):
                if max(abs(g[j] - w[j]) for j in range(3)) > 1e-4:
                    bad_spr.append((o.path_id, 'verts', got))
                    break
            uv = [struct.unpack('<2f', data[48 + i * 8:56 + i * 8]) for i in range(4)]
            if any(u != (0.0, 0.0) for u in uv):
                bad_spr.append((o.path_id, 'uv', uv))
        if rd['uvTransform'] != {'x': 100.0, 'y': W / 2.0, 'z': 100.0, 'w': H / 2.0}:
            bad_spr.append((o.path_id, 'uvTransform', rd['uvTransform'], (W, H)))
        if rd['settingsRaw'] != 64:
            bad_spr.append((o.path_id, 'settingsRaw', rd['settingsRaw']))
        if rd['textureRectOffset'] != {'x': 0.0, 'y': 0.0}:
            bad_spr.append((o.path_id, 'rectOffset', rd['textureRectOffset']))
        if rd['atlasRectOffset'] != {'x': -1.0, 'y': -1.0}:
            bad_spr.append((o.path_id, 'atlasOffset', rd['atlasRectOffset']))
        if rd['m_Bindpose'] != [] or rd['secondaryTextures'] != []:
            bad_spr.append((o.path_id, 'bindpose/secondary'))
        if rd['downscaleMultiplier'] != 1.0:
            bad_spr.append((o.path_id, 'downscale', rd['downscaleMultiplier']))
    check(not bad_spr, '218 个 Sprite 的 pivot/矩形/网格/UV/设置全部正确', bad_spr[:5])
    check(set(tex_ref.values()) == {1} and len(tex_ref) == 218, '每个贴图恰好被一个 Sprite 引用')

    # ---- 待机 / 攻击尺寸 ----
    idle_ids = [p['m_PathID'] for p in
                clips['3041_1']['m_ClipBindingConstant']['pptrCurveMapping']]
    idle_sizes = {(int(spr_by_id[i].read_typetree()['m_Rect']['width']),
                   int(spr_by_id[i].read_typetree()['m_Rect']['height'])) for i in idle_ids}
    check(idle_sizes == {(328, 350)}, '待机 21 帧统一画布 328x350', idle_sizes)
    att_sizes = {}
    for clip in ('3041_2', '3041_3', '3041_4'):
        ids = [p['m_PathID'] for p in clips[clip]['m_ClipBindingConstant']['pptrCurveMapping']]
        att_sizes[clip] = len(ids)
    check(att_sizes == {'3041_2': 88, '3041_3': 53, '3041_4': 56}, '攻击片段帧数 88/53/56', att_sizes)

    # ---- 贴图属性 ----
    bad_tex = []
    total_astc = 0
    for o in texs:
        t = o.read_typetree()
        w, h = t['m_Width'], t['m_Height']
        want = ((w + 7) // 8) * ((h + 7) // 8) * 16
        data = t['image data']
        total_astc += len(data)
        if (t['m_TextureFormat'] != 51 or t['m_MipCount'] != 1
                or t['m_StreamData']['size'] != 0 or t['m_StreamData']['path'] != ''
                or t['m_CompleteImageSize'] != want or len(data) != want):
            bad_tex.append((o.path_id, t['m_TextureFormat'], t['m_MipCount'],
                            t['m_StreamData'], t['m_CompleteImageSize'], len(data), want))
    check(not bad_tex, '218 张贴图格式/内联数据长度全部正确（ASTC 8x8）', bad_tex[:3])
    print('ASTC 总长 %.2f MB' % (total_astc / 1048576.0))

    # ---- 像素内容 ----
    empty, cover_low = [], []
    for o in sprites:
        t = o.read_typetree()
        tex = tex_by_id[t['m_RD']['texture']['m_PathID']]
        im = tex.read().image
        if im is None:
            empty.append(('none', tex.path_id)); continue
        im = im.convert('RGBA')
        bb = im.getbbox()
        if bb is None:
            empty.append(('empty', tex.path_id)); continue
        area = (bb[2] - bb[0]) * (bb[3] - bb[1])
        full = im.width * im.height
        if area < full * 0.01:
            cover_low.append((tex.path_id, area / float(full)))
    check(not empty, '218 张贴图解码后均非空', empty[:5])
    check(not cover_low, '218 张贴图内容覆盖率均 >=1%', cover_low[:5])

    print('\n===== FAIL', len(FAIL), '/ OK', len(OK), '=====')
    for f in FAIL:
        print('  !', f)
    return 0 if not FAIL else 1


if __name__ == '__main__':
    sys.exit(main())
