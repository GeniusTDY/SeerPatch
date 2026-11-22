#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""以官方 3040 bundle 明文为基线，等长字节改名生成 fight3042 / fight3043 基线。

- 3040 -> 3042/3043（27 处，等长）
- AB 内部名哈希 806d51af... -> 每只精灵独立的 32 位哈希（2 处，等长）
- 其余 445 个对象原始数据逐字节不变
"""
import struct, sys, hashlib, os
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
OLD_HASH = b'806d51af380916b1521aadc4dc817a57'
PETS = {
    '3042': hashlib.md5(b'seer-fight-3042-v1.1.30').hexdigest(),
    '3043': hashlib.md5(b'seer-fight-3043-v1.1.30').hexdigest(),
}


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


def build(pid, new_hash):
    enc = open(SRC, 'rb').read()
    plain, salt = seer.decrypt_bytes(enc)
    assert plain[:7] == b'UnityFS'
    data, nodes = parse_container(plain)
    print(pid, 'container', len(plain), 'data', len(data), 'nodes', len(nodes))
    cab = data[nodes[0][1]:nodes[0][1] + nodes[0][2]]
    ress = data[nodes[1][1]:nodes[1][1] + nodes[1][2]]
    n = cab.count(b'3040'); nh = cab.count(OLD_HASH)
    print(pid, '3040 occurrences', n, 'hash occurrences', nh)
    assert n == 27 and nh == 2, (n, nh)
    cab2 = cab.replace(b'3040', pid.encode()).replace(OLD_HASH, new_hash.encode())
    assert len(cab2) == len(cab)
    assert cab2.count(b'3040') == 0 and cab2.count(pid.encode()) == 27

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
    open('/workspace/work/fight%s_v9.plain' % pid, 'wb').write(out)
    seer.encrypt(out, salt)
    open('/workspace/work/fight%s_v9.bundle' % pid, 'wb').write(seer.encrypt(out, salt))
    print(pid, 'plain', len(out), 'salt', salt.hex())

    env2 = UnityPy.load(out)
    objs = list(env2.objects)
    env0 = UnityPy.load(plain)
    objs0 = list(env0.objects)
    assert len(objs) == len(objs0) == 445
    raw0 = {o.path_id: (o.type.name, o.byte_size, cab[o.byte_start:o.byte_start + o.byte_size]) for o in objs0}
    diffs = []
    for o in objs:
        typ, sz, b0 = raw0[o.path_id]
        b = cab2[o.byte_start:o.byte_start + o.byte_size]
        if b != b0:
            diffs.append((typ, o.path_id))
    assert len(diffs) == 8, diffs
    ab = [o for o in objs if o.type.name == 'AssetBundle'][0].read_typetree()
    assert ab['m_Name'] == new_hash + '.bundle', ab['m_Name']
    assert all('/%s/' % pid in p for p, _ in ab['m_Container']), ab['m_Container']
    print(pid, 'AB ok, container', [p for p, _ in ab['m_Container']])


if __name__ == '__main__':
    for pid, h in PETS.items():
        print('==', pid, h)
        build(pid, h)
