**English** · [Français](README.fr.md)

# envoi-mail-programme

Queue an email and have it sent **at the set time**, from a server that stays on. Three small Python scripts (standard library only): no third-party service, your emails go out through the SMTP server of your own account.

## What is in the repository
- `schedule.py`: `add` (queue), `list` (see what is waiting), `cancel` (remove).
- `send_due.py`: run it every minute; it sends the emails whose time has passed, archives them in `sent/`, retries 5 times and then moves them to `failed/`. It also drops a copy into the account's Sent folder over IMAP if the account has one.
- `check_sent.py`: checks over IMAP that an email really went out.
- `accounts/exemple.json`: an account template. **Your real accounts (`accounts/*.json`) are ignored by git and must never be committed**: they contain an app password.

## Install
Requirements: Python 3.9 or later, cron.
```
git clone <this repository> && cd envoi-mail-programme
export MAIL_PROGRAMME_DIR=$HOME/.mail-programme     # working folder (queue, archives, accounts)
export MAIL_PROGRAMME_TZ=Europe/Paris               # time zone of the times you enter (UTC by default)
mkdir -p $MAIL_PROGRAMME_DIR/accounts
cp accounts/exemple.json $MAIL_PROGRAMME_DIR/accounts/perso.json && chmod 600 $MAIL_PROGRAMME_DIR/accounts/perso.json
# edit perso.json: address, server, port, app password
crontab -l 2>/dev/null; echo '* * * * * MAIL_PROGRAMME_DIR=$HOME/.mail-programme python3 /path/to/send_due.py >> $HOME/.mail-programme/cron.log 2>&1'
```
(add the line with `crontab -e`).

## Usage
```
python3 schedule.py add --account perso --to recipient@example.org --subject "Hello" \
  --html-file body.html --attach file1.pdf,file2.pdf --at "2027-01-15T08:00"
python3 schedule.py add --account perso --to recipient@example.org --subject "In one hour" --text "Hi" --in 1h
python3 schedule.py list
python3 schedule.py cancel <id>
python3 check_sent.py perso "Hello"       # how many "Hello" emails are in Sent
```
`smtp_security`: `ssl` (port 465), `starttls` (587) or `none` (local test server, no password).

## Security
- Passwords are stored in clear text in `accounts/*.json` (mode 600): use an app password, not your main password.
- `queue/`, `sent/`, `failed/`, `logs/` contain real emails: do not publish them (already in `.gitignore`).

## Licenses
Code: Apache 2.0 (`LICENSE`, `NOTICE`). Text: CC BY 4.0 (`LICENSE-docs`). No third-party dependency.
