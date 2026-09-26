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
    # 26 sessions du CEE, 2000-2025. La fréquence entre parenthèses est le
    # nombre de sessions où le chapitre est tombé. L'ordre les suit, sauf que
    # les conversions d'aires (11) remontent juste derrière les aires des
    # figures (17) : on ne calcule pas une aire en hectares sans savoir
    # convertir. Les séances sont plus courtes qu'au BEPC — un enfant de CM2
    # ne tient pas une heure sur un même chapitre.
    "cee": [
        ("Poser et effectuer les opérations", 4),        # 25/26
        ("Les durées : heures, minutes, secondes", 3),   # 18/26
        ("Les aires : rectangle, carré, triangle", 3),   # 17/26
        ("Les conversions d'aires : ha, a, ca", 2),      # 11/26
        ("Les problèmes de prix et de bénéfice", 3),     # 17/26
        ("Les fractions", 3),                            # 14/26
        ("Les conversions : longueurs, masses, litres", 3),  # 14/26
        ("Les périmètres et les clôtures", 2),           #  8/26
        ("Lire, écrire et comparer les nombres", 2),     #  8/26
        ("Les angles et les figures", 2),                #  6/26
        ("La division avec quotient et reste", 2),       #  3/26
        ("Les volumes", 2),                              #  2/26
    ],
    # 21 sessions du CEE, 2005-2025. Le croquis annoté tombe 17 fois sur 21 :
    # c'est le chapitre le plus rentable, il passe en tête. Les séances sont
    # courtes — cette épreuve se récite plus qu'elle ne se raisonne.
    "cee-sciences": [
        ("Les croquis à savoir annoter", 4),             # 17/21
        ("La santé et les maladies", 3),                 # 12/21
        ("Le corps humain : organes et appareils", 3),   #  9/21
        ("La matière et ses états", 2),                  #  8/21
        ("L'énergie et l'environnement", 2),             #  8/21
        ("Le squelette, les os et les muscles", 2),      #  7/21
        ("Les organes excréteurs et leurs déchets", 2),  #  6/21
        ("Les plantes et leur multiplication", 2),       #  6/21
        ("Les techniques culturales", 2),                #  5/21
        ("Les animaux : régimes et milieux de vie", 2),  #  5/21
    ],
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
    # Physique de Terminale SM/SE : 18 sessions relevées, 2016-2024, les deux
    # séries chaque année. Le commentaire donne le nombre de sessions où le
    # chapitre est tombé, et le poids en séances le suit. L'ORDRE, lui, reste
    # celui du programme de l'enseignant : en physique les chapitres
    # s'enchaînent, la dynamique a besoin de la cinématique et l'induction du
    # champ magnétique — on ne peut pas les trier par fréquence sans casser
    # ces dépendances.
    "bac-physique": [
        ("Cinématique et mouvements", 4),                                 # 11/18
        ("Dynamique : relation fondamentale et énergie cinétique", 4),    #  9/18
        ("Interaction et champ gravitationnel, satellites et planètes", 3),  # 5/18
        ("Mouvement d'un projectile dans le champ de pesanteur", 3),      #  5/18
        ("Particule chargée dans un champ électrostatique", 2),           #  3/18
        ("Solide en rotation et théorème de Huygens", 2),                 #  2/18
        ("Oscillations mécaniques libres : pendule élastique", 2),        #  2/18
        ("Champ magnétique et loi de Laplace", 5),                        # 14/18
        ("Induction électromagnétique et auto-induction", 4),             # 12/18
        ("Oscillations électriques et courant alternatif", 5),            # 12/18
        ("Ondes électromagnétiques", 1),                                  #  0/18
        ("Optique ondulatoire : interférences lumineuses", 4),            #  9/18
        ("Effet photoélectrique et niveaux d'énergie de l'atome", 3),     #  4/18
        ("Physique nucléaire : noyau, radioactivité, réactions", 5),      # 12/18
    ],
    # Chimie de Terminale SM/SE : 30 sessions relevées, de 1993 à 2025. La
    # fréquence entre parenthèses est le nombre de sessions où le chapitre
    # est tombé. L'ordre les suit, à une exception près : un chapitre ne
    # passe jamais avant celui dont il a besoin. Le pH des acides forts
    # (16) remonte donc devant les couples (21), et les alcools (15)
    # devant les acides carboxyliques (16) — on ne fait pas d'ester sans
    # alcool. Les poids en séances suivent les durées de l'enseignant :
    # acides et bases 40 heures, cinétique 25.
    "bac-chimie": [
        ("pH, acides forts et bases fortes", 4),                        # 16/30
        ("Couples acide-base et constante d'acidité", 4),               # 21/30
        ("Dosage acido-basique", 3),                                    # 21/30
        ("Alcools et polyalcools", 3),                                  # 15/30
        ("Acides carboxyliques et leurs dérivés", 4),                   # 16/30
        ("Vitesse de réaction : formation et disparition", 4),          # 15/30
        ("Aldéhydes, cétones et oxydation des alcools", 3),             # 11/30
        ("Solutions tampon", 2),                                        # 10/30
        ("Mécanisme réactionnel et catalyse", 3),                       #  9/30
        ("Stéréochimie : conformation, isomérie Z/E, énantiomérie", 4), #  9/30
        ("Amines et amides", 3),                                        #  9/30
        ("Facteurs cinétiques : concentration, température, pression", 3),  # 6/30
        ("Réactions acido-basiques et courbes de pH", 4),               #  5/30
        ("Classification des couples et indicateurs colorés", 3),       #  4/30
        ("Des acides α-aminés aux protéines", 3),                       #  2/30
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
    # Philosophie de Terminale SS : relevée sur le programme manuscrit d'un
    # enseignant (15 octobre 2025). AUCUNE ANNALE pour cette série : aucune
    # fréquence ici, et il ne faut pas en inventer. L'ordre est celui du
    # cahier, qui est aussi celui de l'année scolaire.
    #
    # Les deux méthodes passent en PREMIER, avant toute matière, et c'est
    # délibéré : un élève qui connaît l'esthétique sans savoir disserter
    # n'a aucun point. La forme s'apprend avant le fond, et elle resservira
    # à chaque chapitre.
    "bac-philo": [
        ("Méthode de la dissertation philosophique", 5),
        ("Méthode de l'explication de texte", 4),
        ("L'esthétique : art, artisanat, technique, le beau et le laid", 3),
        ("Les différentes formes d'art et leur classification", 2),
        ("L'art africain et ses sept fonctions", 4),
        ("L'État, le Droit et la Morale", 4),
        ("Les grandes conceptions de la morale", 4),
        ("Les droits de l'homme et les droits des peuples", 3),
        ("La liberté, la démocratie et la bonne gouvernance", 4),
        ("L'épistémologie : définition et objet", 2),
        ("Les sciences de la nature : méthode, faits, lois, théories", 4),
        ("Causalité, déterminisme et finalité", 3),
        ("Les sciences humaines", 3),
        ("Le problème de la vérité : critères et caractéristiques", 4),
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
