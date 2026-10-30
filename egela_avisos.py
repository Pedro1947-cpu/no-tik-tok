#!/usr/bin/env python3
"""Avisa de entregas próximas y notificaciones nuevas de eGela (Moodle).

Uso:
    export EGELA_TOKEN=...            # nunca en el código
    python3 egela_avisos.py

Opcional (avisos a Telegram en vez de solo por pantalla):
    export TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=...
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

BASE = os.environ.get("EGELA_URL", "https://egela.ehu.eus")
TOKEN = os.environ.get("EGELA_TOKEN")
STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".egela_state.json")


def call(function, **params):
    params.update(wstoken=TOKEN, wsfunction=function, moodlewsrestformat="json")
    data = urllib.parse.urlencode(params).encode()
    with urllib.request.urlopen(f"{BASE}/webservice/rest/server.php", data, timeout=30) as r:
        out = json.load(r)
    if isinstance(out, dict) and out.get("exception"):
        sys.exit(f"Error de eGela en {function}: {out.get('errorcode')} - {out.get('message')}")
    return out


def load_state():
    try:
        with open(STATE) as f:
            return set(json.load(f))
    except (OSError, ValueError):
        return set()


def notify(text):
    print(text)
    bot, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if bot and chat:
        data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
        urllib.request.urlopen(f"https://api.telegram.org/bot{bot}/sendMessage", data, timeout=30)


def main():
    if not TOKEN:
        sys.exit("Falta la variable de entorno EGELA_TOKEN")
    seen = load_state()
    userid = call("core_webservice_get_site_info")["userid"]
    news = []

    events = call("core_calendar_get_action_events_by_timesort",
                  timesortfrom=int(time.time()), limitnum=50)["events"]
    for e in events:
        key = f"event:{e['id']}"
        if key not in seen:
            when = time.strftime("%d/%m %H:%M", time.localtime(e["timesort"]))
            news.append((key, f"📅 {e['name']} ({e.get('course', {}).get('shortname', '')}) - {when}"))

    notifs = call("message_popup_get_popup_notifications", useridto=userid)["notifications"]
    for n in notifs:
        key = f"notif:{n['id']}"
        if key not in seen and not n.get("read"):
            news.append((key, f"🔔 {n['subject']}"))

    for key, text in news:
        notify(text)
        seen.add(key)
    if not news:
        print("Sin novedades.")
    with open(STATE, "w") as f:
        json.dump(sorted(seen), f)


if __name__ == "__main__":
    main()
