"""
Generate .docx and .pdf exports from the scale/pricing analysis.
Run with: python docs/_gen_exports.py
"""
import os

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
MD_PATH = os.path.join(OUT_DIR, "kith_foundry_scale_pricing_analysis.md")
DOCX_PATH = os.path.join(OUT_DIR, "kith_foundry_scale_pricing_analysis.docx")
PDF_PATH  = os.path.join(OUT_DIR, "kith_foundry_scale_pricing_analysis.pdf")

TITLE    = "Kith Foundry — Scale, Capacity & Revenue Analysis"
SUBTITLE = "March 12, 2026  |  Prepared by GitHub Copilot (Claude Sonnet 4.6)"

# ── Structured content ─────────────────────────────────────────────────────────
SECTIONS = [
    {
        "heading": "Q1: Is the application able to support and scale to 1M customers per day?",
        "level": 1,
        "body": [
            ("para", "No — not even close. Here is the honest breakdown."),
            ("heading2", "Scale Assessment: 1M Customers/Day"),
            ("para", "1M customers/day ≈ 12 req/sec average, easily 120–600 req/sec at peak (assuming "
                     "10:1 peak ratio and multiple API calls per session)."),
            ("heading2", "Hard Blockers"),
            ("table", {
                "headers": ["Issue", "Current State", "What 1M/day Needs"],
                "rows": [
                    ["Single process", "One uvicorn process, no multi-worker config",
                     "Horizontally scaled workers behind a load balancer"],
                    ["DB connection pool", "pool_size=5, max_overflow=10 → max 15 connections",
                     "pool_size=20, max_overflow=40 + PgBouncer"],
                    ["No caching", "Every request hits Postgres cold",
                     "Redis for hot-path queries (project lists, user lookups)"],
                    ["No rate limiting", "Zero middleware protecting LLM-calling endpoints",
                     "Per-user/IP rate limits on /csuite, /design, /artifacts"],
                    ["In-memory global state", "_workers, _fix_state all in-process",
                     "Must move to Redis — loses all state on any restart"],
                    ["Fly sandbox cold start", "Up to 60s for IP allocation (20 retries × 3s)",
                     "Pre-warming, pooling strategy, or async hand-off"],
                    ["WebSocket per project", "Single-process tracker, no distributed fanout",
                     "Redis pub/sub or a dedicated WS gateway"],
                ],
            }),
            ("heading2", "Compounding Problems at Scale"),
            ("bullets", [
                "C-Suite = 7 parallel LLM calls per request. At 1% of daily users = 70,000 LLM calls/day from that feature alone.",
                "retries=0 on all Inngest jobs. At scale, transient failures become frequent — silent data loss.",
                "PROVIDER_ENCRYPTION_KEY not set = random key per boot. Every restart invalidates all stored API keys.",
                "BRIDGE_SECRET not set = random per boot. Every backend restart disconnects all live sandbox sessions.",
                "No CDN — static frontend assets at 1M users will saturate egress.",
            ]),
            ("heading2", "What Must Change Before 1M/day Is Viable"),
            ("numbered", [
                "Deploy multiple uvicorn workers (--workers 4+ or Gunicorn + uvicorn workers) behind nginx/Caddy.",
                "Add PgBouncer (transaction pooling mode) + set pool_size=20, max_overflow=40, pool_recycle=300.",
                "Redis for session state, global in-memory dicts, and query caching on hot reads.",
                "Set PROVIDER_ENCRYPTION_KEY and BRIDGE_SECRET as stable secrets in deployment environment.",
                "Enable Inngest retries (retries=3 minimum) on all functions.",
                "Rate limiting middleware (slowapi or reverse proxy) on LLM-heavy endpoints.",
                "CDN (Cloudflare, CloudFront) in front of the frontend build.",
                "Fly sandbox pre-warming — queue-based machine creation instead of blocking the request.",
                "Database read replicas for project/idea list queries.",
            ]),
        ],
    },
    {
        "heading": "Q2: How many users and requests per minute can we support today?",
        "level": 1,
        "body": [
            ("heading2", "The Three Binding Constraints"),
            ("para", "1. Sync SQLAlchemy in async def handlers — the worst bottleneck. "
                     "Every db.query() call blocks the asyncio event loop entirely. "
                     "Remote Postgres latency ~10–50ms avg; typical request 3–5 DB calls = "
                     "30–150ms total event loop blocking."),
            ("para", "2. DB connection pool — pool_size=5 (default), max_overflow=10 = max 15 simultaneous connections. "
                     "Only 1 is exercised at a time anyway due to event loop blocking."),
            ("para", "3. Inngest concurrency ceilings — Design=3, C-Suite=5, Artifacts=3. All retries=0."),
            ("heading2", "Requests Per Minute — By Endpoint Type"),
            ("table", {
                "headers": ["Endpoint Type", "Avg Response Time", "Est. Sustained Req/Min"],
                "rows": [
                    ["Simple reads (GET /projects, auth check)", "30–80ms", "750–1,200"],
                    ["Project writes (POST /projects)", "50–150ms", "400–900"],
                    ["C-Suite POST /csuite/{id}/run", "15–60s (LLM async)", "5–10 (Inngest limit=5)"],
                    ["Design generation", "10–30s per mockup", "6–18 (Inngest limit=3–5)"],
                    ["Artifacts generation", "10–20s", "6–15 (Inngest limit=3–5)"],
                    ["Overall mixed workload", "—", "~600–900 req/min realistic peak"],
                ],
            }),
            ("heading2", "Daily Active Users"),
            ("table", {
                "headers": ["Scenario", "Logic", "Est. DAU"],
                "rows": [
                    ["Heavy users (full LLM workflows)",
                     "C-Suite: 5 concurrent × ~3 runs/hr; Design: 3 × ~6 screens/hr → ~33 workflows/hr × 10hr",
                     "~330 full-workflow users/day"],
                    ["Realistic mixed (80% light, 20% heavy)",
                     "~600 req/min steady × 10hr × 60 ÷ 20 req/session",
                     "~3,000–5,000 DAU before degradation"],
                ],
            }),
            ("heading2", "Capacity Summary"),
            ("table", {
                "headers": ["Metric", "Current Capacity"],
                "rows": [
                    ["Peak requests/min (mixed)", "~600–900"],
                    ["Simple reads/min only", "~1,000–1,200"],
                    ["Concurrent active users", "15–30"],
                    ["Concurrent LLM jobs", "11"],
                    ["Sustainable DAU (light)", "~3,000–5,000"],
                    ["Sustainable DAU (full workflows)", "~300–500"],
                ],
            }),
            ("para", "Key insight: Swapping to asyncpg + AsyncSession (async SQLAlchemy) would multiply "
                     "throughput by 5–10× with no infrastructure changes."),
        ],
    },
    {
        "heading": "Q3: What should we charge, and what is the ideal pricing model vs. the market?",
        "level": 1,
        "body": [
            ("heading2", "What Kith Foundry Actually Is"),
            ("para", "This is not just an app builder. It is a full-stack startup acceleration platform — "
                     "a single loop from zero to working prototype:"),
            ("para", "Idea → Validation → C-Suite Advisory → Brand/UI Design → Live Code → Business Docs"),
            ("bullets", [
                "Ideation Engine — questionnaire → 3 curated startup ideas with TAM, CAC/LTV, 90-day launch plan, strategic moat",
                "C-Suite Simulation — 7 parallel AI advisors (CEO, CTO, CFO, CMO, CPO, COO, CDO) with financial modeling, go-to-market, tech architecture",
                "Design Studio — brand-consistent UI mockup generation with locked design tokens",
                "Live Code Sandbox — React/TypeScript app with live preview, per-project Fly.io VM",
                "Artifact Generation — PRD, Executive Brief, Tech Spec, Design System docs",
            ]),
            ("heading2", "Competitive Market Landscape"),
            ("table", {
                "headers": ["Product", "What it does", "Price/mo", "Gap vs Kith"],
                "rows": [
                    ["Lovable", "AI app builder (code gen only)", "$20–$80", "No ideation, no advisory, no strategy"],
                    ["Bolt.new", "AI app builder", "$20", "No ideation, no advisory, no design system"],
                    ["v0 (Vercel)", "UI component generation", "$20–$30", "UI only, no business layer"],
                    ["Cursor", "AI code editor", "$20", "Code only, IDE-based"],
                    ["Tome", "AI pitch deck / narrative", "$16–$25", "No code, no advisory"],
                    ["Builder.ai", "Managed app building (human+AI)", "$499–$2,000+", "Enterprise, human-assisted, slow"],
                ],
            }),
            ("para", "No single product combines all five layers. The closest equivalent bundle = "
                     "Lovable + v0 + a strategy consultant = $40–$80/mo + $150–$500/hr consulting."),
            ("heading2", "Recommended Pricing Tiers"),
            ("table", {
                "headers": ["Tier", "Target", "Price", "Key Limits"],
                "rows": [
                    ["Free", "Hobbyists, evaluation", "$0", "1 project, 3 C-Suite runs/mo, 5 design screens, BYOK only"],
                    ["Indie", "Solo founders, freelancers", "$39/mo", "5 projects, 20 C-Suite runs, 30 design screens, 3 artifact sets"],
                    ["Pro", "Serious founders, product managers", "$89/mo", "Unlimited projects, 100 C-Suite runs, 150 screens, all artifacts"],
                    ["Team", "Startups, agencies (3–10 seats)", "$249/mo", "Everything Pro × team, shared workspace, team API keys"],
                    ["Enterprise", "Studios, VCs, accelerators", "$999+/mo", "Custom seats, white-label mockups, dedicated region, SLA"],
                ],
            }),
            ("heading2", "Ideal Business Model"),
            ("numbered", [
                "Primary revenue: Monthly subscription per tier",
                "Expansion revenue: Extra run packs ($9 for 25 C-Suite runs, $9 for 50 design screens)",
                "BYOK discount path: Users who connect own API keys get 20% off (saves LLM costs)",
                "Annual pre-pay: 20% discount = strong cash flow + churn reduction",
            ]),
            ("heading2", "Unit Economics at Current LLM Costs (~$0.012/1K tokens, Claude Sonnet)"),
            ("table", {
                "headers": ["Action", "LLM Cost"],
                "rows": [
                    ["C-Suite run (~150K tokens, 7 agents)", "~$0.80–1.50"],
                    ["Design screen generation", "~$0.15–0.40"],
                    ["Artifact generation", "~$0.20–0.60"],
                    ["Pro user at 30–40% utilization", "~$25–40/mo LLM cost"],
                    ["Gross margin per Pro user", "~55–72% before hosting"],
                ],
            }),
        ],
    },
    {
        "heading": "Q4: What is the ideal monthly net revenue ballpark?",
        "level": 1,
        "body": [
            ("heading2", "Scenario 1: Early Stage (~6 months post-launch)"),
            ("table", {
                "headers": ["Tier", "Subscribers", "MRR"],
                "rows": [
                    ["Indie $39", "50", "$1,950"],
                    ["Pro $89", "20", "$1,780"],
                    ["Team $249", "5", "$1,245"],
                    ["Enterprise $999", "1", "$999"],
                    ["Gross MRR", "", "$5,974"],
                ],
            }),
            ("table", {
                "headers": ["Cost Item", "Monthly Amount"],
                "rows": [
                    ["LLM (Claude Sonnet, ~30% BYOK offset)", "~$800"],
                    ["Fly.io sandboxes (~75 active projects × $8)", "~$600"],
                    ["Nhost DB + storage", "~$50"],
                    ["Stripe fees (2.9%)", "~$175"],
                    ["Inngest + misc", "~$75"],
                    ["Total costs", "~$1,700"],
                ],
            }),
            ("para", "Net: ~$4,300/mo (~72% margin)"),

            ("heading2", "Scenario 2: Growth (~18 months)"),
            ("table", {
                "headers": ["Tier", "Subscribers", "MRR"],
                "rows": [
                    ["Indie $39", "300", "$11,700"],
                    ["Pro $89", "150", "$13,350"],
                    ["Team $249", "40", "$9,960"],
                    ["Enterprise $1,499 avg", "5", "$7,495"],
                    ["Gross MRR", "", "$42,505"],
                ],
            }),
            ("table", {
                "headers": ["Cost Item", "Monthly Amount"],
                "rows": [
                    ["LLM (~35% BYOK, ~30% utilization)", "~$6,000"],
                    ["Fly.io (~500 projects × $8)", "~$4,000"],
                    ["Nhost Pro", "~$200"],
                    ["Stripe fees", "~$1,250"],
                    ["Inngest + CDN + monitoring", "~$450"],
                    ["Total costs", "~$11,900"],
                ],
            }),
            ("para", "Net: ~$30,600/mo (~72% margin) → ~$367K ARR net"),

            ("heading2", "Scenario 3: Scale (~3 years)"),
            ("table", {
                "headers": ["Tier", "Subscribers", "MRR"],
                "rows": [
                    ["Indie $39", "1,000", "$39,000"],
                    ["Pro $89", "500", "$44,500"],
                    ["Team $249", "150", "$37,350"],
                    ["Enterprise $1,999 avg", "20", "$39,980"],
                    ["Annual prepay uplift", "—", "+$10,000"],
                    ["Gross MRR", "", "~$170,830"],
                ],
            }),
            ("table", {
                "headers": ["Cost Item", "Monthly Amount"],
                "rows": [
                    ["LLM (~40% BYOK, ~25% avg utilization)", "~$18,000"],
                    ["Infrastructure (Fly.io, DB, CDN, monitoring)", "~$18,000"],
                    ["Stripe + payment ops", "~$5,000"],
                    ["Compliance/security tools", "~$2,000"],
                    ["Total costs", "~$43,000"],
                ],
            }),
            ("para", "Net: ~$127,800/mo (~75% margin) → ~$1.53M ARR net"),

            ("heading2", "Net Revenue Milestones Summary"),
            ("table", {
                "headers": ["Stage", "Timeline", "Subscribers", "Net MRR", "Net ARR"],
                "rows": [
                    ["Early", "~6 months", "~76 paying", "~$4,300", "~$51,600"],
                    ["Growth", "~18 months", "~495 paying", "~$30,600", "~$367,200"],
                    ["Scale", "~3 years", "~1,670 paying", "~$127,800", "~$1,533,600"],
                ],
            }),
            ("heading2", "Key Revenue Levers"),
            ("table", {
                "headers": ["Lever", "Impact"],
                "rows": [
                    ["BYOK adoption hits 50%+", "Saves $3–15K/mo in LLM costs at growth/scale"],
                    ["Annual prepay at 20% discount", "30% annual conversion = ~20% effective MRR boost, cash upfront"],
                    ["Usage packs add-on", "+$9 packs at 15% attachment rate adds ~$2–8K/mo at growth"],
                    ["Sandbox sleep-on-idle", "Active time drops 8hr → 2–3hr/day → Fly costs cut by 60%"],
                    ["Enterprise tier at $2,500+", "5 more logos = +$12,500/mo at near-zero marginal cost"],
                ],
            }),
            ("para", "The $1M net ARR milestone requires ~1,700 paying subscribers — roughly when the "
                     "async DB refactor and horizontal scaling become necessary. Conveniently, $1M ARR "
                     "also funds exactly that engineering work."),
        ],
    },
]


