#!/usr/bin/env python3
"""Daily deep-quote Instagram bot.

  python main.py post             # generate, render, commit-ready image, publish
  python main.py post --dry-run   # generate + render only (no Instagram call)
  python main.py publish          # publish an already-rendered posts/<today>.jpg
  python main.py insights         # weekly performance report -> reports/
  python main.py refresh-token    # print a refreshed long-lived token
"""
import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from caption import build_caption  # noqa: E402
from generate import generate  # noqa: E402
from render import render  # noqa: E402

HISTORY = ROOT / "data" / "history.json"
PENDING = ROOT / "data" / "pending.json"
IST = timezone(timedelta(hours=5, minutes=30))


def load_cfg():
    return yaml.safe_load((ROOT / "config.yaml").read_text())


def load_history():
    return json.loads(HISTORY.read_text()) if HISTORY.exists() else []


def save_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False))


def cmd_prepare(cfg):
    """Generate quote + image + caption, and stage them in data/pending.json."""
    history = load_history()
    today = datetime.now(IST).date().isoformat()
    if any(h["date"] == today and h.get("media_id") for h in history):
        print(f"Already posted for {today}; nothing to do.")
        return None
    q = generate(cfg, history)
    img = ROOT / "posts" / f"{today}.jpg"
    render(q["quote"], img, cfg, cfg["page_handle"])
    cap = build_caption(q, cfg, seed=today)
    pending = {"date": today, **q, "caption": cap, "image": str(img.relative_to(ROOT))}
    save_json(PENDING, pending)
    print(f"Prepared {img.name}\n---\n{cap}\n---")
    return pending


def cmd_publish(cfg):
    """Publish data/pending.json. The image must already be reachable at a public URL."""
    from instagram import IG

    if not PENDING.exists():
        print("No pending post.")
        return
    p = json.loads(PENDING.read_text())
    base = os.environ.get("PUBLIC_IMAGE_BASE_URL")
    if not base:
        sys.exit("PUBLIC_IMAGE_BASE_URL not set (e.g. https://raw.githubusercontent.com/<user>/<repo>/main)")
    url = f"{base.rstrip('/')}/{p['image']}"
    media_id = IG().publish_image(url, p["caption"])
    p["media_id"] = media_id
    p["posted_at"] = datetime.now(IST).isoformat(timespec="minutes")
    history = load_history()
    history.append({k: p.get(k) for k in ("date", "quote", "theme", "source", "media_id", "posted_at")})
    save_json(HISTORY, history)
    PENDING.unlink()
    print(f"Published media {media_id}")


def cmd_insights(cfg):
    from instagram import IG

    ig = IG()
    media = ig.recent_media(limit=30)
    rows = []
    for m in media:
        ins = ig.media_insights(m["id"])
        ts = datetime.fromisoformat(m["timestamp"].replace("+0000", "+00:00")).astimezone(IST)
        rows.append({
            "date": ts.strftime("%Y-%m-%d"), "hour": ts.hour,
            "quote": (m.get("caption") or "").split("\n")[0][:70],
            "reach": ins.get("reach", 0), "views": ins.get("views", 0),
            "likes": m.get("like_count", 0), "comments": m.get("comments_count", 0),
            "saves": ins.get("saved", 0), "shares": ins.get("shares", 0),
            "link": m.get("permalink", ""),
        })
    acct = ig.account_insights(7)

    week_ago = (datetime.now(IST) - timedelta(days=7)).strftime("%Y-%m-%d")
    week = [r for r in rows if r["date"] >= week_ago]
    by_hour = defaultdict(list)
    for r in rows:
        by_hour[r["hour"]].append(r["reach"])
    best_hours = sorted(by_hour, key=lambda h: -sum(by_hour[h]) / len(by_hour[h]))[:3]
    top = sorted(rows, key=lambda r: -(r["saves"] * 3 + r["shares"] * 3 + r["comments"] * 2 + r["likes"]))[:5]

    def table(rs):
        out = ["| Date | Quote | Reach | Likes | Comments | Saves | Shares |",
               "|---|---|---:|---:|---:|---:|---:|"]
        out += [f"| {r['date']} | [{r['quote']}]({r['link']}) | {r['reach']} | {r['likes']} | "
                f"{r['comments']} | {r['saves']} | {r['shares']} |" for r in rs]
        return "\n".join(out)

    total = lambda k: sum(r[k] for r in week)  # noqa: E731
    md = f"""# Weekly report — {datetime.now(IST):%d %b %Y}

**Last 7 days:** {len(week)} posts · reach {total('reach')} · likes {total('likes')} · comments {total('comments')} · saves {total('saves')} · shares {total('shares')}
**Account reach (7d):** {acct.get('reach', 'n/a')} · **New followers (7d):** {acct.get('follower_count', 'n/a')}

**Best posting hours so far (IST, by avg reach):** {', '.join(f'{h}:00' for h in best_hours) or 'not enough data'}
*If the best hour differs from the schedule, change the cron in `.github/workflows/daily-post.yml`.*

## Top posts (weighted by saves, shares, comments)
{table(top)}

## This week
{table(week)}
"""
    out = ROOT / "reports" / f"{date.today().isoformat()}.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(md)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        Path(summary).write_text(md)
    print(md)


def cmd_refresh():
    from instagram import IG

    res = IG.refresh_token(os.environ["IG_ACCESS_TOKEN"])
    # Printed to a file (not logs) so the workflow can store it as a secret.
    Path(os.environ.get("TOKEN_OUT", "new_token.txt")).write_text(res["access_token"])
    print(f"Token refreshed; valid for {int(res['expires_in']) // 86400} days.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["post", "prepare", "publish", "insights", "refresh-token"])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    cfg = load_cfg()
    if a.command == "prepare" or (a.command == "post" and a.dry_run):
        cmd_prepare(cfg)
    elif a.command == "post":
        if cmd_prepare(cfg):
            cmd_publish(cfg)
    elif a.command == "publish":
        cmd_publish(cfg)
    elif a.command == "insights":
        cmd_insights(cfg)
    elif a.command == "refresh-token":
        cmd_refresh()


if __name__ == "__main__":
    main()
