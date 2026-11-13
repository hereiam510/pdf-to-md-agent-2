"""Preserved synthetic schema-1 snapshots for T2, never enriched-save acceptance.

Valid hyperlink-only inventories are explicitly assembled fixture snapshots.
The incomplete control is an explicit snapshot without its asset inventory,
reproducing what the pre-T3a embed-only save produced for a hyperlink.
No original conversion task or provider is accessed.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import random
import sys
import zipfile

import pymupdf

from pdfmd.documents import Documents, render
from pdfmd.schema import Document
from pdfmd.storage import Store, encode, uid
from pdfmd.tools import Dispatcher


def save(dispatcher, job, text, operation):
    current = dispatcher.store.get("job", job)
    result = dispatcher.execute(job, operation, "edit_document", json.dumps({
        "base_version": current["head"], "expected_head": current["head"],
        "replace_blocks": [{"id": "body", "pages": [1], "markdown": text}],
        "page_updates": {"1": {"disposition": "included", "printed": "none"}}, "claim": "complete"}))
    assert result["ok"], result
    return result["data"]["version_id"]


def snapshot(dispatcher, job, base, text, *, schema=1, inventory=True):
    """An explicit fixture constructor, not a production new-save path."""
    docs = dispatcher.documents
    envelope = deepcopy(docs.version(job, base))
    version = uid()
    envelope.update(version=version, schema_version=schema, parent=base)
    if not inventory:
        envelope.update(assets={}, originals={})
    envelope["content"]["blocks"][0]["markdown"] = text
    markdown = docs.markdown(Document.model_validate(envelope["content"]))
    files = {"document.json": encode(envelope), "document.md": markdown.encode("utf-8"),
             "preview.html": render(markdown, envelope["content"]["title"]).encode("utf-8")}
    for path in [*envelope["assets"], *envelope["originals"]]:
        files[path] = (docs.root / base / path).read_bytes()
    hashes = {name: sha256(data).hexdigest() for name, data in files.items()}
    files["manifest.json"] = encode({"version": version, "claim": envelope["content"]["claim"], "files": hashes.copy()})
    folder = docs.root / version
    for name, data in files.items():
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        hashes[name] = sha256(data).hexdigest()
    dispatcher.store.put("version", version, job, {"id": version, "job": job, "parent": base,
        "claim": "complete", "title": envelope["content"]["title"], "files": hashes})
    dispatcher.store.update_job(job, head=version)
    return version


def prepare(directory):
    root = Path(directory)
    source = root / "Reference fixture.pdf"
    picture = pymupdf.Pixmap(pymupdf.csRGB, 512, 512, random.Random(29).randbytes(512 * 512 * 3), False)
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=600, height=650)
        page.insert_text((32, 30), "Synthetic reference evidence. No provider.")
        page.insert_image(pymupdf.Rect(35, 60, 547, 572), stream=picture.tobytes("png"))
        pdf.save(source)
    store = Store(root / "workspace")
    dispatcher = Dispatcher(store)
    job = dispatcher.evidence.create_job(str(source), "T2 reference fixture only; do not start conversion.")
    store.update_job(job["id"], name="T2 references", status="paused", active_seconds=999999)
    image = dispatcher.evidence.render_page(job["id"], 1, 50)
    large_image = dispatcher.evidence.render_page(job["id"], 1, 144)
    jpeg = dispatcher.evidence.image(job["id"], picture.tobytes('jpeg'), 'jpg', {
        "source_ref": store.get('job', job['id'])['source_ref'], "page": 1, "width": 512, "height": 512,
        "derivation": "Synthetic JPEG encoding of the generated fixture picture; no production extraction claim."})
    path = image["asset_path"]
    large_path = large_image["asset_path"]
    base = save(dispatcher, job["id"], f'Baseline ![source]({path}) ![large]({large_path}) ![jpeg]({jpeg["asset_path"]})', "baseline")
    link = snapshot(dispatcher, job["id"], base, f'Hyperlink fixture [Open selected image]({path})')
    mixed_text = (f'Mixed fixture [Open selected image]({path})\n\n'
                  f'<a href="{path}">HTML image link</a>\n\n' + '\n\n'.join(f'![Repeated {i}]({large_path})' for i in range(4)) +
                  f'\n\n[![Linked thumbnail]({path})]({jpeg["asset_path"]})' +
                  '\n\n[External citation](https://example.invalid/forbidden)\n\n'
                  '<a href="https://example.invalid/window" target="_blank" download>New window</a>\n\n'
                  '<script>parent.document.body.dataset.sourceScript="ran"</script>')
    mixed = snapshot(dispatcher, job["id"], base, mixed_text)
    large_link = snapshot(dispatcher, job["id"], base, f'Large-link control [Large selected image]({large_path})\n\n' +
                          '\n\n'.join(f'![Large repeated {i}]({large_path})' for i in range(4)))
    incomplete = snapshot(dispatcher, job["id"], base, f'Historical incomplete [Missing source]({path})', inventory=False)
    unsupported = snapshot(dispatcher, job["id"], base, 'Unsupported historical ![remote alt](https://example.invalid/no-fetch.png)')
    unavailable = snapshot(dispatcher, job["id"], base, f'Future policy [Unavailable source]({path})', schema=999)
    store.update_job(job["id"], head=mixed)
    other = dispatcher.evidence.create_job(str(source), "Other isolated selection")
    store.update_job(other["id"], name="T2 other task", status="paused", active_seconds=999999)
    other_version = save(dispatcher, other["id"], "Other task marker", "other")
    corrupt = dispatcher.evidence.create_job(str(source), "Registered-file corruption control")
    store.update_job(corrupt["id"], name="T2 corrupt", status="paused", active_seconds=999999)
    corrupt_image = dispatcher.evidence.render_page(corrupt["id"], 1, 72)
    corrupt_version = save(dispatcher, corrupt["id"], f'Corrupt ![source]({corrupt_image["asset_path"]})', "corrupt")
    corrupt_path = dispatcher.documents.root / corrupt_version / corrupt_image["asset_path"]
    corrupt_path.write_bytes(corrupt_path.read_bytes() + b"intentional corruption control")
    result = {"job": job["id"], "link": link, "mixed": mixed, "incomplete": incomplete, "unsupported": unsupported,
              "unavailable": unavailable, "other": other["id"], "other_version": other_version, "corrupt": corrupt["id"],
              "corrupt_version": corrupt_version, "asset": path, "width": image["width"], "height": image["height"],
              "asset_bytes": len(store.bytes(image["ref"], job["id"])), "provider_calls": 0,
              "large_link": large_link, "large_width": large_image["width"], "large_height": large_image["height"],
              "large_asset": large_path, "large_bytes": len(store.bytes(large_image["ref"], job["id"])),
              "jpeg_asset": jpeg['asset_path'],
              "versions": {v: store.get("version", v, job=job["id"])["files"] for v in [base, link, mixed, large_link, incomplete, unsupported, unavailable]}}
    (root / "fixture.json").write_bytes(encode(result))
    return result


def advance(directory):
    root = Path(directory)
    fixture = json.loads((root / "fixture.json").read_bytes())
    dispatcher = Dispatcher(Store(root / "workspace"))
    version = save(dispatcher, fixture["job"], "Advanced head marker", "advanced-" + uid())
    return {"version": version}


def verify(directory):
    root = Path(directory)
    fixture = json.loads((root / "fixture.json").read_bytes())
    store = Store(root / "workspace")
    documents = Documents(store)
    for version, files in fixture["versions"].items():
        assert store.get("version", version, job=fixture["job"])["files"] == files
        for name, digest in files.items():
            assert sha256((documents.root / version / name).read_bytes()).hexdigest() == digest
            if name.endswith(('.md', '.html', '.json')):
                assert b'pdfmd-preview:' not in (documents.root / version / name).read_bytes()
                assert b'pdfmd-resource-' not in (documents.root / version / name).read_bytes()
    for name, version in [("link.zip", fixture["link"]), ("incomplete.zip", fixture["incomplete"])]:
        record = store.get("version", version, job=fixture["job"])
        with zipfile.ZipFile(root / name) as archive:
            assert set(archive.namelist()) == set(record["files"])
            assert all(archive.read(n) == (documents.root / version / n).read_bytes() for n in archive.namelist())
    assert not (root / "corrupt.zip").exists()
    assert all(j["attempts"] == 0 for j in store.records("job"))
    assert all(not store.records("request", j["id"]) for j in store.records("job"))
    assert all("asset_reference_check" not in r for r in store.records("export", fixture["job"]))
    return {"original_versions_unchanged": True, "selected_zip_members_and_bytes_equal": True,
            "historical_incomplete_not_healed": True, "corrupt_zip_absent": True, "provider_requests": 0,
            "enriched_save_acceptance": False}


if __name__ == "__main__":
    print(json.dumps(globals()[sys.argv[1]](sys.argv[2]), ensure_ascii=True))
