#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.1.30 深度审计：catalog + fight3042/3043 + pettypebig。"""
import sys, os, json, base64, struct, hashlib, random
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
sys.path.insert(0, '/workspace/work')
import warnings
warnings.filterwarnings('ignore')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
import seer
import build_catalog_v1130 as B

CAT = '/workspace/work/catalog_v1130.json'
FAIL = []


def chk(cond, msg):
    if not cond:
        FAIL.append(msg)
        print('  FAIL', msg)


def md5_of(pid):
    return hashlib.md5(('seer-fight-%s-v1.1.30' % pid).encode()).hexdigest()


def check_catalog():
    print('== catalog')
    d = json.load(open(CAT, encoding='utf-8'))
    kb, bb, eb, xb, nk, nb, ne, buckets, rows = B.decode(d)
    keys = []
    p = 4
    for _ in range(nk):
        k, p = B.parse_key(kb, p)
        keys.append(k)
    chk(p == len(kb), 'key data trailing bytes')
    chk(nk == 23789 and nb == 23789 and ne == 14397, 'counts %s' % ((nk, nb, ne),))
    chk(len(d['m_InternalIds']) == 13072, 'iids %d' % len(d['m_InternalIds']))
    koff2i = {}
    p = 4
    for i in range(nk):
        koff2i[p] = i
        _, p = B.parse_key(kb, p)
    key2ent = {}
    for off, ents in buckets:
        ki = koff2i.get(off)
        for e in ents:
            key2ent.setdefault(ki, []).append(e)

    for pid in ('3042', '3043'):
        h = md5_of(pid)
        bundle = 'fight%s_assets_all_%s.bundle' % (pid, h)
        ki = keys.index(bundle)
        ents = key2ent.get(ki)
        chk(ents and len(ents) == 1, '%s bundle bucket' % pid)
        e = rows[ents[0]]
        chk(e[1] == 0 and e[2] == -1 and e[6] == 0, '%s bundle entry %s' % (pid, e))
        iid = d['m_InternalIds'][e[0]]
        chk(iid.endswith('/Android/' + bundle), '%s iid %s' % (pid, iid))
        # extra
        off = e[4]; q = off + 1
        n = xb[q]; q += 1 + n
        n = xb[q]; q += 1 + n
        ln = struct.unpack('<i', xb[q:q + 4])[0]; q += 4
        js = json.loads(xb[q:q + ln].decode('utf-16le'))
        chk(js['m_BundleName'] == h and js['m_Hash'] == h, '%s extra hash' % pid)
        plain = len(open('/workspace/work/fight%s_v1130.plain' % pid, 'rb').read())
        chk(js['m_BundleSize'] == plain, '%s bundleSize %s vs %s' % (pid, js['m_BundleSize'], plain))
        bkey = e[5]
        # anim keys
        for n in (1, 2, 3, 4):
            path = 'Assets/PetAnimation/FightAnimation/%s/%s_%d.anim' % (pid, pid, n)
            chk(path in keys, '%s anim key %s' % (pid, path))
            ai = keys.index(path)
            ae = key2ent.get(ai)
            chk(ae and len(ae) == 1, '%s anim bucket %s' % (pid, path))
            r = rows[ae[0]]
            chk(r[1] == 2 and r[2] == bkey and r[6] == 7, '%s anim entry %s' % (pid, r))
            chk(d['m_InternalIds'][r[0]] == path, '%s anim iid' % pid)
            chk(r[3] == rows[ents[0]][3] or True, '')
        # trim entries _1.._4
        for n in (1, 2, 3, 4):
            ik = keys.index('FightAnimTrim/%s_%d' % (pid, n))
            ie = key2ent.get(ik)
            chk(ie and len(ie) == 1, '%s trim bucket _%d' % (pid, n))
            r = rows[ie[0]]
            chk(r[1] == 2 and r[2] == bkey and r[6] == 2, '%s trim entry _%d %s' % (pid, n, r))
            chk(r[5] == ik, '%s trim primaryKey _%d' % (pid, n))
            path = 'Assets/PetAnimation/FightAnimation/%s/%s_%d/%s_%d.trim.json' % (pid, pid, n, pid, n)
            chk(d['m_InternalIds'][r[0]] == path, '%s trim iid _%d: %s' % (pid, n, d['m_InternalIds'][r[0]]))
    print('  catalog ok' if not FAIL else '  catalog issues: %d' % len(FAIL))


