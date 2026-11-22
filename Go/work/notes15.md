# 赛尔号 1.0.1 修正版 v1.1.15

## 说明

v1.1.15 撤回「关闭 Unity 启动页」的改动（实测该开关对游戏无效，启动页保持原样，不再处理）。

内容与 v1.1.14 一致：

- 修复 v1.1.12 / v1.1.13 启动即闪退（贴图像素偏移写错，覆盖了 `m_StreamData`）；
- 加载页（星空 / 星环背景）四边白边移除；
- v1.1.11 的全部界面改动保留（精灵背包立绘、对战技能面板立绘等）；
- 补丁包只包含有改动的文件：5 个 bundle + 2 个 `.split`，不含 `globalgamemanagers`。

## 文件

| 文件 | 大小 (B) | SHA-256 |
| --- | --- | --- |
| Seer_v1.1.15.apk.000 | 2097152000 | `6351c1bfaf43891f21efc2a206a9236acbbb400bc016b28aa71b10d3604ca0c7` |
| Seer_v1.1.15.apk.001 | 1995540145 | `16bb8328f224d2d2161382b92d8c8ebc05ad224bb0a36fdaff82a289e170150b` |
| Seer_v1.1.15_patch.zip | 46218800 | `2eceb9c0c6b0d459d2f0197617cb026e1c1e4476743594d2a73207d6015f4bba` |

## 安装

```
cat Seer_v1.1.15.apk.000 Seer_v1.1.15.apk.001 > Seer_v1.1.15.apk
```

卸载旧版本后安装（签名与官方不同，不能覆盖安装）。

已装 v1.1.11 及以后版本的用户，也可以只装补丁 `Seer_v1.1.15_patch.zip`：
解压后把 `assets` 按原路径覆盖进 APK（ZArchiver / MT 管理器），再用
`seer-patch.keystore`（别名 `seerpatch`，密码 `SeerPatch2026!`）签名后安装。
