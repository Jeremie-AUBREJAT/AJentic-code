from pathlib import Path


EXTENSIONS = [
    ".php",
    ".js",
    ".ts",
    ".json",
    ".blade.php"
]

IGNORED = [
    "vendor",
    "node_modules",
    ".git"
]


def scan_codebase(root):

    files = []

    for path in Path(root).rglob("*"):

        if any(ignored in str(path) for ignored in IGNORED):
            continue

        if path.suffix in EXTENSIONS:
            files.append(path)

    return files