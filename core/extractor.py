import zipfile
import shutil
from pathlib import Path
import rarfile


def extract_input(input_path, workspace):

    input_path = Path(input_path)
    workspace = Path(workspace)

    project_dir = workspace / "project"

    if project_dir.exists():
        shutil.rmtree(project_dir)

    project_dir.mkdir(parents=True)

    if input_path.suffix == ".zip":

        with zipfile.ZipFile(input_path, 'r') as zip_ref:
            zip_ref.extractall(project_dir)

    elif input_path.suffix == ".rar":

        with rarfile.RarFile(input_path) as rar_ref:
            rar_ref.extractall(project_dir)

    elif input_path.is_dir():

        shutil.copytree(input_path, project_dir, dirs_exist_ok=True)

    else:
        raise Exception("Unsupported input type")

    return project_dir