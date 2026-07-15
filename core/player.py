import sys

VERSION_PRIORITY = ["超级绿茵场演播室", "CCTV5解说", "CCTV5演播室", "央视体育剪辑版", "央视体育"]

YANG_SHIPIN_URL = "https://www.yangshipin.cn/video/home?cid=f5tsldorccggid3&lid=10819"

ANTI_SPOILER_JS = """
(function() {
    var s = document.createElement('style');
    s.textContent = `
        [class*="video-main-r"],[class*="comment"],[class*="danmu"],[class*="danmaku"],
        [class*="recommend"],[class*="sidebar"],[class*="bottom-bar"],[class*="policy"],
        [class*="next-episode"],.volume-muted-tip,.corner-marker-vid
    { display: none !important; }
        [class*="video-main"]{ width: 100vw !important; max-width: 100vw !important; }
        [class*="video-con"]{ width: 100vw !important; height: 100vh !important; }
        video{ width: 100vw !important; height: 100vh !important; object-fit: contain !important; }
    `;
    document.head.appendChild(s);
    function h(n) {
        if (n.nodeType === 3) n.textContent = n.textContent.replace(/\\d+\\s*[-:]\\s*\\d+/g, '??-??');
        else if (n.nodeType === 1 && n.tagName !== 'SCRIPT' && n.tagName !== 'STYLE')
            for (var i = 0; i < n.childNodes.length; i++) h(n.childNodes[i]);
    }
    h(document.body);
    new MutationObserver(function(m) {
        for (var i = 0; i < m.length; i++)
            for (var j = 0; j < m[i].addedNodes.length; j++) h(m[i].addedNodes[j]);
    }).observe(document.body, { childList: true, subtree: true });
})();
"""

AUTOPLAY_JS = """
(function() {
    var v = document.querySelector('video');
    if (v) { v.muted = false; v.play().catch(function(){}); return 'ok'; }
    return 'no_video';
})();
"""


VERSION_ALIAS = {
    "演播室": "超级绿茵场演播室",
    "解说": "CCTV5解说",
}

class NoReplayError(Exception):
    pass


def _browsers_path() -> str:
    import os, sys
    from pathlib import Path
    if sys.platform == 'darwin':
        return str(Path.home() / "Library" / "Caches" / "ms-playwright")
    elif sys.platform == 'win32':
        return str(Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / "ms-playwright")
    else:
        return str(Path.home() / ".cache" / "ms-playwright")

def _setup_env():
    import os
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", _browsers_path())
    os.environ.setdefault("PLAYWRIGHT_DOWNLOAD_HOST", "https://npmmirror.com/mirrors/playwright/")

def play_match(match: dict, version: str = ""):
    _setup_env()

    home = match.get("home", "")
    away = match.get("away", "")
    stage = match.get("stage", "")

    version_label = f"（{version}）" if version else ""
    print(f"[player] ▶ 正在播放: {home} vs {away}{version_label}")

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        launch_kw = dict(
            headless=False,
            args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
        )
        if sys.platform == 'win32':
            launch_kw["channel"] = "msedge"
        browser = p.chromium.launch(**launch_kw)
        context = browser.new_context(no_viewport=True, locale="zh-CN")
        page = context.new_page()

        page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined })")
        page.add_init_script(ANTI_SPOILER_JS)

        page.goto(YANG_SHIPIN_URL, wait_until="domcontentloaded", timeout=30000)
        _wait_for_episodes(page)

        if not _find_and_click_match(page, home, away, stage, version):
            page.close()
            browser.close()
            raise NoReplayError(f"{home} vs {away} 在央视频暂未提供全场回放")

        page.wait_for_timeout(3000)
        _autoplay(page)

        print("[player] ✓ 比分已隐藏，关闭浏览器窗口即可停止")

        try:
            while not page.is_closed():
                page.wait_for_timeout(10000)
        except Exception:
            pass
        finally:
            browser.close()


def _wait_for_episodes(page, timeout=20):
    for i in range(timeout):
        try:
            count = page.evaluate(
                "document.querySelectorAll('[class*=\"video-main-r-more-a-item\"].cursorHand').length"
            )
            if count > 0:
                print(f"[player] 已加载 {count} 个视频项")
                return
        except Exception:
            pass
        page.wait_for_timeout(1000)
    print("[player] ⚠ 等待视频列表超时")


def _find_and_click_match(page, home: str, away: str, stage: str, preferred_version: str = "") -> bool:
    items = page.query_selector_all('[class*="video-main-r-more-a-item"].cursorHand')
    if not items:
        return False

    stage_clean = stage.replace(" ", "").strip()
    home_norm = home.replace("（", "(").replace("）", ")")
    away_norm = away.replace("（", "(").replace("）", ")")

    candidates = []
    for item in items:
        text_el = item.query_selector('[class*="overflow-2"]')
        if not text_el:
            continue
        title = text_el.inner_text().strip()

        if home_norm not in title and home not in title:
            continue
        if away_norm not in title and away not in title:
            continue
        if stage_clean not in title:
            continue

        candidates.append((item, title))

    if not candidates:
        print(f"[player] 找不到 {home} vs {away}（{stage}）")
        return False

    # 如果指定了版本，优先匹配
    if preferred_version:
        alias = VERSION_ALIAS.get(preferred_version, preferred_version)
        for item, title in candidates:
            if alias in title:
                print(f"[player] 找到: {title}")
                item.click()
                return True

    # 未指定或指定版本不存在 → 按优先级
    for prio in VERSION_PRIORITY:
        for item, title in candidates:
            if prio in title:
                print(f"[player] 找到: {title}")
                item.click()
                return True

    print(f"[player] 找到（默认）: {candidates[0][1]}")
    candidates[0][0].click()
    return True


def _autoplay(page):
    for _ in range(10):
        try:
            r = page.evaluate(AUTOPLAY_JS)
            if r == "ok":
                print("[player] ✓ 视频已播放")
                return
        except Exception:
            pass
        page.wait_for_timeout(2000)
