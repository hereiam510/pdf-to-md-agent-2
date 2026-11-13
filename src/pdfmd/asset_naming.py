"""Readable asset filenames and the portable comparison key (T3b).

Policies (docs/design/ASSET_REFERENCES.md, "Readable filenames and source
locators" and "Portable comparison and destination matrix"):

* ``readable-180-v1`` assembles ``description-locator[-figure][suffix].ext``,
  applies the prohibited-character substitutions and control flattening to
  generated components, NFC-normalizes with the pinned Unicode 17.0.0 data and
  rejects a basename above 180 UTF-8 bytes. Text is never shortened here; the
  agent supplies a faithful fitting label and receives the remaining budget.
* ``nfc-fullfold-u17-v1`` is ``NFC(full_case_fold(NFC(name)))`` using the C and
  F entries of the bundled Unicode 17.0.0 CaseFolding.txt, never the host
  runtime's unversioned ``str.casefold`` table.
"""
from __future__ import annotations

from functools import lru_cache
from importlib.resources import files
import re

import unicodedata2

NAMING_POLICY = "readable-180-v1"
COMPARISON_POLICY = "nfc-fullfold-u17-v1"
MAX_BYTES = 180
FALLBACK = "image"
SUBSTITUTIONS = str.maketrans({"<": "＜", ">": "＞", ":": "：", '"': "＂", "/": "／", "\\": "＼",
                               "|": "｜", "?": "？", "*": "＊"})
CONTROLS = re.compile(r"[\x00-\x1f\x7f]")
RESERVED = re.compile(r"(con|conin\$|conout\$|prn|aux|nul|com[1-9¹²³]|lpt[1-9¹²³])", re.ASCII | re.IGNORECASE)
EXTENSIONS = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}


class NameBudgetError(ValueError):
    def __init__(self, message: str, details: dict):
        super().__init__(message)
        self.details = details


def nfc(text: str) -> str:
    return unicodedata2.normalize("NFC", text)


@lru_cache(maxsize=1)
def _folding() -> dict[int, str]:
    table: dict[int, str] = {}
    data = files("pdfmd").joinpath("data/CaseFolding-17.0.0.txt").read_text(encoding="utf-8")
    if not data.startswith("# CaseFolding-17.0.0.txt"):
        raise RuntimeError("Bundled CaseFolding data is not Unicode 17.0.0.")
    for line in data.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        code, status, mapping = (part.strip() for part in line.split(";")[:3])
        if status in {"C", "F"}:
            table[int(code, 16)] = "".join(chr(int(c, 16)) for c in mapping.split())
    return table


def comparison_key(basename: str) -> str:
    folded = nfc(basename).translate(_folding())
    return nfc(folded)


def component(text: str) -> str:
    """Flatten controls and apply the agreed safety substitutions to generated text."""
    return CONTROLS.sub(" ", text).translate(SUBSTITUTIONS)


def stem(description: str) -> str:
    cleaned = component(description).lstrip()
    cleaned = re.sub(r"[\s.]+$", "", cleaned)  # outer whitespace and terminal ASCII dots
    return cleaned if cleaned.strip(". ") else FALLBACK


def locator(groups: list[dict], printed: dict[int, dict]) -> str:
    """Build ``p58``, ``p58–p59``, ``p58&p61``, ``i12–i13`` or ``p58&i67``.

    ``printed`` maps a physical page to its shared page-map state
    ``{"state": known|none|unknown, "value": str|None}``.
    """
    parts = []
    for group in groups:
        pages = group["pages"]
        known = [printed[p]["state"] == "known" for p in pages]
        def one(page: int) -> str:
            info = printed[page]
            return "p" + component(info["value"]) if info["state"] == "known" else f"i{page}"
        if group["kind"] == "single":
            parts.append(one(pages[0]))
        elif all(known):
            parts.append(f"{one(pages[0])}–{one(pages[-1])}")
        elif not any(known):
            parts.append(f"i{pages[0]}–i{pages[-1]}")
        else:
            raise ValueError("A range must be wholly printed or wholly physical; use single groups for mixed labels.")
    return "&".join(parts)


def suffix(number: int | None, punctuation: str) -> str:
    if number is None:
        return ""
    return f"（{number}）" if punctuation == "fullwidth" else f" ({number})"


def build(description: str, groups: list[dict], printed: dict[int, dict], figure: str | None,
          extension: str, punctuation: str, collision: int | None = None) -> str:
    """Assemble and validate one complete basename; raise NameBudgetError on overflow."""
    if extension not in EXTENSIONS:
        raise ValueError(f"Unsupported deliverable image type: {extension}")
    label = stem(description)
    fixed = "-" + locator(groups, printed) + ("-" + component(figure) if figure else "") + "." + extension
    tail = suffix(collision, punctuation)
    name = nfc(label + fixed[:-len(extension) - 1] + tail + "." + extension)
    # Win32 ignores ASCII spaces immediately before the first dot of a device name.
    base = name.split(".", 1)[0].rstrip(" ")
    prefix = "image-" if RESERVED.fullmatch(base) else ""
    name = prefix + name
    size = len(name.encode("utf-8"))
    if size > MAX_BYTES:
        fixed_bytes = len(nfc(prefix + fixed).encode("utf-8"))
        suffix_bytes = len(tail.encode("utf-8"))
        raise NameBudgetError(
            f"The filename needs {size} UTF-8 bytes; the limit is {MAX_BYTES}. Supply a shorter faithful "
            "description.filename label; the full description stays in the embedded record.",
            {"maximum": MAX_BYTES, "fixed_component_bytes": fixed_bytes, "suffix_bytes": suffix_bytes,
             "remaining_description_bytes": MAX_BYTES - fixed_bytes - suffix_bytes})
    if not name or any(c in name for c in '<>:"/\\|?*') or CONTROLS.search(name) or name.endswith((" ", ".")):
        raise ValueError("Generated filename failed validation.")
    return name
