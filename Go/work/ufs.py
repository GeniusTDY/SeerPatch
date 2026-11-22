#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最小 UnityFS 读取：解出 bundle 数据块，用于确认内部资源路径。"""
import struct, sys, re
sys.path.insert(0, '/workspace/tools')
import seer
import lz4.block


def align16(x):
    return x + (-x) % 16


def parse(path):
    d, _ = seer.decrypt(path)
    p = 8
    ver, = struct.unpack('>I', d[p:p + 4]); p += 4
    for _ in range(2):
        p = d.index(b'\0', p) + 1
    total, = struct.unpack('>q', d[p:p + 8]); p += 8
    cbs, ubs, flags = struct.unpack('>III', d[p:p + 12]); p += 12
    if flags & 0x80:
        info_raw = d[-cbs:]
        info_off = align16(p)
    else:
        info_off = align16(p)
        info_raw = d[info_off:info_off + cbs]
        info_off += cbs
    info = lz4.block.decompress(info_raw, uncompressed_size=ubs)
    q = 16
    nblk, = struct.unpack('>I', info[q:q + 4]); q += 4
    blocks = [struct.unpack('>IIH', info[q + i * 10:q + i * 10 + 10]) for i in range(nblk)]
    q += nblk * 10
    nodes, = struct.unpack('>I', info[q:q + 4]); q += 4
    dirs = []
    for _ in range(nodes):
        off, size, nfl = struct.unpack('>qqI', info[q:q + 20]); q += 20
        e = info.index(b'\0', q)
        dirs.append((info[q:e].decode(), off, size))
        q = e + 1
    data = bytearray()
    pos = info_off
    for u, c, f in blocks:
        blob = d[pos:pos + c]; pos += c
        data += blob if (f & 0x3F) == 0 else lz4.block.decompress(blob, uncompressed_size=u)
    return bytes(d), bytes(data), dirs, blocks, flags


if __name__ == '__main__':
    raw, data, dirs, blocks, flags = parse(sys.argv[1])
    print('flags', hex(flags), 'blocks', len(blocks), 'data', len(data))
    print('nodes', [d[0] for d in dirs])
    seen = set()
    for m in re.finditer(rb'[ -~]{6,200}', data):
        s = m.group().decode()
        if ('Assets/' in s or 'FightAnimTrim' in s or '.anim' in s or '.trim.json' in s or s.endswith('.bundle')) and s not in seen:
            seen.add(s)
            print('  ', s)
