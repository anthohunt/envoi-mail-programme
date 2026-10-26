#!/usr/bin/env python3
"""Count mails in an account's Sent folder whose subject contains MARK.
Usage: check_sent.py ACCOUNT MARK   (ACCOUNT = name of accounts/ACCOUNT.json)
Proves by IMAP that a scheduled mail really left."""
import imaplib, json, os, ssl, sys
from pathlib import Path
if len(sys.argv) != 3:
    sys.exit(__doc__)
base = Path(os.environ.get("MAIL_PROGRAMME_DIR", str(Path.home() / ".mail-programme")))
a = json.load(open(base / "accounts" / f"{sys.argv[1]}.json", encoding="utf-8"))
M = imaplib.IMAP4_SSL(a["imap_server"], a.get("imap_port", 993), ssl_context=ssl.create_default_context())
M.login(a["username"], a["password"])
M.select(a.get("sent_folder", "Sent"), readonly=True)
t, d = M.search(None, "SUBJECT", sys.argv[2])
print(len(d[0].split() if d and d[0] else []))
M.logout()
