"""Local deferred-update fixture; never loads credentials or uses a real provider."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_context_retry_delivery import run_retry_delivery
from test_stencil_pins import verify_delivery


if __name__ == "__main__":
    mode, directory, protocol = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
    if mode == "prepare":
        result = run_retry_delivery(directory, {"endpoint": "http://127.0.0.1:8317/v1/chat/completions",
            "model": "offline-fixture", "context_tokens": 40000, "output_tokens": 2048}, protocol)
    else:
        result = verify_delivery(directory)
    print(json.dumps(result))
