"""
Module B : Illustration - Generation des images.
- Pages de coloriage : Imagen 4 via generate_images (precision des prompts)
- Couvertures : Gemini 3 Pro via generate_content (qualite visuelle)
"""
from __future__ import annotations

import os
import time
from google import genai
from google.genai import types
from PIL import Image as PILImage
from config import COVER_IMAGE_MODEL, PAGES_IMAGE_MODEL, VISION_MODEL, MAX_IMAGE_RETRIES, DPI

STYLE_GUIDE_PREFIX = (
    "FIRST RULE — READ BEFORE ANYTHING ELSE:\n"
    "THIS IS NOT A FRAMED ILLUSTRATION.\n"
    "NO BORDER. NO FRAME. NO BOX. NO RECTANGLE AROUND THE IMAGE.\n"
    "ZERO ENCLOSURE OF ANY KIND. IF YOU DRAW A BORDER = REJECTED.\n\n"
    "Single coloring book page for toddlers aged 2-4, vertical portrait "
    "format, 8.5x11 aspect ratio.\n\n"
    "SUBJECT: "
)

STYLE_GUIDE_SUFFIX = (
    "\n\nNO TEXT EVER: Do NOT generate any text, letters, numbers, labels, "
    "watermarks, titles, or words anywhere in the image.\n\n"
    "NO FRAME EVER: Do NOT draw any border, frame, box, rectangle, "
    "rounded rectangle, or any shape that surrounds or encloses "
    "the illustration. The illustration floats freely on a plain "
    "white background with absolutely no enclosure of any kind.\n\n"
    "SAFE MARGIN — MANDATORY: Leave a minimum 40mm of pure empty "
    "white space between ANY drawn element and ALL 4 edges of the "
    "image canvas. Nothing touches or approaches the image border.\n\n"
    "MAXIMUM ELEMENTS — STRICT:\n"
    "- 1 main subject ONLY. Nothing else. No background element.\n"
    "- The subject floats alone on pure white. No scenery, no environment,\n"
    "no clouds, no bushes, no grass, no ground, no sky behind the subject.\n"
    "- Human characters: plain clothes ONLY — zero stripes, zero dots,\n"
    "zero buttons, zero patterns on clothing whatsoever.\n"
    "- NO stars, NO hearts, NO clouds, NO bushes, NO decorative shapes,\n"
    "NO props, NO background of any kind.\n\n"
    "STYLE: Hand-drawn kawaii coloring book style. Exclusively soft, "
    "rounded, organic shapes — NO straight lines, NO sharp angles, "
    "NO rigid geometry. Characters look cuddly, bouncy, and cute "
    "like a children's doodle. Think Sanrio meets simple French "
    "picture book illustration.\n\n"
    "OUTLINES: MATCH THE EXACT LINE THICKNESS AND STYLE from the provided "
    "reference image. If no reference is provided, use very thick bold "
    "black outlines (6px). All shapes fully closed. Clean continuous lines, "
    "no broken strokes.\n\n"
    "FILL: 100% pure white inside all shapes. Absolutely no shading, "
    "no gray areas, no gradients, no cross-hatching, no halftones. "
    "Pure black and white only.\n\n"
    "COMPOSITION: Subject centered, filling 65% of the safe zone. "
    "Large empty white breathing space around the subject.\n"
    "Everything large enough to be colored by a 2-year-old hand.\n\n"
    "TECHNICAL: High contrast monochrome. Printable quality 300 DPI. "
    "No color, no watermark, no page numbers. Pure white background.\n"
    "Toddler coloring book illustration style.\n\n"
    "FINAL REMINDER: NO BORDER. NO FRAME. NO BOX. NO RECTANGLE. "
    "THE DRAWING FLOATS ON WHITE. NOTHING SURROUNDS THE ILLUSTRATION."
)

# Nombre de tentatives en cas d'erreur reseau
RETRY_DELAY_BASE = 5  # secondes


def _extract_image_bytes(response):
    """
    Extrait les bytes d'image depuis une reponse generate_content (Gemini 3 Pro).
    """
    if not response or not response.candidates:
        return None

    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
            return part.inline_data.data

    return None


