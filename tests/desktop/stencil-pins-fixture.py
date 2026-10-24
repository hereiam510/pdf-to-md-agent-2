"""Local deterministic conversion, artifact and real-renderer color checks."""
import json
from pathlib import Path
import sys

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_stencil_pins import run_delivery, verify_delivery


def colors(directory):
    observations = []
    for stage in ["saved", "reopened", "exported"]:
        for name, channel in [("red", 0), ("blue", 2)]:
            path = directory / f"{stage}-{name}.png"
            pix = pymupdf.Pixmap(str(path))
            samples = pix.samples
            pixels = [samples[i:i + pix.n] for i in range(0, len(samples), pix.n)]
            painted = sum(p[channel] > 200 and all(p[c] < 30 for c in [0, 1, 2] if c != channel) for p in pixels)
            assert painted > len(pixels) * .3, (path, painted, len(pixels))
            observations.append({"file": path.name, "painted_pixels": painted, "total_pixels": len(pixels)})
    result = {"observations": observations, "all_expected_colors_present": True, "live_model_calls": 0}
    (directory / "renderer-colors.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    mode, directory = sys.argv[1], Path(sys.argv[2])
    if mode == "prepare":
        result = run_delivery(directory, {"endpoint": "http://127.0.0.1:8317/v1/chat/completions",
                              "model": "offline-fixture", "context_tokens": 65536, "output_tokens": 2048}, sys.argv[3])
    else:
        result = verify_delivery(directory) if mode == "verify" else colors(directory)
    print(json.dumps(result))
