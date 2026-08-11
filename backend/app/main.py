"""API du tuteur IA — BEPC Maths (Guinée).

Le navigateur de l'élève parle à cette API, qui parle à Claude.
La clé API reste ici, côté serveur : elle n'est jamais exposée à l'élève.
"""
import base64
import binascii
import hashlib
import json
import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import bilan as module_bilan
from .prompts import NIVEAU_DEFAUT, NIVEAUX, construire_systeme

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

# Claude Opus 5 : le meilleur modèle, pour la meilleure qualité pédagogique.
# L'effort "medium" garde des réponses rapides pour une conversation.
MODELE = "claude-opus-5"
EFFORT = "medium"

# Toutes les données durables vivent sous un seul dossier : en ligne, c'est
# le disque persistant de Render (DATA_DIR), qui survit aux redémarrages.
DOSSIER_DONNEES = Path(os.getenv("DATA_DIR") or BASE_DIR)
DOSSIER_SESSIONS = DOSSIER_DONNEES / "sessions"
DOSSIER_BILANS = DOSSIER_DONNEES / "bilans"
DOSSIER_PHOTOS = DOSSIER_DONNEES / "photos"
DOSSIER_SESSIONS.mkdir(parents=True, exist_ok=True)
DOSSIER_BILANS.mkdir(parents=True, exist_ok=True)
DOSSIER_PHOTOS.mkdir(parents=True, exist_ok=True)

# Les photos sont déjà réduites par le téléphone (1300 px, JPEG) : au-delà,
# c'est un envoi anormal, on ne le conserve pas.
MAX_PHOTO_OCTETS = 3 * 1024 * 1024


def _nom_normalise(eleve: str) -> str:
    """« Touré », « toure », « TOURÉ » doivent désigner le même élève.

    Sans cette normalisation, un accent oublié en tapant son prénom fait
    repartir l'élève de zéro, avec un historique vide.
    """
    sans_accent = unicodedata.normalize("NFD", eleve.lower().strip())
    sans_accent = "".join(c for c in sans_accent if unicodedata.category(c) != "Mn")
    propre = "".join(c for c in sans_accent if c.isalnum() or c in " -_")
    return propre.replace(" ", "_")[:40] or "eleve"


def _identifiant(eleve: str, code: str | None = None) -> str:
    """Identifie un élève par son abonnement (le code) ET son prénom.

    C'est ce qui permet à l'élève de retrouver son travail sur n'importe
    quel appareil — téléphone puis ordinateur — tout en gardant des
    historiques séparés quand deux personnes se partagent un téléphone.
    Le code n'apparaît jamais en clair : seule son empreinte est utilisée.
    """
    nom = _nom_normalise(eleve)
    if not code:
        return nom
    empreinte = hashlib.sha256(code.encode("utf-8")).hexdigest()[:10]
    return f"{empreinte}_{nom}"


def _identifiant_ancien(eleve: str) -> str:
    """Ancien nommage, avant que l'historique suive l'abonnement."""
    propre = "".join(c for c in eleve.lower().strip() if c.isalnum() or c in " -_")
    return propre.replace(" ", "_")[:40] or "eleve"


def _fichier_session(eleve: str, code: str | None = None) -> Path:
    """Journal de l'élève, en récupérant au passage ses anciennes données."""
    fichier = DOSSIER_SESSIONS / f"{_identifiant(eleve, code)}.jsonl"
    if fichier.exists():
        return fichier

    # Conversations enregistrées avant ce changement : on les rattache à
    # l'abonnement plutôt que de les perdre.
    for ancien_nom in (_identifiant_ancien(eleve), _nom_normalise(eleve)):
        ancien = DOSSIER_SESSIONS / f"{ancien_nom}.jsonl"
        if ancien.exists() and ancien != fichier:
            ancien.rename(fichier)
            ancien_bilan = DOSSIER_BILANS / f"{ancien_nom}.json"
            if ancien_bilan.exists():
                ancien_bilan.rename(DOSSIER_BILANS / f"{_identifiant(eleve, code)}.json")
            break
    return fichier

