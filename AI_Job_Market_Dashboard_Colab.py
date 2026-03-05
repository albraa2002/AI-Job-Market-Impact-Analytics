# ============================================================
#  AI BOOM & TECH JOB MARKET IMPACT DASHBOARD
#  Single-Cell Google Colab Script — Run as-is
# ============================================================

# ── 0. Install / Import ──────────────────────────────────────
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

try:
    from google.colab import files as colab_files
    IN_COLAB = True
except ImportError:
    IN_COLAB = False

# ─────────────────────────────────────────────────────────────
# STEP 1 — GENERATE REALISTIC JOB MARKET DATA (~12 000 rows)
# ─────────────────────────────────────────────────────────────
np.random.seed(42)

# Date range: Jan 2023 → Feb 2026
date_range = pd.date_range(start="2023-01-01", end="2026-02-28", freq="D")
n_days     = len(date_range)          # ≈ 1155 days

# ── Daily posting volumes with a time-shift inflection ───────
# Pre mid-2023  : Traditional dominates (70/30 split)
# Post mid-2023 : AI-Augmented spikes; Traditional stagnates
inflection = pd.Timestamp("2023-07-01")

rows = []
for d in date_range:
    days_since_inflection = max(0, (d - inflection).days)
    # growth factor for AI roles: logistic-ish curve
    ai_growth = 1 + 5.5 * (1 / (1 + np.exp(-0.012 * (days_since_inflection - 120))))

    # Base daily counts (Poisson noise)
    trad_base = max(1, int(np.random.poisson(6)))           # slow decline post-boom
    trad_decay = max(0.3, 1 - 0.0004 * days_since_inflection)
    trad_count = max(1, int(np.random.poisson(trad_base * trad_decay)))

    ai_count   = max(1, int(np.random.poisson(3 * ai_growth)))

    # ── Traditional roles ────────────────────────────────────
    for _ in range(trad_count):
        salary = np.random.normal(80_000, 10_000)
        salary = float(np.clip(salary, 45_000, 130_000))
        work   = np.random.choice(
            ["Remote", "Hybrid", "On-site"],
            p=[0.30, 0.40, 0.30]
        )
        rows.append({
            "Date_Posted"  : d,
            "Job_Category" : "Traditional Tech/Admin",
            "Salary_USD"   : round(salary, 2),
            "Work_Model"   : work,
        })

    # ── AI-Augmented roles ───────────────────────────────────
    for _ in range(ai_count):
        salary = np.random.normal(130_000, 18_000)
        salary = float(np.clip(salary, 80_000, 220_000))
        work   = np.random.choice(
            ["Remote", "Hybrid", "On-site"],
            p=[0.70, 0.22, 0.08]
        )
        rows.append({
            "Date_Posted"  : d,
            "Job_Category" : "AI-Augmented/Data Roles",
            "Salary_USD"   : round(salary, 2),
            "Work_Model"   : work,
        })

df = pd.DataFrame(rows)
df["Date_Posted"] = pd.to_datetime(df["Date_Posted"])

# Trim / pad to exactly ~12 000 rows
if len(df) > 12_200:
    df = df.sample(n=12_000, random_state=42).reset_index(drop=True)
elif len(df) < 11_800:
    extra = df.sample(n=12_000 - len(df), replace=True, random_state=1).copy()
    df    = pd.concat([df, extra], ignore_index=True)

df = df.sort_values("Date_Posted").reset_index(drop=True)

print(f"✅  Dataset: {len(df):,} rows | {df['Date_Posted'].min().date()} → {df['Date_Posted'].max().date()}")
print(df["Job_Category"].value_counts())

# ─────────────────────────────────────────────────────────────
# STEP 2 — KPI CALCULATIONS
# ─────────────────────────────────────────────────────────────
total_jobs     = len(df)

ai_mask        = df["Job_Category"] == "AI-Augmented/Data Roles"
trad_mask      = df["Job_Category"] == "Traditional Tech/Admin"

avg_ai_salary  = df.loc[ai_mask,   "Salary_USD"].mean()
avg_trd_salary = df.loc[trad_mask, "Salary_USD"].mean()
ai_premium_pct = ((avg_ai_salary - avg_trd_salary) / avg_trd_salary) * 100

