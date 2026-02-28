#!/usr/bin/env python3
"""Generate index.html and index-en.html for newsletter-master GitHub Pages.

Reads series.json + zips/ + output/ directories and produces static
index pages with play/ZIP/PDF links for each newsletter issue.
Design matches tokistorage.github.io/lp/newsletters.html.
"""

import json
import os
import zipfile
from html import escape

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SERIES_JSON = os.path.join(REPO_ROOT, "series.json")
ZIPS_DIR = os.path.join(REPO_ROOT, "zips")
OUTPUT_DIR = os.path.join(REPO_ROOT, "output")

PAGES_BASE = "https://tokistorage.github.io/newsletter-master"
LP_BASE = "https://tokistorage.github.io/lp"
PLAY_BASE = "https://tokistorage.github.io/qr/play.html"

STRINGS = {
    "ja": {
        "lang": "ja",
        "title": "別冊特集シリーズ | トキストレージ",
        "h1": "別冊特集シリーズ",
        "subtitle": "TokiQR特集権を購入されたお客様ごとに開設される別冊特集ニュースレター。",
        "subtitle2": "各シリーズは独立した逐次刊行物として国立国会図書館に納本されます。",
        "empty": "現在開設されている別冊特集シリーズはありません。",
        "play": "&#9654; 再生",
        "issues_one": "号",
        "issues_other": "号",
        "back": "ニュースレター本誌に戻る",
        "back_url": f"{LP_BASE}/newsletters.html",
        "mission": "あなたが物語となり、世代の対話が重なり、未来の道となる。",
        "mission_en": "You become the story, generations of dialogue layer upon one another, and together they form the path ahead.",
        "lang_switch_label": "EN",
        "lang_switch_url": "index-en.html",
        "filename": "index.html",
    },
    "en": {
        "lang": "en",
        "title": "Special Feature Series | TokiStorage",
        "h1": "Special Feature Series",
        "subtitle": "Dedicated newsletter series created for each TokiQR Series Rights holder.",
        "subtitle2": "Each series is deposited as an independent serial publication with Japan's National Diet Library.",
        "empty": "No special feature series have been opened yet.",
        "play": "&#9654; Play",
        "issues_one": " issue",
        "issues_other": " issues",
        "back": "Back to Newsletter",
        "back_url": f"{LP_BASE}/newsletters-en.html",
        "mission": "You become the story, generations of dialogue layer upon one another, and together they form the path ahead.",
        "mission_en": "",
        "lang_switch_label": "JA",
        "lang_switch_url": "index.html",
        "filename": "index-en.html",
    },
}


def load_series():
    if not os.path.exists(SERIES_JSON):
        return {}
    with open(SERIES_JSON, encoding="utf-8") as f:
        data = json.load(f)
    return {s["seriesId"]: s for s in data.get("series", [])}


def scan_issues():
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

            date_display = date[:10] if date else ""

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

        issues.sort(key=lambda x: x["serial_str"], reverse=True)
        if issues:
            issues_by_series[series_id] = issues

    return issues_by_series


