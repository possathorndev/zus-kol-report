#!/usr/bin/env python3
import argparse
import csv
import html
import re
import statistics
from dataclasses import dataclass
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

CANONICAL_COLUMNS = (
    ["List"]
    + [POST_COLS[k] for k in POST_COLS]
    + [REEL_COLS[k] for k in REEL_COLS]
    + [TIKTOK_COLS[k] for k in TIKTOK_COLS if TIKTOK_COLS[k]]
)

FOXTELLS_ALIASES = {
    "List": "List",
    "Tiktok Channel": "List",
    # Some Foxtells/Sheets exports lose names for cols 1–16 → Column 1/2/3 = NO./Status/List
    "Column 3": "List",
    "Reels - View": "IG - View (Reels)",
    "Reels - Like": "IG - Like (Reels)",
    "Reels - Comment": "IG - Comment (Reels)",
    "Reels - Share": "IG - Share (Reels)",
    "Reels - Repost": "IG - Repost (Reels)",
    "Reels - Save": "IG - Save (Reels)",
    "Tiktok - View": "TT - View",
    "Tiktok - Like": "TT - Like",
    "Tiktok - Comment": "TT - Comment",
    "Tiktok - Share": "TT - Share",
    "Tiktok - Save": "TT - Save",
}

ALL_KEYS = ["views", "likes", "comments", "shares", "reposts", "saves"]


@dataclass
class ReportPayload:
    campaign_id: str
    campaign_name: str
    total_kols: int
    post_kols: int
    reels_kols: int
    tiktok_kols: int
    has_post_data: bool
    show_campaign_column: bool
    pt: dict
    rt: dict
    tt: dict
    pt_eng: int
    rt_eng: int
    tt_eng: int
    combined_eng: int
    post_avg_views: float
    reels_avg_views: float
    tiktok_avg_views: float
    post_avg_er: float
    reels_avg_er: float
    tiktok_avg_er: float
    reach_winner: str
    reach_diff: int
    reach_pct: float
    er_winner: str
    post_top_views: list
    post_top_comments: list
    post_top_saves: list
    reels_top_views: list
    reels_top_comments: list
    reels_top_saves: list
    tiktok_top_views: list
    tiktok_top_comments: list
    tiktok_top_saves: list
    post_rows: list
    reels_rows: list
    tiktok_rows: list
    post_views_mean: float
    post_er_mean: float
    post_views_sd: float
    post_er_sd: float
    reels_views_mean: float
    reels_er_mean: float
    reels_views_sd: float
    reels_er_sd: float
    tiktok_views_mean: float
    tiktok_er_mean: float
    tiktok_views_sd: float
    tiktok_er_sd: float


def parse_num(v):
    s = (v or "").strip().replace(",", "")
    return int(s) if s.isdigit() else None


def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower())
    return s.strip("-")


def nfmt(v):
    return f"{v:,}"


def pfmt(v):
    return f"{v:.2f}%"


IG_ICON = '<img class="platform-icon" src="assets/instagram.png" alt="">'
TT_ICON = '<img class="platform-icon" src="assets/tiktok.png" alt="">'


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


def find_header_row(raw_rows):
    for i, row in enumerate(raw_rows):
        if not row:
            continue
        first = (row[0] or "").strip().upper()
        if first == "NO.":
            return i
        cells = {(c or "").strip() for c in row}
        # Foxtells metric header (incl. Sheets exports where A1 is "Column 1")
        if "Tiktok - View" in cells or "Reels - View" in cells:
            return i
    if raw_rows and (raw_rows[0][0] or "").strip() == "List":
        return 0
    raise ValueError("Could not find header row (expected NO., List, or Foxtells metrics)")


def normalize_row(row_dict):
    out = {col: "" for col in CANONICAL_COLUMNS}
    for src, dst in FOXTELLS_ALIASES.items():
        if src in row_dict and row_dict[src] is not None:
            out[dst] = row_dict[src]
    if "List" in row_dict and row_dict["List"] is not None:
        out["List"] = row_dict["List"]
    for col in CANONICAL_COLUMNS:
        if col in row_dict and row_dict[col] is not None:
            out[col] = row_dict[col]
    return out


def extract_campaign_name(raw_rows, path, brand_short):
    for row in raw_rows[:6]:
        if row and (row[0] or "").strip() == "In Process" and len(row) > 1:
            name = (row[1] or "").strip()
            if name:
                return name
    stem = path.stem
    prefix = f"{brand_short} - "
    if stem.startswith(prefix):
        return stem[len(prefix) :]
    return stem


