import os
from pathlib import Path
import re
from html import escape


# ---------------------------------------------------------
# EXTRACTION AUTOMATIQUE DES FAILLES
# ---------------------------------------------------------
def extract_findings(text):
    """
    Extrait automatiquement les failles depuis le texte du LLM.
    On cherche des mots-clés typiques d'audit web.
    """

    findings = []

    patterns = [
        r"xss",
        r"dom[- ]?xss",
        r"innerHTML",
        r"outerHTML",
        r"eval\(",
        r"Function\(",
        r"localStorage",
        r"sessionStorage",
        r"document\.cookie",
        r"csrf",
        r"open redirect",
        r"injection",
        r"endpoint",
        r"expos[ée]",
        r"non sécurisé",
        r"vulnérabilit",
        r"risque",
        r"faille",
        r"danger",
    ]

    for p in patterns:
        matches = re.findall(p, text, flags=re.IGNORECASE)
        if matches:
            findings.append(p)

    return list(set(findings))


# ---------------------------------------------------------
# GÉNÉRATION HTML
# ---------------------------------------------------------
def generate_html_doc_web(results, output_dir):
    """
    results = [
        { "file": "page_0.html", "analysis": "texte du LLM" },
        ...
    ]
    """

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    html_path = output_dir / "audit_report.html"

    # ---------------------------------------------------------
    # EXTRACTION GLOBALE
    # ---------------------------------------------------------
    global_findings = []
    per_file_findings = {}

    for r in results:
        file = r["file"]
        analysis = r["analysis"]

        findings = extract_findings(analysis)
        per_file_findings[file] = findings
        global_findings.extend(findings)

    global_findings = list(set(global_findings))

    # ---------------------------------------------------------
    # HTML
    # ---------------------------------------------------------
    html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Audit Web – Rapport</title>

<style>
body{
    font-family: Arial, sans-serif;
    background:#111;
    color:#eee;
    margin:0;
    padding:0;
}
h1,h2,h3{
    color:#4fc3f7;
}
.container{
    width:90%;
    max-width:1100px;
    margin:auto;
    padding:20px;
}
.section{
    background:#1c1c1c;
    padding:20px;
    margin-top:20px;
    border-radius:10px;
    border:1px solid #333;
}
.finding{
    background:#2a2a2a;
    padding:10px;
    margin:5px 0;
    border-left:4px solid #ff5252;
}
.file-block{
    background:#1e1e1e;
    padding:15px;
    margin-top:15px;
    border-radius:8px;
    border:1px solid #333;
}
pre{
    white-space:pre-wrap;
    background:#000;
    padding:10px;
    border-radius:8px;
    border:1px solid #333;
    color:#9ccc65;
}
a{
    color:#4fc3f7;
}
</style>
</head>

<body>
<div class="container">

<h1>Audit Web – Rapport Complet</h1>
<p>Analyse automatique des fichiers récupérés lors du crawl.</p>

<div class="section">
<h2>Résumé global</h2>
<p><b>Nombre total de fichiers analysés :</b> """ + str(len(results)) + """</p>
<p><b>Nombre total de failles détectées :</b> """ + str(len(global_findings)) + """</p>
"""

    if global_findings:
        html += "<h3>Types de failles détectées :</h3>"
        for f in global_findings:
            html += f"<div class='finding'>{escape(f)}</div>"
    else:
        html += "<p>Aucune faille détectée.</p>"

    html += "</div>"

    # ---------------------------------------------------------
    # SECTIONS PAR FICHIER
    # ---------------------------------------------------------
    html += """
<div class="section">
<h2>Détails par fichier</h2>
"""

    for r in results:
        file = r["file"]
        analysis = escape(r["analysis"])
        findings = per_file_findings[file]

        html += f"""
<div class="file-block">
<h3>{escape(file)}</h3>
<p><b>Failles détectées :</b> {len(findings)}</p>
"""

        if findings:
            for f in findings:
                html += f"<div class='finding'>{escape(f)}</div>"
        else:
            html += "<p>Aucune faille détectée dans ce fichier.</p>"

        html += f"""
<h4>Analyse complète :</h4>
<pre>{analysis}</pre>
</div>
"""

    html += """
</div>
</div>
</body>
</html>
"""

    html_path.write_text(html, encoding="utf-8")
    return str(html_path)
