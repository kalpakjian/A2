"""
批次去背工具：把指定的 PNG/JPG 圖檔轉成真正的透明 RGBA PNG。

使用方式（在專案根目錄 c:\\Users\\princ\\A2 下執行）：

  # 1) 處理單一檔案
  python remove_bg.py Assets/Chief.png

  # 2) 處理多個檔案
  python remove_bg.py Assets/Chief.png Assets/Hero.png

  # 3) 處理整個資料夾（自動遞迴搜尋 .png/.jpg/.jpeg/.webp）
  python remove_bg.py Assets/Portraits

  # 4) 用 glob
  python remove_bg.py "Assets/**/*.png"

  # 5) 跳過已經是 RGBA 的檔案（避免重複處理）
  python remove_bg.py Assets --skip-rgba

  # 6) 不備份原檔（預設會備份成 *.original.png）
  python remove_bg.py Assets --no-backup

  # 7) 換模型（預設 isnet-general-use；人像可用 u2net_human_seg；
  #    動漫角色可試 isnet-anime；更精細可用 birefnet-general，但較慢）
  python remove_bg.py Assets --model u2net_human_seg

  # 8) 不傳任何參數 = 處理 Assets/Chief.png 與 Assets/Hero.png（向後相容）
  python remove_bg.py
"""

from __future__ import annotations

import argparse
import glob
import os
import shutil
import sys
from pathlib import Path

# Windows cmd 預設 GBK，無法輸出非 ASCII 字元；強制改用 UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

SUPPORTED_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
DEFAULT_TARGETS = ["Assets/Chief.png", "Assets/Hero.png"]
BACKUP_SUFFIX = ".original"


# ---------- 輔助函式 ----------

