#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.1.32: 在 catalog.json 中登记 3042 / 3043，复用已有的 fight3041 bundle 键。

不再新增 bundle 文件：3042 / 3043 的动画与 trim 全部指向 fight3041 包，
补丁只需要替换 APK 里本来就有的 fight3041 文件。
"""
import json, base64, struct, hashlib

SRC = '/workspace/patch_v1.1.29/assets/aa/catalog.json'
OUT = '/workspace/work/catalog_v1132.json'
BUNDLE41 = 'fight3041_assets_all_6b19939c69def5b7c66c3cc84ce44beb.bundle'

PETS = {
    '3042': {'trim_key_idx': (19601, 19603, 19605),
             'trim_entry_idx': (10888, 10889, 10890)},
    '3043': {'trim_key_idx': (19607, 19609, 19611),
             'trim_entry_idx': (10891, 10892, 10893)},
}


def parse_key(kb, off):
    t = kb[off]
    if t == 0:
        n = struct.unpack('<i', kb[off + 1:off + 5])[0]
        return kb[off + 5:off + 5 + n].decode('ascii'), off + 5 + n
    if t == 1:
        n = struct.unpack('<i', kb[off + 1:off + 5])[0]
        return kb[off + 5:off + 5 + n].decode('utf-16le'), off + 5 + n
    if t == 2:
        return struct.unpack('<H', kb[off + 1:off + 3])[0], off + 3
    if t == 3:
        return struct.unpack('<I', kb[off + 1:off + 5])[0], off + 5
    if t == 4:
        return struct.unpack('<i', kb[off + 1:off + 5])[0], off + 5
    if t == 5:
        n = kb[off + 1]
        return kb[off + 2:off + 2 + n].decode('ascii'), off + 2 + n
    if t == 6:
        n = kb[off + 1]
        return ('type', kb[off + 2:off + 2 + n]), off + 2 + n
    if t == 7:
        a = kb[off + 1]
        p = off + 2 + a
        c = kb[p]
        p = p + 1 + c
        n = struct.unpack('<i', kb[p:p + 4])[0]
        return json.loads(kb[p + 4:p + 4 + n].decode('utf-16le')), p + 4 + n
    raise SystemExit(f'bad key type {t}')


def decode(d):
    kb = base64.b64decode(d['m_KeyDataString'])
    bb = base64.b64decode(d['m_BucketDataString'])
    eb = base64.b64decode(d['m_EntryDataString'])
    xb = base64.b64decode(d['m_ExtraDataString'])
    nk = struct.unpack('<i', kb[:4])[0]
    nb = struct.unpack('<i', bb[:4])[0]
    ne = struct.unpack('<i', eb[:4])[0]
    q = 4
    buckets = []
    for _ in range(nb):
        off = struct.unpack('<i', bb[q:q + 4])[0]
        c = struct.unpack('<i', bb[q + 4:q + 8])[0]
        ents = struct.unpack('<%di' % c, bb[q + 8:q + 8 + 4 * c]) if c else ()
        buckets.append((off, ents))
        q += 8 + 4 * c
    rows = [struct.unpack('<7i', eb[4 + i * 28:4 + (i + 1) * 28]) for i in range(ne)]
    return kb, bb, eb, xb, nk, nb, ne, buckets, rows


def key_bytes(s):
    b = s.encode('ascii')
    return bytes([0]) + struct.pack('<i', len(b)) + b


def main():
    d = json.load(open(SRC, encoding='utf-8'))
    kb, bb, eb, xb, nk, nb, ne, buckets, rows = decode(d)
    assert (nk, nb, ne) == (23777, 23777, 14385), (nk, nb, ne)
    assert len(d['m_InternalIds']) == 13054

    keys = []
    p = 4
    off2i = {}
    for i in range(nk):
        o = p
        k, p = parse_key(kb, p)
        keys.append(k)
        off2i[o] = i
    assert p == len(kb)

    bkey = None
    for off, ents in buckets:
        if off in off2i and keys[off2i[off]] == BUNDLE41:
            bkey = off2i[off]
            assert rows[ents[0]][1] == 0, rows[ents[0]]
            break
    assert bkey is not None and bkey == 23771, bkey

    dh41 = None
    anim41 = 'Assets/PetAnimation/FightAnimation/3041/3041_1.anim'
    for off, ents in buckets:
        if off in off2i and keys[off2i[off]] == anim41:
            r = rows[ents[0]]
            assert r[2] == bkey, r
            dh41 = r[3]
            break
    assert dh41 == -1698412003, dh41

    nk_new = nk
    nb_new = nb

    for pid, cfg in PETS.items():
        anim_iids = []
        for n in (1, 2, 3, 4):
            anim_iids.append(len(d['m_InternalIds']))
            d['m_InternalIds'].append(
                'Assets/PetAnimation/FightAnimation/%s/%s_%d.anim' % (pid, pid, n))
        trim_iids = []
        for n in (2, 3, 4):
            trim_iids.append(len(d['m_InternalIds']))
            d['m_InternalIds'].append(
                'Assets/PetAnimation/FightAnimation/%s/%s_%d/%s_%d.trim.json'
                % (pid, pid, n, pid, n))
        idle_trim_iid = len(d['m_InternalIds'])
        d['m_InternalIds'].append(
            'Assets/PetAnimation/FightAnimation/%s/%s_1/%s_1.trim.json' % (pid, pid, pid))

        for n, iid in zip((1, 2, 3, 4), anim_iids):
            path = d['m_InternalIds'][iid]
            koff = len(kb)
            kb += key_bytes(path)
            keys.append(path)
            nk_new += 1
            k = len(keys) - 1
            e = len(rows)
            rows.append((iid, 2, bkey, dh41, -1, k, 7))
            bb += struct.pack('<iii', koff, 1, e)
            nb_new += 1

        for kidx, eidx, iid in zip(cfg['trim_key_idx'], cfg['trim_entry_idx'], trim_iids):
            r = rows[eidx]
            assert r[5] == kidx, (r, kidx)
            assert r[1] == 1, r
            rows[eidx] = (iid, 2, bkey, dh41, -1, kidx, 2)

        idle_key = 'FightAnimTrim/%s_1' % pid
        assert idle_key not in keys
        koff = len(kb)
        kb += key_bytes(idle_key)
        keys.append(idle_key)
        nk_new += 1
        ik = len(keys) - 1
        e = len(rows)
        rows.append((idle_trim_iid, 2, bkey, dh41, -1, ik, 2))
        bb += struct.pack('<iii', koff, 1, e)
        nb_new += 1

        print(pid, '-> bundle', bkey, BUNDLE41)
        print('   anim iids', anim_iids, 'trim iids', trim_iids, 'idle', idle_trim_iid)

    assert nk_new == 23787, nk_new
    assert nb_new == 23787, nb_new
    assert len(rows) == 14395, len(rows)
    assert len(d['m_InternalIds']) == 13070, len(d['m_InternalIds'])

    eb = struct.pack('<i', len(rows)) + b''.join(struct.pack('<7i', *r) for r in rows)
    d['m_KeyDataString'] = base64.b64encode(struct.pack('<i', nk_new) + kb[4:]).decode()
    d['m_BucketDataString'] = base64.b64encode(struct.pack('<i', nb_new) + bb[4:]).decode()
    d['m_EntryDataString'] = base64.b64encode(eb).decode()

    with open(OUT, 'w', encoding='ascii') as f:
        json.dump(d, f, ensure_ascii=True, separators=(',', ':'))
    print('wrote', OUT)


if __name__ == '__main__':
    main()