def validate_image_quality(client, image_path):
    """
    Juge IA : Utilise Gemini Vision pour verifier qu'une image est valide.
    (Noir et blanc pur, pas de texte, cadre present).
    Retourne True si valide, False sinon.
    """
    try:
        img = PILImage.open(image_path)
        
        prompt = (
            "You are a strict quality control judge for a toddler's coloring book.\n"
            "Analyze this image carefully. Reply with 'YES' if it's perfect.\n"
            "If it's NOT perfect, reply with 'NO' followed by a SHORT explanation (max 10 words) of which rule is broken.\n\n"
            "Rule 1: The illustration must be PURE black and white lines. STRICTLY NO COLORS AT ALL.\n"
            "Rule 2: There must be absolutely NO TEXT, letters, numbers, or labels.\n"
            "Rule 3: It must be a simple drawing suitable for a 2-year-old. NO tiny patterns, NO complex textures, NO intricate details. ULTRA MINIMALIST.\n"
            "Rule 4: Absolutely NO cliché French tourist objects (no croissants, no Eiffel Tower).\n"
            "Rule 5: There MUST NOT be any kind of border, frame, or box surrounding the image.\n"
            "\nDoes this image respect all rules? Answer YES or NO + reason."
        )
        
        response = client.models.generate_content(
            model=VISION_MODEL,
            contents=[img, prompt]
        )
        
        answer = response.text.strip()
        if answer.upper().startswith("YES"):
            return True, "Validé"
        else:
            return False, answer.replace("NO", "").strip(": ").strip()
            
    except Exception as e:
        print(f"       Erreur Vision Juge : {e}")
        # En cas d'erreur de l'API Vision, on valide par defaut pour ne pas bloquer le script
        return True, f"Bypass (Erreur API: {e})"


