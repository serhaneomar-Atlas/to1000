#!/usr/bin/env python3
"""notify.py — alertes marketing/ops pour to1000.com.

Envoie une alerte sur le 1er canal configuré (priorité : Telegram > Discord > SMTP).
Déclencheurs : pic de trafic, nouveau but de CR7, échec d'un workflow.

Usages :
  1) Lire les alertes calculées par collect_metrics.py (dashboard-data.json["alerts"])
     et les envoyer (dédupliquées via scripts/notify_sent.json) :
         python scripts/notify.py --from-dashboard
  2) Alerte ad hoc (ex. depuis un step "on failure") :
         python scripts/notify.py --event workflow_failure \
             --title "News sync KO" --message "Le run a échoué" --level error

Config (env / secrets) — le 1er canal renseigné gagne :
  TELEGRAM_BOT_TOKEN + TELEGRAM_ALERT_CHAT  (chat privé/admin ; PAS le canal public)
        -> à défaut de TELEGRAM_ALERT_CHAT, retombe sur TELEGRAM_CHANNEL
  DISCORD_WEBHOOK_URL
  SMTP_HOST + SMTP_USER + SMTP_PASS + ALERT_EMAIL_TO  (+ SMTP_PORT def 587)

  NOTIFY_CHANNEL=telegram|discord|email|auto   NOTIFY_DRY_RUN=1   NOTIFY_MIN_LEVEL=info|warn|error

Le token Telegram est aussi lu depuis to1000/.env (comme telegram_poster.py). Stdlib pure.
"""
from __future__ import annotations

import argparse
import json
import os
import smtplib
import sys
from email.mime.text import MIMEText
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
PUB = PROJECT_DIR / "public"
ENV_FILE = PROJECT_DIR / ".env"
DASHBOARD = PUB / "dashboard-data.json"
SENT_FILE = SCRIPT_DIR / "notify_sent.json"

REQUEST_TIMEOUT = 15
LEVEL_RANK = {"info": 0, "warn": 1, "error": 2}
LEVEL_EMOJI = {"info": "🟢", "warn": "🟡", "error": "🔴"}


def log(msg: str) -> None:
    sys.stderr.write(f"[notify] {msg}\n")


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val
    except OSError:
        pass


_load_env_file(ENV_FILE)