def parse_kol_row(normalized, row_num):
    username_raw = (normalized.get("List") or "").strip()
    if not username_raw:
        return None
    username = username_raw.lstrip("@")

    post_views = parse_num(normalized.get(POST_COLS["views"]))
    reels_views = parse_num(normalized.get(REEL_COLS["views"]))
    tiktok_views = parse_num(normalized.get(TIKTOK_COLS["views"]))
    has_post = post_views is not None
    has_reels = reels_views is not None
    has_tiktok = tiktok_views is not None

    post = {}
    reels = {}
    tiktok = {}
    for k in ALL_KEYS:
        p = parse_num(normalized.get(POST_COLS[k]))
        rr = parse_num(normalized.get(REEL_COLS[k]))
        tt_col = TIKTOK_COLS[k]
        tt = parse_num(normalized.get(tt_col)) if tt_col else 0
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

    return {
        "row": row_num,
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


def read_campaign_csv(path, brand_short="ZUS"):
    path = Path(path)
    with path.open(newline="", encoding="utf-8-sig") as f:
        raw_rows = list(csv.reader(f))

    header_idx = find_header_row(raw_rows)
    headers = [(h or "").strip() for h in raw_rows[header_idx]]
    campaign_name = extract_campaign_name(raw_rows, path, brand_short)
    campaign_id = slugify(path.stem)

    rows = []
    for line_no, raw in enumerate(raw_rows[header_idx + 1 :], start=header_idx + 2):
        if not raw or not any((c or "").strip() for c in raw):
            continue
        padded = raw + [""] * max(0, len(headers) - len(raw))
        row_dict = dict(zip(headers, padded))
        normalized = normalize_row(row_dict)
        parsed = parse_kol_row(normalized, line_no)
        if parsed:
            rows.append(parsed)

    return campaign_id, campaign_name, rows


def load_campaigns(data_dir, brand_short="ZUS"):
    data_dir = Path(data_dir)
    campaigns = {}
    for path in sorted(data_dir.glob("*.csv")):
        campaign_id, campaign_name, rows = read_campaign_csv(path, brand_short)
        campaigns[campaign_id] = {
            "id": campaign_id,
            "name": campaign_name,
            "rows": rows,
        }
    return campaigns


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
        row_out = {
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
        if "campaign_name" in r:
            row_out["campaign_name"] = r["campaign_name"]
        rows.append(row_out)

    rows.sort(key=lambda x: (-x["views"], x.get("campaign_name", ""), x["username"]))
    return rows, views_mean, er_mean, views_sd, er_sd


def build_report(
    rows, campaign_id="all", campaign_name="All Campaigns", show_campaign_column=False
):
    if not rows:
        raise ValueError("No rows found.")

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
    has_post_data = post_kols > 0

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

    channel_stats = []
    if tiktok_kols:
        channel_stats.append(("TikTok", tt["views"], tiktok_avg_er))
    if reels_kols:
        channel_stats.append(("Reels", rt["views"], reels_avg_er))
    if post_kols:
        channel_stats.append(("Posts", pt["views"], post_avg_er))

    if len(channel_stats) >= 2:
        by_reach = sorted(channel_stats, key=lambda x: (-x[1], x[0]))
        reach_winner = by_reach[0][0]
        reach_diff = by_reach[0][1] - by_reach[1][1]
        reach_base = by_reach[1][1] or 1
        reach_pct = (reach_diff / reach_base) * 100
        er_winner = max(channel_stats, key=lambda x: (x[2], x[0]))[0]
    else:
        reach_winner = channel_stats[0][0] if channel_stats else ""
        reach_diff = 0
        reach_pct = 0.0
        er_winner = channel_stats[0][0] if channel_stats else ""

    return ReportPayload(
        campaign_id=campaign_id,
        campaign_name=campaign_name,
        total_kols=total_kols,
        post_kols=post_kols,
        reels_kols=reels_kols,
        tiktok_kols=tiktok_kols,
        has_post_data=has_post_data,
        show_campaign_column=show_campaign_column,
        pt=pt,
        rt=rt,
        tt=tt,
        pt_eng=pt_eng,
        rt_eng=rt_eng,
        tt_eng=tt_eng,
        combined_eng=combined_eng,
        post_avg_views=post_avg_views,
        reels_avg_views=reels_avg_views,
        tiktok_avg_views=tiktok_avg_views,
        post_avg_er=post_avg_er,
        reels_avg_er=reels_avg_er,
        tiktok_avg_er=tiktok_avg_er,
        reach_winner=reach_winner,
        reach_diff=reach_diff,
        reach_pct=reach_pct,
        er_winner=er_winner,
        post_top_views=top3(post_rows, "views"),
        post_top_comments=top3(post_rows, "comments"),
        post_top_saves=top3(post_rows, "saves"),
        reels_top_views=top3(reels_rows, "views"),
        reels_top_comments=top3(reels_rows, "comments"),
        reels_top_saves=top3(reels_rows, "saves"),
        tiktok_top_views=top3(tiktok_rows, "views"),
        tiktok_top_comments=top3(tiktok_rows, "comments"),
        tiktok_top_saves=top3(tiktok_rows, "saves"),
        post_rows=post_rows,
        reels_rows=reels_rows,
        tiktok_rows=tiktok_rows,
        post_views_mean=post_views_mean,
        post_er_mean=post_er_mean,
        post_views_sd=post_views_sd,
        post_er_sd=post_er_sd,
        reels_views_mean=reels_views_mean,
        reels_er_mean=reels_er_mean,
        reels_views_sd=reels_views_sd,
        reels_er_sd=reels_er_sd,
        tiktok_views_mean=tiktok_views_mean,
        tiktok_er_mean=tiktok_er_mean,
        tiktok_views_sd=tiktok_views_sd,
        tiktok_er_sd=tiktok_er_sd,
    )


def build_combined_report(campaigns):
    pooled = []
    for c in campaigns.values():
        for r in c["rows"]:
            pooled.append({**r, "campaign_name": c["name"]})
    return build_report(
        pooled,
        campaign_id="all",
        campaign_name="All Campaigns",
        show_campaign_column=True,
    )


def kol_username_html(username, link=True):
    if link:
        return (
            f'<a href="{html.escape(profile_link(username))}" target="_blank" '
            f'rel="noopener noreferrer">{html.escape(username)}</a>'
        )
    return html.escape(username)


def highlight_top3_rows(top_views, top_comments, top_saves, link=True):
    def metric_row(label, rows3, metric):
        entries = "".join(
            f'<div class="highlight-entry">'
            f'<span class="highlight-rank rank-{i}">{i}</span>'
            f'<span class="highlight-user">{kol_username_html(r["username"], link)}</span>'
            f'<span class="highlight-num">{nfmt(r[metric])}</span>'
            f"</div>"
            for i, r in enumerate(rows3, start=1)
        )
        return (
            f'<div class="highlight-metric">'
            f'<div class="highlight-metric-label">{label}</div>'
            f'<div class="highlight-top3">{entries}</div>'
            f"</div>"
        )

    return (
        metric_row("👁️ Most Viewed", top_views, "views")
        + metric_row("💬 Most Commented", top_comments, "comments")
        + metric_row("💾 Most Saved", top_saves, "saves")
    )


def highlight_card(
    card_class, title_color, icon, title, top_views, top_comments, top_saves, link=True
):
    return f"""<div class="compare-card {card_class}">
        <div class="compare-title" style="color:{title_color}">{icon} {title}</div>
        {highlight_top3_rows(top_views, top_comments, top_saves, link)}
      </div>"""


def table_html(rowsx, link=True, show_campaign=False):
    out = []
    for r in rowsx:
        username_html = (
            f'<a href="{html.escape(profile_link(r["username"]))}" target="_blank" rel="noopener noreferrer">{html.escape(r["username"])}</a>'
            if link
            else html.escape(r["username"])
        )
        campaign_cell = ""
        if show_campaign:
            campaign_cell = f"<td>{html.escape(r.get('campaign_name', ''))}</td>"
        out.append(
            f"""
                <tr>
                  {campaign_cell}
                  <td>{username_html}</td>
                  <td class="num">{nfmt(r["views"])}</td>
                  <td class="num">{nfmt(r["likes"])}</td>
                  <td>{nfmt(r["comments"])}</td>
                  <td>{nfmt(r["shares"])}</td>
                  <td>{nfmt(r["reposts"])}</td>
                  <td>{nfmt(r["saves"])}</td>
                  <td class="er">{pfmt(r["er"])}</td>
                  <td><span class="tag {r["views_class"]}">{html.escape(r["views_tag"])}</span></td>
                  <td><span class="tag {r["er_class"]}">{html.escape(r["er_tag"])}</span></td>
                </tr>
                """
        )
    return "".join(out)


def render_panel(r: ReportPayload, brand: str) -> str:
    sc = r.show_campaign_column
    campaign_th = "<th>Campaign</th>" if sc else ""
    post_tab_btn = ""
    post_panel = ""
    post_highlight_card = ""
    post_compare_card = ""
    post_overview_cards = ""
    post_engagement_cards = ""
    post_benchmarks = ""
    pid = r.campaign_id
    if r.has_post_data:
        post_tab_btn = f'<button type="button" class="table-tab-btn" data-tab-target="post-table-{pid}">{IG_ICON} Posts</button>'
        post_panel = f"""
    <div id="post-table-{pid}" class="table-panel">
      <div class="table-panel-title" style="color:var(--post)">{IG_ICON} Posts Performance Table</div>
      <div class="table-wrapper">
        <table>
          <thead><tr>{campaign_th}<th>KOL Username</th><th>Views</th><th>Likes</th><th>Comments</th><th>Shares</th><th>Reposts</th><th>Saves</th><th>ER %</th><th>👁️ Views Tag</th><th>👍 ER Tag</th></tr></thead>
          <tbody>{table_html(r.post_rows, show_campaign=sc)}</tbody>
        </table>
      </div>
    </div>"""
        post_highlight_card = highlight_card(
            "posts",
            "var(--post)",
            IG_ICON,
            "Posts",
            r.post_top_views,
            r.post_top_comments,
            r.post_top_saves,
        )
        post_compare_card = f"""
      <div class="compare-card posts">
        <div class="compare-title" style="color:var(--post)">{IG_ICON} Posts</div>
        <div class="compare-row"><span class="compare-row-label">👁️ Total Views</span><span class="compare-row-val">{nfmt(r.pt["views"])}</span></div>
        <div class="compare-row"><span class="compare-row-label">❤️ Total Likes</span><span class="compare-row-val">{nfmt(r.pt["likes"])}</span></div>
        <div class="compare-row"><span class="compare-row-label">💬 Total Comments</span><span class="compare-row-val">{nfmt(r.pt["comments"])}</span></div>
        <div class="compare-row"><span class="compare-row-label">↗️ Total Shares</span><span class="compare-row-val">{nfmt(r.pt["shares"])}</span></div>
        <div class="compare-row"><span class="compare-row-label">🔁 Total Reposts</span><span class="compare-row-val">{nfmt(r.pt["reposts"])}</span></div>
        <div class="compare-row"><span class="compare-row-label">💾 Total Saves</span><span class="compare-row-val">{nfmt(r.pt["saves"])}</span></div>
        <div class="compare-row"><span class="compare-row-label">📊 Avg. Views / KOL</span><span class="compare-row-val">{nfmt(round(r.post_avg_views))}</span></div>
        <div class="compare-row"><span class="compare-row-label">📈 Avg. Eng. Rate</span><span class="compare-row-val">{pfmt(r.post_avg_er)}</span></div>
      </div>"""
        post_overview_cards = f"""
      <div class="stat-card stat-card-post"><div class="stat-badge badge-post">{IG_ICON} Posts</div><div class="stat-num">{nfmt(r.pt["views"])}</div><div class="stat-label">Total Post Views</div><div class="stat-sublabel">Across {nfmt(r.post_kols)} KOL rows with Post data</div></div>"""
        post_engagement_cards = f"""
      <div class="stat-card stat-card-post"><div class="stat-badge badge-post">{IG_ICON} Post Engagement</div><div class="stat-num">{nfmt(r.pt_eng)}</div><div class="stat-label">Likes + Comments + Shares + Saves</div><div class="stat-sublabel">Likes {nfmt(r.pt["likes"])} · Comments {nfmt(r.pt["comments"])} · Shares {nfmt(r.pt["shares"])} · Saves {nfmt(r.pt["saves"])}</div></div>"""
        post_benchmarks = f"""<strong>Post Benchmarks:</strong><br>
      Views Mean {nfmt(round(r.post_views_mean))}, SD {nfmt(round(r.post_views_sd))}<br>
      ER Mean {pfmt(r.post_er_mean)}, SD {pfmt(r.post_er_sd)}<br><br>"""

    highlights_cards = (
        highlight_card(
            "tiktok",
            "var(--tiktok)",
            TT_ICON,
            "TikTok",
            r.tiktok_top_views,
            r.tiktok_top_comments,
            r.tiktok_top_saves,
            link=False,
        )
        + highlight_card(
            "reels",
            "var(--reel)",
            IG_ICON,
            "Reels",
            r.reels_top_views,
            r.reels_top_comments,
            r.reels_top_saves,
        )
        + post_highlight_card
    )

    compare_cols = (
        f"""
      <div class="compare-card tiktok">
        <div class="compare-title" style="color:var(--tiktok)">{TT_ICON} TikTok</div>
        <div class="compare-row"><span class="compare-row-label">👁️ Total Views</span><span class="compare-row-val">{nfmt(r.tt["views"])}</span></div>
        <div class="compare-row"><span class="compare-row-label">❤️ Total Likes</span><span class="compare-row-val">{nfmt(r.tt["likes"])}</span></div>
        <div class="compare-row"><span class="compare-row-label">💬 Total Comments</span><span class="compare-row-val">{nfmt(r.tt["comments"])}</span></div>
        <div class="compare-row"><span class="compare-row-label">↗️ Total Shares</span><span class="compare-row-val">{nfmt(r.tt["shares"])}</span></div>
        <div class="compare-row"><span class="compare-row-label">🔁 Total Reposts</span><span class="compare-row-val">{nfmt(r.tt["reposts"])}</span></div>
        <div class="compare-row"><span class="compare-row-label">💾 Total Saves</span><span class="compare-row-val">{nfmt(r.tt["saves"])}</span></div>
        <div class="compare-row"><span class="compare-row-label">📊 Avg. Views / KOL</span><span class="compare-row-val">{nfmt(round(r.tiktok_avg_views))}</span></div>
        <div class="compare-row"><span class="compare-row-label">📈 Avg. Eng. Rate</span><span class="compare-row-val">{pfmt(r.tiktok_avg_er)}</span></div>
      </div>
      <div class="compare-card reels">
        <div class="compare-title" style="color:var(--reel)">{IG_ICON} Reels</div>
        <div class="compare-row"><span class="compare-row-label">👁️ Total Views</span><span class="compare-row-val">{nfmt(r.rt["views"])}</span></div>
        <div class="compare-row"><span class="compare-row-label">❤️ Total Likes</span><span class="compare-row-val">{nfmt(r.rt["likes"])}</span></div>
        <div class="compare-row"><span class="compare-row-label">💬 Total Comments</span><span class="compare-row-val">{nfmt(r.rt["comments"])}</span></div>
        <div class="compare-row"><span class="compare-row-label">↗️ Total Shares</span><span class="compare-row-val">{nfmt(r.rt["shares"])}</span></div>
        <div class="compare-row"><span class="compare-row-label">🔁 Total Reposts</span><span class="compare-row-val">{nfmt(r.rt["reposts"])}</span></div>
        <div class="compare-row"><span class="compare-row-label">💾 Total Saves</span><span class="compare-row-val">{nfmt(r.rt["saves"])}</span></div>
        <div class="compare-row"><span class="compare-row-label">📊 Avg. Views / KOL</span><span class="compare-row-val">{nfmt(round(r.reels_avg_views))}</span></div>
        <div class="compare-row"><span class="compare-row-label">📈 Avg. Eng. Rate</span><span class="compare-row-val">{pfmt(r.reels_avg_er)}</span></div>
      </div>"""
        + post_compare_card
    )

    show_verdict = sum(1 for k in (r.tiktok_kols, r.reels_kols, r.post_kols) if k > 0) >= 2
    verdict = ""
    if show_verdict:
        verdict = f"""<div class="verdict"><strong>Key Takeaway:</strong> {r.reach_winner} led reach by <strong>{nfmt(r.reach_diff)} views</strong> ({r.reach_pct:.2f}% ahead of the next channel), while {r.er_winner} delivered stronger proportional engagement per view on average.</div>"""

    row_meta = []
    if r.tiktok_kols > 0:
        row_meta.append(
            f'<div class="meta-item"><span class="meta-label">TikTok Rows</span><span class="meta-value">{nfmt(r.tiktok_kols)}</span></div>'
        )
    if r.reels_kols > 0:
        row_meta.append(
            f'<div class="meta-item"><span class="meta-label">Reel Rows</span><span class="meta-value">{nfmt(r.reels_kols)}</span></div>'
        )
    if r.post_kols > 0:
        row_meta.append(
            f'<div class="meta-item"><span class="meta-label">Post Rows</span><span class="meta-value">{nfmt(r.post_kols)}</span></div>'
        )
    row_meta_html = "\n    ".join(row_meta)

    tiktok_overview_card = f"""
      <div class="stat-card stat-card-tiktok"><div class="stat-badge badge-tiktok">{TT_ICON} TikTok</div><div class="stat-num">{nfmt(r.tt["views"])}</div><div class="stat-label">Total TikTok Views</div><div class="stat-sublabel">Across {nfmt(r.tiktok_kols)} KOL rows with TikTok data</div></div>"""
    reels_overview_card = f"""
      <div class="stat-card stat-card-reel"><div class="stat-badge badge-reel">{IG_ICON} Reels</div><div class="stat-num">{nfmt(r.rt["views"])}</div><div class="stat-label">Total Reel Views</div><div class="stat-sublabel">Across {nfmt(r.reels_kols)} KOL rows with Reels data</div></div>"""
    total_overview_card = f"""
      <div class="stat-card stat-card-total"><div class="stat-badge badge-total">📊 Total</div><div class="stat-num" style="color:var(--zus-blue)">{nfmt(r.pt["views"] + r.rt["views"] + r.tt["views"])}</div><div class="stat-label">Combined Total Views</div><div class="stat-sublabel">TikTok + Reels + Posts</div><div class="mobile-tooltip-triggers"><button type="button" class="mobile-tooltip-btn" data-tooltip-target="tiktok-tooltip-{r.campaign_id}">TikTok Stats</button><button type="button" class="mobile-tooltip-btn" data-tooltip-target="reel-tooltip-{r.campaign_id}">Reel Stats</button><button type="button" class="mobile-tooltip-btn" data-tooltip-target="post-tooltip-{r.campaign_id}">Post Stats</button></div><div id="tiktok-tooltip-{r.campaign_id}" class="mobile-tooltip"><strong>TikTok</strong><br>Views: {nfmt(r.tt["views"])}<br>Engagement: {nfmt(r.tt_eng)}</div><div id="reel-tooltip-{r.campaign_id}" class="mobile-tooltip"><strong>Reels</strong><br>Views: {nfmt(r.rt["views"])}<br>Engagement: {nfmt(r.rt_eng)}</div><div id="post-tooltip-{r.campaign_id}" class="mobile-tooltip"><strong>Posts</strong><br>Views: {nfmt(r.pt["views"])}<br>Engagement: {nfmt(r.pt_eng)}</div></div>"""
    tiktok_engagement_card = f"""
      <div class="stat-card stat-card-tiktok"><div class="stat-badge badge-tiktok">{TT_ICON} TikTok Engagement</div><div class="stat-num">{nfmt(r.tt_eng)}</div><div class="stat-label">Likes + Comments + Shares + Saves</div><div class="stat-sublabel">Likes {nfmt(r.tt["likes"])} · Comments {nfmt(r.tt["comments"])} · Shares {nfmt(r.tt["shares"])} · Saves {nfmt(r.tt["saves"])}</div></div>"""
    reels_engagement_card = f"""
      <div class="stat-card stat-card-reel"><div class="stat-badge badge-reel">{IG_ICON} Reel Engagement</div><div class="stat-num">{nfmt(r.rt_eng)}</div><div class="stat-label">Likes + Comments + Shares + Saves</div><div class="stat-sublabel">Likes {nfmt(r.rt["likes"])} · Comments {nfmt(r.rt["comments"])} · Shares {nfmt(r.rt["shares"])} · Saves {nfmt(r.rt["saves"])}</div></div>"""
    combined_engagement_card = f"""
      <div class="stat-card stat-card-total"><div class="stat-badge badge-total">🔥 Combined</div><div class="stat-num" style="color:var(--zus-blue)">{nfmt(r.combined_eng)}</div><div class="stat-label">Combined Engagement</div><div class="stat-sublabel">TikTok + Reel + Post Engagement</div></div>"""

    tiktok_benchmarks = f"""<strong>TikTok Benchmarks:</strong><br>
      Views Mean {nfmt(round(r.tiktok_views_mean))}, SD {nfmt(round(r.tiktok_views_sd))}<br>
      ER Mean {pfmt(r.tiktok_er_mean)}, SD {pfmt(r.tiktok_er_sd)}<br><br>"""
    reels_benchmarks = f"""<strong>Reels Benchmarks:</strong><br>
      Views Mean {nfmt(round(r.reels_views_mean))}, SD {nfmt(round(r.reels_views_sd))}<br>
      ER Mean {pfmt(r.reels_er_mean)}, SD {pfmt(r.reels_er_sd)}<br><br>"""

    return f"""
<div class="campaign-panel" data-campaign="{html.escape(r.campaign_id)}">
<div class="report-header">
  <div class="header-tag">KOL Campaign Report</div>
  <div class="header-title">{html.escape(brand)}</div>
  <div class="header-sub">{html.escape(r.campaign_name)}</div>
  <div class="header-meta">
    <div class="meta-item"><span class="meta-label">Platform</span><span class="meta-value">Instagram</span></div>
    <div class="meta-item"><span class="meta-label">Status</span><span class="meta-value">All Done ✓</span></div>
    {row_meta_html}
  </div>
</div>
<div class="container">
  <div class="section">
    <div class="section-title">Campaign Overview</div>
    <div class="overview-grid overview-grid-2">
      {tiktok_overview_card}
      {reels_overview_card}
      {post_overview_cards}
      {total_overview_card}
    </div>
    <div class="overview-grid overview-grid-2">
      {tiktok_engagement_card}
      {reels_engagement_card}
      {post_engagement_cards}
      {combined_engagement_card}
    </div>
  </div>

  <div class="section">
    <div class="section-title">Performance by Channel</div>
    <div class="compare-grid">{compare_cols}</div>
    {verdict}
  </div>

  <div class="section">
    <div class="section-title">Top 3 Highlights</div>
    <div class="compare-grid">{highlights_cards}</div>
  </div>

  <div class="section">
    <div class="section-title">KOL Performance Tables</div>
    <div class="appendix-note">
      {tiktok_benchmarks}
      {reels_benchmarks}
      {post_benchmarks}
    </div>
    <div class="table-tabs">
      <button type="button" class="table-tab-btn active" data-tab-target="tiktok-table-{pid}">{TT_ICON} TikTok</button>
      <button type="button" class="table-tab-btn" data-tab-target="reel-table-{pid}">{IG_ICON} Reels</button>
      {post_tab_btn}
    </div>
    <div id="tiktok-table-{pid}" class="table-panel active">
      <div class="table-panel-title" style="color:var(--tiktok)">{TT_ICON} TikTok Performance Table</div>
      <div class="table-wrapper">
        <table>
          <thead><tr>{campaign_th}<th>KOL Username</th><th>Views</th><th>Likes</th><th>Comments</th><th>Shares</th><th>Reposts</th><th>Saves</th><th>ER %</th><th>👁️ Views Tag</th><th>👍 ER Tag</th></tr></thead>
          <tbody>{table_html(r.tiktok_rows, link=False, show_campaign=sc)}</tbody>
        </table>
      </div>
    </div>
    <div id="reel-table-{pid}" class="table-panel">
      <div class="table-panel-title" style="color:var(--reel)">{IG_ICON} Reels Performance Table</div>
      <div class="table-wrapper">
        <table>
          <thead><tr>{campaign_th}<th>KOL Username</th><th>Views</th><th>Likes</th><th>Comments</th><th>Shares</th><th>Reposts</th><th>Saves</th><th>ER %</th><th>👁️ Views Tag</th><th>👍 ER Tag</th></tr></thead>
          <tbody>{table_html(r.reels_rows, show_campaign=sc)}</tbody>
        </table>
      </div>
    </div>
    {post_panel}
  </div>
</div>
</div>"""


def _parse_hex(color: str) -> tuple[int, int, int]:
    color = color.strip().lstrip("#")
    if len(color) == 3:
        color = "".join(ch * 2 for ch in color)
    if len(color) != 6 or not re.fullmatch(r"[0-9a-fA-F]{6}", color):
        raise ValueError(f"Invalid hex color: #{color}")
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))


