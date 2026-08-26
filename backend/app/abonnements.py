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
        return _aujourdhui() <= date.fromisoformat(abonnement["expire_le"])

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
            fin = date.fromisoformat(abonnement["expire_le"])
            liste.append({
                "code": code,
                **abonnement,
                "jours_restants": (fin - _aujourdhui()).days,
                "expire": fin < _aujourdhui(),
            })
        liste.sort(key=lambda a: (not a["actif"], a["jours_restants"]))
        return liste