def _load_sent() -> set:
    try:
        return set(json.loads(SENT_FILE.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError, FileNotFoundError):
        return set()


def _save_sent(keys: set) -> None:
    if len(keys) > 500:
        keys = set(sorted(keys)[-500:])
    try:
        SENT_FILE.write_text(json.dumps(sorted(keys)), encoding="utf-8")
    except OSError as e:
        log(f"could not persist notify_sent.json: {e}")


def _send_telegram(title: str, message: str, level: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = (os.environ.get("TELEGRAM_ALERT_CHAT")
            or os.environ.get("TELEGRAM_CHANNEL", "")).strip()
    if not token or not chat:
        return False
    text = f"{LEVEL_EMOJI.get(level, '')} <b>{title}</b>\n{message}".strip()
    payload = {"chat_id": chat, "text": text,
               "parse_mode": "HTML", "disable_web_page_preview": True}
    req = Request(f"https://api.telegram.org/bot{token}/sendMessage",
                  data=urlencode(payload).encode("utf-8"), method="POST",
                  headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        if not result.get("ok"):
            log(f"telegram API error: {result}")
            return False
        return True
    except (HTTPError, URLError, TimeoutError) as e:
        log(f"telegram network error: {e}")
        return False


def _send_discord(title: str, message: str, level: str) -> bool:
    url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not url:
        return False
    color = {"info": 0x34E07A, "warn": 0xF2C14E, "error": 0xFF6178}.get(level, 0x808080)
    payload = {"embeds": [{"title": f"{LEVEL_EMOJI.get(level, '')} {title}".strip(),
                           "description": message[:4000], "color": color}]}
    req = Request(url, data=json.dumps(payload).encode("utf-8"), method="POST",
                  headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return resp.status in (200, 204)
    except (HTTPError, URLError, TimeoutError) as e:
        log(f"discord network error: {e}")
        return False


def _send_email(title: str, message: str, level: str) -> bool:
    host = os.environ.get("SMTP_HOST", "").strip()
    user = os.environ.get("SMTP_USER", "").strip()
    pwd = os.environ.get("SMTP_PASS", "").strip()
    to = os.environ.get("ALERT_EMAIL_TO", "").strip()
    if not (host and user and pwd and to):
        return False
    port = int(os.environ.get("SMTP_PORT", "587"))
    msg = MIMEText(message, "plain", "utf-8")
    msg["Subject"] = f"[to1000 {level.upper()}] {title}"
    msg["From"] = os.environ.get("SMTP_FROM", user)
    msg["To"] = to
    try:
        with smtplib.SMTP(host, port, timeout=REQUEST_TIMEOUT) as srv:
            srv.starttls()
            srv.login(user, pwd)
            srv.send_message(msg)
        return True
    except Exception as e:  # noqa: BLE001
        log(f"smtp error: {e}")
        return False


CHANNELS = {"telegram": _send_telegram, "discord": _send_discord, "email": _send_email}
AUTO_ORDER = ["telegram", "discord", "email"]


def send(title: str, message: str, level: str = "info") -> bool:
    forced = os.environ.get("NOTIFY_CHANNEL", "auto").strip().lower()
    order = [forced] if forced in CHANNELS else AUTO_ORDER
    if os.environ.get("NOTIFY_DRY_RUN") == "1":
        log(f"DRY-RUN [{level}] {title} :: {message}  (canaux: {order})")
        return True
    for name in order:
        if CHANNELS[name](title, message, level):
            log(f"sent via {name}: {title}")
            return True
    log(f"NO channel configured/succeeded for: {title}")
    return False


def run_from_dashboard() -> int:
    try:
        data = json.loads(DASHBOARD.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, FileNotFoundError) as e:
        log(f"dashboard-data.json illisible: {e}")
        return 1
    alerts = data.get("alerts", []) or []
    if not alerts:
        log("aucune alerte dans dashboard-data.json")
        return 0
    min_level = LEVEL_RANK.get(os.environ.get("NOTIFY_MIN_LEVEL", "info"), 0)
    sent = _load_sent()
    newly = set()
    fired = 0
    for a in alerts:
        key = a.get("id") or f"{a.get('event')}:{a.get('title')}"
        level = a.get("level", "info")
        if LEVEL_RANK.get(level, 0) < min_level:
            continue
        if key in sent:
            continue
        if send(a.get("title", "Alerte to1000"), a.get("message", ""), level):
            newly.add(key)
            fired += 1
    if newly:
        _save_sent(sent | newly)
    log(f"{fired} alerte(s) envoyée(s) sur {len(alerts)} candidate(s)")
    return 0


def run_adhoc(args) -> int:
    key = args.id or f"{args.event}:{args.title}"
    sent = _load_sent()
    if not args.allow_dup and key in sent:
        log(f"déjà envoyée, skip: {key}")
        return 0
    ok = send(args.title, args.message, args.level)
    if ok and not args.allow_dup:
        _save_sent(sent | {key})
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="Alertes to1000")
    p.add_argument("--from-dashboard", action="store_true",
                   help="lit dashboard-data.json[alerts] et envoie les nouvelles")
    p.add_argument("--event", default="manual",
                   help="traffic_spike | cr7_goal | workflow_failure | manual")
    p.add_argument("--title", default="Alerte to1000")
    p.add_argument("--message", default="")
    p.add_argument("--level", default="info", choices=list(LEVEL_RANK))
    p.add_argument("--id", default="", help="clé de dédup (sinon event:title)")
    p.add_argument("--allow-dup", action="store_true")
    args = p.parse_args()
    if args.from_dashboard:
        return run_from_dashboard()
    return run_adhoc(args)


if __name__ == "__main__":
    raise SystemExit(main())
