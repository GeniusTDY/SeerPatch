#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bundle 深度审计：SEERAB01 / UnityFS / 对象引用 / clip-trim-sprite 一致性。"""
import sys, json, struct, hashlib
import UnityPy

sys.path.insert(0, '/workspace/tools')
import seer

BUNDLE = '/workspace/work/fight3041_v8.bundle'
ORIG3040 = '/workspace/work/fight3041.plain'
UnityPy.config.FALLBACK_UNITY_VERSION = '5.6.7f1'

fails = []
def chk(cond, msg):
    print(('PASS  ' if cond else 'FAIL  ') + msg)
    if not cond:
        fails.append(msg)

# ---------- SEERAB01 ----------
enc = open(BUNDLE, 'rb').read()
print('== SEERAB01 ==')
chk(enc[:8] == b'SEERAB01', 'magic SEERAB01')
salt = enc[8:24]; size = struct.unpack('<Q', enc[24:32])[0]
chk(enc[32:64] == seer._h(enc[:32], seer._keys(salt)[1]), '头部 HMAC 正确')
plain, salt2 = seer.decrypt_bytes(enc)
chk(salt2 == salt and len(plain) == size, '解密长度/盐一致 (%d)' % len(plain))
chk(seer.encrypt(plain, salt) == enc, '重新加密可逐字节复现（确定性）')

# ---------- UnityFS ----------
print('== UnityFS ==')
chk(plain[:7] == b'UnityFS', 'signature UnityFS')
p = 8
ver = struct.unpack('>I', plain[p:p+4])[0]; p += 4
e = plain.index(b'\0', p); uv = plain[p:e].decode(); p = e + 1
e = plain.index(b'\0', p); ur = plain[p:e].decode(); p = e + 1
total, cbs, ubs, flags = struct.unpack('>qIII', plain[p:p+20])
print('  ver', ver, 'uv', uv, 'rev', ur, 'total', total, 'cbs', cbs, 'ubs', ubs, 'flags', hex(flags))
chk(total == len(plain), '头部 total == 实际长度')
chk(flags & 0x3F == 2, '压缩类型 = LZ4 (2)')
import lz4.block
header_end = 24  # 签名+版本+两个字符串，尚未读 20 字节头
blocks_start = header_end + (-header_end) % 16
chk(blocks_start % 16 == 0, 'blocks 数据区 16 字节对齐 (0x%x)' % blocks_start)
info_raw = plain[-cbs:]
chk(len(info_raw) == cbs, 'blocksInfo 位于文件尾部，长度 = cbs')
info = lz4.block.decompress(info_raw, uncompressed_size=ubs)
chk(len(info) == ubs, 'blocksInfo 解压长度 = ubs (%d)' % ubs)
chk(info[:16] == hashlib.md5(plain[blocks_start:len(plain)-cbs]).digest(), 'blocksInfo 头 16B = 数据区 MD5')
nblk = struct.unpack('>I', info[16:20])[0]
q = 20; infos = []
for i in range(nblk):
    u, c, f = struct.unpack('>IIH', info[q:q+10]); q += 10; infos.append((u, c, f))
print('  block 数 %d，压缩后合计 %d，解压合计 %d' % (nblk, sum(i[1] for i in infos), sum(i[0] for i in infos)))
chk(blocks_start + sum(i[1] for i in infos) == len(plain) - cbs, '块数据区紧邻 blocksInfo，无缝隙/多余')
chk(all((f & 0x3F) in (0, 2) for _, _, f in infos), '所有块压缩类型为 0/2')
nodes, = struct.unpack('>I', info[q:q+4]); q += 4
dirs = []
for _ in range(nodes):
    off, sz, nfl = struct.unpack('>qqI', info[q:q+20]); q += 20
    e = info.index(b'\0', q); dirs.append((info[q:e].decode(), off, sz)); q = e + 1
