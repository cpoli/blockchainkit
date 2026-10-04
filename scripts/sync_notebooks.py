"""Copy Sphinx-Gallery notebooks into the distributable course directory.

Run a Sphinx HTML build first. Copies are deterministic and keep notebooks
derived from the gallery scripts rather than becoming a second source of truth.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Synchronize the generated notebooks, including stable cell IDs."""
    gallery = ROOT / "docs/source/gallery"
    destination = ROOT / "notebooks"
    destination.mkdir(exist_ok=True)
    sources = sorted((ROOT / "examples").glob("plot_*.py"))
    if not sources:
        raise SystemExit("No gallery examples found")
    for source in sources:
        generated = gallery / f"{source.stem}.ipynb"
        if not generated.exists():
            raise SystemExit(f"Missing {generated.name}; build Sphinx HTML first")
        notebook = json.loads(generated.read_text())
        notebook["nbformat_minor"] = 5
        for index, cell in enumerate(notebook["cells"]):
            cell["id"] = f"cell-{index:03d}"
        notebook["metadata"]["kernelspec"] = {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        }
        # The source notebook must not drift merely because CI uses another
        # Python patch release. Execution records the actual kernel version.
        notebook["metadata"].get("language_info", {}).pop("version", None)
        target = destination / generated.name
        target.write_text(json.dumps(notebook, indent=1, ensure_ascii=False) + "\n")
        print(target.relative_to(ROOT))


if __name__ == "__main__":
    main()
