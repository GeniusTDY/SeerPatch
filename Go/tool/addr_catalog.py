import zipfile, json, base64, struct, sys


def load_catalog(apk='/workspace/downloads/Seer2.2.apk.1'):
    z = zipfile.ZipFile(apk)
    return json.loads(z.read('assets/aa/catalog.json'))


def parse(d):
    kd = base64.b64decode(d['m_KeyDataString'])
    bd = base64.b64decode(d['m_BucketDataString'])
    ed = base64.b64decode(d['m_EntryDataString'])
    keys = []
    off = 0
    n, = struct.unpack_from('<i', kd, off); off += 4
    for _ in range(n):
        ln, = struct.unpack_from('<i', kd, off); off += 4
        keys.append(kd[off:off + ln].decode('utf-8')); off += ln
    buckets = []
    off = 0
    n, = struct.unpack_from('<i', bd, off); off += 4
    for _ in range(n):
        ki, = struct.unpack_from('<i', bd, off); off += 4
        ec, = struct.unpack_from('<i', bd, off); off += 4
        ents = list(struct.unpack_from('<%di' % ec, bd, off)); off += 4 * ec
        buckets.append((ki, ents))
    entries = []
    for off in range(0, len(ed), 20):
        entries.append(struct.unpack_from('<5i', ed, off))
    return keys, buckets, entries


def key_to_internal(keys, buckets, entries, internal_ids, key):
    idx = keys.index(key)
    for ki, ents in buckets:
        if ki == idx:
            iid = entries[ents[0]][0]
            return internal_ids[iid], [internal_ids[entries[e][0]] for e in ents]
    return None


if __name__ == '__main__':
    d = load_catalog()
    keys, buckets, entries = parse(d)
    ids = d['m_InternalIds']
    for k in sys.argv[1:]:
        print(k, '->', key_to_internal(keys, buckets, entries, ids, k))
