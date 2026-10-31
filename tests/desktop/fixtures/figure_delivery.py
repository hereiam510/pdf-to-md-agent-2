"""Synthetic FD-01 renderer fixture. Never starts conversion or calls a provider."""
import json
from pathlib import Path
import sys

from tests.engine.documents.test_figure_delivery import prepare_figures, verify_figures


if __name__ == "__main__":
    directory = Path(sys.argv[2])
    result = prepare_figures(directory) if sys.argv[1] == "prepare" else verify_figures(directory)
    print(json.dumps(result))
