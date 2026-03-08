"""
Module C : Compilateur — Assemblage PDF aux normes Amazon KDP.
Prend les images générées et produit un PDF intérieur + un PDF couverture.
"""
from __future__ import annotations

import os
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import black, white
from PIL import Image as PILImage
from config import (
    PAGE_WIDTH, PAGE_HEIGHT, BLEED, SAFE_MARGIN, DPI,
    SPINE_WIDTH_PER_PAGE, COVER_HEIGHT
)


def create_interior_pdf(image_paths: list[str], output_path: str, book_title: str = "Coloring Book"):
    """
    Compile les images de coloriage en un PDF intérieur conforme KDP.
    Structure : [Page titre] [Verso vide] [Coloriage 1] [Verso vide] [Coloriage 2] [Verso vide] ...

    Args:
        image_paths: Liste triée des chemins vers les images PNG de coloriage.
        output_path: Chemin complet du fichier PDF à créer.
        book_title: Titre affiché sur la page de titre intérieure.
    """
    print(f"\n[Phase C] Compilation du PDF interieur ({len(image_paths)} pages de coloriage)...")

    page_w = PAGE_WIDTH * inch
    page_h = PAGE_HEIGHT * inch
    margin = (BLEED + SAFE_MARGIN) * inch

    c = canvas.Canvas(output_path, pagesize=(page_w, page_h))

    # ---- Page 1 : Page de Titre ----
    c.setFillColor(white)
    c.rect(0, 0, page_w, page_h, fill=True, stroke=False)

    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(page_w / 2.0, page_h - (2.5 * inch), book_title)

    c.setFont("Helvetica", 16)
    c.drawCentredString(page_w / 2.0, page_h - (3.5 * inch),
                        f"{len(image_paths)} dessins uniques")
    c.drawCentredString(page_w / 2.0, page_h - (4.0 * inch),
                        "Pour enfants de 2 a 7 ans")

    c.setFont("Helvetica", 14)
    c.drawCentredString(page_w / 2.0, page_h - (6.0 * inch),
                        "Ce livre appartient a :")

    # Ligne pour ecrire le nom
    line_y = page_h - (7.0 * inch)
    line_half = 2.5 * inch
    c.setStrokeColor(black)
    c.setLineWidth(1.5)
    c.line(page_w / 2.0 - line_half, line_y, page_w / 2.0 + line_half, line_y)

    c.setFont("Helvetica", 10)
    c.drawCentredString(page_w / 2.0, 1.0 * inch,
                        "Dessins simples avec de gros traits - ideal pour les tout-petits")

    c.showPage()

    # ---- Page 2 : Verso de la page de titre (vide) ----
    _add_blank_page(c, page_w, page_h)

    # ---- Pages de coloriage (recto = dessin, verso = blanc) ----
    for idx, img_path in enumerate(image_paths):
        print(f"  Ajout page coloriage {idx + 1}/{len(image_paths)}...")

        try:
            # Calculer la zone de dessin (à l'intérieur des marges de sécurité)
            draw_x = margin
            draw_y = margin
            draw_w = page_w - (2 * margin)
            draw_h = page_h - (2 * margin)

            # Recto : Image de coloriage
            c.setFillColor(white)
            c.rect(0, 0, page_w, page_h, fill=True, stroke=False)
            c.drawImage(
                img_path, draw_x, draw_y,
                width=draw_w, height=draw_h,
                preserveAspectRatio=True, anchor='c'
            )
            c.showPage()

            # Verso : Page blanche (protection contre les feutres qui transpercent)
            _add_blank_page(c, page_w, page_h)

        except Exception as e:
            print(f"  ERREUR avec l'image {img_path} : {e}")
            # Ajouter des pages vides pour ne pas casser l'ordre recto/verso
            _add_blank_page(c, page_w, page_h)
            _add_blank_page(c, page_w, page_h)

    c.save()

    # Compter le nombre total de pages
    total_pages = 2 + (len(image_paths) * 2)  # titre + verso titre + (coloriage + verso) * N
    print(f"  OK : PDF interieur sauvegarde : {output_path} ({total_pages} pages)")
    return total_pages


