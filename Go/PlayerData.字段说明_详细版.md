# PlayerData 解密明文 · 详细字段说明

> 对应文件：`PlayerData.decrypted.json`（243,494 字节，UTF-8，标准 JSON）

> 加密方式：`Base64( 明文 XOR 16 字节循环密钥 )`；密钥为 ASCII 字符串 `51fc6818b9404196`。

> 说明：字段含义依据字段名、取值分布及《赛尔号》体系推断；标注“推测/待确认”的字段无权威定义。


## 1. 顶层字段（共 51 个）

| # | 字段 | 类型 | 当前值/规模 | 含义 |
|---:|---|---|---|---|
| 1 | `abyssKeyRemaining` | int | 0 | 深渊钥匙剩余数量 |
| 2 | `abyssKeyPaused` | bool | false | 深渊钥匙计时是否暂停 |
| 3 | `abyssKeyCollapsed` | bool | false | 深渊钥匙是否已崩塌/失效 |
| 4 | `essenceItemIdVersion` | int | 1 | 精华类道具 ID 版本号 |
| 5 | `lookoutGachaMisses` | int | 0 | 瞭望塔抽卡连续未中次数（保底计数） |
| 6 | `SerErDou` | int | 41492468 | 赛尔豆（游戏货币） |
| 7 | `playerName` | str | "" | 玩家昵称（空字符串=未设置） |
| 8 | `profile` | object | 对象（18 个键） | 玩家档案（18 个字段，见第 2 节） |
| 9 | `seerAppearanceVersion` | int | 2 | 赛尔（玩家形象）外观版本 |
| 10 | `seerFlying` | bool | true | 赛尔是否处于飞行状态 |
| 11 | `seerBodyColor` | str | "#FF8026" | 赛尔身体颜色（#RRGGBB） |
| 12 | `nonoBodyColor` | str | "#FF8CBF" | NONO（诺诺）身体颜色（#RRGGBB） |
| 13 | `seerSuitId` | int | 0 | 赛尔当前套装 ID（0=默认） |
| 14 | `baseHome` | object | 对象（4 个键） | 基地/家园数据（4 个字段，见附录 A） |
| 15 | `seerClothingItemIds` | array[int] | [100019, 100017, 100016, 100618] | 已拥有的赛尔服装道具 ID 列表 |
| 16 | `followingPetCatchTime` | str | "2026-11-01" | 跟随精灵的捕获日期 |
| 17 | `followingPetRandomValue` | int | 69662533 | 跟随精灵的随机种子/校验值（非经验） |
| 18 | `CanHitXuanWu` | bool | false | 是否可挑战玄武 |
| 19 | `BaiHuGuardiansCleared` | bool | false | 白虎守卫是否已全部清除 |
| 20 | `BaiHuDefeatedAvatars` | int | 0 | 已击败白虎分身数量 |
| 21 | `ZhuQueChallengeStage` | int | 0 | 朱雀挑战阶段 |
| 22 | `XierChallengeStage` | int | 0 | 希尔挑战阶段 |
| 23 | `PuLaTiaoZhan` | bool | false | 普拉挑战是否已开启/完成 |
| 24 | `puLaStep` | str | "" | 普拉挑战步骤标记 |
| 25 | `boolHit88` | bool | true | 编号 88 的触发/解锁标记 |
| 26 | `boolHit42` | bool | true | 编号 42 的触发/解锁标记 |
| 27 | `boolHit50` | bool | true | 编号 50 的触发/解锁标记 |
| 28 | `boolHit69` | bool | true | 编号 69 的触发/解锁标记 |
| 29 | `PuNiProcess` | int | 7 | 谱尼挑战/封印进度 |
| 30 | `CanHitQingLong` | bool | false | 是否可挑战青龙 |
| 31 | `currentTowerIndex` | int | 0 | 当前爬塔层索引 |
| 32 | `totalPowerIndex` | int | 0 | 总战力值/战力索引 |
| 33 | `maxTowerNum` | int | 0 | 已到达的最高塔层数 |
| 34 | `rogueTowerHighestFloor` | int | 0 | 肉鸽塔最高层数 |
| 35 | `rogueTowerCompletedRuns` | int | 0 | 肉鸽塔通关次数 |
| 36 | `PlRewardStatue` | int | 0 | 奖励雕像/奖励档位（推测） |
| 37 | `keyinqijiexp` | int | 0 | 与“七界/奇界”相关的经验值（推测） |
| 38 | `AhwdcList` | array[int] | [299, 169, 171, 174, 183, 177, 195, 192, 222, 224, 2394, 359, 4714, 421] | 活动/图鉴相关 ID 列表（具体含义待确认） |
| 39 | `NuoYiErProgress` | int | 0 | 诺伊尔挑战进度 |
| 40 | `darkAlliance` | object | 对象（2 个键） | 暗黑联盟数据（2 个字段，见附录 B） |
| 41 | `getItemList` | array[空] | `[]`（空） | 待领取道具列表（当前为空） |
| 42 | `petSaveDatas` | array[dict] | 对象数组（60 项） | 精灵存档数据（60 只，见第 3 节） |
| 43 | `petSaveDatasInBag` | array[dict] | 对象数组（5 项） | 背包内精灵数据（5 只，见第 3 节） |
| 44 | `petAbdanDatas` | array[dict] | 对象数组（10 项） | 备用/图鉴精灵数据（10 只，均 petId=46） |
| 45 | `firstMailPending` | bool | false | 是否有首封邮件待领取 |
| 46 | `exp` | int | 523079 | 玩家经验值 |
| 47 | `dicItem` | object | 对象（1 个键） | 道具字典（172 条，见第 4 节） |
| 48 | `abilityCores` | array[空] | `[]`（空） | 能力核心列表（当前为空） |
| 49 | `YuanShenZhuDatas` | array[空] | `[]`（空） | 元神珠数据列表（当前为空） |
| 50 | `jingYuanDatas` | array[dict] | 对象数组（1 项） | 精元（待孵化精灵）数据（1 条，见第 5 节） |
| 51 | `petBreedState` | object | 对象（2 个键） | 精灵繁殖状态（见第 5 节） |

