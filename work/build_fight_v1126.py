#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.1.26: 把 fight 包中 playerPet 的显示框放大 1.25 倍。

游戏中玩家侧精灵由 prefab 的 playerPet（RectTransform 330x389，pivot 0.5,0）
固定框显示；3041 待机贴图按此框拉伸，因此只改 3041 资源不会变大。
本脚本把该 RectTransform 的 sizeDelta 改为 412.5 x 486.25（= 1.25 倍），
底边 pivot 不变，精灵脚下位置不动。

只改这一个 typetree 字段，其余对象重新序列化后逐棵比对，必须与源完全一致。
"""
import sys, glob, hashlib
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
import warnings
warnings.filterwarnings('ignore')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
import seer

SRC_ENC = glob.glob('/workspace/patch_v1.1.25/assets/aa/Android/fight_*bundle')[0]
OUT_ENC = '/workspace/work/fight_v1126.bundle'
NEW = (412.5, 486.25)


def main():
    enc = open(SRC_ENC, 'rb').read()
    plain, salt = seer.decrypt_bytes(enc)
    env = UnityPy.load(plain)
    by = {o.path_id: o for o in env.objects}
    src_tt = {}
    for o in env.objects:
        try:
            src_tt[o.path_id] = o.read_typetree()
        except Exception:
            src_tt[o.path_id] = None

    target = None
    for o in env.objects:
        if o.type.name != 'GameObject':
            continue
        t = o.read_typetree()
        if t['m_Name'] != 'playerPet':
            continue
        rts = [by[c['component']['m_PathID']] for c in t['m_Component']
               if by.get(c['component']['m_PathID']) and
               by[c['component']['m_PathID']].type.name == 'RectTransform']
        if rts:
            target = rts[0]
            break
    assert target is not None
    tt = target.read_typetree()
    print('before sizeDelta', tt['m_SizeDelta'], 'pivot', tt['m_Pivot'])
    assert (tt['m_SizeDelta']['x'], tt['m_SizeDelta']['y']) == (330.0, 389.0)
    assert (tt['m_Pivot']['x'], tt['m_Pivot']['y']) == (0.5, 0.0)
    tt['m_SizeDelta'] = {'x': NEW[0], 'y': NEW[1]}
    target.save_typetree(tt)

    bf = list(env.files.values())[0]
    print('files', list(env.files.keys()))
    out = bf.save(packer='lz4')
    open('/workspace/work/fight_v1126.plain', 'wb').write(out)
    print('plain', len(plain), '->', len(out))

    # 自检：只有目标 RectTransform 的 typetree 变化
    env2 = UnityPy.load(out)
    objs2 = list(env2.objects)
    by2 = {o.path_id: o for o in objs2}
    assert len(objs2) == len(list(env.objects)), (len(objs2), len(list(env.objects)))
    changed = []
    for o in objs2:
        if o.path_id not in src_tt:
            continue
        a = src_tt[o.path_id]
        try:
            b = o.read_typetree()
        except Exception:
            continue
        if a != b:
            changed.append((o.type.name, o.path_id))
    print('changed typetrees', changed)
    assert changed == [('RectTransform', target.path_id)], changed
    t2 = by2[target.path_id].read_typetree()
    assert (t2['m_SizeDelta']['x'], t2['m_SizeDelta']['y']) == NEW
    print('after sizeDelta', t2['m_SizeDelta'])

    enc2 = seer.encrypt(out, salt)
    open(OUT_ENC, 'wb').write(enc2)
    print('encrypted', len(enc2), 'sha', hashlib.sha256(enc2).hexdigest())

    # 回读
    p3, s3 = seer.decrypt_bytes(open(OUT_ENC, 'rb').read())
    assert s3 == salt and p3 == out
    print('roundtrip ok')


if __name__ == '__main__':
    main()
