"""
Module A : Idéation — Génération des prompts d'images via Gemini (texte).
Prend un thème et génère une liste de descriptions détaillées pour chaque page de coloriage.
"""
from __future__ import annotations

from google import genai
from config import TEXT_MODEL

import json
import os


def generate_prompts(client: genai.Client, theme: str, num_pages: int = 20, output_folder: str = None) -> list[str]:
    """
    Genere les prompts des pages interieures du livre en fonction du theme.
    Args:
        client: Instance du client Google GenAI.
        theme: Le thème du livre de coloriage (ex: "dinosaures mignons").
        num_pages: Le nombre total de pages de coloriage souhaitées.
        output_folder: Dossier de destination pour sauvegarder les prompts (optionnel).

    Returns:
        Une liste de chaînes de caractères, chaque élément étant un prompt image.
    """
    print(f"\n[Phase A] Generation de {num_pages} idees de dessins sur le theme : '{theme}'...")

    system_prompt = f"""You are a creative French children's coloring book designer for Amazon KDP.
Generate EXACTLY {num_pages} unique scene descriptions for a toddler coloring book aged 2-7.

THEME: "{theme}"

CULTURAL RULES:
- Think like a French local, not a tourist.
- For Easter: use chocolate bells, chocolate eggs, chocolate fish, children hunting eggs in gardens — NOT just Easter bunnies.
- ABSOLUTELY NO TOURIST CLICHÉS: no croissants, no baguettes, no berets, no Eiffel Tower unless the theme is specifically Paris.
- Write all descriptions in English.

YOUR JOB — CRITICAL:
You are not just naming a subject. You must describe a COMPLETE MINI SCENE with enough detail for an image AI to place every element correctly. Each description must specify:
1. WHAT the main subject is
2. WHAT it is doing or its pose
3. WHERE it is positioned on the page (always centered)

SIMPLICITY IS THE ABSOLUTE RULE:
- 1 main subject only, always centered on the page.
- The subject floats alone on a pure white background.
- Nothing else. No background. No scenery. No environment.

SECONDARY ELEMENT — EXTREMELY RESTRICTED:
95% of scenes must have ZERO secondary element.
The main subject is completely alone on the white page.

The ONLY exception (maximum 1 scene in the whole list):
A secondary element is allowed ONLY if it is physically attached to or naturally part of the main subject AND directly touching or overlapping it.

VALID secondary element examples:
- A fish with a small seaweed touching its tail
- A chick standing on top of a cracked eggshell
- A bunny holding a flower directly in its paw
- A bell with a ribbon tied directly onto it
- A child holding an egg in both hands

INVALID — always forbidden:
- Any floating element disconnected from the main subject
- Any element placed in a corner or edge of the page
- A cloud floating above any subject
- A sun placed near any subject
- Any element that does not physically touch the main subject
- Any background, scenery, grass, sky, or environment

SUBJECT VARIETY — enforce strictly across the full list:
- Objects alone (Easter egg, chocolate bell, basket, chocolate fish, bouquet of flowers): at least 30%.
- Single animal alone (bunny, chick, lamb, duck): at least 25%.
- Single child alone: at least 25%.
- Simple action scene (child running, jumping, painting): max 20%.
- No subject type may repeat more than 3 times total.

POSE AND EXPRESSION VARIETY — enforce strictly:
Each subject must have a unique pose or expression.
Vary between: sitting, standing, jumping, sleeping, laughing, surprised, proud, shy, running, holding something, looking up, looking sideways, curled up, stretching, waving.
No two scenes may share the same pose.

WRITING FORMAT — mandatory for every description:
"[Main subject] [precise pose and expression], centered alone on the page."
OR for the rare exception:
"[Main subject] [precise pose], centered on the page, [secondary element physically attached to subject]."

EXAMPLES OF GOOD DESCRIPTIONS:
- "A large round Easter egg standing upright, centered alone, decorated with three simple bold stripes across its middle."
- "A chubby Easter bunny sitting cross-legged, centered alone, holding a single large egg pressed against its chest."
- "A fluffy chick standing on both feet, centered alone, beak open wide in a big surprised expression."
- "A child kneeling, centered alone, both hands reaching forward to pick up a large Easter egg."
- "A sleeping bunny curled into a tight ball, centered alone, eyes closed with a peaceful smile."
- "A smiling chocolate bell, centered alone, tilted slightly to one side with a large ribbon bow tied directly on top."
- "A happy chick perched on top of a cracked open eggshell, centered, wings spread wide in celebration."

EXAMPLES OF BAD DESCRIPTIONS — FORBIDDEN:
- "A bunny with a cloud floating above." ← disconnected secondary element
- "A chick in a spring meadow with flowers and grass." ← background and multiple elements
- "An Easter basket near a fence with eggs scattered around." ← too many elements, environment
- "A bell with a small sun in the corner." ← floating disconnected element
- "A child with a beret holding a baguette." ← tourist cliché

ANTI-REPETITION: Every description must feel completely unique in subject, pose, and expression. No two scenes alike.

OUTPUT: Numbered list only. No introduction, no conclusion."""

    response = client.models.generate_content(
        model=TEXT_MODEL,
        contents=system_prompt,
    )

    # Parse la réponse pour extraire les prompts nettoyés
    lines = response.text.strip().split('\n')
    prompts = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Enlever le numéro initial "1. ", "2. ", etc.
        if len(line) > 2 and line[0].isdigit():
            dot_pos = line.find('. ')
            if dot_pos != -1 and dot_pos < 5:
                prompts.append(line[dot_pos + 2:].strip())
            else:
                prompts.append(line)
        else:
            prompts.append(line)

    if len(prompts) < num_pages:
        print(f"  ATTENTION : Gemini a renvoye {len(prompts)} idees au lieu de {num_pages}.")
    else:
        print(f"  OK : {len(prompts)} idees generees avec succes.")

    final_prompts = prompts[:num_pages]
    
    return final_prompts


