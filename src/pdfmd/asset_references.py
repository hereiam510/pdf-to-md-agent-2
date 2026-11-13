"""Whole-document reference interpretation for delivery, assessment and preview.

The syntax authority is markdown-it-py 4.2.0 with the existing table/footnote
rules. MappedText carries original code-point positions through those rules;
the destination helper records only destinations the parser actually accepts.
No global parser/module mutation or filesystem lookup participates in parsing.
The indentation adaptation's upstream notices are in data/markdown-it-LICENSE.txt.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, dataclass
import html
from html.parser import HTMLParser
import re
from types import SimpleNamespace
from hashlib import sha256
from urllib.parse import quote, unquote, unquote_to_bytes, urlsplit

from markdown_it import MarkdownIt
from markdown_it.common.utils import isStrSpace
from markdown_it.parser_block import ParserBlock
from markdown_it.rules_block import StateBlock, reference
from markdown_it.rules_inline import autolink, image, link
from mdit_py_plugins.footnote import footnote_plugin
import nh3


@dataclass(frozen=True)
class SourceSpan:
    block_id: str
    start: int
    end: int
    expected: str


@dataclass(frozen=True)
class Reference:
    destination: str
    role: str
    block_id: str | None
    span: SourceSpan | None


class ReferenceError(ValueError):
    def __init__(self, code: str, message: str, ref: Reference | None = None):
        super().__init__(message)
        self.issue = {"code": code, "message": message,
                      "destination": ref.destination if ref else None,
                      "role": ref.role if ref else None,
                      "span": asdict(ref.span) if ref and ref.span else None}


class MappedText(str):
    """A parser input string with one original half-open interval per character."""
    def __new__(cls, value, origins=None):
        obj = super().__new__(cls, value)
        obj.origins = origins if origins is not None else [None] * len(value)
        return obj

    def __getitem__(self, key):
        value = super().__getitem__(key)
        return MappedText(value, self.origins[key]) if isinstance(key, slice) else value

    def __add__(self, other):
        return MappedText(str(self) + str(other), self.origins + getattr(other, "origins", [None] * len(other)))

    def __radd__(self, other):
        return MappedText(str(other) + str(self), getattr(other, "origins", [None] * len(other)) + self.origins)

    def strip(self, chars=None):
        start = len(self) - len(str.lstrip(self, chars))
        end = len(str.rstrip(self, chars))
        return self[start:max(start, end)]


def mapped_join(parts):
    return MappedText("".join(parts), [origin for part in parts for origin in getattr(part, "origins", [None] * len(part))])


class MappedBlockState(StateBlock):
    def getLines(self, begin, end, indent, keepLastLF):
        # Same indentation/tab semantics as upstream StateBlock.getLines (MIT),
        # retaining slices instead of losing correspondence in str.join.
        pieces = []
        for line in range(begin, end):
            first = line_start = self.bMarks[line]
            last = self.eMarks[line] + (line + 1 < end or keepLastLF)
            line_indent = 0
            while first < last and line_indent < indent:
                ch = self.src[first]
                if isStrSpace(ch):
                    line_indent += 4 - (line_indent + self.bsCount[line]) % 4 if ch == "\t" else 1
                elif first - line_start < self.tShift[line]:
                    line_indent += 1
                else:
                    break
                first += 1
            pieces.append(" " * max(0, line_indent - indent) + self.src[first:last])
        return mapped_join(pieces)


class MappedBlockParser(ParserBlock):
    def parse(self, src, md, env, outTokens):
        if not src:
            return None
        state = MappedBlockState(src, md, env, outTokens)
        self.tokenize(state, state.line, state.lineMax)
        return state.tokens


def compose(blocks: list[dict], pages: dict) -> tuple[MappedText, dict[str, str]]:
    """The normal saved Markdown, with generated markers deliberately unmapped."""
    pieces = []
    originals = {}
    for block in blocks:
        if block["id"] in originals:
            raise ReferenceError("inventory_mismatch", "Block IDs must be unique.")
        originals[block["id"]] = block["markdown"]
        positions = ", ".join(str(p) for p in block["pages"])
        labels = ", ".join(f"{p}={pages[str(p)]['printed']}" for p in block["pages"])
        if pieces:
            pieces.append("\n\n")
        pieces.append(f"<!-- PDF pages: {positions} | printed pages: {labels} -->\n\n")
        pieces.append(MappedText(block["markdown"], [(block["id"], i, i + 1) for i in range(len(block["markdown"]))]))
    pieces.append("\n" if blocks else "")
    return mapped_join(pieces), originals


def source_span(text, start, end, originals):
    if not isinstance(text, MappedText) or not originals:
        return None
    if start == end:
        origin = text.origins[start] if start < len(text) else None
        return SourceSpan(origin[0], origin[1], origin[1], "") if origin else None
    origins = text.origins[start:end]
    if not origins or any(x is None or x[0] != origins[0][0] for x in origins):
        return None
    if any(a[2] > b[1] for a, b in zip(origins, origins[1:])):
        return None
    block, first, _ = origins[0]
    last = origins[-1][2]
    return SourceSpan(block, first, last, originals[block][first:last])


def safe_fragment(value: str) -> str:
    return nh3.clean(value,
                     tags=set(nh3.ALLOWED_TAGS) | {"sup", "sub", "table", "thead", "tbody", "tr", "td", "th", "img"},
                     attributes={**nh3.ALLOWED_ATTRIBUTES, "img": {"src", "alt", "title", "width", "height"},
                                 "td": {"colspan", "rowspan"}, "th": {"colspan", "rowspan", "scope"},
                                 "*": {"id", "class", "lang"}},
                     url_schemes={"http", "https", "mailto"})


# This scans attributes of parser-emitted HTML tokens, never Markdown syntax.
ATTR = re.compile(r'''([^\s/=>]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?''')


def attributes(raw):
    match = re.match(r"<\s*[^\s/>]+", raw)
    if not match:
        return []
    found = []
    for attr in ATTR.finditer(raw, match.end()):
        value_group = next((i for i in (2, 3, 4) if attr.group(i) is not None), None)
        found.append((attr.group(1).lower(), html.unescape(attr.group(value_group)) if value_group else None,
                      attr.start(value_group) if value_group else None, attr.end(value_group) if value_group else None))
    return found


class ResourceHTML(HTMLParser):
    def __init__(self, text, originals=None):
        super().__init__(convert_charrefs=True)
        self.text, self.originals = text, originals or {}
        self.refs: list[Reference] = []
        self.issues: list[dict] = []
        self.line_starts = [0] + [m.end() for m in re.finditer("\n", text)]
        self.anchor_depth = 0

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == "a":
            self.anchor_depth = max(0, self.anchor_depth - 1)

    def handle_starttag(self, tag, attrs):
        raw = self.get_starttag_text()
        offset = self.line_starts[self.getpos()[0] - 1] + self.getpos()[1]
        operative = "src" if tag == "img" else "href" if tag == "a" else None
        parsed = attributes(raw)
        values = [x for x in parsed if x[0] == operative] if operative else []
        ref = None
        if values:
            _, destination, start, end = values[0]
            span = source_span(self.text, offset + start, offset + end, self.originals) if start is not None else None
            block = span.block_id if span else None
            ref = Reference(destination or "", "image" if tag == "img" else "hyperlink", block, span)
            self.refs.append(ref)
        if tag == "a":
            if self.anchor_depth:
                self.issues.append(ReferenceError("unsupported_resource_markup", "Nested anchors change resource-label binding during HTML repair; separate the links.", ref).issue)
            self.anchor_depth += 1
        if len(values) > 1 or (values and [(n, v) for n, v, _, _ in parsed] != attrs):
            self.issues.append(ReferenceError("unsupported_resource_markup", "Ambiguous or duplicate resource attributes; use one src/href attribute.", ref).issue)
        if tag in {"picture", "source"} or any(n == "srcset" for n, _ in attrs):
            self.issues.append(ReferenceError("unsupported_resource_markup", "Use supported img.src or a.href resource markup.", ref).issue)


@dataclass
class Analysis:
    references: list[Reference]
    issues: list[dict]
    html: str

    def require_supported(self):
        if self.issues:
            issue = self.issues[0]
            error = ReferenceError(issue["code"], issue["message"])
            error.issue = issue
            raise error


def parser() -> MarkdownIt:
    return MarkdownIt("commonmark", {"html": True}).enable("table").use(footnote_plugin)


def analyze(blocks: list[dict], pages: dict) -> Analysis:
    text, originals = compose(blocks, pages)
    md = parser()
    md.block = MappedBlockParser()
    # footnote_plugin installs both block and inline/core rules; copy only its
    # configured block ruler so inline/core registrations stay single.
    md.block.ruler = parser().block.ruler
    md.options["store_labels"] = True
    # Retain input-only handles and disallowed image schemes until assessment.
    # The same tokens still go through the normal safe scheme filter below.
    md.validateLink = lambda value: True
    normalize_link = md.normalizeLink
    # Do not let URL normalization repair malformed percent escapes into valid
    # literal-percent names before the strict one-decode lookup can reject them.
    md.normalizeLink = lambda value: value if re.search(r"%(?![0-9A-Fa-f]{2})", value) else normalize_link(value)
    frames = []
    base_helper = md.helpers.parseLinkDestination

    def destination(src, pos, maximum):
        result = base_helper(src, pos, maximum)
        if result.ok and frames:
            angle = src[pos:pos + 1] == "<"
            frames[-1].append(source_span(src, pos + int(angle), result.pos - int(angle), originals))
        return result

    md.helpers = SimpleNamespace(**{name: getattr(md.helpers, name) for name in dir(md.helpers) if not name.startswith("_")})
    md.helpers.parseLinkDestination = destination

    def normalize(state):
        source = state.src
        pieces = []
        cursor = 0
        for match in re.finditer(r"\r\n?|\x00", source):
            pieces.append(source[cursor:match.start()])
            origin = source.origins[match.start():match.end()]
            mapped = (origin[0][0], origin[0][1], origin[-1][2]) if all(origin) and origin[0][0] == origin[-1][0] else None
            pieces.append(MappedText("\ufffd" if match.group() == "\x00" else "\n", [mapped]))
            cursor = match.end()
        pieces.append(source[cursor:])
        state.src = mapped_join(pieces)

    md.core.ruler.at("normalize", normalize)

    def definition(state, start, end, silent):
        captures = []
        prior = {k: id(v) for k, v in state.env.get("references", {}).items()}
        frames.append(captures)
        try:
            accepted = reference(state, start, end, silent)
        finally:
            frames.pop()
        if accepted and not silent:
            for key, value in state.env.get("references", {}).items():
                if prior.get(key) != id(value):
                    value["source_span"] = captures[-1] if captures else None
        return accepted

    md.block.ruler.at("reference", definition)

    def instrument(rule, token_type):
        def wrapped(state, silent):
            start, first = state.pos, len(state.tokens)
            captures = []
            frames.append(captures)
            try:
                accepted = rule(state, silent)
            finally:
                frames.pop()
            if accepted and not silent:
                token = next(t for t in state.tokens[first:] if t.type == token_type)
                label = token.meta.get("label")
                span = state.env["references"][label].get("source_span") if label else (captures[0] if captures else None)
                origin = state.src.origins[start] if isinstance(state.src, MappedText) else None
                token.meta["asset_reference"] = Reference(token.attrGet("src" if token_type == "image" else "href") or "",
                                                         "image" if token_type == "image" else "hyperlink", origin[0] if origin else None, span)
            return accepted
        return wrapped

    md.inline.ruler.at("link", instrument(link, "link_open"))
    md.inline.ruler.at("image", instrument(image, "image"))
    def handle_autolink(state, silent):
        start, first = state.pos, len(state.tokens)
        accepted = autolink(state, silent)
        if accepted and not silent:
            token = next(t for t in state.tokens[first:] if t.type == "link_open")
            destination = token.attrGet("href") or ""
            if destination.lower().startswith("asset:"):
                span = source_span(state.src, start + 1, state.pos - 1, originals)
                token.meta["asset_reference"] = Reference(destination, "hyperlink", span.block_id if span else None, span)
                token.meta["unsupported_asset_autolink"] = True
        return accepted
    md.inline.ruler.at("autolink", handle_autolink)
    env = {}
    tokens = md.parse(text, env)
    refs, issues = [], []

    def collect(items, image_alt=False):
        for token in items:
            if not image_alt and "asset_reference" in token.meta:
                refs.append(token.meta["asset_reference"])
                if token.meta.get("unsupported_asset_autolink"):
                    issues.append(ReferenceError("unsupported_resource_markup", "Input asset handles need inline/reference links or HTML attributes; a relative asset URI cannot replace an autolink destination.", token.meta["asset_reference"]).issue)
            if not image_alt and token.type in {"html_inline", "html_block"}:
                scan = ResourceHTML(token.content, originals)
                scan.feed(token.content)
                scan.close()
                refs.extend(scan.refs)
                issues.extend(scan.issues)
            if token.children:
                collect(token.children, image_alt or token.type == "image")

    collect(tokens)
    rendered = md.renderer.render(tokens, md.options, env)
    complete_html = ResourceHTML(str(rendered))
    complete_html.feed(rendered)
    issues.extend(complete_html.issues)
    safe = safe_fragment(rendered)
    # HTMLParser is a span scanner, not an HTML5 repair authority. Compare the
    # complete resource multiset with nh3's HTML5 interpretation before use.
    output = ResourceHTML(safe)
    output.feed(safe)
    def comparable(ref):
        try:
            return classify(ref.destination, ref.role)[0] in {"asset", "handle", "invalid"}
        except ValueError:
            return True
    before = Counter((r.role, r.destination) for r in refs if comparable(r))
    after = Counter((r.role, r.destination) for r in output.refs if comparable(r))
    # Handles intentionally disappear at the sanitizer boundary, never publish.
    before = Counter({k: v for k, v in before.items() if not k[1].lower().startswith("asset:")})
    if before != after:
        changed = next((r for r in refs if (r.role, r.destination) in before - after), None)
        message = "Resource markup disagrees with safe rendering; use unambiguous supported markup."
        if changed and changed.role == "image" and classify(changed.destination, changed.role)[0] == "invalid":
            message = "Image sources must use the canonical URI of a registered local asset."
        issues.append(ReferenceError("unsupported_resource_markup", message, changed).issue)
    return Analysis(refs, issues, safe)


def asset_uri(path: str) -> str:
    if not path.startswith("assets/") or not valid_basename(path[7:]):
        raise ValueError("An exact registered assets/<basename> path is required.")
    return "assets/" + quote(path[7:], safe="-._~", encoding="utf-8", errors="strict")


def valid_basename(name):
    return bool(name) and name not in {".", ".."} and not any(c in name for c in "/\\") and not any(ord(c) < 32 or ord(c) == 127 for c in name)


def classify(destination: str, role: str) -> tuple[str, str | None]:
    """Return asset path, input handle, unrelated link, or invalid; no IO/aliases."""
    if destination.lower().startswith("asset:"):
        if re.fullmatch(r"asset:new/[A-Za-z0-9_-]{1,64}", destination) or re.fullmatch(r"asset:id/[A-Za-z0-9_-]+", destination):
            return "handle", destination
        return "invalid", None
    try:
        parts = urlsplit(destination)
    except ValueError:
        return "invalid", None
    if parts.scheme or parts.netloc or destination.startswith("//"):
        return ("invalid", None) if role == "image" else ("unrelated", None)
    if destination.startswith("#") and role != "image":
        return "unrelated", None
    try:
        if re.search(r"%(?![0-9A-Fa-f]{2})", parts.path):
            raise ValueError("Malformed URI escape")
        decoded = unquote_to_bytes(parts.path).decode("utf-8", "strict")
    except (ValueError, UnicodeError):
        if role == "image":
            return "invalid", None
        # An ordinary relative citation (e.g. "100%-coverage.md") is not an
        # asset reference. Keep strict rejection only for reserved assets paths,
        # judged on a lenient decode so escaped separators still count.
        lenient = unquote(parts.path, errors="replace")
        if any(c.casefold() == "assets" for c in re.split(r"[/\\]", lenient)):
            return "invalid", None
        return "unrelated", None
    components = re.split(r"[/\\]", decoded)
    reserved = any(c.casefold() == "assets" for c in components)
    if not reserved:
        return ("invalid", None) if role == "image" else ("unrelated", None)
    if not destination.startswith("assets/") or decoded.count("/") != 1 or "\\" in decoded or "?" in destination or "#" in destination:
        return "invalid", None
    # Decode basename once, never URL-decode the resulting filesystem spelling.
    basename = decoded[7:]
    if not decoded.startswith("assets/") or not valid_basename(basename) or "%" in parts.path[:7]:
        return "invalid", None
    return "asset", decoded


def dependencies(analysis: Analysis, registered: set[str], *, handles: dict[str, str] | None = None) -> dict[str, list[Reference]]:
    """Pre-publication resolver for the T3a schema 1 save and T3b/T4 enriched saves; handles require an explicit edit mapping."""
    analysis.require_supported()
    result = {}
    for ref in analysis.references:
        kind, path = classify(ref.destination, ref.role)
        if kind == "unrelated":
            continue
        if kind == "invalid":
            if ref.destination.lower().startswith("asset:"):
                raise ReferenceError("ASSET_REFERENCE_INVALID",
                                     "Invalid input asset handle. Use lowercase asset:new/<client_key> with a matching "
                                     "asset_changes create. Use 1 to 64 ASCII letters, digits, underscores or hyphens "
                                     "for the client_key. For an existing occurrence, use asset:id/<occurrence_id> "
                                     "from the selected schema 2 base.", ref)
            raise ReferenceError("ASSET_REFERENCE_INVALID", "Use the exact registered asset URI; image sources must be local registered assets.", ref)
        if kind == "handle":
            if ref.span is None:
                raise ReferenceError("ASSET_SPAN_AMBIGUOUS", "Write the handle in an explicit link or image destination "
                                     "with an unambiguous source span.", ref)
            path = (handles or {}).get(ref.destination)
            if path is None:
                if ref.destination.startswith("asset:new/"):
                    key = ref.destination.removeprefix("asset:new/")
                    raise ReferenceError("ASSET_REFERENCE_INVALID",
                                         f"To resolve this handle, add an asset_changes create with client_key {key!r} and facts.image_ref set to the "
                                         "render_page or extract_image result's ref, with its source-grounded facts.", ref)
                raise ReferenceError("ASSET_REFERENCE_INVALID",
                                     "For this handle, use an occurrence ID from the selected schema 2 base, or add an asset_changes create "
                                     "and use asset:new/<client_key>.", ref)
            asset_uri(path)
        if path not in registered:
            raise ReferenceError("ASSET_NOT_OWNED", "This asset is not registered in the selected task/version. Register it in this edit or correct the destination.", ref)
        if ref.span is None:
            raise ReferenceError("ASSET_SPAN_AMBIGUOUS", "The operative destination has no unambiguous guarded source span.", ref)
        result.setdefault(path, []).append(ref)
    return result


def rewrite(blocks: list[dict], pages: dict, analysis: Analysis, replacements: dict[str, str]) -> list[dict]:
    """Guard, patch each controlling span once, and verify every operative role."""
    from copy import deepcopy
    analysis.require_supported()
    edits = {}
    for ref in analysis.references:
        if ref.destination not in replacements:
            continue
        span = ref.span
        if span is None:
            raise ReferenceError("ASSET_SPAN_AMBIGUOUS", "Cannot rewrite a destination without exact source correspondence.", ref)
        value = replacements[ref.destination]
        kind, _ = classify(value, ref.role)
        if kind != "asset":
            raise ReferenceError("ASSET_REFERENCE_INVALID", "Replacements must be serialized canonical asset URIs.", ref)
        key = (span.block_id, span.start, span.end)
        if key in edits and edits[key][1] != value:
            raise ReferenceError("ASSET_SPAN_AMBIGUOUS", "A shared destination has conflicting replacements.", ref)
        edits[key] = (span, value)
    result = deepcopy(blocks)
    for block in result:
        last = len(block["markdown"]) + 1
        for span, value in sorted((v for v in edits.values() if v[0].block_id == block["id"]), key=lambda v: v[0].start, reverse=True):
            if span.end > last or not 0 <= span.start <= span.end <= len(block["markdown"]) or block["markdown"][span.start:span.end] != span.expected:
                raise ReferenceError("ASSET_SPAN_AMBIGUOUS", "Destination source guard failed; retain the candidate and reanalyze the working blocks.")
            block["markdown"] = block["markdown"][:span.start] + value + block["markdown"][span.end:]
            last = span.start
    after = analyze(result, pages)
    after.require_supported()
    expected = [(r.role, r.block_id, replacements.get(r.destination, r.destination)) for r in analysis.references]
    if [(r.role, r.block_id, r.destination) for r in after.references] != expected:
        raise ReferenceError("ASSET_SPAN_AMBIGUOUS", "Reparsed destinations/roles disagree with the requested source edits.")
    return result


POLICY = {"schema": 1, "naming": "readable-180-v1", "comparison": "nfc-fullfold-u17-v1",
          "uri": "utf8-percent-v1", "provenance": 1}


def _shared_schema1_original(original: dict, actual: dict, source_ref: str,
                             lookup: Callable[[str], dict | None]) -> bool:
    provenance = actual.get("provenance")
    if not isinstance(provenance, dict) or not source_ref or provenance.get("source_ref") != source_ref:
        return False
    digest = actual["sha256"]
    stem = f"originals/{provenance.get('xref')}-{digest}"
    if original["path"] not in {f"{stem}.{ext}" for ext in ("bin", "jpeg", "jpx")}:
        return False
    # Each registration must independently attest to the retained stream.
    # The selected version's verified original supplies the actual bytes.
    for ref in (original["ref"], actual["ref"]):
        record = lookup(ref)
        if (record is None or record.get("ref") != ref or record.get("kind") != "image_stream"
                or record.get("sha256") != digest or record.get("meta") != provenance):
            return False
    return True


def assess(
    saved: dict, files: dict[str, str], *, original_record: Callable[[str], dict | None] | None = None,
) -> tuple[dict, Analysis | None]:
    """Out-of-band completeness diagnosis, after the caller's byte-integrity gate.

    For a schema 1 ref mismatch, a task-scoped lookup can prove two records
    describe an already verified original member. It supplies metadata only.
    """
    try:
        if saved.get("schema_version") not in {1, 2} or (saved["schema_version"] == 2 and saved.get("asset_policy") != POLICY):
            return {"status": "unavailable", "issues": [ReferenceError("unsupported_policy", "This saved version's asset policy is unsupported.").issue]}, None
        content = saved["content"]
        analysis = analyze(content["blocks"], content["pages"])
        issues = list(analysis.issues)
        expected_md = str(compose(content["blocks"], content["pages"])[0]).encode("utf-8")
        if files.get("document.md") != sha256(expected_md).hexdigest():
            issues.append(ReferenceError("inventory_mismatch", "Saved Markdown and the selected content envelope disagree.").issue)
        assets, originals = saved["assets"], saved.get("originals", {})
        uses_by_path = {}
        for ref in analysis.references:
            kind, path = classify(ref.destination, ref.role)
            if kind == "unrelated":
                continue
            if kind != "asset":
                issues.append(ReferenceError("noncanonical_destination", "Use an exact registered local asset destination; this saved target is unavailable.", ref).issue)
                continue
            uses_by_path.setdefault(path, ref)
            if path not in assets:
                issues.append(ReferenceError("missing_version_asset", "The selected saved version does not contain this asset. Its original inventory is preserved.", ref).issue)
            elif path not in files or files[path] != assets[path]["sha256"]:
                issues.append(ReferenceError("inventory_mismatch", "The asset inventory and registered version files disagree.", ref).issue)
        for path, asset in assets.items():
            use = uses_by_path.get(path)
            if classify(asset_uri(path), "image") != ("asset", path) or files.get(path) != asset["sha256"]:
                issues.append(ReferenceError("inventory_mismatch", f"Saved asset inventory disagrees with registered files: {path}").issue)
            if saved["schema_version"] == 1 and not re.fullmatch(r"assets/[a-f0-9]+\.[a-z0-9]+", path):
                issues.append(ReferenceError("inventory_mismatch", f"Asset path does not match this historical version's policy: {path}").issue)
            provenance = asset["provenance"]
            if saved["schema_version"] == 2:
                representation = saved["asset_catalog"][asset["occurrence_id"]]["representation"]
                if (representation["id"] != asset["representation_id"] or representation["enriched_ref"] != asset["ref"] or
                    representation["enriched_sha256"] != asset["sha256"] or representation["asset_path"] != path or
                    representation["asset_uri"] != asset_uri(path) or representation["provenance_record"] != provenance):
                    issues.append(ReferenceError("inventory_mismatch", f"Occurrence representation and selected asset disagree: {path}").issue)
            declared = provenance.get("originals", []) if saved["schema_version"] == 1 else provenance["image"]["originals"]
            for original in declared:
                actual = originals.get(original["path"])
                if actual is None or original["path"] not in files:
                    issues.append(ReferenceError("missing_associated_original", f"Selected asset {path} is missing its declared original: {original['path']}", use).issue)
                    continue
                if saved["schema_version"] == 2:
                    # Separate extractions can cite one retained stream under distinct refs.
                    metadata = original.get("metadata")
                    same_stream = (original.get("sha256") == actual["sha256"] and isinstance(metadata, dict)
                                   and metadata == actual.get("provenance"))
                else:
                    same_stream = False
                    if original.get("sha256", actual["sha256"]) == actual["sha256"]:
                        same_stream = actual["ref"] == original["ref"] or (
                            original_record is not None and files[original["path"]] == actual["sha256"]
                            and _shared_schema1_original(original, actual, saved.get("source_ref", ""), original_record)
                        )
                if not same_stream or files[original["path"]] != actual["sha256"]:
                    issues.append(ReferenceError("inventory_mismatch", f"Associated original inventory disagrees for: {path}", use).issue)
        for path, original in originals.items():
            if files.get(path) != original["sha256"]:
                issues.append(ReferenceError("inventory_mismatch", f"Original inventory disagrees with registered files: {path}").issue)
        return {"status": "incomplete" if issues else "ok", "issues": issues}, analysis
    except Exception as exc:
        # Diagnostics must never hide the saved content or assert a false pass.
        # Byte-integrity errors occur in the caller, outside this boundary.
        return {"status": "unavailable", "issues": [ReferenceError("analysis_unavailable", f"Asset reference assessment is unavailable ({type(exc).__name__}).").issue]}, None


def display_mime(path: str, data: bytes) -> str:
    extension = path.rsplit(".", 1)[-1]
    if extension == "png" and data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if extension in {"jpg", "jpeg"} and data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    raise ValueError("Saved asset type is not a supported PNG/JPEG display image.")


def bind_preview(safe_html: str, bindings: dict[str, str], *, available=True, slots: list | None = None) -> str:
    """Rewrite parsed, already sanitized resource attributes; never source data URLs."""
    scan = ResourceHTML(safe_html)
    scan.feed(safe_html)
    edits = []
    class Binder(HTMLParser):
        def handle_startendtag(self, tag, attrs):
            self.handle_starttag(tag, attrs)

        def handle_starttag(self, tag, attrs):
            if tag not in {"a", "img"}:
                return
            raw = self.get_starttag_text()
            offset = scan.line_starts[self.getpos()[0] - 1] + self.getpos()[1]
            name = "src" if tag == "img" else "href"
            value = dict(attrs).get(name)
            kind, path = classify(value or "", "image" if tag == "img" else "hyperlink")
            if kind == "unrelated":
                return
            url = bindings.get(path) if available and kind == "asset" else None
            if tag == "img" and not url:
                label = dict(attrs).get("alt") or "Image"
                edits.append((offset, offset + len(raw), f'<span class="unavailable-image">{html.escape(label)} (image unavailable)</span>'))
            else:
                for attr, _, start, end in attributes(raw):
                    if attr == name and start is not None:
                        # Empty href cannot navigate out of the snapshot. Remove
                        # the whole target attribute below for unavailable links.
                        if url:
                            edits.append((offset + start, offset + end, html.escape(url, quote=True)))
                        else:
                            replacement = re.sub(r'\s+href="[^"]*"', '', raw, count=1)
                            edits.append((offset, offset + len(raw), replacement))
                        break
    binder = Binder(convert_charrefs=True)
    binder.feed(safe_html)
    parts, cursor, size = [], 0, 0
    bound_values = set(bindings.values())
    for start, end, value in sorted(edits):
        prefix = safe_html[cursor:start]
        parts.extend([prefix, value])
        size += len(prefix.encode('utf-16-le')) // 2
        if slots is not None and value in bound_values:
            # Offsets cross the Python/JS boundary as UTF-16 code units, unlike
            # canonical block SourceSpan offsets (Unicode code points).
            slots.append({"start": size,
                          "end": size + len(value.encode('utf-16-le')) // 2,
                          "expected": value, "key": value})
        size += len(value.encode('utf-16-le')) // 2
        cursor = end
    parts.append(safe_html[cursor:])
    return ''.join(parts)
