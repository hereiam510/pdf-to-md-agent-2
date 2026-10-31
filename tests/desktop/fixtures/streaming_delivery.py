"""Synthetic streaming recovery evidence; no live Nexus or private source."""
import json
from pathlib import Path
import sys

from tests.engine.transport.test_streaming_delivery import prepare_stream_delivery, verify_stream_delivery

if __name__ == "__main__":
    mode, directory = sys.argv[1], Path(sys.argv[2])
    value = (prepare_stream_delivery(directory, sys.argv[3], sys.argv[4])
             if mode == "prepare" else verify_stream_delivery(directory))
    print(json.dumps(value))
