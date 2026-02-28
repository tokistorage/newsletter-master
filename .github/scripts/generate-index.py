#!/usr/bin/env python3
"""Generate index.html for newsletter-master GitHub Pages.

Reads series.json + zips/ + output/ directories and produces a static
index.html with play/ZIP/PDF links for each newsletter issue.
"""

import json
import os
import zipfile
from html import escape

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SERIES_JSON = os.path.join(REPO_ROOT, "series.json")
ZIPS_DIR = os.path.join(REPO_ROOT, "zips")
OUTPUT_DIR = os.path.join(REPO_ROOT, "output")
INDEX_PATH = os.path.join(REPO_ROOT, "index.html")

PAGES_BASE = "https://tokistorage.github.io/newsletter-master"
PLAY_BASE = "https://tokistorage.github.io/qr/play.html"


def load_series():
    if not os.path.exists(SERIES_JSON):
        return {}
    with open(SERIES_JSON, encoding="utf-8") as f:
        data = json.load(f)
    return {s["seriesId"]: s for s in data.get("series", [])}


def scan_issues():
    """Scan zips/ directory and collect issue metadata.

    Returns dict: seriesId -> list of issue dicts, sorted by serial desc.
    """
    issues_by_series = {}
    if not os.path.isdir(ZIPS_DIR):
        return issues_by_series

    for series_id in sorted(os.listdir(ZIPS_DIR)):
        series_dir = os.path.join(ZIPS_DIR, series_id)
        if not os.path.isdir(series_dir):
            continue
        issues = []
        for fname in os.listdir(series_dir):
            if not fname.endswith(".zip"):
                continue
            serial_str = fname.replace(".zip", "")
            zip_path = os.path.join(series_dir, fname)

            # Read manifest from ZIP
            title = ""
            date = ""
            try:
                with zipfile.ZipFile(zip_path, "r") as zf:
                    if "manifest.json" in zf.namelist():
                        with zf.open("manifest.json") as mf:
                            manifest = json.loads(mf.read().decode("utf-8"))
                            title = manifest.get("title", "")
                            if not title:
                                metadata = manifest.get("metadata", {})
                                title = metadata.get("title", "")
                            date = manifest.get("createdAt", "")
            except Exception as e:
                print(f"  WARNING: Could not read {zip_path}: {e}")

            # Format date for display
            date_display = ""
            if date:
                date_display = date[:10]  # yyyy-MM-dd

            # Check if PDF exists
            pdf_name = f"TQ-{serial_str}.pdf"
            pdf_path = os.path.join(OUTPUT_DIR, series_id, pdf_name)
            has_pdf = os.path.exists(pdf_path)

            zip_url = f"{PAGES_BASE}/zips/{series_id}/{fname}"
            pdf_url = f"{PAGES_BASE}/output/{series_id}/{pdf_name}" if has_pdf else ""
            play_url = f"{PLAY_BASE}?zip={zip_url}"

            issues.append({
                "serial_str": serial_str,
                "title": title,
                "date": date_display,
                "zip_url": zip_url,
                "pdf_url": pdf_url,
                "play_url": play_url,
            })

        # Sort descending by serial
        issues.sort(key=lambda x: x["serial_str"], reverse=True)
        if issues:
            issues_by_series[series_id] = issues

    return issues_by_series


def generate_html(series_map, issues_by_series):
    """Generate the full index.html content."""
    series_sections = []

    for series_id in sorted(issues_by_series.keys()):
        issues = issues_by_series[series_id]
        info = series_map.get(series_id, {})
        series_name = escape(info.get("seriesName", series_id))

        rows = []
        for issue in issues:
            title_text = escape(issue["title"]) if issue["title"] else f'TQ-{issue["serial_str"]}'
            date_text = escape(issue["date"]) if issue["date"] else ""

            links = []
            links.append(f'<a href="{escape(issue["play_url"])}" class="link play">&#9654; 再生</a>')
            links.append(f'<a href="{escape(issue["zip_url"])}" class="link zip">ZIP</a>')
            if issue["pdf_url"]:
                links.append(f'<a href="{escape(issue["pdf_url"])}" class="link pdf">PDF</a>')

            rows.append(f"""        <div class="issue">
          <div class="issue-info">
            <span class="issue-title">{title_text}</span>
            <span class="issue-date">{date_text}</span>
          </div>
          <div class="issue-links">{" ".join(links)}</div>
        </div>""")

        series_sections.append(f"""    <section class="series">
      <h2>{series_name}</h2>
      <p class="series-count">{len(issues)} issue{"s" if len(issues) != 1 else ""}</p>
{chr(10).join(rows)}
    </section>""")

    if not series_sections:
        body_content = '    <p class="empty">まだニュースレターがありません。</p>'
    else:
        body_content = "\n".join(series_sections)

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TokiQR Newsletter Archive</title>
<style>
*,*::before,*::after{{box-sizing:border-box}}
body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f8fafc;color:#1e293b}}
.header{{background:#fff;border-bottom:3px solid #2563eb;padding:24px 16px;text-align:center}}
.header h1{{margin:0;font-size:1.5rem;color:#1e293b}}
.header p{{margin:8px 0 0;color:#64748b;font-size:0.875rem}}
.container{{max-width:720px;margin:0 auto;padding:24px 16px}}
.series{{background:#fff;border-radius:8px;padding:20px;margin-bottom:24px;box-shadow:0 1px 3px rgba(0,0,0,0.08)}}
.series h2{{margin:0 0 4px;font-size:1.125rem;color:#1e293b}}
.series-count{{margin:0 0 16px;font-size:0.8rem;color:#94a3b8}}
.issue{{display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-top:1px solid #e2e8f0}}
.issue:first-of-type{{border-top:none}}
.issue-info{{display:flex;flex-direction:column;gap:2px;min-width:0;flex:1}}
.issue-title{{font-size:0.9rem;color:#1e293b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.issue-date{{font-size:0.75rem;color:#94a3b8}}
.issue-links{{display:flex;gap:8px;flex-shrink:0;margin-left:12px}}
.link{{display:inline-block;padding:4px 10px;border-radius:4px;font-size:0.75rem;text-decoration:none;font-weight:500;transition:opacity 0.15s}}
.link:hover{{opacity:0.8}}
.link.play{{background:#2563eb;color:#fff}}
.link.zip{{background:#e2e8f0;color:#475569}}
.link.pdf{{background:#f1f5f9;color:#2563eb;border:1px solid #2563eb}}
.empty{{text-align:center;color:#94a3b8;padding:40px 0}}
.footer{{text-align:center;padding:24px 16px;color:#94a3b8;font-size:0.75rem}}
.footer a{{color:#2563eb;text-decoration:none}}
@media(max-width:480px){{
  .issue{{flex-direction:column;align-items:flex-start;gap:8px}}
  .issue-links{{margin-left:0}}
}}
</style>
</head>
<body>
  <div class="header">
    <h1>TokiQR Newsletter Archive</h1>
    <p>Voice newsletters preserved as QR codes</p>
  </div>
  <div class="container">
{body_content}
  </div>
  <div class="footer">
    <p>&copy; <a href="https://tokistorage.github.io/lp/">TokiStorage</a></p>
  </div>
</body>
</html>
"""


def main():
    series_map = load_series()
    issues_by_series = scan_issues()
    html = generate_html(series_map, issues_by_series)

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    total = sum(len(v) for v in issues_by_series.values())
    print(f"Generated index.html: {len(issues_by_series)} series, {total} issues")


if __name__ == "__main__":
    main()