def _journal(fichier: Path) -> list[dict]:
    """Échanges de l'élève, chacun rattaché à sa séance de travail.

    Une séance = un exercice ou un chapitre. L'élève peut en ouvrir une
    deuxième pour vérifier une information sans perdre son cours en cours.
    """
    if not fichier.exists():
        return []
    lignes = [json.loads(l) for l in fichier.read_text(encoding="utf-8").splitlines() if l]
    echanges, courante = [], 1
    for ligne in lignes:
        # Ancien marqueur de coupure : il ouvrait simplement la séance suivante.
        if ligne["role"] == "separateur":
            courante += 1
            continue
        courante = ligne.get("seance", courante)
        echanges.append({**ligne, "seance": courante})
    return echanges


def _seance_courante(echanges: list[dict]) -> int:
    """Dernière séance touchée par l'élève."""
    return echanges[-1]["seance"] if echanges else 1


def _titre_seance(echanges: list[dict]) -> str:
    """Première question de l'élève : c'est elle qui nomme la séance."""
    for e in echanges:
        if e["role"] == "eleve" and e["texte"].strip():
            titre = " ".join(e["texte"].split())
            return titre[:48] + "…" if len(titre) > 48 else titre
    return "Exercice photographié" if any(e.get("photo") for e in echanges) else "Séance vide"


def _enregistrer_photo(donnees_base64: str, type_media: str | None) -> str | None:
    """Conserve la photo sur le disque, pour que l'élève la retrouve ailleurs."""
    try:
        brut = base64.b64decode(donnees_base64, validate=True)
    except (binascii.Error, ValueError):
        return None
    if not brut or len(brut) > MAX_PHOTO_OCTETS:
        return None
    nom = f"{uuid4().hex}.{'png' if 'png' in (type_media or '') else 'jpg'}"
    (DOSSIER_PHOTOS / nom).write_bytes(brut)
    return nom


