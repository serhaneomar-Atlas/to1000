"""
goal_watcher.py — Détecte automatiquement les buts de CR7 et déploie le site

Lancé toutes les 5 minutes par Windows Task Scheduler.
Fait des appels API UNIQUEMENT pendant les fenêtres de match (économise le quota gratuit).

Quota API-Football free tier : 100 req/jour
  - Hors match  : 1 req/heure (rafraîchit le calendrier) = ~24/jour
  - Pendant match : 1 req/5 min × 2h = ~24/match

Setup :
  1. Créer un compte gratuit sur https://dashboard.api-football.com/register
  2. Copier ta clé API
  3. Exécuter setup_watcher.ps1 (enregistre la tâche Windows + stocke la clé)
"""

import json, os, sys, subprocess, requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ─── CHEMINS ────────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
PUBLIC_DIR  = PROJECT_DIR / "public"
STATS_FILE  = PUBLIC_DIR / "stats.json"
STATE_FILE  = SCRIPT_DIR / "watcher_state.json"
LOG_FILE    = SCRIPT_DIR / "watcher.log"

# ─── CONFIG API ─────────────────────────────────────────────────────────────
API_KEY   = os.environ.get("APIFOOTBALL_KEY", "")
CR7_ID    = 874
AL_NASSR  = 2911
PORTUGAL  = 27
SPL_ID    = 307   # Saudi Pro League
TARGET    = 1000
BASELINE  = 832   # Buts de carrière avant saison 2025-26

API_BASE = "https://v3.football.api-sports.io"
HEADERS  = {"x-rapidapi-host": "v3.football.api-sports.io", "x-rapidapi-key": API_KEY}

# Fenêtre de match : 30 min avant à 2h après le coup d'envoi
PRE_MATCH  = 30
POST_MATCH = 120

# ─── LOGGING ────────────────────────────────────────────────────────────────
def log(msg):
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        # Garder les 1000 dernières lignes
        lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
        if len(lines) > 1000:
            LOG_FILE.write_text("\n".join(lines[-1000:]) + "\n", encoding="utf-8")
    except:
        pass

# ─── ÉTAT LOCAL ─────────────────────────────────────────────────────────────
def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except:
            pass
    return {"last_fixture_fetch": None, "next_match": None}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

def load_stats():
    if STATS_FILE.exists():
        return json.loads(STATS_FILE.read_text(encoding="utf-8"))
    return {"goals": 968, "target": TARGET, "remaining": 32}

# ─── API-FOOTBALL ────────────────────────────────────────────────────────────
def fetch_next_fixture():
    """Cherche le prochain match d'Al Nassr ou du Portugal. Coûte 2 req API."""
    best = None
    for team_id in [AL_NASSR, PORTUGAL]:
        try:
            r = requests.get(f"{API_BASE}/fixtures", headers=HEADERS,
                             params={"team": team_id, "next": 5}, timeout=10)
            r.raise_for_status()
            for fx in r.json().get("response", []):
                kickoff = fx.get("fixture", {}).get("date", "")
                if not kickoff:
                    continue
                candidate = {
                    "kickoff_utc": kickoff,
                    "home": fx["teams"]["home"]["name"],
                    "away": fx["teams"]["away"]["name"],
                    "competition": fx.get("league", {}).get("name", ""),
                    "team_id": team_id,
                }
                if best is None or kickoff < best["kickoff_utc"]:
                    best = candidate
        except Exception as e:
            log(f"  ⚠ Fixture fetch error (team {team_id}): {e}")
    if best:
        log(f"  📅 Prochain match : {best['home']} vs {best['away']} @ {best['kickoff_utc']}")
    return best

