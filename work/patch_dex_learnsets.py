#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补齐 dex.json 中缺失的可学技能。

Config.txt 的 learnsets 与客户端 skill3.txt 各有缺漏：
  - Config 对 10001 等 18 只精灵技能为空；
  - skill3 缺少部分新版精灵（如 5075 索伦森）及个别技能。
因此按技能 ID 取两者并集，同一技能以 Config 的等级为准。
"""
import json
import re
import xml.etree.ElementTree as ET

CFG = '/workspace/work/skillcfg'
DEX = '/workspace/pdapp/assets/dex.json'


def load_moves():
    root = ET.parse(CFG + '/skill1.xml').getroot()
    out = {}
    for mv in root.findall('Move'):
        mid = int(mv.get('ID'))
        if mid in out:
            continue
        out[mid] = (
            (mv.get('Name') or '').strip(),
            int(mv.get('Power') or 0),
            int(mv.get('MaxPP') or 0),
            int(mv.get('Category') or 3),
            int(mv.get('Type') or 0),
        )
    return out


def load_skill3():
    txt = open(CFG + '/skill3.txt', encoding='utf-8', errors='replace').read()
    out = {}
    for pid, body in re.findall(r'<ID>(\d+)</ID>(.*?)</row-\d+>', txt, re.S):
        vals = re.findall(r'<Move>(\d+)</Move>', body)
        pairs = [(int(vals[i]), int(vals[i + 1])) for i in range(0, len(vals) - 1, 2)]
        out.setdefault(int(pid), []).extend(pairs)
    return out


def load_monster():
    raw = open(CFG + '/9c14d78f3a5e4cf5b04ed1f44ab4e286', 'rb').read()
    txt = raw[raw.find(b'<Monsters>'):].decode('utf-8', errors='replace')
    out = {}
    for m in re.finditer(r'<Monster ID="(\d+)"[^>]*>(.*?)</Monster>', txt, re.S):
        out[int(m.group(1))] = [
            (int(a), int(b))
            for a, b in re.findall(r'<Move ID="(\d+)" LearningLv="(\d+)"', m.group(2))
        ]
    return out


def main():
    cfg = json.load(open(CFG + '/Config.txt', encoding='utf-8'))
    cmoves = {m['id']: m for m in cfg['moves']}
    moves = load_moves()
    s3 = load_skill3()
    mon = load_monster()

    data = json.load(open(DEX, encoding='utf-8'))
    changed = added = skipped = 0
    for pet in data['pets']:
        pid = int(pet['i'])
        rows = {}
        for m in pet.get('k') or []:
            mid = int(m[1])
            name = (moves.get(mid) or ((m[2] or '').strip(),))[0]
            rows[mid] = [m[0], mid, name, m[3], m[4], m[5], m[6]]
        for source in (s3, mon):
            for mid, lv in source.get(pid, []):
                if mid in rows:
                    continue
                mv = moves.get(mid)
                if mv is None:
                    cm = cmoves.get(mid)
                    if not cm:
                        skipped += 1
                        continue
                    mv = (cm.get('name', ''), cm.get('power', 0), cm.get('pp', 0),
                          cm.get('category', 3), cm.get('type', 0))
                rows[mid] = [lv, mid, mv[0], mv[1], mv[2], mv[3], mv[4]]
                added += 1
        new = [rows[k] for k in sorted(rows, key=lambda k: (rows[k][0], k))]
        if new != [list(x) for x in pet.get('k') or []]:
            pet['k'] = new
            changed += 1

    with open(DEX, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    print('pets changed', changed, 'skills added', added, 'skipped(no def)', skipped)
    for pid in (10001, 10002, 5075):
        p = next(x for x in data['pets'] if int(x['i']) == pid)
        print(pid, p['n'], len(p['k']), [k[2] for k in p['k']][:6])


if __name__ == '__main__':
    main()
