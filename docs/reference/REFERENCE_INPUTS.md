# Historical reference inputs and known limits

This note preserves five reference packages from the earlier project. Their recorded conditions and defects are historical observations. They are not validation results for the rebuilt app.

On 2026-10-23, the user authorized copying all five packages into local `references/` and the credential/configuration into local `private/`. The copy preserved source bytes and verified all 46 manifest entries; the manifest itself makes 47 reference files. All five PDFs contain real PDF bytes. These directories are Git-ignored and are not bundled in the public repository. The package IDs below identify the inputs; the locally bundled discussion sources preserve their development lessons.

<a id="package-identities"></a>
## Package identities

| Package ID | Supplied source | Physical pages | Linked example images | Recorded input condition |
| --- | --- | --- | --- | --- |
| `jre` | JRE Joint Recruitment Examination Practical Guide, second edition, excerpt | 14 | 1 JPEG | Image-only. No page had extractable text. |
| `gynecology` | Comprehensive Gynecology, Gershenson et al., eighth edition, excerpt | 21 | 16 PNGs | Existing text after user-applied Adobe OCR. |
| `nursing` | Maternal & Child Nursing Care, London et al., fifth edition, excerpt | 14 | 16 PNGs | Existing text after user-applied Adobe OCR. |
| `jre-full` | JRE Joint Recruitment Examination Practical Guide, second edition, complete supplied PDF | 173 | 0 | Image-only. No page had extractable characters. |
| `news-writing` | News Writing: Theory, Methods and Techniques, complete supplied PDF | 290 | 0 | Every page had extractable characters. This did not certify OCR accuracy. |

These counts describe physical positions in the supplied PDFs. They do not establish printed page labels or the completeness of a published book. The linked-image counts describe the supplied Markdown examples, not the source PDFs' graphics.

The original manifest identifies five PDFs, five Markdown examples, 33 images and three guidance pointers. File identity and package integrity do not certify content. The local copy receipt is `.local/reference-copy-report.json`. A converter receives only the chosen source PDF and task scope; reference-output answers are available to reviewers, not injected into the conversion.

Historical inventory and limits: [SUP-03](sources/support/SUP-03.txt). The original handoff names all five packages and distinguishes their role from app capability: [EVT-0001](sources/text/EVT-0001.txt).

<a id="jre-identity-and-source-spelling"></a>
## JRE identity and source spelling

The 14-page excerpt and the 173-page supplied PDF are separate inputs. The full filename includes `173无1-2`. That name does not prove that every published page is present. The supplied filename uses GRE, while the example Markdown title uses JRE. Preserve these identity facts when matching inputs. Read printed labels from the source instead of assuming an offset.

The full example claims that embedded OCR was used. The recorded PDF inspection found no extractable characters on any of its 173 pages. The example's claim remains supplied data, not established source provenance. Its content, tiny graphics and page-marker completeness were not independently recertified.

A recorded source correction concerns `勞工福利部部長` on physical page 18, printed page `019`. Two consecutive `部` glyphs cross the line boundary. The earlier duplication allegation and its OCR-cause inference were withdrawn. This correction concerns that source detail. Preserve the source spelling instead of removing a glyph because it looks redundant.

Sources: [SUP-03](sources/support/SUP-03.txt) for the JRE identities, [SUP-07](sources/support/SUP-07.txt) for the correction, and [ATT-07](sources/attachments/ATT-07.txt) for the spelling and printed label.

<a id="reference-image-and-ocr-caveats"></a>
## Reference image and OCR caveats

The JRE excerpt's cover image is a rendered derivative with added lossy JPEG encoding. It does not meet the current no-added-lossy requirement. Its tiny illustration lettering and every transcribed character were not independently certified. The example's language-loading warnings did not establish successful loading of every requested OCR language.

The Gynecology example's `figure-1-06.png` contains a white-painted region. It does not meet the current unchanged-source-graphic requirement. Its PNG figures are rendered crops. They do not prove byte-preserving extraction of embedded image streams or native-resolution preservation.

The Nursing example's figures include crops from 140-DPI page renders. A lossless file format alone does not establish native resolution or sufficient detail. The example also includes optional opening decoration and a sentence that continues beyond the excerpt. Preserve the requested scope without inventing that continuation.

Both medical PDFs had user-confirmed Adobe OCR preprocessing. Their examples cannot alone establish this app's handling of an untreated scanned input. Preprocessing is not a required user step.

A separate Nursing observation concerns physical page 12. Its 446 spans all reported `GlyphLessFont`, flags 12 and alpha 0. These uniform attributes could not distinguish visible emphasis. This is a scoped observation, not a claim about every page of both medical PDFs. Font name and transparency alone do not establish OCR provenance.

Sources: [SUP-03](sources/support/SUP-03.txt), [ATT-07](sources/attachments/ATT-07.txt), [ATT-10](sources/attachments/ATT-10.txt), [EVT-0479](sources/text/EVT-0479.txt). The [layout explanation](../design/CONTEXT_AND_EVIDENCE.md#layout-and-visual-evidence) separates reported attributes, derived hints and source pixels.

<a id="full-source-example-limits"></a>
## Full-source example limits

The full JRE and News Writing Markdown examples have no linked images or separate artwork. They therefore do not establish image coverage or compliance. Reaching late-book sections or including page comments does not certify complete content coverage.

News Writing's example claims dual-OCR comparison and page verification. Those claims remain unverified self-reports. Extractable text on all 290 pages does not certify its accuracy or the example's transcription.

Source: [SUP-03](sources/support/SUP-03.txt).

<a id="use-with-current-requirements"></a>
## Use with current requirements

Source PDFs and [product requirements](../PRODUCT_REQUIREMENTS.md#images-and-source-coordinates) govern fidelity. The supplied examples are useful reading references, not certified answers or a quality ceiling. Existing source JPEG encoding is valid. Added lossy recompression and painted-over source content are different cases.

Reviewers may consult examples. A formal comparison converter must not receive a matching-range reference answer, developer transcription or another arm's output. Select a useful source-led scope when the user authorizes a conversion or comparison.

This inventory creates no mandatory benchmark matrix or whole-book threshold. It carries no old runtime defaults, acceptance results or closed-job permissions into the rebuild. The reference conditions above do not require rerunning old work.

Sources: [EVT-0001](sources/text/EVT-0001.txt), [SUP-01](sources/support/SUP-01.txt), [SUP-03](sources/support/SUP-03.txt). See the current [acceptance and cost requirements](../PRODUCT_REQUIREMENTS.md#acceptance-and-cost).
