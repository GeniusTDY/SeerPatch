## v1.1.13：回退 Unity 启动页移除（修复启动闪退），保留加载页白边修复

**重要**：v1.1.12 关闭 Unity 启动页后，在 Redmi / Android 14 上启动即闪退（libunity 原生断言）。本版已回退该改动，恢复原始 `globalgamemanagers`，启动页正常显示。

1. **已回退**：Unity 启动页（`globalgamemanagers` 的 splash 开关）恢复原状。
2. **保留**：加载页（星空/星环背景）四周白边已移除，只重编码受影响的贴图块。
3. 其余与 v1.1.11 一致：详情立绘下移、对战卡片立绘放大、头像垂直居中、仓库格子铺满等。

### 如果你是用补丁覆盖安装（重要）
v1.1.13 补丁现已包含**原版 `globalgamemanagers`**。之前打过 v1.1.12 补丁的 APK，必须用新补丁里的这个文件覆盖，否则关闭启动页的改动会残留、继续闪退。
也可以只下载 `Seer_v1.1.13_fix_globalgamemanagers.zip`（280 KB），把里面的 `assets/bin/Data/globalgamemanagers` 覆盖进 APK 后重签即可修复。

### 资产
- `Seer_v1.1.13.apk.000` / `Seer_v1.1.13.apk.001`：完整签名 APK 分卷
- `Seer_v1.1.13_patch.zip`：**累积补丁**（5 个 bundle + 白边修复分片 + 原版 `globalgamemanagers` + keystore + 使用说明，46,505,338 B，SHA-256 `a579e6c78b801ac3fda69596a89ba96e568f3ea825f51dd02c6d32f943aa6984`）
- `Seer_v1.1.13_fix_globalgamemanagers.zip`：单文件修复包（280,191 B，SHA-256 `2205cebe3ea5c73c8383aed1aaaae6f6de04dfe749e60444020af70ae059e889`）

### 合并分卷
```
cat Seer_v1.1.13.apk.000 Seer_v1.1.13.apk.001 > Seer_v1.1.13.apk
```

APK SHA-256：`d1d26791ddfb588084d3cfe2b723f88535c5464257927c315e4245cde65a27b5`

- `Seer_v1.1.13.apk.000`：2,097,152,000 B
- `Seer_v1.1.13.apk.001`：1,995,540,145 B
- 合并后 `Seer_v1.1.13.apk`：4,092,692,145 B
