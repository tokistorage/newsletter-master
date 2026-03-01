#!/usr/bin/env python3
"""Verify QR codes in a generated PDF against the manifest in the source ZIP.

Renders each PDF page at 300 dpi, detects QR codes with pyzbar, and checks
that every URL from the ZIP manifest is present in at least one decoded QR.

Usage:
  python3 verify-qr.py <pdf_path> <zip_path>

Exit codes:
  0 — all manifest URLs found in the PDF
  1 — one or more manifest URLs missing
"""

import ctypes.util
import json
import os
import platform
import sys
import zipfile

# macOS Homebrew: pyzbar uses find_library('zbar') which fails on Apple Silicon.
# Patch find_library before importing pyzbar.
_orig_find_library = ctypes.util.find_library
def _patched_find_library(name):
    result = _orig_find_library(name)
    if result is None and name == "zbar" and platform.system() == "Darwin":
        candidate = "/opt/homebrew/opt/zbar/lib/libzbar.dylib"
        if os.path.exists(candidate):
            return candidate
    return result
ctypes.util.find_library = _patched_find_library

import fitz  # PyMuPDF
from pyzbar.pyzbar import decode as pyzbar_decode
from PIL import Image


DPI = 300
ZOOM = DPI / 72  # fitz default is 72 dpi


def load_expected_urls(zip_path):
    """Read manifest.json from ZIP and return the list of expected URLs."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        with zf.open("manifest.json") as f:
            manifest = json.load(f)
    return manifest.get("urls", [])


def extract_qr_urls_from_pdf(pdf_path):
    """Render each PDF page and return all decoded QR URLs."""
    doc = fitz.open(pdf_path)
    found_urls = set()
    mat = fitz.Matrix(ZOOM, ZOOM)

    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        decoded = pyzbar_decode(img)
        for obj in decoded:
            data = obj.data.decode("utf-8", errors="replace")
            found_urls.add(data)

    doc.close()
    return found_urls


def main():
    if len(sys.argv) != 3:
        print("Usage: verify-qr.py <pdf_path> <zip_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    zip_path = sys.argv[2]

    expected_urls = load_expected_urls(zip_path)
    if not expected_urls:
        print("WARNING: No URLs in manifest, skipping verification")
        return

    print(f"Verifying {len(expected_urls)} QR code(s) in {pdf_path} ...")

    found_urls = extract_qr_urls_from_pdf(pdf_path)

    # Check main QR URLs (from manifest)
    missing = []
    for url in expected_urls:
        if url not in found_urls:
            missing.append(url)

    # Report bonus detections (Play QR / Recovery QR)
    bonus = found_urls - set(expected_urls)
    if bonus:
        print(f"  Bonus QRs detected: {len(bonus)} (Play/Recovery)")

    if missing:
        print(f"FAIL: {len(missing)}/{len(expected_urls)} QR code(s) not detected:")
        for url in missing:
            print(f"  MISSING: {url[:120]}...")
        sys.exit(1)
    else:
        print(f"PASS: All {len(expected_urls)} QR code(s) verified successfully")


if __name__ == "__main__":
    main()
