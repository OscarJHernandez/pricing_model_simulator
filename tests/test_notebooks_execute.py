"""Execute every notebook under notebooks/ (requires PostgreSQL for DB-backed notebooks)."""

from __future__ import annotations

import os
from pathlib import Path

import nbformat
import pytest
from nbconvert.preprocessors import ExecutePreprocessor

REPO_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = REPO_ROOT / "notebooks"
NOTEBOOKS = sorted(NOTEBOOK_DIR.glob("*.ipynb"))


@pytest.mark.parametrize("nb_path", NOTEBOOKS, ids=[p.name for p in NOTEBOOKS])
def test_notebook_executes(nb_path: Path) -> None:
    if os.environ.get("SKIP_NOTEBOOK_TESTS") == "1":
        pytest.skip("SKIP_NOTEBOOK_TESTS=1")

    with nb_path.open(encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

    ep = ExecutePreprocessor(timeout=900, kernel_name="python3")
    ep.preprocess(nb, {"metadata": {"path": str(NOTEBOOK_DIR)}})
