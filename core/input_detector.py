from pathlib import Path


def detect_input(path):
    path = Path(path)

    if not path.exists():
        raise Exception(f"Input not found: {path}")

    if path.is_dir():
        return "folder"

    suffix = path.suffix.lower()

    if suffix == ".zip":
        return "zip"

    if suffix == ".rar":
        return "rar"

    return "unknown"