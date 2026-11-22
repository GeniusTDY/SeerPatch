# PlayerData.json 解密明文与字段说明

## 一、解密信息

| 项目 | 内容 |
|---|---|
| 文件 | `PlayerData.decrypted.json`（完整明文，UTF-8，格式化 JSON） |
| 加密方式 | `Base64( 明文 XOR 循环密钥 )`，即重复密钥异或（字节版维吉尼亚） |
| 密钥 | ASCII 字符串 `51fc6818b9404196`（16 字节） |
| 密钥长度 | 16 字节循环 |
| 结论 | 非标准密码学加密（不是 AES/DES/RC4），属于轻量混淆 |

> 说明：`51fc6818b9404196` 形似 16 位十六进制串，但实际是按 ASCII 字符逐字节参与异或的密钥。

解密代码：

```python
import base64

key = b"51fc6818b9404196"
raw = base64.b64decode(open("PlayerData.json", "rb").read())
plain = bytes(b ^ key[i % 16] for i, b in enumerate(raw)).decode("utf-8")
open("PlayerData.decrypted.json", "w", encoding="utf-8").write(plain)
```

---

## 二、顶层字段（51 个）

| 字段 | 类型 | 当前值 | 含义 |
|---|---|---|---|
| `abyssKeyRemaining` | int | 0 | 深渊钥匙剩余数量 |
| `abyssKeyPaused` | bool | false | 深渊钥匙计时是否暂停 |
| `abyssKeyCollapsed` | bool | false | 深渊钥匙是否已崩塌/失效 |
| `essenceItemIdVersion` | int | 1 | 精华类道具 ID 版本号 |
| `lookoutGachaMisses` | int | 0 | 瞭望塔抽卡连续未中次数（保底计数） |
| `SerErDou` | int | 41492468 | 赛尔豆（游戏货币） |
| `playerName` | str | `""` | 玩家昵称（空表示未设置） |
| `profile` | object | 见第三节 | 玩家档案数据 |
| `seerAppearanceVersion` | int | 2 | 赛尔（玩家形象）外观版本 |
| `seerFlying` | bool | true | 赛尔是否处于飞行状态 |
| `seerBodyColor` | str | `#FF8026` | 赛尔身体颜色（十六进制 RGB） |
| `nonoBodyColor` | str | `#FF8CBF` | NONO（诺诺）身体颜色 |
| `seerSuitId` | int | 0 | 赛尔当前套装 ID（0 = 默认） |
| `baseHome` | object | 见第四节 | 基地/家园数据 |
| `seerClothingItemIds` | int[] | `[100019,100017,100016,100618]` | 已拥有的赛尔服装道具 ID |
| `followingPetCatchTime` | str | `2026-11-01` | 跟随精灵的捕获日期 |
| `followingPetRandomValue` | int | 69662533 | 跟随精灵的随机值/个体校验种子 |
| `CanHitXuanWu` | bool | false | 是否可挑战玄武 |
| `BaiHuGuardiansCleared` | bool | false | 白虎守卫是否已全部清除 |
| `BaiHuDefeatedAvatars` | int | 0 | 已击败白虎分身数量 |
| `ZhuQueChallengeStage` | int | 0 | 朱雀挑战阶段 |
| `XierChallengeStage` | int | 0 | 希尔挑战阶段 |
| `PuLaTiaoZhan` | bool | false | 普拉挑战是否已开启/完成 |
| `puLaStep` | str | `""` | 普拉挑战步骤标记 |
| `boolHit88` | bool | true | 编号 88 的触发/解锁标记 |
| `boolHit42` | bool | true | 编号 42 的触发/解锁标记 |
| `boolHit50` | bool | true | 编号 50 的触发/解锁标记 |
| `boolHit69` | bool | true | 编号 69 的触发/解锁标记 |
| `PuNiProcess` | int | 7 | 谱尼挑战/封印进度 |
| `CanHitQingLong` | bool | false | 是否可挑战青龙 |
| `currentTowerIndex` | int | 0 | 当前爬塔层索引 |
| `totalPowerIndex` | int | 0 | 总战力值/战力索引 |
| `maxTowerNum` | int | 0 | 已到达的最高塔层数 |
| `rogueTowerHighestFloor` | int | 0 | 肉鸽塔最高层数 |
| `rogueTowerCompletedRuns` | int | 0 | 肉鸽塔通关次数 |
| `PlRewardStatue` | int | 0 | 奖励雕像/奖励档位（推测） |
| `keyinqijiexp` | int | 0 | 与“七界/奇界”相关的经验值（推测） |
| `AhwdcList` | int[] | 14 个 ID | 一组事件/精灵/道具 ID 列表（具体含义待确认） |
| `NuoYiErProgress` | int | 0 | 诺伊尔挑战进度 |
| `darkAlliance` | object | 见第五节 | 暗黑联盟数据 |
| `getItemList` | array | `[]` | 待领取道具列表 |
| `petSaveDatas` | object[] | 60 条 | 精灵存档数据（详见第六节） |
| `petSaveDatasInBag` | object[] | 5 条 | 背包内精灵数据（结构同精灵对象） |
| `petAbdanDatas` | object[] | 10 条 | 备用/图鉴精灵数据（均为 petId=46） |
| `firstMailPending` | bool | false | 是否有首封邮件待领取 |
| `exp` | int | 523079 | 玩家经验值 |
| `dicItem` | object | 172 条 | 道具字典，见第八节 |
| `abilityCores` | array | `[]` | 能力核心列表 |
| `YuanShenZhuDatas` | array | `[]` | 元神珠数据列表 |
| `jingYuanDatas` | object[] | 1 条 | 精元（待孵化精灵）数据，见第九节 |
| `petBreedState` | object | 见第十节 | 精灵繁殖状态 |