def generate_html(series_map, issues_by_series, s):
    """Generate HTML for a given language."""
    series_sections = []

    for series_id in sorted(issues_by_series.keys()):
        issues = issues_by_series[series_id]
        info = series_map.get(series_id, {})
        series_name = escape(info.get("seriesName", series_id))
        count = len(issues)
        count_label = f"{count}{s['issues_one']}" if s["lang"] == "ja" else f"{count}{s['issues_one'] if count == 1 else s['issues_other']}"

        rows = []
        for issue in issues:
            title_text = escape(issue["title"]) if issue["title"] else f'TQ-{issue["serial_str"]}'
            date_text = escape(issue["date"]) if issue["date"] else ""

            links = [f'<a href="{escape(issue["play_url"])}" class="link play">{s["play"]}</a>']
            links.append(f'<a href="{escape(issue["zip_url"])}" class="link zip">ZIP</a>')
            if issue["pdf_url"]:
                links.append(f'<a href="{escape(issue["pdf_url"])}" class="link pdf">PDF</a>')

            rows.append(f"""            <div class="issue">
                <div class="issue-info">
                    <span class="issue-title">{title_text}</span>
                    <span class="issue-date">{date_text}</span>
                </div>
                <div class="issue-links">{" ".join(links)}</div>
            </div>""")

        series_sections.append(f"""        <div class="series-card">
            <h3>{series_name}</h3>
            <p class="series-count">{count_label}</p>
{chr(10).join(rows)}
        </div>""")

    if not series_sections:
        body_content = f'        <p class="empty">{s["empty"]}</p>'
    else:
        body_content = "\n".join(series_sections)

    mission_sub = ""
    if s.get("mission_en"):
        mission_sub = f'\n            <p class="mission-sub">{s["mission_en"]}</p>'

    return f"""<!DOCTYPE html>
<html lang="{s['lang']}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" type="image/png" sizes="32x32" href="{LP_BASE}/asset/favicon-32.png">
    <link rel="apple-touch-icon" sizes="180x180" href="{LP_BASE}/asset/apple-touch-icon.png">
    <title>{s['title']}</title>
    <style>
        *, *::before, *::after {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Hiragino Sans', 'Segoe UI', Roboto, sans-serif;
            background: #f8fafc;
            color: #1e293b;
        }}

        .page-header {{
            background: #fff;
            border-bottom: 1px solid #e2e8f0;
            padding: 0.75rem 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .page-header a {{ color: #2563EB; text-decoration: none; font-size: 0.85rem; }}
        .page-header a:hover {{ text-decoration: underline; }}
        .lang-switch {{
            font-size: 0.8rem;
            color: #64748b;
            border: 1px solid #e2e8f0;
            padding: 0.2rem 0.6rem;
            border-radius: 4px;
            text-decoration: none !important;
        }}
        .lang-switch:hover {{ border-color: #2563EB; color: #2563EB; }}

        .page {{
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem 1.5rem;
        }}

        .page-title {{
            text-align: center;
            margin-bottom: 2.5rem;
        }}
        .page-title h1 {{
            font-family: 'Hiragino Mincho ProN', 'Yu Mincho', Georgia, serif;
            font-size: 1.8rem;
            color: #1e293b;
            margin: 0 0 0.75rem;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.6rem;
        }}
        .page-title h1::before {{
            content: '';
            width: 4px;
            height: 1.5rem;
            background: #C9A962;
            border-radius: 2px;
        }}
        .page-title .lead {{
            font-size: 0.9rem;
            color: #64748b;
            line-height: 1.8;
            max-width: 560px;
            margin: 0 auto;
        }}

        .series-card {{
            background: #fff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            transition: border-color 0.2s;
        }}
        .series-card:hover {{
            border-color: #C9A962;
        }}
        .series-card h3 {{
            font-family: 'Hiragino Mincho ProN', 'Yu Mincho', Georgia, serif;
            font-size: 1.15rem;
            color: #1e293b;
            margin: 0 0 0.25rem;
        }}
        .series-count {{
            font-size: 0.8rem;
            color: #94a3b8;
            margin: 0 0 1rem;
        }}

        .issue {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.6rem 0;
            border-top: 1px solid #f1f5f9;
        }}
        .issue:first-of-type {{ border-top: none; }}
        .issue-info {{
            display: flex;
            flex-direction: column;
            gap: 2px;
            min-width: 0;
            flex: 1;
        }}
        .issue-title {{
            font-size: 0.9rem;
            color: #1e293b;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .issue-date {{
            font-size: 0.75rem;
            color: #94a3b8;
        }}
        .issue-links {{
            display: flex;
            gap: 8px;
            flex-shrink: 0;
            margin-left: 12px;
        }}

        .link {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.75rem;
            text-decoration: none;
            font-weight: 500;
            transition: opacity 0.15s;
        }}
        .link:hover {{ opacity: 0.8; }}
        .link.play {{ background: #C9A962; color: #fff; }}
        .link.zip {{ background: #e2e8f0; color: #475569; }}
        .link.pdf {{ background: #f1f5f9; color: #C9A962; border: 1px solid #C9A962; }}

        .empty {{
            text-align: center;
            color: #94a3b8;
            padding: 3rem 0;
            font-size: 0.9rem;
        }}

        .page-footer {{
            text-align: center;
            padding: 2.5rem 1.5rem;
            border-top: 1px solid #e2e8f0;
            margin-top: 1rem;
        }}
        .mission {{
            font-family: Georgia, 'Times New Roman', serif;
            font-size: 0.85rem;
            color: #94a3b8;
            font-style: italic;
            margin: 0 0 0.4rem;
            line-height: 1.6;
        }}
        .mission-sub {{
            font-family: Georgia, 'Times New Roman', serif;
            font-size: 0.75rem;
            color: #b0bec5;
            font-style: italic;
            margin: 0 0 1rem;
        }}
        .copyright {{
            font-size: 0.75rem;
            color: #94a3b8;
            margin: 0;
        }}
        .copyright a {{ color: #2563EB; text-decoration: none; }}

        @media (max-width: 480px) {{
            .issue {{ flex-direction: column; align-items: flex-start; gap: 8px; }}
            .issue-links {{ margin-left: 0; }}
            .page-title h1 {{ font-size: 1.4rem; }}
        }}
    </style>
</head>
<body>
    <div class="page-header">
        <a href="{s['back_url']}">&larr; {s['back']}</a>
        <a href="{s['lang_switch_url']}" class="lang-switch">{s['lang_switch_label']}</a>
    </div>
    <div class="page">
        <div class="page-title">
            <h1>{s['h1']}</h1>
            <p class="lead">{s['subtitle']}<br>{s['subtitle2']}</p>
        </div>
{body_content}
    </div>
    <footer class="page-footer">
        <p class="mission">{s['mission']}</p>{mission_sub}
        <p class="copyright">&copy; 2026 <a href="{LP_BASE}/">TokiStorage</a>. All rights reserved.</p>
    </footer>
</body>
</html>
"""


def main():
    series_map = load_series()
    issues_by_series = scan_issues()

    for lang, strings in STRINGS.items():
        html = generate_html(series_map, issues_by_series, strings)
        out_path = os.path.join(REPO_ROOT, strings["filename"])
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)

    total = sum(len(v) for v in issues_by_series.values())
    print(f"Generated index.html + index-en.html: {len(issues_by_series)} series, {total} issues")


if __name__ == "__main__":
    main()