# ──────────────────────────────────────────────────────────────────────────────
# DOCX GENERATION
# ──────────────────────────────────────────────────────────────────────────────
def generate_docx():
    from docx import Document
    from docx.shared import Pt, RGBColor, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    doc = Document()

    # Page margins
    for section in doc.sections:
        section.top_margin    = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin   = Inches(1.25)
        section.right_margin  = Inches(1.25)

    # Title
    t = doc.add_heading(TITLE, level=0)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub = doc.add_paragraph(SUBTITLE)
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub.runs[0].font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    doc.add_paragraph()

    def shade_row(row, hex_color="D9E1F2"):
        for cell in row.cells:
            tc = cell._tc
            tcPr = tc.get_or_add_tcPr()
            shd = OxmlElement("w:shd")
            shd.set(qn("w:val"), "clear")
            shd.set(qn("w:color"), "auto")
            shd.set(qn("w:fill"), hex_color)
            tcPr.append(shd)

    def add_table(doc, headers, rows):
        col_count = len(headers)
        tbl = doc.add_table(rows=1, cols=col_count)
        tbl.style = "Table Grid"
        hdr_row = tbl.rows[0]
        shade_row(hdr_row, "2E4057")
        for i, h in enumerate(headers):
            cell = hdr_row.cells[i]
            cell.text = h
            cell.paragraphs[0].runs[0].font.bold  = True
            cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            cell.paragraphs[0].runs[0].font.size  = Pt(9)
        for idx, row_data in enumerate(rows):
            row = tbl.add_row()
            if idx % 2 == 0:
                shade_row(row, "EDF2FF")
            for i, val in enumerate(row_data):
                row.cells[i].text = val
                row.cells[i].paragraphs[0].runs[0].font.size = Pt(9)
        doc.add_paragraph()

    for sec in SECTIONS:
        doc.add_heading(sec["heading"], level=sec["level"])
        for item_type, content in sec["body"]:
            if item_type == "para":
                doc.add_paragraph(content)
            elif item_type == "heading2":
                doc.add_heading(content, level=2)
            elif item_type == "bullets":
                for b in content:
                    doc.add_paragraph(b, style="List Bullet")
            elif item_type == "numbered":
                for b in content:
                    doc.add_paragraph(b, style="List Number")
            elif item_type == "table":
                add_table(doc, content["headers"], content["rows"])

    doc.add_paragraph()
    footer_p = doc.add_paragraph("Analysis based on codebase review of Kith Foundry V8 — March 12, 2026")
    footer_p.runs[0].font.color.rgb = RGBColor(0x88, 0x88, 0x88)
    footer_p.runs[0].font.size = Pt(8)

    doc.save(DOCX_PATH)
    print(f"DOCX saved: {DOCX_PATH}")