def generate_cover_prompt(client: genai.Client, theme: str, title: str = "", num_pages: int = 20) -> str:
    """
    Genere le prompt pour l'image de COUVERTURE AVANT.
    Adapte le template eprouve de l'utilisateur au theme choisi.
    """
    print(f"\n[Phase A] Generation du prompt de couverture AVANT pour : '{theme}'...")

    display_title = title if title else f"Coloriage {theme.title()}"

    prompt = f"""You are an expert children's coloring book cover designer.
I will give you a PERFECT template prompt for a coloring book front cover about Easter.
Your job is to ADAPT this template to the theme "{theme}" with the title "{display_title}".

ORIGINAL TEMPLATE (Easter version):
---
Children's Easter coloring book cover illustration, vertical portrait format, 3:4 aspect ratio.

BACKGROUND: Single warm golden-yellow gradient covering the ENTIRE image top to bottom, no divisions.

TOP 35%: Large chunky bubbly title "Coloriage Paques" in enormous bold rounded letters, each letter a different bright color (pink, green, blue, orange, purple), thick black outline. Below: "2-7 ans" in white bubbly letters with black outline.

BOTTOM 65%: A fun Easter scene with THREE characters - one large chubby white bunny in the center (occupying 65% of image height), one small yellow chick on the left, one small pastel purple bunny on the right. All characters have simple rounded shapes, flat solid colors, very thick bold black outlines, simple round eyes, NO sparkles, NO fur texture. The main bunny holds a large white Easter egg, pure white with black outline only. Around the characters: 4-5 colorful Easter eggs on the ground (striped and dotted patterns), 3-4 simple bold spring flowers. A simple green grass strip at the bottom.

BOTTOM: Small pastel green ribbon banner with "L'Atelier" in white bubbly letters with black outline, integrated into the grass.

Flat colors only, no shading on characters, no gradients on elements. Thick black outlines throughout. No white bands. Full bleed. No additional text, no watermark.
---

YOUR TASK:
Rewrite this EXACT same prompt structure but replace:
- "Easter" references with "{theme}" adapted to authentic FRENCH CULTURE (use exact local traditions, NO tourist cliches like croissants or berets).
- "Coloriage Paques" with "{display_title}"
- "20" with "{num_pages}"
- "bunny, chick, spring flowers, Easter eggs" with elements that match "{theme}" for a French audience.
- Keep the EXACT same style rules, background, layout percentages, and technical instructions.
- Keep "L'Atelier" and age references unchanged.

Return ONLY the adapted prompt, nothing else."""

    response = client.models.generate_content(
        model=TEXT_MODEL,
        contents=prompt,
    )
    cover_prompt = response.text.strip()
    print(f"  OK : Prompt de couverture AVANT genere.")
    return cover_prompt


