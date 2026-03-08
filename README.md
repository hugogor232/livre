# 🚀 Gemini KDP Creator

Outil 100% automatisé pour générer des **livres de coloriage** prêts à être publiés sur **Amazon KDP**, en utilisant exclusivement l'IA Google Gemini (gratuit avec vos crédits).

## ⚡ Installation

### 1. Installer Python (3.10 ou supérieur)
Téléchargez Python sur [python.org](https://www.python.org/downloads/) si ce n'est pas déjà fait.

### 2. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 3. Configurer votre clé API Gemini
Obtenez votre clé gratuite sur [Google AI Studio](https://aistudio.google.com/apikey), puis :
```bash
# Windows (PowerShell)
$env:GEMINI_API_KEY = "votre_cle_ici"

# Windows (CMD)
set GEMINI_API_KEY=votre_cle_ici

# Linux / Mac
export GEMINI_API_KEY=votre_cle_ici
```

## 🎮 Utilisation

```bash
# Livre de coloriage de 20 pages sur les dinosaures
python run.py --theme "dinosaures mignons" --pages 20

# Avec un titre personnalisé
python run.py --theme "chats astronautes" --pages 30 --title "Les Chats de l'Espace"

# Avec un délai plus long entre les appels API (si erreurs de quota)
python run.py --theme "robots" --pages 25 --delay 6
```

## 📁 Fichiers générés

Après exécution, vous trouverez dans le dossier `output/<theme>/` :

| Fichier | Description |
|---|---|
| `KDP_Interieur_<theme>.pdf` | Le PDF intérieur prêt pour KDP (pages recto coloriage / verso blanc) |
| `KDP_Couverture_<theme>.pdf` | Le PDF de couverture à plat (4ème + tranche + 1ère de couverture) |
| `pages/` | Les images PNG brutes (inspectez et supprimez les défauts avant de republier) |
| `cover_image.png` | L'image de couverture en couleurs |

## 📋 Comment publier sur Amazon KDP

1. Allez sur [kdp.amazon.com](https://kdp.amazon.com) et connectez-vous.
2. Cliquez sur **"Créer un nouveau titre"** > **Livre broché**.
3. Remplissez les métadonnées (titre, auteur, description).
4. Uploadez `KDP_Interieur_<theme>.pdf` comme **manuscrit**.
5. Uploadez `KDP_Couverture_<theme>.pdf` comme **couverture**.
6. **⚠️ IMPORTANT** : Cochez **"AI-generated"** dans la section sur le contenu IA.
7. Fixez votre prix et publiez !

## 🏗️ Architecture du projet

```
livre/
├── run.py                  # Script principal (point d'entrée)
├── config.py               # Configuration (dimensions KDP, modèles IA)
├── requirements.txt        # Dépendances Python
├── README.md               # Ce fichier
└── modules/
    ├── __init__.py
    ├── ideation.py          # Phase A : Génération des prompts texte
    ├── illustration.py      # Phase B : Génération des images IA
    └── compiler.py          # Phase C : Assemblage PDF KDP
```