## 2. `profile` 玩家档案（共 18 个字段）

| # | 字段 | 类型 | 当前值 | 含义 |
|---:|---|---|---|---|
| 1 | `mimiId` | str | "321386029" | 米米号（账号唯一 ID） |
| 2 | `registrationDate` | str | "2026-10-31" | 注册日期（YYYY-MM-DD） |
| 3 | `selectedTitleId` | int | 0 | 当前佩戴称号 ID（0=无） |
| 4 | `unlockedTitleIds` | array[int] | [3, 4, 55] | 已解锁称号 ID 列表 |
| 5 | `sptWins` | array[int] | [301, 302, 303, 304, 305, 306, 307, 308, 310, 311, 312, 314, 315, 316, 317, 318, 320] | SPT 挑战已通关关卡编号 |
| 6 | `battleCount` | int | 3256 | 累计战斗次数 |
| 7 | `winCount` | int | 2606 | 累计胜利次数 |
| 8 | `onlineBattleCount` | int | 0 | 联机对战次数 |
| 9 | `onlineWinCount` | int | 0 | 联机对战胜利次数 |
| 10 | `graduationCount` | int | 0 | 精灵毕业/满级培养次数 |
| 11 | `monKingWin` | int | 0 | 魔王类玩法胜利次数（推测） |
| 12 | `messWin` | int | 0 | 乱斗类玩法胜利次数（推测） |
| 13 | `maxStage` | int | 0 | 最高关卡进度 |
| 14 | `maxArenaWins` | int | 0 | 竞技场最高胜场/最高连胜 |
| 15 | `collectedSpeciesIds` | array[int] | [1, 3, 4, 6, 7, 9, 27, 35, 41, 46, 70, 77, 86, 88, 114, 122, 125, 164, 166, 198, 215, 216, 273, 274, 301, 303, 304, 306, 307, 309, 357, 796, 864, 875, 1044, 1203, 1337, 2394, 2781, 4714, 5605, 5606, 5607, 20070, 21666] | 已收集精灵种类 ID 列表 |
| 16 | `gaiaRuleMask` | int | 0 | 盖亚规则位掩码（按位标记解锁规则） |
| 17 | `erselaDayMask` | int | 0 | 厄尔塞拉日期位掩码（按位标记天数） |
| 18 | `maxTrialStage` | int | 0 | 最高试炼关卡 |

补充：`sptWins` 共 17 个关卡编号；`collectedSpeciesIds` 共 45 个精灵种类。


## 3. 精灵对象

### 3.1 出现位置与数量

