"""Fabrique un code d'accès par testeur.

Les codes sont écrits dans backend/codes.txt (jamais envoyé sur GitHub) :
gardez ce fichier, c'est votre liste « qui a reçu quel code ».
"""
import secrets
import sys
from pathlib import Path

# Sans les caractères ambigus (0/O, 1/I/l) : le code est dicté par WhatsApp.
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"

DOSSIER = Path(__file__).resolve().parent.parent
FICHIER = DOSSIER / "codes.txt"


def fabriquer(prefixe: str) -> str:
    """Ex. : BEPC-K7M2Q4 — le préfixe dit tout de suite qui c'est."""
    return prefixe + "-" + "".join(secrets.choice(ALPHABET) for _ in range(6))


def main() -> None:
    # Par défaut : les 5 candidats BEPC et les 5 candidats BAC du test.
    demandes = sys.argv[1:] or ["BEPC"] * 5 + ["BAC"] * 5
    codes = [fabriquer(p.upper()) for p in demandes]

    lignes = ["Codes d'accès — un par testeur. Ne partagez jamais le même code à deux personnes.",
              "Notez à côté de chaque code le nom de la personne à qui vous l'avez donné.", ""]
    lignes += [f"{code}   →  ................................" for code in codes]
    lignes += ["", "À coller dans Render, variable CODE_ACCES (une seule ligne) :", ",".join(codes)]
    FICHIER.write_text("\n".join(lignes) + "\n", encoding="utf-8")

    print(f"\n  {len(codes)} codes écrits dans : {FICHIER}\n")
    print("  Ouvrez ce fichier, copiez la derniere ligne dans Render (CODE_ACCES).\n")


if __name__ == "__main__":
    main()
