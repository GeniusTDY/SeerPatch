#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.1.24 bundle 深度审计：待机 3041_1 改走 trim 路径，攻击段保持 v1.1.23。

用法: audit_bundle_v1124.py [bundle] [baseline_v10_plain] [baseline_v11_plain]
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

BUNDLE = sys.argv[1] if len(sys.argv) > 1 else '/workspace/work/fight3041_v1124.bundle'
BASE_PLAIN = sys.argv[2] if len(sys.argv) > 2 else '/workspace/work/fight3041_v10.plain'
V11_PLAIN = sys.argv[3] if len(sys.argv) > 3 else '/workspace/work/fight3041_v11.plain'
NEW_HASH = '6b19939c69def5b7c66c3cc84ce44beb'
IDLE_W, IDLE_H = 459, 490
FAIL = []
OK = []


def check(cond, msg, detail=''):
    (OK if cond else FAIL).append(msg)
    print(('PASS ' if cond else 'FAIL ') + msg + ((' | ' + str(detail)) if detail and not cond else ''))


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


def load_raws(plain):
    env = UnityPy.load(plain)
    objs = list(env.objects)
    c = parse_container(open(plain, 'rb').read())
    cab = c['data'][c['nodes'][0][1]:c['nodes'][0][1] + c['nodes'][0][2]]
    return env, objs, {o.path_id: cab[o.byte_start:o.byte_start + o.byte_size] for o in objs}, cab


