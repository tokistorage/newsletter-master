#!/usr/bin/env python3
"""Generate index pages for newsletter-master GitHub Pages.

Reads series.json + zips/ + output/ directories and produces:
  - index.html / index-en.html        — series list (cards)
  - series/{id}/index.html / index-en.html — per-series issue list

Design matches tokistorage.github.io/lp/newsletters.html.
"""

import json
import os
import zipfile
from collections import OrderedDict
from datetime import datetime, timezone, timedelta
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
        "issues_one": "件",
        "issues_other": "件",
        "series_latest": "最新",
        "back": "ニュースレター本誌に戻る",
        "back_url": f"{LP_BASE}/newsletters.html",
        "back_series": "シリーズ一覧に戻る",
        "back_series_url": "../../index.html",
        "mission": "あなたが物語となり、世代の対話が重なり、未来の道となる。",
        "mission_en": "",
        "lang_switch_label": "EN",
        "lang_switch_url": "index-en.html",
        "filename": "index.html",
        "nav_logo": "トキストレージ",
        "nav_newsletter": "ニュースレター本誌",
        "nav_newsletter_url": f"{LP_BASE}/newsletters.html",
        "nav_series": "シリーズ一覧",
        "nav_toggle_label": "メニュー",
        "recent_series": "最新のシリーズ",
        "recent_issues": "最新の号",
        "all_series": "すべてのシリーズ",
        "all_issues": "すべての号",
        "century_suffix": "世紀",
        "year_suffix": "年",
        "months": ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"],
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
        "series_latest": "Latest",
        "back": "Back to Newsletter",
        "back_url": f"{LP_BASE}/newsletters-en.html",
        "back_series": "Back to series list",
        "back_series_url": "../../index-en.html",
        "mission": "You become a story, generations connect in dialogue, the path forward.",
        "mission_en": "",
        "lang_switch_label": "JA",
        "lang_switch_url": "index.html",
        "filename": "index-en.html",
        "nav_logo": "TokiStorage",
        "nav_newsletter": "Newsletter",
        "nav_newsletter_url": f"{LP_BASE}/newsletters-en.html",
        "nav_series": "Series List",
        "nav_toggle_label": "Menu",
        "recent_series": "Recent Series",
        "recent_issues": "Recent Issues",
        "all_series": "All Series",
        "all_issues": "All Issues",
        "century_suffix": "",  # handled by _century_label
        "year_suffix": "",
        "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    },
}


def load_series():
    if not os.path.exists(SERIES_JSON):
        return {}
    with open(SERIES_JSON, encoding="utf-8") as f:
        data = json.load(f)
    return {s["seriesId"]: s for s in data.get("series", [])}


def _format_datetime(iso_str, tz_str=""):
    """Format ISO datetime to 'YYYY-MM-DD HH:MM' with optional timezone offset."""
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        if tz_str:
            clean = tz_str.lstrip("+-")
            parts = clean.split(":")
            hours = int(parts[0])
            minutes = int(parts[1]) if len(parts) > 1 else 0
            sign = -1 if tz_str.startswith("-") else 1
            dt = dt.astimezone(timezone(timedelta(hours=hours, minutes=minutes) * sign))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return iso_str[:10] if len(iso_str) >= 10 else iso_str


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
            tz_offset = ""
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
                            tz_offset = manifest.get("metadata", {}).get("tz", "")
            except Exception as e:
                print(f"  WARNING: Could not read {zip_path}: {e}")

            date_display = _format_datetime(date, tz_offset)

            pdf_name = f"TQ-{serial_str}.pdf"
            pdf_path = os.path.join(OUTPUT_DIR, series_id, pdf_name)
            has_pdf = os.path.exists(pdf_path)

            zip_url = f"{PAGES_BASE}/zips/{series_id}/{fname}"
            pdf_url = f"{PAGES_BASE}/output/{series_id}/{pdf_name}" if has_pdf else ""
            play_url = f"{PLAY_BASE}?zip={zip_url}"
            if pdf_url:
                play_url += f"&pdf={pdf_url}"

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


