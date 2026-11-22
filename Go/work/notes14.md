# 赛尔号 1.0.1 修正版 v1.1.14

## 本次重点：修复启动闪退

v1.1.12 / v1.1.13 在 Redmi / Android 14 上启动即闪退（libunity SIGTRAP，栈中涉及 `m_StreamData`）。

**根因已定位**：修改加载页贴图（975×573 ASTC 6×6）时，像素数据偏移多算了 16 字节，
把对象末尾的 `m_StreamData` 结构（偏移 8B + 大小 4B + 路径字符串长度 4B）覆盖成了贴图像素。
Unity 反序列化该 Texture2D 时读到随机的路径长度，直接触发原生断言退出。

**修复**：按正确偏移 `对象起点 + 104` 写入像素数据，尾部 `m_StreamData` 原样保留，
已用 UnityPy 重新解析校验通过（`m_StreamData.path` 为空、无异常）。

## 内容

- 加载页（星空 / 星环背景）四边白边已移除
- Unity 启动页本次**未改动**（保持原始 `globalgamemanagers`）
- 其余界面改动与 v1.1.11 一致（精灵背包立绘、对战技能面板立绘等）

## 文件

| 文件 | 大小 (B) | SHA-256 |
| --- | --- | --- |
| Seer_v1.1.14.apk.000 | 2097152000 | `6351c1bfaf43891f21efc2a206a9236acbbb400bc016b28aa71b10d3604ca0c7` |
| Seer_v1.1.14.apk.001 | 1995540145 | `60169c059f9b0cd2e458d70a38cf4a21220bc530da483692a60cd12b4dc6d18c` |
| Seer_v1.1.14_patch.zip | 46495649 | `5d4c7f7225539aae99b76ac4dc9840f47108920170bc3dc11fc83204209bc9bb` |

合并后 APK 大小 4092692145 B，SHA-256 `b403fd5354edd2ef3e7fef532b468199976a88f9131802f55f4ac4bd078b590b`。

## 安装

1. 下载 `Seer_v1.1.14.apk.000`、`Seer_v1.1.14.apk.001`，放在同一目录合并：

   ```
   cat Seer_v1.1.14.apk.000 Seer_v1.1.14.apk.001 > Seer_v1.1.14.apk
   ```

2. 卸载旧版本（签名与官方不同，不能覆盖安装），再安装合并后的 APK。

3. 已装 v1.1.11 的用户也可以只装补丁 `Seer_v1.1.14_patch.zip`：
   解压后把 `assets` 覆盖进 APK（ZArchiver / MT 管理器），再用
   `seer-patch.keystore`（别名 `seerpatch`，密码 `SeerPatch2026!`）签名，
   卸载旧版后安装。补丁包含 5 个 bundle + `globalgamemanagers` + 修复后的
   `sharedassets0.assets.split48/49`。

## 校验

```
sha256sum Seer_v1.1.14.apk.000 Seer_v1.1.14.apk.001
```
