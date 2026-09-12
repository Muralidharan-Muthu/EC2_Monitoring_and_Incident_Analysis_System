"""
Script to generate docs/architecture.png.
Renders a flow-based architecture diagram with small, distinct blocks from START to END.
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path


def create_flow_architecture_diagram():
    width = 1560
    height = 760
    bg_color = (13, 17, 23)  # Modern dark slate
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Color Palette
    border_subtle = (48, 54, 61)
    border_active = (75, 85, 99)
    card_bg = (22, 27, 34)
    item_bg = (28, 33, 40)
    
    c_green = (34, 197, 94)    # Start / Healthy
    c_blue = (56, 189, 248)    # Ingestion
    c_amber = (245, 158, 11)   # Anomaly Detection
    c_purple = (168, 85, 247)  # Correlation
    c_rose = (244, 63, 94)     # AI Diagnosis
    c_cyan = (6, 182, 212)     # Database
    c_emerald = (16, 185, 129) # End / UI
    
    text_primary = (240, 246, 252)
    text_secondary = (148, 163, 184)
    text_muted = (100, 116, 139)

    # Fonts
    try:
        title_font = ImageFont.truetype("arial.ttf", 24)
        subtitle_font = ImageFont.truetype("arial.ttf", 14)
        tag_font = ImageFont.truetype("arial.ttf", 11)
        card_title_font = ImageFont.truetype("arial.ttf", 16)
        item_font = ImageFont.truetype("arial.ttf", 13)
        desc_font = ImageFont.truetype("arial.ttf", 11)
        arrow_font = ImageFont.truetype("arial.ttf", 11)
    except:
        title_font = ImageFont.load_default()
        subtitle_font = title_font
        tag_font = title_font
        card_title_font = title_font
        item_font = title_font
        desc_font = title_font
        arrow_font = title_font

    # --- Header ---
    draw.text((60, 32), "EC2 Monitoring & Incident Analysis System", fill=text_primary, font=title_font)
    draw.text(
        (60, 64),
        "End-to-End Application Flow Architecture  •  From Remote EC2 Telemetry to AI Root-Cause Remediation",
        fill=text_secondary,
        font=subtitle_font,
    )
    draw.line([(60, 96), (1500, 96)], fill=border_subtle, width=1)

    # Helper: Draw Small Compact Flow Block
    def draw_block(x, y, w, h, step_tag, title, accent_color, bullets, is_terminal=None):
        # Outer Card
        outline_col = accent_color if is_terminal else border_subtle
        draw.rounded_rectangle([x, y, x + w, y + h], radius=8, fill=card_bg, outline=outline_col, width=2 if is_terminal else 1)
        
        # Header banner
        draw.rounded_rectangle([x, y, x + w, y + 42], radius=8, fill=(28, 33, 40))
        draw.rectangle([x, y + 26, x + w, y + 42], fill=(28, 33, 40))
        draw.line([(x, y + 42), (x + w, y + 42)], fill=border_subtle, width=1)
        
        # Accent indicator
        draw.line([(x + 8, y + 2), (x + w - 8, y + 2)], fill=accent_color, width=3)
        
        # Tag badge
        draw.text((x + 12, y + 8), step_tag.upper(), fill=accent_color, font=tag_font)
        # Title
        draw.text((x + 12, y + 22), title, fill=text_primary, font=card_title_font)

        # Bullets
        cur_y = y + 54
        for b in bullets:
            # Bullet dot
            draw.ellipse([x + 14, cur_y + 4, x + 18, cur_y + 8], fill=accent_color)
            draw.text((x + 24, cur_y), b["text"], fill=text_primary, font=item_font)
            if "sub" in b:
                draw.text((x + 24, cur_y + 16), b["sub"], fill=text_muted, font=desc_font)
                cur_y += 34
            else:
                cur_y += 24

    # Helper: Draw Right Arrow
    def draw_right_arrow(x1, x2, y, label=""):
        mid_x = (x1 + x2) // 2
        draw.line([(x1, y), (x2, y)], fill=text_muted, width=2)
        draw.polygon([(x2, y), (x2 - 8, y - 5), (x2 - 8, y + 5)], fill=text_secondary)
        if label:
            draw.text((mid_x - 30, y - 18), label, fill=text_secondary, font=arrow_font)

    # Helper: Draw Left Arrow
    def draw_left_arrow(x1, x2, y, label=""):
        mid_x = (x1 + x2) // 2
        draw.line([(x1, y), (x2, y)], fill=text_muted, width=2)
        draw.polygon([(x2, y), (x2 + 8, y - 5), (x2 + 8, y + 5)], fill=text_secondary)
        if label:
            draw.text((mid_x - 35, y - 18), label, fill=text_secondary, font=arrow_font)

    # Helper: Draw Down Arrow
    def draw_down_arrow(x, y1, y2, label=""):
        mid_y = (y1 + y2) // 2
        draw.line([(x, y1), (x, y2)], fill=text_muted, width=2)
        draw.polygon([(x, y2), (x - 5, y2 - 8), (x + 5, y2 - 8)], fill=text_secondary)
        if label:
            draw.text((x + 12, mid_y - 8), label, fill=c_purple, font=arrow_font)

    # ==================== ROW 1 (Left to Right: Steps 1 -> 4) ====================
    r1_y = 120
    b_w = 280
    b_h = 240
    gap = 80

    # Block 1: Start / Target EC2
    x1 = 60
    draw_block(
        x1, r1_y, b_w, b_h,
        step_tag="START • INFRASTRUCTURE",
        title="1. AWS EC2 Target Host",
        accent_color=c_green,
        bullets=[
            {"text": "Ubuntu 24.04 LTS (AWS EC2)", "sub": "Target monitored cloud host"},
            {"text": "Native Linux Tools", "sub": "mpstat, free, df, /proc, ps"},
            {"text": "Zero-Agent Overhead", "sub": "No background daemons installed"},
        ],
        is_terminal="start",
    )

    # Arrow 1 -> 2
    draw_right_arrow(x1 + b_w, x1 + b_w + gap, r1_y + 110, "SSH :22")

    # Block 2: Ingestion
    x2 = x1 + b_w + gap
    draw_block(
        x2, r1_y, b_w, b_h,
        step_tag="STEP 2 • INGESTION",
        title="2. SSH Ingestion Engine",
        accent_color=c_blue,
        bullets=[
            {"text": "AsyncSSH Session Reuse", "sub": "Low latency ~1.2s connection"},
            {"text": "Resilient Polling (~15s)", "sub": "Independent subtask collectors"},
            {"text": "Strict Null Safety", "sub": "Never masks failures as fake 0%"},
        ],
    )

    # Arrow 2 -> 3
    draw_right_arrow(x2 + b_w, x2 + b_w + gap, r1_y + 110, "Telemetry")

    # Block 3: Anomaly Detection
    x3 = x2 + b_w + gap
    draw_block(
        x3, r1_y, b_w, b_h,
        step_tag="STEP 3 • DETECTION",
        title="3. Anomaly Detector",
        accent_color=c_amber,
        bullets=[
            {"text": "Multi-Tier Thresholds", "sub": "CPU/RAM >90%, Disk >85%"},
            {"text": "Persistence Filter (N=3)", "sub": "Eliminates transient spikes"},
            {"text": "Process Snapshotting", "sub": "Captures top CPU/RAM processes"},
        ],
    )

    # Arrow 3 -> 4
    draw_right_arrow(x3 + b_w, x3 + b_w + gap, r1_y + 110, "Anomalies")

    # Block 4: Incident Correlation
    x4 = x3 + b_w + gap
    draw_block(
        x4, r1_y, b_w, b_h,
        step_tag="STEP 4 • CORRELATION",
        title="4. Correlation Engine",
        accent_color=c_purple,
        bullets=[
            {"text": "5-Min Sliding Window", "sub": "Groups concurrent subsystem spikes"},
            {"text": "Deduplication Key", "sub": "SHA256(hostname + family)"},
            {"text": "Alert Storm Mitigation", "sub": "Single unified incident created"},
        ],
    )

    # ==================== CONNECTOR: Row 1 to Row 2 ====================
    down_x = x4 + b_w // 2
    draw_down_arrow(down_x, r1_y + b_h, 440, "Unified Incident")

    # ==================== ROW 2 (Right to Left: Steps 5 -> 7) ====================
    r2_y = 440

    # Block 5: LangGraph AI (under Block 4)
    x5 = x4
    draw_block(
        x5, r2_y, b_w, b_h,
        step_tag="STEP 5 • AI DIAGNOSIS",
        title="5. LangGraph AI Engine",
        accent_color=c_rose,
        bullets=[
            {"text": "8-Node State Machine", "sub": "Evidence -> Severity -> Root Cause"},
            {"text": "Groq LLM (qwen3.8-27b)", "sub": "Pinpoints culprit (stress-ng-cpu)"},
            {"text": "Actionable Remediation", "sub": "Generates copyable bash commands"},
        ],
    )

    # Arrow 5 -> 6 (flows leftward)
    draw_left_arrow(x5, x3 + b_w, r2_y + 110, "Persist & Log")

    # Block 6: Supabase PostgreSQL (under Block 3)
    x6 = x3
    draw_block(
        x6, r2_y, b_w, b_h,
        step_tag="STEP 6 • PERSISTENCE",
        title="6. Supabase PostgreSQL",
        accent_color=c_cyan,
        bullets=[
            {"text": "Time-Series 'metrics'", "sub": "CPU, Memory, Disk, Load queues"},
            {"text": "Correlated 'incidents'", "sub": "Master incidents & deduplication"},
            {"text": "'incident_analyses' Table", "sub": "AI diagnosis & remediation JSON"},
        ],
    )

    # Arrow 6 -> 7 (flows leftward to Dashboard)
    draw_left_arrow(x6, x2 + b_w, r2_y + 110, "REST API")

    # Block 7: React Dashboard (spans width of Block 1 + Block 2)
    b7_w = b_w * 2 + gap
    x7 = x1
    draw_block(
        x7, r2_y, b7_w, b_h,
        step_tag="END • OPERATOR DASHBOARD",
        title="7. React 18 & Vite Web Application",
        accent_color=c_emerald,
        bullets=[
            {"text": "Real-Time Telemetry Gauges & Spline Trend Charts", "sub": "Live CPU, Memory, Disk, and System Load monitored every 10 seconds"},
            {"text": "Unified Incident Action Center", "sub": "Displays active alerts, severity badges (CRITICAL/HIGH), and culprit process tags"},
            {"text": "1-Click Copyable Remediation Actions", "sub": "Bash commands generated by LangGraph ready to execute for instant incident resolution"},
        ],
        is_terminal="end",
    )

    # Save to docs/architecture.png
    out_dir = Path(__file__).resolve().parent.parent / "docs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "architecture.png"
    img.save(out_path, format="PNG", optimize=True)
    print(f"[SUCCESS] Flow-based architecture diagram generated at: {out_path} ({width}x{height})")


if __name__ == "__main__":
    create_flow_architecture_diagram()
