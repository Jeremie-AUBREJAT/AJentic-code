import os
import re
import shutil
import requests
from bs4 import BeautifulSoup, Comment
from urllib.parse import urljoin, urlparse
from pathlib import Path


# ---------------------------------------------------------
# NETTOYAGE INTELLIGENT (HTML / JS / JSON)
# ---------------------------------------------------------
def clean_content(content, filetype):
    """
    Nettoyage intelligent :
    - réduit la taille
    - supprime le bruit inutile
    - conserve tout ce qui peut contenir une faille
    """

    MAX_LEN = 20000  # limite dure pour éviter prompts énormes
    content = content[:MAX_LEN]

    # -------------------------
    # HTML
    # -------------------------
    if filetype == "html":
        soup = BeautifulSoup(content, "html.parser")

        # Supprimer commentaires
        for c in soup.find_all(string=lambda t: isinstance(t, Comment)):
            c.extract()

        # Supprimer <style> et CSS inline
        for s in soup.find_all("style"):
            s.decompose()

        # Supprimer scripts inline (mais garder les src)
        for s in soup.find_all("script"):
            if not s.get("src"):
                s.decompose()

        # Supprimer attributs inutiles
        for tag in soup.find_all(True):
            for attr in list(tag.attrs):
                if attr not in ["href", "src", "action", "method", "name", "value", "id"]:
                    del tag.attrs[attr]

        return str(soup)

    # -------------------------
    # JS
    # -------------------------
    if filetype == "js":
        # Enlever commentaires
        content = re.sub(r"//.*?$", "", content, flags=re.MULTILINE)
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)

        # Enlever lignes vides
        content = "\n".join([l for l in content.split("\n") if l.strip()])

        # Garder uniquement les patterns dangereux
        patterns = [
            "fetch(", "axios", "$.ajax", "XMLHttpRequest",
            "innerHTML", "outerHTML", "document.cookie",
            "localStorage", "sessionStorage",
            "eval(", "Function(", "setTimeout(", "setInterval("
        ]

        extracted = []
        for line in content.split("\n"):
            if any(p in line for p in patterns):
                extracted.append(line)

        # Si rien trouvé → garder le JS nettoyé
        if extracted:
            return "\n".join(extracted)[:MAX_LEN]

        return content[:MAX_LEN]

    # -------------------------
    # JSON / API
    # -------------------------
    if filetype == "json":
        return content[:MAX_LEN]

    return content


# ---------------------------------------------------------
# AGENT WEB AUDIT
# ---------------------------------------------------------
class Agent:
    name = "web_audit"

    def __init__(self):
        self.visited = set()
        self.max_pages = 30

    # ---------------------------------------------------------
    # CRAWL → TÉLÉCHARGE ET NETTOIE LES FICHIERS
    # ---------------------------------------------------------
    def crawl(self, url, workspace="workspace/web_audit"):
        """
        Crawl légal : télécharge HTML, JS, JSON, AJAX
        et les enregistre comme fichiers individuels.
        Nettoyage intelligent pour réduire la taille
        sans perdre les failles potentielles.
        """

        domain = urlparse(url).netloc.replace(":", "_")
        base_dir = Path(workspace) / domain

        # Reset dossier
        if base_dir.exists():
            shutil.rmtree(base_dir)
        base_dir.mkdir(parents=True, exist_ok=True)

        to_visit = [url]
        saved_files = []

        while to_visit and len(saved_files) < self.max_pages:
            current = to_visit.pop(0)
            if current in self.visited:
                continue

            self.visited.add(current)

            try:
                r = requests.get(current, timeout=5)
            except:
                continue

            content_type = r.headers.get("Content-Type", "")

            # ---------------------------------------------------------
            # HTML
            # ---------------------------------------------------------
            if "text/html" in content_type:
                soup = BeautifulSoup(r.text, "html.parser")

                cleaned = clean_content(r.text, "html")

                filename = f"page_{len(saved_files)}.html"
                filepath = base_dir / filename
                filepath.write_text(cleaned, encoding="utf-8")
                saved_files.append(filepath)

                # Links internes
                for a in soup.find_all("a", href=True):
                    link = urljoin(current, a["href"])
                    if urlparse(link).netloc == urlparse(url).netloc:
                        to_visit.append(link)

                # JS externes
                for script in soup.find_all("script", src=True):
                    js_url = urljoin(current, script["src"])
                    try:
                        js_r = requests.get(js_url, timeout=5)
                        if js_r.status_code == 200:
                            cleaned_js = clean_content(js_r.text, "js")
                            js_name = f"script_{len(saved_files)}.js"
                            js_path = base_dir / js_name
                            js_path.write_text(cleaned_js, encoding="utf-8")
                            saved_files.append(js_path)
                    except:
                        pass

            # ---------------------------------------------------------
            # JSON / API
            # ---------------------------------------------------------
            elif "application/json" in content_type:
                cleaned = clean_content(r.text, "json")
                filename = f"endpoint_{len(saved_files)}.json"
                filepath = base_dir / filename
                filepath.write_text(cleaned, encoding="utf-8")
                saved_files.append(filepath)

        return base_dir, saved_files

    # ---------------------------------------------------------
    # PROMPT PAR FICHIER (ULTRA AUDIT)
    # ---------------------------------------------------------
    def build_prompt(self, code):
        return f"""
Tu es un expert en cybersécurité spécialisé en audit web.
Analyse ce fichier **en profondeur** et détecte TOUT :

### 🔥 Vulnérabilités potentielles
- XSS (toutes formes)
- injections JS
- endpoints exposés
- fuites de données
- mauvaises pratiques HTML/JS
- DOM-based XSS
- accès non protégé à des API
- manipulation dangereuse du DOM
- stockage non sécurisé (localStorage, cookies)
- patterns dangereux (eval, innerHTML, etc.)

### 🔧 Ce que tu dois fournir
- liste des risques trouvés
- explication claire
- niveau de criticité
- comment exploiter la faille
- comment corriger

### 📄 Contenu du fichier analysé :
{code}
"""
