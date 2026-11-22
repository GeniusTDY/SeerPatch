#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给 fight3042/3043 补 3042_1/3043_1 的待机 trim（586x625 1:1 显示）。

与 v1.1.29 的 fight3041 保持一致：待机 clip 也要有一条 trim 资源，
否则会退回 prefab 拉伸框而显得偏小。
"""
import sys, os, json, random, struct
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
sys.path.insert(0, '/workspace/work')
import warnings
warnings.filterwarnings('ignore')
import UnityPy
from UnityPy.files.ObjectReader import ObjectReader
from UnityPy.helpers import TypeTreeHelper
from UnityPy.streams import EndianBinaryWriter
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
import seer

OUT_PLAIN = '/workspace/work/fight%s_v1130.plain'
OUT_ENC = '/workspace/work/fight%s_v1130.bundle'
W, H = 586, 625


def add_obj(sf, template, pid, typetree):
    node = template._get_typetree_node()
    w = EndianBinaryWriter(endian=sf.reader.endian)
    TypeTreeHelper.write_typetree(typetree, node, w, sf)
    data = w.bytes
    nr = ObjectReader.__new__(ObjectReader)
    nr.assets_file = sf
    nr.reader = sf.reader
    nr.data = data
    nr.version = sf.version
    nr.version2 = sf.header.version
    nr.platform = sf.target_platform
    nr.build_type = sf.build_type
    nr.path_id = pid
    nr.type_id = template.type_id
    nr.serialized_type = template.serialized_type
    nr.class_id = template.class_id
    nr.type = template.type
    nr.byte_size = len(data)
    sf.objects[pid] = nr
    return nr


def run(pid):
    src = OUT_PLAIN % pid
    env = UnityPy.load(open(src, 'rb').read())
    bf = env.files[list(env.files.keys())[0]]
    sf = bf.files[[k for k in bf.files if not k.endswith('.resS')][0]]

    trims = {}
    ab = None
    for o in sf.objects.values():
        if o.type.name == 'AssetBundle':
            ab = o
        elif o.type.name == 'TextAsset':
            t = o.read_typetree()
            if t['m_Name'].endswith('.trim'):
                trims[t['m_Name'][:-5]] = o
    assert ab is not None
    assert (pid + '_1') not in trims, 'already has idle trim'

    template = trims[pid + '_2']
    js = {
        'animKey': pid + '_1',
        'frameCount': 21,
        'frames': [{
            'spriteName': str(i + 1), 'sourceW': W, 'sourceH': H,
            'trimX': 0, 'trimY': 0, 'trimW': W, 'trimH': H,
        } for i in range(21)],
    }
    tt = template.read_typetree()
    tt['m_Name'] = pid + '_1.trim'
    tt['m_Script'] = '\ufeff' + json.dumps(js, ensure_ascii=False, indent=4)

    npid = -8500000000000000000 - random.getrandbits(40)
    while npid in sf.objects:
        npid -= 1
    add_obj(sf, template, npid, tt)

    at = ab.read_typetree()
    pre = at['m_PreloadTable']
    at['m_Container'].append([
        'Assets/PetAnimation/FightAnimation/%s/%s_1/%s_1.trim.json' % (pid, pid, pid),
        {'preloadIndex': len(pre), 'preloadSize': 1,
         'asset': {'m_FileID': 0, 'm_PathID': npid}},
    ])
    pre.append({'m_FileID': 0, 'm_PathID': npid})
    ab.save_typetree(at)
    print(pid, 'idle trim object', npid, 'container', len(at['m_Container']),
          'preload', len(pre))

    raw = bf.save(packer='lz4')
    open(src, 'wb').write(raw)
    _, salt = seer.decrypt_bytes(open(OUT_ENC % pid, 'rb').read())
    enc = seer.encrypt(raw, salt)
    open(OUT_ENC % pid, 'wb').write(enc)
    print(pid, 'plain', len(raw), 'enc', len(enc), 'salt', salt.hex())

    # 回读自检
    env2 = UnityPy.load(raw)
    n = 0
    for o in env2.objects:
        if o.type.name == 'TextAsset':
            t = o.read_typetree()
            if t['m_Name'] == pid + '_1.trim':
                j2 = json.loads(t['m_Script'].lstrip('\ufeff'))
                assert j2['frameCount'] == 21 and len(j2['frames']) == 21
                assert j2['frames'][0]['trimW'] == W
                n += 1
    assert n == 1, n
    print(pid, 'selfcheck ok')


if __name__ == '__main__':
    for pid in (sys.argv[1:] or ['3042', '3043']):
        run(pid)