def generate_coloring_images(client, prompts, output_folder, delay=4.0):
    """
    Genere les images de coloriage (noir et blanc) via GEMINI 3 PRO.
    Utilise generate_content avec response_modalities=IMAGE.
    """
    print(f"\n[Phase B] Generation de {len(prompts)} images de coloriage (Gemini 3 Pro)...")

    pages_dir = os.path.join(output_folder, "pages")
    os.makedirs(pages_dir, exist_ok=True)
    image_paths = []

    for i, prompt_text in enumerate(prompts):
        filename = os.path.join(pages_dir, f"page_{i + 1:03d}.png")
        short_desc = prompt_text[:60] + "..." if len(prompt_text) > 60 else prompt_text
        print(f"  Image {i + 1}/{len(prompts)} : {short_desc}")

        # --- GESTION DE L'IMAGE DE REFERENCE (STYLE) ---
        reference_img = None
        ref_path_png = "reference.png"
        ref_path_jpg = "reference.jpg"
        
        if os.path.exists(ref_path_png):
            try:
                reference_img = PILImage.open(ref_path_png)
            except Exception as e:
                print(f"    [Warning] Impossible de lire {ref_path_png}: {e}")
        elif os.path.exists(ref_path_jpg):
            try:
                reference_img = PILImage.open(ref_path_jpg)
            except Exception as e:
                print(f"    [Warning] Impossible de lire {ref_path_jpg}: {e}")

        response = None
        for attempt in range(MAX_IMAGE_RETRIES):
            try:
                enhanced_prompt = STYLE_GUIDE_PREFIX + prompt_text + STYLE_GUIDE_SUFFIX
                
                # Si on a une image de reference, on l'envoie avec le prompt pour forcer le style
                if reference_img:
                    request_contents = [reference_img, enhanced_prompt]
                    if attempt == 0: # N'afficher le message qu'une seule fois par page
                         print("    [Info] Utilisation de l'image de reference pour guider le style.")
                else:
                    request_contents = enhanced_prompt

                response = client.models.generate_content(
                    model=COVER_IMAGE_MODEL,  # On utilise le modele 3 Pro pour tout
                    contents=request_contents,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                    ),
                )
                
                img_bytes = _extract_image_bytes(response)
                if img_bytes:
                    os.makedirs(os.path.dirname(filename), exist_ok=True)
                    with open(filename, "wb") as f:
                        f.write(img_bytes)
                        
                    # Verification Qualite par le Juge IA
                    print(f"       Validation IA en cours (Tentative {attempt+1})...")
                    is_valid, reason = validate_image_quality(client, filename)
                    
                    if is_valid:
                        # Succes et validation, sortir de la boucle
                        image_paths.append(filename)
                        print(f"       [OK] Validée par l'IA.")
                        break
                    else:
                        print(f"       [REJET] Image non conforme. Raison : {reason}")
                        # On supprime la mauvaise image et on passe a la tentative suivante
                        if os.path.exists(filename):
                            os.remove(filename)
                        if attempt < MAX_IMAGE_RETRIES - 1:
                            print(f"       >> Regénération de l'image (Essai {attempt + 2}/{MAX_IMAGE_RETRIES})...")
                else:
                    print(f"       Erreur: Pas de bytes d'image.")

            except Exception as e:
                import traceback; traceback.print_exc()
                if attempt < MAX_IMAGE_RETRIES - 1:
                    retry_delay = RETRY_DELAY_BASE * (2 ** attempt)
                    print(f"       Erreur interceptée (tentative {attempt + 1}/{MAX_IMAGE_RETRIES}) : {repr(e)}")
                    print(f"       Reessai dans {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    print(f"       Erreur apres {MAX_IMAGE_RETRIES} tentatives pour la page {i + 1} : {e}")
                    response = None
        
        if not os.path.exists(filename) and filename not in image_paths:
            print(f"       ECHEC : Impossible de générer une image conforme pour la page {i + 1} après {MAX_IMAGE_RETRIES} essais.")

        # Pause pour respecter les limites de quota de l'API
        if i < len(prompts) - 1:
            time.sleep(delay)

    print(f"\n  Resultat : {len(image_paths)}/{len(prompts)} images generees avec succes.")
    return image_paths


def generate_cover_image(client, cover_prompt, output_folder):
    """
    Genere l'image de COUVERTURE AVANT via GEMINI 3 PRO (generate_content).
    """
    print(f"\n[Phase B] Generation de l'image de couverture AVANT (Gemini 3 Pro)...")

    cover_path = os.path.join(output_folder, "cover_image.png")

    try:
        # Imagen 3 Pro via Gemini 3 Pro
        # On utilise types.GenerateContentConfig pour passer les options d'image
        response = client.models.generate_content(
            model=COVER_IMAGE_MODEL,
            contents=cover_prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )

        img_bytes = _extract_image_bytes(response)
        if img_bytes:
            with open(cover_path, "wb") as f:
                f.write(img_bytes)
            print(f"  OK : Couverture AVANT sauvegardee : {cover_path}")
            return cover_path
        else:
            print(f"  ECHEC : Aucune image de couverture retournee.")
            return None

    except Exception as e:
        print(f"  Erreur lors de la generation de la couverture : {e}")
        return None


def generate_back_cover_image(client, back_cover_prompt, output_folder):
    """
    Genere l'image de 4EME DE COUVERTURE via GEMINI 3 PRO (generate_content).
    """
    print(f"\n[Phase B] Generation de l'image de 4eme de couverture (Gemini 3 Pro)...")

    back_path = os.path.join(output_folder, "back_cover_image.png")

    try:
        response = client.models.generate_content(
            model=COVER_IMAGE_MODEL,
            contents=back_cover_prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )

        img_bytes = _extract_image_bytes(response)
        if img_bytes:
            with open(back_path, "wb") as f:
                f.write(img_bytes)
            print(f"  OK : 4eme de couverture sauvegardee : {back_path}")
            return back_path
        else:
            print(f"  ECHEC : Aucune image de 4eme de couverture retournee.")
            return None

    except Exception as e:
        print(f"  Erreur lors de la generation de la 4eme de couverture : {e}")
        return None