def main():
    enc = open(BUNDLE, 'rb').read()
    check(enc[:8] == b'SEERAB01', 'SEERAB01 magic')
    plain, salt = seer.decrypt_bytes(enc)
    check(seer.encrypt(plain, salt) == enc, 'SEERAB01 可复现加密（同一 salt）')
    check(plain[:7] == b'UnityFS', 'UnityFS 签名')
    c = parse_container(plain)
    check(c['total'] == len(plain), 'header total == 文件长度', (c['total'], len(plain)))
    check((c['flags'] & 0x3F) in (2, 3), 'blocks 压缩类型 LZ4', hex(c['flags']))
    check(len(c['info']) == c['ubs'], 'blocksInfo 解压长度', (len(c['info']), c['ubs']))
    check(sum(b[0] for b in c['blocks']) == len(c['data']), 'blocks 解压总长 == 数据区')
    nodes = c['nodes']
    check(len(nodes) == 1 and nodes[0][0].startswith('CAB-'), '节点数量 1（resS 已移除）', nodes)

    env = UnityPy.load(plain)
    sf = list(env.file.files.values())[0]
    objs = list(env.objects)
    by_id = {o.path_id: o for o in objs}
    cab = c['data'][nodes[0][1]:nodes[0][1] + nodes[0][2]]
    check(len(cab) == sf.header.file_size, 'SerializedFile file_size == CAB 节点长度')
    check(cab.count(b'3040') == 0, 'CAB 内无 3040 残留', cab.count(b'3040'))

    from collections import Counter
    cnt = Counter(o.type.name for o in objs)
    check(len(objs) == 446, '对象总数 446', len(objs))
    check(cnt == Counter({'Sprite': 218, 'Texture2D': 218, 'AnimationClip': 4,
                          'TextAsset': 4, 'AssetBundle': 1, 'MonoScript': 1}),
          '对象类型分布正确', dict(cnt))
    ranges = sorted((o.byte_start, o.byte_start + o.byte_size) for o in objs)
    check(all(0 <= a < b <= len(cab) for a, b in ranges), '所有对象区间位于 CAB 内')
    check(all(ranges[i][1] <= ranges[i + 1][0] for i in range(len(ranges) - 1)), '对象区间互不重叠')

    # ---- 与 v10 基线对比 ----
    env0, objs0, raw0, cab0 = load_raws(BASE_PLAIN)
    check(len(objs0) == 445, '基线 v10 445 对象', len(objs0))
    diffs = []
    for o in objs:
        b = cab[o.byte_start:o.byte_start + o.byte_size]
        if b != raw0.get(o.path_id):
            diffs.append((o.type.name, o.path_id))
    check(len(diffs) == 441, '与 v10 raw 不同的对象恰为 441 个', len(diffs))
    check(Counter(d[0] for d in diffs) == Counter({'Sprite': 218, 'Texture2D': 218,
                                                   'TextAsset': 4, 'AssetBundle': 1}),
          '差异对象类型 = 218 Texture2D + 218 Sprite + 4 TextAsset + 1 AB',
          Counter(d[0] for d in diffs))

    # ---- 与 v1.1.23 对比：攻击段必须逐字节一致 ----
    env11, objs11, raw11, _ = load_raws(V11_PLAIN)
    idle_old = [p['m_PathID'] for p in
                [x for x in objs11 if x.type.name == 'AnimationClip'
                 and x.read_typetree()['m_Name'] == '3041_1'][0]
                .read_typetree()['m_ClipBindingConstant']['pptrCurveMapping']]
    expect_changed = set(idle_old)
    for sid in idle_old:
        st = [x for x in objs11 if x.path_id == sid][0].read_typetree()
        expect_changed.add(st['m_RD']['texture']['m_PathID'])
    ab_pid = [o.path_id for o in objs if o.type.name == 'AssetBundle'][0]
    new_trim_pid = [o.path_id for o in objs if o.type.name == 'TextAsset' and
                    o.read_typetree()['m_Name'] == '3041_1.trim'][0]
    expect_changed |= {ab_pid, new_trim_pid}
    changed = {o.path_id for o in objs if raw11.get(o.path_id) !=
               cab[o.byte_start:o.byte_start + o.byte_size]}
    check(changed == expect_changed,
          '仅待机 Sprite/Texture、AB、新增 trim 有变化（攻击与 v1.1.23 逐字节一致）',
          sorted(changed ^ expect_changed)[:5])
    check(len(changed - {ab_pid, new_trim_pid}) == 42,
          '待机变化对象 42（21 Sprite + 21 Texture2D）',
          len(changed - {ab_pid, new_trim_pid}))

    # ---- AB 容器 / Preload ----
    ab = [o for o in objs if o.type.name == 'AssetBundle'][0].read_typetree()
    check(ab['m_Name'] == NEW_HASH + '.bundle', 'AB m_Name 保持新哈希.bundle', ab['m_Name'])
    conts = [p for p, _ in ab['m_Container']]
    exp = {f'Assets/PetAnimation/FightAnimation/3041/3041_{i}.anim' for i in range(1, 5)}
    exp |= {f'Assets/PetAnimation/FightAnimation/3041/3041_{i}/3041_{i}.trim.json'
            for i in (1, 2, 3, 4)}
    check(set(conts) == exp, 'AB 容器路径含 3041_1.trim.json 且无多余项', sorted(set(conts) ^ exp))
    ab11 = [o for o in objs11 if o.type.name == 'AssetBundle'][0].read_typetree()
    check(len(ab['m_PreloadTable']) == 448, 'PreloadTable 448 条', len(ab['m_PreloadTable']))
    check(ab['m_PreloadTable'][:447] == ab11['m_PreloadTable'], '前 447 条与 v1.1.23 完全一致')
    new_asset = ab['m_Container'][-1][1]['asset']['m_PathID']
    check(ab['m_PreloadTable'][447] == {'m_FileID': 0, 'm_PathID': new_asset},
          'PreloadTable 末尾指向新增 trim TextAsset')

    # ---- clip ----
    clips = {o.read_typetree()['m_Name']: o.read_typetree() for o in objs if o.type.name == 'AnimationClip'}
    clips11 = {o.read_typetree()['m_Name']: o.read_typetree() for o in objs11 if o.type.name == 'AnimationClip'}
    check(set(clips) == {'3041_1', '3041_2', '3041_3', '3041_4'}, 'clip 名称 = 3041_1..4', sorted(clips))
    for name in clips:
        check(clips[name] == clips11[name], name + ' 整棵 typetree 与 v1.1.23 一致')

    # ---- trim ----
    trims = {}
    for o in objs:
        if o.type.name == 'TextAsset':
            t = o.read_typetree()
            js = json.loads(t['m_Script'].lstrip('\ufeff'))
            trims[t['m_Name']] = (t, js)
            check(t['m_Name'].endswith('.trim') and js['animKey'] == t['m_Name'][:-5],
                  'TextAsset 名/animKey 正确', (t['m_Name'], js['animKey']))
            check(t['m_Script'].startswith('\ufeff') and
                  t['m_Script'] == '\ufeff' + json.dumps(js, ensure_ascii=False, indent=4),
                  'trim JSON 为 BOM + indent=4', t['m_Name'])
            check(js['frameCount'] == len(js['frames']), 'frameCount == frames 长度', t['m_Name'])
    check(set(trims) == {'3041_1.trim', '3041_2.trim', '3041_3.trim', '3041_4.trim'},
          'TextAsset 名正确（含新增 3041_1.trim）', sorted(trims))
    check({k: v[1]['frameCount'] for k, v in trims.items()} ==
          {'3041_1.trim': 21, '3041_2.trim': 88, '3041_3.trim': 53, '3041_4.trim': 56},
          'trim 帧数 21/88/53/56', {k: v[1]['frameCount'] for k, v in trims.items()})

    spr_by_id = {o.path_id: o for o in objs if o.type.name == 'Sprite'}
    tex_by_id = {o.path_id: o for o in objs if o.type.name == 'Texture2D'}
    bad = []
    for tname, (t, js) in trims.items():
        clip = tname[:-5]
        ids = [p['m_PathID'] for p in clips[clip]['m_ClipBindingConstant']['pptrCurveMapping']]
        if len(ids) != js['frameCount']:
            bad.append((tname, 'clip/frames', len(ids), js['frameCount']))
            continue
        for i, f in enumerate(js['frames']):
            st = spr_by_id[ids[i]].read_typetree()
            W, H = int(st['m_Rect']['width']), int(st['m_Rect']['height'])
            tt = tex_by_id[st['m_RD']['texture']['m_PathID']].read_typetree()
            if st['m_Name'] != f['spriteName']:
                bad.append((tname, i, 'spriteName', st['m_Name'], f['spriteName']))
            if not (f['trimW'] == W and f['trimH'] == H and tt['m_Width'] == W and tt['m_Height'] == H):
                bad.append((tname, i, 'size', (f['trimW'], f['trimH']), (W, H),
                            (tt['m_Width'], tt['m_Height'])))
            if tname == '3041_1.trim':
                if f['trimX'] != 0 or f['trimY'] != 0:
                    bad.append((tname, i, 'offset', f['trimX'], f['trimY']))
                if (f['sourceW'], f['sourceH']) != (W, H):
                    bad.append((tname, i, 'source', (f['sourceW'], f['sourceH']), (W, H)))
    check(not bad, '全部 trim 帧：sprite 对齐；3041_1 中心/底边归零、source=trim 尺寸', bad[:5])

    trims11 = {}
    for o in objs11:
        if o.type.name == 'TextAsset':
            t = o.read_typetree()
            trims11[t['m_Name']] = t['m_Script']
    same = all(trims[k][0]['m_Script'] == trims11[k] for k in
               ('3041_2.trim', '3041_3.trim', '3041_4.trim'))
    check(same, '攻击 3 段 trim JSON 与 v1.1.23 完全一致')

    # ---- Sprite ----
    sprites = [o for o in objs if o.type.name == 'Sprite']
    texs = [o for o in objs if o.type.name == 'Texture2D']
    check(len(sprites) == 218 and len(texs) == 218, 'Sprite/Texture 数量 218/218')
    bad_spr = []
    tex_ref = Counter()
    for o in sprites:
        t = o.read_typetree()
        rd = t['m_RD']
        pid = rd['texture']['m_PathID']
        tex_ref[pid] += 1
        if pid not in tex_by_id:
            bad_spr.append((o.path_id, 'texture missing', pid)); continue
        tt = tex_by_id[pid].read_typetree()
        W, H = tt['m_Width'], tt['m_Height']
        if (t['m_Rect']['x'], t['m_Rect']['y'], t['m_Rect']['width'], t['m_Rect']['height']) != \
                (0.0, 0.0, float(W), float(H)):
            bad_spr.append((o.path_id, 'm_Rect', t['m_Rect'], (W, H)))
        if rd['textureRect'] != {'x': 0.0, 'y': 0.0, 'width': float(W), 'height': float(H)}:
            bad_spr.append((o.path_id, 'textureRect', rd['textureRect']))
        if t['m_IsPolygon'] is not False or t['m_PhysicsShape'] != []:
            bad_spr.append((o.path_id, 'polygon'))
        if rd['m_SubMeshes'] != [{
                'firstByte': 0, 'indexCount': 6, 'topology': 0, 'baseVertex': 0,
                'firstVertex': 0, 'vertexCount': 4,
                'localAABB': {'m_Center': {'x': 0.0, 'y': 0.0, 'z': 0.0},
                              'm_Extent': {'x': 0.0, 'y': 0.0, 'z': 0.0}}}]:
            bad_spr.append((o.path_id, 'submesh'))
        if bytes(rd['m_IndexBuffer']) != struct.pack('<6H', 0, 1, 2, 0, 2, 3):
            bad_spr.append((o.path_id, 'indexbuf'))
        vd = rd['m_VertexData']
        data = bytes(vd['m_DataSize'])
        if vd['m_VertexCount'] != 4 or len(data) != 80:
            bad_spr.append((o.path_id, 'vertex', vd['m_VertexCount'], len(data)))
        else:
            hw, hh = W / 200.0, H / 200.0
            want = [(-hw, -hh, 0.0), (hw, -hh, 0.0), (hw, hh, 0.0), (-hw, hh, 0.0)]
            got = [struct.unpack('<3f', data[i * 12:(i + 1) * 12]) for i in range(4)]
            for g, w in zip(got, want):
                if max(abs(g[j] - w[j]) for j in range(3)) > 1e-4:
                    bad_spr.append((o.path_id, 'verts')); break
        if rd['uvTransform'] != {'x': 100.0, 'y': W / 2.0, 'z': 100.0, 'w': H / 2.0}:
            bad_spr.append((o.path_id, 'uvTransform'))
        if rd['settingsRaw'] != 64 or rd['downscaleMultiplier'] != 1.0:
            bad_spr.append((o.path_id, 'settings'))
        if rd['atlasRectOffset'] != {'x': -1.0, 'y': -1.0}:
            bad_spr.append((o.path_id, 'atlasOffset'))
        if rd['m_Bindpose'] != [] or rd['secondaryTextures'] != []:
            bad_spr.append((o.path_id, 'bindpose/secondary'))
    check(not bad_spr, '218 个 Sprite 矩形/网格/UV/设置全部正确', bad_spr[:5])
    check(set(tex_ref.values()) == {1} and len(tex_ref) == 218, '每个贴图恰好被一个 Sprite 引用')

    # ---- 尺寸 ----
    idle_ids = [p['m_PathID'] for p in clips['3041_1']['m_ClipBindingConstant']['pptrCurveMapping']]
    idle_sizes = {(int(spr_by_id[i].read_typetree()['m_Rect']['width']),
                   int(spr_by_id[i].read_typetree()['m_Rect']['height'])) for i in idle_ids}
    check(idle_sizes == {(IDLE_W, IDLE_H)}, '待机 21 帧统一画布 %dx%d' % (IDLE_W, IDLE_H), idle_sizes)
    att = {}
    for clip in ('3041_2', '3041_3', '3041_4'):
        ids = [p['m_PathID'] for p in clips[clip]['m_ClipBindingConstant']['pptrCurveMapping']]
        att[clip] = len(ids)
    check(att == {'3041_2': 88, '3041_3': 53, '3041_4': 56}, '攻击片段帧数 88/53/56', att)

    # ---- 贴图属性 / 像素 ----
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

    empty, grand = [], []
    for o in sprites:
        t = o.read_typetree()
        im = tex_by_id[t['m_RD']['texture']['m_PathID']].read().image
        if im is None:
            empty.append(('none', o.path_id)); continue
        im = im.convert('RGBA')
        bb = im.getbbox()
        if bb is None:
            empty.append(('empty', o.path_id)); continue
        grand.append(bb)
    check(not empty, '218 张贴图解码后均非空', empty[:5])
    def abbox(im, th=16):
        return im.split()[3].point(lambda v: 255 if v >= th else 0).getbbox()

    old_bb = {}
    by11 = {x.path_id: x for x in objs11}
    for sid in idle_old:
        t = by11[sid].read_typetree()
        im = by11[t['m_RD']['texture']['m_PathID']].read().image.convert('RGBA')
        old_bb[sid] = abbox(im)
    scale = IDLE_H / 350.0
    bad_bb = []
    for sid in idle_ids:
        t = spr_by_id[sid].read_typetree()
        im = tex_by_id[t['m_RD']['texture']['m_PathID']].read().image.convert('RGBA')
        bb = abbox(im)
        ob = old_bb[sid]
        want_c = (ob[0] + ob[2]) / 2.0 * scale
        if (abs((bb[0] + bb[2]) / 2.0 - want_c) > 4 or abs(bb[3] - ob[3] * scale) > 3
                or abs(bb[2] - bb[0] - (ob[2] - ob[0]) * scale) > 5):
            bad_bb.append((sid, bb, ob, want_c))
    check(not bad_bb, '待机 21 帧为 v1.1.23 等比放大（中心/底边/宽度一致，未裁切）', bad_bb[:3])

    print('\n===== FAIL', len(FAIL), '/ OK', len(OK), '=====')
    for f in FAIL:
        print('  !', f)
    return 0 if not FAIL else 1


if __name__ == '__main__':
    sys.exit(main())