| 数组 | 数量 | 说明 |
|---|---:|---|
| `petSaveDatas` | 60 | 精灵存档主体 |
| `petSaveDatasInBag` | 5 | 背包内精灵（`isInBag=true`） |
| `petAbdanDatas` | 10 | 备用/图鉴精灵（全部为 petId=46） |
| 合计 | 75 | 三个数组结构完全相同 |

### 3.2 精灵对象字段（共 39 个）

示例值取自 `petSaveDatas[0]`；取值范围为 75 只精灵的统计结果。

| # | 字段 | 类型 | 示例值 | 75 只取值范围 | 含义 |
|---:|---|---|---|---|---|
| 1 | `fixedBattleFormId` | int | 0 | 0 ~ 0（1 种） | 固定战斗形态 ID（0=普通形态） |
| 2 | `abilityTraitId` | int | 0 | 0 ~ 0（1 种） | 精灵特性 ID |
| 3 | `abilityTypeId` | int | 0 | 0 ~ 0（1 种） | 特性类型 ID |
| 4 | `atkValueItem` | int | 0 | 0 ~ 170（2 种） | 攻击数值道具提供的基础数值加成 |
| 5 | `spAtkValueItem` | int | 0 | 0 ~ 0（1 种） | 特攻数值道具加成 |
| 6 | `defValueItem` | int | 0 | 0 ~ 0（1 种） | 防御数值道具加成 |
| 7 | `spDefValueItem` | int | 0 | 0 ~ 0（1 种） | 特防数值道具加成 |
| 8 | `speedValueItem` | int | 0 | 0 ~ 140（2 种） | 速度数值道具加成 |
| 9 | `hpValueItem` | int | 0 | 0 ~ 1520（3 种） | 体力数值道具加成 |
| 10 | `SpecialBaseDataAtk` | int | 0 | 0 ~ 0（1 种） | 特殊形态基础攻击补正 |
| 11 | `SpecialBaseDataDef` | int | 0 | 0 ~ 0（1 种） | 特殊形态基础防御补正 |
| 12 | `SpecialBaseDataSpAtk` | int | 0 | 0 ~ 0（1 种） | 特殊形态基础特攻补正 |
| 13 | `SpecialBaseDataSpdef` | int | 0 | 0 ~ 0（1 种） | 特殊形态基础特防补正 |
| 14 | `YouNaSiSPecialSkill` | str | "" | `""`（空字符串） | 尤纳斯特殊技能标记（字符串） |
| 15 | `PulaBoundSkillIds` | array[空] | [] | 长度 0 ~ 0 | 普拉绑定的技能 ID 列表 |
| 16 | `SpecialBaseDataSpeed` | int | 0 | 0 ~ 0（1 种） | 特殊形态基础速度补正 |
| 17 | `SpecialBaseDataHp` | int | 0 | 0 ~ 0（1 种） | 特殊形态基础体力补正 |
| 18 | `petId` | str | "1" | 32 种取值 | 精灵种族 ID（字符串形式） |
| 19 | `petSpecialSkillUse` | str | "" | `""`（空字符串） | 精灵特殊技能使用状态 |
| 20 | `level` | int | 2 | 1 ~ 100（7 种） | 等级（1~100） |
| 21 | `evHP` | int | 0 | 0 ~ 255（3 种） | 体力学习力（努力值） |
| 22 | `evAttack` | int | 8 | 0 ~ 255（3 种） | 攻击学习力 |
| 23 | `evDefense` | int | 0 | 0 ~ 255（4 种） | 防御学习力 |
| 24 | `evSpAttack` | int | 0 | 0 ~ 24（2 种） | 特攻学习力 |
| 25 | `evSpDefense` | int | 0 | 0 ~ 255（4 种） | 特防学习力 |
| 26 | `evSpeed` | int | 0 | 0 ~ 255（3 种） | 速度学习力 |
| 27 | `randomValue` | int | 50935726 | 2900001 ~ 98235465（75 种） | 随机种子/个体校验值（每只唯一） |
| 28 | `nature` | int | 24 | 0 ~ 24（25 种） | 性格 ID（0~24） |
| 29 | `hadTime` | str | "2026-10-31" | 6 种取值：2026-10-31, 2026-11-01, 2026-11-02, 2026-11-03, 2026-11-04, 2026-11-05 | 获得日期（YYYY-MM-DD） |
| 30 | `XingBie` | int | 0 | 0 ~ 2（3 种） | 性别（0=无性别，1=雄，2=雌） |
| 31 | `isInBag` | bool | false | false / true | 是否在背包中 |
| 32 | `ivHP` | int | 29 | 0 ~ 31（28 种） | 体力个体值（IV，0~31） |
| 33 | `specialNature` | int | 999 | 24 ~ 999（3 种） | 特殊性格 ID（999=无） |
| 34 | `isHasSpecialNature` | bool | false | false | 是否拥有特殊性格 |
| 35 | `currentExp` | int | 8 | 0 ~ 587（3 种） | 当前经验值 |
| 36 | `isMys` | int | 0 | 0 ~ 0（1 种） | 神秘/特殊标记（具体含义待确认） |
| 37 | `moves` | array[空] | [] | 长度 0 ~ 0 | 已学技能 ID 列表 |
| 38 | `movesFight` | array[dict] | 1 条技能对象（示例：`撞击`） | 长度 1 ~ 4 | 战斗技能详细数据（对象数组，见 3.3） |
| 39 | `YuanShenZhu` | array[空] | [] | 长度 0 ~ 0 | 该精灵的元神珠数据列表 |

