import os
from datetime import datetime


def generate_html_doc(analysis, output_dir="output/docs"):

    os.makedirs(output_dir, exist_ok=True)

    results = analysis.get("results", [])

    html = []

    html.append("<html><head><meta charset='utf-8'>")
    html.append("<title>Plugin Documentation</title>")

    html.append("""
    <style>
    body { font-family: Arial; background:#111; color:#eee; padding:20px; }
    h1 { color:#4fc3f7; }
    h2 { color:#81d4fa; margin-top:30px; }
    h3 { color:#90caf9; }
    .box { background:#1e1e1e; padding:12px; margin:10px 0; border-radius:6px; }
    .tag { color:#ffd54f; font-weight:bold; }
    ul { margin:0; padding-left:20px; }
    </style>
    """)

    html.append("</head><body>")

    html.append("<h1>Plugin Documentation</h1>")
    html.append(f"<p>Generated: {datetime.now()}</p>")

    # -----------------------
    # GLOBAL VIEW
    # -----------------------

    html.append("<h2>GLOBAL VIEW</h2>")

    llm = analysis.get("llm", {})

    html.append("<div class='box'>")

    html.append("<h3>Functions</h3>")
    html.append(f"<p>{', '.join(llm.get('fn', []))}</p>")

    html.append("<h3>Hooks</h3>")
    html.append(f"<p>{', '.join(llm.get('hk', []))}</p>")

    html.append("<h3>AJAX</h3>")
    html.append(f"<p>{', '.join(str(x) for x in llm.get('ax', []))}</p>")

    html.append("</div>")

    # -----------------------
    # FILES
    # -----------------------

    html.append("<h2>FILES</h2>")

    for r in results:

        file_name = r["file"]
        data = r.get("analysis", {})

        llm_data = data.get("llm", {})
        doc = data.get("doc", {})

        html.append("<div class='box'>")

        html.append(f"<h3>{file_name}</h3>")

        # LANG
        html.append(f"<p><span class='tag'>LANG:</span> {llm_data.get('lang','')}</p>")

        # FUNCTIONS
        fn = llm_data.get("fn", [])
        if fn:
            html.append("<h4>Functions</h4><ul>")
            for f in fn:
                html.append(f"<li>{f}</li>")
            html.append("</ul>")

        # HOOKS
        hk = llm_data.get("hk", [])
        if hk:
            html.append("<h4>Hooks</h4><ul>")
            for h in hk:
                html.append(f"<li>{h}</li>")
            html.append("</ul>")

        # AJAX
        ax = llm_data.get("ax", [])
        if ax:
            html.append("<h4>AJAX</h4><ul>")
            for a in ax:
                html.append(f"<li>{a}</li>")
            html.append("</ul>")

        # LOGIC (ultra important)
        lg = llm_data.get("lg", [])
        if lg:
            html.append("<h4>Logic</h4><ul>")
            for l in lg:
                html.append(f"<li>{l}</li>")
            html.append("</ul>")

        # DOC HUMAN
        html.append("<h4>Summary</h4>")
        html.append(f"<p>{doc.get('summary','')}</p>")

        features = doc.get("features", [])
        if features:
            html.append("<h4>Features</h4><ul>")
            for f in features:
                html.append(f"<li>{f}</li>")
            html.append("</ul>")

        notes = doc.get("notes", [])
        if notes:
            html.append("<h4>Notes</h4><ul>")
            for n in notes:
                html.append(f"<li>{n}</li>")
            html.append("</ul>")

        html.append("</div>")

    html.append("</body></html>")

    output_file = os.path.join(output_dir, "index.html")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(html))

    return output_file