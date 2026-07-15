import json
import re
from datetime import datetime, timezone, timedelta

import requests

CCTV_API_URL = "https://cbs-u.sports.cctv.com/pc/game/season_game_list?leagueId=3400&season=2026&client=pc"
CCTV_MATCH_URL = "https://worldcup.cctv.cn/2026/match/{match_id}/index.shtml"
CCTV_SCHEDULE_URL = "https://worldcup.cctv.com/2026/schedule/"

ROUND_CN = {
    "小组赛": "小组赛", "1/16决赛": "1/16决赛", "1/8决赛": "1/8决赛",
    "1/4决赛": "1/4决赛", "半决赛": "半决赛", "季军赛": "季军赛", "决赛": "决赛",
}

def _api_time_to_beijing(time_str: str) -> str:
    try:
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        dt = dt.replace(tzinfo=timezone(timedelta(hours=8)))
        return dt.isoformat()
    except ValueError:
        return time_str


def _format_stage(round_type: str, game_round: str) -> str:
    rt = round_type or ""
    gr = game_round or ""
    if "组" in rt:
        return f"小组赛 {rt}"
    if "决赛" in gr:
        return gr
    if "决赛" in rt:
        return rt
    return gr or rt


def fetch_from_cctv_api() -> list[dict]:
    """Fetch all matches from CCTV's internal API."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://worldcup.cctv.com/",
    }
    resp = requests.get(CCTV_API_URL, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if not data.get("success"):
        print(f"[scheduler] API 返回失败: {data.get('msg', '')}")
        return []

    matches = []
    for game in data.get("results", []):
        match_id = str(game.get("id", ""))
        if not match_id:
            continue

        home = game.get("homeName", "").strip()
        away = game.get("guestName", "").strip()
        time_raw = game.get("startTime", "")
        round_type = game.get("roundType", "")
        game_round = game.get("gameRound", "")
        has_video = game.get("hasVideo", 0) == 1

        if not home or not away:
            continue

        matches.append({
            "id": match_id,
            "home": home,
            "away": away,
            "home_en": home,
            "away_en": away,
            "time": _api_time_to_beijing(time_raw),
            "stage": _format_stage(round_type, game_round),
            "replay_url": CCTV_MATCH_URL.format(match_id=match_id),
            "replay_available": has_video,
            "cctv_confirmed": True,
            "watched": False,
        })

    return matches


def get_daily_schedule() -> list[dict]:
    print("[scheduler] 正在从央视获取赛程数据...")
    try:
        matches = fetch_from_cctv_api()
        print(f"[scheduler] 成功获取 {len(matches)} 场比赛")
        return matches
    except Exception as e:
        print(f"[scheduler] 央视API获取失败: {e}")
        print("[scheduler] 尝试从 openfootball 获取备用数据...")
        try:
            return _fetch_fallback()
        except Exception as e2:
            print(f"[scheduler] 备用数据也获取失败: {e2}")
            return []


def _fetch_fallback() -> list[dict]:
    """Fallback to openfootball data if CCTV API fails."""
    OPENFOOTBALL_URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"
    resp = requests.get(OPENFOOTBALL_URL, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    TEAM_NAME_CN = {
        "Mexico": "墨西哥", "South Africa": "南非", "South Korea": "韩国",
        "United States": "美国", "Canada": "加拿大", "Brazil": "巴西", "Argentina": "阿根廷",
        "France": "法国", "Spain": "西班牙", "England": "英格兰", "Germany": "德国",
        "Portugal": "葡萄牙", "Netherlands": "荷兰", "Italy": "意大利", "Croatia": "克罗地亚",
        "Japan": "日本", "Saudi Arabia": "沙特", "Australia": "澳大利亚", "Iran": "伊朗",
        "Morocco": "摩洛哥", "Senegal": "塞内加尔", "Uruguay": "乌拉圭", "Colombia": "哥伦比亚",
        "Switzerland": "瑞士", "Algeria": "阿尔及利亚", "Paraguay": "巴拉圭", "Egypt": "埃及",
        "Belgium": "比利时", "Norway": "挪威", "Sweden": "瑞典", "Scotland": "苏格兰",
        "Qatar": "卡塔尔", "Austria": "奥地利", "Poland": "波兰", "Denmark": "丹麦",
        "Iceland": "冰岛", "Nigeria": "尼日利亚", "Cameroon": "喀麦隆", "Ghana": "加纳",
        "Tunisia": "突尼斯", "Ecuador": "厄瓜多尔", "Chile": "智利", "Peru": "秘鲁",
        "Costa Rica": "哥斯达黎加", "Panama": "巴拿马", "Jamaica": "牙买加",
        "Iraq": "伊拉克", "Uzbekistan": "乌兹别克斯坦", "Jordan": "约旦",
        "New Zealand": "新西兰", "China": "中国", "Indonesia": "印度尼西亚",
        "Cape Verde": "佛得角", "Haiti": "海地", "Curaçao": "库拉索",
        "Czech": "捷克", "Czech Republic": "捷克", "Korea Republic": "韩国",
        "USA": "美国", "Bosnia & Herzegovina": "波黑", "Bosnia and Herzegovina": "波黑",
        "Ivory Coast": "科特迪瓦", "Côte d'Ivoire": "科特迪瓦", "Honduras": "洪都拉斯",
        "DR Congo": "刚果（金）", "Congo DR": "刚果（金）",
        "Türkiye": "土耳其", "Turkey": "土耳其",
    }

    matches = []
    for m in data.get("matches", []):
        home_en = m.get("team1", "")
        away_en = m.get("team2", "")
        if not home_en or not away_en:
            continue
        if re.match(r'^[WL]\d{3}$', home_en) or re.match(r'^[WL]\d{3}$', away_en):
            continue

        match_id = re.sub(r'[^a-zA-Z0-9]', '_', f"{m.get('date', '')}-{home_en}-{away_en}").strip('_').lower()
        date_str = m.get("date", "")
        time_str = m.get("time", "")
        round_str = m.get("round", "")
        group = m.get("group", "")

        dt = _parse_fallback_time(date_str, time_str)
        if dt is None:
            continue

        matches.append({
            "id": match_id,
            "home": TEAM_NAME_CN.get(home_en, home_en),
            "away": TEAM_NAME_CN.get(away_en, away_en),
            "home_en": home_en,
            "away_en": away_en,
            "time": dt.isoformat(),
            "stage": _format_fallback_stage(round_str, group),
            "replay_url": "",
            "replay_available": False,
            "cctv_confirmed": False,
            "watched": False,
        })

    print(f"[scheduler] 备用数据: {len(matches)} 场比赛")
    return matches


def _parse_fallback_time(date_str: str, time_str: str):
    try:
        utc_offset = timedelta()
        if time_str:
            offset_match = re.search(r'UTC([+-]\d+(?::\d+)?)', time_str)
            if offset_match:
                parts = [int(x) for x in offset_match.group(1).split(':')]
                utc_offset = timedelta(hours=parts[0]) if len(parts) == 1 else timedelta(hours=parts[0], minutes=parts[1])
            time_clean = re.sub(r'\s*UTC[+-]\d+(?::\d+)?', '', time_str).strip()
        else:
            time_clean = "12:00"

        dt = datetime.fromisoformat(f"{date_str}T{time_clean}")
        dt = dt.replace(tzinfo=timezone.utc) - utc_offset
        return dt.astimezone(timezone(timedelta(hours=8)))
    except (ValueError, TypeError):
        return None


def _format_fallback_stage(round_str: str, group: str) -> str:
    if group and ("Group" in round_str or "Matchday" in round_str):
        return f"小组赛 {group}"
    stage_map = {
        "Matchday": "小组赛", "Group": "小组赛", "Round of 32": "1/16决赛",
        "Round of 16": "1/8决赛", "Quarter-finals": "1/4决赛", "Quarter": "1/4决赛",
        "Semi-finals": "半决赛", "Semi": "半决赛", "Third place": "季军赛",
        "Third": "季军赛", "Final": "决赛",
    }
    for en, cn in stage_map.items():
        if en.lower() in round_str.lower():
            return cn
    return round_str