def create_preview_pdf(image_paths: list[str], output_path: str, 
                       cover_path: str | None = None, 
                       back_cover_path: str | None = None,
                       book_title: str | None = None):
    """
    Compile les images en un PDF de prévisualisation enrichi.
    Structure : [1ere Couverture] -> [Page Titre] -> [Dessins...] -> [4eme Couverture].
    """
    print(f"\n[Phase C] Compilation du PDF de prévisualisation enrichi...")

    page_w = PAGE_WIDTH * inch
    page_h = PAGE_HEIGHT * inch
    margin = (BLEED + SAFE_MARGIN) * inch

    c = canvas.Canvas(output_path, pagesize=(page_w, page_h))

    # 1. 1ère de Couverture
    if cover_path and os.path.exists(cover_path):
        try:
            c.drawImage(cover_path, 0, 0, width=page_w, height=page_h, preserveAspectRatio=True, anchor='c')
            c.showPage()
        except Exception as e:
            print(f"  Erreur ajout couverture preview : {e}")

    # 2. Page de Titre (si titre fourni)
    if book_title:
        c.setFillColor(white)
        c.rect(0, 0, page_w, page_h, fill=True, stroke=False)
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 32)
        c.drawCentredString(page_w / 2.0, page_h - (3 * inch), book_title)
        
        c.setFont("Helvetica", 16)
        c.drawCentredString(page_w / 2.0, page_h - (4 * inch), f"{len(image_paths)} Coloriages pour tout-petits")
        
        c.setFont("Helvetica", 12)
        c.drawCentredString(page_w / 2.0, 1.5 * inch, "Aperçu numerique - Ne pas utiliser pour impression KDP")
        c.showPage()

    # 3. Pages de coloriage
    for idx, img_path in enumerate(image_paths):
        try:
            draw_x = margin
            draw_y = margin
            draw_w = page_w - (2 * margin)
            draw_h = page_h - (2 * margin)

            c.setFillColor(white)
            c.rect(0, 0, page_w, page_h, fill=True, stroke=False)
            c.drawImage(
                img_path, draw_x, draw_y,
                width=draw_w, height=draw_h,
                preserveAspectRatio=True, anchor='c'
            )
            c.showPage()
        except Exception as e:
            print(f"  ERREUR Preview image {img_path} : {e}")

    # 4. 4ème de Couverture
    if back_cover_path and os.path.exists(back_cover_path):
        try:
            c.drawImage(back_cover_path, 0, 0, width=page_w, height=page_h, preserveAspectRatio=True, anchor='c')
            c.showPage()
        except Exception as e:
            print(f"  Erreur ajout 4eme couverture preview : {e}")

    c.save()
    print(f"  OK : PDF de prévisualisation enrichi sauvegarde : {output_path}")
    return len(image_paths)


def create_cover_pdf(cover_image_path: str | None, output_path: str,
                     total_interior_pages: int, book_title: str = "Coloring Book",
                     back_cover_image_path: str | None = None):
    """
    Cree le PDF de couverture KDP (4eme + tranche + 1ere).
    Les images IA contiennent deja le design complet (texte inclus).
    """
    print(f"\n[Phase C] Creation de la couverture KDP...")

    spine_width = total_interior_pages * SPINE_WIDTH_PER_PAGE

    single_cover_width = PAGE_WIDTH
    cover_total_width = (single_cover_width * 2) + spine_width
    cover_total_height = COVER_HEIGHT

    cw = cover_total_width * inch
    ch = cover_total_height * inch
    sw = spine_width * inch
    single_w = single_cover_width * inch

    c = canvas.Canvas(output_path, pagesize=(cw, ch))

    c.setFillColor(white)
    c.rect(0, 0, cw, ch, fill=True, stroke=False)

    # ---- 1ere de couverture (cote droit) ----
    front_x = single_w + sw
    if cover_image_path and os.path.exists(cover_image_path):
        try:
            c.drawImage(
                cover_image_path, front_x, 0,
                width=single_w, height=ch,
                preserveAspectRatio=True, anchor='c'
            )
        except Exception as e:
            print(f"  Impossible de placer l'image de couverture avant : {e}")

    # ---- Tranche (spine) ----
    if spine_width > 0.5:
        c.saveState()
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 8)
        spine_center_x = single_w + (sw / 2.0)
        c.translate(spine_center_x, ch / 2.0)
        c.rotate(90)
        c.drawCentredString(0, 0, book_title)
        c.restoreState()

    # ---- 4eme de couverture (cote gauche) ----
    if back_cover_image_path and os.path.exists(back_cover_image_path):
        try:
            c.drawImage(
                back_cover_image_path, 0, 0,
                width=single_w, height=ch,
                preserveAspectRatio=True, anchor='c'
            )
        except Exception as e:
            print(f"  Impossible de placer l'image de 4eme de couverture : {e}")
    else:
        c.setFillColor(black)
        c.setFont("Helvetica", 10)
        c.drawCentredString(
            single_w / 2.0, 1.0 * inch,
            "Dessins simples pour tout-petits"
        )

    c.save()
    print(f"  OK : Couverture sauvegardee : {output_path}")
    print(f"     Dimensions : {cover_total_width:.3f}\" x {cover_total_height:.3f}\"")
    print(f"     Epaisseur de tranche : {spine_width:.3f}\"")


def _add_blank_page(c, page_w, page_h):
    """Ajoute une page entierement blanche au PDF."""
    c.setFillColor(white)
    c.rect(0, 0, page_w, page_h, fill=True, stroke=False)
    c.showPage()

