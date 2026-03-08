"""
╔══════════════════════════════════════════════════════╗
║           GEMINI KDP CREATOR - v1.0                  ║
║   Générateur de livres de coloriage Amazon KDP       ║
║   100% automatisé via Google Gemini (gratuit)        ║
╚══════════════════════════════════════════════════════╝

Usage :
    python run.py --theme "dinosaures mignons" --pages 30 --title "Mon Livre Dino"
    python run.py --theme "chats" --pages 20 --api-key "AIza..."
"""
import os
import sys
import argparse

from google import genai

from config import GEMINI_API_KEY, OUTPUT_BASE_DIR
from modules.ideation import generate_prompts, generate_cover_prompt, generate_back_cover_prompt
from modules.illustration import generate_coloring_images, generate_cover_image, generate_back_cover_image
from modules.compiler import create_interior_pdf, create_cover_pdf, create_preview_pdf


def main():
    # ========================
    #  ARGUMENTS CLI
    # ========================
    parser = argparse.ArgumentParser(
        description="Gemini KDP Creator - Genere un livre de coloriage complet pour Amazon KDP.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation :
  python run.py --theme "chats astronautes" --pages 20
  python run.py --theme "animaux de la ferme" --pages 30 --title "La Ferme en Couleurs"
  python run.py --theme "mandalas de fleurs" --pages 40 --delay 5
  python run.py --theme "robots" --pages 10 --api-key "AIzaSy..."
        """
    )
    parser.add_argument(
        "--theme", type=str, required=True,
        help="Le theme de votre livre (ex: 'dinosaures mignons', 'robots dans l espace')."
    )
    parser.add_argument(
        "--pages", type=int, default=20,
        help="Nombre de pages de coloriage a generer (defaut: 20)."
    )
    parser.add_argument(
        "--title", type=str, default=None,
        help="Titre du livre (defaut: genere automatiquement a partir du theme)."
    )
    parser.add_argument(
        "--delay", type=float, default=4.0,
        help="Pause en secondes entre chaque appel API image (defaut: 4s)."
    )
    parser.add_argument(
        "--api-key", type=str, default=None,
        help="Cle API Gemini (alternative a la variable d'environnement GEMINI_API_KEY)."
    )

    args = parser.parse_args()

    # Titre auto si non fourni
    if args.title is None:
        args.title = f"Coloriage {args.theme.title()}"

    # ========================
    #  INITIALISATION
    # ========================
    # Priorité : argument CLI > variable d'environnement
    api_key = args.api_key or GEMINI_API_KEY

    if not api_key:
        print("=" * 60)
        print("ERREUR : Cle API Gemini non configuree !")
        print("")
        print("Option 1 - En argument :")
        print('  python run.py --theme "test" --api-key "votre_cle_ici"')
        print("")
        print("Option 2 - Variable d'environnement :")
        print('  PowerShell : $env:GEMINI_API_KEY = "votre_cle_ici"')
        print('  CMD        : set GEMINI_API_KEY=votre_cle_ici')
        print('  Linux/Mac  : export GEMINI_API_KEY=votre_cle_ici')
        print("")
        print("Obtenez votre cle gratuite sur : https://aistudio.google.com/apikey")
        print("=" * 60)
        sys.exit(1)

    # Créer le client GenAI
    client = genai.Client(api_key=api_key)

    # Créer le dossier de sortie
    safe_theme = args.theme.replace(" ", "_").lower()
    output_folder = os.path.join(OUTPUT_BASE_DIR, safe_theme)
    os.makedirs(output_folder, exist_ok=True)

    # ========================
    #  LANCEMENT DU PIPELINE
    # ========================
    print("=" * 60)
    print("GEMINI KDP CREATOR - Demarrage")
    print(f"   Theme       : {args.theme}")
    print(f"   Titre       : {args.title}")
    print(f"   Pages       : {args.pages}")
    print(f"   Sortie      : {output_folder}/")
    print("=" * 60)

    # ========================
    #  GÉNÉRATION DU LIVRE
    # ========================

    # ---- Phase A : Idéation ----
    interior_prompts = generate_prompts(client, args.theme, num_pages=args.pages)
    if not interior_prompts:
        print("\nERREUR CRITIQUE : Aucun prompt n'a ete genere. Verifiez votre connexion et votre cle API.")
        sys.exit(1)

    cover_prompt = generate_cover_prompt(client, args.theme, title=args.title, num_pages=args.pages)
    back_cover_prompt = generate_back_cover_prompt(client, args.theme, title=args.title, num_pages=args.pages)

    # Sauvegarde de tous les prompts
    all_prompts = {
        "interior": interior_prompts,
        "cover": cover_prompt,
        "back_cover": back_cover_prompt
    }
    prompts_file = os.path.join(output_folder, "prompts.json")
    import json
    with open(prompts_file, "w", encoding="utf-8") as f:
        json.dump(all_prompts, f, ensure_ascii=False, indent=4)
    print(f"  -> Tous les prompts sauvegardes dans : {prompts_file}")

    # ---- Phase B : Illustration ----
    image_paths = generate_coloring_images(client, interior_prompts, output_folder, delay=args.delay)
    if not image_paths:
        print("\nERREUR CRITIQUE : Aucune image n'a pu etre generee.")
        print("   Causes possibles : quota API epuise, modele Imagen indisponible, ou erreur reseau.")
        sys.exit(1)

    cover_image_path = generate_cover_image(client, cover_prompt, output_folder)
    back_cover_image_path = generate_back_cover_image(client, back_cover_prompt, output_folder)

    # ---- Phase C : Compilation PDF ----
    interior_pdf = os.path.join(output_folder, f"KDP_Interieur_{safe_theme}.pdf")
    cover_pdf = os.path.join(output_folder, f"KDP_Couverture_{safe_theme}.pdf")
    preview_pdf = os.path.join(output_folder, f"Preview_Complet_{safe_theme}.pdf")

    total_pages = create_interior_pdf(image_paths, interior_pdf, book_title=args.title)
    create_preview_pdf(image_paths, preview_pdf, 
                       cover_path=cover_image_path, 
                       back_cover_path=back_cover_image_path, 
                       book_title=args.title)
    create_cover_pdf(cover_image_path, cover_pdf, total_pages, book_title=args.title, back_cover_image_path=back_cover_image_path)

    # ========================
    #  RÉSUMÉ FINAL
    # ========================
    print("\n" + "=" * 60)
    print("SUCCES ! Votre livre KDP est pret !")
    print("=" * 60)
    print(f"   Dossier de sortie  : {output_folder}/")
    print(f"   PDF Interieur      : {interior_pdf}")
    print(f"   PDF Couverture     : {cover_pdf}")
    print(f"   PDF Aperçu Complet : {preview_pdf}")
    print(f"   Images brutes      : {output_folder}/pages/")
    print(f"   Pages totales      : {total_pages}")
    print("")
    print("Prochaines etapes :")
    print("   1. Verifiez les images dans le dossier 'pages/' (supprimez celles qui ont des defauts).")
    print("   2. Relancez le script ou uploadez directement les PDFs sur https://kdp.amazon.com")
    print("   3. N'oubliez PAS de cocher 'AI-generated' lors de la publication sur KDP !")
    print("=" * 60)


if __name__ == "__main__":
    main()
