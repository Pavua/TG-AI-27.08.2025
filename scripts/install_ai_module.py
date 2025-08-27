from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path


def find_ftg_modules_dir() -> Path | None:
    spec = importlib.util.find_spec("friendly_telegram")
    if not spec or not spec.submodule_search_locations:
        return None
    base = Path(spec.submodule_search_locations[0])
    modules_dir = base / "modules"
    return modules_dir if modules_dir.is_dir() else None


def main() -> int:
    src = Path(__file__).resolve().parents[1] / "ftg" / "modules" / "ai.py"
    if not src.exists():
        print("Source module not found:", src)
        return 1
    dst_dir = find_ftg_modules_dir()
    if not dst_dir:
        print("Could not locate friendly_telegram modules directory")
        return 2
    dst = dst_dir / "ftg_ai.py"
    shutil.copy2(src, dst)
    print("Installed:", dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())


