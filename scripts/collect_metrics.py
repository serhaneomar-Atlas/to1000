#!/usr/bin/env python3
"""collect_metrics.py — agrège les métriques du site dans public/dashboard-data.json
et tient un historique (scripts/metrics_history.json) pour les courbes d'évolution.

Données sans auth externe : progression des buts (le hook), vélocité de contenu
(news, sources), pages indexables (sitemap), fraîcheur. TRAFIC réel : GA4 si
GA4_PROPERTY_ID + GOOGLE_APPLICATION_CREDENTIALS, sinon état "à connecter".

NOUVEAU : deltas vs run précédent, répartition par source/langue, et « alertes »
dérivées (pic de trafic, nouveau but CR7, run news en échec, jalon proche).
Le bloc data["alerts"] est consommé par scripts/notify.py --from-dashboard.
"""
import json, os, re, glob
from collections import Counter
from pathlib import Path
from datetime import datetime, timezone

PUB = Path(__file__).resolve().parent.parent / "public"
HIST = Path(__file__).resolve().parent / "metrics_history.json"

TRAFFIC_SPIKE_RATIO = float(os.environ.get("ALERT_TRAFFIC_SPIKE_RATIO", "1.5"))
TRAFFIC_SPIKE_MIN = int(os.environ.get("ALERT_TRAFFIC_SPIKE_MIN", "30"))


def _load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def _now():
    return os.environ.get("RUN_DATE") or datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _delta(cur, prev):
    if cur is None or prev is None:
        return None
    diff = cur - prev
    pct = round(diff / prev * 100, 1) if prev else None
    return {"abs": diff, "pct": pct, "dir": "up" if diff > 0 else "down" if diff < 0 else "flat"}


def fetch_ga4():
    prop = os.environ.get("GA4_PROPERTY_ID", "").strip()
    if not prop or not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        return None
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            DateRange, Dimension, Metric, RunReportRequest, OrderBy)
        cli = BetaAnalyticsDataClient()
        daily = cli.run_report(RunReportRequest(
            property=f"properties/{prop}",
            dimensions=[Dimension(name="date")],
            metrics=[Metric(name="activeUsers"), Metric(name="sessions"),
                     Metric(name="screenPageViews")],
            date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
            order_bys=[OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="date"))]))
        series = [{"date": r.dimension_values[0].value,
                   "users": int(r.metric_values[0].value),
                   "sessions": int(r.metric_values[1].value),
                   "views": int(r.metric_values[2].value)} for r in daily.rows]

        def top(dim, metric="screenPageViews", n=8):
            rep = cli.run_report(RunReportRequest(
                property=f"properties/{prop}", dimensions=[Dimension(name=dim)],
                metrics=[Metric(name=metric)],
                date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
                order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name=metric), desc=True)],
                limit=n))
            return [{"label": r.dimension_values[0].value, "value": int(r.metric_values[0].value)} for r in rep.rows]
        return {
            "connected": True,
            "users_30d": sum(d["users"] for d in series),
            "sessions_30d": sum(d["sessions"] for d in series),
            "views_30d": sum(d["views"] for d in series),
            "series": series,
            "top_pages": top("pagePath"),
            "sources": top("sessionDefaultChannelGroup", "sessions"),
            "countries": top("country", "activeUsers"),
        }
    except Exception as e:
        return {"connected": False, "error": str(e)[:160]}


def compute_deltas(snapshot, history):
    prev = None
    for h in reversed(history):
        if h.get("date") != snapshot["date"]:
            prev = h
            break
    keys = ("goals", "news_items", "news_sources", "article_pages", "sitemap_urls")
    return {k: _delta(snapshot.get(k), (prev or {}).get(k)) for k in keys}, prev


def compute_traffic_delta(traffic, history):
    if not traffic or not traffic.get("connected"):
        return None
    prev = None
    for h in reversed(history):
        if h.get("users_30d") is not None and h.get("date") != _now():
            prev = h
            break
    return _delta(traffic.get("users_30d"), (prev or {}).get("users_30d"))


