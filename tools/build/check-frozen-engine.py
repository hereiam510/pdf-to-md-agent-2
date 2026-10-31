"""Local package smoke check. This script makes no network or model requests."""
import ssl
import sys

import httpx
import pymupdf

assert getattr(sys, "frozen", False), "Run this check through the frozen engine."
context = ssl.create_default_context()
assert context.verify_mode == ssl.CERT_REQUIRED
with httpx.Client(http2=True, trust_env=False):
    pass
print("Frozen engine: TLS validation, HTTP client, PDF resources, and script entry point ready.")
