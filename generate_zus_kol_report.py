#!/usr/bin/env python3
import argparse
import csv
import html
import statistics
from pathlib import Path

POST_COLS = {
    "views": "IG - View (Post)",
    "likes": "IG - Like (Post)",
    "comments": "IG - Comment (Post)",
    "shares": "IG - Share (Post)",
    "reposts": "IG - Repost (Post)",
    "saves": "IG - Save (Post)",
}

REEL_COLS = {
    "views": "IG - View (Reels)",
    "likes": "IG - Like (Reels)",
    "comments": "IG - Comment (Reels)",
    "shares": "IG - Share (Reels)",
    "reposts": "IG - Repost (Reels)",
    "saves": "IG - Save (Reels)",
}

TIKTOK_COLS = {
    "views": "TT - View",
    "likes": "TT - Like",
    "comments": "TT - Comment",
    "shares": "TT - Share",
    "reposts": None,
    "saves": "TT - Save",
}

ALL_KEYS = ["views", "likes", "comments", "shares", "reposts", "saves"]


def parse_num(v):
    s = (v or "").strip().replace(",", "")
    return int(s) if s.isdigit() else None


def nfmt(v):
    return f"{v:,}"


def pfmt(v):
    return f"{v:.2f}%"


def calc_er(likes, comments, shares, saves, views):
    if views <= 0:
        return 0.0
    return ((likes + comments + shares + saves) / views) * 100.0


def pstdev(values):
    return statistics.pstdev(values) if len(values) > 1 else 0.0


def tag_views(v, mean, sd):
    if v >= mean + 2 * sd:
        return ("👁️ 🌟 Outstanding", "tag-outstanding")
    if v >= mean + sd:
        return ("👁️ ✅ Above Average", "tag-above")
    if v >= mean - sd:
        return ("👁️ 🟡 Average", "tag-average")
    if v >= mean - 2 * sd:
        return ("👁️ 🔸 Below Average", "tag-below")
    return ("👁️ ❌ Underperform", "tag-under")


def tag_er(v, mean, sd):
    if v >= mean + 2 * sd:
        return ("👍 🌟 Highly Engaging", "tag-highly")
    if v >= mean + sd:
        return ("👍 ✅ Engaging", "tag-engaging")
    if v >= mean - sd:
        return ("👍 🟡 Moderate", "tag-moderate")
    if v >= mean - 2 * sd:
        return ("👍 🔸 Low Engagement", "tag-low")
    return ("👍 ❌ Minimal Engagement", "tag-minimal")


def read_data(csv_path):
    rows = []
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        for i, r in enumerate(csv.DictReader(f), start=2):
            username_raw = (r.get("List") or "").strip()
            if not username_raw:
                continue
            username = username_raw.lstrip("@")

            post_views = parse_num(r.get(POST_COLS["views"]))
            reels_views = parse_num(r.get(REEL_COLS["views"]))
            tiktok_views = parse_num(r.get(TIKTOK_COLS["views"]))
            has_post = post_views is not None
            has_reels = reels_views is not None
            has_tiktok = tiktok_views is not None

            post = {}
            reels = {}
            tiktok = {}
            for k in ALL_KEYS:
                p = parse_num(r.get(POST_COLS[k]))
                rr = parse_num(r.get(REEL_COLS[k]))
                tt_col = TIKTOK_COLS[k]
                tt = parse_num(r.get(tt_col)) if tt_col else 0
                post[k] = p if p is not None else 0
                reels[k] = rr if rr is not None else 0
                tiktok[k] = tt if tt is not None else 0

            post_er = (
                calc_er(
                    post["likes"],
                    post["comments"],
                    post["shares"],
                    post["saves"],
                    post["views"],
                )
                if has_post
                else None
            )
            reels_er = (
                calc_er(
                    reels["likes"],
                    reels["comments"],
                    reels["shares"],
                    reels["saves"],
                    reels["views"],
                )
                if has_reels
                else None
            )
            tiktok_er = (
                calc_er(
                    tiktok["likes"],
                    tiktok["comments"],
                    tiktok["shares"],
                    tiktok["saves"],
                    tiktok["views"],
                )
                if has_tiktok
                else None
            )

            rows.append(
                {
                    "row": i,
                    "username": username,
                    "has_post": has_post,
                    "has_reels": has_reels,
                    "has_tiktok": has_tiktok,
                    "post": post,
                    "reels": reels,
                    "tiktok": tiktok,
                    "post_er": post_er,
                    "reels_er": reels_er,
                    "tiktok_er": tiktok_er,
                }
            )
    return rows


def top3(rows, metric):
    return sorted(rows, key=lambda x: (-x[metric], x["username"]))[:3]


def profile_link(username):
    return f"https://instagram.com/{username}"


