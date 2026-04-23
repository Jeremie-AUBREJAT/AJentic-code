import re
from pathlib import Path


def parse_php_file(path):

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        code = f.read()

    classes = re.findall(r'class\s+([A-Za-z0-9_]+)', code)
    functions = re.findall(r'function\s+([A-Za-z0-9_]+)', code)
    hooks = re.findall(r'add_action\(\s*[\'"](.+?)[\'"]', code)
    filters = re.findall(r'add_filter\(\s*[\'"](.+?)[\'"]', code)

    return {
        "file": str(path),
        "classes": classes,
        "functions": functions,
        "actions": hooks,
        "filters": filters
    }