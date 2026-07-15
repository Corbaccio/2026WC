import os
import sys
import threading
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from core.bookmark import load, save, mark_watched
from core.scheduler import get_daily_schedule

if getattr(sys, 'frozen', False):
    _TEMPLATE_DIR = Path(sys._MEIPASS) / "web" / "templates"
else:
    _TEMPLATE_DIR = Path(__file__).parent / "templates"

app = Flask(__name__, template_folder=str(_TEMPLATE_DIR))

_play_status: dict = {}


def _refresh_schedule():
    print("[web] 正在刷新赛程数据...")
    try:
        new_matches = get_daily_schedule()
        existing = {m["id"]: m for m in load()}
        for m in new_matches:
            if m["id"] in existing:
                existing[m["id"]]["replay_available"] = m.get("replay_available", False)
                existing[m["id"]]["replay_url"] = m.get("replay_url", "")
            else:
                existing[m["id"]] = m
        save(list(existing.values()))
        print(f"[web] 赛程刷新完成，共 {len(existing)} 场比赛")
    except Exception as e:
        print(f"[web] 赛程刷新失败: {e}")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/matches")
def api_matches():
    matches = load()

    KNOCKOUT_ROUNDS = ["1/16决赛", "1/8决赛", "1/4决赛", "半决赛", "季军赛", "决赛"]

    knockout = [m for m in matches if m.get("stage", "") in KNOCKOUT_ROUNDS]
    knockout.sort(key=lambda m: m.get("time", ""))

    rounds = {}
    for m in knockout:
        s = m["stage"]
        if s not in rounds:
            rounds[s] = []
        rounds[s].append(_sanitize([m])[0])

    return jsonify({
        "rounds": rounds,
        "order": KNOCKOUT_ROUNDS,
    })


@app.route("/api/play/<match_id>")
def api_play(match_id):
    matches = load()
    match = next((m for m in matches if m["id"] == match_id), None)
    if not match:
        return jsonify({"error": "比赛未找到"}), 404

    version = request.args.get("version", "")

    _play_status["error"] = None
    _play_status["message"] = "正在打开播放器..."

    def _play():
        from core.player import play_match, NoReplayError
        try:
            play_match(match, version=version)
            _play_status["message"] = "播放完成"
        except NoReplayError as e:
            _play_status["error"] = str(e)
            _play_status["message"] = str(e)
        except Exception as e:
            _play_status["error"] = f"播放失败: {e}"
            _play_status["message"] = f"播放失败: {e}"

    threading.Thread(target=_play, daemon=True).start()
    return jsonify({"status": "ok", "message": "正在打开播放器..."})


@app.route("/api/play-status")
def api_play_status():
    return jsonify({
        "error": _play_status.get("error"),
        "message": _play_status.get("message", ""),
    })


@app.route("/api/watched/<match_id>", methods=["POST"])
def api_watched(match_id):
    mark_watched(match_id)
    return jsonify({"status": "ok"})


@app.route("/api/refresh")
def api_refresh():
    _refresh_schedule()
    return jsonify({"status": "ok"})


@app.route("/api/shutdown")
def api_shutdown():
    threading.Thread(target=_do_shutdown, daemon=True).start()
    return jsonify({"status": "ok", "message": "正在关闭..."})


def _do_shutdown():
    import time
    time.sleep(0.5)
    os._exit(0)


def _sanitize(matches: list) -> list:
    return [{
        "id": m["id"],
        "home": m["home"],
        "away": m["away"],
        "time": m["time"],
        "stage": m["stage"],
        "replay_available": m.get("replay_available", False),
        "watched": m.get("watched", False),
    } for m in matches]
