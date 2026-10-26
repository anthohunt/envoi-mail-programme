#!/usr/bin/env python3
"""Scheduled-mail sender. Run every minute by cron (see README).
Scans queue/*.json, sends any whose send_at <= now (UTC), archives to sent/ or failed/.
If the account has an IMAP setting (imap_server/sent_folder), a COPY of the mail is
appended to the account's Sent folder, so it shows up in your mail client."""
import json, os, smtplib, ssl, sys, traceback, imaplib, time
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import format_datetime
from pathlib import Path

BASE = Path(os.environ.get("MAIL_PROGRAMME_DIR", str(Path.home() / ".mail-programme")))
ACCOUNTS = BASE / "accounts"
QUEUE = BASE / "queue"
SENT = BASE / "sent"
FAILED = BASE / "failed"
LOG = BASE / "logs" / "send.log"
MAX_ATTEMPTS = 5

def log(msg):
    ts = datetime.now(timezone.utc).isoformat()
    line = f"[{ts}] {msg}"
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)

def load_account(label):
    p = ACCOUNTS / f"{label}.json"
    if not p.exists():
        raise FileNotFoundError(f"account '{label}' not configured ({p})")
    return json.load(open(p, encoding="utf-8"))

def build_message(job, acct):
    msg = EmailMessage()
    msg["Date"] = format_datetime(datetime.now(timezone.utc))
    msg["From"] = job.get("from") or acct["from"]
    to = job.get("to") or []
    cc = job.get("cc") or []
    bcc = job.get("bcc") or []
    if isinstance(to, str): to = [to]
    if isinstance(cc, str): cc = [cc]
    if isinstance(bcc, str): bcc = [bcc]
    if not to:
        raise ValueError("no recipient (to)")
    msg["To"] = ", ".join(to)
    if cc: msg["Cc"] = ", ".join(cc)
    if bcc: msg["Bcc"] = ", ".join(bcc)
    msg["Subject"] = job.get("subject", "")
    text = job.get("text") or "This message requires an HTML-capable mail client."
    msg.set_content(text)
    html = job.get("html")
    if html:
        msg.add_alternative(html, subtype="html")
    for ap in job.get("attachments", []) or []:
        p = Path(ap)
        data = p.read_bytes()
        import mimetypes
        ctype, _ = mimetypes.guess_type(str(p))
        maintype, subtype = (ctype.split("/", 1) if ctype else ("application", "octet-stream"))
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=p.name)
    return msg

def append_to_sent(msg, acct):
    """Depose une copie dans le dossier Envoyes via IMAP APPEND. Best-effort:
    le mail est deja parti, un echec ici n'annule pas l'envoi (juste logge)."""
    host = acct.get("imap_server")
    if not host:
        return None  # no IMAP setting -> assume the provider files sent mail by itself
    port = int(acct.get("imap_port", 993))
    folder = acct.get("sent_folder", "Sent")
    sec = acct.get("imap_security", "ssl").lower()
    if sec == "ssl":
        M = imaplib.IMAP4_SSL(host, port, ssl_context=ssl.create_default_context())
    else:
        M = imaplib.IMAP4(host, port)
        M.starttls(ssl.create_default_context())
    try:
        M.login(acct["username"], acct["password"])
        M.append(folder, "\\Seen", imaplib.Time2Internaldate(time.time()), msg.as_bytes())
    finally:
        try: M.logout()
        except Exception: pass
    return folder

def send(job, acct):
    msg = build_message(job, acct)
    sec = acct.get("smtp_security", "ssl").lower()
    host, port = acct["smtp_server"], int(acct["smtp_port"])
    if sec == "none":  # serveur local de test, sans chiffrement ni authentification
        with smtplib.SMTP(host, port) as s:
            s.send_message(msg)
    elif sec == "ssl":
        with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context()) as s:
            s.login(acct["username"], acct["password"])
            s.send_message(msg)
    else:  # starttls
        with smtplib.SMTP(host, port) as s:
            s.ehlo(); s.starttls(context=ssl.create_default_context()); s.ehlo()
            s.login(acct["username"], acct["password"])
            s.send_message(msg)
    # copie dans Envoyes (best-effort)
    try:
        f = append_to_sent(msg, acct)
        if f:
            log(f"FILED copy -> {f} ({acct.get('label','?')})")
    except Exception as e:
        log(f"WARN append-to-sent failed ({acct.get('label','?')}): {type(e).__name__}: {e}")

def main():
    for d in (QUEUE, SENT, FAILED, LOG.parent):
        d.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    jobs = sorted(QUEUE.glob("*.json"))
    for jp in jobs:
        try:
            job = json.load(open(jp, encoding="utf-8"))
        except Exception as e:
            log(f"SKIP unreadable {jp.name}: {e}")
            continue
        try:
            send_at = datetime.fromisoformat(job["send_at"])
            if send_at.tzinfo is None:
                send_at = send_at.replace(tzinfo=timezone.utc)
        except Exception as e:
            log(f"BAD send_at in {jp.name}: {e}")
            continue
        if send_at > now:
            continue  # not due yet
        # claim atomically
        claimed = jp.with_suffix(".json.processing")
        try:
            jp.rename(claimed)
        except FileNotFoundError:
            continue
        try:
            acct = load_account(job["account"])
            send(job, acct)
            job["sent_at"] = now.isoformat()
            out = SENT / jp.name
            json.dump(job, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
            claimed.unlink()
            log(f"SENT {jp.name} -> {job.get('to')} via {job['account']} (subj: {job.get('subject','')[:50]})")
        except Exception as e:
            job["attempts"] = job.get("attempts", 0) + 1
            job["last_error"] = f"{type(e).__name__}: {e}"
            if job["attempts"] >= MAX_ATTEMPTS:
                out = FAILED / jp.name
                json.dump(job, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
                claimed.unlink()
                log(f"FAILED (giving up after {job['attempts']}) {jp.name}: {job['last_error']}")
            else:
                json.dump(job, open(claimed.with_suffix(""), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
                claimed.unlink()
                log(f"RETRY {jp.name} attempt {job['attempts']}: {job['last_error']}")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        log("FATAL:\n" + traceback.format_exc())
        sys.exit(1)