def _century_label(century, s):
    if s["lang"] == "ja":
        return f"{century}{s['century_suffix']}"
    # English ordinal
    if 11 <= century % 100 <= 13:
        suffix = "th"
    elif century % 10 == 1:
        suffix = "st"
    elif century % 10 == 2:
        suffix = "nd"
    elif century % 10 == 3:
        suffix = "rd"
    else:
        suffix = "th"
    return f"{century}{suffix} century"


def _year_label(year, s):
    if s["lang"] == "ja":
        return f"{year}{s['year_suffix']}"
    return str(year)


def _month_label(month, s):
    return s["months"][month - 1]


def _shikinen_range(year):
    century = (year - 1) // 100 + 1
    century_start = (century - 1) * 100 + 1
    shikinen_idx = (year - century_start) // 20
    shikinen_start = century_start + shikinen_idx * 20
    shikinen_end = shikinen_start + 19
    return shikinen_start, shikinen_end


def _time_hierarchy(items, date_key, s):
    """Group items into century > shikinen > year > month, newest first."""
    tree = OrderedDict()
    for item in items:
        d = item[date_key]
        if not d or len(d) < 7:
            continue
        year = int(d[:4])
        month = int(d[5:7])
        century = (year - 1) // 100 + 1
        sh_start, sh_end = _shikinen_range(year)

        c_key = century
        sh_key = (sh_start, sh_end)
        y_key = year
        m_key = month

        tree.setdefault(c_key, OrderedDict()) \
            .setdefault(sh_key, OrderedDict()) \
            .setdefault(y_key, OrderedDict()) \
            .setdefault(m_key, []).append(item)

    # Sort all levels descending (newest first)
    sorted_tree = OrderedDict()
    for c_key in sorted(tree.keys(), reverse=True):
        sorted_c = OrderedDict()
        for sh_key in sorted(tree[c_key].keys(), reverse=True):
            sorted_sh = OrderedDict()
            for y_key in sorted(tree[c_key][sh_key].keys(), reverse=True):
                sorted_y = OrderedDict()
                for m_key in sorted(tree[c_key][sh_key][y_key].keys(), reverse=True):
                    sorted_y[m_key] = tree[c_key][sh_key][y_key][m_key]
                sorted_sh[y_key] = sorted_y
            sorted_c[sh_key] = sorted_sh
        sorted_tree[c_key] = sorted_c

    return sorted_tree


def _count_items(node):
    """Count leaf items recursively in a nested OrderedDict."""
    if isinstance(node, list):
        return len(node)
    return sum(_count_items(v) for v in node.values())


def _render_time_groups(tree, render_item, s, collapsed=False):
    """Render nested time hierarchy as accordion HTML.
    If collapsed=True, all groups start closed (no auto-open)."""
    parts = []
    levels = ["century", "shikinen", "year", "month"]

    def _render(node, level_idx, is_first):
        level = levels[level_idx]
        keys = list(node.keys())
        single_child = len(keys) == 1

        for i, key in enumerate(keys):
            first_at_level = (i == 0) and is_first
            if collapsed:
                open_class = ""
            else:
                open_class = " open" if first_at_level or single_child else ""
            count = _count_items(node[key])
            count_text = _group_count_label(count, s)

            if level == "century":
                label = _century_label(key, s)
            elif level == "shikinen":
                sh_start, sh_end = key
                label = f"{sh_start}\u2013{sh_end}"
            elif level == "year":
                label = _year_label(key, s)
            else:
                label = _month_label(key, s)

            parts.append(
                f'<div class="time-group{open_class}" data-level="{level}">'
                f'<button class="time-heading">{escape(label)} '
                f'<span class="time-count">{count_text}</span></button>'
                f'<div class="time-body">'
            )

            if level_idx < len(levels) - 1:
                _render(node[key], level_idx + 1, first_at_level)
            else:
                # Leaf level — render items
                for item in node[key]:
                    parts.append(render_item(item))

            parts.append('</div></div>')

    _render(tree, 0, True)
    return "\n".join(parts)


def _count_label(count, s):
    if s["lang"] == "ja":
        return f"{count}{s['issues_one']}"
    return f"{count}{s['issues_one'] if count == 1 else s['issues_other']}"


