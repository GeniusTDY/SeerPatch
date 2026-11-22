## v1.1.12：移除 Unity 启动页 + 移除加载页白边

1. **Unity 启动页**：修改 `assets/bin/Data/globalgamemanagers` 里 PlayerSettings 的 `m_ShowUnitySplashScreen` / `m_ShowUnitySplashLogo`，启动时不再显示黑底 “MADE WITH Unity” 标志，直接进入游戏加载页。启动总时长基本不变（只是少了标志展示）。
2. **加载页白边**：加载背景（星空/星环贴图 975×573，ASTC 6×6）四周的白色边框像素替换为相邻的星空/黑色内容，只重编码受影响的贴图块，其余像素保持原样。白边消失，画面其余部分不变。
3. 其余内容与 v1.1.11 完全一致。

### 资产
- `Seer_v1.1.12.apk.000` / `Seer_v1.1.12.apk.001`：完整签名 APK 分卷
- `Seer_v1.1.12_patch.zip`：**累积补丁**（已整合 v1.1.11 的 5 个 bundle，加 `globalgamemanagers` + `sharedassets0.assets.split48/49` + keystore + 使用说明，46,505,614 B，SHA-256 `73fcddeccadc5036d05211a573eb2911bc57749100cef5948e1f43d8b15d360c`）。可直接覆盖到原版 APK，无需再单独打 v1.1.11 补丁。

### 合并分卷
```
cat Seer_v1.1.12.apk.000 Seer_v1.1.12.apk.001 > Seer_v1.1.12.apk
```

APK SHA-256：`f7d7806b1f82facbae004198789afa658452fd528d5ca4c27112a1c01e4fc1ba`

- `Seer_v1.1.12.apk.000`：2,097,152,000 B
- `Seer_v1.1.12.apk.001`：1,995,540,145 B
- 合并后 `Seer_v1.1.12.apk`：4,092,692,145 B