def fetch_cr7_goals():
    """Récupère les buts de CR7 cette saison pour calculer le total carrière. Coûte 1 req API."""
    season = datetime.now().year if datetime.now().month >= 7 else datetime.now().year - 1
    try:
        r = requests.get(f"{API_BASE}/players", headers=HEADERS, params={
            "id": CR7_ID, "team": AL_NASSR, "league": SPL_ID, "season": season,
        }, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("response"):
            stats = data["response"][0].get("statistics", [])
            if stats:
                season_goals = stats[0].get("goals", {}).get("total", 0) or 0
                career_total = BASELINE + season_goals
                log(f"  📊 Saison {season}: {season_goals} buts SPL → Carrière estimée: {career_total}")
                return career_total
    except Exception as e:
        log(f"  ⚠ Goals fetch error: {e}")
    return None

# ─── FENÊTRE DE MATCH ────────────────────────────────────────────────────────
def in_match_window(next_match):
    if not next_match or not next_match.get("kickoff_utc"):
        return False
    try:
        kickoff = datetime.fromisoformat(next_match["kickoff_utc"].replace("Z", "+00:00"))
        now     = datetime.now(timezone.utc)
        return (kickoff - timedelta(minutes=PRE_MATCH)) <= now <= (kickoff + timedelta(minutes=POST_MATCH))
    except:
        return False

def minutes_until_match(next_match):
    if not next_match or not next_match.get("kickoff_utc"):
        return 9999
    try:
        kickoff = datetime.fromisoformat(next_match["kickoff_utc"].replace("Z", "+00:00"))
        return (kickoff - datetime.now(timezone.utc)).total_seconds() / 60
    except:
        return 9999

# ─── MISE À JOUR DU SITE ─────────────────────────────────────────────────────
def update_stats_file(new_goals):
    """Met à jour stats.json avec le nouveau nombre de buts."""
    stats = load_stats()
    stats["goals"]        = new_goals
    stats["remaining"]    = TARGET - new_goals
    stats["last_updated"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    stats["version"]      = stats.get("version", 1) + 1
    STATS_FILE.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"  ✅ stats.json mis à jour → {new_goals} buts")

def run_full_update():
    """Lance update_stats.py pour mettre à jour toutes les statistiques riches (dernier match, prochain match, etc.)."""
    update_script = SCRIPT_DIR / "update_stats.py"
    if not update_script.exists():
        log("  ⚠ update_stats.py introuvable — mise à jour basique uniquement")
        return False
    try:
        result = subprocess.run(
            [sys.executable, str(update_script)],
            cwd=PROJECT_DIR, capture_output=True, text=True, timeout=60,
            env={**os.environ, "APIFOOTBALL_KEY": API_KEY}
        )
        if result.stdout:
            for line in result.stdout.strip().splitlines():
                log(f"  [update_stats] {line}")
        if result.returncode != 0 and result.stderr:
            log(f"  ⚠ update_stats stderr: {result.stderr[:300]}")
        return result.returncode == 0
    except Exception as e:
        log(f"  ⚠ update_stats error: {e}")
        return False

def deploy():
    """Déploie le site sur Cloudflare Pages via Wrangler."""
    log("  🚀 Déploiement en cours...")
    try:
        # Sur Windows, on a besoin de shell=True pour npx
        cmd = "npx wrangler pages deploy public/ --project-name to1000 --branch main"
        result = subprocess.run(
            cmd, cwd=PROJECT_DIR, capture_output=True, text=True,
            timeout=120, shell=True
        )
        if result.returncode == 0:
            log("  ✅ Déploiement réussi !")
            return True
        else:
            log(f"  ❌ Déploiement échoué: {result.stderr[:500]}")
            return False
    except Exception as e:
        log(f"  ❌ Déploiement erreur: {e}")
        return False

# ─── NOTIFICATION WINDOWS ────────────────────────────────────────────────────
def notify(title, message):
    """Envoie une notification toast Windows."""
    try:
        ps_script = f'''
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$template = [Windows.UI.Notifications.ToastTemplateType]::ToastImageAndText02
$xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($template)
$xml.GetElementsByTagName("text")[0].AppendChild($xml.CreateTextNode("{title}")) | Out-Null
$xml.GetElementsByTagName("text")[1].AppendChild($xml.CreateTextNode("{message}")) | Out-Null
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("CR7 Goal Watcher").Show($toast)
'''
        subprocess.Popen(
            ["powershell", "-WindowStyle", "Hidden", "-Command", ps_script],
            creationflags=0x08000000  # CREATE_NO_WINDOW
        )
        log(f"  🔔 Notification envoyée: {title}")
    except Exception as e:
        log(f"  ⚠ Notification error: {e}")

# ─── MAIN ────────────────────────────────────────────────────────────────────
def main():
    log("━━━ Goal Watcher démarré ━━━")

    if not API_KEY:
        log("❌ APIFOOTBALL_KEY non défini.")
        log("   → Va sur https://dashboard.api-football.com/register pour une clé gratuite")
        log("   → Puis lance setup_watcher.ps1 pour configurer le système")
        sys.exit(1)

    state        = load_state()
    stats        = load_stats()
    current_goals = stats.get("goals", 968)
    now          = datetime.now(timezone.utc)

    # ── Rafraîchir le calendrier des matchs toutes les heures ──
    last_fetch        = state.get("last_fixture_fetch")
    fetch_needed      = True
    if last_fetch:
        try:
            if (now - datetime.fromisoformat(last_fetch)).total_seconds() < 3600:
                fetch_needed = False
        except:
            pass

    if fetch_needed:
        log("  📅 Rafraîchissement du calendrier des matchs...")
        next_match = fetch_next_fixture()

        # Fallback : si l'API ne retourne rien, lire next_match depuis stats.json
        if not next_match:
            stats_data = load_stats()
            nm = stats_data.get("next_match")
            if nm and nm.get("kickoff_utc"):
                next_match = {
                    "kickoff_utc": nm["kickoff_utc"],
                    "home": nm.get("home_team", ""),
                    "away": nm.get("away_team", ""),
                    "competition": nm.get("competition", ""),
                }
                log(f"  📅 Prochain match (stats.json) : {next_match['home']} vs {next_match['away']} @ {next_match['kickoff_utc']}")
            else:
                log("  📅 Aucun match trouve (API + stats.json)")

        state["next_match"]         = next_match
        state["last_fixture_fetch"] = now.isoformat()
        save_state(state)
    else:
        next_match = state.get("next_match")
        mins       = int(minutes_until_match(next_match))
        if next_match:
            log(f"  📅 Prochain match dans {mins} min (cache valide)")

    # ── Vérifier la fenêtre de match ──
    in_window = in_match_window(next_match)
    if not in_window:
        mins = int(minutes_until_match(next_match))
        if mins < 9999:
            log(f"  💤 Hors fenêtre de match ({mins} min avant coup d'envoi) — pas de vérification de buts")
        else:
            log("  💤 Aucun match prévu — pas de vérification de buts")
        log("━━━ Terminé ━━━\n")
        return

    # ── Dans la fenêtre de match : vérifier les buts ──
    log(f"  🔴 FENÊTRE DE MATCH ACTIVE — Vérification des buts (actuel: {current_goals})")
    new_goals = fetch_cr7_goals()

    if new_goals is None:
        log("  ⚠ Impossible de récupérer le nombre de buts — ignoré")
        log("━━━ Terminé ━━━\n")
        return

    if new_goals > current_goals:
        scored = new_goals - current_goals
        log(f"  ⚽⚽⚽ BUT DÉTECTÉ ! {current_goals} → {new_goals} (+{scored})")

        # Mise à jour rapide de stats.json
        update_stats_file(new_goals)

        # Mise à jour complète (dernier match, prochain match, stats riches)
        log("  🔄 Mise à jour complète des statistiques...")
        run_full_update()

        # Déploiement
        deploy()

        # Notification Windows
        remaining = TARGET - new_goals
        if scored == 1:
            notify("⚽ CR7 a marqué !", f"{current_goals} → {new_goals} buts | Plus que {remaining} pour 1000 !")
        else:
            notify(f"⚽ CR7 a marqué {scored} buts !", f"Total: {new_goals} | Reste: {remaining} pour 1000 !")

        state["last_goal_check"] = now.isoformat()
        save_state(state)

    elif new_goals == current_goals:
        log(f"  — Pas de nouveau but (toujours {current_goals})")
    else:
        log(f"  ⚠ API retourne {new_goals} < actuel {current_goals} — anomalie ignorée")

    log("━━━ Terminé ━━━\n")


if __name__ == "__main__":
    main()
