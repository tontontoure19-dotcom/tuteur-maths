# Tuteur Maths — BEPC (Guinée)

Un tuteur de mathématiques par IA pour les élèves guinéens qui préparent le
**BEPC** (10e année) ou le **BAC** (Terminale).
**Il ne donne jamais la réponse** : il fait chercher l'élève, étape par étape.

Porteur : Tonton Touré / MansaSoft — Conakry

---

## Pourquoi ce produit

Les élèves utilisent déjà l'IA gratuite pour faire leurs devoirs (photo → réponse).
Résultat : bonne note au contrôle, et **41 % d'échec au BEPC** quand même
(58,96 % de réussite en 2026, sur 146 906 candidats).

Le client n'est donc pas l'élève — c'est **le parent**, qui veut que son enfant
réussisse en juin. Trois choses qu'une IA gratuite ne fait pas :

1. Elle connaît le **programme guinéen** et le format réel de l'épreuve
2. Elle **refuse de donner la réponse** et fait travailler l'élève
3. Elle **rend compte au parent** (temps de travail, points faibles, progrès)

Prix de référence : un répétiteur à domicile coûte 500 000 à 1 000 000 GNF/mois.

---

## Démarrer (3 étapes)

### 1. Mettre votre clé API

```bash
cd backend
copy .env.example .env
```

Ouvrez `backend\.env` avec le Bloc-notes et remplacez la ligne par votre vraie
clé (obtenue sur console.anthropic.com → API Keys) :

```
ANTHROPIC_API_KEY=sk-ant-votre-vraie-cle
```

⚠️ Ce fichier `.env` n'est jamais envoyé sur GitHub — votre clé reste privée.

### 2. Installer (une seule fois)

