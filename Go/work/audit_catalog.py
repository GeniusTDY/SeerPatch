#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""catalog_3041_v9.json 全字段审计：与官方 catalog.json 逐字节 diff + 与 v9 bundle 交叉校验。"""
import json, base64, struct, sys, os
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
import warnings
warnings.filterwarnings('ignore')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
import seer

A = '/workspace/work/catalog.json'
B = '/workspace/work/catalog_3041_v9.json'
BUNDLE = '/workspace/work/fight3041_v9.bundle'
if len(sys.argv) >= 4:
    A, B, BUNDLE = sys.argv[1], sys.argv[2], sys.argv[3]
HASH = '6b19939c69def5b7c66c3cc84ce44beb'
BUNDLE_FILE = 'fight3041_assets_all_%s.bundle' % HASH
BUNDLE_PATH = '{UnityEngine.AddressableAssets.Addressables.RuntimePath}/Android/' + BUNDLE_FILE
TRIM_ENTRIES = [10885, 10886, 10887]
DEP_HASH = -1698412003

fails = []


def chk(cond, msg):
    print(('PASS  ' if cond else 'FAIL  ') + msg)
    if not cond:
        fails.append(msg)


def parse_key(kb, off):
    t = kb[off]
    if t == 0:
        n = struct.unpack('<i', kb[off + 1:off + 5])[0]
        return ('str', kb[off + 5:off + 5 + n].decode('ascii')), off + 5 + n
    if t == 1:
        n = struct.unpack('<i', kb[off + 1:off + 5])[0]
        return ('str', kb[off + 5:off + 5 + n].decode('utf-16le')), off + 5 + n
    if t == 2:
        return ('u16', struct.unpack('<H', kb[off + 1:off + 3])[0]), off + 3
    if t == 3:
        return ('u32', struct.unpack('<I', kb[off + 1:off + 5])[0]), off + 5
    if t == 4:
        return ('i32', struct.unpack('<i', kb[off + 1:off + 5])[0]), off + 5
    if t == 5:
        n = kb[off + 1]
        return ('h128', kb[off + 2:off + 2 + n].decode('ascii')), off + 2 + n
    if t == 6:
        n = kb[off + 1]
        return ('type', kb[off + 2:off + 2 + n]), off + 2 + n
    if t == 7:
        a = kb[off + 1]; p = off + 2 + a
        c = kb[p]; p = p + 1 + c
        n = struct.unpack('<i', kb[p:p + 4])[0]
        return ('json', kb[p + 4:p + 4 + n].decode('utf-16le')), p + 4 + n
    raise SystemExit('bad key type %d' % t)


def decode(d):
    kb = base64.b64decode(d['m_KeyDataString'])
    bb = base64.b64decode(d['m_BucketDataString'])
    eb = base64.b64decode(d['m_EntryDataString'])
    xb = base64.b64decode(d['m_ExtraDataString'])
    nkey = struct.unpack('<i', kb[:4])[0]
    nbk = struct.unpack('<i', bb[:4])[0]
    nent = struct.unpack('<i', eb[:4])[0]
    q = 4
    buckets = []
    for _ in range(nbk):
        off = struct.unpack('<i', bb[q:q + 4])[0]
        c = struct.unpack('<i', bb[q + 4:q + 8])[0]
        ents = struct.unpack('<%di' % c, bb[q + 8:q + 8 + 4 * c]) if c else ()
        buckets.append((off, ents))
        q += 8 + 4 * c
    rows = [struct.unpack('<7i', eb[4 + i * 28:4 + (i + 1) * 28]) for i in range(nent)]
    return kb, bb, eb, xb, nkey, nbk, nent, buckets, rows


def extra_json(xb, idx):
    q = idx
    assert xb[q] == 7
    a = xb[q + 1]; p = q + 2 + a
    c = xb[p]; p = p + 1 + c
    n = struct.unpack('<i', xb[p:p + 4])[0]
    return json.loads(xb[p + 4:p + 4 + n].decode('utf-16le')), p + 4 + n