### 3.3 `movesFight` 技能对象字段（共 25 个）

示例值取自背包精灵的技能“守护方阵”。

| # | 字段 | 类型 | 示例值 | 含义 |
|---:|---|---|---|---|
| 1 | `ID` | int | 20158 | 技能 ID |
| 2 | `Name` | str | "守护方阵" | 技能名称 |
| 3 | `Category` | int | 4 | 技能分类（1=物理攻击，4=变化/辅助，其余为特殊攻击等） |
| 4 | `Type` | int | 8 | 属性/系别 ID（8=普通系） |
| 5 | `Power` | int | 0 | 技能威力 |
| 6 | `MaxPP` | int | 30 | 最大 PP（可使用次数） |
| 7 | `Accuracy` | int | 100 | 命中率（%） |
| 8 | `Priority` | int | 0 | 优先级/先手值 |
| 9 | `Url` | str | "pro_3" | 技能动画/资源标识 |
| 10 | `Cooldown` | int | 291 | 冷却时间（毫秒级） |
| 11 | `SideEffect` | str | "4 4" | 附加效果编号 |
| 12 | `SideEffectArg` | str | "1 100 1 3 100 1" | 附加效果参数 |
| 13 | `AtkType` | str | "3" | 攻击类型标记 |
| 14 | `MustHit` | str | "1" | 是否必中 |
| 15 | `Info` | str | "防御和特防提升了" | 技能效果描述文本 |
| 16 | `CritRate` | str | "" | 暴击率补正 |
| 17 | `CritAtkFirst` | int | 0 | 先手暴击标记 |
| 18 | `CritSelfHalfHp` | int | 0 | 自身血量过半时暴击标记 |
| 19 | `UseKeYin` | bool | false | 是否使用“克制”机制 |
| 20 | `UserStatChanges` | array[空] | [] | 对自身的能力变化列表 |
| 21 | `TargetStatChanges` | array[空] | [] | 对目标的能力变化列表 |
| 22 | `StatusEffects` | array[空] | [] | 附加状态效果列表 |
| 23 | `isPlayer` | bool | false | 是否玩家侧技能 |
| 24 | `isXianShou` | bool | false | 是否先手技能 |
| 25 | `isUseKeYin` | bool | false | 是否使用克制 |

### 3.4 全部精灵一览（75 只）

