"""Execute all course notebooks in fresh kernels and retain executed copies."""

import os
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Fail on the first notebook error and save successful outputs under build/."""
    destination = ROOT / "build/executed-notebooks"
    destination.mkdir(parents=True, exist_ok=True)
    # Also supports verifying an unpacked checkout before editable installation.
    os.environ["PYTHONPATH"] = str(ROOT) + os.pathsep + os.environ.get("PYTHONPATH", "")
    notebooks = sorted((ROOT / "notebooks").glob("plot_*.ipynb"))
    if not notebooks:
        raise SystemExit("No notebooks found; build docs and run sync_notebooks.py first")
    for path in notebooks:
        notebook = nbformat.read(path, as_version=4)
        NotebookClient(
            notebook,
            timeout=180,
            kernel_name="python3",
            resources={"metadata": {"path": str(ROOT)}},
        ).execute()
        nbformat.write(notebook, destination / path.name)
        print(f"Executed {path.name}", flush=True)


if __name__ == "__main__":
    main()
