"""Suivi de niveau : ce que le parent achète réellement.

À partir des conversations de l'élève, on produit un bilan lisible par un
parent qui n'est pas mathématicien : chapitres travaillés, niveau atteint,
points à retravailler et recommandations concrètes.

Le bilan est mis en cache : il n'est recalculé que si l'élève a travaillé
depuis la dernière fois. Un parent qui rafraîchit sa page ne coûte rien.
"""
import json
from pathlib import Path
from typing import Literal

import anthropic
from pydantic import BaseModel, Field

MODELE_ANALYSE = "claude-opus-5"

# Nombre d'échanges au-delà duquel on ne remonte plus (les plus récents comptent).
MAX_ECHANGES_ANALYSES = 200

# Une analyse coûte environ 500 GNF. Sans ce seuil, un élève qui ouvre sa
# progression après chaque question la ferait recalculer à chaque fois et
# mangerait la marge de l'abonnement. Entre deux recalculs, on ressert le
# bilan précédent : la progression reste visible, elle est juste un peu
# moins fraîche.
ECHANGES_AVANT_RECALCUL = 20


class Chapitre(BaseModel):
    """Un chapitre du programme travaillé par l'élève."""
    nom: str = Field(description="Nom du chapitre, ex : 'Théorème de Pythagore'")
    questions: int = Field(description="Nombre de questions posées sur ce chapitre")
    niveau: Literal["acquis", "en cours", "difficulté"] = Field(
        description="acquis = il sait faire seul ; en cours = il y arrive avec de "
                    "l'aide ; difficulté = il bloque encore"
    )
    commentaire: str = Field(description="Une phrase précise sur ce qu'il maîtrise ou non")


class Bilan(BaseModel):
    """Bilan complet, rédigé pour être lu par un parent."""
    resume_parent: str = Field(
        description="3 à 4 phrases pour le parent, en français simple, sans jargon "
                    "mathématique. Ce qu'a fait son enfant et où il en est."
    )
    perseverance: Literal["excellente", "bonne", "irrégulière", "faible"] = Field(
        description="L'élève persévère-t-il quand c'est difficile, ou abandonne-t-il vite ?"
    )
    commentaire_perseverance: str = Field(description="Une phrase justifiant l'évaluation")
    chapitres: list[Chapitre] = Field(description="Chapitres travaillés, du plus au moins traité")
    points_forts: list[str] = Field(description="2 à 4 réussites concrètes de l'élève")
    points_a_travailler: list[str] = Field(description="2 à 4 difficultés précises à reprendre")
    recommandations: list[str] = Field(
        description="2 à 4 actions concrètes pour la semaine à venir, formulées "
                    "pour l'élève et compréhensibles par le parent"
    )

    # --- Ce que l'élève lit lui-même -------------------------------------
    # Produit dans le même appel que le reste : voir l'élève progresser ne
    # coûte donc rien de plus. C'est ce qui lui donne envie de revenir,
    # surtout quand aucun parent ne suit son travail.
    resume_eleve: str = Field(
        description="2 à 3 phrases adressées DIRECTEMENT à l'élève, en le "
                    "tutoyant. Ce qu'il a réussi depuis le début, en nommant "
                    "un progrès précis. Honnête mais jamais décourageant."
    )
    prochaine_etape: str = Field(
        description="UNE seule chose concrète à travailler ensuite, adressée à "
                    "l'élève en le tutoyant, faisable en une séance. "
                    "Ex : « Reprends les équations à deux inconnues : tu poses "
                    "bien le système, c'est la résolution qui coince encore. »"
    )