| # | 来源数组 | petId | 等级 | ivHP | nature | XingBie | isInBag | currentExp |
|---:|---|---:|---:|---:|---:|---:|---|---:|
| 1 | petSaveDatas | 1 | 2 | 29 | 24 | 0 | false | 8 |
| 2 | petSaveDatas | 6 | 100 | 25 | 16 | 1 | false | 0 |
| 3 | petSaveDatas | 9 | 100 | 31 | 13 | 1 | false | 0 |
| 4 | petSaveDatas | 3 | 100 | 17 | 15 | 0 | false | 0 |
| 5 | petSaveDatas | 4 | 13 | 25 | 17 | 1 | false | 0 |
| 6 | petSaveDatas | 4 | 12 | 24 | 18 | 1 | false | 0 |
| 7 | petSaveDatas | 864 | 1 | 11 | 20 | 1 | false | 0 |
| 8 | petSaveDatas | 114 | 1 | 17 | 1 | 1 | false | 0 |
| 9 | petSaveDatas | 46 | 1 | 27 | 15 | 2 | false | 0 |
| 10 | petSaveDatas | 2394 | 1 | 0 | 21 | 1 | false | 0 |
| 11 | petSaveDatas | 2394 | 1 | 15 | 11 | 1 | false | 0 |
| 12 | petSaveDatas | 2394 | 1 | 30 | 9 | 1 | false | 0 |
| 13 | petSaveDatas | 2394 | 1 | 4 | 1 | 1 | false | 0 |
| 14 | petSaveDatas | 2394 | 1 | 21 | 20 | 1 | false | 0 |
| 15 | petSaveDatas | 70 | 100 | 31 | 3 | 1 | false | 0 |
| 16 | petSaveDatas | 306 | 100 | 31 | 3 | 1 | false | 0 |
| 17 | petSaveDatas | 77 | 16 | 21 | 19 | 1 | false | 0 |
| 18 | petSaveDatas | 20070 | 1 | 31 | 3 | 1 | false | 0 |
| 19 | petSaveDatas | 166 | 60 | 28 | 24 | 0 | false | 587 |
| 20 | petSaveDatas | 357 | 1 | 30 | 5 | 0 | false | 0 |
| 21 | petSaveDatas | 796 | 1 | 30 | 18 | 1 | false | 0 |
| 22 | petSaveDatas | 1044 | 1 | 30 | 22 | 1 | false | 0 |
| 23 | petSaveDatas | 122 | 1 | 31 | 15 | 1 | false | 0 |
| 24 | petSaveDatas | 88 | 100 | 31 | 3 | 2 | false | 0 |
| 25 | petSaveDatas | 1203 | 1 | 31 | 3 | 1 | false | 0 |
| 26 | petSaveDatas | 303 | 100 | 31 | 5 | 0 | false | 0 |
| 27 | petSaveDatas | 41 | 1 | 31 | 21 | 0 | false | 0 |
| 28 | petSaveDatas | 875 | 1 | 31 | 15 | 1 | false | 0 |
| 29 | petSaveDatas | 1337 | 1 | 30 | 18 | 2 | false | 0 |
| 30 | petSaveDatas | 21666 | 1 | 31 | 3 | 1 | false | 0 |
| 31 | petSaveDatas | 4714 | 100 | 31 | 2 | 2 | false | 0 |
| 32 | petSaveDatas | 125 | 1 | 1 | 13 | 1 | false | 0 |
| 33 | petSaveDatas | 125 | 1 | 28 | 12 | 1 | false | 0 |
| 34 | petSaveDatas | 125 | 1 | 26 | 15 | 1 | false | 0 |
| 35 | petSaveDatas | 125 | 1 | 20 | 23 | 1 | false | 0 |
| 36 | petSaveDatas | 125 | 1 | 6 | 23 | 1 | false | 0 |
| 37 | petSaveDatas | 125 | 1 | 22 | 15 | 1 | false | 0 |
| 38 | petSaveDatas | 125 | 1 | 18 | 2 | 1 | false | 0 |
| 39 | petSaveDatas | 125 | 1 | 1 | 8 | 1 | false | 0 |
| 40 | petSaveDatas | 125 | 1 | 4 | 9 | 1 | false | 0 |
| 41 | petSaveDatas | 125 | 1 | 21 | 7 | 1 | false | 0 |
| 42 | petSaveDatas | 125 | 1 | 18 | 0 | 1 | false | 0 |
| 43 | petSaveDatas | 125 | 1 | 16 | 3 | 1 | false | 0 |
| 44 | petSaveDatas | 125 | 1 | 27 | 1 | 1 | false | 0 |
| 45 | petSaveDatas | 125 | 1 | 13 | 0 | 1 | false | 0 |
| 46 | petSaveDatas | 125 | 1 | 15 | 17 | 1 | false | 0 |
| 47 | petSaveDatas | 125 | 1 | 25 | 5 | 1 | false | 0 |
| 48 | petSaveDatas | 125 | 1 | 17 | 24 | 1 | false | 0 |
| 49 | petSaveDatas | 125 | 1 | 12 | 15 | 1 | false | 0 |
| 50 | petSaveDatas | 125 | 1 | 27 | 10 | 1 | false | 0 |
| 51 | petSaveDatas | 125 | 1 | 20 | 4 | 1 | false | 0 |
| 52 | petSaveDatas | 125 | 1 | 4 | 18 | 1 | false | 0 |
| 53 | petSaveDatas | 125 | 1 | 19 | 23 | 1 | false | 0 |
| 54 | petSaveDatas | 125 | 1 | 0 | 7 | 1 | false | 0 |
| 55 | petSaveDatas | 125 | 1 | 30 | 12 | 1 | false | 0 |
| 56 | petSaveDatas | 125 | 1 | 21 | 4 | 1 | false | 0 |
| 57 | petSaveDatas | 125 | 1 | 10 | 5 | 1 | false | 0 |
| 58 | petSaveDatas | 125 | 1 | 7 | 1 | 1 | false | 0 |
| 59 | petSaveDatas | 125 | 1 | 3 | 19 | 1 | false | 0 |
| 60 | petSaveDatas | 2781 | 1 | 30 | 14 | 1 | false | 0 |
| 61 | petSaveDatasInBag | 5607 | 100 | 31 | 3 | 1 | true | 0 |
| 62 | petSaveDatasInBag | 274 | 100 | 31 | 23 | 1 | true | 0 |
| 63 | petSaveDatasInBag | 309 | 100 | 31 | 10 | 1 | true | 0 |
| 64 | petSaveDatasInBag | 216 | 100 | 31 | 3 | 1 | true | 0 |
| 65 | petSaveDatasInBag | 2394 | 100 | 31 | 3 | 1 | true | 0 |
| 66 | petAbdanDatas | 46 | 1 | 25 | 0 | 2 | false | 0 |
| 67 | petAbdanDatas | 46 | 1 | 25 | 19 | 2 | false | 0 |
| 68 | petAbdanDatas | 46 | 1 | 17 | 6 | 2 | false | 0 |
| 69 | petAbdanDatas | 46 | 1 | 2 | 5 | 2 | false | 0 |
| 70 | petAbdanDatas | 46 | 1 | 15 | 9 | 2 | false | 0 |
| 71 | petAbdanDatas | 46 | 1 | 16 | 8 | 2 | false | 0 |
| 72 | petAbdanDatas | 46 | 1 | 14 | 12 | 2 | false | 0 |
| 73 | petAbdanDatas | 46 | 1 | 0 | 11 | 2 | false | 0 |
| 74 | petAbdanDatas | 46 | 1 | 17 | 7 | 2 | false | 0 |
| 75 | petAbdanDatas | 46 | 1 | 26 | 12 | 2 | false | 0 |