def _group_count_label(count, s):
    """Count label for accordion headings (件 / items)."""
    if s["lang"] == "ja":
        return f"{count}件"
    return f"{count} item{'s' if count != 1 else ''}"


def _footer_html(s):
    mission_sub = ""
    if s.get("mission_en"):
        mission_sub = f'\n            <p class="mission-sub">{s["mission_en"]}</p>'
    return f"""    <footer class="page-footer">
        <p class="mission">{s['mission']}</p>{mission_sub}
        <p class="copyright">&copy; 2026 <a href="{LP_BASE}/">TokiStorage</a>. All rights reserved.</p>
    </footer>"""


def _nav_html(s, extra_links=""):
    """Generate toki-nav navigation bar."""
    return f"""    <nav class="toki-nav">
        <a href="{LP_BASE}/" class="nav-logo">{s['nav_logo']}</a>
        <div class="nav-links">
            <a href="{s['nav_newsletter_url']}">{s['nav_newsletter']}</a>
{extra_links}            <a href="{s['lang_switch_url']}" class="lang-switch" aria-label="{s['lang_switch_label']}">{s['lang_switch_label']}</a>
        </div>
        <button class="nav-toggle" aria-label="{s['nav_toggle_label']}">
            <span></span><span></span><span></span>
        </button>
    </nav>"""


def _nav_js():
    """Mobile nav toggle + accordion script."""
    return """    <script>
    (function() {
        var t = document.querySelector('.nav-toggle');
        var n = document.querySelector('.nav-links');
        if (t && n) t.addEventListener('click', function() { n.classList.toggle('open'); });
        document.querySelectorAll('.time-heading').forEach(function(btn) {
            btn.addEventListener('click', function() {
                this.parentElement.classList.toggle('open');
            });
        });
    })();
    </script>"""