# ──────────────────────────────────────────────────────────────────────────────
# PDF GENERATION
# ──────────────────────────────────────────────────────────────────────────────
def generate_pdf():
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    # Replace typographic characters not supported by core Latin-1 fonts
    def _safe(text: str) -> str:
        replacements = {
            "\u2014": "--", "\u2013": "-", "\u2018": "'", "\u2019": "'",
            "\u201c": '"',  "\u201d": '"',  "\u2022": "*", "\u00d7": "x",
            "\u2265": ">=", "\u2264": "<=", "\u2248": "~=", "\u2192": "->",
            "\u2190": "<-", "\u00b1": "+/-", "\u00b2": "^2", "\u00b3": "^3",
            "\u00b0": "deg", "\u2030": "0/00", "\u00e9": "e", "\u00e8": "e",
            "\u00e0": "a",  "\u00e2": "a",   "\u00f4": "o", "\u00fb": "u",
        }
        for ch, rep in replacements.items():
            text = text.replace(ch, rep)
        # Final safety net: drop any remaining non-Latin-1 characters
        return text.encode("latin-1", errors="replace").decode("latin-1")

    class PDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 9)
            self.set_text_color(120, 120, 120)
            self.cell(0, 8, "Kith Foundry -- Scale, Capacity & Revenue Analysis", align="L",
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(1)

        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 8, f"Page {self.page_no()} -- March 12, 2026", align="C")

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(20, 20, 20)
    pdf.add_page()

    # Cover title
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(30, 30, 30)
    pdf.multi_cell(0, 10, _safe(TITLE), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 7, _safe(SUBTITLE), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(6)

    def write_h1(text):
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(30, 60, 120)
        pdf.multi_cell(0, 8, _safe(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)

    def write_h2(text):
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(50, 50, 50)
        pdf.multi_cell(0, 7, _safe(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1)

    def write_para(text):
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(0, 6, _safe(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)

    def write_bullet(text):
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(30, 30, 30)
        pdf.set_x(pdf.get_x() + 6)
        pdf.multi_cell(0, 6, f"* {_safe(text)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def write_numbered(idx, text):
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(30, 30, 30)
        pdf.set_x(pdf.get_x() + 6)
        pdf.multi_cell(0, 6, f"{idx}. {_safe(text)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def write_table(headers, rows):
        usable = pdf.w - pdf.l_margin - pdf.r_margin
        col_w = usable / len(headers)

        # Header row
        pdf.set_fill_color(46, 64, 87)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 8)
        for h in headers:
            pdf.cell(col_w, 7, _safe(h)[:28], border=1, fill=True)
        pdf.ln()

        # Data rows
        pdf.set_font("Helvetica", "", 8)
        for i, row in enumerate(rows):
            if i % 2 == 0:
                pdf.set_fill_color(237, 242, 255)
            else:
                pdf.set_fill_color(255, 255, 255)
            pdf.set_text_color(30, 30, 30)
            for val in row:
                pdf.cell(col_w, 6, _safe(str(val))[:36], border=1, fill=True)
            pdf.ln()
        pdf.ln(3)

    for sec in SECTIONS:
        write_h1(sec["heading"])
        for item_type, content in sec["body"]:
            if item_type == "para":
                write_para(content)
            elif item_type == "heading2":
                write_h2(content)
            elif item_type == "bullets":
                for b in content:
                    write_bullet(b)
                pdf.ln(2)
            elif item_type == "numbered":
                for idx, b in enumerate(content, 1):
                    write_numbered(idx, b)
                pdf.ln(2)
            elif item_type == "table":
                write_table(content["headers"], content["rows"])

    pdf.output(PDF_PATH)
    print(f"PDF  saved: {PDF_PATH}")


if __name__ == "__main__":
    generate_docx()
    generate_pdf()
    print("Done.")
