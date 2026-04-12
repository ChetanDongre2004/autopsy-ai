# -*- coding: utf-8 -*-
"""Export analysis results as standalone HTML reports with score bars and radar chart."""

import json
from datetime import datetime
from typing import Dict
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

router = APIRouter()


class ReportRequest(BaseModel):
    repository: str = Field(default="Unknown Repository")
    branch: str = Field(default="main")
    results: Dict = Field(..., description="Full analysis results to export")
    report_type: str = Field(default="full", description="full, summary, security, qa")


def generate_html_report(data: ReportRequest) -> str:
    """Generate a complete standalone HTML report."""
    results = data.results
    overall = results.get("overallScore", results.get("score", "N/A"))
    grade = results.get("grade", "?")
    scores = results.get("scores", {})
    issues = results.get("issues", results.get("vulnerabilities", []))
    recs = results.get("topRecommendations", results.get("recommendations", []))
    repo_info = results.get("repoInfo", {})
    breakdown = results.get("issueBreakdown", {})
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    grade_colors = {"A": "#22c55e", "B": "#3b82f6", "C": "#eab308", "D": "#f97316", "F": "#ef4444"}
    grade_color = grade_colors.get(grade, "#888")

    score_bars = ""
    for key, val in scores.items():
        label = key.replace("_", " ").replace("C", " C").replace("Q", " Q").strip().title()
        color = "#22c55e" if val >= 80 else "#eab308" if val >= 60 else "#ef4444"
        score_bars += f"""
        <div class="score-row">
            <span class="score-label">{label}</span>
            <div class="score-track"><div class="score-fill" style="width:{val}%;background:{color};"></div></div>
            <span class="score-value">{val}</span>
        </div>"""

    issues_html = ""
    for issue in issues[:30]:
        sev = issue.get("severity", "info")
        sev_colors = {"critical": "#ef4444", "high": "#f97316", "medium": "#eab308", "low": "#3b82f6", "info": "#6b7280"}
        color = sev_colors.get(sev, "#6b7280")
        desc = issue.get("description", issue.get("what", ""))
        fix = issue.get("suggestion", issue.get("fix", issue.get("remediation", "")))
        file_path = issue.get("file", issue.get("function_name", ""))
        issues_html += f"""
        <div class="issue-card" style="border-left:3px solid {color};">
            <div class="issue-header">
                <span style="color:{color};font-weight:700;text-transform:uppercase;font-size:0.75rem;">{sev}</span>
                {f'<span class="issue-file">{file_path}</span>' if file_path else ''}
            </div>
            <p class="issue-desc">{desc}</p>
            {f'<p class="issue-fix">Fix: {fix}</p>' if fix else ''}
        </div>"""

    recs_html = ""
    for i, r in enumerate(recs[:10], 1):
        if isinstance(r, dict):
            recs_html += f'<div class="rec-item"><strong>#{i} {r.get("title", "")}</strong><p>{r.get("description", "")}</p></div>'
        else:
            recs_html += f'<div class="rec-item"><strong>#{i}</strong> {r}</div>'

    radar_data = json.dumps(list(scores.values())) if scores else "[]"
    radar_labels = json.dumps([k.replace("_", " ").title() for k in scores.keys()]) if scores else "[]"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Autopsy AI Report - {data.repository}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a0a0f;color:#e8e8f0;padding:40px 20px;max-width:1000px;margin:0 auto;}}