---

## 三、`profile` 玩家档案

| 字段 | 类型 | 当前值 | 含义 |
|---|---|---|---|
| `mimiId` | str | `321386029` | 米米号（赛尔号账号唯一 ID） |
| `registrationDate` | str | `2026-10-31` | 注册日期 |
| `selectedTitleId` | int | 0 | 当前佩戴称号 ID（0 = 无） |
| `unlockedTitleIds` | int[] | `[3,4,55]` | 已解锁称号 ID |
| `sptWins` | int[] | `[301…320]` | SPT 挑战已通关关卡编号（17 个） |
| `battleCount` | int | 3256 | 累计战斗次数 |
| `winCount` | int | 2606 | 累计胜利次数 |
| `onlineBattleCount` | int | 0 | 联机对战次数 |
| `onlineWinCount` | int | 0 | 联机对战胜利次数 |
| `graduationCount` | int | 0 | 精灵“毕业”/满级培养次数 |
| `monKingWin` | int | 0 | 魔王类玩法胜利次数（推测） |
| `messWin` | int | 0 | 乱斗类玩法胜利次数（推测） |
| `maxStage` | int | 0 | 最高关卡进度 |
| `maxArenaWins` | int | 0 | 竞技场最高胜场/最高连胜 |
| `collectedSpeciesIds` | int[] | 45 个 ID | 已收集精灵种类 ID 列表 |
| `gaiaRuleMask` | int | 0 | 盖亚规则位掩码（按位标记解锁规则） |
| `erselaDayMask` | int | 0 | 厄尔塞拉日期位掩码（按位标记天数） |
| `maxTrialStage` | int | 0 | 最高试炼关卡 |

---

## 四、`baseHome` 基地/家园

| 字段 | 类型 | 当前值 | 含义 |
|---|---|---|---|
| `version` | int | 1 | 家园数据版本号 |
| `roomId` | int | 500001 | 当前房间 ID |
| `owned` | object[] | 20 条 | 已拥有家具列表 |
| `owned[].id` | int | 500001 | 家具 ID |
| `owned[].count` | int | 1 | 拥有数量 |
| `placements` | object[] | 17 条 | 已摆放家具列表 |
| `placements[].id` | int | 500501 | 家具 ID |
| `placements[].direction` | int | 0 | 摆放朝向 |
| `placements[].x` | float | 269.46 | 摆放 X 坐标 |
| `placements[].y` | float | 323.81 | 摆放 Y 坐标 |