def png_color_type(path: str) -> int | None:
    """讀 PNG IHDR 取得 color type；非 PNG 回傳 None。
    色彩類型代碼：0=Grayscale, 2=RGB, 3=Palette, 4=Grayscale+Alpha, 6=RGBA。
    """
    try:
        with open(path, "rb") as f:
            head = f.read(26)
        if head[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        return head[25]
    except Exception:
        return None


def is_already_rgba(path: str) -> bool:
    return png_color_type(path) == 6


def is_backup_file(path: str) -> bool:
    """判斷是否為腳本產生的 *.original.png 備份檔。"""
    stem = Path(path).stem
    return stem.endswith(BACKUP_SUFFIX)


def backup(path: str) -> str:
    """把 foo.png 複製成 foo.original.png（已存在則略過）。"""
    p = Path(path)
    bak = p.with_name(p.stem + BACKUP_SUFFIX + p.suffix)
    if not bak.exists():
        shutil.copy2(path, bak)
        print(f"  [backup] -> {bak}")
    else:
        print(f"  [backup] 已存在，略過: {bak}")
    return str(bak)


def expand_targets(inputs: list[str]) -> list[str]:
    """把 [檔案 / 資料夾 / glob] 全部展開成圖片檔案清單，並去重。"""
    files: list[str] = []
    for raw in inputs:
        # glob（含 ** 遞迴）
        if any(ch in raw for ch in "*?["):
            matched = glob.glob(raw, recursive=True)
            files.extend(matched)
            continue

        p = Path(raw)
        if p.is_dir():
            for ext in SUPPORTED_EXT:
                files.extend(str(x) for x in p.rglob(f"*{ext}"))
        elif p.is_file():
            files.append(str(p))
        else:
            print(f"  [warn] 找不到: {raw}")

    # 過濾副檔名 + 去除備份檔 + 去重 + 排序
    out: list[str] = []
    seen: set[str] = set()
    for f in files:
        ext = Path(f).suffix.lower()
        if ext not in SUPPORTED_EXT:
            continue
        if is_backup_file(f):
            continue
        norm = str(Path(f).resolve())
        if norm in seen:
            continue
        seen.add(norm)
        out.append(f)
    out.sort()
    return out


# ---------- 去背實作 ----------

_session_cache: dict[str, object] = {}


def remove_bg_rembg(src: str, dst: str, model: str) -> bool:
    """用 rembg 去背，成功回傳 True；輸出永遠是 PNG (RGBA)。"""
    try:
        from rembg import remove, new_session  # type: ignore
    except Exception as e:
        print(f"  [rembg] 匯入失敗: {e}")
        return False

    try:
        if model not in _session_cache:
            _session_cache[model] = new_session(model)
        session = _session_cache[model]

        with open(src, "rb") as f:
            data = f.read()
        out = remove(data, session=session, post_process_mask=True)

        # 確保副檔名是 .png（JPG 沒有 alpha）
        dst_png = str(Path(dst).with_suffix(".png"))
        with open(dst_png, "wb") as f:
            f.write(out)

        # 若原本是 .jpg/.webp，順手把舊檔刪掉，避免兩個檔案並存
        if dst != dst_png and os.path.exists(dst):
            os.remove(dst)
        return True
    except Exception as e:
        print(f"  [rembg] 執行失敗: {e}")
        return False


def remove_bg_pillow_whitekey(src: str, dst: str, threshold: int = 240) -> bool:
    """退路方案：把接近白色的像素設為透明（邊緣較硬）。"""
    try:
        from PIL import Image  # type: ignore
    except Exception as e:
        print(f"  [pillow] 匯入失敗: {e}")
        return False

    im = Image.open(src).convert("RGBA")
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, _ = px[x, y]
            if r >= threshold and g >= threshold and b >= threshold:
                px[x, y] = (r, g, b, 0)
    dst_png = str(Path(dst).with_suffix(".png"))
    im.save(dst_png, "PNG")
    if dst != dst_png and os.path.exists(dst):
        os.remove(dst)
    return True


# ---------- 主流程 ----------

def process_one(path: str, *, model: str, do_backup: bool, skip_rgba: bool) -> str:
    """處理單一檔案，回傳狀態字串：'ok' / 'skip' / 'fail'。"""
    print(f"\n=== 處理 {path} ===")
    if not os.path.exists(path):
        print("  找不到檔案，略過")
        return "fail"

    ext = Path(path).suffix.lower()
    ct_before = png_color_type(path)
    if ext == ".png":
        label_before = {0: "Grayscale", 2: "RGB", 3: "Palette",
                        4: "GA", 6: "RGBA"}.get(ct_before or -1, "?")
        print(f"  原始: PNG color_type={ct_before} ({label_before})")
    else:
        print(f"  原始: {ext.upper()[1:]} 檔（無 alpha）")

    if skip_rgba and ct_before == 6:
        print("  [SKIP] 已是 RGBA，依 --skip-rgba 設定略過")
        return "skip"

    if do_backup:
        backup(path)

    ok = remove_bg_rembg(path, path, model=model)
    used = f"rembg ({model})"
    if not ok:
        print("  改用 Pillow 白底→透明 fallback")
        ok = remove_bg_pillow_whitekey(path, path, threshold=240)
        used = "pillow whitekey"

    if not ok:
        print("  [FAIL] 兩種方法都不可用，請先 pip install pillow rembg onnxruntime")
        return "fail"

    final_path = str(Path(path).with_suffix(".png"))
    ct_after = png_color_type(final_path)
    label_after = {0: "Grayscale", 2: "RGB", 3: "Palette",
                   4: "GA", 6: "RGBA"}.get(ct_after or -1, "?")
    flag = "[OK]" if ct_after == 6 else "[WARN]"
    print(f"  {flag} 完成：方法={used}, 新 color_type={ct_after} ({label_after})")
    return "ok" if ct_after == 6 else "fail"


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="批次把圖片去背為透明 RGBA PNG（rembg AI；fallback: Pillow 白底→透明）。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("paths", nargs="*",
                    help="要處理的檔案 / 資料夾 / glob；不傳則處理 Assets/Chief.png 與 Assets/Hero.png")
    ap.add_argument("--model", default="isnet-general-use",
                    help="rembg 模型名稱（預設 isnet-general-use）。"
                         "可選：u2net, u2netp, u2net_human_seg, "
                         "isnet-general-use, isnet-anime, birefnet-general, silueta")
    ap.add_argument("--no-backup", action="store_true",
                    help="不備份原檔（預設會備份成 *.original.png）")
    ap.add_argument("--skip-rgba", action="store_true",
                    help="跳過已經是 RGBA 的 PNG（避免重複處理）")
    return ap.parse_args()


def main() -> int:
    # 切到此腳本所在目錄，確保相對路徑（如 Assets/...）正確
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    args = parse_args()

    inputs = args.paths if args.paths else DEFAULT_TARGETS
    targets = expand_targets(inputs)

    if not targets:
        print("找不到任何可處理的圖片檔。")
        return 1

    print(f"共找到 {len(targets)} 個檔案，使用模型: {args.model}")
    if args.no_backup:
        print("(不備份原檔)")
    if args.skip_rgba:
        print("(略過已是 RGBA 的檔案)")

    counts = {"ok": 0, "skip": 0, "fail": 0}
    for t in targets:
        status = process_one(
            t,
            model=args.model,
            do_backup=not args.no_backup,
            skip_rgba=args.skip_rgba,
        )
        counts[status] += 1

    print("\n--- 結果統計 ---")
    print(f"  成功 : {counts['ok']}")
    print(f"  略過 : {counts['skip']}")
    print(f"  失敗 : {counts['fail']}")
    print("\n--- 後續 ---")
    print("1. 回到 Unity，等它自動 reimport（或在 Project 視窗右鍵 Reimport）。")
    print("2. 必要時把 sprite 的 Mesh Type 設為 Full Rect，避免半透明邊緣被裁掉。")
    print("3. 想還原：把對應的 *.original.png 改名回去即可。")
    return 0 if counts["fail"] == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