def detect_alerts(snapshot, deltas, traffic, traffic_delta, news, prev_snapshot):
    alerts = []
    day = snapshot["date"]
    nstats = news.get("stats", {}) or {}

    if prev_snapshot and snapshot["goals"] > prev_snapshot.get("goals", snapshot["goals"]):
        diff = snapshot["goals"] - prev_snapshot["goals"]
        rem = snapshot["remaining"]
        alerts.append({
            "id": f"cr7_goal:{snapshot['goals']}",
            "event": "cr7_goal", "level": "info",
            "title": f"⚽ But CR7 — compteur à {snapshot['goals']}/1000",
            "message": f"+{diff} but(s). Plus que {rem} avant l'histoire ({snapshot['pct_to_1000']}%).",
        })

    if traffic_delta and traffic_delta.get("pct") is not None:
        users = (traffic or {}).get("users_30d", 0)
        if (traffic_delta["dir"] == "up"
                and traffic_delta["pct"] >= (TRAFFIC_SPIKE_RATIO - 1) * 100
                and users >= TRAFFIC_SPIKE_MIN):
            alerts.append({
                "id": f"traffic_spike:{day}",
                "event": "traffic_spike", "level": "info",
                "title": "📈 Pic de trafic détecté",
                "message": f"Visiteurs 30 j : {users} (+{traffic_delta['pct']}% vs run précédent).",
            })

    published = nstats.get("published", snapshot.get("news_items", 0))
    feeds_failed = nstats.get("feeds_failed", 0)
    feeds_fetched = nstats.get("feeds_fetched", 0)
    total_feeds = feeds_failed + feeds_fetched
    if published == 0:
        alerts.append({
            "id": f"news_empty:{day}",
            "event": "workflow_failure", "level": "error",
            "title": "🛑 Pipeline news vide",
            "message": "0 news publiée au dernier run — vérifier news_aggregator.py.",
        })
    elif total_feeds and feeds_failed > total_feeds * 0.5:
        alerts.append({
            "id": f"feeds_degraded:{day}",
            "event": "workflow_failure", "level": "warn",
            "title": "⚠️ Sources d'actu dégradées",
            "message": f"{feeds_failed}/{total_feeds} flux RSS en échec ce run.",
        })

    if 0 < snapshot["remaining"] <= 10:
        alerts.append({
            "id": f"milestone_near:{snapshot['goals']}",
            "event": "milestone_near", "level": "warn",
            "title": f"🔥 Plus que {snapshot['remaining']} buts avant 1000",
            "message": "Fenêtre de buzz imminente — préparer push social + presse.",
        })

    return alerts


def main():
    stats = _load(PUB / "stats.json", {}) or {}
    news = _load(PUB / "news.json", {}) or {}
    items = news.get("items", [])
    nstats = news.get("stats", {}) or {}

    goals = stats.get("goals", 0)
    target = stats.get("target", 1000)
    source_names = [(it.get("primary_source") or {}).get("name")
                    for it in items if it.get("primary_source")]
    sources = sorted(set(n for n in source_names if n))
    source_breakdown = [{"label": k, "value": v}
                        for k, v in Counter(n for n in source_names if n).most_common()]
    lang_breakdown = [{"label": k, "value": v} for k, v in Counter(
        (it.get("primary_source") or {}).get("lang", "?") for it in items).most_common()]

    article_pages = len(glob.glob(str(PUB / "news" / "*.html")))
    try:
        sitemap_urls = len(re.findall(r"<loc>", (PUB / "sitemap.xml").read_text(encoding="utf-8")))
    except Exception:
        sitemap_urls = 0

    snapshot = {
        "date": _now(),
        "goals": goals,
        "remaining": stats.get("remaining", target - goals),
        "pct_to_1000": round(goals / target * 100, 1) if target else 0,
        "news_items": len(items),
        "news_sources": len(sources),
        "cr7_items": sum(1 for it in items if it.get("kind") == "cr7"),
        "article_pages": article_pages,
        "sitemap_urls": sitemap_urls,
    }

    history = _load(HIST, []) or []
    prev_for_alerts = None
    for h in reversed(history):
        if h.get("date") != snapshot["date"]:
            prev_for_alerts = h
            break
    history = [h for h in history if h.get("date") != snapshot["date"]]

    traffic = fetch_ga4() or {"connected": False,
        "note": "Connecte GA4 (service-account) pour afficher les visites réelles."}

    hist_point = {k: snapshot[k] for k in
                  ("date", "goals", "news_items", "news_sources", "article_pages", "sitemap_urls")}
    if traffic.get("connected"):
        hist_point["users_30d"] = traffic.get("users_30d")
    history.append(hist_point)
    history = sorted(history, key=lambda h: h["date"])[-365:]
    HIST.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

    deltas, _prev = compute_deltas(snapshot, history)
    traffic_delta = compute_traffic_delta(traffic, history)
    alerts = detect_alerts(snapshot, deltas, traffic, traffic_delta, news, prev_for_alerts)

    seo = {
        "ga4": True,
        "search_console": False,
        "sitemap_urls": sitemap_urls,
        "news_prerendered": True,
        "canonical_clean_urls": True,
        "robots_has_sitemap": True,
    }

    data = {
        "generated_at": (os.environ.get("RUN_DATE") or datetime.now(timezone.utc).isoformat()),
        "snapshot": snapshot,
        "deltas": deltas,
        "traffic_delta": traffic_delta,
        "alerts": alerts,
        "history": history,
        "traffic": traffic,
        "seo": seo,
        "source_breakdown": source_breakdown,
        "lang_breakdown": lang_breakdown,
        "marketing_log": _load(PUB / "marketing_log.json", []) or [],
        "news_meta": {"generated_at": news.get("generated_at"),
                      "tagline": news.get("tagline"),
                      "feeds_fetched": nstats.get("feeds_fetched"),
                      "feeds_failed": nstats.get("feeds_failed"),
                      "published": nstats.get("published"),
                      "filtered_offtopic": nstats.get("filtered_offtopic")},
    }
    (PUB / "dashboard-data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"dashboard-data.json écrit · buts {goals} · news {len(items)} · "
          f"sources {len(sources)} · sitemap {sitemap_urls} · history {len(history)} pts · "
          f"alertes {len(alerts)} · "
          f"trafic {'GA4' if data['traffic'].get('connected') else 'à connecter'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
