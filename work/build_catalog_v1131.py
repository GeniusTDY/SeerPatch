#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.1.31: 在 catalog.json 中登记 fight3042 / fight3043。

每只精灵追加：
  - bundle key（文件名）
  - 4 个动画 key（Assets/PetAnimation/FightAnimation/<id>/<id>_<n>.anim）
  - bundle / 4 个动画 / 3 个 trim 的 entry（trim 复用官方已有 key，仅改写 entry）
  - 1 条 extraData（AssetBundleRequestOptions）
"""
import json, base64, struct, hashlib

SRC = '/workspace/patch_v1.1.29/assets/aa/catalog.json'
OUT = '/workspace/work/catalog_v1131.json'

PETS = {
    '3042': {
        'hash': hashlib.md5(b'seer-fight-3042-v1.1.31').hexdigest(),
        'plain_size': 5758240,
        'trim_key_idx': (19601, 19603, 19605),
        'trim_entry_idx': (10888, 10889, 10890),
    },
    '3043': {
        'hash': hashlib.md5(b'seer-fight-3043-v1.1.31').hexdigest(),
        'plain_size': 11793405,
        'trim_key_idx': (19607, 19609, 19611),
        'trim_entry_idx': (10891, 10892, 10893),
    },
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
        a = kb[off + 1]; p = off + 2 + a
        c = kb[p]; p = p + 1 + c
        n = struct.unpack('<i', kb[p:p + 4])[0]
        return json.loads(kb[p + 4:p + 4 + n].decode('utf-16le')), p + 4 + n
    raise SystemExit('bad key type %d' % t)


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


ASM = b'Unity.ResourceManager, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null'
CLS = b'UnityEngine.ResourceManagement.ResourceProviders.AssetBundleRequestOptions'


def enc_extra(js):
    s = json.dumps(js, ensure_ascii=False, separators=(',', ':')).encode('utf-16le')
    return bytes([7, len(ASM)]) + ASM + bytes([len(CLS)]) + CLS + struct.pack('<i', len(s)) + s


def key_bytes(s):
    b = s.encode('ascii')
    return bytes([0]) + struct.pack('<i', len(b)) + b


def main():
    d = json.load(open(SRC, encoding='utf-8'))
    kb, bb, eb, xb, nk, nb, ne, buckets, rows = decode(d)
    assert (nk, nb, ne) == (23777, 23777, 14385), (nk, nb, ne)
    assert len(d['m_InternalIds']) == 13054

    used = {r[3] for r in rows}
    keys = []
    p = 4
    for _ in range(nk):
        k, p = parse_key(kb, p)
        keys.append(k)
    assert p == len(kb)
    nk_new = nk
    nb_new = nb

    for pid, cfg in PETS.items():
        bundle = 'fight%s_assets_all_%s.bundle' % (pid, cfg['hash'])
        assert bundle not in keys
        h = hashlib.md5(('dep-%s-v1131' % pid).encode()).digest()
        dh = struct.unpack('<i', h[:4])[0]
        while dh in used:
            h = hashlib.md5(h).digest()
            dh = struct.unpack('<i', h[:4])[0]
        used.add(dh)

        iid_base = len(d['m_InternalIds'])
        d['m_InternalIds'].append(
            '{UnityEngine.AddressableAssets.Addressables.RuntimePath}/Android/' + bundle)
        anim_iids = []
        for n in (1, 2, 3, 4):
            anim_iids.append(len(d['m_InternalIds']))
            d['m_InternalIds'].append(
                'Assets/PetAnimation/FightAnimation/%s/%s_%d.anim' % (pid, pid, n))
        trim_iids = []
        for n in (2, 3, 4):
            trim_iids.append(len(d['m_InternalIds']))
            d['m_InternalIds'].append(
                'Assets/PetAnimation/FightAnimation/%s/%s_%d/%s_%d.trim.json' % (pid, pid, n, pid, n))
        idle_trim_iid = len(d['m_InternalIds'])
        d['m_InternalIds'].append(
            'Assets/PetAnimation/FightAnimation/%s/%s_1/%s_1.trim.json' % (pid, pid, pid))

        # bundle key + bucket + entry
        koff = len(kb)
        kb += key_bytes(bundle)
        keys.append(bundle); nk_new += 1
        data_off = len(xb)
        xb += enc_extra({
            'm_Hash': cfg['hash'], 'm_Crc': 0, 'm_Timeout': 0,
            'm_ChunkedTransfer': False, 'm_RedirectLimit': -1, 'm_RetryCount': 0,
            'm_BundleName': cfg['hash'], 'm_AssetLoadMode': 0,
            'm_BundleSize': cfg['plain_size'],
            'm_UseCrcForCachedBundles': False, 'm_UseUWRForLocalBundles': False,
            'm_ClearOtherCachedVersionsWhenLoaded': False,
        })
        bkey = len(keys) - 1
        be = len(rows)
        rows.append((iid_base, 0, -1, 0, data_off, bkey, 0))
        bb += struct.pack('<iii', koff, 1, be); nb_new += 1

        for n, iid in zip((1, 2, 3, 4), anim_iids):
            path = d['m_InternalIds'][iid]
            koff = len(kb)
            kb += key_bytes(path)
            keys.append(path); nk_new += 1
            k = len(keys) - 1
            e = len(rows)
            rows.append((iid, 2, bkey, dh, -1, k, 7))
            bb += struct.pack('<iii', koff, 1, e); nb_new += 1

        for kidx, eidx, iid in zip(cfg['trim_key_idx'], cfg['trim_entry_idx'], trim_iids):
            r = rows[eidx]
            assert r[5] == kidx, (r, kidx)
            assert r[1] == 1, r
            rows[eidx] = (iid, 2, bkey, dh, -1, kidx, 2)

        # 待机 trim（586x625 1:1），与 3041 一致
        idle_key = 'FightAnimTrim/%s_1' % pid
        assert idle_key not in keys
        koff = len(kb)
        kb += key_bytes(idle_key)
        keys.append(idle_key); nk_new += 1
        ik = len(keys) - 1
        e = len(rows)
        rows.append((idle_trim_iid, 2, bkey, dh, -1, ik, 2))
        bb += struct.pack('<iii', koff, 1, e); nb_new += 1

        print(pid, 'bundle', bundle)
        print('   key#%d entry#%d depHash %d iid#%d' % (bkey, be, dh, iid_base))

    assert nk_new == 23789, nk_new
    assert nb_new == 23789, nb_new
    assert len(rows) == 14397, len(rows)
    assert len(d['m_InternalIds']) == 13072, len(d['m_InternalIds'])

    eb = struct.pack('<i', len(rows)) + b''.join(struct.pack('<7i', *r) for r in rows)
    d['m_KeyDataString'] = base64.b64encode(struct.pack('<i', nk_new) + kb[4:]).decode()
    d['m_BucketDataString'] = base64.b64encode(struct.pack('<i', nb_new) + bb[4:]).decode()
    d['m_EntryDataString'] = base64.b64encode(eb).decode()
    d['m_ExtraDataString'] = base64.b64encode(xb).decode()

    with open(OUT, 'w', encoding='ascii') as f:
        json.dump(d, f, ensure_ascii=True, separators=(',', ':'))
    print('wrote', OUT, 'extra', len(xb))


if __name__ == '__main__':
    main()
