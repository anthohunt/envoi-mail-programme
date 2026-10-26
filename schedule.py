#!/usr/bin/env python3
"""CLI to manage scheduled emails.
  add     enqueue a mail:  schedule.py add --account exemple --to x@y --subject "..." --html-file body.html --at "2026-06-29T08:00"
          or relative:     ... --in 30m | 2h | 1d
  list    show pending jobs (queue/) with their send time
  cancel  remove a pending job:  schedule.py cancel <id>
Times without timezone are read in the zone MAIL_PROGRAMME_TZ (default UTC)."""
import argparse, json, os, re, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(os.environ.get("MAIL_PROGRAMME_DIR", str(Path.home() / ".mail-programme")))
QUEUE = BASE / "queue"
ACCOUNTS = BASE / "accounts"
TZNAME = os.environ.get("MAIL_PROGRAMME_TZ", "UTC")
QUEUE.mkdir(parents=True, exist_ok=True)

def local_tz():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(TZNAME)
    except Exception:
        return timezone.utc

def parse_when(at, rel):
    if rel:
        m = re.fullmatch(r"(\d+)\s*([mhd])", rel.strip())
        if not m:
            sys.exit("--in must look like 30m, 2h, 1d")
        n, unit = int(m.group(1)), m.group(2)
        delta = {"m": timedelta(minutes=n), "h": timedelta(hours=n), "d": timedelta(days=n)}[unit]
        return datetime.now(timezone.utc) + delta
    dt = datetime.fromisoformat(at)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=local_tz())
    return dt.astimezone(timezone.utc)

def cmd_add(a):
    if not (ACCOUNTS / f"{a.account}.json").exists():
        sys.exit(f"account '{a.account}' not configured in {ACCOUNTS}")
    when = parse_when(a.at, getattr(a, "in"))
    html = a.html
    if a.html_file:
        html = Path(a.html_file).read_text(encoding="utf-8")
    split = lambda v: [x.strip() for x in v.split(",") if x.strip()] if v else []
    now = datetime.now(timezone.utc)
    jid = now.strftime("%Y%m%dT%H%M%S") + "-" + os.urandom(3).hex()
    job = {
        "id": jid, "account": a.account,
        "to": split(a.to), "cc": split(a.cc), "bcc": split(a.bcc),
        "subject": a.subject or "", "html": html, "text": a.text,
        "attachments": split(a.attach),
        "send_at": when.isoformat(), "created_at": now.isoformat(), "attempts": 0,
    }
    if a.from_addr: job["from"] = a.from_addr
    out = QUEUE / f"{jid}.json"
    json.dump(job, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    local = when.astimezone(local_tz())
    print(f"Scheduled {jid}  ->  {job['to']}  at {local.strftime('%Y-%m-%d %H:%M %Z')} ({TZNAME}) / {when.isoformat()} UTC")

def cmd_list(a):
    rows = []
    for jp in sorted(QUEUE.glob("*.json")):
        try:
            j = json.load(open(jp, encoding="utf-8"))
            w = datetime.fromisoformat(j["send_at"]).astimezone(local_tz())
            rows.append((w, j["id"], j["account"], j.get("to"), j.get("subject", "")[:40]))
        except Exception as e:
            rows.append((None, jp.name, "?", "?", f"unreadable: {e}"))
    if not rows:
        print("(no pending scheduled mail)"); return
    for w, jid, acct, to, subj in sorted(rows, key=lambda r: (r[0] is None, r[0])):
        wt = w.strftime("%Y-%m-%d %H:%M %Z") if w else "??"
        print(f"{wt}  [{acct}]  {to}  | {subj}  ({jid})")

def cmd_cancel(a):
    p = QUEUE / (a.id if a.id.endswith(".json") else f"{a.id}.json")
    if not p.exists():
        sys.exit(f"no pending job '{a.id}'")
    p.unlink()
    print(f"cancelled {a.id}")

ap = argparse.ArgumentParser(description="Scheduled email manager")
sub = ap.add_subparsers(dest="cmd", required=True)
pa = sub.add_parser("add"); pa.set_defaults(fn=cmd_add)
pa.add_argument("--account", required=True)
pa.add_argument("--from", dest="from_addr", help="override From (display name + addr)")
pa.add_argument("--to", required=True); pa.add_argument("--cc"); pa.add_argument("--bcc")
pa.add_argument("--subject"); pa.add_argument("--html"); pa.add_argument("--html-file")
pa.add_argument("--text"); pa.add_argument("--attach")
g = pa.add_mutually_exclusive_group(required=True)
g.add_argument("--at", help="YYYY-MM-DDTHH:MM (zone MAIL_PROGRAMME_TZ if no tz)")
g.add_argument("--in", help="relative: 30m | 2h | 1d")
pl = sub.add_parser("list"); pl.set_defaults(fn=cmd_list)
pc = sub.add_parser("cancel"); pc.set_defaults(fn=cmd_cancel); pc.add_argument("id")
args = ap.parse_args()
args.fn(args)