```bash
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. Lancer

**Double-cliquez sur `DEMARRER.bat`** (dans le dossier `tuteur-bepc`).
Une fenêtre noire s'ouvre — c'est normal, c'est le serveur. Chrome s'ouvre
tout seul sur l'application.

⚠️ **Ne fermez pas la fenêtre noire** tant que vous utilisez l'application :
c'est elle qui fait tourner le tuteur. Pour arrêter, fermez-la.

Deux adresses :

| Pour | Adresse |
|---|---|
| L'élève | http://localhost:8100 |
| Le parent | http://localhost:8100/parent.html |

> Si le tuteur affiche « Clé API absente », c'est que l'étape 1 n'est pas faite.

---

## Installer sur un téléphone (comme une application)

1. Ouvrir le lien du site dans **Chrome** sur le téléphone
2. Menu **⋮** → **« Ajouter à l'écran d'accueil »**
3. Une icône apparaît sur le téléphone — elle s'ouvre en plein écran, sans
   barre de navigateur. Pour l'élève, **c'est une application.**

Pas de Play Store, pas de fichier à télécharger, et les corrections sont
disponibles pour tout le monde immédiatement.

---

## Structure

```
tuteur-bepc/
├── backend/
│   ├── app/
│   │   ├── prompts.py   ← LE CŒUR : pédagogie du tuteur + programme 10e année
│   │   └── main.py      ← l'API (parle à Claude, garde la clé côté serveur)
│   ├── sessions/        ← conversations des élèves (jamais versionnées)
│   └── .env             ← votre clé API (jamais versionnée)
└── web/                 ← l'interface (« l'application »)
```

**Le fichier le plus important est `backend/app/prompts.py`.** C'est lui qui
définit comment le tuteur enseigne et refuse de donner les réponses. C'est là
qu'on intégrera les sujets d'annales du BEPC.

---

## Suivre l'activité d'un élève

```
http://localhost:8100/api/rapport/fatoumata
```

Retourne le nombre d'échanges, de questions posées et de photos envoyées.
C'est la base du futur rapport hebdomadaire au parent.

---

## Modèle économique visé

| | Montant |
|---|---|
| Prix pour le parent | ~75 000 GNF/mois |
| Coût de l'IA (estimation) | ~30 000 GNF/élève/mois |
| **Marge** | **~45 000 GNF/élève/mois** |

À valider avec les coûts réels mesurés pendant le test.

---

## Ce qui reste à faire

- [ ] Intégrer les vrais sujets d'annales BEPC dans `prompts.py`
- [x] Suivi de niveau et recommandations (page parent)
- [ ] Envoi automatique du bilan par WhatsApp chaque semaine
- [ ] Limite d'usage par abonnement (protéger la marge)
- [ ] Mise en ligne (Render) pour que les élèves y accèdent hors du PC
- [ ] Choisir le nom définitif (langue nationale)
- [x] Deux niveaux : 10e année (BEPC) et Terminale (BAC)
- [x] Plusieurs élèves sur un même téléphone (profils séparés)
- [ ] Système de codes d'accès (un code = un abonnement)
- [ ] Paiement hebdomadaire (Orange Money / MTN)
- [ ] Test avec des candidats BEPC et BAC

---

## Suivi de niveau (page parent)

Le parent ouvre (sans rien après, la liste des élèves s'affiche) :

```
http://localhost:8100/parent.html
```

Il y trouve, généré automatiquement à partir des conversations :

- **En résumé** — 3-4 phrases en français simple, sans jargon
- **Persévérance** — s'accroche-t-il face à la difficulté, ou abandonne-t-il vite ?
- **Chapitres travaillés** — chacun classé *acquis* / *en cours* / *difficulté*
- **Ce qui va bien** — réussites concrètes
- **À retravailler** — difficultés précises
- **Conseils pour cette semaine** — actions faisables en 7 jours

Le bilan n'est recalculé qu'après **20 nouveaux échanges** de l'élève. Entre
deux recalculs on ressert le précédent : la page reste consultable autant qu'on
veut sans rien coûter, au prix d'un bilan parfois un peu moins frais.

---

## Ma progression (écran élève)

Bouton 📈 dans l'en-tête de l'application. L'élève y voit **son propre travail** :

- **Trois compteurs** — questions posées, chapitres travaillés, chapitres acquis
- **Où tu en es** — 2-3 phrases qui le tutoient et nomment un progrès précis
  (« au début tu ne savais pas quel théorème utiliser, à la fin tu expliquais
  toi-même pourquoi Pythagore marchait ici »)
- **Tes chapitres** — les mêmes pastilles vert / orange / rouge que le parent
- **Ta prochaine étape** — une seule chose concrète à travailler ensuite

C'est ce qui donne envie de revenir le lendemain. Il compte double pour l'élève
qui se finance seul sa formation : personne d'autre ne regarde son travail.

Ces deux textes sont produits **dans le même appel** que le bilan du parent :
voir sa progression ne coûte donc rien de plus.

### Coûts mesurés en réel

| | Coût |
|---|---|
| Une question posée au tuteur | ~50-75 GNF |
| Une séance complète (7 questions) | ~340 GNF |
| Un bilan (parent + progression élève) | ~500 GNF, au plus tous les 20 échanges |
| **Un élève actif sur un mois** | **~5 000 à 15 000 GNF** |

À comparer aux 75 000 GNF/mois d'abonnement visés.

---

## En ligne

L'application tourne sur : **https://tuteur-maths.onrender.com**

| Pour | Adresse |
|---|---|
| L'élève | https://tuteur-maths.onrender.com |
| Le parent | https://tuteur-maths.onrender.com/parent.html |

Chaque testeur saisit **son** code d'accès une seule fois.

---

## Les codes d'accès

Un code par testeur, jamais un code partagé : c'est ce qui permet de couper
l'accès à une seule personne, et de voir si un code circule.

**Fabriquer les codes** — double-cliquez sur `CODES.bat`. Il crée 5 codes
`BEPC-…` et 5 codes `BAC-…` dans `backend/codes.txt` (fichier privé, jamais
envoyé sur GitHub) et l'ouvre dans le Bloc-notes. Écrivez à côté de chaque
code le nom de la personne à qui vous l'avez donné.

Pour un autre nombre : `CODES.bat BEPC BEPC BAC` fabrique 3 codes.

**Les activer** — copiez la dernière ligne du fichier (tous les codes séparés
par des virgules) dans Render → *Environment* → `CODE_ACCES`.

**Ce qu'un code peut consommer** — l'application garde le code enregistré
dans l'appareil, comme WhatsApp : on ne le redemande pas à chaque ouverture,
sinon les élèves abandonnent. Le budget est donc protégé côté serveur :

| Limite | Défaut | Variable Render |
|---|---|---|
| Élèves par code | 2 (frères et sœurs) | `MAX_ELEVES_PAR_CODE` |
| Questions par jour et par code | 40 | `MAX_QUESTIONS_PAR_JOUR` |

Le 3ᵉ prénom sur un code est refusé, en nommant les deux élèves déjà en
place. Au-delà du plafond du jour, le tuteur invite à revenir demain.

**Surveiller** — https://tuteur-maths.onrender.com/api/codes?code=VOTRE_CODE
montre, pour chaque code, les prénoms qui l'ont utilisé. Un code avec
plusieurs prénoms (`"partage": true`) a été transmis à d'autres : retirez-le
de `CODE_ACCES` dans Render, les autres testeurs ne sont pas dérangés.

---

## Mise en ligne (Render)

Le fichier `render.yaml` décrit tout le déploiement.

1. Pousser le dépôt sur GitHub
2. Sur [render.com](https://render.com) : **New +** → **Blueprint** → sélectionner le dépôt
3. Renseigner les deux variables demandées :

| Variable | Valeur |
|---|---|
| `ANTHROPIC_API_KEY` | Votre clé (celle du fichier `.env` local) |
| `CODE_ACCES` | Les codes fabriqués par `CODES.bat`, séparés par des virgules |

⚠️ **`CODE_ACCES` est obligatoire.** Sans lui, n'importe quel visiteur du site
poserait des questions facturées sur votre clé.

Vous donnez ensuite **un code différent à chaque testeur**, avec le lien.
Chacun le saisit une seule fois.

### Plan et conservation des données

Le service tourne sur le plan **starter** (~7 $/mois) avec un disque de 1 Go.
C'est ce disque qui conserve les conversations et les bilans entre deux
redémarrages — sans lui, le suivi de niveau serait remis à zéro
régulièrement, or c'est précisément ce que les parents doivent voir.

Les données vivent dans `/var/data` (variable `DATA_DIR`). En local, sans
cette variable, elles restent dans `backend/sessions` et `backend/bilans`.
