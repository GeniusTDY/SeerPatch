#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.1.32 合并包审计：对象表、引用、容器/预载、trim/clip、贴图解码。"""
import sys, warnings, json
warnings.filterwarnings('ignore')
sys.path.insert(0, '/workspace/tools')
sys.path.insert(0, '/workspace/tools/ext/unitypy-1.23.0')
import UnityPy, seer
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.62f3'

PATH = '/workspace/work/fight3041_v1132.bundle'
fails = []


def chk(cond, msg):
    if not cond:
        fails.append(msg)
        print('FAIL', msg)


def walk(node, path, out):
    if isinstance(node, dict):
        if len(node) == 2 and 'm_FileID' in node and 'm_PathID' in node:
            out.append((path, node['m_FileID'], node['m_PathID']))
            return
        for k, v in node.items():
            walk(v, f'{path}/{k}', out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, f'{path}[{i}]', out)


def main():
    plain, salt = seer.decrypt_bytes(open(PATH, 'rb').read())
    env = UnityPy.load(plain)
    bf = env.files[list(env.files.keys())[0]]
    sf = bf.files[list(bf.files.keys())[0]]
    pids = list(sf.objects.keys())
    chk(pids == sorted(pids), 'object table not ascending')
    chk(len(pids) == 1334, f'objects {len(pids)}')

    ab = next(o for o in sf.objects.values() if o.type.name == 'AssetBundle')
    at = ab.read_typetree()
    chk(at['m_AssetBundleName'] == '6b19939c69def5b7c66c3cc84ce44beb.bundle',
        f"ab name {at['m_AssetBundleName']}")
    chk(len(at['m_Container']) == 24, f"container {len(at['m_Container'])}")
    chk(len(at['m_PreloadTable']) == 464, f"preload {len(at['m_PreloadTable'])}")
    keys = [c[0] for c in at['m_Container']]
    chk(len(set(keys)) == 24, 'duplicate container keys')
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
    chk(keys[:8] == base8, '3041 container order changed')

    bad = []
    for o in sf.objects.values():
        refs = []
        walk(o.read_typetree(), '', refs)
        for path, fid, pid in refs:
            if fid == 0 and pid != 0 and pid not in sf.objects:
                bad.append((o.path_id, path, pid))
    chk(not bad, f'unresolved PPtrs {bad[:3]}')
    chk(all(x['m_PathID'] in sf.objects for x in at['m_PreloadTable']), 'preload unresolved')
    chk(all(v['asset']['m_PathID'] in sf.objects for _, v in at['m_Container']),
        'container unresolved')

    trims, clips, sprites = {}, [], set()
    textures = 0
    for o in sf.objects.values():
        if o.type.name == 'TextAsset':
            t = o.read_typetree()
            trims[t['m_Name']] = json.loads(t['m_Script'].lstrip('\ufeff'))
        elif o.type.name == 'AnimationClip':
            clips.append(o.read_typetree()['m_Name'])
        elif o.type.name == 'Sprite':
            sprites.add(o.read_typetree()['m_Name'])
        elif o.type.name == 'Texture2D':
            textures += 1

    want = {1: 21, 2: 88, 3: 53, 4: 56}
    for pid in ('3041', '3042', '3043'):
        for n, f in want.items():
            name = f'{pid}_{n}.trim'
            chk(name in trims, f'missing trim {name}')
            if name not in trims:
                continue
            js = trims[name]
            chk(js['frameCount'] == f and len(js['frames']) == f,
                f"frames {name} {js['frameCount']}")
            miss = [x['spriteName'] for x in js['frames'] if x['spriteName'] not in sprites]
            chk(not miss, f'trim missing sprites {name} {miss[:3]}')
            if n == 1:
                chk(all(x['sourceW'] == 586 and x['sourceH'] == 625 for x in js['frames']),
                    f'idle dims {name}')
        for n in (1, 2, 3, 4):
            chk(f'{pid}_{n}' in clips, f'missing clip {pid}_{n}')

    chk(len(trims) == 12, f'trims {len(trims)}')
    chk(len(clips) == 12, f'clips {len(clips)}')

    badsp = []
    for o in sf.objects.values():
        if o.type.name == 'Sprite':
            try:
                im = o.read().image
                if im is None or im.getbbox() is None:
                    badsp.append(o.read_typetree()['m_Name'])
            except Exception as e:
                badsp.append(o.read_typetree()['m_Name'] + ':err')
    chk(not badsp, f'empty sprites {badsp[:5]}')

    print(f'objects={len(pids)} textures={textures} sprites={len(sprites)} '
          f'trims={len(trims)} clips={len(clips)}')
    print('enc/plain', len(plain), 'salt', salt.hex())
    print('FAILS', len(fails))


if __name__ == '__main__':
    main()
