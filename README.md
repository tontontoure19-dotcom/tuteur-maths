# Tuteur Maths — BEPC (Guinée)

Un tuteur de mathématiques par IA pour les élèves de 3e qui préparent le BEPC.
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

```bash
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8100
```

Puis ouvrez **http://localhost:8100** dans le navigateur.

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
│   │   ├── prompts.py   ← LE CŒUR : pédagogie du tuteur + programme 3e
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
- [ ] Rapport hebdomadaire au parent (page dédiée + envoi WhatsApp)
- [ ] Limite d'usage par abonnement (protéger la marge)
- [ ] Mise en ligne (Render) pour que les élèves y accèdent hors du PC
- [ ] Choisir le nom définitif (langue nationale)
- [ ] Test avec 5 élèves de 3e
