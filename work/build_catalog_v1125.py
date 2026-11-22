#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.1.25: 在 catalog.json 中补登记 FightAnimTrim/3041_1。

v1.1.24 只把 3041_1.trim 放进了 bundle，但 Addressables catalog 里没有
FightAnimTrim/3041_1 这个 key，游戏取不到待机 trim，仍按 prefab 330x389
拉伸显示，所以立绘没变大。本脚本在 catalog 尾部追加：

  key     FightAnimTrim/3041_1
  entry   internalId = .../3041_1/3041_1.trim.json
          provider = 2 (BundledAssetProvider)
          dependency = 23771 (3041 bundle 的 bucket)
          rtype = 2 (TextAsset)
  internalId 字符串追加到 m_InternalIds
"""
import json, base64, struct, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '/workspace/patch_v1.1.24/assets/aa/catalog.json'
OUT = sys.argv[2] if len(sys.argv) > 2 else '/workspace/work/catalog_3041_v1125.json'

NEW_KEY = 'FightAnimTrim/3041_1'
NEW_IID = 'Assets/PetAnimation/FightAnimation/3041/3041_1/3041_1.trim.json'
BUNDLE_BUCKET = 23771
DEP_HASH = -1698412003


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
        a = kb[off + 1]; p = off + 2 + a
        c = kb[p]; p = p + 1 + c
        n = struct.unpack('<i', kb[p:p + 4])[0]
        return json.loads(kb[p + 4:p + 4 + n].decode('utf-16le')), p + 4 + n
    raise SystemExit('bad key type %d' % t)


def decode(d):
    kb = base64.b64decode(d['m_KeyDataString'])
    bb = base64.b64decode(d['m_BucketDataString'])
    eb = base64.b64decode(d['m_EntryDataString'])
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
    return kb, bb, eb, nk, nb, ne, buckets, rows


def main():
    d = json.load(open(SRC, encoding='utf-8'))
    kb, bb, eb, nk, nb, ne, buckets, rows = decode(d)
    assert nk == nb == 23776 and ne == 14384, (nk, nb, ne)
    assert len(d['m_InternalIds']) == 13053

    # 确认 bundle bucket / 依赖与现有 3041 trim 完全一致
    assert parse_key(kb, buckets[BUNDLE_BUCKET][0])[0].endswith(
        'fight3041_assets_all_6b19939c69def5b7c66c3cc84ce44beb.bundle')
    for e in (10885, 10886, 10887):
        r = rows[e]
        assert (r[1], r[2], r[3], r[4], r[6]) == (2, BUNDLE_BUCKET, DEP_HASH, -1, 2), r
    # key 不存在
    p = 4
    keys = []
    for _ in range(nk):
        k, p = parse_key(kb, p)
        keys.append(k)
    assert NEW_KEY not in keys, NEW_KEY
    assert NEW_IID not in d['m_InternalIds']

    # --- key ---
    krec = bytes([0]) + struct.pack('<i', len(NEW_KEY)) + NEW_KEY.encode('ascii')
    new_key_off = len(kb)
    kb = kb + krec
    nk += 1

    # --- bucket -> entry ---
    new_entry_idx = ne
    bb = bb + struct.pack('<iii', new_key_off, 1, new_entry_idx)
    new_bucket_idx = nb
    nb += 1

    # --- entry ---
    new_iid_idx = len(d['m_InternalIds'])
    eb = eb + struct.pack('<7i', new_iid_idx, 2, BUNDLE_BUCKET, DEP_HASH, -1,
                          new_bucket_idx, 2)
    ne += 1

    d['m_InternalIds'].append(NEW_IID)
    d['m_KeyDataString'] = base64.b64encode(
        struct.pack('<i', nk) + kb[4:]).decode('ascii')
    d['m_BucketDataString'] = base64.b64encode(
        struct.pack('<i', nb) + bb[4:]).decode('ascii')
    d['m_EntryDataString'] = base64.b64encode(
        struct.pack('<i', ne) + eb[4:]).decode('ascii')

    with open(OUT, 'w', encoding='ascii') as f:
        json.dump(d, f, ensure_ascii=True, separators=(',', ':'))
    print('wrote', OUT)

    # --- 回读校验 ---
    d2 = json.load(open(OUT, encoding='utf-8'))
    kb2, bb2, eb2, nk2, nb2, ne2, buckets2, rows2 = decode(d2)
    assert (nk2, nb2, ne2) == (23777, 23777, 14385)
    p = 4
    found = None
    for i in range(nk2):
        off, p = p, p
        k, p = parse_key(kb2, p)
        if k == NEW_KEY:
            found = i
    assert found == 23776, found
    off, ents = buckets2[found]
    assert off == new_key_off and ents == (14384,), (off, ents)
    r = rows2[14384]
    assert r == (13053, 2, BUNDLE_BUCKET, DEP_HASH, -1, 23776, 2), r
    assert d2['m_InternalIds'][13053] == NEW_IID
    assert d2['m_ProviderIds'] == d['m_ProviderIds']
    assert d2['m_BuildResultHash'] == d['m_BuildResultHash']
    print('verify ok: key#23776 -> entry#14384 -> iid#13053')


if __name__ == '__main__':
    main()