CONSIGNE = """Tu analyses les conversations entre un élève guinéen de 10e année \
(qui prépare le BEPC) et son tuteur de mathématiques.

Tu produis un bilan destiné à SON PARENT. Le parent n'est pas mathématicien : il \
veut savoir si son enfant travaille, s'il progresse, et ce qu'il doit retravailler.

Règles :
- Écris en français simple. Pas de jargon inutile.
- Sois précis et factuel : appuie-toi sur ce que l'élève a réellement dit et fait.
- Sois honnête. Si l'élève a peu travaillé ou a abandonné souvent, dis-le avec \
tact mais clairement — un parent qui paie a droit à la vérité.
- Reste encourageant : signale toujours ce qui va bien, même quand le bilan est faible.
- Vocabulaire scolaire guinéen : 10e année, Terminale. Jamais « 3e » ni « seconde ».
- Les recommandations doivent être concrètes et faisables en une semaine.
- **Tu ne connais pas le genre de l'élève.** N'écris jamais « il » ni « elle » : \
dis « votre enfant », ou tourne la phrase autrement (« Pythagore est acquis », \
« bonne maîtrise des calculs »). Un parent qui lit le mauvais pronom perd \
immédiatement confiance dans le bilan.

Deux champs (« resume_eleve » et « prochaine_etape ») ne sont PAS lus par le \
parent : l'élève les lit lui-même, sur son téléphone. Pour ceux-là :
- Tutoie-le, parle-lui directement.
- Nomme un progrès précis qu'il a réellement fait — pas « tu progresses bien », \
mais « au début tu ne voyais pas quand utiliser Pythagore, maintenant tu le \
repères seul ». C'est ce qui donne envie de continuer.
- Si son travail est faible, reste honnête sans l'accabler : montre-lui la \
plus petite marche qu'il peut franchir tout de suite.
- Beaucoup de ces élèves n'ont personne derrière eux pour les encourager. \
Ce texte est parfois le seul retour qu'ils reçoivent sur leur travail.

Voici les conversations :

"""


def _transcription(fichier: Path) -> tuple[str, int]:
    """Transforme le journal des échanges en texte lisible pour l'analyse."""
    lignes = [json.loads(l) for l in fichier.read_text(encoding="utf-8").splitlines() if l]
    recents = lignes[-MAX_ECHANGES_ANALYSES:]
    texte = "\n".join(
        f"{'ÉLÈVE' if l['role'] == 'eleve' else 'TUTEUR'} : {l['texte']}"
        + (" [photo d'exercice envoyée]" if l.get("photo") else "")
        for l in recents
    )
    return texte, len(lignes)


def generer(fichier_session: Path, fichier_cache: Path,
            client: anthropic.Anthropic, cout_gnf=lambda _u: 0.0) -> dict | None:
    """Retourne le bilan de l'élève, en le recalculant seulement si nécessaire."""
    if not fichier_session.exists():
        return None

    transcription, nb_echanges = _transcription(fichier_session)
    if nb_echanges < 4:
        return {"pas_assez_de_donnees": True, "echanges": nb_echanges}

    # Bilan déjà calculé pour ce même nombre d'échanges : on le réutilise.
    if fichier_cache.exists():
        try:
            cache = json.loads(fichier_cache.read_text(encoding="utf-8"))
            depuis = nb_echanges - cache.get("_echanges", -10_000)
            # « resume_eleve » : un bilan enregistré avant l'ajout de la page
            # de progression de l'élève ne le contient pas — on le refait.
            if 0 <= depuis < ECHANGES_AVANT_RECALCUL and "resume_eleve" in cache:
                return cache
        except (json.JSONDecodeError, OSError):
            pass

    reponse = client.messages.parse(
        model=MODELE_ANALYSE,
        max_tokens=4000,
        messages=[{"role": "user", "content": CONSIGNE + transcription}],
        output_format=Bilan,
    )
    bilan = reponse.parsed_output
    if bilan is None:
        return None

    resultat = bilan.model_dump()
    resultat["_echanges"] = nb_echanges
    resultat["_cout_gnf"] = round(cout_gnf(reponse.usage), 2)
    fichier_cache.write_text(
        json.dumps(resultat, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return resultat