ai_2023 = df.loc[ai_mask & (df["Date_Posted"].dt.year == 2023)].shape[0]
ai_2025 = df.loc[ai_mask & (df["Date_Posted"].dt.year == 2025)].shape[0]
ai_growth_pct = ((ai_2025 - ai_2023) / ai_2023) * 100 if ai_2023 > 0 else 0

print(f"\n📊  KPIs")
print(f"   Total Jobs Analyzed  : {total_jobs:,}")
print(f"   AI Salary Premium    : +{ai_premium_pct:.1f}%  (${avg_ai_salary:,.0f} vs ${avg_trd_salary:,.0f})")
print(f"   AI Jobs Growth 23→25 : +{ai_growth_pct:.1f}%")

# ─────────────────────────────────────────────────────────────
# STEP 3 — THREE INDEPENDENT PLOTLY FIGURES
# ─────────────────────────────────────────────────────────────

# ── Shared palette ────────────────────────────────────────────
C_BG         = "#0b0f19"
C_CARD       = "rgba(255,255,255,0.04)"
C_GRID       = "rgba(255,255,255,0.06)"
C_TEXT       = "#e2e8f0"
C_SUBTEXT    = "#94a3b8"
C_TRAD       = "#7c3aed"   # Deep Purple  → Traditional
C_AI         = "#22d3ee"   # Neon Cyan    → AI-Augmented
C_ACCENT     = "#818cf8"   # Neon Blue    → accents

FONT_FAMILY  = "IBM Plex Mono, monospace"

BASE_LAYOUT  = dict(
    paper_bgcolor = C_BG,
    plot_bgcolor  = C_BG,
    font          = dict(family=FONT_FAMILY, color=C_TEXT, size=12),
    margin        = dict(l=40, r=30, t=60, b=40),
)

# ────────────────────────────────────────
# FIG 1 — Monthly trend line chart
# ────────────────────────────────────────
monthly = (
    df.groupby([pd.Grouper(key="Date_Posted", freq="ME"), "Job_Category"])
      .size()
      .reset_index(name="count")
)

fig_trend = go.Figure()

for cat, color, dash in [
    ("Traditional Tech/Admin",   C_TRAD, "dot"),
    ("AI-Augmented/Data Roles",  C_AI,   "solid"),
]:
    sub = monthly[monthly["Job_Category"] == cat]
    fig_trend.add_trace(go.Scatter(
        x    = sub["Date_Posted"],
        y    = sub["count"],
        mode = "lines+markers",
        name = cat,
        line = dict(color=color, width=2.5, dash=dash),
        marker= dict(size=4, color=color),
        hovertemplate="<b>%{x|%b %Y}</b><br>Postings: %{y:,}<extra>"+cat+"</extra>",
    ))

# Inflection annotation — add_vline has a Plotly bug with datetime axes;
# use add_shape + add_annotation instead
fig_trend.add_shape(
    type  = "line",
    x0    = inflection.isoformat(), x1 = inflection.isoformat(),
    y0    = 0,                      y1 = 1,
    xref  = "x",   yref = "paper",
    line  = dict(color=C_ACCENT, width=1.2, dash="dash"),
)
fig_trend.add_annotation(
    x         = inflection.isoformat(),
    y         = 1,
    xref      = "x",  yref = "paper",
    text      = "⚡ GenAI Boom",
    showarrow = False,
    xanchor   = "left",
    yanchor   = "bottom",
    font      = dict(color=C_ACCENT, size=11, family=FONT_FAMILY),
    xshift    = 6,
)

fig_trend.update_layout(
    **BASE_LAYOUT,
    title        = dict(text="Monthly Job Postings by Category", font=dict(size=15, color=C_TEXT), x=0.02),
    xaxis        = dict(showgrid=False, zeroline=False, color=C_SUBTEXT, tickfont=dict(size=10)),
    yaxis        = dict(gridcolor=C_GRID, zeroline=False, color=C_SUBTEXT, tickfont=dict(size=10)),
    legend       = dict(orientation="h", y=1.12, x=0, font=dict(size=11), bgcolor="rgba(0,0,0,0)"),
    hovermode    = "x unified",
)