def common_css():
    return """        *, *::before, *::after { box-sizing: border-box; }
        body {
            margin: 0;
            padding-top: 3.2rem;
            font-family: -apple-system, BlinkMacSystemFont, 'Hiragino Sans', 'Segoe UI', Roboto, sans-serif;
            background: #f8fafc;
            color: #1e293b;
        }

        /* ---- Navigation ---- */
        .toki-nav {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 1000;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.8rem 2rem;
            background: rgba(255, 255, 255, 0.92);
            backdrop-filter: blur(16px);
            border-bottom: 1px solid #e2e8f0;
            transition: box-shadow 0.3s ease;
        }
        .nav-logo {
            font-family: 'Hiragino Mincho ProN', 'Yu Mincho', Georgia, serif;
            font-size: 1.1rem;
            font-weight: 600;
            color: #1e293b;
            text-decoration: none;
            letter-spacing: 0.08em;
        }
        .nav-logo::before {
            content: '';
            display: inline-block;
            width: 22px;
            height: 22px;
            background: url('""" + LP_BASE + """/asset/tokistorage-icon-512.png') no-repeat center / contain;
            vertical-align: -3px;
            margin-right: 6px;
        }
        .nav-links {
            display: flex;
            align-items: center;
            gap: 2rem;
        }
        .nav-links a {
            color: #64748b;
            text-decoration: none;
            font-size: 0.8rem;
            letter-spacing: 0.03em;
            transition: color 0.3s ease;
        }
        .nav-links a:hover { color: #2563EB; }
        .lang-switch {
            padding: 0.35rem 0.7rem !important;
            font-size: 0.7rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            border: 1.5px solid #e2e8f0;
            border-radius: 0.3rem;
            color: #94a3b8 !important;
            transition: all 0.3s ease;
            margin-left: 0.3rem;
        }
        .lang-switch:hover {
            color: #2563EB !important;
            border-color: #2563EB;
        }
        .nav-toggle {
            display: none;
            flex-direction: column;
            gap: 5px;
            background: none;
            border: none;
            cursor: pointer;
            padding: 4px;
        }
        .nav-toggle span {
            display: block;
            width: 22px;
            height: 2px;
            background: #1e293b;
            transition: all 0.3s ease;
        }

        /* ---- Page ---- */
        .page {
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem 1.5rem;
        }

        .page-title {
            text-align: center;
            margin-bottom: 2.5rem;
        }
        .page-title h1 {
            font-family: 'Hiragino Mincho ProN', 'Yu Mincho', Georgia, serif;
            font-size: 1.8rem;
            color: #1e293b;
            margin: 0 0 0.75rem;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.6rem;
        }
        .page-title h1::before {
            content: '';
            width: 4px;
            height: 1.5rem;
            background: #C9A962;
            border-radius: 2px;
        }
        .page-title .lead {
            font-size: 0.9rem;
            color: #64748b;
            line-height: 1.8;
            max-width: 560px;
            margin: 0 auto;
        }

        /* ---- Cards ---- */
        .series-card {
            background: #fff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            transition: border-color 0.2s;
        }
        .series-card:hover {
            border-color: #C9A962;
        }
        .series-card h3 {
            font-family: 'Hiragino Mincho ProN', 'Yu Mincho', Georgia, serif;
            font-size: 1.15rem;
            color: #1e293b;
            margin: 0 0 0.25rem;
        }
        .series-count {
            font-size: 0.8rem;
            color: #94a3b8;
            margin: 0 0 1rem;
        }

        /* ---- Issues ---- */
        .issue {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.6rem 0;
            border-top: 1px solid #f1f5f9;
        }
        .issue:first-of-type { border-top: none; }
        .issue-info {
            display: flex;
            flex-direction: column;
            gap: 2px;
            min-width: 0;
            flex: 1;
        }
        .issue-title {
            font-size: 0.9rem;
            color: #1e293b;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .issue-date {
            font-size: 0.75rem;
            color: #94a3b8;
        }
        .issue-links {
            display: flex;
            gap: 8px;
            flex-shrink: 0;
            margin-left: 12px;
        }

        .link {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.75rem;
            text-decoration: none;
            font-weight: 500;
            transition: opacity 0.15s;
        }
        .link:hover { opacity: 0.8; }
        .link.play { background: #C9A962; color: #fff; }
        .link.zip { background: #e2e8f0; color: #475569; }
        .link.pdf { background: #f1f5f9; color: #C9A962; border: 1px solid #C9A962; }

        .empty {
            text-align: center;
            color: #94a3b8;
            padding: 3rem 0;
            font-size: 0.9rem;
        }

        /* ---- Time Accordion ---- */
        .time-group { margin-bottom: 0.5rem; }
        .time-heading {
            display: flex; align-items: center; gap: 0.5rem;
            width: 100%; background: none; border: none;
            padding: 0.5rem 0; cursor: pointer;
            font-family: 'Hiragino Mincho ProN', 'Yu Mincho', Georgia, serif;
            font-size: 1rem;
            color: #1e293b; text-align: left;
        }
        .time-heading::before {
            content: '\u25b6'; font-size: 0.65rem; color: #94a3b8;
            transition: transform 0.2s;
        }
        .time-group.open > .time-heading::before { transform: rotate(90deg); }
        .time-body { display: none; padding-left: 1rem; }
        .time-group.open > .time-body { display: block; }
        .time-count { font-size: 0.75rem; color: #94a3b8; font-weight: normal; }
        [data-level="century"] > .time-heading { font-size: 1.1rem; }
        [data-level="shikinen"] > .time-heading { font-size: 1rem; }
        [data-level="year"] > .time-heading { font-size: 0.95rem; }
        [data-level="month"] > .time-heading { font-size: 0.9rem; }

        /* ---- Section Heading ---- */
        .section-heading {
            font-family: 'Hiragino Mincho ProN', 'Yu Mincho', Georgia, serif;
            font-size: 1.1rem;
            color: #1e293b;
            margin: 0 0 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #C9A962;
        }
        .section-divider {
            margin-top: 2rem;
        }

        /* ---- Footer ---- */
        .page-footer {
            text-align: center;
            padding: 2.5rem 1.5rem;
            border-top: 1px solid #e2e8f0;
            margin-top: 1rem;
        }
        .mission {
            font-family: Georgia, 'Times New Roman', serif;
            font-size: 0.85rem;
            color: #94a3b8;
            font-style: italic;
            margin: 0 0 0.4rem;
            line-height: 1.6;
        }
        .mission-sub {
            font-family: Georgia, 'Times New Roman', serif;
            font-size: 0.75rem;
            color: #b0bec5;
            font-style: italic;
            margin: 0 0 1rem;
        }
        .copyright {
            font-size: 0.75rem;
            color: #94a3b8;
            margin: 0;
        }
        .copyright a { color: #2563EB; text-decoration: none; }

        /* ---- Responsive ---- */
        @media (max-width: 768px) {
            .toki-nav { padding: 0.7rem 1.5rem; }
            .nav-links {
                display: none;
                position: absolute;
                top: 100%;
                left: 0;
                right: 0;
                background: rgba(255, 255, 255, 0.97);
                backdrop-filter: blur(16px);
                flex-direction: column;
                padding: 1.2rem 1.5rem;
                gap: 0.8rem;
                border-bottom: 1px solid #e2e8f0;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            }
            .nav-links.open { display: flex; }
            .nav-toggle { display: flex; }
        }
        @media (max-width: 480px) {
            .issue { flex-direction: column; align-items: flex-start; gap: 8px; }
            .issue-links { margin-left: 0; }
            .page-title h1 { font-size: 1.4rem; }
        }"""


