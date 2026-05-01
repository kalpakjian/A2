"""
調整圖片尺寸工具：依百分比或指定寬高縮放圖片。

使用方式：

  # 放大 50%（變成 150%）
  python resize_image.py Assets/HeroPortrait.png --scale 1.5

  # 縮小 50%（變成 50%）
  python resize_image.py Assets/HeroPortrait.png --scale 0.5

  # 指定寬度（高度等比例縮放）
  python resize_image.py Assets/HeroPortrait.png --width 1024

  # 指定高度（寬度等比例縮放）
  python resize_image.py Assets/HeroPortrait.png --height 1024

  # 指定寬與高（可能變形）
  python resize_image.py Assets/HeroPortrait.png --width 512 --height 512

  # 不備份原檔
  python resize_image.py Assets/HeroPortrait.png --scale 1.5 --no-backup
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def backup(path: str) -> str:
    p = Path(path)
    bak = p.with_name(p.stem + ".original" + p.suffix)
    if not bak.exists():
        shutil.copy2(path, bak)
        print(f"  [backup] -> {bak}")
    else:
        print(f"  [backup] 已存在，略過: {bak}")
    return str(bak)


def resize_image(src: str, dst: str, *, scale: float | None = None, width: int | None = None, height: int | None = None) -> bool:
    try:
        from PIL import Image
    except Exception as e:
        print(f"  [pillow] 匯入失敗: {e}")
        return False

    im = Image.open(src)
    orig_w, orig_h = im.size
    new_w, new_h = orig_w, orig_h

    if scale is not None:
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)
    elif width is not None and height is not None:
        new_w, new_h = width, height
    elif width is not None:
        new_w = width
        new_h = int(orig_h * (width / orig_w))
    elif height is not None:
        new_h = height
        new_w = int(orig_w * (height / orig_h))
    else:
        print("  [error] 請指定 --scale、--width 或 --height")
        return False

    print(f"  原始尺寸: {orig_w}x{orig_h}")
    print(f"  新尺寸:   {new_w}x{new_h}")

    im_resized = im.resize((new_w, new_h), Image.LANCZOS)
    im_resized.save(dst)
    return True


def main() -> int:
    ap = argparse.ArgumentParser(
        description="調整圖片尺寸（百分比或指定寬高）。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("image", help="要處理的圖片路徑")
    ap.add_argument("--scale", type=float, help="縮放倍率，例如 1.5 表示放大 50%")
    ap.add_argument("--width", type=int, help="指定新寬度（等比例縮放）")
    ap.add_argument("--height", type=int, help="指定新高度（等比例縮放）")
    ap.add_argument("--no-backup", action="store_true", help="不備份原檔")
    args = ap.parse_args()

    if not os.path.exists(args.image):
        print(f"找不到檔案: {args.image}")
        return 1

    if not args.no_backup:
        backup(args.image)

    ok = resize_image(
        args.image,
        args.image,
        scale=args.scale,
        width=args.width,
        height=args.height,
    )

    if ok:
        print("  [OK] 完成")
        return 0
    else:
        print("  [FAIL] 失敗")
        return 1


if __name__ == "__main__":
    sys.exit(main())