app = FastAPI(title="Tuteur BEPC — Maths", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Une clé non remplacée (texte d'exemple) doit être traitée comme absente,
# sinon l'utilisateur reçoit une erreur d'authentification incompréhensible.
_cle = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
CLE_PRESENTE = _cle.startswith("sk-ant-")

# Codes d'accès : un par testeur, séparés par des virgules dans CODE_ACCES.
# Permet de couper l'accès à une seule personne sans gêner les autres, et de
# repérer un code qui circule (plusieurs prénoms sur le même code).
# Vide en local = aucune protection (pratique pour développer).
CODES_ACCES = {c.strip() for c in (os.getenv("CODE_ACCES") or "").split(",") if c.strip()}


# Un abonnement = un élève, ou deux quand des frères et sœurs partagent un
# téléphone. Au-delà, le code circule : on refuse le troisième prénom.
MAX_ELEVES_PAR_CODE = int(os.getenv("MAX_ELEVES_PAR_CODE", "2"))

# Plafond de questions par jour et par abonnement. C'est la vraie protection
# du budget : un code enregistré dans un appareil prêté ne peut pas être
# utilisé sans fin, même si l'application, elle, ne redemande rien.
MAX_QUESTIONS_PAR_JOUR = int(os.getenv("MAX_QUESTIONS_PAR_JOUR", "40"))


def _verifier_code(code: str | None) -> str | None:
    """Refuse les inconnus quand des codes sont configurés."""
    if not CODES_ACCES:
        return None
    propre = (code or "").strip()
    if propre not in CODES_ACCES:
        raise HTTPException(status_code=403, detail="Code d'accès invalide.")
    return propre

client = anthropic.Anthropic()  # lit ANTHROPIC_API_KEY dans l'environnement

if not CLE_PRESENTE:
    print(
        "\n  ATTENTION : aucune clé API valide trouvée.\n"
        "  Ouvrez le fichier backend/.env et collez votre clé (elle commence par sk-ant-).\n"
        "  L'interface fonctionnera, mais le tuteur ne pourra pas répondre.\n"
    )


def _fichiers_du_code(code: str) -> list[Path]:
    """Journaux des élèves rattachés à cet abonnement."""
    empreinte = hashlib.sha256(code.encode("utf-8")).hexdigest()[:10]
    return list(DOSSIER_SESSIONS.glob(f"{empreinte}_*.jsonl"))


def _verifier_quota(eleve: str, code: str | None) -> None:
    """Ce qu'un abonnement a le droit de consommer.

    L'application garde le code enregistré dans l'appareil, comme WhatsApp :
    redemander le code chaque jour ferait fuir les élèves. La contrepartie,
    c'est que le budget doit être protégé ici, côté serveur.
    """
    if not code:
        return
    fichiers = _fichiers_du_code(code)

    connus = {f.stem for f in fichiers}
    if _identifiant(eleve, code) not in connus and len(connus) >= MAX_ELEVES_PAR_CODE:
        raise HTTPException(
            status_code=409,
            detail=f"Ce code est déjà utilisé par {len(connus)} élèves "
                   f"({', '.join(sorted(n.split('_', 1)[-1].title() for n in connus))}). "
                   "Chaque élève a besoin de son propre code.",
        )

    aujourdhui = datetime.now(timezone.utc).date().isoformat()
    posees = sum(
        1
        for f in fichiers
        for e in _journal(f)
        if e["role"] == "eleve" and e["horodatage"].startswith(aujourdhui)
    )
    if posees >= MAX_QUESTIONS_PAR_JOUR:
        raise HTTPException(
            status_code=429,
            detail=f"Tu as posé {posees} questions aujourd'hui, c'est la limite "
                   "journalière. Reprends demain — et relis ce qu'on a déjà fait "
                   "en attendant.",
        )


class Message(BaseModel):
    role: str
    content: str
    # Photo de l'exercice, encodée en base64 (facultatif)
    image: str | None = None
    image_type: str | None = None


class DemandeChat(BaseModel):
    eleve: str = Field(..., max_length=60)
    messages: list[Message]
    # « bepc » (10e année) ou « bac » (Terminale)
    niveau: str = Field(default=NIVEAU_DEFAUT, max_length=10)
    code: str | None = Field(default=None, max_length=60)
    # Séance de travail : permet d'ouvrir une question rapide sans perdre
    # le cours en cours. Absente = on continue la dernière séance.
    seance: int | None = None


def _bloc_utilisateur(message: Message) -> list[dict]:
    """Construit le contenu d'un message élève (texte + photo éventuelle)."""
    blocs: list[dict] = []
    if message.image:
        blocs.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": message.image_type or "image/jpeg",
                "data": message.image,
            },
        })
    blocs.append({"type": "text", "text": message.content or "Voici mon exercice."})
    return blocs


# Tarifs Claude Opus 5, en dollars par million de jetons.
PRIX_ENTREE = 5.00
PRIX_SORTIE = 25.00
PRIX_CACHE_ECRITURE = 6.25   # 1,25 x entrée
PRIX_CACHE_LECTURE = 0.50    # 0,10 x entrée
GNF_PAR_DOLLAR = float(os.getenv("GNF_PAR_DOLLAR", "8700"))


def _cout_gnf(usage) -> float:
    """Coût réel d'un échange, en francs guinéens."""
    dollars = (
        (usage.input_tokens or 0) * PRIX_ENTREE
        + (usage.output_tokens or 0) * PRIX_SORTIE
        + (getattr(usage, "cache_creation_input_tokens", 0) or 0) * PRIX_CACHE_ECRITURE
        + (getattr(usage, "cache_read_input_tokens", 0) or 0) * PRIX_CACHE_LECTURE
    ) / 1_000_000
    return dollars * GNF_PAR_DOLLAR