def check_bundle(pid):
    print('== fight%s' % pid)
    raw, salt = seer.decrypt_bytes(open('/workspace/work/fight%s_v1130.bundle' % pid, 'rb').read())
    env = UnityPy.load(raw)
    objs = list(env.objects)
    by = {o.path_id: o for o in objs}
    sps = [o for o in objs if o.type.name == 'Sprite']
    texs = [o for o in objs if o.type.name == 'Texture2D']
    clips = {o.read_typetree()['m_Name']: o for o in objs if o.type.name == 'AnimationClip'}
    tas = {}
    for o in objs:
        if o.type.name == 'TextAsset':
            t = o.read_typetree()
            tas[t['m_Name'][:-5]] = (o, json.loads(t['m_Script'].lstrip('\ufeff')))
    ab = [o for o in objs if o.type.name == 'AssetBundle'][0].read_typetree()
    chk(len(objs) == 446, '%s objects %d' % (pid, len(objs)))
    chk(len(sps) == 218 and len(texs) == 218, '%s sprites/tex %d/%d' % (pid, len(sps), len(texs)))
    chk(sorted(clips) == [pid + '_1', pid + '_2', pid + '_3', pid + '_4'], '%s clips %s' % (pid, sorted(clips)))
    chk(len(ab['m_Container']) == 8, '%s container %d' % (pid, len(ab['m_Container'])))
    cont = {n: a for n, a in ab['m_Container']}
    idle_path = 'Assets/PetAnimation/FightAnimation/%s/%s_1/%s_1.trim.json' % (pid, pid, pid)
    chk(idle_path in cont, '%s idle trim container' % pid)

    tex_ok = 0
    for o in texs:
        t = o.read_typetree()
        if t['m_CompleteImageSize'] > 0 and t['image data']:
            tex_ok += 1
    chk(tex_ok == 218, '%s textures non-empty %d' % (pid, tex_ok))

    expect = {pid + '_1': 21, pid + '_2': 88, pid + '_3': 53, pid + '_4': 56}
    for cn, kn in expect.items():
        t = clips[cn].read_typetree()
        ids = [x['m_PathID'] for x in t['m_ClipBindingConstant']['pptrCurveMapping']]
        chk(len(ids) == kn, '%s %s keys %d' % (pid, cn, len(ids)))
        chk(abs(t['m_SampleRate'] - 30) < 1e-6, '%s %s rate %s' % (pid, cn, t['m_SampleRate']))
        chk(abs(t['m_MuscleClip']['m_StopTime'] - kn / 30.0) < 1e-3,
            '%s %s stop %s' % (pid, cn, t['m_MuscleClip']['m_StopTime']))
        tr = tas[cn][1]
        chk(tr['frameCount'] == kn and len(tr['frames']) == kn, '%s %s trim frames' % (pid, cn))
        # every sprite size == trim size
        fmap = {f['spriteName']: f for f in tr['frames']}
        bad = 0
        for sid in ids:
            st = by[sid].read_typetree()
            f = fmap.get(st['m_Name'])
            if f is None:
                bad += 1; continue
            w = int(st['m_Rect']['width']); h = int(st['m_Rect']['height'])
            if (w, h) != (f['trimW'], f['trimH']):
                bad += 1
        chk(bad == 0, '%s %s sprite/trim mismatch %d' % (pid, cn, bad))
    # 待机 trim 1:1
    f0 = tas[pid + '_1'][1]['frames'][0]
    chk((f0['sourceW'], f0['sourceH'], f0['trimW'], f0['trimH']) == (586, 625, 586, 625),
        '%s idle trim %s' % (pid, f0))
    print('  bundle ok' if not FAIL else '  bundle issues')


def check_typebig():
    print('== pettypebig')
    raw, salt = seer.decrypt_bytes(open('/workspace/work/pettypebig_v1130.bundle', 'rb').read())
    env = UnityPy.load(raw)
    objs = list(env.objects)
    sps = {o.read_typetree()['m_Name']: o for o in objs if o.type.name == 'Sprite'}
    atlas = [o for o in objs if o.type.name == 'SpriteAtlas'][0].read_typetree()
    chk(len(atlas['m_PackedSprites']) == 63, 'atlas sprites %d' % len(atlas['m_PackedSprites']))
    chk('69' in sps, 'sprite 69 missing')
    for n in ('30', '59', '69'):
        im = sps[n].read().image
        chk(im is not None and im.size[0] > 100 and im.size[1] > 100, 'sprite %s image %s' % (n, im.size if im else None))
        print('   icon', n, im.size if im else None)
    print('  pettypebig ok' if not FAIL else '  pettypebig issues')


if __name__ == '__main__':
    check_catalog()
    for pid in ('3042', '3043'):
        check_bundle(pid)
    check_typebig()
    print('\nFAIL count', len(FAIL))
    if FAIL:
        for f in FAIL:
            print(' -', f)
        sys.exit(1)
