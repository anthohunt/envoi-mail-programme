# envoi-mail-programme

Mettre un mail en file d'attente et le faire partir **à l'heure dite**, depuis un serveur qui reste allumé. Trois petits scripts Python (bibliothèque standard seulement) : pas de service tiers, vos mails partent par le serveur SMTP de votre propre compte.

## Ce que contient le dépôt
• `schedule.py` : `add` (mettre en file), `list` (voir ce qui attend), `cancel` (retirer).
• `send_due.py` : à lancer chaque minute ; envoie les mails dont l'heure est passée, les archive dans `sent/`, réessaie 5 fois puis range dans `failed/`. Dépose aussi une copie dans le dossier « Envoyés » du compte par IMAP si le compte en a un.
• `check_sent.py` : vérifie par IMAP qu'un mail est bien parti.
• `accounts/exemple.json` : modèle d'un compte. **Vos vrais comptes (`accounts/*.json`) sont ignorés par git et ne doivent jamais être commités** : ils contiennent un mot de passe d'application.

## Installer
Prérequis : Python 3.9 ou plus, cron.
```
git clone <ce dépôt> && cd envoi-mail-programme
export MAIL_PROGRAMME_DIR=$HOME/.mail-programme     # dossier de travail (file, archives, comptes)
export MAIL_PROGRAMME_TZ=Europe/Paris               # fuseau des heures saisies (UTC par défaut)
mkdir -p $MAIL_PROGRAMME_DIR/accounts
cp accounts/exemple.json $MAIL_PROGRAMME_DIR/accounts/perso.json && chmod 600 $MAIL_PROGRAMME_DIR/accounts/perso.json
# éditez perso.json : adresse, serveur, port, mot de passe d'application
crontab -l 2>/dev/null; echo '* * * * * MAIL_PROGRAMME_DIR=$HOME/.mail-programme python3 /chemin/vers/send_due.py >> $HOME/.mail-programme/cron.log 2>&1'
```
(ajoutez la ligne avec `crontab -e`).

## Utiliser
```
python3 schedule.py add --account perso --to destinataire@example.org --subject "Bonjour" \
  --html-file corps.html --attach piece1.pdf,piece2.pdf --at "2027-01-15T08:00"
python3 schedule.py add --account perso --to destinataire@example.org --subject "Dans une heure" --text "Salut" --in 1h
python3 schedule.py list
python3 schedule.py cancel <id>
python3 check_sent.py perso "Bonjour"       # combien de mails « Bonjour » dans les Envoyés
```
`smtp_security` : `ssl` (port 465), `starttls` (587) ou `none` (serveur local de test, sans mot de passe).

## Sécurité
• Les mots de passe sont en clair dans `accounts/*.json` (droits 600) : utilisez un mot de passe d'application, pas votre mot de passe principal.
• `queue/`, `sent/`, `failed/`, `logs/` contiennent de vrais mails : ne les publiez pas (déjà dans `.gitignore`).

## Licences
Code : Apache 2.0 (`LICENSE`, `NOTICE`). Texte : CC BY 4.0 (`LICENSE-docs`). Aucune dépendance tierce.
