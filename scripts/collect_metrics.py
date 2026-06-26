#!/usr/bin/env python3
"""collect_metrics.py — agrège les métriques du site dans public/dashboard-data.json
et tient un historique (public/metrics_history.json) pour les courbes d'évolution.

Données disponibles SANS auth externe : progression des buts (le hook), vélocité
de contenu (news, sources), pages indexables (sitemap), fraîcheur.
TRAFIC réel : branché sur GA4 si les variables d'env sont présentes
(GA4_PROPERTY_ID + GOOGLE_APPLICATION_CREDENTIALS), sinon état "à connecter".

Lancé par le workflow (quotidien) → régénère le JSON → déployé → le dashboard
se met à jour tout seul.
"""
import json, os, re, glob
from pathlib import Path
from datetime import datetime, timezone

PUB = Path(__file__).resolve().parent.parent / "public"
HIST = Path(__file__).resolve().parent / "metrics_history.json"

def _load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default

def _now():
    # le workflow passe la date via env (les scripts n'ont pas d'horloge live ici)
    return os.environ.get("RUN_DATE") or datetime.now(timezone.utc).strftime("%Y-%m-%d")

def fetch_ga4():
    """Trafic GA4 (30 j) si service-account configuré, sinon None (état à connecter)."""
    prop = os.environ.get("GA4_PROPERTY_ID", "").strip()
    if not prop or not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        return None
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            DateRange, Dimension, Metric, RunReportRequest, OrderBy)
        cli = BetaAnalyticsDataClient()
        # Visites par jour (30 j)
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
        # Top pages + sources
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

def main():
    stats = _load(PUB / "stats.json", {}) or {}
    news = _load(PUB / "news.json", {}) or {}
    items = news.get("items", [])
    nstats = news.get("stats", {}) or {}

    goals = stats.get("goals", 0)
    target = stats.get("target", 1000)
    sources = sorted({(it.get("primary_source") or {}).get("name") for it in items if it.get("primary_source")})
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

    # ----- historique (1 point/jour, garde 365) -----
    history = _load(HIST, []) or []
    history = [h for h in history if h.get("date") != snapshot["date"]]
    history.append({k: snapshot[k] for k in
                    ("date", "goals", "news_items", "news_sources", "article_pages", "sitemap_urls")})
    history = sorted(history, key=lambda h: h["date"])[-365:]
    HIST.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

    # ----- SEO health (signaux que l'on peut calculer) -----
    seo = {
        "ga4": True,
        "search_console": False,            # à vérifier/poser une balise de vérif
        "sitemap_urls": sitemap_urls,
        "news_prerendered": True,           # cartes news dans le HTML statique
        "canonical_clean_urls": True,
        "robots_has_sitemap": True,
    }

    data = {
        "generated_at": (os.environ.get("RUN_DATE") or datetime.now(timezone.utc).isoformat()),
        "snapshot": snapshot,
        "history": history,
        "traffic": fetch_ga4() or {"connected": False,
            "note": "Connecte GA4 (service-account) pour afficher les visites réelles."},
        "seo": seo,
        "marketing_log": _load(PUB / "marketing_log.json", []) or [],
        "news_meta": {"generated_at": news.get("generated_at"),
                      "tagline": news.get("tagline"),
                      "filtered_offtopic": nstats.get("filtered_offtopic")},
    }
    (PUB / "dashboard-data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"dashboard-data.json écrit · buts {goals} · news {len(items)} · "
          f"sources {len(sources)} · sitemap {sitemap_urls} · history {len(history)} pts · "
          f"trafic {'GA4' if data['traffic'].get('connected') else 'à connecter'}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
