# R01CAL-A03-DELIVERY-01 portable asset-reference specification

[Adopted design](../../design/ASSET_REFERENCES.md) · [Discussion and investigation](../../discussions/ASSET_REFERENCES.md) · [Local tickets](tickets.md) · [Specification review](verification.md) · [Work selection](../../WORK_ITEMS.md#context-capability-and-delivery-work)

## Status and authority

**Specification identity AR-S4.4, primary-XMP enrichment and portable-link save increment, 2026-11-09 (Asia/Singapore).** The user approved the [scoped amendment](../../discussions/ASSET_REFERENCES.md#primary-xmp-and-portable-link-split-adopted), including the split into T3a and T3b and a new primary-XMP qualification ticket. This instruction authorizes documentation and tickets only. The [design](../../design/ASSET_REFERENCES.md#basis-for-this-revision) owns the effective contract and the [ticket plan](tickets.md#sequence-and-dependencies) owns prerequisites and execution state.

The [historical AR-S1 draft and amendments](20261108_1152_spec_AR_S1.md), [AR-S2 before technical-choice adoption](20261108_1536_spec_AR_S2.md), [AR-S3 before technical completion](20261108_1555_spec_AR_S3.md), [AR-S4 before production-release correction](20261108_1616_spec_AR_S4.md) and [AR-S4.1 before the applicability audit](20261108_1634_spec_AR_S4_1.md) preserve their original text and status. The [discussion decision](../../discussions/ASSET_REFERENCES.md#technical-choices-adopted-and-ampersand-locators) records adoption; [technical completion](../../discussions/ASSET_REFERENCES.md#schema-api-and-dependency-completion), [production-release reconsideration](../../discussions/ASSET_REFERENCES.md#official-production-release-reconsideration) and [dependency-audit rationale](../../discussions/ASSET_REFERENCES.md#official-release-audit-and-later-fix-applicability) retain the subsequent reasoning. Neither a prior proposal nor a historical observation overrides this revision. [Readiness](#readiness-and-continuation) links the remaining batch acceptance and execution boundaries.

The [captured AR-S4.3 before primary-XMP adoption](20261109_1648_spec_AR_S4_3.md) retains the earlier specification and its recursive coverage gate. The [design version list](../../design/ASSET_REFERENCES.md#design-versions) links the matching design and preceding editions. The scoped preview protocol and its existing [T2 acceptance](#t2-protocol-acceptance-checks) carry forward.

**Platform scope amendment, 2026-11-12.** The user limited the app to Windows for now. The [platform scope decision](../../decisions/REBUILD.md#windows-only-platform-scope-2026-11-12) defers the Ubuntu and macOS destination rows, so batch acceptance requires the Windows row only. The user then accepted Windows 10 build 19045 for that row in place of Windows 11. Commit `4b22a02` retains the preceding text of this spec and the design matrix.

**T5 verdict scope amendment, 2026-11-13.** The user [decided](../../discussions/ASSET_REFERENCES.md#t5-closing-route-selected) that a publisher-source JPEG with pre-existing competing source values or legacy XMP does not block T5 acceptance. If no such authorized source is exercised, the verdict records it as an AR-12 limitation. The controlled B-lite legacy and extended-packet evidence and the real-source StandardXMP merge stand in for that case. Every other AR-12 condition is unchanged. Commit `0b46f45` retains the preceding text.

This is a distinct delivery outcome from the completed A03 experiment. This spec owns batch outcome, boundaries and planned acceptance; the [design](../../design/ASSET_REFERENCES.md#design-basis-and-ownership) owns technical contracts and their rationale, [local tickets](tickets.md#planning-basis-and-authority) own decomposition/dependencies/progress, and [verification](verification.md#t1-windows-helper-qualification) owns observed review/checks. T1's bounded local qualification does not select the remaining application repair, original-task mutation, provider call, Start/Continue/replay, new importer, deletion, product packaging/installation, publication or subagent work. The [local ticket policy](../../../AGENTS.md#batch-documents-and-ticket-mode) remains in force.

## Outcome, basis and preserved guarantees

**Outcome:** an agent or user can reference a registered source image as a hyperlink or inline image, using a readable filename with a page locator. Each delivered image carries its established source information in embedded metadata and remains independently useful when copied alone. A new accepted save preserves consistent filenames, references, enriched image bytes and associated originals; actual reopen, in-app link use and relocated export retain that selected version. Missing dependencies, incomplete provenance or fidelity gaps are not hidden by a successful receipt or an agent's complete claim.

The [T3a portable-link increment](#t3a-portable-link-acceptance) addresses the original missing saved/exported hyperlink targets under existing hash paths. T3b adds readable names and standalone primary-XMP provenance in the enriched creation path. Diagnostic screenshots fail source-image publication in both increments. Full batch acceptance still covers one coherent enriched delivery chain.

The [original P2 finding](../R01CAL-A03/verification.md#r01cal-a03-delivery-01--linked-page-renders-are-absent-from-the-saved-version-and-zip) owns the real A03 failure. The [offline investigation](../../discussions/ASSET_REFERENCES.md#investigation-basis-and-observed-checks) establishes two separate implementation boundaries: image-only dependency collection during saving, and image-only binding in the app's saved preview. Its synthetic/API/browser controls are diagnostic evidence, not repaired desktop acceptance. Original A03 files and its verdict remain unchanged.

The [AR-S4.3 protocol evidence](verification.md#final-t2-protocol-evidence-and-scoped-assessment) identifies the tested application state and retained fixtures. The [original data-URL evidence](verification.md#ar-t2-01--large-image-data-url-navigation-blocks) retains its earlier transport and failure basis. Reconcile the actual working tree before dependent implementation, preserving inherited changes, original sources and the independent history of the original `pdf-to-md-agent` repository.

Read these governing sections, including their qualifications, when implementing the affected boundary:

- [Document schema, candidate retention, explicit base/head and commit/replay](../../design/DOCUMENT_MODEL.md#q1-document-schema-and-commit).
- [Referenced display assets, associated original streams and source provenance](../../design/PDF_EVIDENCE.md#pdf-coordinates-and-image-delivery).
- [Explicit-version export without inference and separate completion facts](../../design/RUNTIME_AND_DELIVERY.md#stop-task-completion-and-export).
- [Whole-document rendering and selected-version resource binding](../../guides/DOCUMENT_ENGINE.md#8-rendering-reading-and-precise-comparison), especially [saved content and preview resources](../../guides/DOCUMENT_ENGINE.md#preview-content-and-resource-boundary).
- [Code/test locations](../../guides/PROJECT_LAYOUT.md), [artifact retention and isolated tests](../../ARTIFACT_STORAGE.md#test-executions), and [Stage B's complete usable-delivery outcome](../../PHASE_PLAN.md#b-establish-complete-autonomous-conversion-on-actual-sources).

This adopted extension preserves those owners' guarantees. Raw source/candidate content, exact unmodified Markdown, full and precise access, agent method choice, task ownership, selected-version identity, immutable originals, useful failed work and no-inference export remain required. An explicit asset request may resolve input handles or correct operative reference spans in the new version, while preserving the received candidate and unrelated text. No compulsory image embed, generic attachment declaration, global catalogue or second mutable document body is introduced. Bounded acceptance does not close Stage B or establish general source fidelity, calibrated capacity or installed-product readiness.

## Adopted design contract

The technical rules now live in [the adopted asset design](../../design/ASSET_REFERENCES.md#design-basis-and-ownership), with their rationale and explicit implementation/acceptance boundaries. This spec owns the batch scope and acceptance; it does not keep a second editable copy of those contracts. Existing linked anchors below route historical readers to the same rule.

| Contract area | Substantive design owner |
| --- | --- |
| <a id="consolidated-discussion-agreement"></a>Consolidated discussion agreement | [Rule and rationale](../../design/ASSET_REFERENCES.md#consolidated-discussion-agreement) |
| <a id="readable-filenames-and-source-locators"></a>Readable filenames and source locators | [Rule and rationale](../../design/ASSET_REFERENCES.md#readable-filenames-and-source-locators) |
| <a id="punctuation-and-exceptional-filename-repairs"></a>Punctuation and exceptional filename repairs | [Rule and rationale](../../design/ASSET_REFERENCES.md#punctuation-and-exceptional-filename-repairs) |
| <a id="filename-byte-budget-and-meaning-preserving-shortening"></a>Filename byte budget and meaning-preserving shortening | [Rule and rationale](../../design/ASSET_REFERENCES.md#filename-byte-budget-and-meaning-preserving-shortening) |
| <a id="collision-only-allocation-and-identity"></a>Collision-only allocation and identity | [Rule and rationale](../../design/ASSET_REFERENCES.md#collision-only-allocation-and-identity) |
| <a id="standalone-embedded-provenance-and-faithful-image-bytes"></a>Standalone embedded provenance and faithful image bytes | [Rule and rationale](../../design/ASSET_REFERENCES.md#standalone-embedded-provenance-and-faithful-image-bytes) |
| Selected XMP mapping and embedding approach | [Rule and rationale](../../design/ASSET_REFERENCES.md#selected-xmp-mapping-and-embedding-approach) |
| <a id="synchronized-corrections-and-distinct-occurrences"></a>Synchronized corrections and distinct occurrences | [Rule and rationale](../../design/ASSET_REFERENCES.md#synchronized-corrections-and-distinct-occurrences) |
| Selected asset-change interface | [Rule and rationale](../../design/ASSET_REFERENCES.md#selected-asset-change-interface) |
| <a id="versioned-data-and-embedded-schema"></a>Versioned data and embedded schema | [Rule and rationale](../../design/ASSET_REFERENCES.md#versioned-data-and-embedded-schema) |
| Facts, pages and occurrences | [Rule and rationale](../../design/ASSET_REFERENCES.md#facts-pages-and-occurrences) |
| Saved envelope and representation records | [Rule and rationale](../../design/ASSET_REFERENCES.md#saved-envelope-and-representation-records) |
| Exact XMP namespace and serialization | [Rule and rationale](../../design/ASSET_REFERENCES.md#exact-xmp-namespace-and-serialization) |
| <a id="document-edit-api-and-operation-semantics"></a>Document-edit API and operation semantics | [Rule and rationale](../../design/ASSET_REFERENCES.md#document-edit-api-and-operation-semantics) |
| Responses and diagnostics | [Rule and rationale](../../design/ASSET_REFERENCES.md#responses-and-diagnostics) |
| <a id="reference-interpretation-and-destination-policy"></a>Reference interpretation and destination policy | [Rule and rationale](../../design/ASSET_REFERENCES.md#reference-interpretation-and-destination-policy) |
| Whole-document analysis | [Rule and rationale](../../design/ASSET_REFERENCES.md#whole-document-analysis) |
| Destination-span contract | [Rule and rationale](../../design/ASSET_REFERENCES.md#destination-span-contract) |
| <a id="supported-destinations"></a>Supported destinations | [Rule and rationale](../../design/ASSET_REFERENCES.md#supported-destinations) |
| Save and immutable dependency preparation | [Rule and rationale](../../design/ASSET_REFERENCES.md#save-and-immutable-dependency-preparation) |
| Saved-version assessment and diagnostics | [Rule and rationale](../../design/ASSET_REFERENCES.md#saved-version-assessment-and-diagnostics) |
| Preview binding and return behavior | [Rule and rationale](../../design/ASSET_REFERENCES.md#preview-binding-and-return-behavior) |
| Export and existing-version preservation | [Rule and rationale](../../design/ASSET_REFERENCES.md#export-and-existing-version-preservation) |
| Portable comparison and destination matrix | [Rule and rationale](../../design/ASSET_REFERENCES.md#portable-comparison-and-destination-matrix) |
| <a id="dependency-versions-and-helper-boundary"></a>Dependency versions and helper boundary | [Rule and rationale](../../design/ASSET_REFERENCES.md#dependency-versions-and-helper-boundary) |

## Implementation responsibilities and boundaries

| Component / owner | Responsibility in the selected target |
| --- | --- |
| `src/pdfmd/evidence.py`, task-owned asset storage and the applicable image-tool interfaces | Separate occurrence, original/display/enriched representation and readable path identities; naming/metadata preparation and durable collision reservation, preserving existing source-access capabilities. Reuse native service boundaries; no global catalogue. |
| `src/pdfmd/documents.py` and focused helpers where warranted | Shared whole-document reference interpretation/serialization, synchronized correction, final dependency validation/preparation and saved-version assessment. Preserve publication/replay/export semantics. |
| `src/pdfmd/server.py` | Supply the authenticated selected-version assessment, sanitized HTML and complete verified resource bytes/binding metadata to the trusted desktop host; attach export diagnostics without altering original receipt semantics. |
| `src/desktop/main.ts` and the existing preload/IPC boundary | Own the internal session protocol, verified transfer checks, snapshot resource table, lease activation/release and native request/frame guards. Keep renderer credentials and host filesystem paths out of resource URLs. |
| `src/renderer/features/documents/`, `src/renderer/main.tsx`, `src/renderer/types.ts`, `src/renderer/index.html` | Coordinate selection/load generation with host lease lifecycle, typed assessment/preview errors, cached snapshot Return and version-bound export feedback. Preserve source sanitization and the empty sandbox; apply only the adopted derived-view CSP permissions. |
| Existing tool descriptions / governing document owners | Describe supported canonical hyperlink/embed forms and useful validation feedback when the target is adopted. Preserve candidate and source-access guarantees. |
| `tests/engine/documents/` and `tests/desktop/` | Service/failure/identity checks and actual isolated desktop save/reopen/link/export checks. Reuse canonical fixture imports and existing source-image fixtures. |

The [dependency section](../../design/ASSET_REFERENCES.md#dependency-versions-and-helper-boundary) owns selected versions and integration gates. Selected parser/sanitizer/Electron source/type evidence is also at the [investigation owner](../../discussions/ASSET_REFERENCES.md#existing-dependency-support-and-destination-semantics). Before framework implementation, retrieve applicable current official guidance for those versions as required by AGENTS. Follow native lifecycle APIs; internal module/helper names may remain flexible without changing the wire and preservation contracts.

Future verification uses fresh short ignored run directories, synthetic sources/credentials, isolated Electron profiles and provider-denial controls. Preserve meaningful existing generated builds or select isolated build output before desktop checks. Necessary implementation validation, when authorized, may use a development build; it does not imply installation or release. No historical conversion allowance transfers to this work.

Excluded are original A03 repair/migration, new live conversion or replay, numerical calibration, route changes, agent-loop/compaction design, general arbitrary-link checking, non-image attachments, new importers/image formats/extraction, retry-policy redesign, broad security/resource isolation, global long-path configuration, release packaging/installation, deletion/retention redesign and cleanup. Future implementation includes the selected app-owned helper/resource integration; that is not release publication. Portable filename/path validation and metadata preservation for currently supported deliverables are in scope. These exclusions do not permit omitting the coordinated preview/export behavior or preserved failure guarantees specified here.

## Acceptance and evidence correspondence

AR-1 through AR-7 retain the investigation proposal's identities, with the selected representation/filename/serialization rules applied. AR-8 through AR-12 cover the subsequently agreed requirements. These are planned acceptance criteria; earlier diagnostics, arithmetic and document checks do not pass them. Actual observations and the combined verdict belong in [verification](verification.md). [T2 evidence](verification.md#t2-reference-and-selected-version-implementation) records its bounded runtime observations; integrated enriched-save and whole-batch acceptance remain open. Completion requires the integrated applicable conditions, not a scanner-only or metadata-only pass.

### AR-1 — Supported references and presentation

**Condition:** save canonical inline/reference-style hyperlinks, a cross-block definition, embeds, mixed use, supported HTML and a linked image against registered task assets; include entity-escaped attributes, code literals, comments, unrelated citations/footnotes and duplicate resource attributes.

**Expected and check:** accepted cases preserve exact block Markdown and source characters, link-versus-inline rendering and parser-resolved destinations. The saved dependency union contains each referenced file once. Non-reference text and unrelated links add no files. Duplicate resource attributes reject under the stated policy with the complete candidate retained; collection cannot silently choose a different target from rendering. Compare parsed roles, saved bytes and actual rendered output, not lexical link counts.

Include `p58&p61` and `p58&i67` filenames whose generated destinations contain `%26`, spaces/parentheses, Chinese basenames, entities and literal percent-looking text. Verify one decoding boundary, correct filename bytes, no query reinterpretation, no second decoding and no alternate-case/path lookup. Targeted correction must update operative spans/definitions while leaving identical text in code and unrelated prose unchanged.

### AR-2 — Rejection and candidate preservation

**Condition:** use missing, foreign-task-only, noncanonical and unsupported image destinations; include absent/corrupt registered asset bytes and representative reserved-path variants from the destination table.

**Expected and check:** reject before version publication/head advance, preserve prior work and the exact received candidate, identify the offending destination/role and supply usable guidance. Reuse the retained candidate in a new corrected request. Demonstrate no remote fetch, arbitrary host-file read or cross-task file adoption. A partial claim cannot bypass reference validation. Expected validation errors are distinguished from a broken test helper.

### AR-3 — Display and original dependency preservation

**Condition:** use a page render and relevant existing extracted-image fixtures with image/mask originals, multiple references and an unreferenced asset.

**Expected and check:** inspect saved JSON inventories, manifest and actual file bytes/hashes/provenance. Finalized enriched display assets and associated original streams are present with exact registered bytes; no unrelated image or source PDF is newly bundled. Compare pre-enrichment versus enriched picture data separately from their intentionally changed container/hash identities, including relevant color/alpha/orientation. Verify decoded pixels where relevant. This does not claim new decoder/figure-fidelity coverage beyond the fixtures used.

### AR-4 — Editing, identity and failed publication

**Condition:** add/remove references, make metadata-only edits and rebuild/reuse candidates; exercise stale head, replay after a later head, and representative preparation-write/transaction failure.

**Expected and check:** each new version uses its whole merged dependency set, while old versions retain their bytes. Removing the final reference changes only the new version's inventory. Failed operations do not publish or advance head; useful preparation/candidates remain. Replay returns the original receipt without rebinding to a newer document. Preserve existing publication and conflict regressions rather than replacing them with scanner-only tests.

### AR-5 — Actual desktop reopen and link use

**Condition:** in the normal desktop with isolated synthetic state, save a hyperlink-only result and a mixed result, close/relaunch, explicitly select each version and interact with native image links and Return. Include the preserved AR-T2-01 full-byte large PNG, small PNG/JPEG controls, repeated embeds, linked images and supported raw HTML anchors. Exercise both ordinary development-URL and built-renderer file-load contexts using the selected Electron version. No installer or installed-product claim follows. T2 uses preserved synthetic saved-version inventories; new-save checks belong to T3a and enriched creation/correction checks to T3b/T4, with T5 covering the integrated chain.

**Expected and check:** native links display the complete selected image in the existing empty-sandbox frame. Actual response bytes, decoding and selection identity agree with the verified saved inventory. Return restores its cached matching document without a new version read, head lookup, inference or save. Host/resource and UI checks must agree across lifecycle boundaries. Screenshots/native interaction supplement byte and identity assertions; synthetic-host/API-only checks, successful repeated embedding and a passing negative observation cannot satisfy native-link acceptance. `about:blank#blocked`, a truncated payload or an `unresolved: true` observation remains a failure of required delivery.

#### T2 protocol acceptance checks

These are adopted **planned checks**, with actual evidence recorded in verification against its tested code/spec identity. The [preview design](../../design/ASSET_REFERENCES.md#preview-binding-and-return-behavior) owns the mechanism; this table owns its condition/expected-result/violation correspondence.

| Guarantee | Conditions | Expected result and discriminating check |
| --- | --- | --- |
| Full bytes | Preserved AR-T2-01 large image, small PNG/JPEG, hyperlink-only/mixed, raw HTML links and repeated/linked-image references; controlled payload/length/hash or MIME mismatch and resource preparation failure. | Actual native clicks open the selected image. Capture the complete served body and compare length/SHA-256 to the immutable selected file, then check decoding/natural dimensions. URL length does not grow with payload; repeated references retain one coherent binding. No resampling, recompression, dropped bytes or quota workaround. Invalid transfer/preparation fails visibly without an active partial lease, source mutation or substituting another image. Do not rewrite the preserved failed data-URL run as a protocol pass. |
| Sandbox isolation | Empty sandbox in both shell-loading contexts; source script/custom/Blob/data/file URLs, parent access, external fetch/navigation, forged URL variants, unrelated frame/window/session, redirects, windows/downloads and revoked requests. | Only exact issued PNG/JPEG resources can load for the registered preview frame and active lease. Assert source sanitizer restrictions, opaque sandbox, restrictive CSP and host request/navigation checks; inspect denied requests as well as successful internal loads. Missing caller context, `null` origin or a scheme-prefix match cannot grant access. No sources execute, no parent DOM access or external requests occur, and no window/download is created. Failure to load internally cannot be repaired by adding sandbox permissions or CSP bypass. |
| Selected-version identity | Explicit old version after head advance; default-follow-head; task/version switch; pending/failed/late reads; same-version retry and out-of-order success/failure; editor entry; window/session destruction; missing historical target with a blob present elsewhere, unavailable assessment and corrupt file. | UI and host agree on job/version/load generation. A stale response cannot activate or revive a lease, frame, diagnosis, Return or export feedback, even for the same pair. Old/foreign tokens and unregistered assets fail at the request boundary; abandoned buffers/leases are released. Explicit old selection stays pinned; actual follow-head selection loads a fresh generation. Historical incomplete/unavailable/integrity cases retain their distinctions, raw access and no-fallback rules. Inspect late requests/completions as well as visible state. |
| Return to document | Native image view or blocked citation followed by Return; repeated Return; output-tab unmount/remount; relaunch/reopen; export while viewing an image after head advance. | Return remounts only the cached matching bound document, with its frame guard and usable images. Count version reads and inference/save requests: Return adds none; image reloads use the existing in-memory table. The lease survives decode/remount/tab changes while the snapshot is ready, and is released on the selection/edit/failure/destruction boundaries above. Relaunch creates new transient addresses from verified saved bytes. Exact export still uses the loaded version; no lease/address enters saved/exported files or receipts. |

T2 must establish this selected-version contribution independently of writer qualification, together with the applicable AR-1/AR-2/AR-6/AR-7 checks. T5 later establishes the integrated new-save chain and declared destination/platform acceptance. Keep no-provider controls and original-task preservation throughout future authorized execution; this amendment runs none of these checks.

### AR-6 — Exact export and relocation without inference

**Condition:** export the explicitly loaded version after head advances and with no inference allowance needed, then extract to a new declared short destination and open it in the declared external viewer. Exercise repeated export and an unrelated existing destination.

**Expected and check:** actual ZIP member names and every byte equal the immutable selected version, including originals and manifest. Relative links open and images decode after relocation; inspect Markdown destinations and rendered HTML as well as hashes. No request/attempt or conversion usage is added. Existing unrelated output is preserved. Separate source-image fidelity, package consistency and reference assessment; broader destination/filesystem support is not inferred. The actual saved/exported member comparison must also show that no preview protocol URL or lease was persisted and the authored relative asset destinations remain portable.

### AR-7 — Historical incomplete inventory and diagnosis

**Condition:** use a preserved synthetic fixture produced by the current hyperlink-only save behavior, with its target blob still present elsewhere in the task store. Also check a valid inventory, an unsupported historical resource reference, an assessment failure, and a separately corrupted registered-file control.

**Expected and check:** integrity-valid old content remains inspectable and exactly exportable; missing targets are diagnosed as incomplete and are not filled from the task store. The transient preview disables unbound targets and preserves labels/raw Markdown. The UI/export response distinguishes the original agent claim, reference diagnosis and package-byte verification. Diagnostic responses do not change version files or original receipts. Analysis failure reports unavailable instead of passing. Registered-file corruption continues to fail the existing integrity gate and cannot produce a verified ZIP. Original real A03 stores/packages remain untouched. Direct resource requests must not acquire a lease for a missing/unverified member or bypass the incomplete/unavailable/integrity result.

### T3a portable-link acceptance

Save actual new schema 1 documents with a registered local image hyperlink only and with mixed hyperlink/embed use, including repeated references and an extracted-image control with original streams. Use an isolated A03-shaped regression fixture with page-labelled render hyperlinks, ordinary section Markdown and a mixed variant with an inline image. Both saves must succeed through the shared resolver. Keep the Markdown and link/embed roles exact. Verify one dependency per referenced hash path, no unrelated files and exact display/original bytes and hashes.

Exercise missing or foreign targets, unresolved input handles, unsupported asset markup and an operative reference without an unambiguous source span. Each rejection must identify the offending reference or markup and explain what to correct. The exact candidate and prior head remain available. Use an already-registered diagnostic screenshot with the [existing producer marker](../../design/ASSET_REFERENCES.md#portable-link-save-increment). Referencing a diagnostic-only target must fail before publication. A valid source registration remains usable if it shares the same hash path.

Close and relaunch the desktop app, select the newly saved version, follow the image link, verify the complete image and Return. Export that version, compare its ZIP members and bytes with the saved version, and open the relative links after extracting to a different directory. Preserve the selected-version and no-inference guarantees. These checks can establish the P2 repair independently of enrichment. They do not complete the full destination matrix or the enriched creation, correction and standalone checks.

### AR-8 — Source-grounded naming and embedded standalone provenance

**Condition:** confirmed/incorrect bookmark hints, Roman/repeated/unknown/absent printed labels, multiple assets on one page, present/missing source figure labels, and long or conflicting uploaded/PDF titles. Include two sources with identical picture bytes and matching page/figure text.

**Expected and check:** inspect the actual source basis and final filenames: every current paginated-source asset has its correct `p`/`i` locator; source labels remain original-language; absent figure labels are omitted; no assumed offsets, mandatory title abbreviation or visible internal serial is introduced. Independently copy and rename only an exported image into an empty location. A non-app metadata reader recovers complete established title/citation, honest unknowns, physical/printed distinctions and occurrence/derivation facts without the source, app store, network, manifest or sidecar. Separate occurrences retain distinct provenance. No real source/task deletion is needed for this test.

Check continuous versus nonconsecutive ranges, mixed confirmed/unknown labels, compound literal labels and stable mixed-language style across UI-locale changes. The readable standard XMP and structured primary record must agree on the same complete source facts, with image title/creator distinguished from source book/article title/author. No implied printed-page offset or first-page-only fallback is accepted.

### AR-9 — Portable spelling, exact 180-byte limit and semantic shortening

**Condition:** Chinese/English and declared mixed-language examples; every substitution character; full-width slash; `A:B` versus `A：B`; case/canonical equivalents; reserved versus merely containing-reserved-word names; controls/trailing dots/spaces; fitting and overlong descriptions. Include 179/180/181-byte boundaries, supplementary/combining sequences, suffix growth, and an overlong full destination path with a valid basename.

**Expected and check:** measure UTF-8 bytes of the final basename including structured parts/suffix/extension. Fitting descriptions remain unchanged except required safety/style rules; all accepted names fit 180 bytes. Review shortened text against source meaning, especially negation, scope, direction, units and schematic status, independently of byte tests. Full descriptions retain their attribution in embedded metadata. Required-field overflow yields specific feedback, never silent truncation, locator loss or a sidecar. Final names retain safe full-width spelling/NFC without changing originals. Check actual save/reopen/extraction/relocation on the declared Windows destination; record untested filesystems/viewers explicitly. The Linux and macOS rows are deferred by the platform scope amendment above and remain unverified. Standards or a Windows run cannot establish non-Windows acceptance.

### AR-10 — Collision allocation, retries and distinct occurrences

**Condition:** unique names, unchanged reuse, differing pages/figures, distinct assets with the same complete portable name, occupied suffixes, shortening-created clashes and controlled concurrent allocation/retry. Include identical pictures from different real locations and removal of the final current reference.

**Expected and check:** only actual full-name conflicts receive the next available suffix; existing unrelated names/bytes/provenance never change or get overwritten. Suffix candidates remain within 180 bytes and are compared again after shortening. Durable reservations and replay return coherent identities across restart. Distinct occurrences do not merge citations; removal does not compact survivor suffixes or alter historical snapshots. Save/reopen/export retain the exact assigned path, binding and embedded facts.

Control the order so a suffixed save publishes while the unsuffixed reservation is pending, then the competing save fails. Reopen and export the published version, replay the operation and make a new eligible save. Check each result against the [published-name rule](../../design/ASSET_REFERENCES.md#collision-only-allocation-and-identity).

### AR-11 — Synchronized corrections and immutable history

**Condition:** correct page/figure/description facts for an occurrence used by multiple embeds, hyperlinks and cross-block definitions; correct a page shared by several assets; collide with an occupied corrected name; change only non-filename metadata; correct one of two genuine repeated occurrences. Exercise historical-base rebuild, stale head, interrupted/failed publication and accepted-operation replay after a newer head.

**Expected and check:** all affected operative references, current source facts, enriched representations and inventories become visible together in one new version. Unrelated text, code literals and independent occurrences remain unchanged. Non-filename corrections retain the path but update versioned embedded facts. Failures retain candidates/useful work and leave the prior visible state coherent. Rebuild/replay respect their explicit base/receipt. Actual reopen and export match the new selected version; earlier saved/exported snapshots keep their original names, metadata and bytes. No claim is made to update unknown external copies.

<a id="proposed-t4-completion-checks"></a>
#### T4 completion checks

Follow-up within AR-S4.4 and the existing [T4 scope](tickets.md#r01cal-a03-delivery-01-t4). Apply the adopted [edit API](../../design/ASSET_REFERENCES.md#document-edit-api-and-operation-semantics) and [correction contract](../../design/ASSET_REFERENCES.md#synchronized-corrections-and-distinct-occurrences) through the existing edit, preparation and publication path. The [T4-A selection](../../discussions/ASSET_REFERENCES.md#t4-a-selected) authorizes the shared source metadata case. The [T4-B selection](../../discussions/ASSET_REFERENCES.md#t4-b-selected) authorizes the multiple explicit corrections case. The [T4-C selection](../../discussions/ASSET_REFERENCES.md#t4-c-selected) authorizes the collision, history and recovery case.

| Case | Acceptance check |
| --- | --- |
| Shared source metadata | Correct a visibly evidenced PDF title via `source_update` on a schema 2 base containing a referenced occurrence and an unreferenced occurrence, with an assigned collision suffix on one. Both get fresh representations with stable occurrence IDs, paths and URIs. Independently read back the exact title in the structured record and readable XMP description, and the separate image title in `dc:title`. The new ZIP still includes only referenced assets and their originals. Linking the second occurrence later uses the already corrected bytes. An equivalent patch causes no representation churn. An invalid evidence pointer or preparation failure publishes no partial source correction. |
| Multiple explicit corrections | Correct two distinct occurrences in one edit, with a third occurrence of the same picture at another evidenced location left untouched. Both changes publish in one version. A duplicate correction for one occurrence rejects the whole edit, even if the first item would leave its facts unchanged. Combine explicit corrections with a shared page/source patch and check that each affected occurrence produces a single representation with all applicable facts. This covers [AR-T4-01](verification.md#ar-t4-01--one-correction-per-edit-is-stricter-than-one-per-occurrence). |
| Collision, history and recovery | Correct an occurrence toward an occupied filename and verify the next available valid suffix, both operative destinations and the existing owner's exact bytes. Rebuild from an older base with the current expected head and verify its historical mappings. Interrupt a pending correction and exercise restart, stale-head settlement and exact replay under the existing operation rules. Reopen and export the selected earlier and corrected versions and compare picture data, originals and embedded facts. These checks also exercise [AR-4](#ar-4--editing-identity-and-failed-publication), [AR-10](#ar-10--collision-allocation-retries-and-distinct-occurrences) and [AR-12](#ar-12--enrichment-fidelity-and-complete-delivery-chain). |

The [follow-up tickets](tickets.md#t4-follow-up-tickets) carry the work and dependencies. The existing [T5](tickets.md#r01cal-a03-delivery-01-t5) owns combined delivery acceptance. See the [discussion](../../discussions/ASSET_REFERENCES.md#review-and-proposed-t4-completion) for scope choices still open.

### AR-12 — Enrichment fidelity and complete delivery chain

**Condition:** use the relevant supported PNG/JPEG and existing image/mask/color/rotation fixtures, an embedding failure, longer/repeated images, an isolated copied file, and a deliberately metadata-stripping external transformation as a limitation control.

**Expected and check:** compare original evidence/pre-enrichment image to enriched picture data, encoded payload where applicable, dimensions, color/profile, bit depth, alpha and orientation. Only the declared container metadata representation changes; retained originals remain byte-exact. No lossy recompression, silent downgrade or missing-provenance success is accepted. Then inspect **one identified saved version through actual close/reopen, image-link/return, export, extraction and relocation**, checking names, working Markdown/HTML references, complete independently readable metadata, registered bytes and originals throughout. Export adds no inference/usage or new naming/enrichment. A third-party stripping result demonstrates the stated limitation, not ordinary-copy failure. Report content fidelity, app behavior, metadata interoperability, package integrity and platform coverage separately before the combined verdict.

#### Primary-XMP qualification controls

Use the [eligibility, mutation and validation rules](../../design/ASSET_REFERENCES.md#primary-xmp-enrichment-boundary). Show that the exact candidate passes the following checks before enriched integration:

| Condition | Expected observation |
| --- | --- |
| Verified MuPDF-generated PNG, including render and decoded extract | Exactly one added uncompressed primary XMP `iTXt` with a valid CRC. All original chunks, including encoder metadata and `IDAT`, match byte-for-byte. Wrong file type, unexpected XMP or `caBX` rejects before writing. |
| Unchanged PDF DCT JPEG without primary XMP, and JPEG with valid existing primary XMP | Creation produces one primary record. Merge updates only allowed source fields and necessary framing. Compare all other primary properties semantically, including custom namespaces, comments/CDATA content where relevant, ordered and language-valued properties and thumbnails. Compare unrelated APP1/APP2/APP11/APP13, encoded scans, structural markers and trailers byte-for-byte. Include AR-SDK-01 IPTC and AR-SDK-02 thumbnail controls. |
| Long record and existing ExtendedXMP | Exercise creation and merge, Unicode split across fragments and valid reordered fragments. Verify fragment lengths, offsets, coverage and GUID/digest. A missing, overlapping, truncated or conflicting fragment, malformed primary XML or competing primary packet must fail at its applicable guard. Independently corrupt a staged output and verify the postcheck prevents acceptance. |
| JPEG APP11 `brob` and position-dependent metadata | Preserve every opaque APP11 segment byte-for-byte, with no nested decoding prerequisite. Signature and asset binding are unverified. An MPF-bearing JPEG rejects before writing. Failure to preserve applicable known references also blocks enrichment. |
| Legacy JPEG XMP (B-lite) | APP13 `0x0424` and EXIF IFD0 `0x02BC` values, in both TIFF byte orders and alone or with an existing primary record, become same-length empty packets. Bytes outside those values stay identical, IPTC stays readable, and no reader document of the delivered image carries a legacy value. Too-short, malformed, split-IRB and wrong-type carriers reject before writing. A corrupted blanked value in a staged output fails the postcheck. |
| Isolated independent readback and failure | Copy and rename only the prepared image in an empty directory. A separate offline reader recovers the complete structured source record and matching standard fields, including the full long mixed-language record. Truncation, a competing or stale record selected by the reader, resource-limit failure or any disallowed change fails qualification. A failed check leaves the prior version, PDF, pre-enrichment image and retained originals intact. |

Retain a source-backed eligibility check, bounded preparation, controlled literal working paths and the existing filename/transport safety controls. Include original-filename tags with directory components and visible names containing `%`. Outer byte preservation and primary validation replace recursive inventory as this path's gate. Earlier foreign PNG/recursive carrier and Brotli findings retain their scope in [verification](verification.md#t1-f05-packet-coverage-source-gate).

## Readiness and continuation

AR-S4.4 separates [T3a](tickets.md#r01cal-a03-delivery-01-t3a) from [T3b](tickets.md#r01cal-a03-delivery-01-t3b). The former needs the shared T2 reference and preview path. Enriched integration needs a positively qualified exact writer and reader plus explicit product selection. Follow [T1-F06](tickets.md#t1-f06-primary-xmp-writer-and-independent-reader-qualification) for that handoff. The preserved [AR-S4.3 spec](20261109_1648_spec_AR_S4_3.md#readiness-and-continuation) records the earlier decisions, dependency limits and pre-amendment gates. The naming, wire-interface, fidelity, no-companion and immutable history guarantees still govern the enriched outcome.

**Continuation:** follow the [formal ticket sequence](tickets.md#sequence-and-dependencies) for the T2 handoff, independent link repair and writer gate, and the [current focus](../../CURRENT_STATE.md#focus-and-resume-route) for activity and authority. The [acceptance criteria above](#acceptance-and-evidence-correspondence) guide [T5's integrated verification](tickets.md#r01cal-a03-delivery-01-t5).