# ────────────────────────────────────────
# FIG 2 — Salary distribution box plot
# ────────────────────────────────────────
fig_salary = go.Figure()

BOX_FILLS = {
    "Traditional Tech/Admin":  "rgba(124, 58, 237, 0.15)",
    "AI-Augmented/Data Roles": "rgba( 34,211, 238, 0.15)",
}
for cat, color in [
    ("Traditional Tech/Admin",  C_TRAD),
    ("AI-Augmented/Data Roles", C_AI),
]:
    sub = df.loc[df["Job_Category"] == cat, "Salary_USD"]
    fig_salary.add_trace(go.Box(
        y             = sub,
        name          = cat,
        marker_color  = color,
        line_color    = color,
        fillcolor     = BOX_FILLS[cat],
        boxmean       = "sd",
        hovertemplate = "<b>%{y:$,.0f}</b><extra>"+cat+"</extra>",
    ))

fig_salary.update_layout(
    **BASE_LAYOUT,
    title  = dict(text="Salary Distribution (USD)", font=dict(size=15, color=C_TEXT), x=0.02),
    xaxis  = dict(showgrid=False, color=C_SUBTEXT, tickfont=dict(size=10)),
    yaxis  = dict(gridcolor=C_GRID, zeroline=False, color=C_SUBTEXT,
                  tickprefix="$", tickformat=",", tickfont=dict(size=10)),
    legend = dict(orientation="h", y=1.12, x=0, font=dict(size=11), bgcolor="rgba(0,0,0,0)"),
)

# ────────────────────────────────────────
# FIG 3 — Work model donut (AI only)
# ────────────────────────────────────────
wm_counts = (
    df.loc[ai_mask, "Work_Model"]
      .value_counts()
      .reset_index()
)
wm_counts.columns = ["Work_Model", "count"]

DONUT_COLORS = [C_AI, C_ACCENT, C_TRAD]

fig_work_model = go.Figure(go.Pie(
    labels          = wm_counts["Work_Model"],
    values          = wm_counts["count"],
    hole            = 0.5,
    marker          = dict(colors=DONUT_COLORS,
                           line=dict(color=C_BG, width=2)),
    textfont        = dict(family=FONT_FAMILY, size=12, color=C_TEXT),
    hovertemplate   = "<b>%{label}</b><br>%{value:,} postings (%{percent})<extra></extra>",
))

fig_work_model.update_layout(
    **BASE_LAYOUT,
    title  = dict(text="Work Model — AI-Augmented Roles", font=dict(size=15, color=C_TEXT), x=0.02),
    legend = dict(orientation="h", y=-0.08, x=0.5, xanchor="center",
                  font=dict(size=11), bgcolor="rgba(0,0,0,0)"),
    annotations=[dict(
        text      = f"<b>{total_jobs:,}</b><br>Total",
        x=0.5, y=0.5,
        font      = dict(size=13, color=C_TEXT, family=FONT_FAMILY),
        showarrow = False,
    )],
)

print("✅  3 Plotly figures created.")

# ─────────────────────────────────────────────────────────────
# STEP 4 — EXPORT FIGURES TO HTML FRAGMENTS
# ─────────────────────────────────────────────────────────────
trend_html      = fig_trend.to_html(full_html=False, include_plotlyjs=False, config={"responsive": True})
salary_html     = fig_salary.to_html(full_html=False, include_plotlyjs=False, config={"responsive": True})
work_model_html = fig_work_model.to_html(full_html=False, include_plotlyjs=False, config={"responsive": True})

# ─────────────────────────────────────────────────────────────
# STEP 5 — BUILD PURE HTML/CSS DASHBOARD
# ─────────────────────────────────────────────────────────────
kpi_total   = f"{total_jobs:,}"
kpi_premium = f"+{ai_premium_pct:.1f}%"
kpi_growth  = f"+{ai_growth_pct:.1f}%"

