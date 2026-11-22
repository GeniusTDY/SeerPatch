#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 APK 内置技能数据 pdapp/assets/skills.json

数据来源：
  skill1.xml  技能基础数值（威力/命中/PP/先制/必中/暴击/连击/MonID）
  skill2.txt  客户端技能描述原文
  itemId      客户端刻印表（Type=刻印N，TargetId=技能 ID，Info=强化内容）
  技能效果整理.md  少量特殊技能的补充说明（仅取“完整描述”用于补标点）
"""
import json
import os
import re
import xml.etree.ElementTree as ET

CFG = '/workspace/work/skillcfg'
MD = '/workspace/技能效果整理.md'
OUT = '/workspace/pdapp/assets/skills.json'

# 客户端 item 表（TextAsset）中的刻印条目：Type="刻印N"、TargetId=技能 ID、Info=强化内容。
ITEM_XML = ('/workspace/work/gamedata/assets/bin/Data/'
            '16749c19f49d4634c8edcc6288396d42')

# 客户端配置未收录名称、但可从技能归属精灵确认的属性编号
TYPE_ALIAS = {
    223: '神灵',
    50: '暗影·神秘',
    52: '光·圣灵',
    53: '飞行·神秘',
    56: '暗影·圣灵',
    59: '光·战斗',
    62: '邪灵·神秘',
    69: '光·暗影',
    1001: '电',
}

# 仅在“描述未写、但代码中确有数值”时保留的人工补充。
# 键为技能 ID，值为最终展示文本（不含句末句号）。
CURATED = {
    10210: '单次使用实际秒杀率 15%（命中 15% × 秒杀 100%）',
    11022: '单次实际秒杀率 5%（命中 100% × 5%）',
    11662: '单次实际秒杀率 14.25%（命中 95% × 15%）',
    13546: '单次实际秒杀率 5%（命中 100% × 5%）',
    14072: '单次实际秒杀率 4.75%（命中 95% × 5%）',
    14371: '单次实际秒杀率 4.75%（命中 95% × 5%）',
    14327: '单次实际秒杀率 19%（命中 95% × 20%）',
    31676: '致命一击率 +9/16，约 +56.25%',
    20007: '满 5 回合最多吸取对方最大体力的 5/8',
    25942: '满 4 回合最多吸取对方最大体力的 1 倍',
    13297: 'AtkNum=3 表示连续使用计数，并非单回合连击 3 次',
    31141: '恢复量等于自身最大体力，并造成等量百分比伤害',
}


def load_desc():
    txt = open(CFG + '/skill2.txt', encoding='utf-8', errors='replace').read()
    return {k: v.strip() for k, v in re.findall(r'<M(\d+)>(.*?)</M\d+>', txt, re.S)}


def load_md_desc():
    """整理文档里的“完整描述”只为补标点，不改动文案本身。"""
    out, cur = {}, None
    for line in open(MD, encoding='utf-8'):
        line = line.rstrip('\n')
        m = re.match(r'^###\s+.+?`(\d+)`\s*$', line)
        if m:
            cur = int(m.group(1))
            continue
        if line.startswith('## '):
            cur = None
            continue
        if cur is not None and line.startswith('- 完整描述：'):
            out[cur] = line.split('：', 1)[1].strip()
    return out


def load_marks():
    """读取客户端刻印表：TargetId 技能 ID → [{n: 刻印名, d: 强化内容}]。

    Type="刻印8" 是完整技能石（TargetId 为 2222222 等占位值），不属于技能刻印，跳过。
    """
    data = open(ITEM_XML, 'rb').read().decode('utf-8', errors='ignore')
    out, seen = {}, set()
    for tag in re.findall(r'<Item\b[^>]*>', data):
        ty = item_attr(tag, 'Type')
        if not ty.startswith('刻印') or ty == '刻印8':
            continue
        tid = item_attr(tag, 'TargetId')
        name = item_attr(tag, 'Name')
        info = item_attr(tag, 'Info')
        if not tid.isdigit() or not name or not info:
            continue
        key = (tid, name, info)
        if key in seen:
            continue
        seen.add(key)
        out.setdefault(int(tid), []).append({'n': name, 'd': info})
    return out


def item_attr(tag, key):
    m = re.search(r'\b' + key + r'="([^"]*)"', tag)
    return m.group(1) if m else ''


def clean_desc(raw, polished):
    """折叠空白并去掉句末标点；仅当两版内容一致时采用补过标点的版本。"""
    raw = (raw or '').strip()
    polished = (polished or '').strip().lstrip('：:').strip()
    if polished:
        a = re.sub(r'[\s；;。：:]', '', polished)
        b = re.sub(r'[\s；;。：:]', '', raw)
        if a == b:
            raw = polished
    raw = re.sub(r'\s+', ' ', raw).strip()
    return punctuate(raw).rstrip('。；;，, ').strip()


def punctuate(d):
    """客户端个别技能描述没有分隔标点，仅在原文字之间补分号。"""
    if '若属性相同则技能威力提升' in d and '；' not in d:
        d = re.sub(r'提升(\d+)(?=先出手)', r'提升\1；', d)
        d = re.sub(r'PP1点(?=若后出手)', 'PP 1点；', d)
        d = re.sub(r'回合类效果(?=对手不处于)', '回合类效果；', d)
        d = re.sub(r'1/3(?=对手处于)', '1/3；', d)
        d = re.sub(r'臣服(?=若对手体力|命中后)', '臣服；', d)
    d = re.sub(r'(?<=[0-9])(?=技能使用成功时)', '；', d)
    return d


# 客户端个别描述缺少分隔标点、混用半角标点或存在明显笔误。
# 这里只补标点、去多余空格并修正这处明显笔误，不改写原意。
DESC_FIX = {
    10323: '先出手的话威力为2倍；清除对手护盾',
    10881: '命中后10%令对方中毒；威力大小为自身最大体力的1/3 + 自身个体值',
    10891: '命中后5%令对方中毒；命中后5%令对方烧伤；命中后5%令对方冻伤',
    12510: '命中后10%令对方烧伤；使用后2回合攻击击中对象要害概率增加1/16',
    13840: '令对方所有能力增强效果消失；每损失1点体力则额外附加1点固定伤害',
    13958: '命中后15%令对方害怕；命中后15%令对手睡眠；解除自身的能力下降状态',
    20009: '恢复自身最大体力的1/2；对选中对象或本方全体恢复1/3的体力',
    20291: '恢复自身最大体力的1/5；5回合内每回合恢复自身体力1/10',
    20686: '使自身在接下来的1回合中直接攻击必定致命一击；1回合攻击伤害是正常状态下的2倍',
    21522: '技能使用成功时，100%改变对手防御等级-1；100%改变对手特防等级-1；'
           '100%改变对手速度等级-1；命中后30%令对方冻伤',
    23245: '5回合内免疫所有受到的异常状态；攻击+1、防御+1、特防+1、速度+1；'
           '体力值低于1/2时强化效果翻倍',
    50014: '技能使用成功时，攻击+1、速度+1、命中+1；3回合内若使用技能则恢复150点体力值；'
           '3回合内自身受到直接攻击伤害的40%反馈给对手',
    50027: '降低对方当前血量的1/16；同时恢复对方最大生命值的1/16',
}


def type_name(ty, elements):
    if ty in TYPE_ALIAS:
        return TYPE_ALIAS[ty]
    el = elements.get(ty)
    if not el:
        return '未知'
    name = el.get('name') or ''
    if name.startswith('未定义属性'):
        return '未知'
    comps = el.get('components') or []
    if len(comps) > 1:
        parts = [elements[c]['name'] for c in comps if c in elements]
        if len(parts) > 1:
            return '·'.join(parts)
    return name


def crit_pct(cr):
    return ('%.2f' % (cr * 100.0 / 16)).rstrip('0').rstrip('.')


def uniq(notes):
    out = []
    for n in notes:
        n = n.strip().rstrip('。').strip()
        if n and n not in out:
            out.append(n)
    return out


def main():
    cfg = json.load(open(CFG + '/Config.txt', encoding='utf-8'))
    elements = {e['id']: e for e in cfg['elements']}
    cmoves = {m['id']: m for m in cfg['moves']}

    desc = load_desc()
    md_desc = load_md_desc()
    marks = load_marks()

    root = ET.parse(CFG + '/skill1.xml').getroot()
    seen, skills = set(), []
    for mv in root.findall('Move'):
        sid = int(mv.get('ID'))
        if sid in seen:
            continue
        seen.add(sid)
        cm = cmoves.get(sid, {})
        name = (mv.get('Name') or cm.get('name') or '').strip()
        ty = int(mv.get('Type') or cm.get('type') or 0)
        cat = int(mv.get('Category') or cm.get('category') or 3)
        # 属性技能（Category 3/4）统一归入普通系：客户端里多数属性技能本就标为普通，
        # 少数孤立条目（火魂献祭等）标成水/龙/机械，统一后与图鉴展示、筛选一致。
        if cat >= 3:
            ty = 8
        power = int(mv.get('Power') or 0)
        if cat >= 3 and power > 0:
            # 属性技能不应有直接伤害；少数条目（无念之意/魔化天枢）客户端误填了 Power。
            bad_power = power
            power = 0
        else:
            bad_power = 0
        acc = int(mv.get('Accuracy') if mv.get('Accuracy') is not None
                  else cm.get('accuracy') or 0)
        pp = int(mv.get('MaxPP') or cm.get('pp') or 0)
        pri = int(mv.get('Priority') or 0)
        mh = (mv.get('MustHit') or '') not in ('', '0') or bool(cm.get('mustHit'))
        cr = int(mv.get('CritRate') or 0)
        an = int(mv.get('AtkNum') or 0)
        mon = int(mv.get('MonID') or 0)
        d = DESC_FIX.get(sid) or clean_desc(desc.get(str(sid), ''), md_desc.get(sid, ''))
        if not mh and d.startswith('必中'):
            # 属性技能的 MustHit 字段常缺省，但描述以「必中」开头即表示本次必定命中
            mh = True

        notes = []
        if sid in CURATED:
            notes.append(CURATED[sid])
        if pri > 0 and '先制' not in d:
            notes.append('先制+%d：优先于先制等级更低的技能出手' % pri)
        elif pri < 0 and '后制' not in d:
            notes.append('后制%d：出手顺序延后 %d 级' % (-pri, -pri))
        if mh and '必中' not in d:
            notes.append('必中：无法被闪避')
        if cr > 0 and not re.search(r'\d+\s*/\s*16', d):
            notes.append('致命一击率 %s%%（%d/16）' % (crit_pct(cr), cr))
        if an > 1 and cat in (1, 2) and '连续' not in d and '连击' not in d:
            notes.append('单回合连续攻击 %d 次' % an)
        if mon:
            notes.append('BOSS 专属技能（MonID=%d），玩家无法获得' % mon)
        if 1100001 <= sid <= 1100080:
            notes.append('技能石专属技能，非精灵自带技能')
        if power >= 100000:
            notes.append('客户端威力记为 %d，为占位值' % power)
        if bad_power:
            notes.append('客户端威力字段记为 %d，但分类为属性技能，实际不造成直接伤害' % bad_power)

        missing = []
        if acc <= 0:
            missing.append('命中')
        if pp <= 0:
            missing.append('PP')
        if missing:
            notes.append('客户端未记录' + '与'.join(missing))

        e = {'i': sid, 'n': name, 't': type_name(ty, elements), 'ty': ty,
             'c': cat, 'p': power, 'a': acc, 'pp': pp, 'd': d}
        if pri:
            e['pr'] = pri
        if mh:
            e['mh'] = 1
        if cr:
            e['cr'] = cr
        if an > 1:
            e['an'] = an
        if mon:
            e['mo'] = mon
        if sid in marks:
            e['mk'] = marks[sid]
        notes = uniq(notes)
        if notes:
            e['x'] = '；'.join(notes) + '。'
        skills.append(e)

    skills.sort(key=lambda s: s['i'])
    payload = {'skills': skills}
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, separators=(',', ':'))

    print('skills', len(skills))
    print('desc empty', sum(1 for s in skills if not s['d']))
    print('supplement', sum(1 for s in skills if s.get('x')))
    print('marked', sum(1 for s in skills if s.get('mk')),
          '/', sum(len(s['mk']) for s in skills if s.get('mk')))
    print('curated', len(CURATED))
    print('unknown type', sum(1 for s in skills if s['t'] == '未知'))
    print('size', os.path.getsize(OUT))


if __name__ == '__main__':
    main()