def build_section_rows(source, metric_key, er_key, label):
    if not source:
        return [], 0.0, 0.0, 0.0, 0.0

    views_vals = [r[metric_key]["views"] for r in source]
    er_vals = [r[er_key] for r in source]
    views_mean = statistics.mean(views_vals)
    er_mean = statistics.mean(er_vals)
    views_sd = pstdev(views_vals)
    er_sd = pstdev(er_vals)

    rows = []
    for r in source:
        vt, vc = tag_views(r[metric_key]["views"], views_mean, views_sd)
        et, ec = tag_er(r[er_key], er_mean, er_sd)
        rows.append(
            {
                "username": r["username"],
                "views": r[metric_key]["views"],
                "likes": r[metric_key]["likes"],
                "comments": r[metric_key]["comments"],
                "shares": r[metric_key]["shares"],
                "reposts": r[metric_key]["reposts"],
                "saves": r[metric_key]["saves"],
                "er": r[er_key],
                "views_tag": vt,
                "views_class": vc,
                "er_tag": et,
                "er_class": ec,
                "label": label,
            }
        )

    rows.sort(key=lambda x: (-x["views"], x["username"]))
    return rows, views_mean, er_mean, views_sd, er_sd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="./raw.csv",
    )
    parser.add_argument(
        "--output",
        default="./index.html",
    )
    args = parser.parse_args()

    rows = read_data(Path(args.input))
    if not rows:
        raise SystemExit("No rows found.")

    post_source = [r for r in rows if r["has_post"]]
    reels_source = [r for r in rows if r["has_reels"]]
    tiktok_source = [r for r in rows if r["has_tiktok"]]

    post_rows, post_views_mean, post_er_mean, post_views_sd, post_er_sd = (
        build_section_rows(post_source, "post", "post_er", "Posts")
    )
    reels_rows, reels_views_mean, reels_er_mean, reels_views_sd, reels_er_sd = (
        build_section_rows(reels_source, "reels", "reels_er", "Reels")
    )
    tiktok_rows, tiktok_views_mean, tiktok_er_mean, tiktok_views_sd, tiktok_er_sd = (
        build_section_rows(tiktok_source, "tiktok", "tiktok_er", "TikTok")
    )

    total_kols = len(rows)
    post_kols = len(post_rows)
    reels_kols = len(reels_rows)
    tiktok_kols = len(tiktok_rows)

    def totals(source, fmt):
        return {k: sum(r[fmt][k] for r in source) for k in ALL_KEYS}

    pt = totals(post_source, "post")
    rt = totals(reels_source, "reels")
    tt = totals(tiktok_source, "tiktok")
    pt_eng = pt["likes"] + pt["comments"] + pt["shares"] + pt["saves"]
    rt_eng = rt["likes"] + rt["comments"] + rt["shares"] + rt["saves"]
    tt_eng = tt["likes"] + tt["comments"] + tt["shares"] + tt["saves"]
    combined_eng = pt_eng + rt_eng + tt_eng

    post_avg_views = pt["views"] / post_kols if post_kols else 0
    reels_avg_views = rt["views"] / reels_kols if reels_kols else 0
    tiktok_avg_views = tt["views"] / tiktok_kols if tiktok_kols else 0
    post_avg_er = statistics.mean([r["er"] for r in post_rows]) if post_rows else 0
    reels_avg_er = statistics.mean([r["er"] for r in reels_rows]) if reels_rows else 0
    tiktok_avg_er = (
        statistics.mean([r["er"] for r in tiktok_rows]) if tiktok_rows else 0
    )

    reach_winner = "Reels" if rt["views"] >= pt["views"] else "Posts"
    reach_diff = abs(rt["views"] - pt["views"])
    reach_base = min(rt["views"], pt["views"]) if min(rt["views"], pt["views"]) else 1
    reach_pct = (reach_diff / reach_base) * 100
    er_winner = "Posts" if post_avg_er >= reels_avg_er else "Reels"

    post_top_views = top3(post_rows, "views")
    post_top_comments = top3(post_rows, "comments")
    post_top_saves = top3(post_rows, "saves")
    reels_top_views = top3(reels_rows, "views")
    reels_top_comments = top3(reels_rows, "comments")
    reels_top_saves = top3(reels_rows, "saves")
    tiktok_top_views = top3(tiktok_rows, "views")
    tiktok_top_comments = top3(tiktok_rows, "comments")
    tiktok_top_saves = top3(tiktok_rows, "saves")

    def top_html(rows3, metric, link=True):
        out = []
        for i, r in enumerate(rows3, start=1):
            username_html = (
                f'<a href="{html.escape(profile_link(r["username"]))}" target="_blank" rel="noopener noreferrer">{html.escape(r["username"])}</a>'
                if link
                else html.escape(r["username"])
            )
            out.append(
                f"""
                <div class="top3-item">
                  <div class="rank-badge rank-{i}">{i}</div>
                  <div class="top3-username">{username_html}</div>
                  <div class="top3-val">{nfmt(r[metric])}</div>
                </div>
                """
            )
        return "".join(out)

    def table_html(rowsx, link=True):
        out = []
        for r in rowsx:
            username_html = (
                f'<a href="{html.escape(profile_link(r["username"]))}" target="_blank" rel="noopener noreferrer">{html.escape(r["username"])}</a>'
                if link
                else html.escape(r["username"])
            )
            out.append(
                f"""
                <tr>
                  <td>{username_html}</td>
                  <td class="num">{nfmt(r['views'])}</td>
                  <td class="num">{nfmt(r['likes'])}</td>
                  <td>{nfmt(r['comments'])}</td>
                  <td>{nfmt(r['shares'])}</td>
                  <td>{nfmt(r['reposts'])}</td>
                  <td>{nfmt(r['saves'])}</td>
                  <td class="er">{pfmt(r['er'])}</td>
                  <td><span class="tag {r['views_class']}">{html.escape(r['views_tag'])}</span></td>
                  <td><span class="tag {r['er_class']}">{html.escape(r['er_tag'])}</span></td>
                </tr>
                """
            )
        return "".join(out)

    output = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ZUS Coffee</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=DM+Sans:wght@300;400;500;600&family=Prompt:wght@500;600;700&display=swap" rel="stylesheet">
