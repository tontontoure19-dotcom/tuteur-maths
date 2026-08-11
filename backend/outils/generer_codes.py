"""Fabrique des codes d'accès, sans jamais écraser ceux déjà distribués.

Les codes sont AJOUTÉS à la fin de backend/codes.txt (jamais envoyé sur
GitHub) : ce fichier est votre seule trace de qui a reçu quel code, et le
perdre vous empêcherait de couper l'accès à une personne en particulier.

    CODES.bat              5 codes BEPC et 5 codes BAC
    CODES.bat BEPC BAC     un code de chaque
    CODES.bat ADMIN        votre code de responsable (voir tous les élèves)
"""
import secrets
import sys
from datetime import date
from pathlib import Path

# Sans les caractères ambigus (0/O, 1/I/l) : le code est dicté par WhatsApp.
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"

DOSSIER = Path(__file__).resolve().parent.parent
FICHIER = DOSSIER / "codes.txt"

ENTETE = (
    "Codes d'accès — un par testeur. Ne donnez jamais le même code à deux personnes.\n"
    "Notez à côté de chaque code le nom de la personne à qui vous l'avez donné.\n"
    "Ce fichier n'est jamais écrasé : les nouveaux codes s'ajoutent à la fin.\n"
)


def fabriquer(prefixe: str) -> str:
    """Ex. : BEPC-K7M2Q4 — le préfixe dit tout de suite qui c'est."""
    return prefixe + "-" + "".join(secrets.choice(ALPHABET) for _ in range(6))


def main() -> None:
    # Par défaut : les 5 candidats BEPC et les 5 candidats BAC du test.
    demandes = [p.upper() for p in sys.argv[1:]] or ["BEPC"] * 5 + ["BAC"] * 5
    codes = [fabriquer(p) for p in demandes]
    admin = [c for c in codes if c.startswith("ADMIN-")]
    testeurs = [c for c in codes if not c.startswith("ADMIN-")]

    bloc = [""] if FICHIER.exists() else [ENTETE]
    bloc.append(f"--- Ajoutés le {date.today():%d/%m/%Y} ---")
    bloc += [f"{code}   →  ................................" for code in codes]

    if testeurs:
        bloc += ["",
                 "À AJOUTER à la fin de CODE_ACCES dans Render, précédé d'une virgule.",
                 "NE REMPLACEZ PAS la ligne existante : vos testeurs actuels seraient",
                 "tous déconnectés.",
                 "," + ",".join(testeurs)]
    if admin:
        bloc += ["",
                 "Votre code de responsable : à coller dans Render sous CODE_ADMIN",
                 "(variable à part, PAS dans CODE_ACCES). Ne le donnez à personne.",
                 admin[0]]

    with FICHIER.open("a", encoding="utf-8") as f:
        f.write("\n".join(bloc) + "\n")

    print(f"\n  {len(codes)} code(s) ajouté(s) à la fin de : {FICHIER}")
    print("  Les codes déjà distribués n'ont pas été touchés.\n")


if __name__ == "__main__":
    main()