---

## 五、`darkAlliance` 暗黑联盟

| 字段 | 类型 | 当前值 | 含义 |
|---|---|---|---|
| `phase` | int | 0 | 当前阶段 |
| `guardWins` | int | 0 | 守卫战胜利次数 |

---

## 六、精灵对象（`petSaveDatas` / `petSaveDatasInBag` / `petAbdanDatas` 的元素）

| 字段 | 类型 | 示例 | 含义 |
|---|---|---|---|
| `fixedBattleFormId` | int | 0 | 固定战斗形态 ID（0 = 普通形态） |
| `abilityTraitId` | int | 0 | 特性 ID（精灵特性） |
| `abilityTypeId` | int | 0 | 特性类型 ID |
| `atkValueItem` | int | 0 | 攻击数值道具（刻印/加成）提供的数值 |
| `spAtkValueItem` | int | 0 | 特攻数值道具加成 |
| `defValueItem` | int | 0 | 防御数值道具加成 |
| `spDefValueItem` | int | 0 | 特防数值道具加成 |
| `speedValueItem` | int | 0 | 速度数值道具加成 |
| `hpValueItem` | int | 0 | 体力数值道具加成 |
| `SpecialBaseDataAtk` | int | 0 | 特殊形态基础攻击补正 |
| `SpecialBaseDataDef` | int | 0 | 特殊形态基础防御补正 |
| `SpecialBaseDataSpAtk` | int | 0 | 特殊形态基础特攻补正 |
| `SpecialBaseDataSpdef` | int | 0 | 特殊形态基础特防补正 |
| `SpecialBaseDataSpeed` | int | 0 | 特殊形态基础速度补正 |
| `SpecialBaseDataHp` | int | 0 | 特殊形态基础体力补正 |
| `YouNaSiSPecialSkill` | str | `""` | 尤纳斯特殊技能标记 |
| `PulaBoundSkillIds` | int[] | `[]` | 普拉绑定的技能 ID 列表 |
| `petId` | str | `"1"` / `"5607"` | 精灵（种族）ID |
| `petSpecialSkillUse` | str | `""` | 精灵特殊技能使用状态 |
| `level` | int | 2 / 100 | 等级 |
| `evHP` | int | 0 | 体力学习力（努力值） |
| `evAttack` | int | 8 | 攻击学习力 |
| `evDefense` | int | 0 | 防御学习力 |
| `evSpAttack` | int | 0 | 特攻学习力 |
| `evSpDefense` | int | 0 | 特防学习力 |
| `evSpeed` | int | 0 | 速度学习力 |
| `randomValue` | int | 50935726 | 随机值/个体校验种子 |
| `nature` | int | 24 / 3 | 性格 ID |
| `hadTime` | str | `2026-10-31` | 获得日期 |
| `XingBie` | int | 0 / 1 / 2 | 性别（0 无性别 / 1 雄 / 2 雌） |
| `isInBag` | bool | false | 是否在背包中 |
| `ivHP` | int | 29 / 31 | 体力个体值（IV） |
| `specialNature` | int | 999 / 24 | 特殊性格 ID（999 = 无） |
| `isHasSpecialNature` | bool | false | 是否拥有特殊性格 |
| `currentExp` | int | 8 | 当前经验值 |
| `isMys` | int | 0 | 神秘/变异类标记（具体含义待确认） |
| `moves` | int[] | `[]` | 已学技能 ID 列表 |
| `movesFight` | object[] | 1~4 条 | 战斗技能详细数据，见第七节 |
| `YuanShenZhu` | array | `[]` | 该精灵的元神珠数据 |

---

## 七、技能对象（`movesFight` 的元素）

