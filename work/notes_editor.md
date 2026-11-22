# 赛尔号 1.0.1 可编辑存档版 v1.2.0

## 新增功能

本地存档改为**明文 JSON**，可以用文本编辑器直接修改：

```
/storage/emulated/0/Android/data/com.seer.game/files/PlayerData.json
```

同一目录下的 `GameSettings.json`、`FortuneWheel.json`、`BattleJieTi.json` 等也会一并变成明文。

## 实现方式

只改了 `lib/arm64-v8a/libil2cpp.so` 里 `GameDataManager` 的两个私有方法：

- `EncryptString`：改为原样返回，写盘不再加密；
- `DecryptString`：内容以 `{` 开头的直接按明文使用，否则走原来的解密流程。

所以：

- 旧版加密存档**仍能正常读取**，首次启动后游戏写盘时自动变成明文；
- 之后手动修改的明文内容，游戏下次启动直接生效；
- 其余游戏逻辑、界面改动与 v1.1.15 完全一致。

## 使用方法

1. 完全退出游戏（最近任务里划掉，确认无后台进程）；
2. 用 ZArchiver / MT 管理器打开上面的目录，先备份 `PlayerData.json`；
3. 用文本编辑器修改数值并保存（注意 JSON 语法）；
4. 启动游戏读取修改后的存档。

注意事项：

- 必须游戏完全退出后再编辑，否则会被运行中的游戏覆盖；
- 改坏 JSON 可能导致存档异常或重建，务必先备份；
- 建议先只改一个字段（如 `SerErDou`）验证流程；
- 字段说明见《PlayerData.字段说明_详细版.md》。

## 文件

| 文件 | 大小 (B) | SHA-256 |
| --- | --- | --- |
| Seer_v1.2.0.apk.000 | 2097152000 | `cb79d88622e62642b9f92a9fb127d43b6594ad705a6ecc0fcbb8a245078ac2c7` |
| Seer_v1.2.0.apk.001 | 1995556529 | `889d56e63c36eed3acfc1a3f4a129a577f591ce2b346514a52478efc59429ee3` |
| Seer_v1.2.0_patch.zip | 16052576 | `600409df90c58b06afc4075de3b61334075ba5ec718a7a99f1f66a937cb1c5e4` |

合并后 APK 大小 4,092,708,529 B，SHA-256：
`0da22c4afc293c62fed68117f94bd51ddc884bb951063383b6a7e00feaeb55bd`

## 安装

```
cat Seer_v1.2.0.apk.000 Seer_v1.2.0.apk.001 > Seer_v1.2.0.apk
```

卸载旧版本后安装（签名与官方不同）。

已装 v1.1.x 的用户也可以只装补丁 `Seer_v1.2.0_patch.zip`：
解压后把 `lib` 按原路径覆盖进 APK，再用 `seer-patch.keystore`
（别名 `seerpatch`，密码 `SeerPatch2026!`）签名后安装。

---

## 附加：独立存档编辑器 APK（不改游戏本体）

`Seer_PlayerDataEditor_v1.0.apk`（16,787 B，SHA-256 `2cb026176a03319c73e99ff2d0032c0eebda89ed37e0866cfd267594131ed47e`）

- 独立工具，安装即用，不需要修改或重装游戏；
- 自动识别加密/明文存档，读取时解密，保存时按原格式加密写回；
- 同时兼容原版游戏和 v1.2.0；
- 功能：读取存档 / 保存(加密) / 备份明文 / 格式化 / 全文件访问设置；
- 用法：点『读取存档』→ 选中 `Android/data/com.seer.game/files/PlayerData.json`
  → 编辑 JSON →『保存(加密)』→ 完全退出并重启游戏；
- Android 11+ 若文件选择器进不去 `Android/data`：用 ZArchiver 把文件复制到 Download，
  用本工具修改后『备份明文』导出，再覆盖回原目录（文件名保持不变）。