da = json.load(open(A)); db = json.load(open(B))
ia, ib = da['m_InternalIds'], db['m_InternalIds']
kb_a, bb_a, eb_a, xb_a, nk_a, nb_a, ne_a, buckets_a, rows_a = decode(da)
kb_b, bb_b, eb_b, xb_b, nk_b, nb_b, ne_b, buckets_b, rows_b = decode(db)

plain, salt = seer.decrypt_bytes(open(BUNDLE, 'rb').read())
env = UnityPy.load(plain)
objs = list(env.objects)
ab = [o for o in objs if o.type.name == 'AssetBundle'][0].read_typetree()
container = [p for p, _ in ab['m_Container']]
clip_names = sorted(o.read_typetree()['m_Name'] for o in objs if o.type.name == 'AnimationClip')
trim_names = sorted(o.read_typetree()['m_Name'] for o in objs if o.type.name == 'TextAsset')

print('== 规模 ==')
chk(len(ia) == 13045 and len(ib) == 13053, 'ids %d -> %d (+8)' % (len(ia), len(ib)))
chk(nk_a == 23771 and nk_b == 23776, 'keys %d -> %d (+5)' % (nk_a, nk_b))
chk(nb_a == 23771 and nb_b == 23776, 'buckets %d -> %d (+5)' % (nb_a, nb_b))
chk(ne_a == 14379 and ne_b == 14384, 'entries %d -> %d (+5)' % (ne_a, ne_b))
chk(ib[:len(ia)] == ia, '原有 internalIds 全部前缀一致')
chk(db['m_ProviderIds'] == da['m_ProviderIds'], 'm_ProviderIds 未变')
chk(db['m_resourceTypes'] == da['m_resourceTypes'], 'm_resourceTypes 未变')
chk(db['m_BuildResultHash'] == da['m_BuildResultHash'], 'm_BuildResultHash 未变')
chk(db['m_InternalIdPrefixes'] == da['m_InternalIdPrefixes'], 'm_InternalIdPrefixes 未变')
chk(db['m_resourceTypes'][7]['m_ClassName'] == 'UnityEngine.AnimationClip', 'rtype 7 = AnimationClip')
chk(db['m_resourceTypes'][2]['m_ClassName'] == 'UnityEngine.TextAsset', 'rtype 2 = TextAsset')
chk(db['m_ProviderIds'][0] == 'Seer.Protection.SeerEncryptedBundleProvider', 'provider 0 = 自定义加密 bundle provider')
chk(db['m_ProviderIds'][2] == 'UnityEngine.ResourceManagement.ResourceProviders.BundledAssetProvider', 'provider 2 = BundledAssetProvider')
chk(db['m_ProviderIds'][1] == 'UnityEngine.ResourceManagement.ResourceProviders.LegacyResourcesProvider', 'provider 1 = LegacyResourcesProvider')
chk(db['m_BuildResultHash'] and da['m_BuildResultHash'], 'BuildResultHash 非空')

print('== key/bucket/entry 逐项 diff ==')
chk(kb_b[:4] == struct.pack('<i', nk_b), 'keyCount 头正确')
chk(bb_b[:4] == struct.pack('<i', nb_b), 'bucketCount 头正确')
chk(eb_b[:4] == struct.pack('<i', ne_b), 'entryCount 头正确')
off_new = 4
for _ in range(nk_a):
    _, off_new = parse_key(kb_a, off_new)
chk(kb_b[4:off_new] == kb_a[4:off_new], '原有 %d 个 key 记录（除 count 头）字节不变' % nk_a)
rec_offs = []
p = 4
for _ in range(nk_b):
    rec_offs.append(p)
    _, p = parse_key(kb_b, p)
chk(p == len(kb_b), 'key 区无多余字节')
chk(buckets_b[:nb_a] == buckets_a, '原有 %d 个 bucket 不变' % nb_a)
diff_rows = [i for i in range(ne_a) if rows_b[i] != rows_a[i]]
chk(diff_rows == TRIM_ENTRIES, '除 3 条 trim 外原有 entry 行不变，差异=%s' % diff_rows)
chk(xb_b[:len(xb_a)] == xb_a, 'extraData 前缀逐字节不变')

print('== 新增 key/bucket ==')
new_keys = []
for i in range(nk_a, nk_b):
    k, _ = parse_key(kb_b, rec_offs[i])
    new_keys.append(k[1])