| 字段 | 类型 | 示例 | 含义 |
|---|---|---|---|
| `ID` | int | 10001 | 技能 ID |
| `Name` | str | 撞击 | 技能名称 |
| `Category` | int | 1 / 4 | 技能分类（1 物理攻击 / 4 变化/辅助，其余为特殊攻击等） |
| `Type` | int | 8 | 属性/系别 ID（8 = 普通系） |
| `Power` | int | 35 | 技能威力 |
| `MaxPP` | int | 35 | 最大 PP（使用次数） |
| `Accuracy` | int | 95 | 命中率（%） |
| `Priority` | int | 0 | 优先级/先手值 |
| `Url` | str | `normal_1` | 技能动画/资源标识 |
| `Cooldown` | int | 1000 / 291 | 冷却时间（毫秒级） |
| `SideEffect` | str | `"4 4"` | 附加效果编号 |
| `SideEffectArg` | str | `"1 100 1 3 100 1"` | 附加效果参数 |
| `AtkType` | str | `"3"` | 攻击类型标记 |
| `MustHit` | str | `"1"` | 是否必中 |
| `Info` | str | 防御和特防提升了 | 技能效果描述 |
| `CritRate` | str | `""` | 暴击率补正 |
| `CritAtkFirst` | int | 0 | 先手暴击标记 |
| `CritSelfHalfHp` | int | 0 | 自身血量过半时暴击标记 |
| `UseKeYin` | bool | false | 是否使用“克制”机制 |
| `UserStatChanges` | array | `[]` | 对自身的能力变化 |
| `TargetStatChanges` | array | `[]` | 对目标的能力变化 |
| `StatusEffects` | array | `[]` | 附加状态效果 |
| `isPlayer` | bool | false | 是否玩家侧技能 |
| `isXianShou` | bool | false | 是否先手技能 |
| `isUseKeYin` | bool | false | 是否使用克制 |

---

## 八、`dicItem` 道具字典

| 字段 | 类型 | 示例 | 含义 |
|---|---|---|---|
| `pairs` | object[] | 172 条 | 道具 ID → 数量 的键值列表 |
| `pairs[].key` | str | `"100027"` | 道具 ID |
| `pairs[].value` | int | 1 / 121 | 持有数量 |

---

## 九、`jingYuanDatas` 精元（待孵化精灵）

| 字段 | 类型 | 示例 | 含义 |
|---|---|---|---|
| `index` | int | 4542753 | 唯一索引/实例 ID |
| `itemId` | int | 400105 | 精元道具 ID |
| `isMys` | bool | true | 神秘/特殊标记（待确认） |
| `petId` | int | 0 | 孵化目标精灵 ID（0 = 尚未确定） |

---

## 十、`petBreedState` 精灵繁殖状态

| 字段 | 类型 | 当前值 | 含义 |
|---|---|---|---|
| `eggs` | array | `[]` | 正在孵化的精灵蛋列表 |
| `nextBreedAtUnix` | int | 0 | 下次可繁殖时间（Unix 时间戳，0 = 无冷却） |

---

## 十一、其余列表型字段

| 字段 | 含义 |
|---|---|
| `getItemList` | 待领取道具列表（当前为空） |
| `abilityCores` | 能力核心列表（当前为空） |
| `YuanShenZhuDatas` | 元神珠数据列表（当前为空） |
| `AhwdcList` | 14 个 ID 的列表，疑似特定活动/图鉴记录（具体含义待确认） |

---

## 附：说明与推断依据

1. 该存档属于《赛尔号》体系的玩家数据：`SerErDou`（赛尔豆）、`mimiId`（米米号）、`seer*`（赛尔形象）、`nonoBodyColor`（NONO）、`SPT`、`petSaveDatas`（精灵）、`jingYuanDatas`（精元）、`YuanShenZhu`（元神珠）、白虎/玄武/青龙/朱雀、谱尼、诺伊尔、尤纳斯、盖亚、厄尔塞拉等字段均与之对应。
2. 字段含义由字段名、数值范围和游戏常识推断；标注“推测/待确认”的字段（如 `PlRewardStatue`、`keyinqijiexp`、`isMys`、`AhwdcList`、`monKingWin`、`messWin`）没有权威定义，仅供参考。
3. 解密后的明文为标准 JSON，可直接用任意 JSON 工具打开。
