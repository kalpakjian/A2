# A2

這是一個 Unity 專案，包含角色立繪與場景素材。專案內建 `remove_bg.py` 批次去背工具，可將 PNG/JPG 圖檔一鍵轉為透明背景（RGBA）。

## 目錄結構

- `Assets/` — Unity 場景與圖片素材
  - `A2.unity` — 主場景
  - `Chief.png`、`Hero.png`、`HeroPortrait.png` — 角色圖（已去背）
  - `BG1.png` — 背景圖
- `remove_bg.py` — 去背腳本

## remove_bg.py 用法

### 環境需求

```bash
pip install pillow rembg onnxruntime
```

### 指令範例

```bash
# 處理單一檔案
python remove_bg.py Assets/HeroPortrait.png

# 處理多個檔案
python remove_bg.py Assets/Chief.png Assets/Hero.png

# 處理整個資料夾（自動遞迴搜尋 .png/.jpg/.jpeg/.webp）
python remove_bg.py Assets/

# 用 glob 批次處理
python remove_bg.py "Assets/**/*.png"

# 跳過已經是 RGBA 的檔案
python remove_bg.py Assets --skip-rgba

# 不備份原檔（預設會備份成 *.original.png）
python remove_bg.py Assets --no-backup

# 更換模型（人像可改用 u2net_human_seg）
python remove_bg.py Assets --model u2net_human_seg
```

### 可用模型

| 模型 | 用途 |
|------|------|
| `isnet-general-use` | 預設，通用去背 |
| `u2net_human_seg` | 人像分割 |
| `isnet-anime` | 動漫角色 |
| `birefnet-general` | 更精細（較慢） |

### 還原原檔

每張處理過的圖都會自動備份成 `*.original.png`，想還原時把備份檔改名回去即可。

```bash
# 範例：還原 HeroPortrait.png
mv Assets/HeroPortrait.original.png Assets/HeroPortrait.png
```

---

開發環境：Unity + Python
