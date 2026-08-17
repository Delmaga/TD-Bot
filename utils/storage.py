"""
Petit système de stockage JSON, simple et sans dépendance externe.
Chaque "nom" correspond à un fichier data/<nom>.json.
"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def _path(name: str) -> Path:
    return DATA_DIR / f"{name}.json"


def load(name: str, default=None):
    path = _path(name)
    if not path.exists():
        return default if default is not None else {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return default if default is not None else {}


def save(name: str, data) -> None:
    path = _path(name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