<style>
  :root {{
    --zus-blue: #2F3F8F; --zus-blue-soft: #4D5FB5; --zus-blue-pale: #E8ECFF; --bg: #F6F8FF;
    --ink: #111C44; --ink-muted: #3D497E; --ink-soft: #6471A6; --deep: #1F2B66;
    --reel: #3752C8; --reel-light: #E8EDFF; --post: #2E3E8E; --post-light: #E3E9FF;
    --tiktok: #111111; --tiktok-light: #F1F1F1;
    --border: rgba(47,63,143,0.22); --shadow: 0 4px 28px rgba(31,43,102,0.12);
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'DM Sans', sans-serif; background: var(--bg); color: var(--ink); font-size: 14px; line-height: 1.6; }}
  .report-header {{ background: var(--zus-blue); color: white; padding: 56px 64px 40px; position: relative; overflow: hidden; }}
  .report-header::after {{ content: 'ZUS'; position: absolute; bottom: -20px; right: 40px; font-family: 'Playfair Display', serif; font-size: 180px; font-weight: 900; color: rgba(255,255,255,0.09); letter-spacing: -4px; }}
  .header-tag {{ font-size: 11px; font-weight: 600; letter-spacing: 3px; text-transform: uppercase; color: #CBD5FF; margin-bottom: 14px; }}
  .header-title {{ font-family: 'Playfair Display', serif; font-size: 44px; font-weight: 900; line-height: 1.1; margin-bottom: 8px; }}
  .header-sub {{ font-size: 16px; font-weight: 300; color: rgba(255,255,255,0.8); margin-bottom: 24px; }}
  .header-meta {{ display: flex; gap: 28px; flex-wrap: wrap; }}
  .meta-item {{ display: flex; flex-direction: column; gap: 2px; }}
  .meta-label {{ font-size: 10px; letter-spacing: 2px; text-transform: uppercase; color: #CBD5FF; font-weight: 600; }}
  .meta-value {{ font-size: 14px; font-weight: 500; color: rgba(255,255,255,0.92); }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 42px 30px; }}
  .section {{ margin-bottom: 48px; }}
  .section-title {{ font-family: 'Playfair Display', serif; font-size: 27px; font-weight: 700; margin-bottom: 20px; color: var(--deep); }}
  .overview-grid {{ display: grid; grid-template-columns: 1fr; gap: 16px; margin-bottom: 20px; }}
  .overview-grid-2 {{ grid-template-columns: 1fr; }}
  .overview-grid-3 {{ grid-template-columns: repeat(3, 1fr); }}
  .stat-card {{ background: white; border: 1px solid var(--border); border-radius: 12px; padding: 22px 20px; box-shadow: var(--shadow); }}
  .stat-card-total {{
    background: linear-gradient(135deg, #F2F5FF 0%, #FFFFFF 100%);
    border: 2px solid #6F83E8;
    box-shadow: 0 10px 30px rgba(47, 63, 143, 0.2);
    transform: translateY(-2px);
  }}
  .stat-num {{ font-family: 'Prompt', sans-serif; font-size: 34px; font-weight: 700; color: var(--deep); line-height: 1; margin-bottom: 6px; }}
  .stat-label {{ font-size: 12px; font-weight: 500; color: var(--ink-soft); }}
  .stat-sublabel {{ font-size: 11px; color: var(--ink-soft); margin-top: 6px; }}
  .stat-badge {{ display: inline-block; font-size: 10px; font-weight: 700; letter-spacing: 1px; padding: 2px 8px; border-radius: 20px; margin-bottom: 10px; }}
  .badge-post {{ background: var(--post-light); color: var(--post); }}
  .badge-reel {{ background: var(--reel-light); color: var(--reel); }}
  .badge-tiktok {{ background: var(--tiktok-light); color: var(--tiktok); }}
  .badge-total {{ background: var(--zus-blue-pale); color: var(--zus-blue); }}
  .mobile-tooltip-triggers {{ display: none; margin-top: 10px; gap: 8px; flex-wrap: wrap; }}
  .mobile-tooltip-btn {{ border: 1px solid #B8C4F8; background: #fff; color: var(--zus-blue); border-radius: 999px; padding: 5px 10px; font-size: 11px; font-weight: 600; cursor: pointer; }}
  .mobile-tooltip {{ display: none; margin-top: 8px; background: #fff; border: 1px solid #D6DFFF; border-radius: 10px; padding: 10px; font-size: 11px; color: var(--ink-muted); line-height: 1.5; }}
  .mobile-tooltip.show {{ display: block; }}
  .compare-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }}
  .compare-card {{ border-radius: 14px; padding: 24px; border: 1.5px solid; background: white; }}
  .compare-card.posts {{ border-color: rgba(46,62,142,0.36); }}
  .compare-card.reels {{ border-color: rgba(55,82,200,0.36); }}
  .compare-card.tiktok {{ border-color: rgba(17,17,17,0.24); }}
  .compare-title {{ font-family: 'Playfair Display', serif; font-size: 20px; font-weight: 700; margin-bottom: 14px; }}
  .compare-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px dashed var(--border); font-size: 13px; }}
  .compare-row:last-child {{ border: none; }}
  .compare-row-label {{ color: var(--ink-muted); font-weight: 500; }}
  .compare-row-val {{ font-weight: 700; color: var(--deep); font-size: 14px; }}
  .verdict {{ margin-top: 20px; padding: 16px 18px; background: var(--zus-blue-pale); border-left: 4px solid var(--zus-blue); border-radius: 10px; font-size: 13px; color: var(--deep); }}
  .highlights-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }}
  .highlight-section-title {{ font-size: 13px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 14px; }}
  .top3-group {{ margin-bottom: 16px; }}
  .top3-label {{ font-size: 11px; font-weight: 600; color: var(--ink-soft); text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px; }}
  .top3-list {{ display: flex; flex-direction: column; gap: 8px; }}
  .top3-item {{ display: flex; align-items: center; gap: 10px; background: white; border-radius: 8px; padding: 9px 12px; border: 1px solid var(--border); }}
  .rank-badge {{ width: 22px; height: 22px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; }}
  .rank-1 {{ background: #FFD700; color: #5A3800; }} .rank-2 {{ background: #C0C0C0; color: #333; }} .rank-3 {{ background: #CD7F32; color: #fff; }}
  .top3-username {{ font-weight: 600; font-size: 13px; flex: 1; }} .top3-val {{ font-family: 'Prompt', sans-serif; font-weight: 700; font-size: 15px; }}
  .table-wrapper {{ overflow-x: auto; border-radius: 12px; box-shadow: var(--shadow); background: white; margin-bottom: 24px; }}
  table {{ width: 100%; border-collapse: collapse; background: white; }}
  thead tr {{ background: var(--zus-blue); color: rgba(255,255,255,0.92); }}
  th {{ padding: 11px 10px; font-size: 10.5px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; text-align: center; white-space: nowrap; }}
  th.sortable {{ cursor: pointer; user-select: none; }}
  th.sortable:hover {{ background: var(--zus-blue-soft); }}
  th.sortable.active {{ background: #24357E; }}
  th:first-child, td:first-child {{ text-align: left; padding-left: 16px; }}
  tbody tr {{ border-bottom: 1px solid rgba(47,63,143,0.1); }}
  td {{ padding: 10px 10px; font-size: 12.5px; text-align: center; color: var(--ink-muted); }}
  td.num {{ font-family: 'Prompt', sans-serif; font-weight: 700; color: var(--deep); }}
  td.er {{ font-weight: 700; color: var(--deep); }}
  td a {{ color: var(--zus-blue); text-decoration: none; font-weight: 600; }}
  td a:hover {{ text-decoration: underline; }}
  .tag {{ display: inline-flex; align-items: center; padding: 3px 9px; border-radius: 20px; font-size: 10.5px; font-weight: 700; white-space: nowrap; }}
  .tag-outstanding {{ background: #EEF2FF; color: #1F2B66; }} .tag-above {{ background: #DFE6FF; color: #22307A; }} .tag-average {{ background: #F0F2FF; color: #4D5FB5; }}
  .tag-below {{ background: #FFF0E8; color: #A24E1E; }} .tag-under {{ background: #FCE4E4; color: #8B1010; }} .tag-highly {{ background: #E5EAFF; color: #25358B; }}
  .tag-engaging {{ background: #EAF0FF; color: #2A3E9D; }} .tag-moderate {{ background: #F0F2FF; color: #4D5FB5; }} .tag-low {{ background: #FFF0E8; color: #A24E1E; }} .tag-minimal {{ background: #FCE4E4; color: #8B1010; }}
  .appendix-note {{ background: white; border: 1px solid var(--border); border-radius: 10px; padding: 16px 18px; font-size: 12px; color: var(--ink-soft); margin-bottom: 16px; }}
  .table-tabs {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 14px; }}
  .table-tab-btn {{ border: 1px solid var(--border); background: white; color: var(--ink-muted); border-radius: 999px; padding: 8px 14px; font-size: 12px; font-weight: 700; cursor: pointer; transition: all 0.2s ease; }}
  .table-tab-btn:hover {{ border-color: var(--zus-blue-soft); color: var(--deep); }}
  .table-tab-btn.active {{ color: white; border-color: transparent; box-shadow: var(--shadow); }}
  .table-tab-btn:focus,
  .table-tab-btn:focus-visible {{ color: white; outline: none; }}
  .table-tab-btn[data-tab-target="post-table"] {{ background: #F4F6FF; border-color: #C9D3FF; }}
  .table-tab-btn[data-tab-target="reel-table"] {{ background: #EEF2FF; border-color: #C4D0FF; }}
  .table-tab-btn[data-tab-target="tiktok-table"] {{ background: #F5F5F5; border-color: #D6D6D6; }}
  .table-tab-btn.active[data-tab-target="post-table"] {{ background: var(--post); }}
  .table-tab-btn.active[data-tab-target="reel-table"] {{ background: var(--reel); }}
  .table-tab-btn.active[data-tab-target="tiktok-table"] {{ background: var(--tiktok); }}
  .table-panel {{ display: none; }}
  .table-panel.active {{ display: block; }}
  footer {{ background: var(--zus-blue); color: rgba(255,255,255,0.6); text-align: center; padding: 20px; font-size: 11px; }}
  @media (min-width: 768px) {{
    .overview-grid {{ grid-template-columns: repeat(4, 1fr); }}
    .overview-grid-2 {{ grid-template-columns: repeat(4, 1fr); }}
  }}
  @media (max-width: 800px) {{
    .report-header {{ padding: 32px 20px; }}
    .container {{ padding: 24px 12px; }}
    .overview-grid, .overview-grid-2, .overview-grid-3, .compare-grid, .highlights-grid {{ grid-template-columns: 1fr; }}
    .overview-grid .stat-card-post,
    .overview-grid .stat-card-reel,
    .overview-grid .stat-card-tiktok,
    .overview-grid-3 .stat-card-post,
    .overview-grid-3 .stat-card-reel,
    .overview-grid-3 .stat-card-tiktok,
    .overview-grid-2 .stat-card-post,
    .overview-grid-2 .stat-card-reel,
    .overview-grid-2 .stat-card-tiktok {{ display: none; }}
    .mobile-tooltip-triggers {{ display: flex; }}
  }}
</style>
</head>
<body>
<div class="report-header">
  <div class="header-tag">KOL Campaign Report</div>
  <div class="header-title">ZUS Coffee</div>
  <div class="header-sub">Instagram Influencer Performance Report</div>
  <div class="header-meta">
    <div class="meta-item"><span class="meta-label">Platform</span><span class="meta-value">Instagram</span></div>
    <div class="meta-item"><span class="meta-label">Status</span><span class="meta-value">All Done ✓</span></div>
    <div class="meta-item"><span class="meta-label">KOL Rows</span><span class="meta-value">{nfmt(total_kols)}</span></div>
    <div class="meta-item"><span class="meta-label">Post Rows</span><span class="meta-value">{nfmt(post_kols)}</span></div>
    <div class="meta-item"><span class="meta-label">Reel Rows</span><span class="meta-value">{nfmt(reels_kols)}</span></div>
    <div class="meta-item"><span class="meta-label">TikTok Rows</span><span class="meta-value">{nfmt(tiktok_kols)}</span></div>
  </div>
</div>
<div class="container">
  <div class="section">
    <div class="section-title">Campaign Overview</div>
    <div class="overview-grid overview-grid-2">
      <div class="stat-card stat-card-post"><div class="stat-badge badge-post">📷 Posts</div><div class="stat-num">{nfmt(pt['views'])}</div><div class="stat-label">Total Post Views</div><div class="stat-sublabel">Across {nfmt(post_kols)} KOL rows with Post data</div></div>
      <div class="stat-card stat-card-reel"><div class="stat-badge badge-reel">🎬 Reels</div><div class="stat-num">{nfmt(rt['views'])}</div><div class="stat-label">Total Reel Views</div><div class="stat-sublabel">Across {nfmt(reels_kols)} KOL rows with Reels data</div></div>
      <div class="stat-card stat-card-tiktok"><div class="stat-badge badge-tiktok">🎵 TikTok</div><div class="stat-num">{nfmt(tt['views'])}</div><div class="stat-label">Total TikTok Views</div><div class="stat-sublabel">Across {nfmt(tiktok_kols)} KOL rows with TikTok data</div></div>
      <div class="stat-card stat-card-total"><div class="stat-badge badge-total">📊 Total</div><div class="stat-num" style="color:var(--zus-blue)">{nfmt(pt['views'] + rt['views'] + tt['views'])}</div><div class="stat-label">Combined Total Views</div><div class="stat-sublabel">Posts + Reels + TikTok</div><div class="mobile-tooltip-triggers"><button type="button" class="mobile-tooltip-btn" data-tooltip-target="post-tooltip">Post Stats</button><button type="button" class="mobile-tooltip-btn" data-tooltip-target="reel-tooltip">Reel Stats</button><button type="button" class="mobile-tooltip-btn" data-tooltip-target="tiktok-tooltip">TikTok Stats</button></div><div id="post-tooltip" class="mobile-tooltip"><strong>Posts</strong><br>Views: {nfmt(pt['views'])}<br>Engagement: {nfmt(pt_eng)}</div><div id="reel-tooltip" class="mobile-tooltip"><strong>Reels</strong><br>Views: {nfmt(rt['views'])}<br>Engagement: {nfmt(rt_eng)}</div><div id="tiktok-tooltip" class="mobile-tooltip"><strong>TikTok</strong><br>Views: {nfmt(tt['views'])}<br>Engagement: {nfmt(tt_eng)}</div></div>
    </div>
    <div class="overview-grid overview-grid-2">
      <div class="stat-card stat-card-post"><div class="stat-badge badge-post">📷 Post Engagement</div><div class="stat-num">{nfmt(pt_eng)}</div><div class="stat-label">Likes + Comments + Shares + Saves</div><div class="stat-sublabel">Likes {nfmt(pt['likes'])} · Comments {nfmt(pt['comments'])} · Shares {nfmt(pt['shares'])} · Saves {nfmt(pt['saves'])}</div></div>
      <div class="stat-card stat-card-reel"><div class="stat-badge badge-reel">🎬 Reel Engagement</div><div class="stat-num">{nfmt(rt_eng)}</div><div class="stat-label">Likes + Comments + Shares + Saves</div><div class="stat-sublabel">Likes {nfmt(rt['likes'])} · Comments {nfmt(rt['comments'])} · Shares {nfmt(rt['shares'])} · Saves {nfmt(rt['saves'])}</div></div>
      <div class="stat-card stat-card-tiktok"><div class="stat-badge badge-tiktok">🎵 TikTok Engagement</div><div class="stat-num">{nfmt(tt_eng)}</div><div class="stat-label">Likes + Comments + Shares + Saves</div><div class="stat-sublabel">Likes {nfmt(tt['likes'])} · Comments {nfmt(tt['comments'])} · Shares {nfmt(tt['shares'])} · Saves {nfmt(tt['saves'])}</div></div>
      <div class="stat-card stat-card-total"><div class="stat-badge badge-total">🔥 Combined</div><div class="stat-num" style="color:var(--zus-blue)">{nfmt(combined_eng)}</div><div class="stat-label">Combined Engagement</div><div class="stat-sublabel">Post + Reel + TikTok Engagement</div><div class="mobile-tooltip-triggers"><button type="button" class="mobile-tooltip-btn" data-tooltip-target="post-engagement-tooltip">Post Stats</button><button type="button" class="mobile-tooltip-btn" data-tooltip-target="reel-engagement-tooltip">Reel Stats</button><button type="button" class="mobile-tooltip-btn" data-tooltip-target="tiktok-engagement-tooltip">TikTok Stats</button></div><div id="post-engagement-tooltip" class="mobile-tooltip"><strong>Post Engagement</strong><br>Total: {nfmt(pt_eng)}<br>Likes: {nfmt(pt['likes'])} · Comments: {nfmt(pt['comments'])}<br>Shares: {nfmt(pt['shares'])} · Saves: {nfmt(pt['saves'])}</div><div id="reel-engagement-tooltip" class="mobile-tooltip"><strong>Reel Engagement</strong><br>Total: {nfmt(rt_eng)}<br>Likes: {nfmt(rt['likes'])} · Comments: {nfmt(rt['comments'])}<br>Shares: {nfmt(rt['shares'])} · Saves: {nfmt(rt['saves'])}</div><div id="tiktok-engagement-tooltip" class="mobile-tooltip"><strong>TikTok Engagement</strong><br>Total: {nfmt(tt_eng)}<br>Likes: {nfmt(tt['likes'])} · Comments: {nfmt(tt['comments'])}<br>Shares: {nfmt(tt['shares'])} · Saves: {nfmt(tt['saves'])}</div></div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Posts vs. Reels Performance</div>
    <div class="compare-grid">
      <div class="compare-card posts">
        <div class="compare-title" style="color:var(--post)">📷 Posts</div>
        <div class="compare-row"><span class="compare-row-label">👁️ Total Views</span><span class="compare-row-val">{nfmt(pt['views'])}</span></div>
        <div class="compare-row"><span class="compare-row-label">❤️ Total Likes</span><span class="compare-row-val">{nfmt(pt['likes'])}</span></div>
        <div class="compare-row"><span class="compare-row-label">💬 Total Comments</span><span class="compare-row-val">{nfmt(pt['comments'])}</span></div>
        <div class="compare-row"><span class="compare-row-label">↗️ Total Shares</span><span class="compare-row-val">{nfmt(pt['shares'])}</span></div>
        <div class="compare-row"><span class="compare-row-label">🔁 Total Reposts</span><span class="compare-row-val">{nfmt(pt['reposts'])}</span></div>
        <div class="compare-row"><span class="compare-row-label">💾 Total Saves</span><span class="compare-row-val">{nfmt(pt['saves'])}</span></div>
        <div class="compare-row"><span class="compare-row-label">📊 Avg. Views / KOL</span><span class="compare-row-val">{nfmt(round(post_avg_views))}</span></div>
        <div class="compare-row"><span class="compare-row-label">📈 Avg. Eng. Rate</span><span class="compare-row-val">{pfmt(post_avg_er)}</span></div>
      </div>
      <div class="compare-card reels">
        <div class="compare-title" style="color:var(--reel)">🎬 Reels</div>
        <div class="compare-row"><span class="compare-row-label">👁️ Total Views</span><span class="compare-row-val">{nfmt(rt['views'])}</span></div>
        <div class="compare-row"><span class="compare-row-label">❤️ Total Likes</span><span class="compare-row-val">{nfmt(rt['likes'])}</span></div>
        <div class="compare-row"><span class="compare-row-label">💬 Total Comments</span><span class="compare-row-val">{nfmt(rt['comments'])}</span></div>
        <div class="compare-row"><span class="compare-row-label">↗️ Total Shares</span><span class="compare-row-val">{nfmt(rt['shares'])}</span></div>
        <div class="compare-row"><span class="compare-row-label">🔁 Total Reposts</span><span class="compare-row-val">{nfmt(rt['reposts'])}</span></div>
        <div class="compare-row"><span class="compare-row-label">💾 Total Saves</span><span class="compare-row-val">{nfmt(rt['saves'])}</span></div>
        <div class="compare-row"><span class="compare-row-label">📊 Avg. Views / KOL</span><span class="compare-row-val">{nfmt(round(reels_avg_views))}</span></div>
        <div class="compare-row"><span class="compare-row-label">📈 Avg. Eng. Rate</span><span class="compare-row-val">{pfmt(reels_avg_er)}</span></div>
      </div>
      <div class="compare-card tiktok">
        <div class="compare-title" style="color:var(--tiktok)">🎵 TikTok</div>
        <div class="compare-row"><span class="compare-row-label">👁️ Total Views</span><span class="compare-row-val">{nfmt(tt['views'])}</span></div>
        <div class="compare-row"><span class="compare-row-label">❤️ Total Likes</span><span class="compare-row-val">{nfmt(tt['likes'])}</span></div>
        <div class="compare-row"><span class="compare-row-label">💬 Total Comments</span><span class="compare-row-val">{nfmt(tt['comments'])}</span></div>
        <div class="compare-row"><span class="compare-row-label">↗️ Total Shares</span><span class="compare-row-val">{nfmt(tt['shares'])}</span></div>
        <div class="compare-row"><span class="compare-row-label">🔁 Total Reposts</span><span class="compare-row-val">{nfmt(tt['reposts'])}</span></div>
        <div class="compare-row"><span class="compare-row-label">💾 Total Saves</span><span class="compare-row-val">{nfmt(tt['saves'])}</span></div>
        <div class="compare-row"><span class="compare-row-label">📊 Avg. Views / KOL</span><span class="compare-row-val">{nfmt(round(tiktok_avg_views))}</span></div>
        <div class="compare-row"><span class="compare-row-label">📈 Avg. Eng. Rate</span><span class="compare-row-val">{pfmt(tiktok_avg_er)}</span></div>
      </div>
    </div>
    <div class="verdict"><strong>Key Takeaway:</strong> {reach_winner} led reach by <strong>{nfmt(reach_diff)} views</strong> ({reach_pct:.2f}% difference), while {er_winner} delivered stronger proportional engagement per view on average.</div>
  </div>

  <div class="section">
    <div class="section-title">Top 3 Highlights</div>
    <div class="highlights-grid">
      <div>
        <div class="highlight-section-title" style="color:var(--post)">📷 Posts</div>
        <div class="top3-group"><div class="top3-label">👁️ Most Viewed</div><div class="top3-list">{top_html(post_top_views, 'views')}</div></div>
        <div class="top3-group"><div class="top3-label">💬 Most Commented</div><div class="top3-list">{top_html(post_top_comments, 'comments')}</div></div>
        <div class="top3-group"><div class="top3-label">💾 Most Saved</div><div class="top3-list">{top_html(post_top_saves, 'saves')}</div></div>
      </div>
      <div>
        <div class="highlight-section-title" style="color:var(--reel)">🎬 Reels</div>
        <div class="top3-group"><div class="top3-label">👁️ Most Viewed</div><div class="top3-list">{top_html(reels_top_views, 'views')}</div></div>
        <div class="top3-group"><div class="top3-label">💬 Most Commented</div><div class="top3-list">{top_html(reels_top_comments, 'comments')}</div></div>
        <div class="top3-group"><div class="top3-label">💾 Most Saved</div><div class="top3-list">{top_html(reels_top_saves, 'saves')}</div></div>
      </div>
      <div>
        <div class="highlight-section-title" style="color:var(--tiktok)">🎵 TikTok</div>
        <div class="top3-group"><div class="top3-label">👁️ Most Viewed</div><div class="top3-list">{top_html(tiktok_top_views, 'views', link=False)}</div></div>
        <div class="top3-group"><div class="top3-label">💬 Most Commented</div><div class="top3-list">{top_html(tiktok_top_comments, 'comments', link=False)}</div></div>
        <div class="top3-group"><div class="top3-label">💾 Most Saved</div><div class="top3-list">{top_html(tiktok_top_saves, 'saves', link=False)}</div></div>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">KOL Performance Tables</div>
    <div class="appendix-note">
      <strong>Post Benchmarks:</strong><br>
      Views Mean {nfmt(round(post_views_mean))}, SD {nfmt(round(post_views_sd))}<br>
      ER Mean {pfmt(post_er_mean)}, SD {pfmt(post_er_sd)}<br><br>
      <strong>Reels Benchmarks:</strong><br>
      Views Mean {nfmt(round(reels_views_mean))}, SD {nfmt(round(reels_views_sd))}<br>
      ER Mean {pfmt(reels_er_mean)}, SD {pfmt(reels_er_sd)}<br><br>
      <strong>TikTok Benchmarks:</strong><br>
      Views Mean {nfmt(round(tiktok_views_mean))}, SD {nfmt(round(tiktok_views_sd))}<br>
      ER Mean {pfmt(tiktok_er_mean)}, SD {pfmt(tiktok_er_sd)}
    </div>
    <div class="table-tabs">
      <button type="button" class="table-tab-btn active" data-tab-target="post-table">📷 Posts</button>
      <button type="button" class="table-tab-btn" data-tab-target="reel-table">🎬 Reels</button>
      <button type="button" class="table-tab-btn" data-tab-target="tiktok-table">🎵 TikTok</button>
    </div>
    <div id="post-table" class="table-panel active">
      <div style="margin-bottom:8px;font-size:13px;font-weight:700;color:var(--post)">📷 Posts Performance Table</div>
      <div class="table-wrapper">
        <table>
          <thead><tr><th>KOL Username</th><th>Views</th><th>Likes</th><th>Comments</th><th>Shares</th><th>Reposts</th><th>Saves</th><th>ER %</th><th>👁️ Views Tag</th><th>👍 ER Tag</th></tr></thead>
          <tbody>{table_html(post_rows)}</tbody>
        </table>
      </div>
    </div>
    <div id="reel-table" class="table-panel">
      <div style="margin-bottom:8px;font-size:13px;font-weight:700;color:var(--reel)">🎬 Reels Performance Table</div>
      <div class="table-wrapper">
        <table>
          <thead><tr><th>KOL Username</th><th>Views</th><th>Likes</th><th>Comments</th><th>Shares</th><th>Reposts</th><th>Saves</th><th>ER %</th><th>👁️ Views Tag</th><th>👍 ER Tag</th></tr></thead>
          <tbody>{table_html(reels_rows)}</tbody>
        </table>
      </div>
    </div>
    <div id="tiktok-table" class="table-panel">
      <div style="margin-bottom:8px;font-size:13px;font-weight:700;color:var(--tiktok)">🎵 TikTok Performance Table</div>
      <div class="table-wrapper">
        <table>
          <thead><tr><th>KOL Username</th><th>Views</th><th>Likes</th><th>Comments</th><th>Shares</th><th>Reposts</th><th>Saves</th><th>ER %</th><th>👁️ Views Tag</th><th>👍 ER Tag</th></tr></thead>
          <tbody>{table_html(tiktok_rows, link=False)}</tbody>
        </table>
      </div>
    </div>
  </div>
</div>
<footer>Prepared for <strong>ZUS Coffee</strong> · Instagram KOL Campaign Report</footer>
<script>
  document.addEventListener('DOMContentLoaded', function () {{
    var sortableColumns = ['Views', 'Likes', 'Comments', 'Shares', 'Reposts', 'Saves', 'ER %'];
    var tables = document.querySelectorAll('.table-wrapper table');

    tables.forEach(function (table) {{
      var headerCells = Array.from(table.querySelectorAll('thead th'));
      var tbody = table.querySelector('tbody');
      if (!tbody) return;

      headerCells.forEach(function (th, index) {{
        var baseLabel = th.textContent.trim();
        if (!sortableColumns.includes(baseLabel)) return;

        th.classList.add('sortable');
        th.dataset.order = '';
        th.dataset.baseLabel = baseLabel;
        th.textContent = baseLabel + ' ↕';

        th.addEventListener('click', function () {{
          var nextOrder = th.dataset.order === 'desc' ? 'asc' : 'desc';
          var rows = Array.from(tbody.querySelectorAll('tr'));

          rows.sort(function (rowA, rowB) {{
            var a = rowA.cells[index].textContent.trim().replace(/,/g, '').replace('%', '');
            var b = rowB.cells[index].textContent.trim().replace(/,/g, '').replace('%', '');
            var aNum = Number(a);
            var bNum = Number(b);
            return nextOrder === 'asc' ? aNum - bNum : bNum - aNum;
          }});

          rows.forEach(function (row) {{
            tbody.appendChild(row);
          }});

          headerCells.forEach(function (cell) {{
            if (!cell.classList.contains('sortable')) return;
            cell.classList.remove('active');
            cell.textContent = cell.dataset.baseLabel + ' ↕';
          }});

          th.classList.add('active');
          th.dataset.order = nextOrder;
          th.textContent = th.dataset.baseLabel + (nextOrder === 'asc' ? ' ↑' : ' ↓');
        }});
      }});
    }});

    document.querySelectorAll('.mobile-tooltip-btn').forEach(function (btn) {{
      btn.addEventListener('click', function () {{
        var targetId = btn.dataset.tooltipTarget;
        document.querySelectorAll('.mobile-tooltip').forEach(function (tip) {{
          if (tip.id !== targetId) tip.classList.remove('show');
        }});
        var target = document.getElementById(targetId);
        if (target) target.classList.toggle('show');
      }});
    }});

    document.querySelectorAll('.table-tab-btn').forEach(function (btn) {{
      btn.addEventListener('click', function () {{
        var targetId = btn.dataset.tabTarget;
        document.querySelectorAll('.table-tab-btn').forEach(function (tabBtn) {{
          tabBtn.classList.toggle('active', tabBtn === btn);
        }});
        document.querySelectorAll('.table-panel').forEach(function (panel) {{
          panel.classList.toggle('active', panel.id === targetId);
        }});
      }});
    }});
  }});
</script>
</body>
</html>
"""

    Path(args.output).write_text(output, encoding="utf-8")
    print(f"Generated report: {args.output}")
    print(
        f"KOL rows={total_kols}, post rows={post_kols}, reels rows={reels_kols}, tiktok rows={tiktok_kols}"
    )
    print(
        f"Post views total={pt['views']}, Reel views total={rt['views']}, TikTok views total={tt['views']}"
    )


if __name__ == "__main__":
    main()