def _index_card_css():
    """Extra CSS for top-level index cards (clickable, with latest date)."""
    return """
        .series-card a {
            text-decoration: none;
            color: inherit;
            display: block;
        }
        .series-meta {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        .series-count {
            margin: 0;
        }
        .series-latest {
            font-size: 0.8rem;
            color: #94a3b8;
        }"""


def _render_series_card(item, s):
    """Render a single series card for the index page."""
    series_id = item["_series_id"]
    series_name = escape(item["_series_name"])
    count = item["_count"]
    label = _count_label(count, s)
    latest_date = item["_date"]

    latest_html = ""
    if latest_date:
        latest_html = f' <span class="series-latest">({s["series_latest"]}: {escape(latest_date)})</span>'

    return f"""<div class="series-card">
            <a href="series/{escape(series_id)}/{s['filename']}">
                <h3>{series_name}</h3>
                <div class="series-meta">
                    <p class="series-count">{label}{latest_html}</p>
                </div>
            </a>
        </div>"""


def generate_index_html(series_map, issues_by_series, s):
    """Generate top-level index page (series list only, no individual issues)."""
    # Build items with latest date per series for time grouping
    series_items = []
    for series_id in sorted(issues_by_series.keys()):
        issues = issues_by_series[series_id]
        info = series_map.get(series_id, {})
        latest_date = issues[0]["date"] if issues else ""
        series_items.append({
            "_series_id": series_id,
            "_series_name": info.get("seriesName", series_id),
            "_count": len(issues),
            "_date": latest_date,
        })

    if not series_items:
        body_content = f'        <p class="empty">{s["empty"]}</p>'
    else:
        # Recent section: top 10 series by latest date
        sorted_by_date = sorted(series_items, key=lambda x: x["_date"], reverse=True)
        recent = sorted_by_date[:10]
        render = lambda item: _render_series_card(item, s)
        recent_cards = "\n".join(render(item) for item in recent)
        recent_section = f"""        <h2 class="section-heading">{s['recent_series']}</h2>
{recent_cards}"""

        # All series accordion
        tree = _time_hierarchy(series_items, "_date", s)
        accordion_html = _render_time_groups(tree, render, s, collapsed=True)
        all_section = f"""        <h2 class="section-heading section-divider">{s['all_series']}</h2>
{accordion_html}"""

        body_content = f"{recent_section}\n{all_section}"

    return f"""<!DOCTYPE html>
<html lang="{s['lang']}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" type="image/png" sizes="32x32" href="{LP_BASE}/asset/favicon-32.png">
    <link rel="apple-touch-icon" sizes="180x180" href="{LP_BASE}/asset/apple-touch-icon.png">
    <title>{s['title']}</title>
    <style>
{common_css()}
{_index_card_css()}
    </style>
</head>
<body>
{_nav_html(s)}
    <div class="page">
        <div class="page-title">
            <h1>{s['h1']}</h1>
            <p class="lead">{s['subtitle']}<br>{s['subtitle2']}</p>
        </div>
{body_content}
    </div>
{_footer_html(s)}
{_nav_js()}
</body>
</html>
"""


