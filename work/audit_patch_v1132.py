#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.1.32 最终审计：patch 内的合并包 + catalog 端到端一致性。"""
import sys, os, json, base64, struct, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
sys.path.insert(0, '/workspace/work')
import UnityPy, seer
from audit_v1132 import chk, fails, walk
from build_catalog_v1132 import parse_key, decode
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'

PATCH = '/workspace/patch_v1.1.32'
BUNDLE = 'fight3041_assets_all_6b19939c69def5b7c66c3cc84ce44beb.bundle'
CAT = os.path.join(PATCH, 'assets/aa/catalog.json')
AND = os.path.join(PATCH, 'assets/aa/Android')


def main():
    plain, salt = seer.decrypt_bytes(
        open(os.path.join(AND, BUNDLE), 'rb').read())
    env = UnityPy.load(plain)
    bf = env.files[list(env.files.keys())[0]]
    sf = bf.files[[k for k in bf.files if not k.endswith('.resS')][0]]
    pids = list(sf.objects.keys())
    chk(pids == sorted(pids), 'object table not ascending')
    chk(len(pids) == 1334, f'objects {len(pids)}')

    ab = next(o for o in sf.objects.values() if o.type.name == 'AssetBundle')
    at = ab.read_typetree()
    chk(at['m_AssetBundleName'] == '6b19939c69def5b7c66c3cc84ce44beb.bundle',
        f"ab name {at['m_AssetBundleName']}")
    ckeys = [c[0] for c in at['m_Container']]
    chk(len(ckeys) == 24 and len(set(ckeys)) == 24, f'container {len(ckeys)}')
    chk(len(at['m_PreloadTable']) == 464, f"preload {len(at['m_PreloadTable'])}")
    base8 = [
        'Assets/PetAnimation/FightAnimation/3041/3041_1.anim',
        'Assets/PetAnimation/FightAnimation/3041/3041_2.anim',
        'Assets/PetAnimation/FightAnimation/3041/3041_2/3041_2.trim.json',
        'Assets/PetAnimation/FightAnimation/3041/3041_3.anim',
        'Assets/PetAnimation/FightAnimation/3041/3041_3/3041_3.trim.json',
        'Assets/PetAnimation/FightAnimation/3041/3041_4.anim',
        'Assets/PetAnimation/FightAnimation/3041/3041_4/3041_4.trim.json',
        'Assets/PetAnimation/FightAnimation/3041/3041_1/3041_1.trim.json',
    ]
    chk(ckeys[:8] == base8, '3041 container order changed')

    bad = []
    for o in sf.objects.values():
        refs = []
        walk(o.read_typetree(), '', refs)
        for path, fid, pid in refs:
            if fid == 0 and pid != 0 and pid not in sf.objects:
                bad.append((o.path_id, path, pid))
    chk(not bad, f'unresolved PPtrs {bad[:3]}')
    chk(all(x['m_PathID'] in sf.objects for x in at['m_PreloadTable']),
        'preload unresolved')
    chk(all(v['asset']['m_PathID'] in sf.objects for _, v in at['m_Container']),
        'container unresolved')

    trims, clips, sprites = {}, [], set()
    for o in sf.objects.values():
        if o.type.name == 'TextAsset':
            t = o.read_typetree()
            trims[t['m_Name']] = json.loads(t['m_Script'].lstrip('\ufeff'))
        elif o.type.name == 'AnimationClip':
            clips.append(o.read_typetree()['m_Name'])
        elif o.type.name == 'Sprite':
            sprites.add(o.read_typetree()['m_Name'])
    want = {1: 21, 2: 88, 3: 53, 4: 56}
    for pid in ('3041', '3042', '3043'):
        for n, f in want.items():
            name = f'{pid}_{n}.trim'
            chk(name in trims, f'missing trim {name}')
            if name not in trims:
                continue
            js = trims[name]
            chk(len(js['frames']) == f, f'frames {name} {len(js["frames"])}')
            miss = [x['spriteName'] for x in js['frames']
                    if x['spriteName'] not in sprites]
            chk(not miss, f'trim missing sprites {name} {miss[:3]}')
        for n in (1, 2, 3, 4):
            chk(f'{pid}_{n}' in clips, f'missing clip {pid}_{n}')
    chk(len(trims) == 12 and len(clips) == 12, f'trims {len(trims)} clips {len(clips)}')
    empty = []
    for o in sf.objects.values():
        if o.type.name == 'Sprite':
            try:
                im = o.read().image
                if im is None or im.getbbox() is None:
                    empty.append(o.read_typetree()['m_Name'])
            except Exception:
                empty.append(o.read_typetree()['m_Name'] + ':err')
    chk(not empty, f'empty sprites {empty[:5]}')

    # ---------- catalog ----------
    d = json.load(open(CAT, encoding='utf-8'))
    kb, bb, eb, xb, nk, nb, ne, buckets, rows = decode(d)
    ids = d['m_InternalIds']
    chk((nk, nb, ne) == (23787, 23787, 14395), f'counts {(nk, nb, ne)}')
    chk(len(ids) == 13070, f'iids {len(ids)}')
    keys, p, off2i = [], 4, {}
    for i in range(nk):
        o = p
        k, p = parse_key(kb, p)
        keys.append(k)
        off2i[o] = i
    chk(p == len(kb), 'key blob trailing bytes')

    bkey, bundle_iid = None, None
    for off, ents in buckets:
        if off in off2i and keys[off2i[off]] == BUNDLE:
            bkey = off2i[off]
            bundle_iid = rows[ents[0]][0]
            chk(rows[ents[0]][1] == 0, f'bundle provider {rows[ents[0]][1]}')
            break
    chk(bkey == 23771, f'bundle key {bkey}')
    chk(ids[bundle_iid].endswith('/' + BUNDLE), ids[bundle_iid])
    chk(not any(k == 'fight3042_assets_all_f3967812cf6958a82081c3b8ffc4bee7.bundle'
                or k == 'fight3043_assets_all_f199809ee4b7c930a6ab659b18f61470.bundle'
                for k in keys), 'stale 3042/3043 bundle key present')
    chk(not os.path.exists(os.path.join(AND, 'fight3042_assets_all_f3967812cf6958a82081c3b8ffc4bee7.bundle')), 'fight3042 file still present')
    chk(not os.path.exists(os.path.join(AND, 'fight3043_assets_all_f199809ee4b7c930a6ab659b18f61470.bundle')), 'fight3043 file still present')

    want = []  # (key, 期望 internalId, 期望 entryType)
    for pid in ('3042', '3043'):
        for n in (1, 2, 3, 4):
            a = f'Assets/PetAnimation/FightAnimation/{pid}/{pid}_{n}.anim'
            want.append((a, a, 7))
        for n in (2, 3, 4):
            a = f'Assets/PetAnimation/FightAnimation/{pid}/{pid}_{n}/{pid}_{n}.trim.json'
            want.append((f'FightAnimTrim/{pid}_{n}', a, 2))
        a = f'Assets/PetAnimation/FightAnimation/{pid}/{pid}_1/{pid}_1.trim.json'
        want.append((f'FightAnimTrim/{pid}_1', a, 2))

    for k, iid, et in want:
        hit = [off for off, _ in buckets if off in off2i and keys[off2i[off]] == k]
        chk(len(hit) == 1, f'catalog key {k} hits {len(hit)}')
        if not hit:
            continue
        ents = dict((off, e) for off, e in buckets)[hit[0]]
        chk(len(ents) == 1, f'{k} entries {len(ents)}')
        r = rows[ents[0]]
        chk(r[1] == 2, f'{k} provider {r[1]}')
        chk(r[2] == bkey, f'{k} depkey {r[2]}')
        chk(r[3] == -1698412003, f'{k} dephash {r[3]}')
        chk(r[5] == off2i[hit[0]], f'{k} primaryKey {r[5]}')
        chk(r[6] == et, f'{k} entryType {r[6]}')
        chk(ids[r[0]] == iid, f'{k} iid {ids[r[0]]}')
        chk(iid in ckeys, f'{k} asset path not in bundle container: {iid}')

    # 3041 原始条目仍指向同一包
    for n in (1, 2, 3, 4):
        k = f'Assets/PetAnimation/FightAnimation/3041/3041_{n}.anim'
        hit = [off for off, _ in buckets if off in off2i and keys[off2i[off]] == k]
        chk(len(hit) == 1, f'3041 key missing {k}')
        if hit:
            r = rows[dict(buckets)[hit[0]][0]]
            chk((r[2], r[3]) == (bkey, -1698412003), f'3041 row {r}')

    # patch 中所有 bundle 文件 <=> catalog 里出现的补丁文件
    for f in sorted(os.listdir(AND)):
        if f.endswith('.bundle'):
            chk(any(x.endswith('/' + f) for x in ids), f'orphan bundle {f}')

    print(f'objects={len(pids)} container={len(ckeys)} preload={len(at["m_PreloadTable"])} '
          f'textures=?, sprites={len(sprites)} trims={len(trims)} clips={len(clips)}')
    print('catalog counts', nk, nb, ne, 'iids', len(ids), 'bkey', bkey)
    print('FAILS', len(fails))


if __name__ == '__main__':
    main()
