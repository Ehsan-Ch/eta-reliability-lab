import json
from pathlib import Path
from eta import experiment

ROOT = Path(__file__).resolve().parent


def render():
    source = (ROOT / "explorer.html").read_text(encoding="utf-8")
    return source.replace("<!-- REPORT -->", json.dumps(experiment(), separators=(",", ":")))


if __name__ == "__main__":
    (ROOT / "index.html").write_text(render(), encoding="utf-8", newline="\n")
