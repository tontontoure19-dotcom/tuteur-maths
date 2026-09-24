"""Les abonnements : qui a le droit d'utiliser le répétiteur, et jusqu'à quand.

Jusqu'ici les codes vivaient dans une variable d'environnement : en créer un
demandait de modifier Render et de redéployer le service. Impensable dès
qu'un parent paie et attend son accès dans la minute.

Ils vivent désormais dans un fichier sur le disque persistant. Créer, couper
ou prolonger un abonnement devient immédiat, et chaque code porte une date
d'expiration — celle de l'essai gratuit comme celle du mois payé.

Les codes de la variable d'environnement restent valables et sans limite de
durée : ce sont ceux des testeurs, personne ne doit être coupé.
"""
import json
import secrets
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

# Sans les caractères ambigus (0/O, 1/I/l) : le code se dicte au téléphone.
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"

JOURS_ESSAI = 10
JOURS_MOIS = 30
JOURS_SEMAINE = 7


def _aujourdhui() -> date:
    return datetime.now(timezone.utc).date()


class Abonnements:
    """Le registre des abonnements, rangé sur le disque persistant."""

    def __init__(self, fichier: Path):
        self.fichier = fichier
        self.fichier.parent.mkdir(parents=True, exist_ok=True)

    # ----- lecture et écriture -------------------------------------------

    def _lire(self) -> dict[str, dict]:
        if not self.fichier.exists():
            return {}
        try:
            return json.loads(self.fichier.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            # Un fichier illisible ne doit jamais couper l'accès à tout le
            # monde : on repart d'un registre vide, les codes hérités restent.
            return {}

    def _ecrire(self, registre: dict[str, dict]) -> None:
        # Écriture par fichier temporaire : une coupure en plein milieu ne
        # laisse pas un registre à moitié écrit.
        provisoire = self.fichier.with_suffix(".tmp")
        provisoire.write_text(json.dumps(registre, ensure_ascii=False, indent=1),
                              encoding="utf-8")
        provisoire.replace(self.fichier)

    # ----- création et modification --------------------------------------

    def fabriquer_code(self, prefixe: str) -> str:
        """Ex. : BEPC-K7M2Q4. Recommence tant que le code existe déjà."""
        registre = self._lire()
        while True:
            code = prefixe.upper() + "-" + "".join(secrets.choice(ALPHABET) for _ in range(6))
            if code not in registre:
                return code

    def creer(self, nom: str, niveau: str = "bepc",
              formule: Literal["essai", "semaine", "mois"] = "essai",
              telephone: str = "") -> dict:
        """Ouvre un abonnement et rend le code à donner à l'élève."""
        jours = {"essai": JOURS_ESSAI, "semaine": JOURS_SEMAINE, "mois": JOURS_MOIS}[formule]
        code = self.fabriquer_code("BAC" if niveau == "bac" else "BEPC")

        registre = self._lire()
        registre[code] = {
            "nom": nom.strip(),
            "niveau": niveau,
            "telephone": telephone.strip(),
            "formule": formule,
            "cree_le": _aujourdhui().isoformat(),
            "expire_le": (_aujourdhui() + timedelta(days=jours)).isoformat(),
            "actif": True,
        }
        self._ecrire(registre)
        return {"code": code, **registre[code]}

    def prolonger(self, code: str,
                  formule: Literal["semaine", "mois"] = "mois") -> dict | None:
        """Renouvellement après paiement.

        On repart de la date d'expiration quand elle est encore devant nous :
        un parent qui paie en avance ne doit pas perdre les jours restants.
        """
        registre = self._lire()
        if code not in registre:
            return None

        jours = {"semaine": JOURS_SEMAINE, "mois": JOURS_MOIS}[formule]
        fin = date.fromisoformat(registre[code]["expire_le"])
        depart = max(fin, _aujourdhui())

        registre[code]["expire_le"] = (depart + timedelta(days=jours)).isoformat()
        registre[code]["formule"] = formule
        registre[code]["actif"] = True
        self._ecrire(registre)
        return {"code": code, **registre[code]}

    def renommer(self, code: str, nom: str) -> dict | None:
        """Corrige le nom de l'abonné, sans toucher à rien d'autre.

        Le travail de l'élève n'est pas rangé sous ce nom mais sous le code :
        le renommer ne fait rien perdre.
        """
        registre = self._lire()
        if code not in registre:
            return None
        registre[code]["nom"] = nom.strip()
        self._ecrire(registre)
        return {"code": code, **registre[code]}

    def retirer(self, code: str, nom: str = "") -> dict:
        """Coupe un accès de TESTEUR sans passer par Render.

        Les codes des testeurs vivent dans la variable d'environnement
        CODE_ACCES : les enlever oblige à éditer une liste séparée par des
        virgules dans le tableau de bord, avec le risque d'effacer le mauvais
        code, et à redéployer. On inscrit donc le retrait ici, sur le disque
        persistant, et c'est lui qui l'emporte à la vérification.

        Le retrait est réversible par « rendre » : on ne perd jamais ce qu'on
        sait d'un testeur, au cas où il reviendrait.
        """
        registre = self._lire()
        entree = registre.get(code, {})
        entree.update({
            "nom": nom.strip() or entree.get("nom", "—"),
            "niveau": entree.get("niveau"),
            "formule": "testeur retiré",
            "retire_le": _aujourdhui().isoformat(),
            "retire": True,
            "actif": False,
        })
        registre[code] = entree
        self._ecrire(registre)
        return {"code": code, **entree}

    def rendre(self, code: str) -> dict | None:
        """Annule un retrait ou une coupure : l'accès revient tel qu'il était.

        Sert aux deux cas, et c'est voulu : un testeur retiré comme un abonné
        coupé se rendent de la même façon. Surtout, la date d'expiration n'est
        PAS touchée — sans cela, le seul moyen de rouvrir un abonné coupé
        serait de lui ajouter un mois qu'il n'a pas payé.
        """
        registre = self._lire()
        entree = registre.get(code)
        if entree is None or (entree.get("actif") and not entree.get("retire")):
            return None
        entree.pop("retire", None)
        entree.pop("retire_le", None)
        entree["actif"] = True
        self._ecrire(registre)
        return {"code": code, **entree}

    def est_retire(self, code: str) -> bool:
        """Cet accès a-t-il été retiré à la main ?"""
        return bool(self._lire().get(code, {}).get("retire"))

    def couper(self, code: str) -> dict | None:
        """Suspend un abonnement sans effacer ce qu'on sait de lui."""
        registre = self._lire()
        if code not in registre:
            return None
        registre[code]["actif"] = False
        self._ecrire(registre)
        return {"code": code, **registre[code]}

    # ----- consultation ---------------------------------------------------

    def valide(self, code: str) -> bool:
        """Ce code ouvre-t-il l'accès aujourd'hui ?"""
        abonnement = self._lire().get(code)
        if not abonnement or not abonnement.get("actif"):
            return False
        fin = abonnement.get("expire_le")
        return bool(fin) and _aujourdhui() <= date.fromisoformat(fin)

    def details(self, code: str) -> dict | None:
        abonnement = self._lire().get(code)
        return {"code": code, **abonnement} if abonnement else None

    def tous(self) -> list[dict]:
        """Tous les abonnements, les plus proches de l'expiration en premier.

        C'est l'ordre utile : ce sont ceux-là qu'il faut relancer.
        """
        registre = self._lire()
        liste = []
        for code, abonnement in registre.items():
            # Un testeur retiré n'a pas de date de fin : il n'en a jamais eu.
            # Le registre ne doit jamais pouvoir casser la page du responsable,
            # on lit donc la date sans supposer qu'elle est là.
            brut = abonnement.get("expire_le")
            fin = date.fromisoformat(brut) if brut else None
            liste.append({
                "code": code,
                **abonnement,
                "jours_restants": (fin - _aujourdhui()).days if fin else None,
                "expire": bool(fin and fin < _aujourdhui()),
            })
        # Les sans-date passent en dernier : ce sont les accès retirés.
        liste.sort(key=lambda a: (not a["actif"],
                                  a["jours_restants"] is None,
                                  a["jours_restants"] or 0))
        return liste
