"""Synthetic local delivery fixture. No credentials or real provider calls."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_working_evidence_delivery import run_working_delivery, verify_working_delivery


if __name__ == "__main__":
    mode, directory, protocol = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
    if mode == "prepare":
        route = {"endpoint": "http://127.0.0.1:8317/v1/chat/completions", "model": "offline-fixture",
                 "context_tokens": 131072, "output_tokens": 2048}
        result = run_working_delivery(directory, route, protocol)
    else:
        result = verify_working_delivery(directory)
    print(json.dumps(result))
