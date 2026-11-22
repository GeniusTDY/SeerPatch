#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.1.32: 把 3042 / 3043 的战斗资源合并进已有的 fight3041 包。

原因：3041 的战斗包在官方 APK 里本来就有（补丁只是替换），
而 3042 / 3043 是新增文件，游戏从 APK 内加载新增条目会失败。
合并后补丁只替换已有的 fight3041 包，不再需要新增文件。
"""
import sys, os, json, struct, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
sys.path.insert(0, '/workspace/work')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'
from UnityPy.files.ObjectReader import ObjectReader
from UnityPy.helpers import TypeTreeHelper
from UnityPy.streams import EndianBinaryWriter
import seer

AND = '/workspace/patch_v1.1.31/assets/aa/Android'
TARGET_ENC = AND + '/fight3041_assets_all_6b19939c69def5b7c66c3cc84ce44beb.bundle'
SOURCES = {
    '3042': AND + '/fight3042_assets_all_f3967812cf6958a82081c3b8ffc4bee7.bundle',
    '3043': AND + '/fight3043_assets_all_f199809ee4b7c930a6ab659b18f61470.bundle',
}
OUT_ENC = '/workspace/work/fight3041_v1132.bundle'
OUT_PLAIN = '/workspace/work/fight3041_v1132.plain'
SKIP_TYPES = {'AssetBundle', 'MonoScript'}


def load(p):
    plain, salt = seer.decrypt_bytes(open(p, 'rb').read())
    env = UnityPy.load(plain)
    bf = env.files[list(env.files.keys())[0]]
    sf = bf.files[[k for k in bf.files if not k.endswith('.resS')][0]]
    return plain, salt, bf, sf


def remap(node, mapping):
    if isinstance(node, dict):
        if len(node) == 2 and 'm_FileID' in node and 'm_PathID' in node:
            fid, pid = node['m_FileID'], node['m_PathID']
            if fid == 0 and pid != 0 and pid in mapping:
                return {'m_FileID': 0, 'm_PathID': mapping[pid]}
            return node
        return {k: remap(v, mapping) for k, v in node.items()}
    if isinstance(node, list):
        return [remap(v, mapping) for v in node]
    return node


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


def main():
    plain, salt, bf, sf = load(TARGET_ENC)
    ab = next(o for o in sf.objects.values() if o.type.name == 'AssetBundle')
    at = ab.read_typetree()
    templates = {}
    for o in sf.objects.values():
        templates.setdefault(o.type.name, o)

    next_pid = max(sf.objects) + 1
    added = 0
    for pid in SOURCES:
        s_plain, _s_salt, _s_bf, s_sf = load(SOURCES[pid])
        mapping = {}
        for o in s_sf.objects.values():
            if o.type.name in SKIP_TYPES:
                continue
            mapping[o.path_id] = next_pid
            next_pid += 1

        for o in s_sf.objects.values():
            if o.type.name in SKIP_TYPES:
                continue
            tt = remap(o.read_typetree(), mapping)
            add_obj(sf, templates[o.type.name], mapping[o.path_id], tt)
            added += 1

        s_ab = next(o for o in s_sf.objects.values() if o.type.name == 'AssetBundle')
        s_at = s_ab.read_typetree()
        for key, info in s_at['m_Container']:
            new_pid = mapping[info['asset']['m_PathID']]
            at['m_PreloadTable'].append({'m_FileID': 0, 'm_PathID': new_pid})
            at['m_Container'].append([
                key,
                {'preloadIndex': len(at['m_PreloadTable']) - 1, 'preloadSize': 1,
                 'asset': {'m_FileID': 0, 'm_PathID': new_pid}},
            ])
        print(pid, 'merged objs', len(mapping), 'container now', len(at['m_Container']))

    ab.save_typetree(at)
    sf.objects = dict(sorted(sf.objects.items()))
    out = bf.save(packer='lz4')
    open(OUT_PLAIN, 'wb').write(out)
    open(OUT_ENC, 'wb').write(seer.encrypt(out, salt))
    print('added', added, 'total objs', len(sf.objects))
    print('plain', len(out), 'enc', os.path.getsize(OUT_ENC), 'salt', salt.hex())
    print('container', len(at['m_Container']), 'preload', len(at['m_PreloadTable']))
    print('ascending', list(sf.objects) == sorted(sf.objects), 'min/max', min(sf.objects), max(sf.objects))


if __name__ == '__main__':
    main()