## 4. `dicItem` 道具字典

### 4.1 结构

| 字段 | 类型 | 说明 |
|---|---|---|
| `pairs` | object[] | 道具键值对数组，共 172 条 |
| `pairs[].key` | str | 道具 ID（字符串形式的数字） |
| `pairs[].value` | int | 持有数量 |

合计：172 种道具，总数量 18844。

### 4.2 全部 172 条道具

| # | 道具 ID (`key`) | 数量 (`value`) |
|---:|---:|---:|
| 1 | 100027 | 1 |
| 2 | 100028 | 1 |
| 3 | 300406 | 1 |
| 4 | 300024 | 121 |
| 5 | 300025 | 71 |
| 6 | 300026 | 116 |
| 7 | 300030 | 103 |
| 8 | 300031 | 105 |
| 9 | 300032 | 77 |
| 10 | 300033 | 105 |
| 11 | 300034 | 76 |
| 12 | 300037 | 106 |
| 13 | 300038 | 113 |
| 14 | 300039 | 111 |
| 15 | 300040 | 119 |
| 16 | 300041 | 116 |
| 17 | 300042 | 128 |
| 18 | 300043 | 116 |
| 19 | 300044 | 118 |
| 20 | 300053 | 112 |
| 21 | 300054 | 451 |
| 22 | 300075 | 97 |
| 23 | 300062 | 23 |
| 24 | 300073 | 1 |
| 25 | 300074 | 1 |
| 26 | 300063 | 1 |
| 27 | 400001 | 107 |
| 28 | 400002 | 100 |
| 29 | 400005 | 105 |
| 30 | 400009 | 100 |
| 31 | 400010 | 100 |
| 32 | 400011 | 100 |
| 33 | 400012 | 100 |
| 34 | 400014 | 100 |
| 35 | 400015 | 96 |
| 36 | 400016 | 100 |
| 37 | 400018 | 100 |
| 38 | 400019 | 100 |
| 39 | 400020 | 100 |
| 40 | 400021 | 100 |
| 41 | 400022 | 100 |
| 42 | 400023 | 100 |
| 43 | 400024 | 96 |
| 44 | 400025 | 100 |
| 45 | 400026 | 96 |
| 46 | 400028 | 118 |
| 47 | 400029 | 11 |
| 48 | 400030 | 105 |
| 49 | 400032 | 106 |
| 50 | 400033 | 102 |
| 51 | 300005 | 96 |
| 52 | 300004 | 1057 |
| 53 | 300003 | 2500 |
| 54 | 300001 | 1005 |
| 55 | 300002 | 102 |
| 56 | 300006 | 9 |
| 57 | 300012 | 1007 |
| 58 | 300013 | 1004 |
| 59 | 300014 | 1006 |
| 60 | 300015 | 1000 |
| 61 | 300016 | 970 |
| 62 | 300017 | 1003 |
| 63 | 300018 | 999 |
| 64 | 300019 | 998 |
| 65 | 100016 | 1 |
| 66 | 100017 | 1 |
| 67 | 100018 | 1 |
| 68 | 100019 | 1 |
| 69 | 400102 | 1 |
| 70 | 1100016 | 2 |
| 71 | 400101 | 416 |
| 72 | 400105 | 600 |
| 73 | 1100017 | 1 |
| 74 | 1100078 | 4 |
| 75 | 400059 | 17 |
| 76 | 300057 | 3 |
| 77 | 1100041 | 15 |
| 78 | 400103 | 12 |
| 79 | 1100026 | 26 |
| 80 | 1100018 | 4 |
| 81 | 1100007 | 3 |
| 82 | 1100028 | 4 |
| 83 | 20001 | 1 |
| 84 | 400114 | 1 |
| 85 | 400125 | 1 |
| 86 | 400138 | 1 |
| 87 | 400137 | 1 |
| 88 | 400151 | 1 |
| 89 | 400187 | 1 |
| 90 | 400153 | 1 |
| 91 | 400156 | 1 |
| 92 | 400161 | 1 |
| 93 | 400206 | 1 |
| 94 | 400192 | 1 |
| 95 | 400119 | 1 |
| 96 | 400133 | 1 |
| 97 | 400228 | 1 |
| 98 | 400109 | 1 |
| 99 | 400110 | 1 |
| 100 | 400111 | 1 |
| 101 | 400113 | 1 |
| 102 | 400112 | 1 |
| 103 | 400115 | 1 |
| 104 | 400116 | 1 |
| 105 | 400120 | 1 |
| 106 | 400121 | 1 |
| 107 | 20096 | 1 |
| 108 | 20006 | 1 |
| 109 | 100602 | 1 |
| 110 | 300060 | 5 |
| 111 | 300058 | 4 |
| 112 | 1100008 | 6 |
| 113 | 100125 | 1 |
| 114 | 300064 | 2 |
| 115 | 300056 | 4 |
| 116 | 1100027 | 8 |
| 117 | 300055 | 3 |
| 118 | 20422 | 2 |
| 119 | 20048 | 7 |
| 120 | 400501 | 4 |
| 121 | 1100030 | 1 |
| 122 | 1100036 | 3 |
| 123 | 100141 | 1 |
| 124 | 20182 | 1 |
| 125 | 400058 | 68 |
| 126 | 20041 | 7 |
| 127 | 20004 | 4 |
| 128 | 400158 | 1 |
| 129 | 400007 | 8 |
| 130 | 400004 | 6 |
| 131 | 1100058 | 1 |
| 132 | 300059 | 3 |
| 133 | 1100011 | 2 |
| 134 | 400035 | 4 |
| 135 | 400006 | 1 |
| 136 | 400863 | 1 |
| 137 | 1100042 | 5 |
| 138 | 400159 | 1 |
| 139 | 1100076 | 4 |
| 140 | 400008 | 2 |
| 141 | 1100031 | 2 |
| 142 | 70010 | 1 |
| 143 | 300061 | 6 |
| 144 | 1100043 | 2 |
| 145 | 300153 | 2 |
| 146 | 400003 | 1 |
| 147 | 1100077 | 1 |
| 148 | 100618 | 1 |
| 149 | 1100052 | 1 |
| 150 | 400651 | 1 |
| 151 | 400652 | 1 |
| 152 | 400653 | 1 |
| 153 | 400654 | 1 |
| 154 | 400655 | 1 |
| 155 | 400656 | 1 |
| 156 | 400657 | 1 |
| 157 | 1100044 | 1 |
| 158 | 100724 | 1 |
| 159 | 1100057 | 1 |
| 160 | 1100046 | 1 |
| 161 | 1100021 | 1 |
| 162 | 400031 | 1 |
| 163 | 1100032 | 1 |
| 164 | 400132 | 1 |
| 165 | 400235 | 1 |
| 166 | 400139 | 1 |
| 167 | 400127 | 1 |
| 168 | 20339 | 1 |
| 169 | 400136 | 1 |
| 170 | 13371337 | 1 |
| 171 | 1100051 | 1 |
| 172 | 300021 | 8 |

