"""
Script to generate docs/architecture.png.
Renders a crisp, modern, professional system architecture diagram.
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path


def create_architecture_diagram():
    width = 1600
    height = 1000
    bg_color = (15, 23, 42)  # Dark slate navy
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Palette
    card_bg = (30, 41, 59)
    card_border = (51, 65, 85)
    accent_blue = (59, 130, 246)
    accent_cyan = (6, 182, 212)
    accent_purple = (168, 85, 247)
    accent_green = (16, 185, 129)
    accent_amber = (245, 158, 11)
    text_white = (248, 250, 252)
    text_muted = (148, 163, 184)

    # Fonts
    try:
        title_font = ImageFont.truetype("arial.ttf", 28)
        subtitle_font = ImageFont.truetype("arial.ttf", 16)
        heading_font = ImageFont.truetype("arial.ttf", 18)
        body_font = ImageFont.truetype("arial.ttf", 14)
        mono_font = ImageFont.truetype("consolas.ttf", 13)
    except:
        title_font = ImageFont.load_default()
        subtitle_font = title_font
        heading_font = title_font
        body_font = title_font
        mono_font = title_font

    # Title header
    draw.text((60, 40), "EC2 Monitoring & Incident Analysis System", fill=text_white, font=title_font)
    draw.text(
        (60, 75),
        "Agentless SSH Remote Monitoring | Deterministic Correlation | 8-Node LangGraph + Groq LLM | Supabase PostgreSQL",
        fill=accent_cyan,
        font=subtitle_font,
    )

    # Helper: rounded box
    def draw_card(x, y, w, h, title, subtitle="", border_color=card_border, bg=card_bg):
        draw.rounded_rectangle([x, y, x + w, y + h], radius=8, fill=bg, outline=border_color, width=2)
        draw.text((x + 16, y + 14), title, fill=text_white, font=heading_font)
        if subtitle:
            draw.text((x + 16, y + 36), subtitle, fill=text_muted, font=body_font)

    # Helper: Arrow
    def draw_arrow(x1, y1, x2, y2, color=accent_blue, text=""):
        draw.line([x1, y1, x2, y2], fill=color, width=2)
        # Arrowhead
        if y2 > y1:  # Down
            draw.polygon([(x2, y2), (x2 - 5, y2 - 8), (x2 + 5, y2 - 8)], fill=color)
        elif x2 > x1:  # Right
            draw.polygon([(x2, y2), (x2 - 8, y2 - 5), (x2 - 8, y2 + 5)], fill=color)
        elif x1 > x2:  # Left
            draw.polygon([(x2, y2), (x2 + 8, y2 - 5), (x2 + 8, y2 + 5)], fill=color)

        if text:
            mid_x = (x1 + x2) // 2 + 8
            mid_y = (y1 + y2) // 2 - 8
            draw.text((mid_x, mid_y), text, fill=color, font=mono_font)

    # Column 1: Front-to-Back flow
    # 1. React Frontend
    draw_card(60, 130, 360, 120, "1. React Frontend (Vite + TS)", "Port 5173 · Status & Telemetry UI", accent_cyan)
    draw.text((76, 185), "• Real-time Dashboard (10s auto-refresh)", fill=text_muted, font=body_font)
    draw.text((76, 205), "• Strict Null Handling (formatMetric -> '-')", fill=text_muted, font=body_font)
    draw.text((76, 225), "• Time-Series Recharts (connectNulls=false)", fill=text_muted, font=body_font)

    draw_arrow(240, 250, 240, 290, accent_cyan, "HTTP / REST")

    # 2. FastAPI Backend
    draw_card(60, 290, 360, 130, "2. FastAPI Backend", "Port 8000 · Python 3.11 + Pydantic", accent_blue)
    draw.text((76, 345), "• Agentless Monitoring Lifecycle Worker", fill=text_muted, font=body_font)
    draw.text((76, 365), "• AsyncSSH Client (Private Key Auth)", fill=text_muted, font=body_font)
    draw.text((76, 385), "• Safe Command Execution & Allowlist", fill=text_muted, font=body_font)

    draw_arrow(240, 420, 240, 460, accent_blue, "SSH (:22)")

    # 3. AWS EC2 Remote Linux Host
    draw_card(60, 460, 360, 230, "3. AWS EC2 Ubuntu Instance", "Remote Linux Host (No Agent Installed)", accent_amber)
    cmds = [
        "CPU: mpstat 1 1, nproc, /proc/stat",
        "Memory: free -m (total, used, avail)",
        "Disk: df -P / (POSIX KB -> GB)",
        "Load: cat /proc/loadavg (1m, 5m, 15m)",
        "Processes: ps -eo pid,comm,%cpu,%mem",
        "Network: cat /proc/net/dev (rx, tx)",
        "Logs: journalctl -p warning..err -n 20",
        "System: hostname, uname -r, os-release",
    ]
    for i, c in enumerate(cmds):
        draw.text((76, 515 + i * 20), f"• {c}", fill=text_muted, font=mono_font)

    # Arrow from EC2 back to Backend / Ingestion
    draw_arrow(420, 560, 470, 560, accent_amber, "")
    draw.line([470, 560, 470, 350], fill=accent_amber, width=2)
    draw_arrow(470, 350, 520, 350, accent_amber, "Command Output")

    # Column 2: Data Pipeline & Processing
    # 4. Metric Normalizer & Null Safety
    draw_card(520, 130, 440, 110, "4. Metric Normalization", "Strict Null Preservation (No Fake 0s)", accent_blue)
    draw.text((536, 185), "• Distinguishes true 0.0 from uncollected (null)", fill=text_muted, font=body_font)
    draw.text((536, 205), "• Data Quality: COMPLETE | PARTIAL | FAILED", fill=text_muted, font=body_font)

    draw_arrow(740, 240, 740, 270, accent_blue, "")

    # 5. Anomaly Detection & Persistence
    draw_card(520, 270, 440, 120, "5. Deterministic Anomaly Engine", "Configurable Warning & Critical Rules", accent_amber)
    draw.text((536, 325), "• CPU (70/90%), Memory (75/90%), Disk (80/90%)", fill=text_muted, font=body_font)
    draw.text((536, 345), "• System Load relative to core count (1x / 2x cores)", fill=text_muted, font=body_font)
    draw.text((536, 365), "• Persistence Filter (N=3 consecutive samples)", fill=text_muted, font=body_font)

    draw_arrow(740, 390, 740, 420, accent_amber, "")

    # 6. Correlation Engine
    draw_card(520, 420, 440, 130, "6. Correlation & Incident Engine", "Multi-Metric Deduplication & Lifecycle", accent_purple)
    draw.text((536, 475), "• 5-min Temporal Window Correlation", fill=text_muted, font=body_font)
    draw.text((536, 495), "• Correlates CPU + Mem + Load -> ONE Incident", fill=text_muted, font=body_font)
    draw.text((536, 515), "• 4-Tier Severity: LOW | MEDIUM | HIGH | CRITICAL", fill=text_muted, font=body_font)
    draw.text((536, 535), "• Deduplication Key: Prevents duplicate INC-002", fill=text_muted, font=body_font)

    # Supabase PostgreSQL Storage
    draw_card(520, 580, 440, 110, "Database: Supabase PostgreSQL", "Schema: ec2_monitoring_working", accent_green)
    draw.text((536, 635), "• Nullable MetricSnapshots, ProcessSnapshots", fill=text_muted, font=body_font)
    draw.text((536, 655), "• Anomalies, Incidents, and IncidentAnalysis", fill=text_muted, font=body_font)

    draw_arrow(740, 550, 740, 580, accent_green, "Persist")
    draw_arrow(740, 185, 520, 185, accent_blue, "")

    # Column 3: LangGraph 8-Node Workflow & Groq
    draw_card(1020, 130, 520, 560, "7. 8-Node LangGraph + Groq Workflow", "AI Reasoning with Deterministic Fallback", accent_purple)

    nodes = [
        ("1. Collect Context", "Gathers metrics, anomalies, procs, logs"),
        ("2. Validate Evidence", "Formulates factual observed evidence points"),
        ("3. Correlate Events", "Multi-metric saturation & temporal scoring"),
        ("4. Assess Severity", "4-tier severity: LOW, MEDIUM, HIGH, CRITICAL"),
        ("5. Determine Cause", "Groq LLM (qwen/qwen3.8-27b) / Rule Fallback"),
        ("6. Recommend Actions", "Actionable Linux remediation commands"),
        ("7. Generate Summary", "Executive reasoning & narrative synthesis"),
        ("8. Validate Output", "Pydantic schema validation & verification"),
    ]

    for i, (n_title, n_desc) in enumerate(nodes):
        ny = 185 + i * 46
        box_color = accent_purple if i != 4 else accent_amber
        draw.rounded_rectangle([1040, ny, 1510, ny + 38], radius=6, fill=(45, 55, 72), outline=box_color, width=1)
        draw.text((1055, ny + 5), n_title, fill=text_white, font=heading_font)
        draw.text((1055, ny + 22), n_desc, fill=text_muted, font=body_font)
        if i < 7:
            draw.line([1275, ny + 38, 1275, ny + 46], fill=accent_purple, width=2)

    # Groq Box
    draw_card(1020, 720, 520, 100, "Groq LLM API", "Model: qwen/qwen3.8-27b (Configurable in .env)", accent_amber)
    draw.text((1036, 775), "• Strict JSON Object Output | Zero Hallucination Prompt", fill=text_muted, font=body_font)
    draw.text((1036, 795), "• Automatic Fallback to Rule Engine on Quota / Network Error", fill=text_muted, font=body_font)

    draw_arrow(1275, 690, 1275, 720, accent_amber, "Prompt")
    draw_arrow(1020, 480, 960, 480, accent_purple, "Trigger")

    # Bottom bar: Acceptance criteria
    draw.rounded_rectangle([60, 840, 1540, 960], radius=8, fill=(24, 32, 47), outline=(51, 65, 85), width=1)
    draw.text((80, 855), "CORE PRODUCTION GUARANTEES & SPECIFICATION COMPLIANCE", fill=accent_cyan, font=heading_font)
    draw.text((80, 885), "[✓] AGENTLESS SSH: Backend connects via AsyncSSH using server-side private key (no agent on EC2).", fill=text_white, font=body_font)
    draw.text((80, 905), "[✓] ZERO FAKE VALUES: Missing or failed metrics remain null (UI renders '-'). Never displays fake 0.0.", fill=text_white, font=body_font)
    draw.text((80, 925), "[✓] CORRELATED INCIDENTS: Multiple concurrent anomalies form ONE incident. Deduplicated by family key.", fill=text_white, font=body_font)
    draw.text((80, 945), "[✓] RESILIENT AI: 8-node LangGraph runs Groq with 100% deterministic rule fallback if LLM is offline.", fill=text_white, font=body_font)

    # Save
    out_path = Path(__file__).resolve().parent.parent / "docs" / "architecture.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out_path), "PNG")
    print(f"Saved architecture diagram to: {out_path}")


if __name__ == "__main__":
    create_architecture_diagram()
