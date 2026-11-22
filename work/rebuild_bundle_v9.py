#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v9: 以官方 3040 bundle 明文为基线，仅做等长字节改名（3040->3041、AB 内部名哈希替换），
不经过 UnityPy 重序列化，保持 445 个对象原始数据逐字节不变；UnityFS 结构按官方原样重打包。"""
import struct, sys, hashlib
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
import warnings
warnings.filterwarnings('ignore')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
from UnityPy.helpers import CompressionHelper
from UnityPy.streams import EndianBinaryReader
import seer

SRC = '/workspace/work/fight3040.bundle'
OUT = '/workspace/work/fight3041_v9.bundle'
NEW_HASH = '6b19939c69def5b7c66c3cc84ce44beb'
OLD_HASH = b'806d51af380916b1521aadc4dc817a57'


def parse_container(plain):
    q = 8 + 4
    e = plain.index(b'\0', q); q = e + 1
    e = plain.index(b'\0', q); q = e + 1
    total, cbs, ubs, flags = struct.unpack('>qIII', plain[q:q + 20]); q += 20
    info_off = q + (-q) % 16
    if flags & 0x80:
        info_off = len(plain) - cbs
    raw = plain[info_off:info_off + cbs]
    if (flags & 0x3F) == 1:
        info = CompressionHelper.decompress_lzma(raw)
    elif (flags & 0x3F) in (2, 3):
        info = CompressionHelper.decompress_lz4(raw, ubs)
    elif flags & 0x3F == 0:
        info = raw
    else:
        raise SystemExit('unsupported container compression %d' % (flags & 0x3F))
    assert len(info) == ubs, (len(info), ubs)
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
    data = bytearray()
    for u, c, f in blocks:
        blob = plain[start:start + c]; start += c
        if (f & 0x3F) == 0:
            data += blob
        elif (f & 0x3F) == 1:
            data += CompressionHelper.decompress_lzma(blob)
        elif (f & 0x3F) in (2, 3):
            data += CompressionHelper.decompress_lz4(blob, u)
        else:
            raise SystemExit('unsupported block compression %d' % (f & 0x3F))
    return bytes(data), nodes


def main():
    enc = open(SRC, 'rb').read()
    plain, salt = seer.decrypt_bytes(enc)
    assert plain[:7] == b'UnityFS'
    data, nodes = parse_container(plain)
    print('container', len(plain), 'flags ok, data', len(data), 'nodes', [(n[0], n[2], n[3]) for n in nodes])
    cab = data[nodes[0][1]:nodes[0][1] + nodes[0][2]]
    ress = data[nodes[1][1]:nodes[1][1] + nodes[1][2]]

    n3040 = cab.count(b'3040')
    nhash = cab.count(OLD_HASH)
    print('3040 occurrences', n3040, 'old hash occurrences', nhash)
    assert n3040 == 27, n3040
    assert nhash == 2, nhash
    cab2 = cab.replace(b'3040', b'3041').replace(OLD_HASH, NEW_HASH.encode('ascii'))
    assert len(cab2) == len(cab)
    assert cab2.count(b'3040') == 0 and cab2.count(b'3041') == 27
    assert cab2.count(NEW_HASH.encode()) == 2

    # 用原始 reader 替换文件内容，让 UnityPy 只做 UnityFS 重打包，不触碰 SerializedFile
    env = UnityPy.load(plain)
    bundle = env.file
    names = list(bundle.files.keys())
    assert len(names) == 2 and names[1].endswith('.resS')
    patched = {names[0]: cab2, names[1]: ress}
    readers = {}
    for nm in names:
        r = EndianBinaryReader(patched[nm])
        r.flags = getattr(bundle.files[nm], 'flags', 0)
        readers[nm] = r
    bundle.files = readers
    out = bundle.save(packer='original')
    print('rebuilt container', len(out))
    open('/workspace/work/fight3041_v9.plain', 'wb').write(out)

    enc2 = seer.encrypt(out, salt)
    open(OUT, 'wb').write(enc2)
    print('wrote', OUT, len(enc2), 'plaintext', len(out), 'salt', salt.hex())

    # ---------- 复核 ----------
    env2 = UnityPy.load(out)
    objs = list(env2.objects)
    env0 = UnityPy.load(plain)
    objs0 = list(env0.objects)
    print('objects new', len(objs), 'official', len(objs0))
    assert len(objs) == len(objs0) == 445
    raw0 = {o.path_id: (o.type.name, o.byte_size, cab[o.byte_start:o.byte_start + o.byte_size]) for o in objs0}
    diffs = []
    for o in objs:
        typ, sz, b0 = raw0[o.path_id]
        b = cab2[o.byte_start:o.byte_start + o.byte_size]
        if b != b0:
            diffs.append((typ, o.path_id, sz))
    print('raw diff objects', len(diffs), diffs)
    assert len(diffs) == 8, diffs
    assert all(o.byte_size == raw0[o.path_id][1] for o in objs)
    ab = [o for o in objs if o.type.name == 'AssetBundle'][0].read_typetree()
    print('AB name', ab['m_Name'], 'AB file', ab['m_AssetBundleName'], 'deps', ab['m_Dependencies'])
    print('container:', [p for p, _ in ab['m_Container']])
    assert ab['m_Name'] == NEW_HASH + '.bundle'
    assert all('/3041/' in p for p, _ in ab['m_Container'])
    for o in objs:
        if o.type.name == 'AnimationClip':
            print('clip', o.read_typetree()['m_Name'])
        if o.type.name == 'TextAsset':
            t = o.read_typetree()
            print('text', t['m_Name'], 'animKey', __import__('json').loads(t['m_Script'].lstrip('\ufeff'))['animKey'])
    print('plaintext_size', len(out))


if __name__ == '__main__':
    main()
