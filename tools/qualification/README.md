# Windows metadata-helper qualification

This acceptance-only harness answers R01CAL-A03-DELIVERY-01-T1. It does not integrate a writer into the app, change dependency manifests, publish a document or use a provider. [The verification owner](../../docs/batches/R01CAL-A03-DELIVERY-01/verification.md#t1-windows-helper-qualification) records acquired identities, observations and the dependency disposition. [The design](../../docs/design/ASSET_REFERENCES.md#dependency-versions-and-helper-boundary) owns the required preservation and invocation rules.

Use isolated ignored directories. Acquire the exact Windows ExifTool 13.55 distribution and Adobe SDK commit `581c41213ddcee1fbc72cbb532531102a6617a25` from the URLs/hashes in verification. Preserve the Windows distribution's `exiftool_files` beside a copy of `exiftool(-k).exe` named `exiftool.exe`; the ordinary launcher must not pause for a key. No system Perl is used. Populate the isolated SDK's `third-party/expat/lib` from Expat `R_2_5_0` and `third-party/zlib` with the `.c`/`.h` files from zlib `v1.2.13`, as required by that SDK's own ReadMe files. These are reader-build inputs, not new application dependencies. Preserve their licenses.

For the separately selected [comparative follow-up](../../docs/batches/R01CAL-A03-DELIVERY-01/tickets.md#t1-comparative-follow-up), use the exact 13.61 test artifact and verified baseline/reader identities from [its evidence](../../docs/batches/R01CAL-A03-DELIVERY-01/verification.md#t1-comparative-execution-1355-and-1361). Use new directories and verified runtime copies; preserve the original evidence root unchanged. Version selection comes from that scoped instruction, not an automatic latest-version lookup or product dependency update.

Use an existing compatible Visual Studio 2022 x64 C++ toolchain and CMake. The wrapper delegates library compilation to Adobe's CMake projects, with the supported dynamic configuration. It does not patch SDK sources. For example, after selecting absolute paths:

```powershell
& $QualificationCMake -S tools/qualification -B $QualificationBuild -G 'Visual Studio 17 2022' -A x64 "-DXMP_SDK_ROOT=$QualificationSDK"
& $QualificationCMake --build $QualificationBuild --config Release --target xmp_read --parallel 2
.venv/Scripts/python.exe tools/qualification/qualify_metadata.py --writer $QualificationWriter --reader "$QualificationBuild/Release/xmp_read.exe" --run $QualificationFreshRun
```

`--run` must be new. The harness uses the existing pinned PyMuPDF decoder and canonical `pdfmd.evidence`/`pdfmd.storage` imports. It generates a synthetic isolated store from the seven repository PDF fixtures, plus exact PNG/JPEG/XMP/EXIF controls. All source/preparation bytes, expected records, structured transport files and complete stdout/stderr/argument vectors remain in that run. It deliberately runs failed preparations to inspect their effects; none becomes a saved application version. Private transport/config files are not image companions or required by the independent reader.

The writer uses an explicit first `-config`, UTF-8 settings, a fixed tag allowlist and an absolute opaque preparation path following `--`. Full values travel through the documented UTF-8 CSV importer. `--transport json` reproduces the rejected JSON-import control; it is not an accepted alternative. `--case NAME` selects a focused rerun without changing fixture semantics. Run identity and harness hashes distinguish earlier evidence after harness changes.

Each invocation runs below a Windows Job established before the helper starts: 256 MiB total job memory, five seconds of job CPU time, kill-on-close and a parent 15-second wall deadline. This is bounded test containment, not an application sandbox or a universal resource guarantee. The worker removes unsupported `C.UTF-8` locale variables only from its child environment. It makes no persistent setting change. No attack payload or large allocation bomb is generated.

`xmp_read.cpp` uses read-only Adobe `SXMPFiles` smart handlers and `SXMPIterator` leaf access. It receives only an image path; an empty standalone directory contains the copied/renamed image. It needs its compiled reader/runtime libraries, but no ExifTool config, database, source PDF or record file. The parent uses standard JSON decoding to compare every structured fact and expected standard property. Before/after unrelated XMP leaves are compared separately; passing the new record alone is insufficient.

PNG checks compare every non-XMP chunk payload, including ICC, EXIF, `caBX`, palette/transparency, bit depth, gamma and IDAT. JPEG checks compare every non-XMP marker payload, tables/frame data and the complete scan through EOI. The same pinned decoder additionally compares dimensions, color/alpha and decoded samples. The extended-JPEG control checks fragment GUIDs and full recovery, then removes extension segments from a separate copy to demonstrate that reader-open success can still omit required fields. A separate stripping control demonstrates loss of provenance under an external transformation.

The report records observations, including negative controls; its process exit code does not mean qualification passed. Inspect `qualified_case`, diagnostics, unrelated-metadata equality and the complete report against T1's gate. The harness does not claim save atomicity, real source semantic acceptance, every malformed/resource case, Windows 11 or the remaining T5 platform matrix. A reproduced valid-input preservation failure is a dependency decision, not permission to weaken the checks.

`qualified_case` is deliberately unset for malformed/count probes and the type-mismatch control; it does not turn their observations into accepted preparation. The smart-handler reader is not a strict packet validator and may open a file while omitting a property. Review the raw malformed-input observations, expected negative controls and the governing rejection requirement separately. This harness contains no strict pre-publication XMP validity guard. Refer to the verification owner for its consequences; a valid-input count alone is not the complete qualification disposition.

## AR-Q4 stage-one coverage probe

`probe_xmp_coverage.py` is an exploratory outer-container inventory and parser-identity utility. It is not a complete raw-XMP extractor or strict validator. Every inventory result explicitly sets `complete_packet_coverage` and `accepted_preparation` to false. It distinguishes located outer packets, outer-only absence, ambiguous packets, malformed containers and unavailable coverage. It does not infer XML validity from bytes or field output. [The bounded AR-Q4 execution](../../docs/batches/R01CAL-A03-DELIVERY-01/verification.md#ar-q4-bounded-execution-and-packet-coverage-stop) owns actual observations, source paths, hashes and its stopping point.

Run it only as a child of the existing bounded Job worker, using a new ignored run root and verified copies of the exact scoped helper/reader. Inventory, decompression if later selected, XML validation if later selected, and native processes must all be inside the pre-start bounds. Do not invoke this utility directly on untrusted inputs outside that boundary. For a reproduction, set `project`, `run`, `writer`, `reader` and `inputs_json` to explicit absolute `Path` values. `inputs_json` is a UTF-8 JSON array of absolute image paths, all copied into the fresh evidence root beforehand. Using the existing Python environment, the parent orchestration is:

```python
import sys
sys.path.insert(0, str(project / "tools/qualification"))
from qualify_metadata import Runner

run.mkdir(parents=True, exist_ok=False)
runner = Runner(run, writer, reader)
probe = str(project / "tools/qualification/probe_xmp_coverage.py")
runner.call("parser-identity", [sys.executable, "-B", probe, "--identity"])
runner.call("outer-inventory", [sys.executable, "-B", probe,
                                "--inputs", str(inputs_json)])
```

The parent captures complete command arguments/stdout/stderr/process metrics, with a 15-second deadline around each pre-start 256 MiB/five-second Job. The probe bounds every inspected PNG chunk or pre-scan JPEG segment against actual remaining bytes before taking a span. PNG CRCs and iTXt fields are checked, without stripping a wrapper or searching for an XML closing tag. Compressed/legacy/nested metadata and opaque JPEG scan/trailer regions are explicitly unavailable; ExtendedXMP fragments are not decoded or treated as separate XML documents. Do not present this limited utility as the agreed complete locator or promote unavailable to absent/malformed/accepted.

`--identity` records Python/runtime/build, linked Expat version/features and binding hash. Its default parser construction is for identity inspection only: it parses no XML, selects no qualified namespace-aware/DTD/entity policy and makes no security claim. The installed Python and reader's bundled parser are independent identities. No package installation, automatic upgrade or runtime modification is needed.

The source-led nested witnesses can be reconstructed independently of a prior local run. Use `qualify_metadata`'s existing `png`, `xmp`, `chunk`, `jpeg_segment` and `with_xmp` constructors, and its unchanged JPEG base `pymupdf.Pixmap(pymupdf.csRGB, 3, 2, bytes([10, 80, 210] * 6), False).tobytes("jpeg")`. Construct the logical packet as `xmp("<xmp:Label>PLACEHOLDER</xmp:Label>")`, replacing `PLACEHOLDER` bytes with either `b"Nested exact original"` or `bytes.fromhex("c080f5808080")`. Preserve both exact serializations before embedding.

For TIFF, concatenate `b"II\x2a\0\x08\0\0\0"`, `struct.pack("<H", 1)`, `struct.pack("<HHII", 0x2bc, 1, len(packet), 26)`, four zero bytes and `packet`. The single IFD entry points at the original packet at TIFF offset 26. Insert it as PNG `eXIf` immediately after the 33-byte signature/IHDR region, or as JPEG APP1 `b"Exif\0\0" + tiff` immediately after SOI. These are generated known-offset witnesses, not an arbitrary TIFF extractor.

For Photoshop, build an IRB from `b"8BIM"`, big-endian resource id `0x0424`, two zero bytes for the empty padded Pascal name, a big-endian four-byte packet length, `packet`, and one zero padding byte if that length is odd. Insert JPEG APP13 containing `b"Photoshop 3.0\0" + irb` after SOI. For encoded nesting, put `base64.b64encode(packet).decode("ascii")` in `<ast:XMLPackets xmlns:ast="http://ns.nikon.com/asteroid/1.0/">...</ast:XMLPackets>`, wrap that body with `xmp`, and embed the outer serialization with `with_xmp` in the base PNG. The source span here identifies the original base64 spelling; its associated logical packet is a separate identity.

Read witnesses only through the exact selected full-readback vector and independent reader. Record generator-known physical spans, logical packet hashes and field observations separately. A raw `-b -XMP` read can expose an exact packet in one carrier yet return only the outer serialization for another. ExifTool's namespace/table dispatch can decode and recurse into embedded binary XMP; a perfect check of only the outer XML does not establish complete coverage. Consult the linked source/evidence owner before attempting a new extractor scope or excluding a path. The probe does not start a writer or continue later qualification stages automatically.

## AR-Q4-C1 source-closure route witness

`study_xmp_source_closure.py` reproduces the stage-one source-route question with a verified copied ExifTool 13.61 runtime. It is a constructor for four known-offset controls and fixed read-only commands, not an observer, arbitrary-input extractor, complete inventory or strict guard. [The study evidence](../../docs/batches/R01CAL-A03-DELIVERY-01/verification.md#ar-q4-c1-coverage-study-source-closure-stop) owns the actual stop, source locations, identities and compatibility limits. No native metadata writer, image preparation or Adobe-reader call occurs in this tool.

Use a fresh ignored run root containing verified `baseline/` and `reader/` copies, the earlier exact `inputs/png-alpha.png`, `jpeg-basic.jpg` and `logical-valid.xmp`, `frozen-identities.json`, and unchanged `prior-call-reference/pdfmd.config`. Preserve the old roots and entry/executed harness editions. From a parent driver using the existing Python environment, create `execution` freshly, construct `Runner(execution, run / 'baseline/exiftool.exe', run / 'reader/xmp_read.exe')`, then call:

```python
status, stdout, stderr = runner.call(
    'source-closure-witness',
    [sys.executable, '-B', str(project / 'tools/qualification/study_xmp_source_closure.py'),
     '--inside-job', str(run)])
```

Do not launch `--inside-job` directly outside the existing Job worker. Construction, native raw codec calls, all eight image reads, expected inventories and provenance hashing share **one** pre-start 256 MiB/five-second Job and 15-second parent wall boundary. The tool accepts no native option vector from source values. It fixes the unchanged first config/charset prefix, the original full-readback selection and supplemental `-v3` reads; neither performs metadata assignment/import. An existing raw Brotli codec compresses a fixed 256-byte constructor-known packet and independently decodes it with a fixed 1,024-byte output bound. Raw compression is recorded separately from metadata-writer invocations; it is not an accepted image write.

Each PNG `caBX` / JPEG APP11 control contains a constructed JUMBF superbox with either raw UUID-XMP or `brob` XML. The expected packet/source/occurrence spans come from construction, with distinct occurrences even when logical hashes match. The tool saves complete per-command arguments/stdout/stderr/exits, original logical/encoded bytes and expected manifests. A successful child process means only that this probe finished. All fixture records keep `complete_packet_coverage` and `accepted_preparation` false. Known decode equality does not qualify arbitrary-stream full consumption or the normative status of every constructed box arrangement.

Inspect actual source/buffer conditions before interpreting outputs. `ProcessJpeg2000Box` can pass a shared parent `DataPt` plus child `DirStart`/`DirLen`; `ProcessBrotli` reads offset zero. Capturing after that function's early return cannot invent a decoded child inventory. The fixed full-readback's group filter may also omit a JUMBF property that verbose traversal actually parses. These are separate reasons not to infer absence from field output. A skipped/ambiguous carrier remains unavailable pending its justified route/compatibility evidence. No observer instrumentation or negative-trace matrix is implied by this reproduction tool, and it never resumes strict validation or writer/integration work automatically.


## T1-F06 primary-XMP candidate

`primary_xmp.py` is the qualification candidate for the [primary-XMP enrichment boundary](../../docs/design/ASSET_REFERENCES.md#primary-xmp-enrichment-boundary). It is a self-contained Python splicer, with no third-party dependency, and is not application code. `prepare --input --output --values --report` performs the following steps, in order:

1. Parse the container with bounds and CRC checks.
2. Apply the eligibility profile:
   - A PNG input must contain no XMP-keyword text chunk, `caBX`, `tXMP`, `eXIf` or `zXIf`.
   - A JPEG input is rejected if it has MPF or a competing StandardXMP.
   - B-lite (2026-11-10): a legacy XMP value in Photoshop APP13 0x0424 or EXIF IFD0 0x02BC (BYTE or UNDEFINED type, either byte order) is strictly parsed, then overwritten in place by an empty XMP packet of the same byte length, padded with spaces. Nothing is resized or moved, so IRB sizes, other resources, IFD entries and offsets remain valid. The value is rejected instead when it is shorter than the empty packet (`legacy_xmp_too_short`), is not valid XMP (`legacy_malformed`), or sits in an unparseable or split IRB block or has another TIFF type (`legacy_unparseable`).
3. Validate the primary XMP strictly:
   - strict UTF-8;
   - Expat with namespaces;
   - DOCTYPE and entity declarations rejected, with no external resolution;
   - `x:xmpmeta`/`rdf:RDF`/`rdf:Description` structure only;
   - no duplicate properties and a consistent `rdf:about`.
4. Reconstruct ExtendedXMP by offset. The fragments must have one GUID and one full length, cover the data exactly with no overlap, and match the uppercase MD5 GUID.
5. Merge the records. The allowlisted `dc:title`, `dc:description`, `dc:source` and `pdfmd:*` properties are replaced. Every other top-level property is kept. Preserved properties are reserialized with the same names, attributes and values. Comments are dropped and CDATA becomes escaped text, because neither is part of the XMP data model.
6. Write the record:
   - PNG: one uncompressed `iTXt` before the first `IDAT`.
   - JPEG: the StandardXMP APP1 is replaced in place, or inserted after the leading APP0/EXIF segments. ExtendedXMP segments are added when the packet exceeds 65,000 bytes. `pdfmd:RecordJSON` moves first, then the largest property.
7. Reopen the output and repeat every check. The postcheck re-blanks the input independently, requires every changed byte to lie inside a legacy value range and every output legacy value to equal the empty packet. All other non-primary byte ranges must be equal and in order, the preserved-property models must match, and the allowlisted values must equal the expected ones. Only then is the output published, via a verified stage and `os.replace`.

Exit 0 means accepted; exit 2 means rejected, with the stage and code in the report and no output file. `--inject` adds a post-splice defect for postcheck controls only.

`qualify_primary_xmp.py --reader <ExifTool 13.55 exiftool.exe> [--cross-reader <13.61>] --run <new dir>` builds every control in the [primary-XMP qualification table](../../docs/batches/R01CAL-A03-DELIVERY-01/spec.md#primary-xmp-qualification-controls). Fixtures come from the existing PDF fixtures through `pdfmd.evidence`, plus constructed APP11/APP13/EXIF/MPF/ExtendedXMP inputs. Each preparation and each reader call runs through `qualify_metadata.Runner`, which applies the same pre-start Job limits. The reader is a verified copy of the production ExifTool 13.55, run with `-config ""` so no config is loaded. Its fixed read vector travels in a UTF-8 `-@` argument file, because Windows command lines cannot carry the renamed Chinese path. The image is copied and renamed into an empty folder before it is read.

The harness checks results independently of the candidate's own postcheck:
- container order and bytes, via the `qualify_metadata` parsers;
- decoded pixels, via PyMuPDF;
- standalone values from the reader, using `-b` so long values come back in full;
- unrelated reader values before and after, with only inherited diagnostics allowed.

The 13.61 cross-read is supplementary and is not an acceptance input. [The verification owner](../../docs/batches/R01CAL-A03-DELIVERY-01/verification.md#t1-f06-primary-xmp-qualification) records the run.
## T3b integrated readback check

`check_enriched_readback.py --reader <ExifTool 13.55 exiftool.exe> [--cross-reader <13.61>] --run <new dir>` exercises the application, not the candidate alone. It creates a task from `tests/fixtures/pdf/rgb-jpeg.pdf` in a fresh workspace under the run folder. It then saves one enriched schema 2 version through the normal `edit_document` path, with a MuPDF render PNG and the unchanged DCT JPEG with a long mixed-language description, and exports and extracts the ZIP elsewhere.

Each delivered image is copied alone, under a new name, into an empty folder. It is read with the same fixed vector, argfile and Job limits as `qualify_primary_xmp.py`. The check requires:
- reader exit 0 with no warnings;
- `RecordJSON` equal to the saved provenance record;
- `dc:title`, `dc:source` and `pdfmd:OccurrenceId` equal to their expected values;
- the citation present in `dc:description`;
- byte equality after relocation;
- exactly one XMP document (`XMP-pdfmd:Main:RecordJSON` under `-a -G1:3`).

The optional 13.61 read is a cross-check only. Results are in `<run>/report.json`; the [T3b evidence](../../docs/batches/R01CAL-A03-DELIVERY-01/verification.md#t3b-first-increment-enriched-creation) records the run used.

## T3b writer budget measurement

`measure_writer_budget.py --run <new dir>` measures the bounded XMP worker against encoded input size: peak Job memory, charged user and kernel CPU, and wall time. It uses a 4 GiB measurement ceiling and covers seeded-noise MuPDF PNGs of about 11, 53 and 103 MiB and a DCT JPEG with a DOM-heavy ~15 MiB ExtendedXMP. It then runs one complete `edit_document` save of the ~103 MiB PNG in a fresh process and reports that process's peak commit. Windows only; no provider call. The [lifecycle and budget evidence](../../docs/batches/R01CAL-A03-DELIVERY-01/verification.md#t3b-writer-lifecycle-and-budget-correction) records the run used.
