from pathlib import Path
import yaml


def load_config(path="config/config.example.yaml"):
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    root = path.parents[1] if path.parent.name == "config" else Path.cwd()
    cfg["root"] = str(root)
    return cfg


def resolve(root, p):
    p = Path(p)
    return p if p.is_absolute() else Path(root) / p