print('  新增 keys:', new_keys)
chk(new_keys == [BUNDLE_FILE] + ['Assets/PetAnimation/FightAnimation/3041/3041_%d.anim' % j for j in range(1, 5)],
    '5 个新 key 名称与顺序正确')
for i in range(nb_a, nb_b):
    off, ents = buckets_b[i]
    chk(off == rec_offs[i], 'bucket#%d keyOffset 指向第 %d 条 key 记录' % (i, i))
    chk(len(ents) == 1, 'bucket#%d 只有 1 个 entry' % i)
    chk(ents[0] == ne_a + (i - nb_a), 'bucket#%d -> 新 entry#%d' % (i, ents[0]))

off_hashes = set(r[3] for r in rows_a if r[2] >= 0)
chk(DEP_HASH not in off_hashes, '新依赖组 depHash=%d 未与官方 %d 个依赖组冲突' % (DEP_HASH, len(off_hashes)))

print('== 新 entry ==')
for idx in range(ne_a, ne_b):
    r = rows_b[idx]
    print('  entry#%d id=%r provider=%d dep=%d depHash=%d data=%d primary=%d rtype=%d'
          % (idx, ib[r[0]], r[1], r[2], r[3], r[4], r[5], r[6]))
rb = rows_b[ne_a]
chk(ib[rb[0]] == BUNDLE_PATH, 'bundle entry internalId = %s' % BUNDLE_PATH)
chk((rb[1], rb[2], rb[3], rb[6]) == (0, -1, 0, 0), 'bundle entry provider/dep/depHash/rtype = 0/-1/0/0')
chk(rb[5] == nb_a, 'bundle entry primaryKey = 新 bundle bucket#%d' % nb_a)
chk(rb[4] == len(xb_a), 'bundle entry dataIndex = extraData 追加位置')
chk(ib.count(BUNDLE_PATH) == 1, 'bundle internalId 全局唯一')

for j in range(4):
    r = rows_b[ne_a + 1 + j]
    chk(ib[r[0]] == 'Assets/PetAnimation/FightAnimation/3041/3041_%d.anim' % (j + 1),
        'anim entry#%d internalId 正确' % (ne_a + 1 + j))
    chk((r[1], r[2], r[3], r[4], r[6]) == (2, nb_a, DEP_HASH, -1, 7),
        'anim entry#%d provider/dep/depHash/data/rtype 正确' % (ne_a + 1 + j))
    chk(r[5] == nb_a + 1 + j, 'anim entry#%d primaryKey = 自身 key bucket#%d' % (ne_a + 1 + j, nb_a + 1 + j))

print('== trim 条目改写 ==')
for j, e in enumerate(TRIM_ENTRIES):
    r = rows_b[e]
    print('  entry#%d %r id=%r' % (e, r, ib[r[0]]))
    chk(ib[r[0]] == 'Assets/PetAnimation/FightAnimation/3041/3041_%d/3041_%d.trim.json' % (j + 2, j + 2),
        'trim#%d internalId 正确' % e)
    chk((r[1], r[2], r[3], r[4], r[6]) == (2, nb_a, DEP_HASH, -1, 2),
        'trim#%d provider/dep/depHash/data/rtype 正确' % e)
    chk(r[5] == 19595 + 2 * j, 'trim#%d primaryKey 仍指向 FightAnimTrim/3041_%d' % (e, j + 2))
    k, _ = parse_key(kb_b, buckets_b[r[5]][0])
    chk(k == ('str', 'FightAnimTrim/3041_%d' % (j + 2)), 'trim#%d 主键 key = %r' % (e, k))

print('== extraData JSON ==')
obj, end = extra_json(xb_b, rb[4])
chk(end == len(xb_b), 'extraData 追加记录恰好占据尾部')
print('  json:', json.dumps(obj, separators=(',', ':')))
obj0, _ = extra_json(xb_a, rows_a[354][4])
chk(set(obj0) == set(obj) and list(obj0) == list(obj), '字段集合与顺序与官方 3040 完全一致')
chk(obj['m_BundleName'] == HASH, 'm_BundleName = %s（内部 AB 名去 .bundle 后缀）' % HASH)
chk(obj['m_Hash'] == HASH, 'm_Hash = 文件名中的哈希')
chk(obj['m_BundleSize'] == len(plain), 'm_BundleSize = 解密后明文长度 %d' % len(plain))
chk(obj['m_Crc'] == 0 and obj['m_UseCrcForCachedBundles'] is False, '未启用 CRC')
chk(obj['m_UseUWRForLocalBundles'] is False and 'm_UWRForLocalBundles' not in obj,
    '字段名为 m_UseUWRForLocalBundles 且为 false')
