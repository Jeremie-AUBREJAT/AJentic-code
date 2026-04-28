import os
from datetime import datetime


def generate_html_doc(analysis, output_dir="output/docs"):

    os.makedirs(output_dir, exist_ok=True)

    html = []

    html.append("<html><head><meta charset='utf-8'>")
    html.append("<title>Plugin Documentation</title>")

    html.append("""
    <style>
    body { font-family: Arial; background:#111; color:#eee; padding:20px; }
    h1 { color:#4fc3f7; }
    h2 { color:#81d4fa; margin-top:30px; }
    h3 { color:#90caf9; }
    .box { background:#1e1e1e; padding:15px; margin:10px 0; border-radius:8px; }
    .file { border-left:3px solid #4fc3f7; padding-left:10px; margin-bottom:20px; }
    pre { background:#000; padding:10px; overflow:auto; }
    </style>
    """)

    html.append("</head><body>")

    html.append("<h1>WordPress Plugin Documentation</h1>")
    html.append(f"<p>Generated: {datetime.now()}</p>")

    # ---------------- GLOBAL ----------------

    llm = analysis.get("llm", {})

    html.append("<h2>Architecture Overview</h2>")
    html.append("<div class='box'>")

    html.append(f"<p><b>Functions:</b> {len(llm.get('fn', []))}</p>")
    html.append(f"<p><b>Hooks:</b> {len(llm.get('hk', []))}</p>")
    html.append(f"<p><b>AJAX endpoints:</b> {len(llm.get('ax', []))}</p>")

    html.append("</div>")

    html.append("<h2>Execution Model</h2>")
    html.append("""
    <div class='box'>
    <pre>
1. Plugin init (WordPress hooks)
2. DOM scan (dtx.init)
3. Detect dynamic fields
4. Resolve values (local or AJAX)
5. Server-side CF7 processing
6. Return JSON
7. Update DOM inputs
    </pre>
    </div>
    """)

    html.append("<h2>Files Analysis</h2>")

    # ---------------- FILES ----------------

    for r in analysis.get("results", []):

        file_name = r["file"]
        data = r["analysis"]

        llm_data = data.get("llm", {})
        doc = data.get("doc", {})

        html.append("<div class='box file'>")

        html.append(f"<h3>{file_name}</h3>")

        html.append(f"<p><b>Summary:</b> {doc.get('summary','')}</p>")

        # FEATURES
        features = doc.get("features", [])
        if features:
            html.append("<h4>Features</h4><ul>")
            for f in features:
                html.append(f"<li>{f}</li>")
            html.append("</ul>")

        # FUNCTIONS (clean)
        fn = llm_data.get("fn", [])
        if fn:
            html.append("<h4>Functions</h4><pre>")
            html.append("\n".join(fn))
            html.append("</pre>")

        # HOOKS
        hk = llm_data.get("hk", [])
        if hk:
            html.append("<h4>Hooks</h4><pre>")
            html.append("\n".join(hk))
            html.append("</pre>")

        # AJAX
        ax = llm_data.get("ax", [])
        if ax:
            html.append("<h4>AJAX</h4><pre>")
            html.append("\n".join(ax))
            html.append("</pre>")

        # NOTES
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