h1{{font-size:1.8rem;margin-bottom:4px;}}
h2{{font-size:1.1rem;margin:24px 0 12px;color:#9898b0;text-transform:uppercase;letter-spacing:1px;font-size:0.85rem;}}
.header{{text-align:center;padding:30px;border-bottom:1px solid #2a2a38;margin-bottom:24px;}}
.header .subtitle{{color:#9898b0;font-size:0.85rem;margin-top:4px;}}
.grade-ring{{width:120px;height:120px;border-radius:50%;border:6px solid {grade_color};display:flex;align-items:center;justify-content:center;flex-direction:column;margin:16px auto;}}
.grade-ring .num{{font-size:2.2rem;font-weight:800;color:{grade_color};}}
.grade-ring .lbl{{font-size:0.7rem;color:#9898b0;text-transform:uppercase;}}
.card{{background:#1e1e28;border:1px solid #2a2a38;border-radius:12px;padding:20px;margin-bottom:16px;}}
.metrics-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px;}}
.metric{{text-align:center;background:#111118;border:1px solid #2a2a38;border-radius:8px;padding:14px 8px;}}
.metric .val{{font-size:1.5rem;font-weight:800;}}
.metric .lbl{{font-size:0.68rem;color:#9898b0;text-transform:uppercase;margin-top:2px;}}
.score-row{{display:flex;align-items:center;gap:10px;margin:8px 0;}}
.score-label{{width:130px;text-align:right;font-size:0.8rem;color:#9898b0;font-weight:600;}}
.score-track{{flex:1;height:8px;background:#18181f;border-radius:4px;overflow:hidden;}}
.score-fill{{height:100%;border-radius:4px;}}
.score-value{{width:30px;font-weight:700;font-size:0.85rem;}}
.issue-card{{background:#111118;border:1px solid #2a2a38;border-radius:8px;padding:12px 14px;margin-bottom:8px;}}
.issue-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;}}
.issue-file{{font-family:monospace;font-size:0.72rem;color:#5c5c78;}}
.issue-desc{{font-size:0.82rem;color:#9898b0;margin-bottom:4px;}}
.issue-fix{{font-size:0.78rem;color:#22c55e;}}
.rec-item{{background:#111118;border:1px solid #2a2a38;border-radius:8px;padding:12px;margin-bottom:6px;font-size:0.82rem;}}
.rec-item p{{color:#9898b0;margin-top:4px;}}
.footer{{text-align:center;padding:20px;color:#5c5c78;font-size:0.75rem;margin-top:24px;border-top:1px solid #2a2a38;}}
canvas{{max-width:300px;margin:16px auto;display:block;}}
@media print{{body{{background:white;color:#1a1a2e;}} .card{{border-color:#ddd;background:#f8f8ff;}} .issue-card,.metric,.rec-item{{background:#f4f4fc;border-color:#ddd;}}}}
</style>
</head>
<body>
<div class="header">
    <h1>Autopsy AI Analysis Report</h1>
    <div class="subtitle">{data.repository} | Branch: {data.branch} | {timestamp}</div>
    <div class="grade-ring"><div class="num">{overall}</div><div class="lbl">Grade {grade}</div></div>
</div>

<div class="metrics-row">
    <div class="metric"><div class="val" style="color:#ef4444;">{breakdown.get('critical',0)}</div><div class="lbl">Critical</div></div>
    <div class="metric"><div class="val" style="color:#f97316;">{breakdown.get('high',0)}</div><div class="lbl">High</div></div>
    <div class="metric"><div class="val" style="color:#eab308;">{breakdown.get('medium',0)}</div><div class="lbl">Medium</div></div>
    <div class="metric"><div class="val" style="color:#3b82f6;">{breakdown.get('low',0)}</div><div class="lbl">Low</div></div>
</div>

<div class="card">
    <h2>Score Breakdown</h2>
    {score_bars}
</div>

<canvas id="radarChart" width="300" height="300"></canvas>

<div class="card">
    <h2>Issues ({len(issues)})</h2>
    {issues_html if issues_html else '<p style="color:#22c55e;">No issues found</p>'}
</div>

{f'<div class="card"><h2>Recommendations</h2>{recs_html}</div>' if recs_html else ''}

<div class="footer">
    Generated by Autopsy AI &mdash; AI-Powered Software Auditing Platform<br>
    {timestamp}
</div>

<script>
try {{
    const canvas = document.getElementById('radarChart');
    if (canvas) {{
        const ctx = canvas.getContext('2d');
        const data = {radar_data};
        const labels = {radar_labels};
        const cx = 150, cy = 150, r = 110;
        const n = data.length;
        if (n >= 3) {{
            ctx.strokeStyle = '#2a2a38';
            ctx.lineWidth = 1;
            for (let ring = 20; ring <= 100; ring += 20) {{
                ctx.beginPath();
                for (let i = 0; i <= n; i++) {{
                    const angle = (Math.PI * 2 * i / n) - Math.PI / 2;
                    const x = cx + (r * ring / 100) * Math.cos(angle);
                    const y = cy + (r * ring / 100) * Math.sin(angle);
                    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
                }}
                ctx.stroke();
            }}
            ctx.fillStyle = 'rgba(108,99,255,0.2)';
            ctx.strokeStyle = '#6c63ff';
            ctx.lineWidth = 2;
            ctx.beginPath();
            for (let i = 0; i <= n; i++) {{
                const idx = i % n;
                const angle = (Math.PI * 2 * idx / n) - Math.PI / 2;
                const x = cx + (r * data[idx] / 100) * Math.cos(angle);
                const y = cy + (r * data[idx] / 100) * Math.sin(angle);
                if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
            }}
            ctx.fill();
            ctx.stroke();
            ctx.fillStyle = '#9898b0';
            ctx.font = '11px sans-serif';
            ctx.textAlign = 'center';
            for (let i = 0; i < n; i++) {{
                const angle = (Math.PI * 2 * i / n) - Math.PI / 2;
                const x = cx + (r + 18) * Math.cos(angle);
                const y = cy + (r + 18) * Math.sin(angle);
                ctx.fillText(labels[i], x, y + 4);
            }}
        }}
    }}
}} catch(e) {{}}
</script>
</body>
</html>"""


@router.post("/html")
async def export_html_report(request: ReportRequest):
    """Generate and return a downloadable HTML report."""
    html = generate_html_report(request)
    return HTMLResponse(content=html, headers={
        "Content-Disposition": f'attachment; filename="autopsy-report-{request.repository.replace("/", "-")}.html"'
    })


@router.post("/preview")
async def preview_report(request: ReportRequest):
    """Preview the HTML report inline (not as download)."""
    html = generate_html_report(request)
    return HTMLResponse(content=html)
