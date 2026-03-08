"""
Gemini KDP Creator - Serveur Web Local (Natif)
Lancer avec : python server.py
Ouvrir : http://localhost:5000
"""
import os
import json
import threading
import subprocess
import sys
import shutil
import mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, unquote

# Ajouter le dossier parent au path pour importer config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import GEMINI_API_KEY

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

# Stockage en memoire de l'etat de la generation
generation_status = {
    "running": False,
    "theme": "",
    "progress": "",
    "log": [],
}

class KDPServerHandler(BaseHTTPRequestHandler):
    def _send_response(self, data, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        if isinstance(data, (dict, list)):
            self.wfile.write(json.dumps(data).encode('utf-8'))
        elif isinstance(data, str):
            self.wfile.write(data.encode('utf-8'))
        else:
            self.wfile.write(data)

    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = unquote(parsed_path.path)

        # Route l'interface HTML
        if path == "/" or path == "/index.html":
            filepath = os.path.join(os.path.dirname(__file__), "index.html")
            if os.path.exists(filepath):
                with open(filepath, "rb") as f:
                    self._send_response(f.read(), content_type="text/html")
            else:
                self._send_response("Fichier index.html introuvable.", status=404, content_type="text/plain")
        
        # API : Lister la bibliotheque
        elif path == "/api/books":
            self.handle_list_books()
            
        # API : Statut de la generation
        elif path == "/api/status":
            self._send_response(generation_status)
            
        # Fichiers statiques (Livres dans le dossier output)
        elif path.startswith("/output/"):
            rel_path = path[len("/output/"):]
            full_path = os.path.join(OUTPUT_DIR, rel_path)
            
            # Securite : eviter les path traversal (../../)
            if not os.path.abspath(full_path).startswith(os.path.abspath(OUTPUT_DIR)):
                self._send_response({"error": "Acces interdit"}, status=403)
                return
                
            if os.path.exists(full_path) and os.path.isfile(full_path):
                mime_type, _ = mimetypes.guess_type(full_path)
                try:
                    with open(full_path, "rb") as f:
                        self._send_response(f.read(), content_type=mime_type or "application/octet-stream")
                except Exception as e:
                    self._send_response({"error": str(e)}, status=500)
            else:
                self._send_response({"error": "Fichier introuvable"}, status=404)
        else:
            self._send_response({"error": "Not Found"}, status=404)

    def do_POST(self):
        parsed_path = urlparse(self.path)
        path = unquote(parsed_path.path)

        if path in ["/api/generate", "/api/regenerate", "/api/recompile", "/api/regenerate_cover"]:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                if path == "/api/generate":
                    self.handle_generate(data)
                elif path == "/api/regenerate":
                    self.handle_regenerate_page(data)
                elif path == "/api/recompile":
                    self.handle_recompile_book(data)
                elif path == "/api/regenerate_cover":
                    self.handle_regenerate_cover(data)
            except Exception as e:
                self._send_response({"error": "Donnees invalides"}, status=400)
        else:
            self._send_response({"error": "Not Found"}, status=404)

    def do_DELETE(self):
        parsed_path = urlparse(self.path)
        path = unquote(parsed_path.path)

        if path.startswith("/api/books/"):
            book_id = path[len("/api/books/"):]
            self.handle_delete_book(book_id)
        else:
            self._send_response({"error": "Not Found"}, status=404)

    def handle_list_books(self):
        books = []
        if not os.path.exists(OUTPUT_DIR):
            self._send_response(books)
            return

        for folder_name in sorted(os.listdir(OUTPUT_DIR), reverse=True):
            folder_path = os.path.join(OUTPUT_DIR, folder_name)
            if not os.path.isdir(folder_path):
                continue

            book = {
                "id": folder_name,
                "title": folder_name.replace("_", " ").title(),
                "has_cover": os.path.exists(os.path.join(folder_path, "cover_image.png")),
                "pages": [],
                "pdf_interior": None,
                "pdf_cover": None,
                "pdf_preview": None,
            }

            pages_dir = os.path.join(folder_path, "pages")
            prompts_path = os.path.join(folder_path, "prompts.json")
            
            # Recuperer la liste complete attendue depuis prompts.json
            expected_count = 0
            if os.path.exists(prompts_path):
                try:
                    with open(prompts_path, "r", encoding="utf-8") as f:
                        p_data = json.load(f)
                        if isinstance(p_data, dict):
                            expected_count = len(p_data.get("interior", []))
                        else:
                            expected_count = len(p_data)
                except:
                    pass
            
            if expected_count > 0:
                # On cree la liste des pages attendues
                for i in range(1, expected_count + 1):
                    p_name = f"page_{i:03d}.png"
                    exists = os.path.exists(os.path.join(pages_dir, p_name))
                    book["pages"].append({"name": p_name, "exists": exists})
            elif os.path.exists(pages_dir):
                # Fallback : seulement les fichiers presents
                file_list = sorted([f for f in os.listdir(pages_dir) if f.endswith(".png")])
                book["pages"] = [{"name": f, "exists": True} for f in file_list]

            for f in os.listdir(folder_path):
                if f.startswith("KDP_Interieur") and f.endswith(".pdf"):
                    book["pdf_interior"] = f
                elif f.startswith("KDP_Couverture") and f.endswith(".pdf"):
                    book["pdf_cover"] = f
                elif f.startswith("Preview_Complet") and f.endswith(".pdf"):
                    book["pdf_preview"] = f

            books.append(book)
        self._send_response(books)

    def handle_generate(self, data):
        global generation_status
        if generation_status["running"]:
            self._send_response({"error": "Une generation est deja en cours."}, status=409)
            return

        theme = data.get("theme", "").strip()
        pages = data.get("pages", 20)
        title = data.get("title", "").strip()

        if not theme:
            self._send_response({"error": "Le theme est requis."}, status=400)
            return
        if not GEMINI_API_KEY:
            self._send_response({"error": "Cle API Gemini non configuree dans config.py."}, status=400)
            return

        generation_status = {
            "running": True,
            "theme": theme,
            "progress": "Demarrage du background process...",
            "log": [],
        }

        # Background runner pour ne pas bloquer le serveur HTTP
        def run_generation():
            global generation_status
            try:
                cmd = [sys.executable, "-u", "run.py", "--theme", theme, "--pages", str(pages), "--api-key", GEMINI_API_KEY]
                if title:
                    cmd.extend(["--title", title])

                process = subprocess.Popen(
                    cmd,
                    cwd=os.path.dirname(os.path.abspath(__file__)),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )

                for line in iter(process.stdout.readline, ""):
                    line = line.strip()
                    if line:
                        generation_status["log"].append(line)
                        generation_status["progress"] = line
                        # Garder les 50 dernieres lignes max pour eviter la surconsommation memoire
                        if len(generation_status["log"]) > 50:
                            generation_status["log"] = generation_status["log"][-50:]

                process.wait()
                if process.returncode == 0:
                    generation_status["progress"] = "Termine avec succes !"
                else:
                    generation_status["progress"] = f"Erreur fatale (code de sortie {process.returncode})"

            except Exception as e:
                generation_status["progress"] = f"Crash du compilateur : {str(e)}"
            finally:
                generation_status["running"] = False

        thread = threading.Thread(target=run_generation, daemon=True)
        thread.start()

        self._send_response({"message": "La generation a demarre !"})

    def handle_regenerate_page(self, data):
        """Regenere une page specifique et met a jour le PDF."""
        book_id = data.get("book_id", "").strip()
        page_name = data.get("page_name", "").strip() # ex: "page_004.png"
        
        if not book_id or not page_name:
            self._send_response({"error": "book_id et page_name requis."}, status=400)
            return
            
        folder_path = os.path.join(OUTPUT_DIR, book_id)
        prompts_file = os.path.join(folder_path, "prompts.json")
        
        if not os.path.exists(prompts_file):
            self._send_response({"error": "Fichier prompts.json introuvable. Impossible de regenerer la page pour les anciens livres."}, status=404)
            return

        try:
            # 1. Recuperer l'index et le prompt
            with open(prompts_file, "r", encoding="utf-8") as f:
                prompts = json.load(f)
                
            # page_name est de la forme "page_001.png"
            page_idx = int(page_name.replace("page_", "").replace(".png", "")) - 1
            
            if page_idx < 0 or page_idx >= len(prompts):
                self._send_response({"error": "Index de page invalide."}, status=400)
                return
                
            target_prompt = prompts[page_idx]
            
            # 2. Generer la nouvelle image (Thread dedie)
            def run_regeneration():
                try:
                    from google import genai
                    from modules.illustration import generate_coloring_images
                    from modules.compiler import create_interior_pdf, create_preview_pdf
                    import glob
                    
                    client = genai.Client(api_key=GEMINI_API_KEY)
                    
                    # On lance la generation pour UN SEUL prompt
                    # illustration va creer un fichier "page_001.png" car c'est une liste de 1 element.
                    # TRICKY : generate_coloring_images cree les fichiers a partir de page_001.
                    # Pour palier ca sans trop modifier de code, on genere dans un sous-dossier tmp, et on copie.
                    tmp_folder = os.path.join(folder_path, "tmp_regen")
                    os.makedirs(tmp_folder, exist_ok=True)
                    
                    new_images = generate_coloring_images(client, [target_prompt], tmp_folder)
                    
                    if new_images and len(new_images) > 0:
                        new_img_path = new_images[0]
                        target_img_path = os.path.join(folder_path, "pages", page_name)
                        
                        # Remplacer l'ancienne image
                        shutil.copy2(new_img_path, target_img_path)
                        
                        # Recompiler le PDF
                        pages_dir = os.path.join(folder_path, "pages")
                        all_pages = sorted(glob.glob(os.path.join(pages_dir, "*.png")))
                        
                        # Trouver le bon nom de fichier KDP_Interieur*.pdf
                        pdfs = glob.glob(os.path.join(folder_path, "KDP_Interieur*.pdf"))
                        if pdfs:
                            interior_pdf = pdfs[0]
                            # Extraction du titre existant (ou generique)
                            title = book_id.replace("_", " ").title()
                            create_interior_pdf(all_pages, interior_pdf, book_title=title)
                            
                        # Recompiler la Preview Complete
                        preview_pdfs = glob.glob(os.path.join(folder_path, "Preview_Complet*.pdf"))
                        preview_filename = preview_pdfs[0] if preview_pdfs else os.path.join(folder_path, f"Preview_Complet_{book_id}.pdf")
                        
                        cover_path = os.path.join(folder_path, "cover_image.png")
                        back_cover_path = os.path.join(folder_path, "back_cover_image.png")
                        title = book_id.replace("_", " ").title()
                        
                        create_preview_pdf(all_pages, preview_filename, 
                                           cover_path=cover_path, 
                                           back_cover_path=back_cover_path, 
                                           book_title=title)
                            
                    # Cleanup
                    if os.path.exists(tmp_folder):
                        shutil.rmtree(tmp_folder)
                        
                except Exception as e:
                    print(f"Erreur regeneration de {page_name}: {e}")

            thread = threading.Thread(target=run_regeneration, daemon=True)
            thread.start()
            
            self._send_response({"message": "Regeneration en cours (prend 15-30s)... Rafraichissez bientot !"})
            
        except Exception as e:
            self._send_response({"error": f"Erreur serveur : {str(e)}"}, status=500)
            

    def handle_delete_book(self, book_id):
        folder_path = os.path.join(OUTPUT_DIR, book_id)
        # Securite (path traversal evite car url decode et test root verifie)
        if os.path.basename(book_id) != book_id:
             self._send_response({"error": "Nom de dossier invalide."}, status=400)
             return
             
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            shutil.rmtree(folder_path)
            self._send_response({"message": f"Le livre a ete supprime."})
        else:
            self._send_response({"error": "Le livre est introuvable."}, status=404)


# ========================
#  LANCEMENT
# ========================
    def handle_recompile_book(self, data):
        """Recompile tous les PDF d'un livre (Interieur + Aperçu)."""
        book_id = data.get("book_id", "").strip()
        if not book_id:
            self._send_response({"error": "book_id requis."}, status=400)
            return

        folder_path = os.path.join(OUTPUT_DIR, book_id)
        if not os.path.exists(folder_path):
            self._send_response({"error": "Livre introuvable."}, status=404)
            return

        try:
            from modules.compiler import create_interior_pdf, create_preview_pdf
            import glob

            # 1. Lister les images
            pages_dir = os.path.join(folder_path, "pages")
            all_pages = sorted(glob.glob(os.path.join(pages_dir, "*.png")))
            
            if not all_pages:
                self._send_response({"error": "Aucune image trouvee dans 'pages/'."}, status=400)
                return

            # 2. Recompiler l'Interieur KDP
            pdfs = glob.glob(os.path.join(folder_path, "KDP_Interieur*.pdf"))
            interior_pdf = pdfs[0] if pdfs else os.path.join(folder_path, f"KDP_Interieur_{book_id}.pdf")
            title = book_id.replace("_", " ").title()
            create_interior_pdf(all_pages, interior_pdf, book_title=title)

            # 3. Recompiler l'Aperçu Complet
            preview_pdfs = glob.glob(os.path.join(folder_path, "Preview_Complet*.pdf"))
            preview_filename = preview_pdfs[0] if preview_pdfs else os.path.join(folder_path, f"Preview_Complet_{book_id}.pdf")
            
            cover_path = os.path.join(folder_path, "cover_image.png")
            back_cover_path = os.path.join(folder_path, "back_cover_image.png")
            
            create_preview_pdf(all_pages, preview_filename, 
                               cover_path=cover_path, 
                               back_cover_path=back_cover_path, 
                               book_title=title)

            self._send_response({"message": "PDFs recompiles avec succes !"})

        except Exception as e:
            self._send_response({"error": str(e)}, status=500)
            print(f"Erreur recompilation book {book_id}: {e}")

    def handle_regenerate_cover(self, data):
        """Regenere la couverture avant et arriere d'un livre."""
        book_id = data.get("book_id", "").strip()
        if not book_id:
            self._send_response({"error": "book_id requis."}, status=400)
            return

        folder_path = os.path.join(OUTPUT_DIR, book_id)
        prompts_file = os.path.join(folder_path, "prompts.json")

        if not os.path.exists(prompts_file):
            self._send_response({"error": "Fichier prompts.json introuvable."}, status=404)
            return

        def run_cover_regeneration():
            try:
                from google import genai
                from modules.illustration import generate_cover_image, generate_back_cover_image
                from modules.compiler import create_cover_pdf, create_preview_pdf
                import glob

                with open(prompts_file, "r", encoding="utf-8") as f:
                    all_prompts = json.load(f)
                
                # Compatibilite ancien format
                if isinstance(all_prompts, list):
                    self._send_response({"error": "Ancien format de livre : prompt de couverture absent."}, status=400)
                    return

                cover_prompt = all_prompts.get("cover")
                back_prompt = all_prompts.get("back_cover")
                interior_prompts = all_prompts.get("interior", [])

                if not cover_prompt or not back_prompt:
                    print("Erreur : Prompts de couverture manquants dans prompts.json")
                    return

                client = genai.Client(api_key=GEMINI_API_KEY)

                # Generer les nouvelles images
                new_cover = generate_cover_image(client, cover_prompt, folder_path)
                new_back = generate_back_cover_image(client, back_prompt, folder_path)

                if new_cover and new_back:
                    # Recompiler le PDF Couverture KDP
                    pages_dir = os.path.join(folder_path, "pages")
                    all_pages = sorted(glob.glob(os.path.join(pages_dir, "*.png")))
                    total_interior_pages = len(all_pages)
                    
                    pdfs = glob.glob(os.path.join(folder_path, "KDP_Couverture*.pdf"))
                    cover_pdf = pdfs[0] if pdfs else os.path.join(folder_path, f"KDP_Couverture_{book_id}.pdf")
                    title = book_id.replace("_", " ").title()
                    
                    create_cover_pdf(new_cover, cover_pdf, total_interior_pages, book_title=title, back_cover_image_path=new_back)

                    # Recompiler l'Aperçu Complet
                    preview_pdfs = glob.glob(os.path.join(folder_path, "Preview_Complet*.pdf"))
                    preview_filename = preview_pdfs[0] if preview_pdfs else os.path.join(folder_path, f"Preview_Complet_{book_id}.pdf")
                    create_preview_pdf(all_pages, preview_filename, cover_path=new_cover, back_cover_path=new_back, book_title=title)
                
                print(f"Regeneration couverture terminee pour {book_id}")

            except Exception as e:
                print(f"Erreur regeneration couverture {book_id}: {e}")

        thread = threading.Thread(target=run_cover_regeneration, daemon=True)
        thread.start()
        self._send_response({"message": "Regeneration de la couverture en cours (2K)... Rafraichissez dans 30s !"})

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    PORT = 5000
    server = HTTPServer(('127.0.0.1', PORT), KDPServerHandler)
    
    print("=" * 60)
    print("Gemini KDP Creator - Serveur Web Local (Pur Natif Python)")
    print(f"Connectez-vous sur : http://localhost:{PORT}")
    print("=" * 60)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt manuel du serveur ! Bye.")
        server.server_close()
