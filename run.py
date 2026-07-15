#!/usr/bin/env python3
"""SpoilerFreeWC - 世界杯无剧透回放启动器"""

import os
import sys
import time
import subprocess
import threading
import webbrowser
from pathlib import Path

if getattr(sys, 'frozen', False):
    _BASE = Path(sys._MEIPASS)
else:
    _BASE = Path(__file__).parent

sys.path.insert(0, str(_BASE))

from web.app import app, _refresh_schedule


def _browsers_path() -> str:
    if sys.platform == 'darwin':
        return str(Path.home() / "Library" / "Caches" / "ms-playwright")
    elif sys.platform == 'win32':
        return str(Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / "ms-playwright")
    else:
        return str(Path.home() / ".cache" / "ms-playwright")

def _ensure_playwright_browser():
    """Install Playwright Chromium if missing (first run)."""
    _bp = _browsers_path()
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = _bp

    _cache = Path(_bp)
    if _cache.exists() and any(_cache.iterdir()):
        return

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            p.chromium.launch(headless=True).close()
        return
    except Exception:
        pass

    _mirrors = [
        "https://npmmirror.com/mirrors/playwright/",
        "https://playwright.azureedge.net",
    ]

    from playwright._impl._driver import compute_driver_executable, get_driver_env
    driver_exe, driver_cli = compute_driver_executable()

    for idx, mirror in enumerate(_mirrors):
        print("=" * 50)
        if idx == 0:
            print("  首次运行：正在下载浏览器内核")
            print("  使用国内镜像加速，请耐心等待...")
        else:
            print("  镜像下载失败，尝试默认源...")
        print("=" * 50)
        print()

        _env = get_driver_env()
        _env["PLAYWRIGHT_BROWSERS_PATH"] = _bp
        _env["PLAYWRIGHT_DOWNLOAD_HOST"] = mirror

        try:
            proc = subprocess.run(
                [driver_exe, driver_cli, "install", "chromium"],
                env=_env, check=True,
                timeout=600,
            )
            print()
            print("  ✓ 浏览器内核下载完成")
            print()
            return
        except subprocess.TimeoutExpired:
            print(f"  ⏱ 下载超时（超过 10 分钟）")
        except Exception as e:
            print(f"  ❌ 下载失败: {e}")
        print()

    print("=" * 50)
    print("  ❌ 所有下载源均失败")
    print("=" * 50)
    print()
    print("  可能是网络环境受限，请尝试：")
    print("  1. 关闭 VPN/代理后重新打开")
    print("  2. 检查路由器或防火墙设置")
    print("  3. 在可以访问外网的网络下使用")
    print()
    time.sleep(10)
    sys.exit(1)


def main():
    _ensure_playwright_browser()

    port = 5790

    print("=" * 50)
    print("  LaybackPassion")
    print("=" * 50)
    print()

    threading.Thread(target=_refresh_schedule, daemon=True).start()

    url = f"http://localhost:{port}"
    print(f"  浏览器地址: {url}")
    print()
    print("  使用说明:")
    print("    1. 点击 🎙 播放 自动打开回放")
    print("    2. 看完关闭浏览器窗口即可")
    print("    3. 关闭本窗口 = 停止服务")
    print()

    webbrowser.open(url)
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
