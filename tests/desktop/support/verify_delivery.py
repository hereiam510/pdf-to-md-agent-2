"""Check synthetic source, a fresh saved-version reader and every ZIP member."""
from hashlib import sha256
import json
from pathlib import Path
import sys
import zipfile

import pymupdf

from pdfmd.documents import Documents
from pdfmd.storage import Store


def verify(workspace, source, archive, job, version):
    store = Store(workspace)
    documents = Documents(store)
    saved = documents.version(job, version)
    with pymupdf.open(source) as pdf, zipfile.ZipFile(archive) as z:
        markdown = z.read('document.md').decode('utf-8')
        assert all(line in markdown for page in pdf for line in page.get_text().splitlines())
        assert json.loads(z.read('document.json')) == saved
        files = store.get('version', version, job=job)['files']
        assert set(z.namelist()) == set(files) and len(z.namelist()) == len(files)
        for name in z.namelist():
            assert z.read(name) == (documents.root / version / name).read_bytes()
        for path, asset in saved['assets'].items():
            assert z.read(path) == store.bytes(asset['ref'], job)
        assert store.bytes(saved['source_ref'], job) == Path(source).read_bytes()
        return {'job': job, 'version': version, 'claim': saved['content']['claim'], 'source_pages': len(pdf),
                'blocks': len(saved['content']['blocks']), 'assets': len(saved['assets']), 'verified': True,
                'source_sha256': sha256(Path(source).read_bytes()).hexdigest(),
                'zip_sha256': sha256(Path(archive).read_bytes()).hexdigest(), 'members': files}


if __name__ == '__main__':
    print(json.dumps(verify(*sys.argv[1:])))