def generate_back_cover_prompt(client: genai.Client, theme: str, title: str = "", num_pages: int = 20) -> str:
    """
    Genere le prompt pour la 4EME DE COUVERTURE (dos du livre).
    Adapte le template eprouve de l'utilisateur au theme choisi.
    """
    print(f"\n[Phase A] Generation du prompt de 4eme de couverture pour : '{theme}'...")

    display_title = title if title else f"Coloriage {theme.title()}"

    prompt = f"""You are an expert children's coloring book cover designer.
I will give you a PERFECT template prompt for a coloring book BACK COVER about Easter.
Your job is to ADAPT this template to the theme "{theme}" with the title "{display_title}" and {num_pages} coloring pages.

ORIGINAL TEMPLATE (Easter version):
---
Children's Easter coloring book BACK COVER illustration, vertical portrait format, 3:4 aspect ratio.

BACKGROUND: Single warm golden-yellow gradient covering the entire image, same tone as #F5A623, no divisions. Very lightly scattered small Easter eggs and tiny daisy flowers across the whole background as a subtle pattern, not dense, leaving breathing space.

CENTER: A large white rounded rectangle panel, thick green bold outline (6px), centered. Inside the panel:

    "Coloriage Paques" in chunky bubbly multicolor letters (pink, green, blue, orange, purple) with thick black outline

    Small rounded badge "2-7 ans" in bright blue with white text

    French description text in clean black rounded font:
    "Prends tes crayons et c'est parti ! Ce livre contient 30 coloriages amusants concus pour les tout-petits. Grands dessins simples avec de gros contours pour les premieres seances de coloriage !"

AROUND THE PANEL: 4 small characters in Bold and Easy cartoon style - simple rounded shapes, flat solid colors, very thick bold black outlines (6px), simple round black eyes, NO cheek blush, NO sparkles, NO fur texture, NO gradients on characters:

    Top left: a small chubby white bunny
    Top right: a decorated colorful Easter egg
    Bottom left: a simple yellow chick
    Bottom right: a pink tulip with green stem

BOTTOM CENTER: Small pastel green ribbon banner with "L'Atelier" in white bubbly letters with black outline.

BOTTOM RIGHT: Plain white rectangle (55mm x 35mm) thick black outline, completely empty, for ISBN barcode.

Flat colors only, no shading, no gradients on characters. Thick black outlines throughout. Full bleed. No extra text, no watermark.
---

YOUR TASK:
Rewrite this EXACT same prompt structure but replace:
- "Easter" references with "{theme}" adapted to authentic FRENCH CULTURE (use exact local traditions, NO tourist cliches like croissants or berets).
- "Coloriage Paques" with "{display_title}"
- "30 coloriages" with "{num_pages} coloriages"
- The 4 characters around the panel with elements that match "{theme}" for a French audience (keep exactly 4, same positions).
- The scattered background pattern with theme-appropriate small objects.
- Keep the EXACT same style rules, panel, badge, ISBN rectangle, "L'Atelier" banner, and description text structure.
- Keep "2-7 ans" unchanged.

Return ONLY the adapted prompt, nothing else."""

    response = client.models.generate_content(
        model=TEXT_MODEL,
        contents=prompt,
    )
    back_prompt = response.text.strip()
    print(f"  OK : Prompt de 4eme de couverture genere.")
    return back_prompt

