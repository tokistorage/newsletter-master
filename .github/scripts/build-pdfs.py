#!/usr/bin/env python3
"""Scan zips/ and build missing PDFs using build-tokiqr-newsletter.py.

For each zips/{seriesId}/{serial}.zip without a corresponding
output/{seriesId}/TQ-{serial}.pdf, extract the ZIP, construct
materials.json + client-config.json, and invoke the build script.
"""

import json
import math
import os
import subprocess
import sys
import tempfile
import zipfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUILD_SCRIPT = os.path.join(REPO_ROOT, "lp-scripts", "newsletter", "build-tokiqr-newsletter.py")
SERIES_JSON = os.path.join(REPO_ROOT, "series.json")
ZIPS_DIR = os.path.join(REPO_ROOT, "zips")
OUTPUT_DIR = os.path.join(REPO_ROOT, "output")
PAGES_BASE = "https://tokistorage.github.io/newsletter-master"


def load_series():
    """Load series.json and return a dict keyed by seriesId."""
    if not os.path.exists(SERIES_JSON):
        return {}
    with open(SERIES_JSON, encoding="utf-8") as f:
        data = json.load(f)
    return {s["seriesId"]: s for s in data.get("series", [])}


def find_missing_pdfs():
    """Find ZIPs that don't have corresponding PDFs yet."""
    targets = []
    if not os.path.isdir(ZIPS_DIR):
        return targets
    for series_id in sorted(os.listdir(ZIPS_DIR)):
        series_dir = os.path.join(ZIPS_DIR, series_id)
        if not os.path.isdir(series_dir):
            continue
        for fname in sorted(os.listdir(series_dir)):
            if not fname.endswith(".zip"):
                continue
            serial_str = fname.replace(".zip", "")
            pdf_name = f"TQ-{serial_str}.pdf"
            pdf_path = os.path.join(OUTPUT_DIR, series_id, pdf_name)
            if not os.path.exists(pdf_path):
                targets.append((series_id, serial_str, os.path.join(series_dir, fname)))
    return targets


def build_pdf(series_id, serial_str, zip_path, series_map):
    """Extract ZIP, build materials/config, invoke build script."""
    serial = int(serial_str)
    series_info = series_map.get(series_id)

    if series_info:
        series_name = series_info.get("seriesName", series_id)
        start_year = series_info.get("startYear", 2026)
        vol_duration = series_info.get("volumeDurationYears", 20)
    else:
        # Fallback: derive name from seriesId
        series_name = series_id.replace("-", " ").split()[0] if "-" in series_id else series_id
        start_year = 2026
        vol_duration = 20
        print(f"  WARNING: seriesId '{series_id}' not found in series.json, using defaults")

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Extract ZIP
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp_dir)

        # Read manifest
        manifest_path = os.path.join(tmp_dir, "manifest.json")
        if not os.path.exists(manifest_path):
            print(f"  ERROR: No manifest.json in {zip_path}, skipping")
            return False
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)

        # Extract fields from manifest
        title = manifest.get("title", "")
        if not title:
            metadata = manifest.get("metadata", {})
            title = metadata.get("title", "")
        urls = manifest.get("urls", [])
        created_at = manifest.get("createdAt", "")

        # Compute volume (式年遷宮型: 1 volume = volumeDurationYears)
        if created_at:
            try:
                year = int(created_at[:4])
            except (ValueError, IndexError):
                year = start_year
        else:
            year = start_year
        volume = math.floor((year - start_year) / vol_duration) + 1
        if volume < 1:
            volume = 1

        # Build materials.json
        materials = {
            "serial": serial,
            "volume": volume,
            "number": serial,
            "seriesName": series_name,
            "title": title,
            "urls": urls,
            "date": created_at,
        }

        # Build client-config.json
        pdf_serial_str = f"{serial:05d}"
        config = {
            "pdfUrl": f"{PAGES_BASE}/output/{series_id}/TQ-{pdf_serial_str}.pdf",
            "pagesUrl": PAGES_BASE,
            "colophon": {
                "publisher": "TokiStorage（佐藤卓也）",
                "contentOriginator": series_name,
                "publisherAddress": "",
                "legalBasis": "国立国会図書館法 第25条・第25条の4",
                "note": "",
            },
        }

        # Write temp files
        materials_path = os.path.join(tmp_dir, "materials.json")
        config_path = os.path.join(tmp_dir, "config.json")
        with open(materials_path, "w", encoding="utf-8") as f:
            json.dump(materials, f, ensure_ascii=False, indent=2)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        # Output directory
        out_dir = os.path.join(OUTPUT_DIR, series_id)
        os.makedirs(out_dir, exist_ok=True)

        # ZIP URL for play QR
        zip_url = f"{PAGES_BASE}/zips/{series_id}/{serial_str}.zip"

        # Invoke build script
        cmd = [
            sys.executable, BUILD_SCRIPT,
            materials_path, config_path, out_dir, zip_url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ERROR: Build failed for {zip_path}")
            print(f"  stdout: {result.stdout}")
            print(f"  stderr: {result.stderr}")
            return False
        if result.stdout:
            print(f"  {result.stdout.strip()}")
        return True


def main():
    series_map = load_series()
    targets = find_missing_pdfs()

    if not targets:
        print("No missing PDFs to build.")
        return

    print(f"Building {len(targets)} PDF(s)...")
    success = 0
    for series_id, serial_str, zip_path in targets:
        print(f"  Building: {series_id}/{serial_str}")
        if build_pdf(series_id, serial_str, zip_path, series_map):
            success += 1

    print(f"Done: {success}/{len(targets)} PDFs built successfully.")
    if success < len(targets):
        sys.exit(1)


if __name__ == "__main__":
    main()
