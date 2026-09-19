"""Le plan de révision : ce que l'élève travaille, et dans quel ordre.

Le constat qui l'a fait naître : sur les douze premiers testeurs, la
plupart ont arrêté au bout de deux semaines. Le répétiteur n'était pas en
cause — l'élève ouvrait l'application sans savoir quoi y faire. Un élève
qui a un plan revient : il sait ce qui l'attend aujourd'hui.

Le plan est PROPOSÉ par le répétiteur, jamais imposé par le parent : un
plan venu du parent ferait de l'application un outil de surveillance, le
contraire du grand frère qui aide.

Il est calculé ici, sans appel à l'IA : même demande, même plan, aucun
coût. L'ordre des chapitres vient des annales — ce qui tombe le plus
souvent passe en premier.
"""
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# Chaque chapitre : (nom montré à l'élève, séances de travail prévues).
# L'ordre est celui des fréquences relevées dans les annales.
CHAPITRES = {
    # 21 sessions du BEPC, 2005-2025.
    "bepc": [
        ("Racines carrées", 3),
        ("Identités remarquables et factorisation", 3),
        ("Repère orthonormé et distance entre deux points", 3),
        ("Problèmes concrets et systèmes d'équations", 4),
        ("Théorème de Pythagore et sa réciproque", 3),
        ("Équation d'une droite", 2),
        ("Vecteurs", 3),
        ("Trigonométrie", 3),
        ("Cercle circonscrit et tangente", 2),
        ("Symétries et quadrilatères", 3),
        ("Théorème de Thalès", 2),
        ("Équations produit et encadrement", 2),
        ("Statistiques", 2),
        ("Pourcentages et application affine", 2),
    ],
    # 20 sessions du BEPC, 2006-2025.
    "bepc-physique": [
        ("Puissance et énergie électriques", 3),
        ("Lentilles", 4),
        ("Résistances et loi d'Ohm", 3),
        ("Travail et puissance mécanique", 3),
        ("L'œil et ses défauts", 2),
        ("Machines simples : treuil, poulie, palan", 3),
        ("Rendement", 2),
        ("Vitesse et mouvements", 2),
        ("Réflexion, réfraction, miroir plan", 2),
        ("Quantité de chaleur", 2),
        ("Relais et transistor", 2),
    ],
    # 20 sessions du BEPC, 2006-2025.
    "bepc-chimie": [
        ("Oxydoréduction", 4),
        ("Alcanes, alcènes et alcynes", 4),
        ("Calculs de masse et de volume", 3),
        ("pH, acides et bases", 3),
        ("Combustion et volume d'air", 3),
        ("Identification des ions", 2),
        ("Pile Leclanché, fonte et acier", 2),
    ],
    # Physique de Terminale SM : aucune annale relevée pour l'instant, donc
    # aucune fréquence. L'ordre suit celui du programme de l'enseignant, qui
    # est aussi l'ordre où les chapitres s'enchaînent — la dynamique a besoin
    # de la cinématique, l'induction du champ magnétique.
    "bac-physique": [
        ("Cinématique et mouvements", 3),
        ("Dynamique : relation fondamentale et énergie cinétique", 4),
        ("Interaction et champ gravitationnel, satellites et planètes", 3),
        ("Mouvement d'un projectile dans le champ de pesanteur", 3),
        ("Particule chargée dans un champ électrostatique", 3),
        ("Solide en rotation et théorème de Huygens", 3),
        ("Oscillations mécaniques libres : pendule élastique", 3),
        ("Champ magnétique et loi de Laplace", 4),
        ("Induction électromagnétique et auto-induction", 4),
        ("Oscillations électriques et courant alternatif", 4),
        ("Ondes électromagnétiques", 2),
        ("Optique ondulatoire : interférences lumineuses", 3),
        ("Effet photoélectrique et niveaux d'énergie de l'atome", 3),
        ("Physique nucléaire : noyau, radioactivité, réactions", 4),
    ],
    # BAC SM/SE : cinq sessions seulement, pas de fréquences fiables. Le
    # problème d'étude de fonction et l'arithmétique tombent à chaque
    # session : ils passent en tête, le reste suit l'ordre du programme.
    "bac": [
        ("Limites, continuité et dérivées", 3),
        ("Fonctions logarithme et exponentielle", 4),
        ("Étude de fonctions et théorème des valeurs intermédiaires", 4),
        ("Arithmétique : PGCD, Bézout, congruences", 4),
        ("Intégration et calcul d'aire", 4),
        ("Nombres complexes", 4),
        ("Similitudes et transformations", 3),
        ("Suites numériques et récurrence", 4),
        ("Barycentres", 2),
        ("Probabilités", 3),
        ("Équations différentielles", 2),
    ],
}

# Les deux dernières semaines ne se planifient pas chapitre par chapitre :
# elles servent aux sujets complets, en conditions d'examen.
SEMAINES_DE_REVISION_FINALE = 2

RYTHMES = (2, 3, 4, 5, 6)  # séances par semaine proposées à l'élève


def _aujourdhui() -> date:
    return datetime.now(timezone.utc).date()


def date_examen(mois: str) -> date:
    """« 2027-06 » → 1er juin 2027.

    On vise le PREMIER jour du mois : si l'épreuve tombe tôt dans le mois,
    l'élève a fini à temps ; si elle tombe tard, il a de la marge.
    """
    annee, numero = (int(x) for x in mois.split("-"))
    return date(annee, numero, 1)


