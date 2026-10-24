# Synthetic image regression sources

These seven PDFs are exact copies of the synthetic sources retained by the 2026-10-24 PDF review in `.local/review-follow-up-2026-10-24/pdf/`. They contain generated 64-by-48 patterns, source color profiles, a decorative page background and, where named, soft masks. They are not private inputs or model-generated reference answers. Tests require no historical checkout or external file.

Cases: RGB JPEG; CMYK JPEG; RGB plus SMask; CMYK JPEG plus SMask; raw CMYK plus SMask; inserted RGBA with its generated SMask; and RGB JPX. All have 8-bit components. The coordinate fixtures are generated in `tests/test_pdf_delivery.py`, including four rotations and offset CropBoxes.

The source PDF bytes and encoded image/mask streams are the preservation reference. Source-page rendering provides a separate visible-pixel comparison, including its background when testing alpha. A maximum channel difference of three is allowed for native-resolution alpha compositing rounding in these synthetic checks; it is not a semantic-fidelity threshold or general color certification. Real-browser decoding, saved/reopened/exported files and provenance are checked separately.