html_dashboard = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>AI Boom & Tech Job Market Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;600;700&display=swap" rel="stylesheet"/>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  :root {{
    --bg:       #0b0f19;
    --surface:  rgba(255,255,255,0.04);
    --border:   rgba(255,255,255,0.08);
    --text:     #e2e8f0;
    --muted:    #94a3b8;
    --purple:   #7c3aed;
    --blue:     #818cf8;
    --cyan:     #22d3ee;
    --font:     'IBM Plex Mono', monospace;
    --radius:   16px;
  }}

  html, body {{
    background: var(--bg);
    color: var(--text);
    font-family: var(--font);
    min-height: 100vh;
    padding: 0;
  }}

  /* ── Animated grid background ── */
  body::before {{
    content: '';
    position: fixed; inset: 0; z-index: 0;
    background-image:
      linear-gradient(rgba(129,140,248,0.04) 1px, transparent 1px),
      linear-gradient(90deg, rgba(129,140,248,0.04) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
  }}

  .wrapper {{
    position: relative; z-index: 1;
    max-width: 1400px;
    margin: 0 auto;
    padding: 32px 24px 48px;
  }}

  /* ── Header ── */
  .header {{
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 36px;
    flex-wrap: wrap;
  }}
  .header-left .eyebrow {{
    font-size: 11px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--cyan);
    margin-bottom: 6px;
  }}
  .header-left h1 {{
    font-size: clamp(20px, 3vw, 30px);
    font-weight: 700;
    color: #fff;
    line-height: 1.2;
    letter-spacing: -0.01em;
  }}
  .header-left h1 span {{ color: var(--cyan); }}
  .header-right {{
    font-size: 11px;
    color: var(--muted);
    text-align: right;
    padding-top: 4px;
  }}
  .header-right .dot {{
    display: inline-block;
    width: 7px; height: 7px;
    border-radius: 50%;
    background: var(--cyan);
    margin-right: 6px;
    box-shadow: 0 0 8px var(--cyan);
    animation: pulse 2s ease-in-out infinite;
  }}
  @keyframes pulse {{
    0%, 100% {{ opacity: 1; transform: scale(1); }}
    50%       {{ opacity: 0.5; transform: scale(1.4); }}
  }}

  /* ── Glassmorphism card ── */
  .card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    padding: 24px;
    transition: border-color .25s, box-shadow .25s;
  }}
  .card:hover {{
    border-color: rgba(129,140,248,0.25);
    box-shadow: 0 0 28px rgba(129,140,248,0.08);
  }}

  /* ── KPI row ── */
  .kpi-row {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    margin-bottom: 20px;
  }}
  @media (max-width: 700px) {{
    .kpi-row {{ grid-template-columns: 1fr; }}
  }}

  .kpi-card {{
    position: relative;
    overflow: hidden;
    padding: 22px 24px;
  }}
  .kpi-card::after {{
    content: '';
    position: absolute;
    inset: 0;
    border-radius: var(--radius);
    opacity: 0;
    transition: opacity .3s;
  }}
  .kpi-card:hover::after {{ opacity: 1; }}

  .kpi-card.kpi-total::after   {{ background: radial-gradient(circle at top left, rgba(129,140,248,0.07), transparent 60%); }}
  .kpi-card.kpi-premium::after {{ background: radial-gradient(circle at top left, rgba(34,211,238,0.08), transparent 60%); }}
  .kpi-card.kpi-growth::after  {{ background: radial-gradient(circle at top left, rgba(124,58,237,0.08), transparent 60%); }}

  .kpi-label {{
    font-size: 10px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 10px;
  }}
  .kpi-value {{
    font-size: clamp(28px, 4vw, 40px);
    font-weight: 700;
    line-height: 1;
    letter-spacing: -0.02em;
  }}
  .kpi-value.color-blue   {{ color: var(--blue);   text-shadow: 0 0 20px rgba(129,140,248,0.5); }}
  .kpi-value.color-cyan   {{ color: var(--cyan);   text-shadow: 0 0 20px rgba(34,211,238,0.5); }}
  .kpi-value.color-purple {{ color: var(--purple); text-shadow: 0 0 20px rgba(124,58,237,0.5); }}
  .kpi-sub {{
    font-size: 11px;
    color: var(--muted);
    margin-top: 8px;
  }}
  .kpi-badge {{
    display: inline-block;
    background: rgba(34,211,238,0.12);
    color: var(--cyan);
    border: 1px solid rgba(34,211,238,0.25);
    border-radius: 4px;
    padding: 2px 7px;
    font-size: 10px;
    letter-spacing: 0.08em;
    vertical-align: middle;
    margin-left: 6px;
  }}
  .kpi-badge.purple {{
    background: rgba(124,58,237,0.12);
    color: #a78bfa;
    border-color: rgba(124,58,237,0.25);
  }}

  /* ── Chart rows ── */
  .chart-full  {{
    margin-bottom: 20px;
    padding: 12px 8px 4px;
  }}
  .chart-split {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-bottom: 20px;
  }}
  @media (max-width: 860px) {{
    .chart-split {{ grid-template-columns: 1fr; }}
  }}

  .chart-card {{
    padding: 12px 8px 4px;
    min-height: 380px;
  }}

  .chart-card .js-plotly-plot,
  .chart-full .js-plotly-plot {{
    width: 100% !important;
  }}

  /* ── Footer ── */
  .footer {{
    text-align: center;
    font-size: 11px;
    color: var(--muted);
    margin-top: 12px;
    padding-top: 20px;
    border-top: 1px solid var(--border);
    letter-spacing: 0.06em;
  }}
  .footer span {{ color: var(--cyan); }}
