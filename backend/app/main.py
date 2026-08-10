"""API du tuteur IA — BEPC Maths (Guinée).

Le navigateur de l'élève parle à cette API, qui parle à Claude.
La clé API reste ici, côté serveur : elle n'est jamais exposée à l'élève.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .prompts import construire_systeme

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

# Claude Opus 5 : le meilleur modèle, pour la meilleure qualité pédagogique.
# L'effort "medium" garde des réponses rapides pour une conversation.
MODELE = "claude-opus-5"
EFFORT = "medium"

# Dossier des conversations, base des rapports aux parents.
DOSSIER_SESSIONS = BASE_DIR / "sessions"
DOSSIER_SESSIONS.mkdir(exist_ok=True)

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

client = anthropic.Anthropic()  # lit ANTHROPIC_API_KEY dans l'environnement

if not CLE_PRESENTE:
    print(
        "\n  ATTENTION : aucune clé API valide trouvée.\n"
        "  Ouvrez le fichier backend/.env et collez votre clé (elle commence par sk-ant-).\n"
        "  L'interface fonctionnera, mais le tuteur ne pourra pas répondre.\n"
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


def _enregistrer(eleve: str, role: str, texte: str, avec_photo: bool = False) -> None:
    """Journalise un échange — matière première du rapport au parent."""
    fichier = DOSSIER_SESSIONS / f"{eleve.lower().replace(' ', '_')}.jsonl"
    ligne = {
        "horodatage": datetime.now(timezone.utc).isoformat(),
        "role": role,
        "texte": texte,
        "photo": avec_photo,
    }
    with fichier.open("a", encoding="utf-8") as f:
        f.write(json.dumps(ligne, ensure_ascii=False) + "\n")


@app.post("/api/chat")
def chat(demande: DemandeChat):
    """Répond à l'élève en flux continu (le texte s'affiche au fur et à mesure)."""
    if not demande.messages:
        raise HTTPException(status_code=400, detail="Aucun message.")

    messages = [
        {
            "role": m.role,
            "content": _bloc_utilisateur(m) if m.role == "user" else m.content,
        }
        for m in demande.messages
    ]

    dernier = demande.messages[-1]
    if dernier.role == "user":
        _enregistrer(demande.eleve, "eleve", dernier.content, bool(dernier.image))

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
                    "text": construire_systeme(),
                    # Le programme est identique à chaque appel : on le met en
                    # cache pour diviser son coût par 10.
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=messages,
            ) as stream:
                for texte in stream.text_stream:
                    morceaux.append(texte)
                    yield f"data: {json.dumps({'texte': texte}, ensure_ascii=False)}\n\n"
        except anthropic.APIStatusError as erreur:
            yield f"data: {json.dumps({'erreur': str(erreur.message)}, ensure_ascii=False)}\n\n"
            return
        except anthropic.APIConnectionError:
            yield f"data: {json.dumps({'erreur': 'Connexion perdue. Réessaie.'}, ensure_ascii=False)}\n\n"
            return
        except Exception as erreur:  # filet de sécurité : jamais de page blanche
            yield f"data: {json.dumps({'erreur': f'Erreur technique : {erreur}'}, ensure_ascii=False)}\n\n"
            return

        _enregistrer(demande.eleve, "tuteur", "".join(morceaux))
        yield f"data: {json.dumps({'fin': True})}\n\n"

    return StreamingResponse(flux(), media_type="text/event-stream")


@app.get("/api/rapport/{eleve}")
def rapport(eleve: str):
    """Résumé d'activité d'un élève — base du rapport hebdomadaire au parent."""
    fichier = DOSSIER_SESSIONS / f"{eleve.lower().replace(' ', '_')}.jsonl"
    if not fichier.exists():
        return {"eleve": eleve, "echanges": 0, "questions": 0, "photos": 0}

    lignes = [json.loads(l) for l in fichier.read_text(encoding="utf-8").splitlines() if l]
    questions = [l for l in lignes if l["role"] == "eleve"]
    return {
        "eleve": eleve,
        "echanges": len(lignes),
        "questions": len(questions),
        "photos": sum(1 for l in questions if l.get("photo")),
        "premiere_activite": lignes[0]["horodatage"] if lignes else None,
        "derniere_activite": lignes[-1]["horodatage"] if lignes else None,
    }


# Le site (l'« application ») est servi par la même adresse que l'API.
DOSSIER_WEB = BASE_DIR.parent / "web"
if DOSSIER_WEB.exists():
    app.mount("/", StaticFiles(directory=DOSSIER_WEB, html=True), name="web")