def _render_issue_row(issue, s):
    """Render a single issue row for a series page."""
    title_text = escape(issue["title"]) if issue["title"] else f'TQ-{issue["serial_str"]}'
    date_text = escape(issue["date"]) if issue["date"] else ""

    links = [f'<a href="{escape(issue["play_url"])}" class="link play">{s["play"]}</a>']
    links.append(f'<a href="{escape(issue["zip_url"])}" class="link zip">ZIP</a>')
    if issue["pdf_url"]:
        links.append(f'<a href="{escape(issue["pdf_url"])}" class="link pdf">PDF</a>')

    return f"""<div class="issue">
                <div class="issue-info">
                    <span class="issue-title">{title_text}</span>
                    <span class="issue-date">{date_text}</span>
                </div>
                <div class="issue-links">{" ".join(links)}</div>
            </div>"""


def generate_series_html(series_id, info, issues, s):
    """Generate per-series detail page (all issues listed)."""
    series_name = escape(info.get("seriesName", series_id))
    count = len(issues)
    label = _count_label(count, s)

    render = lambda issue: _render_issue_row(issue, s)

    # Recent section: top 10 issues by date
    sorted_by_date = sorted(issues, key=lambda x: x["date"], reverse=True)
    recent = sorted_by_date[:10]
    recent_rows = "\n".join(render(issue) for issue in recent)
    recent_section = f"""            <h2 class="section-heading">{s['recent_issues']}</h2>
{recent_rows}"""

    # All issues accordion
    tree = _time_hierarchy(issues, "date", s)
    grouped_html = _render_time_groups(tree, render, s, collapsed=True)
    all_section = f"""            <h2 class="section-heading section-divider">{s['all_issues']}</h2>
{grouped_html}"""

    body_content = f"""        <div class="series-card">
            <h3>{series_name}</h3>
            <p class="series-count">{label}</p>
{recent_section}
{all_section}
        </div>"""

    series_link = f'            <a href="{s["back_series_url"]}">{s["nav_series"]}</a>\n'

    return f"""<!DOCTYPE html>
<html lang="{s['lang']}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" type="image/png" sizes="32x32" href="{LP_BASE}/asset/favicon-32.png">
    <link rel="apple-touch-icon" sizes="180x180" href="{LP_BASE}/asset/apple-touch-icon.png">
    <title>{series_name} | {s['title']}</title>
    <style>
{common_css()}
    </style>
</head>
<body>
{_nav_html(s, extra_links=series_link)}
    <div class="page">
        <div class="page-title">
            <h1>{series_name}</h1>
        </div>
{body_content}
    </div>
{_footer_html(s)}
{_nav_js()}
</body>
</html>
"""


def main():
    series_map = load_series()
    issues_by_series = scan_issues()

    # Generate top-level index pages
    for lang, strings in STRINGS.items():
        html = generate_index_html(series_map, issues_by_series, strings)
        out_path = os.path.join(REPO_ROOT, strings["filename"])
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)

    # Generate per-series detail pages
    series_count = 0
    for series_id in sorted(issues_by_series.keys()):
        issues = issues_by_series[series_id]
        info = series_map.get(series_id, {})
        series_dir = os.path.join(REPO_ROOT, "series", series_id)
        os.makedirs(series_dir, exist_ok=True)

        for lang, strings in STRINGS.items():
            html = generate_series_html(series_id, info, issues, strings)
            out_path = os.path.join(series_dir, strings["filename"])
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(html)
        series_count += 1

    total = sum(len(v) for v in issues_by_series.values())
    print(f"Generated index pages: {series_count} series, {total} issues")


if __name__ == "__main__":
    main()
