from pathlib import Path
import pymupdf
import pytest

from pdfmd.evidence import Evidence
from pdfmd.storage import Store


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "source.pdf"
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "A complete synthetic section.\nKeep every value: 25 mg.")
    document.save(path)
    document.close()
    return path


@pytest.fixture
def route():
    return {"endpoint": "http://127.0.0.1:8317/v1/chat/completions", "model": "offline-fixture",
            "context_tokens": 65536, "output_tokens": 2048}


@pytest.fixture
def setup(tmp_path, source, route):
    store = Store(tmp_path / "workspace")
    job = Evidence(store).create_job(str(source), "Convert the complete synthetic section.", route)
    return store, job