print('  nodes:', [d[0] for d in dirs])
chk(nodes == 2 and sum(d[2] for d in dirs) == sum(i[0] for i in infos), '2 个节点且 size 合计 = 解压总长')
chk(dirs[0][0] == dirs[1][0] + '.resS' and not any('3040' in d[0] for d in dirs), '节点名成对且无 3040')
# 解压数据区并与 UnityPy 读到的内容无关地验证
data = bytearray(); pos = blocks_start
for u, c, f in infos:
    blob = plain[pos:pos+c]; pos += c
    data += blob if (f & 0x3F) == 0 else lz4.block.decompress(blob, uncompressed_size=u)
chk(len(data) == sum(i[0] for i in infos), '逐块解压后长度一致 (%d)' % len(data))

# ---------- 对象 ----------
print('== 对象 ==')
env = UnityPy.load(plain)
objs = list(env.objects)
from collections import Counter
cnt = Counter(o.type.name for o in objs)
print('  ', dict(cnt))
chk(len(objs) == 446, '对象总数 446')
chk(cnt['Texture2D'] == 219 and cnt['Sprite'] == 218 and cnt['AnimationClip'] == 4
    and cnt['TextAsset'] == 3 and cnt['AssetBundle'] == 1, '类型分布与 3040 一致')

env0 = UnityPy.load(open(ORIG3040, 'rb').read())
cnt0 = Counter(o.type.name for o in env0.objects)
chk(cnt == cnt0, '类型分布与官方 3040 完全相同')
chk(len(objs) == sum(cnt0.values()), '对象数与官方 3040 相同')

paths = {}
for o in objs:
    paths[o.path_id] = o.type.name

def walk(node, path, out):
    if isinstance(node, dict):
        if 'm_PathID' in node and 'm_FileID' in node:
            out.append((path, node)); return
        for k, v in node.items():
            walk(v, path + '.' + k, out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, path + '[%d]' % i, out)

bad_ext = 0
bad_missing = 0
for o in objs:
    if o.type.name not in ('AnimationClip', 'Sprite', 'AssetBundle', 'MonoScript'):
        continue
    tt = o.read_typetree()
    out = []
    walk(tt, '', out)
    for path, ptr in out:
        if ptr['m_FileID'] != 0:
            bad_ext += 1; print('   外部引用', o.type.name, path, ptr)
        elif ptr['m_PathID'] != 0 and ptr['m_PathID'] not in paths:
            bad_missing += 1; print('   悬空引用', o.type.name, path, ptr)
chk(bad_ext == 0, '无跨文件(外部)引用')
chk(bad_missing == 0, '无悬空 PPtr')

# ---------- Sprite / Texture ----------
print('== Sprite / Texture ==')
tex = {}
for o in objs:
    if o.type.name == 'Texture2D':
        t = o.read_typetree()
        tex[o.path_id] = t
sprites = {}
for o in objs:
    if o.type.name == 'Sprite':
        sprites[o.path_id] = o.read_typetree()
bad = 0
for pid, sp in sprites.items():
    rd = sp['m_RD']
    tp = rd['texture']['m_PathID']
    if tp not in tex:
        bad += 1; print('   sprite 找不到贴图', sp['m_Name'], tp); continue
    t = tex[tp]
    r = sp['m_Rect']
    if r['x'] < -0.01 or r['y'] < -0.01 or r['x'] + r['width'] > t['m_Width'] + 0.01 \
            or r['y'] + r['height'] > t['m_Height'] + 0.01:
        bad += 1; print('   sprite 矩形越界', sp['m_Name'], r, t['m_Width'], t['m_Height'])
chk(bad == 0, '所有 Sprite 的贴图引用与矩形均在贴图范围内')
print('   sprite 唯一名', len({s['m_Name'] for s in sprites.values()}),
      '贴图引用数', len({s['m_RD']['texture']['m_PathID'] for s in sprites.values()}))

# ---------- trim ----------
print('== trim JSON ==')
def read_text(o):
    d = o.read(); s = d.m_Script
    return d.m_Name, (s.decode('utf-8-sig', 'replace') if isinstance(s, (bytes, bytearray)) else s.lstrip('\ufeff'))