def _enregistrer(eleve: str, role: str, texte: str, avec_photo: bool = False,
                 cout_gnf: float | None = None, niveau: str | None = None,
                 code: str | None = None, seance: int | None = None,
                 photo_fichier: str | None = None) -> None:
    """Journalise un échange — matière première du rapport au parent."""
    fichier = _fichier_session(eleve, code)
    ligne = {
        "horodatage": datetime.now(timezone.utc).isoformat(),
        "role": role,
        "texte": texte,
        "photo": avec_photo,
        # Prénom tel que l'élève l'a écrit : le nom du fichier est normalisé,
        # mais la page parent doit afficher l'orthographe d'origine.
        "eleve": eleve,
    }
    if cout_gnf is not None:
        ligne["cout_gnf"] = round(cout_gnf, 2)
    if niveau:
        ligne["niveau"] = niveau
    if code:
        ligne["code"] = code
    if seance is not None:
        ligne["seance"] = seance
    if photo_fichier:
        ligne["photo_fichier"] = photo_fichier
    with fichier.open("a", encoding="utf-8") as f:
        f.write(json.dumps(ligne, ensure_ascii=False) + "\n")


@app.post("/api/chat")
def chat(demande: DemandeChat):
    """Répond à l'élève en flux continu (le texte s'affiche au fur et à mesure)."""
    code_utilise = _verifier_code(demande.code)
    if not demande.messages:
        raise HTTPException(status_code=400, detail="Aucun message.")
    _verifier_quota(demande.eleve, code_utilise)

    messages = [
        {
            "role": m.role,
            "content": _bloc_utilisateur(m) if m.role == "user" else m.content,
        }
        for m in demande.messages
    ]

    # Séance de travail : celle demandée, sinon la dernière ouverte.
    seance = demande.seance or _seance_courante(
        _journal(_fichier_session(demande.eleve, code_utilise)))

    dernier = demande.messages[-1]
    if dernier.role == "user":
        # La photo est conservée sur le disque : l'élève doit la revoir
        # depuis un autre appareil, et le tuteur y revient souvent.
        fichier_photo = (_enregistrer_photo(dernier.image, dernier.image_type)
                         if dernier.image else None)
        _enregistrer(demande.eleve, "eleve", dernier.content, bool(dernier.image),
                     niveau=demande.niveau, code=code_utilise, seance=seance,
                     photo_fichier=fichier_photo)

    def flux():
        morceaux: list[str] = []
        if not CLE_PRESENTE:
            message = ("Clé API absente : ouvrez le fichier backend/.env "
                       "et collez-y votre clé Anthropic (elle commence par sk-ant-).")
            yield f"data: {json.dumps({'erreur': message}, ensure_ascii=False)}\n\n"
            return
        try:
            with client.messages.stream(
                model=MODELE,
                max_tokens=2000,  # réponses courtes : c'est une conversation
                output_config={"effort": EFFORT},
                system=[{
                    "type": "text",
                    "text": construire_systeme(demande.niveau),
                    # Le programme est identique à chaque appel : on le met en
                    # cache pour diviser son coût par 10.
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=messages,
            ) as stream:
                for texte in stream.text_stream:
                    morceaux.append(texte)
                    yield f"data: {json.dumps({'texte': texte}, ensure_ascii=False)}\n\n"
                cout = _cout_gnf(stream.get_final_message().usage)
        except anthropic.APIStatusError as erreur:
            yield f"data: {json.dumps({'erreur': str(erreur.message)}, ensure_ascii=False)}\n\n"
            return
        except anthropic.APIConnectionError:
            yield f"data: {json.dumps({'erreur': 'Connexion perdue. Réessaie.'}, ensure_ascii=False)}\n\n"
            return
        except Exception as erreur:  # filet de sécurité : jamais de page blanche
            yield f"data: {json.dumps({'erreur': f'Erreur technique : {erreur}'}, ensure_ascii=False)}\n\n"
            return

        _enregistrer(demande.eleve, "tuteur", "".join(morceaux), cout_gnf=cout,
                     code=code_utilise, seance=seance)
        yield f"data: {json.dumps({'fin': True})}\n\n"

    return StreamingResponse(flux(), media_type="text/event-stream")


# Au-delà, ce n'est plus la même séance de travail : inutile de tout renvoyer.
MAX_MESSAGES_REPRIS = 40


@app.get("/api/conversation/{eleve}")
def conversation(eleve: str, code: str | None = None, seance: int | None = None):
    """Rend à l'élève une de ses séances, quel que soit l'appareil.

    L'historique était jusqu'ici enregistré dans le téléphone : passer sur un
    ordinateur donnait une conversation vide. Le serveur, lui, a tout gardé.
    """
    _verifier_code(code)
    echanges = _journal(_fichier_session(eleve, code))
    if not echanges:
        return {"messages": [], "seance": 1}

    numero = seance or _seance_courante(echanges)
    retenus = [e for e in echanges if e["seance"] == numero]
    return {
        "seance": numero,
        "messages": [
            {
                "role": "user" if e["role"] == "eleve" else "assistant",
                "content": e["texte"],
                "photo": (f"/api/photo/{e['photo_fichier']}" if e.get("photo_fichier") else None),
            }
            for e in retenus[-MAX_MESSAGES_REPRIS:]
        ],
    }


@app.get("/api/verifier-eleve")
def verifier_eleve(eleve: str, code: str | None = None):
    """Dit à l'écran d'accueil si cet élève a le droit de commencer.

    Sans ce contrôle, la conversation s'ouvrait et c'est la première
    question qui était refusée : l'élève se croyait entré, puis se faisait
    rejeter. Le refus doit arriver avant, sur l'écran d'accueil.
    """
    code_utilise = _verifier_code(code)
    _verifier_quota(eleve, code_utilise)
    return {"autorise": True}


@app.get("/api/profils")
def profils(code: str | None = None):
    """Élèves déjà rattachés à cet abonnement.

    Sur un nouvel appareil, l'application les propose au lieu de faire
    retaper le prénom : une faute de frappe — ou le code saisi par erreur
    dans la case du prénom — créait un élève de plus, à l'historique vide.
    """
    code_utilise = _verifier_code(code)
    if not code_utilise:
        return {"profils": []}

    empreinte = hashlib.sha256(code_utilise.encode("utf-8")).hexdigest()[:10]
    trouves = []
    for fichier in DOSSIER_SESSIONS.glob(f"{empreinte}_*.jsonl"):
        echanges = _journal(fichier)
        if not echanges:
            continue
        nom = echanges[-1].get("eleve") or fichier.stem.split("_", 1)[-1]
        # Un « élève » qui porte le nom d'un code d'accès vient d'une saisie
        # dans la mauvaise case : on ne le propose pas.
        if _nom_normalise(nom) in {_nom_normalise(c) for c in CODES_ACCES}:
            continue
        trouves.append({
            "nom": nom,
            "niveau": next((e["niveau"] for e in reversed(echanges) if e.get("niveau")),
                           NIVEAU_DEFAUT),
            "questions": sum(1 for e in echanges if e["role"] == "eleve"),
            "derniere_activite": echanges[-1]["horodatage"],
        })
    trouves.sort(key=lambda p: p["derniere_activite"], reverse=True)
    return {"profils": trouves}


@app.get("/api/seances/{eleve}")
def liste_seances(eleve: str, code: str | None = None):
    """Toutes les séances de l'élève, la plus récente en premier.

    C'est ce qui lui permet de vérifier une information dans une nouvelle
    discussion puis de revenir exactement où il en était dans son cours.
    """
    _verifier_code(code)
    echanges = _journal(_fichier_session(eleve, code))

    groupes: dict[int, list[dict]] = {}
    for e in echanges:
        groupes.setdefault(e["seance"], []).append(e)

    seances = [
        {
            "numero": numero,
            "titre": _titre_seance(lignes),
            "questions": sum(1 for l in lignes if l["role"] == "eleve"),
            "derniere_activite": lignes[-1]["horodatage"],
        }
        for numero, lignes in groupes.items()
    ]
    seances.sort(key=lambda s: s["derniere_activite"], reverse=True)
    return {"seances": seances, "courante": _seance_courante(echanges)}


@app.get("/api/photo/{nom}")
def photo(nom: str, code: str | None = None):
    """Sert une photo d'exercice conservée sur le disque."""
    _verifier_code(code)
    # Le nom est fabriqué par le serveur : tout ce qui s'en écarte est rejeté,
    # un chemin bricolé ne peut donc pas remonter dans les dossiers.
    if not re.fullmatch(r"[0-9a-f]{32}\.(jpg|png)", nom):
        raise HTTPException(status_code=404, detail="Photo introuvable.")
    chemin = DOSSIER_PHOTOS / nom
    if not chemin.exists():
        raise HTTPException(status_code=404, detail="Photo introuvable.")
    return FileResponse(chemin,
                        media_type="image/png" if nom.endswith(".png") else "image/jpeg")


class DemandeSeance(BaseModel):
    eleve: str = Field(..., max_length=60)
    code: str | None = Field(default=None, max_length=60)


@app.post("/api/nouvelle-seance")
def nouvelle_seance(demande: DemandeSeance):
    """Ouvre une séance de plus, sans toucher aux précédentes.

    L'élève en plein chapitre peut poser une question rapide à côté, puis
    revenir à son cours : rien n'est effacé, tout reste consultable.
    """
    code_utilise = _verifier_code(demande.code)
    echanges = _journal(_fichier_session(demande.eleve, code_utilise))
    numero = (max((e["seance"] for e in echanges), default=0) + 1)
    return {"seance": numero}


@app.get("/api/rapport/{eleve}")
def rapport(eleve: str, code: str | None = None):
    """Résumé d'activité d'un élève — base du rapport hebdomadaire au parent."""
    fichier = _fichier_session(eleve, code)
    if not fichier.exists():
        return {"eleve": eleve, "echanges": 0, "questions": 0, "photos": 0}

    lignes = [json.loads(l) for l in fichier.read_text(encoding="utf-8").splitlines() if l]
    lignes = [l for l in lignes if l["role"] != "separateur"]
    questions = [l for l in lignes if l["role"] == "eleve"]
    cout_total = sum(l.get("cout_gnf", 0) for l in lignes)
    return {
        "eleve": eleve,
        "echanges": len(lignes),
        "questions": len(questions),
        "photos": sum(1 for l in questions if l.get("photo")),
        "cout_total_gnf": round(cout_total, 2),
        "cout_moyen_par_question_gnf": round(cout_total / len(questions), 2) if questions else 0,
        "premiere_activite": lignes[0]["horodatage"] if lignes else None,
        "derniere_activite": lignes[-1]["horodatage"] if lignes else None,
    }


@app.get("/api/config")
def config():
    """Dit à l'application si un code d'accès est exigé."""
    return {"code_requis": bool(CODES_ACCES)}


@app.get("/api/eleves")
def liste_eleves(code: str | None = None):
    """Élèves ayant déjà travaillé — évite au parent de deviner l'orthographe."""
    _verifier_code(code)
    eleves = []
    for fichier in DOSSIER_SESSIONS.glob("*.jsonl"):
        lignes = [l for l in fichier.read_text(encoding="utf-8").splitlines() if l]
        if not lignes:
            continue
        derniere = json.loads(lignes[-1])
        # Le nom du fichier est normalisé (accents retirés) et préfixé par
        # l'empreinte de l'abonnement : on affiche le prénom tel qu'écrit.
        nom = derniere.get("eleve") or fichier.stem.split("_", 1)[-1].replace("_", " ").title()
        eleves.append({
            "identifiant": fichier.stem,
            "nom": nom,
            "questions": sum(1 for l in lignes if json.loads(l)["role"] == "eleve"),
            "derniere_activite": derniere["horodatage"],
        })
    eleves.sort(key=lambda e: e["derniere_activite"], reverse=True)
    return {"eleves": eleves}


@app.get("/api/progres/{eleve}")
def progres_eleve(eleve: str, code: str | None = None):
    """Ce que l'élève voit de sa propre progression.

    Beaucoup de ces élèves n'ont personne qui suit leur travail : voir leurs
    chapitres passer au vert est leur seule raison de revenir demain. On ne
    leur montre donc pas le bilan du parent, mais une version qui leur parle.
    """
    complet = bilan_eleve(eleve, code)
    if complet.get("pas_assez_de_donnees"):
        return complet
    return {
        "eleve": eleve,
        "resume": complet.get("resume_eleve", ""),
        "prochaine_etape": complet.get("prochaine_etape", ""),
        "chapitres": complet.get("chapitres", []),
        "activite": complet.get("activite", {}),
    }


@app.get("/api/codes")
def usage_codes(code: str | None = None):
    """Qui utilise quel code — sert à repérer un code qui a été partagé.

    Un code utilisé par plusieurs prénoms = il circule au-delà du testeur.
    """
    _verifier_code(code)
    par_code: dict[str, dict] = {}
    for fichier in DOSSIER_SESSIONS.glob("*.jsonl"):
        nom = fichier.stem.split("_", 1)[-1].replace("_", " ").title()
        for ligne in fichier.read_text(encoding="utf-8").splitlines():
            if not ligne:
                continue
            entree = json.loads(ligne)
            utilise = entree.get("code")
            if not utilise or entree["role"] != "eleve":
                continue
            fiche = par_code.setdefault(utilise, {"code": utilise, "eleves": set(),
                                                  "questions": 0, "derniere_activite": ""})
            fiche["eleves"].add(entree.get("eleve") or nom)
            fiche["questions"] += 1
            fiche["derniere_activite"] = max(fiche["derniere_activite"], entree["horodatage"])

    codes = []
    for fiche in par_code.values():
        eleves = sorted(fiche["eleves"])
        codes.append({**fiche, "eleves": eleves, "partage": len(eleves) > 1})
    codes.sort(key=lambda c: c["derniere_activite"], reverse=True)

    jamais_utilises = sorted(CODES_ACCES - par_code.keys())
    return {"codes": codes, "jamais_utilises": jamais_utilises,
            "total_configures": len(CODES_ACCES)}


@app.get("/api/bilan/{eleve}")
def bilan_eleve(eleve: str, code: str | None = None):
    """Bilan de niveau destiné au parent : chapitres, progression, conseils.

    Recalculé uniquement quand l'élève a travaillé depuis la dernière fois,
    pour ne pas payer une analyse à chaque rafraîchissement de page.
    """
    _verifier_code(code)
    if not CLE_PRESENTE:
        raise HTTPException(status_code=503,
                            detail="Clé API absente : impossible de générer le bilan.")

    try:
        resultat = module_bilan.generer(
            _fichier_session(eleve, code),
            DOSSIER_BILANS / f"{_identifiant(eleve, code)}.json",
            client,
            _cout_gnf,
        )
    except anthropic.APIStatusError as erreur:
        raise HTTPException(status_code=502, detail=str(erreur.message))

    if resultat is None:
        raise HTTPException(status_code=404, detail="Aucune activité pour cet élève.")

    # On complète le bilan avec les chiffres bruts d'activité.
    resultat = dict(resultat)
    resultat["eleve"] = eleve
    resultat["activite"] = rapport(eleve, code)
    return resultat


# Le site (l'« application ») est servi par la même adresse que l'API.
DOSSIER_WEB = BASE_DIR.parent / "web"
if DOSSIER_WEB.exists():
    app.mount("/", StaticFiles(directory=DOSSIER_WEB, html=True), name="web")
