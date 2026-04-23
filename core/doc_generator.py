import os
from datetime import datetime


def generate_html_doc(analysis, output_dir="output/docs"):
    os.makedirs(output_dir, exist_ok=True)

    html = []
    html.append("<html><head><meta charset='utf-8'><title>Plugin Documentation</title>")
    html.append("""
    <style>
        body { font-family: Arial; background:#111; color:#eee; padding:20px; }
        h1,h2 { color:#4fc3f7; }
        .file { background:#1e1e1e; padding:10px; margin:10px 0; border-radius:8px; }
        pre { background:#000; padding:10px; overflow:auto; }
        .box { margin-bottom:20px; }
    </style>
    """)
    html.append("</head><body>")

    html.append(f"<h1>Plugin Documentation</h1>")
    html.append(f"<p>Generated: {datetime.now()}</p>")

    for file_result in analysis["results"]:

        file_name = file_result["file"]
        file_data = file_result["analysis"]

        html.append(f"<div class='file'>")
        html.append(f"<h2>{file_name}</h2>")

        for chunk in file_data:

            if "raw_response" in chunk:
                html.append("<pre>")
                html.append(chunk["raw_response"])
                html.append("</pre>")
            else:
                html.append("<pre>")
                html.append(str(chunk))
                html.append("</pre>")

        html.append("</div>")

    html.append("</body></html>")

    output_file = os.path.join(output_dir, "index.html")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(html))

    return output_file