"""Réserve d'annales : les sujets réellement tombés à l'examen.

Ces exercices ne sont PAS dans le prompt du répétiteur — ils seraient payés
à chaque question de chaque élève. On y pioche à la demande, un exercice à
la fois, quand l'élève travaille le chapitre correspondant.

C'est l'avantage que personne ne peut copier : « cet exercice est tombé au
BEPC 2007, et tu viens de le résoudre seul » vaut tous les encouragements.
"""
import json
import re
import unicodedata
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent / "annales"


def _sans_accent(texte: str) -> str:
    """Pour que « théorème » et « theoreme » se retrouvent l'un l'autre."""
    decompose = unicodedata.normalize("NFD", texte.lower())
    return "".join(c for c in decompose if unicodedata.category(c) != "Mn")


def charger(examen: str = "bepc", matiere: str = "maths") -> list[dict]:
    """Tous les exercices disponibles pour un examen et une matière."""
    fichier = DOSSIER / f"{examen}_{matiere}.json"
    if not fichier.exists():
        return []
    return json.loads(fichier.read_text(encoding="utf-8"))["exercices"]


MOTS_VIDES = {"les", "des", "une", "aux", "deux", "sur", "dans", "pour", "avec"}


def _mots(texte: str) -> set[str]:
    """Mots utiles d'une expression, au singulier."""
    bruts = re.split(r"[^a-z0-9]+", _sans_accent(texte))
    return {m.rstrip("s") for m in bruts if len(m) > 2 and m not in MOTS_VIDES}


# Racine commune suffisante pour dire que deux mots parlent de la même chose.
LONGUEUR_RACINE = 5


def _voisins(a: str, b: str) -> bool:
    """« factorise » et « factorisation » désignent la même notion.

    L'élève écrit des verbes (« comment on factorise »), le programme des
    noms (« factorisation ») : sans ce rapprochement, il ne trouve rien.
    """
    if a == b:
        return True
    court, long_ = sorted((a, b), key=len)
    return len(court) >= LONGUEUR_RACINE and long_.startswith(court[:LONGUEUR_RACINE])


def _proximite(demande: set[str], reference: set[str]) -> float:
    """Part des mots du chapitre que l'élève a effectivement employés."""
    if not demande or not reference:
        return 0.0
    communs = sum(1 for r in reference if any(_voisins(d, r) for d in demande))
    return communs / len(reference)


def chercher(chapitre: str, examen: str = "bepc", matiere: str = "maths",
             limite: int = 3) -> list[dict]:
    """Exercices d'examen portant sur ce chapitre, du plus récent au plus ancien.

    On compare les mots plutôt que les chaînes entières, puis on retombe sur
    l'énoncé si aucun chapitre ne correspond.
    """
    besoin = _mots(chapitre)
    if not besoin:
        return []

    par_chapitre, par_enonce = [], []
    for ex in charger(examen, matiere):
        proximite = max((_proximite(besoin, _mots(c)) for c in ex["chapitres"]), default=0.0)
        if proximite >= 0.5:
            par_chapitre.append((proximite, ex))
        elif besoin <= _mots(ex["enonce"]):
            par_enonce.append(ex)

    par_chapitre.sort(key=lambda pe: (-pe[0], -pe[1]["session"]))
    par_enonce.sort(key=lambda e: e["session"], reverse=True)
    return [ex for _, ex in par_chapitre][:limite] or par_enonce[:limite]


def chapitres_disponibles(examen: str = "bepc", matiere: str = "maths") -> dict[str, int]:
    """Quels chapitres sont couverts, et par combien d'exercices.

    Sert au suivi : montre où la réserve est riche et où elle est vide.
    """
    compte: dict[str, int] = {}
    for ex in charger(examen, matiere):
        for c in ex["chapitres"]:
            compte[c] = compte.get(c, 0) + 1
    return dict(sorted(compte.items(), key=lambda kv: (-kv[1], kv[0])))


def sessions_disponibles(examen: str = "bepc", matiere: str = "maths") -> list[int]:
    """Années d'examen présentes dans la réserve."""
    return sorted({ex["session"] for ex in charger(examen, matiere)})
