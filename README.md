# Bot Discord — Welcome + Tickets + Say + Social

Bot Discord en Python (discord.py 2.x, slash commands) avec :
- Message de bienvenue avec bannière (avatar + pseudo)
- Système de tickets par catégories (menu déroulant + salons privés)
- `/say` et `/sayedit`
- `/web`, `/twitch`, `/tiktok` (utilisables par tout le monde)

## 1. Créer l'application Discord

1. Va sur https://discord.com/developers/applications → **New Application**.
2. Onglet **Bot** → **Add Bot**, puis copie le **Token** (bouton "Reset Token" si besoin).
3. Toujours dans l'onglet **Bot**, active dans "Privileged Gateway Intents" :
   - **Server Members Intent** (obligatoire pour le message de bienvenue)
   - **Message Content Intent**
4. Onglet **OAuth2 → URL Generator** :
   - Scopes : `bot`, `applications.commands`
   - Permissions minimales conseillées : `Manage Channels`, `Manage Roles`, `Manage Messages`,
     `Send Messages`, `Embed Links`, `Attach Files`, `Read Message History`
     (ou plus simple : `Administrator` si c'est un serveur perso/test)
5. Ouvre l'URL générée et invite le bot sur ton serveur.

## 2. Installer le projet

```bash
cd discord-bot
python -m venv venv
source venv/bin/activate      # Windows : venv\Scripts\activate
pip install -r requirements.txt
```

Requiert **Python 3.10+**.

## 3. Configurer le token

Copie `.env.example` en `.env` et colle ton token :

```
DISCORD_TOKEN=ton_token_ici
```

## 4. Lancer le bot

```bash
python bot.py
```

Au premier lancement, les commandes slash sont synchronisées automatiquement
(ça peut prendre jusqu'à 1h pour apparaître globalement, mais c'est en général instantané).

## Commandes disponibles

### 👋 Bienvenue
- `/welcome salon <salon>` — définit le salon où seront postés les messages de bienvenue
- `/welcome test` — envoie un message de bienvenue test avec ta propre bannière

La bannière utilise ton visuel de marque (`assets/welcome_background.jpg`) tel quel, et ajoute
automatiquement une bande en bas avec l'avatar (photo de profil) et le pseudo du membre —
le logo et le texte d'origine ne sont jamais recouverts. Pour changer le visuel, remplace
simplement ce fichier par une autre image (même nom, ou change le chemin dans
`utils/banner.py`). Pour une police plus jolie sur le pseudo, dépose des fichiers `.ttf` dans
`assets/fonts/Poppins-Bold.ttf` et `assets/fonts/Poppins-Regular.ttf`
(sinon une police par défaut est utilisée automatiquement, aucune erreur).

### 🎫 Tickets
- `/ticket add <nom> <categorie> [emoji] [description] [message]` — crée un type de ticket, lié à
  une catégorie Discord existante (les salons de ticket seront créés dedans). Le paramètre
  `message` est le texte affiché dans l'embed du ticket à son ouverture (utilise `{membre}` pour
  mentionner la personne qui a ouvert le ticket, ex : `"Salut {membre}, décris ton problème !"`).
  Si tu ne mets rien, un texte par défaut est utilisé.
- `/ticket edit <nom> [categorie] [emoji] [description] [message]` — modifie un type de ticket
- `/ticket sup <nom>` — supprime un type de ticket
- `/ticket ping <nom> <role>` — définit le rôle notifié/ajouté quand ce type de ticket est ouvert
- `/ticket setup` — affiche le panneau (menu déroulant) permettant aux membres d'ouvrir un ticket

Chaque ticket ouvert affiche automatiquement le logo (`assets/ticket_logo.png`, extrait de ta
bannière) en haut à droite de l'embed (thumbnail), le texte personnalisé de la catégorie, et
mentionne le rôle configuré via `/ticket ping`.

⚠️ Après chaque `add`/`edit`/`sup`, relance `/ticket setup` pour mettre à jour le panneau affiché.
Chaque ticket créé contient un bouton **Fermer le ticket** qui supprime le salon après 5 secondes.

### 💬 Say
- `/say [salon] [role] [membre]` — ouvre une **fenêtre (modal)** pour composer le message :
  titre, contenu (texte multi-lignes avec **gras**, *italique*, liens, retours à la ligne...),
  une image (URL), et un bouton lien (URL + texte). `role`/`membre` (optionnels) ajoutent une
  vraie mention au message. Permission `Manage Messages` requise.
- `/sayedit <message_id> [role] [membre]` — rouvre la **même fenêtre pré-remplie** avec le
  contenu actuel du message (titre, texte, image, lien...), tu modifies ce que tu veux et ça
  met à jour le message en place. Si `role`/`membre` ne sont pas précisés, le ping existant est
  conservé.

⚠️ Comme demandé, `/sayedit` est accessible à **tout le monde** dès lors qu'on connaît l'ID du
message (pas de vérification de permission). Si tu préfères la restreindre, ajoute simplement
`@app_commands.checks.has_permissions(manage_messages=True)` au-dessus de la fonction `sayedit`
dans `cogs/say.py`.

**Limite Discord à connaître** : dans une fenêtre modale, seuls des champs texte sont possibles
(pas de vrai sélecteur de fichier/emoji natif). L'image se met donc via une **URL** (héberge-la
sur Discord en l'envoyant dans un salon puis en copiant son lien, ou utilise un hébergeur
d'images). Le ping, lui, passe par les paramètres `role`/`membre` de la commande (avant
l'ouverture de la fenêtre), pas par le texte — c'est plus fiable qu'un `@` tapé à la main.

### 🔗 Réseaux
- `/web <lien>` — poste un lien de site web
- `/twitch <lien>` — poste un lien Twitch
- `/tiktok <lien>` — poste un lien TikTok

Ces trois commandes sont utilisables par **tout le monde**, aucune permission requise.

## Structure du projet

```
discord-bot/
├── bot.py                 # point d'entrée
├── cogs/
│   ├── welcome.py
│   ├── tickets.py
│   ├── say.py
│   └── social.py
├── utils/
│   ├── storage.py          # stockage JSON simple (data/*.json)
│   └── banner.py            # génération de la bannière de bienvenue
├── data/                    # créé automatiquement (config par serveur)
├── assets/fonts/            # polices optionnelles pour la bannière
├── requirements.txt
└── .env.example
```

Les données (salon de bienvenue, catégories de tickets, messages `/say`, tickets ouverts)
sont stockées dans de simples fichiers JSON dans `data/`, donc aucune base de données à installer.
