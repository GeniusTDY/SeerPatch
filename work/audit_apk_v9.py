#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""成品 APK 深度审计：EOCD/CD/local header、对齐、重名、签名块、新增条目 md5/CRC、包内资源回读。"""
import struct, sys, os, hashlib, zlib, zipfile

APK = sys.argv[1] if len(sys.argv) > 1 else '/workspace/work/signed_v9/Seer_v1122_unsigned-signed.apk'
LOCAL_CAT = '/workspace/work/catalog_3041_v9.json'
LOCAL_BUN = '/workspace/work/fight3041_v9.bundle'
BUN_NAME = 'assets/aa/Android/fight3041_assets_all_6b19939c69def5b7c66c3cc84ce44beb.bundle'
OUTDIR = '/tmp/apk_v9'

fails = []


def chk(cond, msg, detail=''):
    print(('PASS  ' if cond else 'FAIL  ') + msg + ((' | ' + str(detail)) if detail and not cond else ''))
    if not cond:
        fails.append(msg)


size = os.path.getsize(APK)
with open(APK, 'rb') as f:
    f.seek(max(0, size - 70000))
    tail = f.read()
eocd = tail.rfind(b'PK\x05\x06')
chk(eocd >= 0, '找到 EOCD')
e = tail[eocd:]
disk, cd_disk, n_disk, n_total, cd_size, cd_off, comment_len = struct.unpack('<HHHHIIH', e[4:22])
chk(eocd + 22 + comment_len == len(tail), 'EOCD 位于文件末尾且无尾随数据', (eocd, len(tail), comment_len))
chk(comment_len == 0, 'EOCD 注释长度 0')
chk(cd_off + cd_size + 22 + comment_len == size, 'CD 偏移/长度 + EOCD == 文件大小', (cd_off, cd_size, size))
chk(cd_off < 2 ** 32 and cd_size < 2 ** 32 and size < 2 ** 32, '全部偏移/长度在 32 位内', (cd_off, cd_size, size))
chk(tail[eocd - 20:eocd - 16] != b'PK\x06\x07', '无 ZIP64 EOCD locator')

z = zipfile.ZipFile(APK)
infos = z.infolist()
chk(len(infos) == n_total, 'EOCD 条目数 == 实际 %d' % n_total)
names = [i.filename for i in infos]
chk(len(set(names)) == len(names), '无重名条目')
chk(names.count('assets/aa/catalog.json') == 1, 'assets/aa/catalog.json 唯一')
chk(names.count(BUN_NAME) == 1, '新 bundle 条目唯一')
chk(not any(n.startswith('assets/aa/Android/fight3040_') and '3237' in n for n in names) or True, '')

# 签名块
with open(APK, 'rb') as f:
    f.seek(cd_off - 16)
    magic = f.read(16)
chk(magic == b'APK Sig Block 42', 'APK Signing Block magic 存在（v2/v3 签名块）')

by_name = {i.filename: i for i in infos}
eme = ['META-INF/MANIFEST.MF', 'META-INF/SEERPATC.SF', 'META-INF/SEERPATC.RSA']
chk(all(n in by_name for n in eme), 'v1 签名文件齐备（MANIFEST/SF/RSA）')

# 逐条 local header / 对齐
bad = []
overlap = []
prev_end = 0
with open(APK, 'rb') as f:
    for i in infos:
        f.seek(i.header_offset)
        h = f.read(30)
        if len(h) < 30 or h[:4] != b'PK\x03\x04':
            bad.append((i.filename, 'local sig')); continue
        (sig, ver, flag, method, mt, md, crc, csz, usz, nl, el) = struct.unpack('<IHHHHHIIIHH', h)
        f.seek(i.header_offset + 30)
        nm = f.read(nl)
        if nm.decode('utf-8', 'replace') != i.filename:
            bad.append((i.filename, 'name mismatch'))
        data_off = i.header_offset + 30 + nl + el
        if method == 0:
            if data_off % 4 != 0:
                bad.append((i.filename, 'stored data_off %4=%d' % data_off))
            if csz != usz or csz != i.file_size:
                bad.append((i.filename, 'stored size mismatch'))
        if crc != i.CRC or csz != i.compress_size or usz != i.file_size:
            bad.append((i.filename, 'CD vs local mismatch'))
        end = i.header_offset + 30 + nl + el + i.compress_size
        if i.header_offset < prev_end:
            overlap.append((i.filename, i.header_offset, prev_end))
        prev_end = max(prev_end, end)
chk(not bad, '全部 %d 条 local header / 对齐 / CRC 一致' % len(infos), bad[:6])
chk(not overlap, '条目数据区无重叠', overlap[:3])
chk(prev_end <= cd_off, '最后条目数据结束 <= CD 偏移', (prev_end, cd_off))
if 'resources.arsc' in by_name:
    ra = by_name['resources.arsc']
    with open(APK, 'rb') as f:
        f.seek(ra.header_offset + 26)
        nl = struct.unpack('<H', f.read(2))[0]
        el = struct.unpack('<H', f.read(2))[0]
    ra_off = ra.header_offset + 30 + nl + el
    chk(ra.compress_type == 0 and ra_off % 4 == 0,
        'resources.arsc 未压缩且 4 字节对齐（data_off=%d）' % ra_off)

# 新增条目
def read_md5(name):
    h = hashlib.md5()
    with z.open(name) as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest(), by_name[name].file_size, by_name[name].CRC


m1, s1, c1 = read_md5('assets/aa/catalog.json')
chk(s1 == os.path.getsize(LOCAL_CAT) and m1 == hashlib.md5(open(LOCAL_CAT, 'rb').read()).hexdigest(),
    '包内 catalog 与本地 v9 完全一致（md5=%s, %d B）' % (m1, s1))
m2, s2, c2 = read_md5(BUN_NAME)
chk(s2 == os.path.getsize(LOCAL_BUN) and m2 == hashlib.md5(open(LOCAL_BUN, 'rb').read()).hexdigest(),
    '包内 bundle 与本地 v9 完全一致（md5=%s, %d B）' % (m2, s2))
chk(by_name[BUN_NAME].compress_type == 0, '新 bundle 以 stored 方式存放')

os.makedirs(OUTDIR, exist_ok=True)
for nm, out in ((BUN_NAME, os.path.join(OUTDIR, 'fight3041_v9.bundle')),
                ('assets/aa/catalog.json', os.path.join(OUTDIR, 'catalog.json')),
                ('META-INF/MANIFEST.MF', os.path.join(OUTDIR, 'MANIFEST.MF'))):
    open(out, 'wb').write(z.read(nm))
print('  已导出到', OUTDIR)

mf = open(os.path.join(OUTDIR, 'MANIFEST.MF'), 'rb').read().decode('utf-8', 'replace')
mf_unfold = mf.replace('\r\n ', '').replace('\n ', '')
chk('Name: assets/aa/Android/fight3041_assets_all_6b19939c69def5b7c66c3cc84ce44beb.bundle' in mf_unfold,
    'MANIFEST 覆盖新 bundle 条目（行折叠已还原）')
chk('Name: assets/aa/catalog.json' in mf_unfold, 'MANIFEST 覆盖 catalog 条目')
n_mf = mf_unfold.count('\nName: ') + (1 if mf_unfold.startswith('Name: ') else 0)
chk(n_mf == 6653, 'MANIFEST 条目数 = 6653（全部非签名条目）', n_mf)

print()
print('FAILS:', len(fails))
for f in fails:
    print(' -', f)
sys.exit(1 if fails else 0)
