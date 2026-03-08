"""
Configuration globale pour Gemini KDP Creator.
Centralise les constantes KDP (dimensions, marges) et les paramètres IA.
"""
import os

# ========================
#  CLÉ API GEMINI
# ========================
# Définissez votre clé API via la variable d'environnement GEMINI_API_KEY
# OU passez-la directement en argument --api-key lors du lancement de run.py
#
# PowerShell :  $env:GEMINI_API_KEY = "AIzaSy..."
# CMD        :  set GEMINI_API_KEY=AIzaSy...
# Linux/Mac  :  export GEMINI_API_KEY=AIzaSy...
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# ========================
#  MODÈLES IA
# ========================
# Modèle texte (pour la génération des prompts / idées de dessins)
TEXT_MODEL = "gemini-2.5-flash"

# Modèle Vision (pour valider la conformité des images générées)
VISION_MODEL = "gemini-2.5-flash"

# Modele image pour les COUVERTURES (Gemini 3 Pro - resultats testes en playground)
COVER_IMAGE_MODEL = "gemini-3-pro-image-preview"

# Modele image pour les PAGES DE COLORIAGE (Imagen 4 - suit les prompts avec precision)
PAGES_IMAGE_MODEL = "gemini-3-pro-image-preview"

# Nombre maximum de tentatives en cas de rejet par le Juge IA
MAX_IMAGE_RETRIES = 3

# ========================
#  DIMENSIONS KDP
# ========================
# Taille de page intérieure (en pouces) — Format US Letter standard pour KDP
# Avec bleed (fond perdu) : 0.125" ajouté de chaque côté
PAGE_WIDTH_NO_BLEED = 8.5    # pouces
PAGE_HEIGHT_NO_BLEED = 11.0  # pouces
BLEED = 0.125                # pouces (fond perdu ajouté de chaque côté)

PAGE_WIDTH = PAGE_WIDTH_NO_BLEED + (2 * BLEED)   # 8.75 pouces
PAGE_HEIGHT = PAGE_HEIGHT_NO_BLEED + (2 * BLEED)  # 11.25 pouces

# Marges intérieures "Safe Zone" — zone où l'image ne doit pas être coupée
SAFE_MARGIN = 0.375  # pouces (marge de sécurité ajoutée au bleed)

# Résolution d'impression Amazon KDP
DPI = 300

# ========================
#  COUVERTURE KDP
# ========================
# Épaisseur de la tranche (spine) — calculée dynamiquement selon le nombre de pages
# Formule Amazon pour papier blanc (crème serait 0.0025)
SPINE_WIDTH_PER_PAGE = 0.002252  # pouces par page (papier blanc)

# Couverture : hauteur = hauteur intérieure + 2 * bleed
COVER_HEIGHT = PAGE_HEIGHT  # 11.25 pouces

# ========================
#  DOSSIER DE SORTIE
# ========================
OUTPUT_BASE_DIR = "output"
