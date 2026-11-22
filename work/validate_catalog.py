#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按 Addressables 1.22.3 ContentCatalogData.CreateLocator 逐字节模拟，检查目录能否安全加载。"""
import json, base64, struct, sys


def read_obj(buf, off):
    t = buf[off]
    p = off + 1
    if t == 0:
        n = struct.unpack('<i', buf[p:p+4])[0]
        return ('str', buf[p+4:p+4+n].decode('ascii')), p + 4 + n
    if t == 1:
        n = struct.unpack('<i', buf[p:p+4])[0]
        return ('str', buf[p+4:p+4+n].decode('utf-16le')), p + 4 + n
    if t == 2:
        return ('u16', struct.unpack('<H', buf[p:p+2])[0]), p + 2
    if t == 3:
        return ('u32', struct.unpack('<I', buf[p:p+4])[0]), p + 4
    if t == 4:
        return ('i32', struct.unpack('<i', buf[p:p+4])[0]), p + 4
    if t == 5:
        n = buf[p]
        return ('hash', buf[p+1:p+1+n].decode('ascii')), p + 1 + n
    if t == 6:
        n = buf[p]
        return ('type', buf[p+1:p+1+n]), p + 1 + n
    if t == 7:
        a = buf[p]; p += 1
        asm = buf[p:p+a].decode('ascii'); p += a
        c = buf[p]; p += 1
        cls = buf[p:p+c].decode('ascii'); p += c
        n = struct.unpack('<i', buf[p:p+4])[0]; p += 4
        js = buf[p:p+n].decode('utf-16le'); p += n
        return ('json', cls, js), p
    raise ValueError('unknown key type %d at %d' % (t, off))


def check(path):
    d = json.load(open(path))
    kb = base64.b64decode(d['m_KeyDataString'])
    bb = base64.b64decode(d['m_BucketDataString'])
    eb = base64.b64decode(d['m_EntryDataString'])
    xb = base64.b64decode(d['m_ExtraDataString'])
    ids = d['m_InternalIds']
    prov = d['m_ProviderIds']
    types = d['m_resourceTypes']
    pfx = d.get('m_InternalIdPrefixes') or []

    nkey = struct.unpack('<i', kb[:4])[0]
    nent = struct.unpack('<i', eb[:4])[0]
    nbk = struct.unpack('<i', bb[:4])[0]
    print('== %s keys=%d buckets=%d entries=%d ids=%d' % (path.split('/')[-1], nkey, nbk, nent, len(ids)))

    buckets = []
    q = 4
    for i in range(nbk):
        off = struct.unpack('<i', bb[q:q+4])[0]
        c = struct.unpack('<i', bb[q+4:q+8])[0]
        q += 8
        if c < 0 or c > 64:
            raise SystemExit('bucket %d bad count %d' % (i, c))
        ents = list(struct.unpack('<%di' % c, bb[q:q+4*c]))
        q += 4 * c
        buckets.append((off, ents))
    assert q == len(bb), ('bucket trailing', q, len(bb))

    keys, seen, dup = [], set(), []
    for i, (off, ents) in enumerate(buckets):
        k, _ = read_obj(kb, off)
        keys.append(k)
        if k in seen:
            dup.append((i, k))
        seen.add(k)

    locs = []
    for i in range(nent):
        row = struct.unpack('<7i', eb[4+i*28:4+(i+1)*28])
        iid, pi, dep, dh, di, pk, rt = row
        assert 0 <= iid < len(ids), ('entry %d internalId %d' % (i, iid))
        assert 0 <= pi < len(prov), ('entry %d provider %d' % (i, pi))
        assert dep == -1 or 0 <= dep < nbk, ('entry %d dep %d' % (i, dep))
        assert 0 <= pk < nbk, ('entry %d primary %d' % (i, pk))
        assert 0 <= rt < len(types), ('entry %d rtype %d' % (i, rt))
        assert di == -1 or di < len(xb), ('entry %d data %d' % (i, di))
        v = ids[iid]
        if pfx:
            h = v.rfind('#')
            if h > 0 and v[:h].isdigit() and int(v[:h]) < len(pfx):
                v = pfx[int(v[:h])] + v[h+1:]
        if dep != -1:
            assert keys[dep][0] == 'str', ('entry %d dep key not string' % i)
        if di != -1:
            o, _ = read_obj(xb, di)
            assert o[0] == 'json', ('entry %d extra not json' % i)
            json.loads(o[2])
        locs.append(v)

    for i, (off, ents) in enumerate(buckets):
        for e in ents:
            assert 0 <= e < nent, ('bucket %d entry %d' % (i, e))

    print('  dup keys:', len(dup), dup[:4])
    assert not dup, 'DUPLICATE KEYS -> Dictionary.Add throws'
    assert nkey == nbk, ('keys != buckets', nkey, nbk)
    print('  OK, no duplicates; sample new keys:')
    for i in range(nbk - 5, nbk):
        print('   ', i, keys[i], '-> entries', buckets[i][1])


if __name__ == '__main__':
    for f in sys.argv[1:] or ['/workspace/work/catalog.json', '/workspace/work/catalog_3041_v7.json']:
        check(f)