## 5. 精元与繁殖

### 5.1 `jingYuanDatas` 精元（待孵化精灵）

| 字段 | 类型 | 当前值 | 含义 |
|---|---|---|---|
| `index` | int | 4542753 | 精元实例唯一索引 |
| `itemId` | int | 400105 | 精元道具 ID |
| `isMys` | bool | true | 神秘/特殊标记（待确认） |
| `petId` | int | 0 | 孵化目标精灵 ID（0=尚未确定） |

当前共 1 条精元记录。

### 5.2 `petBreedState` 精灵繁殖状态

| 字段 | 类型 | 当前值 | 含义 |
|---|---|---|---|
| `eggs` | array | `[]` | 正在孵化的精灵蛋列表（当前为空） |
| `nextBreedAtUnix` | int | 0 | 下次可繁殖时间（Unix 时间戳，0=无冷却） |

## 附录 A：`baseHome` 基地/家园（4 个字段）

| 字段 | 类型 | 当前值/规模 | 含义 |
|---|---|---|---|
| `version` | int | 1 | 家园数据版本号 |
| `roomId` | int | 500001 | 当前房间 ID |
| `owned` | object[] | 20 条 | 已拥有家具列表 |
| `owned[].id` | int | 500001 | 家具 ID |
| `owned[].count` | int | 1 | 拥有数量 |
| `placements` | object[] | 17 条 | 已摆放家具列表 |
| `placements[].id` | int | 500501 | 家具 ID |
| `placements[].direction` | int | 0 | 摆放朝向 |
| `placements[].x` | float | 269.4615173339844 | 摆放 X 坐标 |
| `placements[].y` | float | 323.8101806640625 | 摆放 Y 坐标 |