def construire(niveau: str, mois_examen: str, seances_par_semaine: int,
               deja_faits: set[str] | None = None) -> dict:
    """Répartit les chapitres entre aujourd'hui et l'examen.

    Quand le temps manque, on garde les chapitres les plus fréquents et on
    marque les autres « si tu as le temps » — mieux vaut maîtriser ce qui
    tombe souvent que survoler tout le programme.
    """
    if niveau not in CHAPITRES:
        raise ValueError("niveau sans plan")
    if seances_par_semaine not in RYTHMES:
        raise ValueError("rythme inconnu")

    aujourdhui = _aujourdhui()
    examen = date_examen(mois_examen)
    if examen <= aujourdhui:
        raise ValueError("examen passé")
    fin_des_chapitres = examen - timedelta(weeks=SEMAINES_DE_REVISION_FINALE)
    # Examen tout proche : on ne réserve plus de révision finale, chaque
    # jour compte pour les chapitres eux-mêmes.
    if (fin_des_chapitres - aujourdhui).days < 21:
        fin_des_chapitres = examen
    semaines = max(0.0, (fin_des_chapitres - aujourdhui).days / 7)
    seances_disponibles = semaines * seances_par_semaine
    deja_faits = deja_faits or set()

    total = sum(s for _, s in CHAPITRES[niveau])
    # Assez de temps : on étale jusqu'à l'examen, sans quoi un élève d'octobre
    # finirait son plan en décembre et n'aurait plus rien devant lui jusqu'en
    # juin. Pas assez : on avance au rythme choisi, et ce qui ne tient pas
    # devient facultatif.
    etale = total <= seances_disponibles
    duree = (fin_des_chapitres - aujourdhui).days

    chapitres, cumul = [], 0
    for nom, seances in CHAPITRES[niveau]:
        cumul += seances
        tient = cumul <= seances_disponibles
        if etale:
            fin = aujourdhui + timedelta(days=round(duree * cumul / total))
        else:
            fin = aujourdhui + timedelta(days=round(cumul / seances_par_semaine * 7))
        chapitres.append({
            "nom": nom,
            "seances": seances,
            "fin_prevue": min(fin, fin_des_chapitres).isoformat(),
            "optionnel": not tient,
            "fait": nom in deja_faits,
        })

    return {
        "niveau": niveau,
        "mois_examen": mois_examen,
        "seances_par_semaine": seances_par_semaine,
        "cree_le": aujourdhui.isoformat(),
        "chapitres": chapitres,
    }


def etat(plan: dict) -> dict:
    """Où en est l'élève par rapport à son plan, calculé à la lecture.

    Le retard se compte en chapitres, pas en jours : « tu as un chapitre de
    retard » se comprend, « tu as neuf jours de retard » décourage.
    """
    aujourdhui = _aujourdhui()
    chapitres = plan["chapitres"]
    essentiels = [c for c in chapitres if not c["optionnel"]]
    faits = [c for c in chapitres if c["fait"]]

    prochain = next((c for c in essentiels if not c["fait"]), None) \
        or next((c for c in chapitres if not c["fait"]), None)
    attendus = sum(1 for c in essentiels if date.fromisoformat(c["fin_prevue"]) < aujourdhui)
    faits_essentiels = sum(1 for c in essentiels if c["fait"])
    examen = date_examen(plan["mois_examen"])

    return {
        "prochain": prochain["nom"] if prochain else None,
        "prochain_fin_prevue": prochain["fin_prevue"] if prochain else None,
        "faits": len(faits),
        "total": len(chapitres),
        "essentiels": len(essentiels),
        "retard": max(0, attendus - faits_essentiels),
        "jours_avant_examen": (examen - aujourdhui).days,
        "tout_tient": len(essentiels) == len(chapitres),
    }


class Plans:
    """Les plans de révision, un par élève et par matière, sur le disque."""

    def __init__(self, dossier: Path):
        self.dossier = dossier
        self.dossier.mkdir(parents=True, exist_ok=True)

    def _fichier(self, eleve_id: str, niveau: str) -> Path:
        return self.dossier / f"{eleve_id}__{niveau}.json"

    def lire(self, eleve_id: str, niveau: str) -> dict | None:
        fichier = self._fichier(eleve_id, niveau)
        if not fichier.exists():
            return None
        try:
            return json.loads(fichier.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def ecrire(self, eleve_id: str, plan: dict) -> dict:
        fichier = self._fichier(eleve_id, plan["niveau"])
        provisoire = fichier.with_suffix(".tmp")
        provisoire.write_text(json.dumps(plan, ensure_ascii=False, indent=1),
                              encoding="utf-8")
        provisoire.replace(fichier)
        return plan

    def creer(self, eleve_id: str, niveau: str, mois_examen: str,
              seances_par_semaine: int) -> dict:
        """Nouveau plan — en gardant les chapitres déjà cochés si l'élève
        change seulement de date ou de rythme."""
        ancien = self.lire(eleve_id, niveau)
        faits = {c["nom"] for c in ancien["chapitres"] if c["fait"]} if ancien else set()
        return self.ecrire(eleve_id, construire(niveau, mois_examen,
                                                seances_par_semaine, faits))

    def cocher(self, eleve_id: str, niveau: str, nom: str, fait: bool) -> dict | None:
        plan = self.lire(eleve_id, niveau)
        if not plan:
            return None
        for c in plan["chapitres"]:
            if c["nom"] == nom:
                c["fait"] = fait
                c["fait_le"] = _aujourdhui().isoformat() if fait else None
                return self.ecrire(eleve_id, plan)
        return None

    def tous(self, eleve_id: str) -> list[dict]:
        """Tous les plans de l'élève, une matière chacun."""
        plans = []
        for fichier in sorted(self.dossier.glob(f"{eleve_id}__*.json")):
            try:
                plans.append(json.loads(fichier.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                continue
        return plans