trims = {}
for o in objs:
    if o.type.name == 'TextAsset':
        name, txt = read_text(o)
        js = json.loads(txt)
        trims[js['animKey']] = (name, js)
        chk(js['animKey'] == name, '%s: animKey == TextAsset 名' % name)
        chk(js['frameCount'] == len(js['frames']) > 0, '%s: frameCount == frames 数 (%d)' % (name, len(js['frames'])))
        chk(all(f['spriteName'] in {s['m_Name'] for s in sprites.values()} for f in js['frames']),
            '%s: 所有 spriteName 均存在于包内' % name)
        oob = [f for f in js['frames'] if f['trimX'] < 0 or f['trimY'] < 0
               or f['trimX'] + f['trimW'] > f['sourceW'] or f['trimY'] + f['trimH'] > f['sourceH']]
        chk(not oob, '%s: 所有 trim 矩形在 source 内' % name)

# ---------- clip ----------
print('== AnimationClip ==')
clip_info = {}
for o in objs:
    if o.type.name != 'AnimationClip':
        continue
    tt = o.read_typetree()
    out = []
    walk(tt, '', out)
    spr = [ptr for path, ptr in out if paths.get(ptr['m_PathID']) == 'Sprite']
    dur = tt['m_MuscleClip']['m_StopTime']
    frames = round(dur * tt['m_SampleRate'])
    clip_info[tt['m_Name']] = (spr, dur, frames)
    print('  ', tt['m_Name'], 'duration', round(dur, 3), '帧', frames, 'sprite 引用', len(spr))
    chk(len(spr) == frames, '%s: sprite 引用数 == 时长×帧率' % tt['m_Name'])
    names = [sprites[p['m_PathID']]['m_Name'] for p in spr]
    chk(names == [str(i + 1) for i in range(len(names))] or len(set(names)) == len(names),
        '%s: sprite 名称按序/唯一' % tt['m_Name'])
    if tt['m_Name'] in {k.split('_')[0] + '_' + k.split('_')[1] for k in trims}:
        pass

chk(set(clip_info) == {'3041_1', '3041_2', '3041_3', '3041_4'}, '4 个 clip 名称全为 3041_x')

# clip 顺序与 trim 帧序一致
for key, (name, js) in trims.items():
    spr, dur, frames = clip_info[key]
    chk(frames == js['frameCount'], '%s: clip 帧数(%d) == trim frameCount(%d)' % (key, frames, js['frameCount']))
    seq = [sprites[p['m_PathID']]['m_Name'] for p in spr]
    tri = [f['spriteName'] for f in js['frames']]
    chk(seq == tri, '%s: clip sprite 顺序 == trim spriteName 顺序' % key)

# 帧数合计与 Sprite 总数
tot = sum(v[2] for v in clip_info.values())
chk(tot == 218, '4 个 clip 帧数合计 %d == Sprite 总数 218' % tot)
chk(set(range(1, 22)) and all(len({sprites[p['m_PathID']]['m_Name'] for p in clip_info['3041_1'][0]}) == 21 for _ in [0]),
    '3041_1 使用 21 个 Sprite')

# ---------- 文本/命名残留 ----------
print('== 残留检查 ==')
raw = plain
chk(raw.count(b'3040') == 0, 'bundle 内 0 处 3040 (%d)' % raw.count(b'3040'))
chk(raw.count(b'3041') == 4 + 3 + 1, 'bundle 内 3041 出现 %d 次（4 clip 名 + 3 trim 名 + AB 名）' % raw.count(b'3041'))
ab = [o for o in objs if o.type.name == 'AssetBundle'][0].read_typetree()
print('  AB', ab['m_Name'], 'deps', ab.get('m_Dependencies'))
chk(ab['m_Name'] == '6b19939c69def5b7c66c3cc84ce44beb.bundle', '内部 AB 名 = 目录 m_Hash + .bundle')
chk(all('/3041/' in p for p, _ in ab['m_Container']), '容器 7 条全为 3041 路径')

print()
print('FAILS:', len(fails))
for f in fails:
    print(' -', f)
sys.exit(1 if fails else 0)