</style>
</head>
<body>
<div class="wrapper">

  <!-- ── Header ── -->
  <header class="header">
    <div class="header-left">
      <div class="eyebrow">Senior HR Analytics · Tech Sector Intelligence</div>
      <h1>AI Boom &amp; <span>Tech Job Market</span> Impact Dashboard</h1>
    </div>
    <div class="header-right">
      <span class="dot"></span>Live Dataset Analysis<br/>
      Jan 2023 — Feb 2026<br/>
      Generated by HR Data Intelligence
    </div>
  </header>

  <!-- ── KPI Row ── -->
  <div class="kpi-row">

    <div class="card kpi-card kpi-total">
      <div class="kpi-label">Total Jobs Analyzed</div>
      <div class="kpi-value color-blue">{kpi_total}</div>
      <div class="kpi-sub">Across all categories &amp; time periods</div>
    </div>

    <div class="card kpi-card kpi-premium">
      <div class="kpi-label">AI Salary Premium</div>
      <div class="kpi-value color-cyan">{kpi_premium}
        <span class="kpi-badge">↑ AI Edge</span>
      </div>
      <div class="kpi-sub">
        AI Avg: ${avg_ai_salary:,.0f} &nbsp;|&nbsp; Traditional Avg: ${avg_trd_salary:,.0f}
      </div>
    </div>

    <div class="card kpi-card kpi-growth">
      <div class="kpi-label">AI Jobs Growth 2023 → 2025</div>
      <div class="kpi-value color-purple">{kpi_growth}
        <span class="kpi-badge purple">↑ GenAI Boom</span>
      </div>
      <div class="kpi-sub">2023: {ai_2023:,} postings &nbsp;|&nbsp; 2025: {ai_2025:,} postings</div>
    </div>

  </div>

  <!-- ── Trend Chart (full width) ── -->
  <div class="card chart-full">
    {trend_html}
  </div>

  <!-- ── Salary + Work Model (side by side) ── -->
  <div class="chart-split">
    <div class="card chart-card">
      {salary_html}
    </div>
    <div class="card chart-card">
      {work_model_html}
    </div>
  </div>

  <!-- ── Footer ── -->
  <div class="footer">
    Built with <span>Plotly</span> · Data Intelligence Platform · AI &amp; Tech HR Analytics ©2026
  </div>

</div>
</body>
</html>"""

# ─────────────────────────────────────────────────────────────
# STEP 6 — SAVE & AUTO-DOWNLOAD
# ─────────────────────────────────────────────────────────────
OUTPUT_FILE = "AI_Job_Market_Dashboard.html"

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(html_dashboard)

size_kb = os.path.getsize(OUTPUT_FILE) / 1024
print(f"\n✅  Dashboard saved → {OUTPUT_FILE}  ({size_kb:.1f} KB)")

if IN_COLAB:
    colab_files.download(OUTPUT_FILE)
    print("⬇️  Download triggered in Colab.")
else:
    print(f"ℹ️  Not in Colab — open '{OUTPUT_FILE}' in your browser to view the dashboard.")
