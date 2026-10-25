"""Local deferred-update fixture; never loads credentials or uses a real provider."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_context_retry_delivery import run_retry_delivery
from test_context_capacity_delivery import run_capacity_delivery
from test_stencil_pins import verify_delivery


if __name__ == "__main__":
    mode, directory, protocol = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
    if mode == "prepare":
        scenario = sys.argv[4] if len(sys.argv) > 4 else "history"
        route = {"endpoint": "http://127.0.0.1:8317/v1/chat/completions",
                 "model": "offline-fixture", "context_tokens": 40000, "output_tokens": 2048}
        result = (run_retry_delivery(directory, route, protocol) if scenario == "history"
                  else run_capacity_delivery(directory, route, protocol, scenario))
    else:
        result = verify_delivery(directory)
    print(json.dumps(result))
