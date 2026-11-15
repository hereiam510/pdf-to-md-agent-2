import json

import pytest

from pdfmd.tools import Dispatcher
from tests.engine.documents.test_documents import call, edit


@pytest.mark.parametrize("invalid", [{"top": -1}, {"width": 319}, {"height": 199}])
def test_preview_argument_error_is_readable(setup, invalid):
    store, job = setup
    dispatcher = Dispatcher(store)
    version = call(dispatcher, job["id"], "save", edit())["data"]["version_id"]
    result = dispatcher.execute(job["id"], "preview", "preview_document",
                                json.dumps({"version_id": version, **invalid}))
    assert result["ok"] is False
    assert result["data"]["error"] == "Use a nonnegative scroll offset, width 320–3000, and height 200–3000."