def _to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _mix_hex(a: str, b: str, t: float) -> str:
    ra, ga, ba = _parse_hex(a)
    rb, gb, bb = _parse_hex(b)
    return _to_hex(
        tuple(int(round(c1 + (c2 - c1) * t)) for c1, c2 in zip((ra, ga, ba), (rb, gb, bb)))
    )


def _rgba(hex_color: str, alpha: float) -> str:
    r, g, b = _parse_hex(hex_color)
    return f"rgba({r},{g},{b},{alpha})"


def _rgb_to_hsl(r: int, g: int, b: int) -> tuple[float, float, float]:
    r, g, b = r / 255, g / 255, b / 255
    mx, mn = max(r, g, b), min(r, g, b)
    lightness = (mx + mn) / 2
    if mx == mn:
        hue = saturation = 0.0
    else:
        delta = mx - mn
        saturation = delta / (2 - mx - mn) if lightness > 0.5 else delta / (mx + mn)
        if mx == r:
            hue = ((g - b) / delta + (6 if g < b else 0)) / 6
        elif mx == g:
            hue = ((b - r) / delta + 2) / 6
        else:
            hue = ((r - g) / delta + 4) / 6
    return hue * 360, saturation, lightness


def _hsl_to_rgb(h: float, s: float, lightness: float) -> tuple[int, int, int]:
    h = h % 360
    c = (1 - abs(2 * lightness - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = lightness - c / 2
    if h < 60:
        rp, gp, bp = c, x, 0
    elif h < 120:
        rp, gp, bp = x, c, 0
    elif h < 180:
        rp, gp, bp = 0, c, x
    elif h < 240:
        rp, gp, bp = 0, x, c
    elif h < 300:
        rp, gp, bp = x, 0, c
    else:
        rp, gp, bp = c, 0, x
    return tuple(int(round((channel + m) * 255)) for channel in (rp, gp, bp))


def _hsl_hex(h: float, s: float, lightness: float) -> str:
    return _to_hex(_hsl_to_rgb(h, s, lightness))


def _normalize_color(color: str) -> str:
    normalized = color.strip()
    if not normalized.startswith("#"):
        normalized = f"#{normalized}"
    return _to_hex(_parse_hex(normalized))


DEFAULT_THEME = {
    "primary": "#2F3F8F",
    "primary_soft": "#4D5FB5",
    "primary_pale": "#E8ECFF",
    "bg": "#F6F8FF",
    "ink": "#111C44",
    "ink_muted": "#3D497E",
    "ink_soft": "#6471A6",
    "deep": "#1F2B66",
    "reel": "#3752C8",
    "reel_light": "#E8EDFF",
    "post": "#2E3E8E",
    "post_light": "#E3E9FF",
    "tiktok": "#111111",
    "tiktok_light": "#F1F1F1",
    "header_accent": "#CBD5FF",
    "stat_gradient_start": "#F2F5FF",
    "stat_border": "#6F83E8",
    "tooltip_btn_border": "#B8C4F8",
    "tooltip_border": "#D6DFFF",
    "table_active": "#24357E",
    "tag_outstanding_bg": "#EEF2FF",
    "tag_outstanding_fg": "#1F2B66",
    "tag_above_bg": "#DFE6FF",
    "tag_above_fg": "#22307A",
    "tag_average_bg": "#F0F2FF",
    "tag_average_fg": "#4D5FB5",
    "tag_highly_bg": "#E5EAFF",
    "tag_highly_fg": "#25358B",
    "tag_engaging_bg": "#EAF0FF",
    "tag_engaging_fg": "#2A3E9D",
    "tag_moderate_bg": "#F0F2FF",
    "tag_moderate_fg": "#4D5FB5",
}


def build_theme(color: str | None = None) -> dict[str, str]:
    if not color:
        return dict(DEFAULT_THEME)

    base = _normalize_color(color)
    r, g, b = _parse_hex(base)
    hue, sat, light = _rgb_to_hsl(r, g, b)
    sat = max(sat, 0.12)
    light_brand = light >= 0.7

    if light_brand:
        # Pale brands (e.g. #eec8cb): darken primary for white text on header/footer.
        primary_l = 0.38
        primary = _hsl_hex(hue, min(sat * 0.85, 0.72), primary_l)
        primary_soft = _hsl_hex(hue, min(sat * 0.75, 0.65), primary_l + 0.12)
        primary_pale = base
        bg = _mix_hex(base, "#FFFFFF", 0.45)
    else:
        # Mid/dark brands: keep the exact brand hex as primary (pills, header, tables).
        primary = base
        primary_l = light
        primary_soft = _mix_hex(base, "#FFFFFF", 0.28)
        primary_pale = _mix_hex(base, "#FFFFFF", 0.82)
        bg = _mix_hex(base, "#FFFFFF", 0.92)

    text_l = min(primary_l, 0.32)
    deep = _hsl_hex(hue, min(sat * 0.8, 0.68), max(text_l - 0.12, 0.16))
    ink = _hsl_hex(hue, min(sat * 0.75, 0.65), max(text_l - 0.18, 0.14))
    ink_muted = _hsl_hex(hue, min(sat * 0.65, 0.58), max(text_l - 0.02, 0.22))
    ink_soft = _hsl_hex(hue, min(sat * 0.5, 0.45), max(text_l + 0.08, 0.28))
    post = _hsl_hex(hue, min(sat * 0.85, 0.7), max(text_l - 0.04, 0.2))
    reel = _hsl_hex(hue, min(sat * 0.9, 0.75), max(text_l + 0.06, 0.26))
    post_light = _mix_hex(post, "#FFFFFF", 0.88)
    reel_light = _mix_hex(reel, "#FFFFFF", 0.88)
    header_accent = _mix_hex(primary_soft, "#FFFFFF", 0.62)
    stat_gradient_start = _mix_hex(primary_pale, "#FFFFFF", 0.35)
    stat_border = primary_soft
    tooltip_btn_border = _mix_hex(primary_soft, "#FFFFFF", 0.45)
    tooltip_border = _mix_hex(primary_pale, "#FFFFFF", 0.2)
    table_active = _mix_hex(primary, "#000000", 0.18)

    return {
        "primary": primary,
        "primary_soft": primary_soft,
        "primary_pale": primary_pale,
        "bg": bg,
        "ink": ink,
        "ink_muted": ink_muted,
        "ink_soft": ink_soft,
        "deep": deep,
        "reel": reel,
        "reel_light": reel_light,
        "post": post,
        "post_light": post_light,
        "tiktok": DEFAULT_THEME["tiktok"],
        "tiktok_light": DEFAULT_THEME["tiktok_light"],
        "header_accent": header_accent,
        "stat_gradient_start": stat_gradient_start,
        "stat_border": stat_border,
        "tooltip_btn_border": tooltip_btn_border,
        "tooltip_border": tooltip_border,
        "table_active": table_active,
        "tag_outstanding_bg": _mix_hex(primary_pale, "#FFFFFF", 0.15),
        "tag_outstanding_fg": deep,
        "tag_above_bg": _mix_hex(primary_pale, primary_soft, 0.35),
        "tag_above_fg": _hsl_hex(hue, min(sat * 0.8, 0.68), max(primary_l - 0.08, 0.2)),
        "tag_average_bg": _mix_hex(primary_pale, "#FFFFFF", 0.25),
        "tag_average_fg": primary_soft,
        "tag_highly_bg": _mix_hex(primary_pale, primary_soft, 0.2),
        "tag_highly_fg": _hsl_hex(hue, min(sat * 0.85, 0.72), max(primary_l - 0.04, 0.22)),
        "tag_engaging_bg": _mix_hex(primary_pale, primary_soft, 0.28),
        "tag_engaging_fg": _hsl_hex(hue, min(sat * 0.85, 0.72), max(primary_l, 0.26)),
        "tag_moderate_bg": _mix_hex(primary_pale, "#FFFFFF", 0.25),
        "tag_moderate_fg": primary_soft,
    }


def generate_html(reports, brand, brand_short, theme=None):
    theme = theme or build_theme()
    t = theme
    # Escape for use inside a CSS single-quoted string (watermark content:)
    brand_short_css = brand_short.replace("\\", "\\\\").replace("'", "\\'")
    switcher_items = []
    if "all" in reports:
        switcher_items.append(
            '<button type="button" class="campaign-pill active" data-campaign="all">All Campaigns</button>'
        )
    for rid, rep in reports.items():
        if rid == "all":
            continue
        active = " active" if "all" not in reports and len(switcher_items) == 0 else ""
        switcher_items.append(
            f'<button type="button" class="campaign-pill{active}" data-campaign="{html.escape(rid)}">{html.escape(rep.campaign_name)}</button>'
        )
    switcher_html = "\n".join(switcher_items)

    panel_order = (["all"] if "all" in reports else []) + [
        k for k in reports if k != "all"
    ]
    panels_html = ""
    for rid in panel_order:
        panels_html += render_panel(reports[rid], brand)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(brand)}</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=DM+Sans:wght@300;400;500;600&family=Prompt:wght@500;600;700&display=swap" rel="stylesheet">
<style>
  :root {{
    --zus-blue: {t["primary"]}; --zus-blue-soft: {t["primary_soft"]}; --zus-blue-pale: {t["primary_pale"]}; --bg: {t["bg"]};
    --ink: {t["ink"]}; --ink-muted: {t["ink_muted"]}; --ink-soft: {t["ink_soft"]}; --deep: {t["deep"]};
    --reel: {t["reel"]}; --reel-light: {t["reel_light"]}; --post: {t["post"]}; --post-light: {t["post_light"]};
    --tiktok: {t["tiktok"]}; --tiktok-light: {t["tiktok_light"]};
    --border: {_rgba(t["primary"], 0.22)}; --shadow: 0 4px 28px {_rgba(t["deep"], 0.12)};
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'DM Sans', sans-serif; background: var(--bg); color: var(--ink); font-size: 14px; line-height: 1.6; }}
  .campaign-bar {{ background: white; border-bottom: 1px solid var(--border); padding: 14px 30px; position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 12px {_rgba(t["deep"], 0.08)}; }}
  .campaign-bar-inner {{ max-width: 1100px; margin: 0 auto; display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }}
  .campaign-bar-label {{ font-size: 11px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: var(--ink-soft); margin-right: 6px; }}
  .campaign-pill {{ border: 1px solid var(--border); background: white; color: var(--ink-muted); border-radius: 999px; padding: 8px 16px; font-size: 12px; font-weight: 700; cursor: pointer; transition: all 0.2s ease; }}
  .campaign-pill:hover {{ border-color: var(--zus-blue-soft); color: var(--deep); }}
  .campaign-pill.active {{ background: var(--zus-blue); color: white; border-color: var(--zus-blue); }}
  .campaign-panel {{ display: none; }}
  .campaign-panel.active {{ display: block; }}
  .report-header {{ background: var(--zus-blue); color: white; padding: 56px 64px 40px; position: relative; overflow: hidden; }}
  .report-header::after {{ content: '{brand_short_css}'; position: absolute; bottom: -20px; right: 40px; font-family: 'Playfair Display', serif; font-size: 180px; font-weight: 900; color: rgba(255,255,255,0.09); letter-spacing: -4px; }}
  .header-tag {{ font-size: 11px; font-weight: 600; letter-spacing: 3px; text-transform: uppercase; color: {t["header_accent"]}; margin-bottom: 14px; }}
  .header-title {{ font-family: 'Playfair Display', serif; font-size: 44px; font-weight: 900; line-height: 1.1; margin-bottom: 8px; }}
  .header-sub {{ font-size: 16px; font-weight: 300; color: rgba(255,255,255,0.8); margin-bottom: 24px; }}
  .header-meta {{ display: flex; gap: 28px; flex-wrap: wrap; }}
  .meta-item {{ display: flex; flex-direction: column; gap: 2px; }}
  .meta-label {{ font-size: 10px; letter-spacing: 2px; text-transform: uppercase; color: {t["header_accent"]}; font-weight: 600; }}
  .meta-value {{ font-size: 14px; font-weight: 500; color: rgba(255,255,255,0.92); }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 42px 30px; }}
  .section {{ margin-bottom: 48px; }}
  .section-title {{ font-family: 'Playfair Display', serif; font-size: 27px; font-weight: 700; margin-bottom: 20px; color: var(--deep); }}
  .overview-grid {{ display: grid; grid-template-columns: 1fr; gap: 16px; margin-bottom: 20px; }}
  .overview-grid-2 {{ grid-template-columns: 1fr; }}
  .overview-grid-3 {{ grid-template-columns: repeat(3, 1fr); }}
  .stat-card {{ background: white; border: 1px solid var(--border); border-radius: 12px; padding: 22px 20px; box-shadow: var(--shadow); }}
  .stat-card-total {{
    background: linear-gradient(135deg, {t["stat_gradient_start"]} 0%, #FFFFFF 100%);
    border: 2px solid {t["stat_border"]};
    box-shadow: 0 10px 30px {_rgba(t["primary"], 0.2)};
    transform: translateY(-2px);
  }}
  .stat-num {{ font-family: 'Prompt', sans-serif; font-size: 34px; font-weight: 700; color: var(--deep); line-height: 1; margin-bottom: 6px; }}
  .stat-label {{ font-size: 12px; font-weight: 500; color: var(--ink-soft); }}
  .stat-sublabel {{ font-size: 11px; color: var(--ink-soft); margin-top: 6px; }}
  .platform-icon {{ width: 16px; height: 16px; object-fit: contain; flex-shrink: 0; }}
  .stat-badge {{ display: inline-flex; align-items: center; gap: 6px; font-size: 10px; font-weight: 700; letter-spacing: 1px; padding: 2px 8px; border-radius: 20px; margin-bottom: 10px; }}
  .badge-post {{ background: var(--post-light); color: var(--post); }}
  .badge-reel {{ background: var(--reel-light); color: var(--reel); }}
  .badge-tiktok {{ background: var(--tiktok-light); color: var(--tiktok); }}
  .badge-total {{ background: var(--zus-blue-pale); color: var(--zus-blue); }}
  .mobile-tooltip-triggers {{ display: none; margin-top: 10px; gap: 8px; flex-wrap: wrap; }}
  .mobile-tooltip-btn {{ border: 1px solid {t["tooltip_btn_border"]}; background: #fff; color: var(--zus-blue); border-radius: 999px; padding: 5px 10px; font-size: 11px; font-weight: 600; cursor: pointer; }}
  .mobile-tooltip {{ display: none; margin-top: 8px; background: #fff; border: 1px solid {t["tooltip_border"]}; border-radius: 10px; padding: 10px; font-size: 11px; color: var(--ink-muted); line-height: 1.5; }}
  .mobile-tooltip.show {{ display: block; }}
  .compare-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }}
  .compare-card {{ border-radius: 14px; padding: 24px; border: 1.5px solid; background: white; }}
  .compare-card.posts {{ border-color: {_rgba(t["post"], 0.36)}; }}
  .compare-card.reels {{ border-color: {_rgba(t["reel"], 0.36)}; }}
  .compare-card.tiktok {{ border-color: {_rgba(t["tiktok"], 0.24)}; }}
  .compare-title {{ display: inline-flex; align-items: center; gap: 6px; font-family: 'Playfair Display', serif; font-size: 20px; font-weight: 700; margin-bottom: 14px; }}
  .compare-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px dashed var(--border); font-size: 13px; }}
  .compare-row:last-child {{ border: none; }}
  .compare-row-label {{ color: var(--ink-muted); font-weight: 500; }}
  .compare-row-val {{ font-weight: 700; color: var(--deep); font-size: 14px; }}
  .verdict {{ margin-top: 20px; padding: 16px 18px; background: var(--zus-blue-pale); border-left: 4px solid var(--zus-blue); border-radius: 10px; font-size: 13px; color: var(--deep); }}
  .highlight-metric {{ padding: 8px 0; border-bottom: 1px dashed var(--border); }}
  .highlight-metric:last-child {{ border-bottom: none; }}
  .highlight-metric-label {{ color: var(--ink-muted); font-weight: 500; font-size: 13px; margin-bottom: 6px; }}
  .highlight-top3 {{ display: flex; flex-direction: column; gap: 4px; }}
  .highlight-entry {{ display: flex; align-items: center; gap: 8px; font-size: 12px; width: 100%; }}
  .highlight-user {{ flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 600; }}
  .highlight-user a {{ color: var(--zus-blue); text-decoration: none; }}
  .highlight-user a:hover {{ text-decoration: underline; }}
  .highlight-num {{ font-family: 'Prompt', sans-serif; font-weight: 700; color: var(--deep); flex-shrink: 0; font-size: 13px; }}
  .highlight-rank {{ width: 18px; height: 18px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700; flex-shrink: 0; }}
  .highlight-rank.rank-1 {{ background: #FFD700; color: #5A3800; }}
  .highlight-rank.rank-2 {{ background: #C0C0C0; color: #333; }}
  .highlight-rank.rank-3 {{ background: #CD7F32; color: #fff; }}
  .table-wrapper {{ overflow-x: auto; border-radius: 12px; box-shadow: var(--shadow); background: white; margin-bottom: 24px; }}
  table {{ width: 100%; border-collapse: collapse; background: white; }}
  thead tr {{ background: var(--zus-blue); color: rgba(255,255,255,0.92); }}
  th {{ padding: 11px 10px; font-size: 10.5px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; text-align: center; white-space: nowrap; }}
  th.sortable {{ cursor: pointer; user-select: none; }}
  th.sortable:hover {{ background: var(--zus-blue-soft); }}
  th.sortable.active {{ background: {t["table_active"]}; }}
  th:first-child, td:first-child {{ text-align: left; padding-left: 16px; }}
  tbody tr {{ border-bottom: 1px solid {_rgba(t["primary"], 0.1)}; }}
  td {{ padding: 10px 10px; font-size: 12.5px; text-align: center; color: var(--ink-muted); }}
  td.num {{ font-family: 'Prompt', sans-serif; font-weight: 700; color: var(--deep); }}
  td.er {{ font-weight: 700; color: var(--deep); }}
  td a {{ color: var(--zus-blue); text-decoration: none; font-weight: 600; }}
  td a:hover {{ text-decoration: underline; }}
  .tag {{ display: inline-flex; align-items: center; padding: 3px 9px; border-radius: 20px; font-size: 10.5px; font-weight: 700; white-space: nowrap; }}
  .tag-outstanding {{ background: {t["tag_outstanding_bg"]}; color: {t["tag_outstanding_fg"]}; }} .tag-above {{ background: {t["tag_above_bg"]}; color: {t["tag_above_fg"]}; }} .tag-average {{ background: {t["tag_average_bg"]}; color: {t["tag_average_fg"]}; }}
  .tag-below {{ background: #FFF0E8; color: #A24E1E; }} .tag-under {{ background: #FCE4E4; color: #8B1010; }} .tag-highly {{ background: {t["tag_highly_bg"]}; color: {t["tag_highly_fg"]}; }}
  .tag-engaging {{ background: {t["tag_engaging_bg"]}; color: {t["tag_engaging_fg"]}; }} .tag-moderate {{ background: {t["tag_moderate_bg"]}; color: {t["tag_moderate_fg"]}; }} .tag-low {{ background: #FFF0E8; color: #A24E1E; }} .tag-minimal {{ background: #FCE4E4; color: #8B1010; }}
  .appendix-note {{ background: white; border: 1px solid var(--border); border-radius: 10px; padding: 16px 18px; font-size: 12px; color: var(--ink-soft); margin-bottom: 16px; }}
  .table-tabs {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 14px; }}
  .table-panel-title {{ display: inline-flex; align-items: center; gap: 6px; margin-bottom: 8px; font-size: 13px; font-weight: 700; }}
  .table-tab-btn {{ display: inline-flex; align-items: center; gap: 6px; border: 1px solid var(--border); background: white; color: var(--ink-muted); border-radius: 999px; padding: 8px 14px; font-size: 12px; font-weight: 700; cursor: pointer; transition: all 0.2s ease; }}
  .table-tab-btn:hover {{ border-color: var(--zus-blue-soft); color: var(--deep); }}
  .table-tab-btn.active {{ background: var(--zus-blue); color: white; border-color: var(--zus-blue); }}
  .table-tab-btn.active:focus-visible {{ color: white; outline: none; }}
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
    .overview-grid, .overview-grid-2, .overview-grid-3, .compare-grid {{ grid-template-columns: 1fr; }}
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
<div class="campaign-bar">
  <div class="campaign-bar-inner">
    <span class="campaign-bar-label">Campaign</span>
    {switcher_html}
  </div>
</div>
{panels_html}
<footer>Prepared for <strong>{html.escape(brand)}</strong> · Instagram KOL Campaign Report</footer>
<script>
  var sortableColumns = ['Views', 'Likes', 'Comments', 'Shares', 'Reposts', 'Saves', 'ER %'];

  function initPanelSort(panel) {{
    panel.querySelectorAll('.table-wrapper table').forEach(function (table) {{
      if (table.dataset.sortInit === '1') return;
      table.dataset.sortInit = '1';
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

          rows.forEach(function (row) {{ tbody.appendChild(row); }});

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
  }}

  function initPanelTabs(panel) {{
    panel.querySelectorAll('.table-tab-btn').forEach(function (btn) {{
      if (btn.dataset.tabInit === '1') return;
      btn.dataset.tabInit = '1';
      btn.addEventListener('click', function () {{
        var targetId = btn.dataset.tabTarget;
        panel.querySelectorAll('.table-tab-btn').forEach(function (tabBtn) {{
          tabBtn.classList.toggle('active', tabBtn === btn);
        }});
        panel.querySelectorAll('.table-panel').forEach(function (p) {{
          p.classList.toggle('active', p.id === targetId);
        }});
      }});
    }});
  }}

  function activateCampaign(campaignId) {{
    document.querySelectorAll('.campaign-pill').forEach(function (pill) {{
      pill.classList.toggle('active', pill.dataset.campaign === campaignId);
    }});
    document.querySelectorAll('.campaign-panel').forEach(function (panel) {{
      var active = panel.dataset.campaign === campaignId;
      panel.classList.toggle('active', active);
      if (active) {{
        initPanelSort(panel);
        initPanelTabs(panel);
      }}
    }});
  }}

  document.addEventListener('DOMContentLoaded', function () {{
    document.querySelectorAll('.campaign-pill').forEach(function (pill) {{
      pill.addEventListener('click', function () {{
        activateCampaign(pill.dataset.campaign);
      }});
    }});

    document.querySelectorAll('.mobile-tooltip-btn').forEach(function (btn) {{
      btn.addEventListener('click', function () {{
        var panel = btn.closest('.campaign-panel');
        var targetId = btn.dataset.tooltipTarget;
        panel.querySelectorAll('.mobile-tooltip').forEach(function (tip) {{
          if (tip.id !== targetId) tip.classList.remove('show');
        }});
        var target = document.getElementById(targetId);
        if (target) target.classList.toggle('show');
      }});
    }});

    var defaultCampaign = document.querySelector('.campaign-pill.active');
    activateCampaign(defaultCampaign ? defaultCampaign.dataset.campaign : 'all');
  }});
</script>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", default=None, help="Legacy single CSV (canonical raw.csv format)"
    )
    parser.add_argument(
        "--data-dir", default="./data", help="Directory of Foxtells campaign CSVs"
    )
    parser.add_argument("--output", default="./index.html")
    parser.add_argument(
        "--brand", default="ZUS Coffee", help="Full brand name (title/header/footer)"
    )
    parser.add_argument("--brand-short", default="ZUS", help="Short watermark word")
    parser.add_argument(
        "--color",
        default=None,
        help="Brand hex color (e.g. #eec8cb). Default: blue theme.",
    )
    args = parser.parse_args()

    try:
        theme = build_theme(args.color)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    reports = {}

    if args.input:
        path = Path(args.input)
        campaign_id, campaign_name, rows = read_campaign_csv(path, args.brand_short)
        reports[campaign_id] = build_report(rows, campaign_id, campaign_name)
    else:
        campaigns = load_campaigns(args.data_dir, args.brand_short)
        if not campaigns:
            raise SystemExit(f"No CSV files found in {args.data_dir}")
        for cid, cdata in campaigns.items():
            if not cdata["rows"]:
                print(f"Warning: no KOL rows in {cdata['name']} ({cid})")
            reports[cid] = build_report(cdata["rows"], cid, cdata["name"])
        reports["all"] = build_combined_report(campaigns)

    output_html = generate_html(reports, args.brand, args.brand_short, theme)
    Path(args.output).write_text(output_html, encoding="utf-8")
    print(f"Generated report: {args.output}")

    if "all" in reports:
        combined = reports["all"]
        print(
            f"Campaigns: {len(reports) - 1} (+ All Campaigns), "
            f"combined KOL rows={combined.total_kols}"
        )
        for cid, rep in reports.items():
            if cid == "all":
                continue
            print(
                f"  {rep.campaign_name} ({cid}): "
                f"KOL={rep.total_kols}, reels={rep.reels_kols}, tiktok={rep.tiktok_kols}"
            )
    else:
        rep = next(iter(reports.values()))
        print(
            f"KOL rows={rep.total_kols}, post rows={rep.post_kols}, "
            f"reels rows={rep.reels_kols}, tiktok rows={rep.tiktok_kols}"
        )


if __name__ == "__main__":
    main()