## 附录 B：`darkAlliance` 暗黑联盟（2 个字段）

| 字段 | 类型 | 当前值 | 含义 |
|---|---|---|---|
| `phase` | int | 0 | 当前阶段 |
| `guardWins` | int | 0 | 守卫战胜利次数 |

## 附录 C：其余空列表字段

| 字段 | 类型 | 当前值 | 含义 |
|---|---|---|---|
| `getItemList` | array | `[]` | 待领取道具列表（空） |
| `abilityCores` | array | `[]` | 能力核心列表（空） |
| `YuanShenZhuDatas` | array | `[]` | 元神珠数据列表（空） |
| `petBreedState.eggs` | array | `[]` | 精灵蛋列表（空） |

## 附录 D：字段含义的推断说明

1. 该存档属于《赛尔号》体系：赛尔豆（`SerErDou`）、米米号（`mimiId`）、赛尔形象（`seer*`）、NONO（`nonoBodyColor`）、SPT、精灵（`petSaveDatas`）、精元（`jingYuanDatas`）、元神珠（`YuanShenZhu`）、白虎/玄武/青龙/朱雀、谱尼、诺伊尔、尤纳斯、盖亚、厄尔塞拉等字段均对应游戏内容。
2. `nature`（0~24）、`XingBie`（0/1/2）、`specialNature`（999=无）等为枚举值，具体枚举名称需游戏配置表才能确定。
3. 道具 ID、家具 ID、精灵 ID 均为游戏内部 ID，需要对应配置表才能翻译成中文名称。
4. 标注“推测/待确认”的字段：`PlRewardStatue`、`keyinqijiexp`、`isMys`、`AhwdcList`、`monKingWin`、`messWin`、`petAbdanDatas` 的具体业务含义。