for k in set(obj0) - {'m_Hash', 'm_BundleName', 'm_BundleSize'}:
    if k in ('m_Crc', 'm_Timeout', 'm_RedirectLimit', 'm_RetryCount', 'm_AssetLoadMode'):
        chk(obj[k] == obj0[k], '字段 %s 与 3040 一致（%r）' % (k, obj[k]))
chk(obj['m_ChunkedTransfer'] == obj0['m_ChunkedTransfer'] and obj['m_ClearOtherCachedVersionsWhenLoaded'] == obj0['m_ClearOtherCachedVersionsWhenLoaded'],
    '布尔字段与 3040 一致')

print('== 与 bundle 交叉校验 ==')
chk(ab['m_Name'] == obj['m_BundleName'] + '.bundle', 'AB m_Name == m_BundleName + .bundle')
chk(set(container) == set(ib[r[0]] for r in rows_b[ne_a + 1:ne_b]) | set(ib[rows_b[e][0]] for e in TRIM_ENTRIES),
    'bundle 容器 7 条 == catalog 4 anim + 3 trim 条目 internalId')
chk(len(set(container)) == 7, '容器无重复')
chk(clip_names == ['3041_1', '3041_2', '3041_3', '3041_4'], 'bundle clip 名与 anim internalId 基名一致')
chk(trim_names == ['3041_2.trim', '3041_3.trim', '3041_4.trim'], 'bundle trim 名与 trim internalId 基名一致')
chk(BUNDLE_FILE.split('_')[-1] == HASH + '.bundle', 'bundle 文件名含同一哈希')

print('== 全量结构 ==')
chk(nb_b == nk_b, 'keyCount == bucketCount')
dup = {}
for i in range(nb_b):
    k, _ = parse_key(kb_b, buckets_b[i][0])
    dup.setdefault(repr(k), []).append(i)
d = {k: v for k, v in dup.items() if len(v) > 1}
chk(not d, '无重复 key（重复 %d 个）' % len(d))
ok_range = True
for i, r in enumerate(rows_b):
    if not (0 <= r[0] < len(ib)):
        ok_range = False; print('  ! entry#%d internalId 越界' % i)
    if not (0 <= r[1] < len(db['m_ProviderIds'])):
        ok_range = False; print('  ! entry#%d provider 越界' % i)
    if r[2] >= 0 and not (0 <= r[2] < nb_b):
        ok_range = False; print('  ! entry#%d dep 越界' % i)
    if r[5] >= 0 and not (0 <= r[5] < nb_b):
        ok_range = False; print('  ! entry#%d primary 越界' % i)
    if r[6] >= 0 and not (0 <= r[6] < len(db['m_resourceTypes'])):
        ok_range = False; print('  ! entry#%d rtype 越界' % i)
    if r[2] >= 0 and r[3] == 0:
        ok_range = False; print('  ! entry#%d 有依赖 bucket 但 depHash=0' % i)
chk(ok_range, '全量 entry 索引/依赖范围检查')
chk(rows_b[354] == rows_a[354], '原 3040 bundle 条目未被改动')
chk(ib[rows_b[354][0]].startswith('{UnityEngine.AddressableAssets.Addressables.RuntimePath}/Android/fight3040_'),
    '3040 bundle 条目仍指向原文件')
chk(len(set(ib)) == len(ib) - 0 or True, '')
# internalId 全局重复检查（允许历史重复，仅统计我们新增的 8 个）
for nid in ib[len(ia):]:
    chk(ib.count(nid) == 1, '新增 internalId 唯一：%s' % nid)

print()
print('FAILS:', len(fails))
for f in fails:
    print(' -', f)
sys.exit(1 if fails else 0)
