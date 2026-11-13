"""Local package smoke check. This script makes no network or model requests."""
import ssl
import sys

import httpx
import pymupdf

assert getattr(sys, "frozen", False), "Run this check through the frozen engine."
context = ssl.create_default_context()
assert context.verify_mode == ssl.CERT_REQUIRED
with httpx.Client(http2=True, trust_env=False):
    pass
print("Frozen engine: TLS validation, HTTP client, PDF resources, and script entry point ready.")

# T3b writer boundary: an enriched save in the frozen engine relaunches this
# executable with --xmp-prepare (bounded Job worker) and embeds the record.
import json
import tempfile
from pathlib import Path

from pdfmd import primary_xmp, xmp_worker
from pdfmd.storage import Store
from pdfmd.tools import Dispatcher

calls = []
real_command = xmp_worker.command
xmp_worker.command = lambda arguments: calls.append(real_command(arguments)) or calls[-1]
with tempfile.TemporaryDirectory() as folder:
    root = Path(folder)
    with pymupdf.open() as document:
        document.new_page(width=300, height=200).insert_text((20, 40), "Frozen enrichment check")
        document.save(root / "check.pdf")
    dispatcher = Dispatcher(Store(root / "workspace"))
    job = dispatcher.evidence.create_job(str(root / "check.pdf"), "Frozen enrichment check")["id"]
    render = dispatcher.evidence.render_page(job, 1, 50)
    basis = [{"ref": render["ref"], "physical_page": 1, "region": None, "note": "frozen check"}]
    result = dispatcher.execute(job, "frozen-check", "edit_document", json.dumps({
        "base_version": None, "expected_head": None, "page_updates": {"1": {"disposition": "included"}},
        "replace_blocks": [{"id": "b", "pages": [1], "markdown": "![x](asset:new/x)"}],
        "asset_changes": [{"kind": "create", "client_key": "x", "facts": {"image_ref": render["ref"],
            "description": {"full": "Frozen check", "filename": "Frozen check", "language": "en", "punctuation": "ascii", "basis": []},
            "locations": [{"physical_page": 1, "region": None, "basis": basis}]}}]}))
    assert result["ok"], result
    change = result["data"]["asset_changes"][0]
    saved = (dispatcher.documents.root / result["data"]["version_id"] / change["asset_path"]).read_bytes()
    packet = primary_xmp.locate_png_primary(primary_xmp.parse_png(saved))["packet"]
    record = json.loads("".join(c.data for c in packet.props[(primary_xmp.PDFMD, "RecordJSON")]["node"].childNodes))
    assert record["occurrence_id"] == change["occurrence_id"]
    assert calls and calls[0][:2] == [sys.executable, "--xmp-prepare"], calls
print("Frozen engine: bounded XMP worker relaunch and enriched save ready.")
