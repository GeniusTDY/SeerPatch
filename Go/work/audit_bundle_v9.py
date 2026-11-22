#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v9 bundle 深度审计：以官方 3040 明文为基线，逐对象/逐引用核对。"""
import sys, struct, hashlib, json
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
import warnings
warnings.filterwarnings('ignore')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
from UnityPy.helpers import CompressionHelper
import seer

BUNDLE = '/workspace/work/fight3041_v9.bundle'
BASE = '/workspace/work/fight3040.bundle'
if len(sys.argv) >= 3:
    BUNDLE, BASE = sys.argv[1], sys.argv[2]
NEW_HASH = '6b19939c69def5b7c66c3cc84ce44beb'
FAIL = []
OK = []


def check(cond, msg, detail=''):
    (OK if cond else FAIL).append(msg + ((' | ' + str(detail)) if detail and not cond else ''))
    print(('PASS ' if cond else 'FAIL ') + msg + ((' | ' + str(detail)) if detail else ''))


def parse_container(plain):
    q = 8 + 4
    e = plain.index(b'\0', q); uv = plain[q:e].decode(); q = e + 1
    e = plain.index(b'\0', q); ue = plain[q:e].decode(); q = e + 1
    total, cbs, ubs, flags = struct.unpack('>qIII', plain[q:q + 20]); q += 20
    info_off = q + (-q) % 16
    if flags & 0x80:
        info_off = len(plain) - cbs
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
    start = info_off + cbs
    if flags & 0x200:
        start += (-start) % 16
    data_start = start
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
    check(c['flags'] & 0x3F == 3, 'blocksInfo 压缩类型 LZ4HC(3)', hex(c['flags']))
    check(c['flags'] & 0x200 != 0, 'flags 含 BlockInfoNeedPaddingAtStart(0x200)', hex(c['flags']))
    check(c['flags'] & 0x40 != 0, 'flags 含 blocksInfo 压缩(0x40)', hex(c['flags']))
    check(c['flags'] & 0x80 == 0, 'flags 不含 blocksInfo 尾部(0x80)', hex(c['flags']))
    check(len(c['info']) == c['ubs'], 'blocksInfo 解压长度', (len(c['info']), c['ubs']))
    check(sum(b[0] for b in c['blocks']) == len(c['data']), 'blocks 解压总长 == 数据区', (sum(b[0] for b in c['blocks']), len(c['data'])))
    check(sum(b[1] for b in c['blocks']) == len(plain) - c['data_start'], 'blocks 压缩总长 == 数据区长度', (sum(b[1] for b in c['blocks']), len(plain) - c['data_start']))
    check(c['data_start'] % 16 == 0, '数据区起点 16 字节对齐', c['data_start'])
    check(all(b[2] & 0x3F == 1 for b in c['blocks']), '全部 block 为 LZMA(1)', [hex(b[2]) for b in c['blocks']])
    nodes = c['nodes']
    check(len(nodes) == 2, '节点数量 2', len(nodes))
    check(nodes[0][0].startswith('CAB-') and nodes[1][0].endswith('.resS'), '节点名 CAB + .resS', [n[0] for n in nodes])
    check(nodes[0][1] == 0 and nodes[1][1] == nodes[0][2], '节点偏移连续', [(n[0], n[1], n[2]) for n in nodes])
    check(nodes[0][2] + nodes[1][2] == len(c['data']), '节点总长 == 数据区')

    env = UnityPy.load(plain)
    sf = list(env.file.files.values())[0]
    objs = list(env.objects)
    objs_by_id = {o.path_id: o for o in objs}
    cab = c['data'][nodes[0][1]:nodes[0][1] + nodes[0][2]]
    ress = c['data'][nodes[1][1]:nodes[1][1] + nodes[1][2]]
    check(len(cab) == sf.header.file_size, 'SerializedFile file_size == CAB 节点长度', (len(cab), sf.header.file_size))
    check(cab.count(b'3040') == 0, 'CAB 内无 3040 残留', cab.count(b'3040'))
    check(cab.count(b'3041') == 27, 'CAB 内 3041 出现 27 次', cab.count(b'3041'))

    from collections import Counter
    cnt = Counter(o.type.name for o in objs)
    check(len(objs) == 445, '对象总数 445（与官方一致）', len(objs))
    check(cnt == Counter({'Sprite': 218, 'Texture2D': 218, 'AnimationClip': 4, 'TextAsset': 3, 'AssetBundle': 1, 'MonoScript': 1}),
          '对象类型分布与官方一致', dict(cnt))
    # 对象区间合法且不重叠
    ranges = sorted((o.byte_start, o.byte_start + o.byte_size) for o in objs)
    check(all(0 <= a < b <= len(cab) for a, b in ranges), '所有对象区间位于 CAB 内')
    check(all(ranges[i][1] <= ranges[i + 1][0] for i in range(len(ranges) - 1)), '对象区间互不重叠')

    # 与官方逐对象 raw 对比
    env0 = UnityPy.load(seer.decrypt_bytes(open(BASE, 'rb').read())[0])
    sf0 = list(env0.file.files.values())[0]
    objs0 = list(env0.objects)
    cab0 = None
    p0 = parse_container(open(BASE, 'rb').read() and seer.decrypt_bytes(open(BASE, 'rb').read())[0])
    cab0 = p0['data'][p0['nodes'][0][1]:p0['nodes'][0][1] + p0['nodes'][0][2]]
    raw0 = {o.path_id: cab0[o.byte_start:o.byte_start + o.byte_size] for o in objs0}
    check(len(objs0) == 445, '官方基线 445 对象', len(objs0))
    check({o.path_id for o in objs} == set(raw0), '对象 path_id 集合与官方一致')
    diffs = []
    for o in objs:
        b = cab[o.byte_start:o.byte_start + o.byte_size]
        if b != raw0.get(o.path_id):
            diffs.append((o.type.name, o.path_id, o.byte_size, len(raw0.get(o.path_id, b''))))
    check(len(diffs) == 8, '与官方 raw 不同的对象恰为 8 个', diffs)
    check(sorted(d[0] for d in diffs) == ['AnimationClip'] * 4 + ['AssetBundle'] + ['TextAsset'] * 3,
          '8 个差异对象类型 = 4 clip + 3 TextAsset + 1 AB', [d[0] for d in diffs])
    check(all(o.byte_size == len(raw0[o.path_id]) for o in objs), '所有对象 byte_size 与官方一致')

    # AB
    ab = [o for o in objs if o.type.name == 'AssetBundle'][0].read_typetree()
    check(ab['m_Name'] == NEW_HASH + '.bundle', 'AB m_Name = 新哈希.bundle', ab['m_Name'])
    check(ab['m_AssetBundleName'] == NEW_HASH + '.bundle', 'AB m_AssetBundleName = 新哈希.bundle', ab['m_AssetBundleName'])
    check(ab['m_Dependencies'] == [], 'AB 依赖为空', ab['m_Dependencies'])
    conts = [p for p, _ in ab['m_Container']]
    check(len(conts) == 7, 'AB 容器 7 条', len(conts))
    check(all('/3041/' in p for p in conts), '容器路径全部为 3041', conts)
    exp = {f'Assets/PetAnimation/FightAnimation/3041/3041_{i}.anim' for i in range(1, 5)}
    exp |= {f'Assets/PetAnimation/FightAnimation/3041/3041_{i}/3041_{i}.trim.json' for i in (2, 3, 4)}
    check(set(conts) == exp, '容器路径集合完全正确', sorted(set(conts) ^ exp))

    # clip / trim
    clips = {}
    for o in objs:
        if o.type.name == 'AnimationClip':
            t = o.read_typetree()
            clips[t['m_Name']] = t
    check(set(clips) == {f'3041_{i}' for i in range(1, 5)}, 'clip 名称 = 3041_1..4', sorted(clips))
    trims = {}
    for o in objs:
        if o.type.name == 'TextAsset':
            t = o.read_typetree()
            js = json.loads(t['m_Script'].lstrip('\ufeff'))
            trims[t['m_Name']] = js
            check(t['m_Name'].endswith('.trim') and js['animKey'] == t['m_Name'][:-5],
                  'TextAsset 名 xxx.trim 且 animKey == xxx', (t['m_Name'], js['animKey']))
            check(js['frameCount'] == len(js['frames']), 'trim frameCount == frames 长度', t['m_Name'])
    check(set(trims) == {'3041_2.trim', '3041_3.trim', '3041_4.trim'}, 'TextAsset 名 = 3041_2/3/4.trim', sorted(trims))
    exp_frames = {'3041_2.trim': 88, '3041_3.trim': 53, '3041_4.trim': 56}
    check({k: v['frameCount'] for k, v in trims.items()} == exp_frames, 'trim 帧数与 3040 基线一致', {k: v['frameCount'] for k, v in trims.items()})
    clip_frames = {}
    for name, t in clips.items():
        pptr = t['m_ClipBindingConstant']['pptrCurveMapping']
        n = len(pptr)
        clip_frames[name] = n
        check(all(objs_by_id[p['m_PathID']].type.name == 'Sprite' for p in pptr), name + ' pptrCurveMapping 全为 Sprite')
        dur = t['m_MuscleClip']['m_StopTime'] - t['m_MuscleClip']['m_StartTime']
        check(abs(dur * t['m_SampleRate'] - n) < 0.51, 'clip 时长*采样率 ≈ 帧数', (name, dur, t['m_SampleRate'], n))
    check(clip_frames == {'3041_1': 21, '3041_2': 88, '3041_3': 53, '3041_4': 56}, 'clip 帧数 21/88/53/56', clip_frames)

    # PPtr 完整性
    ids = {o.path_id for o in objs}
    bad = []
    external = []
    for o in objs:
        try:
            t = o.read_typetree()
        except Exception as e:
            bad.append((o.type.name, o.path_id, 'typetree:' + str(e)))
            continue
        refs = []
        collect_pptrs(t, refs, o.type.name)
        for fid, pid, pth in refs:
            if fid != 0:
                external.append((o.type.name, o.path_id, fid, pid, pth))
            elif pid != 0 and pid not in ids:
                bad.append((o.type.name, o.path_id, pth, pid))
    check(not bad, '全部 PPtr 均可解析（FileID=0）', bad[:5])
    check(not external, '无外部 PPtr（FileID!=0）', external[:5])
    check(len(ab['m_PreloadTable']) == 447, 'AB m_PreloadTable 447 条（与官方一致）', len(ab['m_PreloadTable']))
    check(all(p['m_FileID'] == 0 and p['m_PathID'] in ids for p in ab['m_PreloadTable'] if p['m_PathID'] != 0), 'PreloadTable 全部可解析')
    ab0 = [o for o in objs0 if o.type.name == 'AssetBundle'][0].read_typetree()
    check([p['m_PathID'] for p in ab['m_PreloadTable']] == [p['m_PathID'] for p in ab0['m_PreloadTable']],
          'PreloadTable 与官方逐项一致', len(ab['m_PreloadTable']))
    # trim JSON 除 animKey 外与官方逐字节一致
    trims0 = {}
    for o in objs0:
        if o.type.name == 'TextAsset':
            t = o.read_typetree()
            trims0[t['m_Name'].replace('3040_', '3041_')] = json.loads(t['m_Script'].lstrip('\ufeff'))
    for k, js in trims.items():
        j0 = dict(trims0[k]); j0['animKey'] = js['animKey']
        check(js == j0, 'trim JSON 除 animKey 外与官方一致', k)

    # Sprite / Texture
    sprites = [o for o in objs if o.type.name == 'Sprite']
    texs = [o for o in objs if o.type.name == 'Texture2D']
    tex_by_id = {o.path_id: o for o in texs}
    bad_sprite = []
    for o in sprites:
        t = o.read_typetree()
        rd = t['m_RD']
        pid = rd['texture']['m_PathID']
        if pid not in tex_by_id:
            bad_sprite.append((o.path_id, 'texture missing', pid)); continue
        w = tex_by_id[pid].read_typetree()['m_Width']
        h = tex_by_id[pid].read_typetree()['m_Height']
        r = rd['textureRect']
        x, y, ww, hh = r['x'], r['y'], r['width'], r['height']
        if not (x >= 0 and y >= 0 and x + ww <= w + 0.01 and y + hh <= h + 0.01):
            bad_sprite.append((o.path_id, 'rect out of texture', (x, y, ww, hh, w, h)))
    check(not bad_sprite, '218 个 Sprite 的纹理引用/矩形全部合法', bad_sprite[:5])
    check(len(sprites) == 218 and len(texs) == 218, 'Sprite/Texture 数量 218/218', (len(sprites), len(texs)))

    # trim spriteName 均存在（在本 clip 帧集合中按序对应）
    for name, js in trims.items():
        names = [fr['spriteName'] for fr in js['frames']]
        check(all(isinstance(n, str) and n for n in names), name + ' spriteName 非空')
        check(all(fr['sourceW'] > 0 and fr['sourceH'] > 0 for fr in js['frames']), name + ' sourceW/H > 0')

    print('\n===== FAIL', len(FAIL), '/ OK', len(OK), '=====')
    for f in FAIL:
        print('  !', f)
    return 0 if not FAIL else 1


if __name__ == '__main__':
    sys.exit(main())
