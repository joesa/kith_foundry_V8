"""
Screen-variant detection, per-variant LLM requirements, and deterministic
fallback HTML generators for the Design Studio mockup pipeline.

Every variant produces a *visually distinct, purpose-specific* HTML document
so that fallback screens never look identical.
"""


# ── Variant detection ────────────────────────────────────────────────────────

def screen_variant(screen_desc: str) -> str:
    """Classify a screen description into a UI-pattern category."""
    lower = (screen_desc or "").lower()

    # Most specific patterns first
    if any(t in lower for t in (
        "login", "log in", "sign in", "sign up", "signup",
        "registration", "register", "authenticate", "authentication",
    )):
        return "auth"

    if any(t in lower for t in (
        "onboarding", "welcome", "getting started", "first run",
        "first-run", "template selection", "walkthrough", "setup wizard",
    )):
        return "onboarding"

    if any(t in lower for t in (
        "setting", "preference", "profile", "account setting",
        "configuration", "notification preference",
    )):
        return "settings"

    if any(t in lower for t in (
        "detail panel", "detail view", "card detail", "slide-in",
        "modal", "inspector", "info panel", "item detail",
    )):
        return "detail"

    if any(t in lower for t in (
        "analytics", "report", "insight", "statistic",
        "data visualization", "metrics",
    )):
        return "analytics"

    if any(t in lower for t in (
        "editor", "builder", "canvas tool", "workspace",
        "compose", "design tool",
    )):
        return "editor"

    if any(t in lower for t in (
        "landing page", "landing", "marketing page", "hero section",
    )):
        return "landing"

    if any(t in lower for t in (
        "thumbnail", "gallery", "browse", "catalog",
        "library", "collection", "all canvases", "saved canvas",
        "grid view", "all items",
    )):
        return "list"

    if any(t in lower for t in (
        "dashboard", "home screen", "main screen", "overview",
    )):
        return "dashboard"

    return "app"


# ── Per-variant LLM requirements ─────────────────────────────────────────────

_REQUIREMENTS: dict[str, str] = {
    "auth": """SCREEN TYPE: Authentication / Login / Sign Up

REQUIRED LAYOUT:
- Split layout: promotional/brand panel (left ~45%) + form panel (right ~55%)
- OR centred single-column card on a gradient background

REQUIRED ELEMENTS:
- Product logo or name at the top
- Email input field with visible label
- Password input field with visible label
- Primary submit button ("Sign In" / "Sign Up" / "Create Account")
- OAuth option button ("Continue with Google")
- Toggle link: "Already have an account? Sign in" or "No account? Create one"
- "Forgot password?" link
- Optional: brief value-prop bullet points in the promo panel

FORBIDDEN – do NOT include:
- Dashboard KPI cards, analytics widgets, data tables
- Sidebar navigation, recent-activity feeds
- Marketing hero sections or pricing tables""",

    "landing": """SCREEN TYPE: Marketing Landing Page

REQUIRED LAYOUT:
- Full-width page with distinct horizontal sections stacked vertically

REQUIRED ELEMENTS:
- Top navigation bar with logo + menu links + CTA button
- Hero section: large headline, subheadline, primary CTA button, optional hero image placeholder
- Feature/benefit grid (3-4 cards in a row)
- Social-proof section (testimonials, logos, or user count)
- Pricing teaser or plan-comparison row
- Footer with links

FORBIDDEN – do NOT include:
- App-style sidebar navigation
- Authenticated user dashboards or settings
- Login/signup forms as the main content""",

    "onboarding": """SCREEN TYPE: Onboarding / Welcome / Setup Wizard

REQUIRED LAYOUT:
- Centred content with a step/progress indicator at the top
- Option cards arranged in a 2- or 3-column grid

REQUIRED ELEMENTS:
- Step/progress indicator showing current step (e.g. "Step 2 of 4")
- Welcome headline specific to the product
- 3+ selectable template or option cards (each with icon, title, short description)
- "Get Started" / "Continue" primary action button
- "Skip" or "Start Blank" secondary action
- Brief instructional copy explaining the choice

FORBIDDEN – do NOT include:
- Sidebar navigation, KPI metrics, analytics charts
- Landing-page-style hero sections
- Login/signup forms""",

    "dashboard": """SCREEN TYPE: User Dashboard / Home

REQUIRED LAYOUT:
- Use a layout that fits the product's workflow and density needs
- Favor intentional hierarchy over a generic KPI-card-grid

REQUIRED ELEMENTS:
- Navigation (sidebar or top nav)
- A data summary area with hierarchy and variation — NOT a uniform row of 4 equal-sized cards
- At least one chart or data visualization (CSS-only bar/line chart using divs)
- An activity feed, log, or secondary data pane
- Quick-action buttons relevant to the product

FORBIDDEN – do NOT include:
- A uniform row of 3-4 identical-sized KPI boxes as the primary layout element
- Login forms, marketing hero sections, onboarding wizards
- Settings form fields or toggle switches as the main content""",

    "settings": """SCREEN TYPE: Settings / Preferences / Profile

REQUIRED LAYOUT:
- App shell: top bar + settings-category sidebar (or tabs) + form area

REQUIRED ELEMENTS:
- Settings-category sidebar or tab bar (General, Notifications, Security, Billing)
- User avatar/photo placeholder with name + email
- Form sections with labelled text inputs
- Toggle switches for on/off preferences (at least 3)
- "Save Changes" primary button + "Cancel" secondary button
- Danger-zone section (Delete Account / Reset Data)

FORBIDDEN – do NOT include:
- KPI cards, chart widgets, marketing hero sections
- Landing-page pricing, onboarding option cards""",

    "detail": """SCREEN TYPE: Detail Panel / Item View / Inspector

REQUIRED LAYOUT:
- Two-column: main content (left ~70%) + metadata sidebar (right ~30%)
- OR full-width with a top header and stacked sections

REQUIRED ELEMENTS:
- Header with item title + back/close button
- Status and priority badges
- Editable fields (title, description, due date, tags/labels)
- Metadata sidebar (Status, Assignee, Due Date, Tags, Created date)
- Activity/comment thread with 3+ entries
- Action buttons (Save, Archive, Delete)

FORBIDDEN – do NOT include:
- KPI dashboards, marketing sections, login forms
- Grid/gallery views, sidebar navigation for app sections""",

    "list": """SCREEN TYPE: List / Grid / Gallery / Browse View

REQUIRED LAYOUT:
- Full-width with toolbar at top + card grid below + pagination at bottom

REQUIRED ELEMENTS:
- Search input + filter/sort controls
- "Create New" / "Add" primary action button
- Grid of 6+ cards with visual thumbnail placeholders, title, subtitle, and date
- Each card should have a unique placeholder icon/monogram and distinct title
- View-toggle control (Grid / List)
- Pagination or "Load More" at bottom

FORBIDDEN – do NOT include:
- Single-item detail views, login forms
- Landing-page heroes, KPI dashboards""",

    "analytics": """SCREEN TYPE: Analytics / Reports / Insights

REQUIRED LAYOUT:
- Use a layout that supports analytical reading and comparison for this product
- Favor hierarchy, grouping, and comparison over a top-row-of-equal-stat-cards pattern

REQUIRED ELEMENTS:
- Date-range selector / filter controls at top
- Key metrics presented with clear hierarchy (could be a big hero number + supporting stats, a horizontal strip, or mixed-size tiles — NOT necessarily 4 equal cards)
- Large chart (CSS-only bar or line using divs, with axis labels and legend)
- Data table with 4+ columns and 5+ rows
- Export / Download action
- Period-comparison label ("vs. previous 30 days")

FORBIDDEN – do NOT include:
- A uniform row of 4 identical stat boxes as the primary hero element
- Login forms, marketing sections, onboarding wizards
- Settings toggles, detail inspector panels""",

    "editor": """SCREEN TYPE: Editor / Builder / Canvas Workspace

REQUIRED LAYOUT:
- Three-panel: left component list + centre canvas + right properties panel
- Toolbar along the top, status bar at the bottom

REQUIRED ELEMENTS:
- Toolbar with action buttons (Save, Undo, Redo, Preview, Text, Shape, Image)
- Left panel: component/element library or layer list (6+ items)
- Centre: large bordered canvas/artboard area with placeholder content blocks
- Right panel: properties inspector (Width, Height, Background, Font, Size fields)
- Status bar (zoom level, coordinates, save status)

FORBIDDEN – do NOT include:
- KPI dashboards, login forms, marketing hero sections
- Settings preferences, analytics tables""",
}


def screen_specific_requirements(screen_desc: str) -> str:
    """Return rich, screen-type-specific prompt instructions for the LLM."""
    variant = screen_variant(screen_desc)
    return _REQUIREMENTS.get(variant, """SCREEN TYPE: Application Screen

REQUIRED ELEMENTS:
- Build layout and controls specific to THIS screen's described functionality
- Include a top header/nav bar with the product name
- Include contextually appropriate interactive elements (forms, lists, cards, buttons)
- The content must clearly represent the screen's stated purpose

FORBIDDEN:
- Do NOT reuse a generic dashboard structure unless this screen IS a dashboard
- Do NOT show KPI metric cards unless the screen explicitly needs them
- Make the UI match what this specific screen is supposed to do""")


# ── Fallback HTML generators ────────────────────────────────────────────────

def _extract_title_subtitle(screen_desc: str) -> tuple[str, str]:
    title = (screen_desc.split("\n", 1)[0].replace("Screen:", "").strip()
             or "Product Screen")
    subtitle = ""
    if "Description:" in screen_desc:
        subtitle = screen_desc.split("Description:", 1)[1].strip()
    return title, subtitle


def fallback_mockup_html(project_name: str, screen_desc: str) -> str:
    """Return a deterministic, visually rich, *screen-type-specific* HTML page."""
    title, subtitle = _extract_title_subtitle(screen_desc)
    variant = screen_variant(screen_desc)
    builder = _BUILDERS.get(variant, _build_app)
    return builder(project_name, title, subtitle)


# ---------------------------------------------------------------------------
# Individual variant builders
# ---------------------------------------------------------------------------

def _build_auth(pname: str, title: str, subtitle: str) -> str:
    action = "Sign Up" if "sign up" in title.lower() else "Sign In"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>{title}</title>
<style>
:root{{--bg:#0a0d1a;--panel:#121832;--border:#2d3a66;--text:#e8eeff;--muted:#9db0de;--primary:#7c5cff;--secondary:#20305a}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:Inter,system-ui,sans-serif;color:var(--text);min-height:100vh;background:radial-gradient(900px 550px at 18% 0%,#253177,transparent 65%),var(--bg);display:grid;place-items:center;padding:24px}}
.shell{{width:min(960px,100%);background:rgba(17,23,42,.76);border:1px solid var(--border);border-radius:20px;display:grid;grid-template-columns:1.1fr .9fr;overflow:hidden}}
.promo{{padding:34px;border-right:1px solid var(--border)}}
.badge{{display:inline-block;padding:4px 10px;font-size:11px;border-radius:999px;background:#1a2953;border:1px solid var(--border);color:#c2d3ff}}
.promo h1{{margin:14px 0 10px;font-size:34px;line-height:1.1}}
.promo p{{margin:0;color:var(--muted);line-height:1.55}}
.points{{margin-top:20px;display:grid;gap:10px;color:#cdd8f8;font-size:14px}}
.form{{padding:34px;display:grid;gap:12px}}
label{{font-size:12px;color:var(--muted)}}
input{{width:100%;height:42px;border-radius:10px;border:1px solid var(--border);background:#0c1228;color:var(--text);padding:0 12px}}
.row{{display:flex;justify-content:space-between;align-items:center;font-size:12px;color:var(--muted)}}
.btn{{height:44px;border-radius:10px;border:1px solid var(--border);background:var(--secondary);color:var(--text);font-weight:600;cursor:pointer}}
.btn.primary{{border:0;background:linear-gradient(90deg,#7c5cff,#5e7bff)}}
.foot{{text-align:center;font-size:12px;color:var(--muted)}}
@media(max-width:860px){{.shell{{grid-template-columns:1fr}}.promo{{border-right:0;border-bottom:1px solid var(--border)}}}}
</style>
</head>
<body>
<main class="shell">
  <section class="promo">
    <div class="badge">{pname}</div>
    <h1>{title}</h1>
    <p>{subtitle or "Authenticate quickly and continue your workflow without interruption."}</p>
    <div class="points">
      <div>&#x2713; Secure email &amp; password authentication</div>
      <div>&#x2713; Google OAuth for faster onboarding</div>
      <div>&#x2713; Session persistence across devices</div>
    </div>
  </section>
  <section class="form">
    <div><label>Email</label><input type="email" placeholder="you@company.com"/></div>
    <div><label>Password</label><input type="password" placeholder="Enter your password"/></div>
    <div class="row"><span><input type="checkbox" style="height:auto;width:auto;vertical-align:middle;margin-right:6px"/>Remember me</span><span>Forgot password?</span></div>
    <button class="btn primary">{action}</button>
    <button class="btn">Continue with Google</button>
    <div class="foot">{"Already have an account? Sign in" if "sign up" in title.lower() else "No account yet? Create one"}</div>
  </section>
</main>
</body>
</html>"""


def _build_landing(pname: str, title: str, subtitle: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>{title}</title>
<style>
:root{{--bg:#080b18;--panel:#111934;--border:#2a3b6b;--text:#ecf0ff;--muted:#9aabd8;--primary:#6f59ff;--accent:#38c993}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:Inter,system-ui,sans-serif;background:radial-gradient(1400px 700px at 75% -15%,#2f2d8a,transparent 62%),var(--bg);color:var(--text)}}
.wrap{{width:min(1120px,100%);margin:0 auto;padding:22px}}
.top{{display:flex;justify-content:space-between;align-items:center}}
.btn{{height:40px;border-radius:10px;border:1px solid var(--border);background:#162349;color:var(--text);padding:0 14px;font-weight:600;cursor:pointer}}
.btn.primary{{border:0;background:linear-gradient(90deg,#6f59ff,#4f85ff)}}
.hero{{display:grid;grid-template-columns:1.2fr .8fr;gap:18px;margin-top:20px}}
.card{{border:1px solid var(--border);border-radius:16px;background:rgba(17,25,52,.78);padding:20px}}
h1{{margin:8px 0 10px;font-size:48px;line-height:1.05}}
p{{margin:0;color:var(--muted);line-height:1.55}}
.cta{{margin-top:20px;display:flex;gap:10px;flex-wrap:wrap}}
.grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:16px}}
.feature h3{{margin:0 0 8px}}
.price{{font-size:32px;font-weight:700;margin:8px 0}}
.quote{{margin-top:16px;border-left:3px solid var(--accent);padding-left:10px;color:#d4e8ff;font-size:14px}}
.logos{{display:flex;gap:24px;margin-top:16px;color:var(--muted);font-size:13px;align-items:center}}
@media(max-width:960px){{h1{{font-size:36px}}.hero,.grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <strong style="font-size:18px">{pname}</strong>
    <nav style="display:flex;gap:18px;color:var(--muted);font-size:14px"><span>Features</span><span>Pricing</span><span>About</span></nav>
    <div style="display:flex;gap:8px"><button class="btn">Log In</button><button class="btn primary">Start Free</button></div>
  </header>
  <section class="hero">
    <article class="card">
      <div style="font-size:12px;color:#b4c5f7">Launch Faster</div>
      <h1>{title}</h1>
      <p>{subtitle or "Ship polished products faster with an all-in-one platform for ideation, design, and deployment."}</p>
      <div class="cta"><button class="btn primary">Get Started Free</button><button class="btn">Book a Demo</button></div>
      <div class="logos"><span>Trusted by:</span><span>Acme Corp</span><span>Globex</span><span>Initech</span><span>1,200+ teams</span></div>
    </article>
    <aside class="card">
      <h3 style="margin:0 0 6px">What users are saying</h3>
      <div class="quote">"Setup took minutes and the conversion uplift was immediate."<br/><span style="font-size:12px;color:var(--muted)">— Sarah K., Product Lead</span></div>
      <div class="quote" style="margin-top:12px">"Finally a tool that bridges design and engineering."<br/><span style="font-size:12px;color:var(--muted)">— Mark T., CTO</span></div>
    </aside>
  </section>
  <section class="grid">
    <article class="card feature"><h3>&#x26A1; Rapid prototyping</h3><p>Go from idea to interactive mockup in minutes, not days.</p></article>
    <article class="card feature"><h3>&#x1F3A8; Design system</h3><p>Maintain visual consistency across every screen automatically.</p></article>
    <article class="card feature"><h3>&#x1F680; One-click deploy</h3><p>Ship to production with zero DevOps configuration.</p></article>
  </section>
  <section class="card" style="margin-top:12px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
    <div><div style="font-size:12px;color:#a8bbe9">Starting at</div><div class="price">$29<span style="font-size:16px;color:var(--muted)">/month</span></div></div>
    <button class="btn primary">Choose Plan</button>
  </section>
</div>
</body>
</html>"""


def _build_onboarding(pname: str, title: str, subtitle: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>{title}</title>
<style>
:root{{--bg:#0a0d1a;--panel:#121832;--border:#2d3a66;--text:#e8eeff;--muted:#9db0de;--primary:#7c5cff}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:Inter,system-ui,sans-serif;color:var(--text);min-height:100vh;background:radial-gradient(900px 550px at 50% 0%,#1a2455,transparent 65%),var(--bg);display:flex;flex-direction:column;align-items:center;padding:40px 24px}}
.steps{{display:flex;gap:8px;margin-bottom:24px}}
.step{{width:40px;height:6px;border-radius:999px;background:var(--border)}}
.step.active{{background:var(--primary)}}
h1{{margin:0 0 8px;font-size:32px}}
.sub{{color:var(--muted);margin-bottom:24px;font-size:15px;text-align:center;max-width:600px}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;width:min(900px,100%);margin-bottom:24px}}
.card{{background:var(--panel);border:2px solid var(--border);border-radius:14px;padding:20px;cursor:pointer;transition:border-color .2s}}
.card:hover{{border-color:var(--primary)}}
.card h3{{margin:0 0 6px;font-size:16px}}
.card p{{margin:0;color:var(--muted);font-size:13px;line-height:1.4}}
.thumb{{height:90px;background:#1a2455;border-radius:8px;margin-bottom:12px;display:grid;place-items:center;color:var(--muted);font-size:28px}}
.btn{{height:44px;border-radius:10px;border:0;padding:0 28px;font-weight:600;font-size:14px;cursor:pointer}}
.btn.primary{{background:linear-gradient(90deg,#7c5cff,#5e7bff);color:#fff}}
.btn.outline{{background:var(--panel);border:1px solid var(--border);color:var(--text)}}
.skip{{color:var(--muted);font-size:13px;margin-top:14px;cursor:pointer}}
@media(max-width:720px){{.grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<div class="steps"><div class="step active"></div><div class="step active"></div><div class="step"></div><div class="step"></div></div>
<h1>{title}</h1>
<p class="sub">{subtitle or "Choose a template to get started quickly, or start from scratch."}</p>
<div class="grid">
  <div class="card"><div class="thumb">&#x1F4CB;</div><h3>Weekly Sprint</h3><p>Kanban-style board with weekly milestones and task tracking.</p></div>
  <div class="card"><div class="thumb">&#x1F4CA;</div><h3>Project Roadmap</h3><p>Timeline view with quarterly goals and team assignments.</p></div>
  <div class="card"><div class="thumb">&#x1F4BC;</div><h3>Client Board</h3><p>Manage freelance clients, invoices, and deliverables in one place.</p></div>
</div>
<div style="display:flex;gap:12px;align-items:center">
  <button class="btn primary">Get Started</button>
  <button class="btn outline">Start Blank</button>
</div>
<div class="skip">Skip for now &#x2192;</div>
</body>
</html>"""


def _build_dashboard(pname: str, title: str, subtitle: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>{title}</title>
<style>
:root{{--bg:#0a0d1a;--panel:#11172a;--border:#2a3557;--text:#e8eeff;--muted:#9aa7ce;--primary:#7c5cff;--green:#38c993}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:Inter,system-ui,sans-serif;background:var(--bg);color:var(--text)}}
.top{{height:56px;border-bottom:1px solid var(--border);background:rgba(9,13,27,.9);display:flex;align-items:center;justify-content:space-between;padding:0 22px}}
.layout{{display:grid;grid-template-columns:220px 1fr;min-height:calc(100vh - 56px)}}
.side{{border-right:1px solid var(--border);padding:16px}}
.nav-item{{padding:10px 12px;border-radius:8px;font-size:14px;color:var(--muted);cursor:pointer;margin-bottom:4px}}
.nav-item.active{{background:#1a2455;color:var(--text)}}
.main{{padding:22px}}
.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:18px}}
.kpi{{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:16px}}
.kpi .label{{font-size:12px;color:var(--muted)}}
.kpi .value{{font-size:28px;font-weight:700;margin:4px 0}}
.kpi .trend{{font-size:12px}}
.trend.up{{color:var(--green)}}
.trend.down{{color:#ff6b6b}}
.chart{{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:18px;margin-bottom:16px;height:200px;display:flex;align-items:flex-end;gap:8px}}
.bar{{background:var(--primary);border-radius:4px 4px 0 0;flex:1;min-width:20px}}
.activity{{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:16px}}
.act-item{{padding:10px 0;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;font-size:14px}}
.act-item:last-child{{border-bottom:0}}
.time{{color:var(--muted);font-size:12px}}
.btn{{border:0;background:linear-gradient(90deg,#7c5cff,#5e7bff);color:#fff;border-radius:8px;padding:8px 16px;font-weight:600;font-size:13px;cursor:pointer}}
@media(max-width:860px){{.layout{{grid-template-columns:1fr}}.kpis{{grid-template-columns:repeat(2,1fr)}}}}
</style>
</head>
<body>
<header class="top"><strong>{pname}</strong><div style="display:flex;gap:10px;align-items:center"><button class="btn">+ New</button><div style="width:32px;height:32px;border-radius:50%;background:var(--primary);display:grid;place-items:center;font-size:13px">U</div></div></header>
<div class="layout">
  <aside class="side">
    <div class="nav-item active">Dashboard</div><div class="nav-item">Projects</div><div class="nav-item">Analytics</div><div class="nav-item">Team</div><div class="nav-item">Settings</div>
  </aside>
  <main class="main">
    <h2 style="margin:0 0 16px">{title}</h2>
    <div class="kpis">
      <div class="kpi"><div class="label">Active Users</div><div class="value">12,480</div><div class="trend up">&#x2191; 12.4% this week</div></div>
      <div class="kpi"><div class="label">Conversion</div><div class="value">8.9%</div><div class="trend up">&#x2191; 1.2% vs last week</div></div>
      <div class="kpi"><div class="label">Revenue</div><div class="value">$42.7k</div><div class="trend up">&#x2191; 8.3% MoM</div></div>
      <div class="kpi"><div class="label">Avg Session</div><div class="value">4m 32s</div><div class="trend down">&#x2193; 0.5%</div></div>
    </div>
    <div class="chart"><div class="bar" style="height:45%"></div><div class="bar" style="height:62%"></div><div class="bar" style="height:38%"></div><div class="bar" style="height:75%"></div><div class="bar" style="height:55%"></div><div class="bar" style="height:88%"></div><div class="bar" style="height:70%"></div></div>
    <div class="activity">
      <h3 style="margin:0 0 10px">Recent Activity</h3>
      <div class="act-item"><span>New task created for onboarding redesign</span><span class="time">2 min ago</span></div>
      <div class="act-item"><span>Team comment on design review thread</span><span class="time">15 min ago</span></div>
      <div class="act-item"><span>Deployment checklist updated</span><span class="time">1 hour ago</span></div>
      <div class="act-item"><span>Analytics report generated for Q1</span><span class="time">3 hours ago</span></div>
    </div>
  </main>
</div>
</body>
</html>"""


def _build_settings(pname: str, title: str, subtitle: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>{title}</title>
<style>
:root{{--bg:#0a0d1a;--panel:#11172a;--border:#2a3557;--text:#e8eeff;--muted:#9aa7ce;--primary:#7c5cff}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:Inter,system-ui,sans-serif;background:var(--bg);color:var(--text)}}
.top{{height:56px;border-bottom:1px solid var(--border);background:rgba(9,13,27,.9);display:flex;align-items:center;padding:0 22px}}
.layout{{display:grid;grid-template-columns:220px 1fr;min-height:calc(100vh - 56px)}}
.side{{border-right:1px solid var(--border);padding:16px}}
.nav-item{{padding:10px 12px;border-radius:8px;font-size:14px;color:var(--muted);cursor:pointer;margin-bottom:4px}}
.nav-item.active{{background:#1a2455;color:var(--text)}}
.main{{padding:22px;max-width:700px}}
.section{{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:16px}}
.section h3{{margin:0 0 16px;font-size:16px}}
.field{{margin-bottom:14px}}
.field label{{display:block;font-size:12px;color:var(--muted);margin-bottom:6px}}
.field input,.field select{{width:100%;height:40px;border-radius:8px;border:1px solid var(--border);background:#0c1228;color:var(--text);padding:0 12px;font-size:14px}}
.toggle-row{{display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid var(--border)}}
.toggle-row:last-child{{border-bottom:0}}
.toggle{{width:44px;height:24px;border-radius:999px;position:relative;cursor:pointer}}
.toggle.off{{background:var(--border)}}
.toggle.on{{background:var(--primary)}}
.toggle::after{{content:'';position:absolute;width:18px;height:18px;background:#fff;border-radius:50%;top:3px;left:3px}}
.toggle.on::after{{left:23px}}
.avatar-row{{display:flex;align-items:center;gap:16px;margin-bottom:16px}}
.avatar{{width:64px;height:64px;border-radius:50%;background:var(--primary);display:grid;place-items:center;font-size:24px}}
.btn{{border:0;border-radius:8px;padding:10px 20px;font-weight:600;font-size:14px;cursor:pointer}}
.btn.primary{{background:linear-gradient(90deg,#7c5cff,#5e7bff);color:#fff}}
.btn.outline{{background:transparent;border:1px solid var(--border);color:var(--text)}}
.btn.danger{{background:transparent;border:1px solid #ff4d6a;color:#ff4d6a}}
.danger-zone{{border-color:#3a1a2a}}
@media(max-width:860px){{.layout{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<header class="top"><strong>{pname}</strong></header>
<div class="layout">
  <aside class="side"><div class="nav-item active">General</div><div class="nav-item">Notifications</div><div class="nav-item">Security</div><div class="nav-item">Billing</div><div class="nav-item">Integrations</div></aside>
  <main class="main">
    <h2 style="margin:0 0 16px">{title}</h2>
    <div class="section">
      <h3>Profile</h3>
      <div class="avatar-row"><div class="avatar">U</div><div><div style="font-weight:600">User Name</div><div style="font-size:13px;color:var(--muted)">user@company.com</div></div></div>
      <div class="field"><label>Display Name</label><input type="text" value="User Name"/></div>
      <div class="field"><label>Email Address</label><input type="email" value="user@company.com"/></div>
    </div>
    <div class="section">
      <h3>Preferences</h3>
      <div class="toggle-row"><div><div style="font-weight:500">Email Notifications</div><div style="font-size:12px;color:var(--muted)">Receive email updates for important events</div></div><div class="toggle on"></div></div>
      <div class="toggle-row"><div><div style="font-weight:500">Dark Mode</div><div style="font-size:12px;color:var(--muted)">Use dark theme across the application</div></div><div class="toggle on"></div></div>
      <div class="toggle-row"><div><div style="font-weight:500">Weekly Digest</div><div style="font-size:12px;color:var(--muted)">Get a summary of activity each week</div></div><div class="toggle off"></div></div>
    </div>
    <div class="section danger-zone">
      <h3 style="color:#ff4d6a">Danger Zone</h3>
      <div style="display:flex;justify-content:space-between;align-items:center"><div><div style="font-weight:500">Delete Account</div><div style="font-size:12px;color:var(--muted)">Permanently remove your data</div></div><button class="btn danger">Delete Account</button></div>
    </div>
    <div style="display:flex;gap:10px"><button class="btn primary">Save Changes</button><button class="btn outline">Cancel</button></div>
  </main>
</div>
</body>
</html>"""


def _build_detail(pname: str, title: str, subtitle: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>{title}</title>
<style>
:root{{--bg:#0a0d1a;--panel:#11172a;--border:#2a3557;--text:#e8eeff;--muted:#9aa7ce;--primary:#7c5cff}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:Inter,system-ui,sans-serif;background:var(--bg);color:var(--text)}}
.top{{height:56px;border-bottom:1px solid var(--border);background:rgba(9,13,27,.9);display:flex;align-items:center;gap:12px;padding:0 22px}}
.back{{background:none;border:1px solid var(--border);color:var(--muted);border-radius:8px;padding:6px 12px;cursor:pointer;font-size:13px}}
.layout{{display:grid;grid-template-columns:1fr 300px;min-height:calc(100vh - 56px)}}
.content{{padding:22px}}
.badge{{display:inline-block;padding:3px 10px;font-size:11px;border-radius:999px;margin-right:8px;font-weight:600}}
.badge.status{{background:#1a3a2a;color:#38c993}}
.badge.priority{{background:#3a2a1a;color:#f5a623}}
.desc{{color:var(--muted);font-size:15px;line-height:1.6;margin:16px 0;padding:16px;background:var(--panel);border-radius:10px;border:1px solid var(--border)}}
.comment{{display:flex;gap:10px;padding:12px 0;border-bottom:1px solid var(--border)}}
.comment:last-child{{border-bottom:0}}
.comment-avatar{{width:32px;height:32px;border-radius:50%;background:var(--primary);display:grid;place-items:center;font-size:12px;flex-shrink:0}}
.comment-meta{{font-size:12px;color:var(--muted);margin-bottom:4px}}
.sidebar{{border-left:1px solid var(--border);padding:22px}}
.meta-group{{margin-bottom:18px}}
.meta-group label{{display:block;font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}}
.meta-group .val{{font-size:14px;padding:8px 12px;background:var(--panel);border:1px solid var(--border);border-radius:8px}}
.actions{{display:flex;flex-direction:column;gap:8px;margin-top:20px}}
.btn{{height:38px;border-radius:8px;font-weight:600;font-size:13px;cursor:pointer}}
.btn.primary{{background:linear-gradient(90deg,#7c5cff,#5e7bff);color:#fff;border:0}}
.btn.outline{{background:transparent;border:1px solid var(--border);color:var(--text)}}
.btn.danger-text{{background:transparent;color:#ff4d6a;border:1px solid #3a1a2a}}
.comment-input{{width:100%;height:36px;border-radius:8px;border:1px solid var(--border);background:#0c1228;color:var(--text);padding:0 12px;margin-top:10px}}
@media(max-width:860px){{.layout{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<header class="top"><button class="back">&#x2190; Back</button><strong>{title}</strong></header>
<div class="layout">
  <main class="content">
    <div><span class="badge status">In Progress</span><span class="badge priority">High Priority</span></div>
    <h1 style="margin:12px 0 0;font-size:26px">{title}</h1>
    <div class="desc">{subtitle or "Detailed view for this item. Edit the title, description, or metadata fields. Changes are saved automatically."}</div>
    <div style="margin-top:20px">
      <h3 style="margin:0 0 10px">Activity</h3>
      <div class="comment"><div class="comment-avatar">A</div><div><div class="comment-meta">Alice &middot; 2 hours ago</div><div>Updated the description and added acceptance criteria.</div></div></div>
      <div class="comment"><div class="comment-avatar">B</div><div><div class="comment-meta">Bob &middot; 5 hours ago</div><div>Moved to In Progress and assigned to design team.</div></div></div>
      <div class="comment"><div class="comment-avatar">C</div><div><div class="comment-meta">Carol &middot; 1 day ago</div><div>Created this item from the sprint planning session.</div></div></div>
      <input class="comment-input" placeholder="Add a comment..."/>
    </div>
  </main>
  <aside class="sidebar">
    <div class="meta-group"><label>Status</label><div class="val">In Progress</div></div>
    <div class="meta-group"><label>Assignee</label><div class="val">Design Team</div></div>
    <div class="meta-group"><label>Due Date</label><div class="val">Mar 15, 2026</div></div>
    <div class="meta-group"><label>Tags</label><div class="val">UI, Design, Sprint-Q1</div></div>
    <div class="meta-group"><label>Created</label><div class="val">Feb 28, 2026</div></div>
    <div class="actions"><button class="btn primary">Save Changes</button><button class="btn outline">Archive</button><button class="btn danger-text">Delete</button></div>
  </aside>
</div>
</body>
</html>"""


def _build_list(pname: str, title: str, subtitle: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>{title}</title>
<style>
:root{{--bg:#0a0d1a;--panel:#11172a;--border:#2a3557;--text:#e8eeff;--muted:#9aa7ce;--primary:#7c5cff}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:Inter,system-ui,sans-serif;background:var(--bg);color:var(--text)}}
.top{{height:56px;border-bottom:1px solid var(--border);background:rgba(9,13,27,.9);display:flex;align-items:center;justify-content:space-between;padding:0 22px}}
.toolbar{{display:flex;align-items:center;gap:10px;padding:16px 22px}}
.search{{flex:1;max-width:400px;height:40px;border-radius:8px;border:1px solid var(--border);background:#0c1228;color:var(--text);padding:0 14px;font-size:14px}}
.filter{{height:40px;border-radius:8px;border:1px solid var(--border);background:var(--panel);color:var(--text);padding:0 14px;font-size:13px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px;padding:0 22px 22px}}
.card{{background:var(--panel);border:1px solid var(--border);border-radius:12px;overflow:hidden;cursor:pointer;transition:border-color .2s}}
.card:hover{{border-color:var(--primary)}}
.thumb{{height:140px;background:linear-gradient(135deg,#1a2455,#162040);display:grid;place-items:center;color:var(--muted);font-size:32px}}
.card-body{{padding:14px}}
.card-body h4{{margin:0 0 4px;font-size:15px}}
.card-body p{{margin:0;font-size:12px;color:var(--muted)}}
.card-footer{{display:flex;justify-content:space-between;padding:0 14px 12px;font-size:12px;color:var(--muted)}}
.btn{{height:40px;border-radius:8px;border:0;font-weight:600;font-size:14px;cursor:pointer;padding:0 18px}}
.btn.primary{{background:linear-gradient(90deg,#7c5cff,#5e7bff);color:#fff}}
.pagination{{display:flex;justify-content:center;gap:6px;padding:16px}}
.page{{width:36px;height:36px;border-radius:8px;border:1px solid var(--border);background:var(--panel);color:var(--text);display:grid;place-items:center;font-size:13px;cursor:pointer}}
.page.active{{background:var(--primary);border-color:var(--primary)}}
@media(max-width:640px){{.grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<header class="top"><strong>{pname}</strong><button class="btn primary">+ Create New</button></header>
<div class="toolbar">
  <input class="search" placeholder="Search items..."/>
  <select class="filter"><option>All Types</option><option>Recent</option><option>Favorites</option></select>
  <select class="filter"><option>Sort: Newest</option><option>Sort: Oldest</option><option>Sort: Name</option></select>
</div>
<div class="grid">
  <div class="card"><div class="thumb">&#x1F4CB;</div><div class="card-body"><h4>Weekly Sprint Board</h4><p>Kanban board with task tracking</p></div><div class="card-footer"><span>Updated 2h ago</span><span>12 items</span></div></div>
  <div class="card"><div class="thumb">&#x1F4CA;</div><div class="card-body"><h4>Q1 Roadmap</h4><p>Product roadmap and milestones</p></div><div class="card-footer"><span>Updated 1d ago</span><span>8 items</span></div></div>
  <div class="card"><div class="thumb">&#x1F3A8;</div><div class="card-body"><h4>Design System</h4><p>Components and style guidelines</p></div><div class="card-footer"><span>Updated 3d ago</span><span>24 items</span></div></div>
  <div class="card"><div class="thumb">&#x1F4BC;</div><div class="card-body"><h4>Client Projects</h4><p>Active client deliverables</p></div><div class="card-footer"><span>Updated 5d ago</span><span>6 items</span></div></div>
  <div class="card"><div class="thumb">&#x1F4DD;</div><div class="card-body"><h4>Meeting Notes</h4><p>Team meeting summaries</p></div><div class="card-footer"><span>Updated 1w ago</span><span>15 items</span></div></div>
  <div class="card"><div class="thumb">&#x1F680;</div><div class="card-body"><h4>Launch Checklist</h4><p>Pre-launch verification steps</p></div><div class="card-footer"><span>Updated 2w ago</span><span>20 items</span></div></div>
</div>
<div class="pagination"><div class="page active">1</div><div class="page">2</div><div class="page">3</div><div class="page">&#x2192;</div></div>
</body>
</html>"""


def _build_analytics(pname: str, title: str, subtitle: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>{title}</title>
<style>
:root{{--bg:#0a0d1a;--panel:#11172a;--border:#2a3557;--text:#e8eeff;--muted:#9aa7ce;--primary:#7c5cff;--green:#38c993}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:Inter,system-ui,sans-serif;background:var(--bg);color:var(--text)}}
.top{{height:56px;border-bottom:1px solid var(--border);background:rgba(9,13,27,.9);display:flex;align-items:center;justify-content:space-between;padding:0 22px}}
.main{{padding:22px}}
.filters{{display:flex;gap:10px;margin-bottom:18px;flex-wrap:wrap}}
.filter{{height:38px;border-radius:8px;border:1px solid var(--border);background:var(--panel);color:var(--text);padding:0 14px;font-size:13px}}
.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:18px}}
.stat{{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:16px}}
.stat .label{{font-size:12px;color:var(--muted)}}
.stat .value{{font-size:24px;font-weight:700;margin:4px 0}}
.chart-area{{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:18px;margin-bottom:18px}}
.chart-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}}
.chart{{height:180px;display:flex;align-items:flex-end;gap:6px;border-bottom:1px solid var(--border);padding-bottom:8px}}
.bar-group{{flex:1;display:flex;gap:3px;align-items:flex-end}}
.bar{{flex:1;border-radius:3px 3px 0 0;min-width:8px}}
.bar.a{{background:var(--primary)}}
.bar.b{{background:rgba(124,92,255,.3)}}
.table-area{{background:var(--panel);border:1px solid var(--border);border-radius:12px;overflow:hidden}}
table{{width:100%;border-collapse:collapse;font-size:14px}}
th{{text-align:left;padding:12px 16px;font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid var(--border)}}
td{{padding:10px 16px;border-bottom:1px solid var(--border)}}
tr:last-child td{{border-bottom:0}}
.btn{{height:38px;border-radius:8px;border:1px solid var(--border);background:var(--panel);color:var(--text);padding:0 14px;font-weight:600;font-size:13px;cursor:pointer}}
@media(max-width:860px){{.stats{{grid-template-columns:repeat(2,1fr)}}}}
</style>
</head>
<body>
<header class="top"><strong>{pname} &mdash; Analytics</strong><button class="btn">&#x2193; Export CSV</button></header>
<main class="main">
  <div class="filters">
    <select class="filter"><option>Last 30 Days</option><option>Last 7 Days</option><option>Last 90 Days</option></select>
    <select class="filter"><option>All Channels</option><option>Organic</option><option>Paid</option></select>
    <div style="flex:1"></div>
    <span style="color:var(--muted);font-size:13px;align-self:center">Compared to previous period</span>
  </div>
  <div class="stats">
    <div class="stat"><div class="label">Total Visitors</div><div class="value">48,291</div><div style="font-size:12px;color:var(--green)">&#x2191; 14.2%</div></div>
    <div class="stat"><div class="label">Page Views</div><div class="value">142,803</div><div style="font-size:12px;color:var(--green)">&#x2191; 8.7%</div></div>
    <div class="stat"><div class="label">Bounce Rate</div><div class="value">32.1%</div><div style="font-size:12px;color:#ff6b6b">&#x2191; 2.3%</div></div>
    <div class="stat"><div class="label">Avg Duration</div><div class="value">3m 45s</div><div style="font-size:12px;color:var(--green)">&#x2191; 12s</div></div>
  </div>
  <div class="chart-area">
    <div class="chart-header"><h3 style="margin:0">Traffic Overview</h3><div style="display:flex;gap:14px;font-size:12px"><span style="color:var(--primary)">&#x25CF; Current</span><span style="color:rgba(124,92,255,.4)">&#x25CF; Previous</span></div></div>
    <div class="chart">
      <div class="bar-group"><div class="bar a" style="height:45%"></div><div class="bar b" style="height:35%"></div></div>
      <div class="bar-group"><div class="bar a" style="height:62%"></div><div class="bar b" style="height:50%"></div></div>
      <div class="bar-group"><div class="bar a" style="height:55%"></div><div class="bar b" style="height:48%"></div></div>
      <div class="bar-group"><div class="bar a" style="height:78%"></div><div class="bar b" style="height:60%"></div></div>
      <div class="bar-group"><div class="bar a" style="height:88%"></div><div class="bar b" style="height:65%"></div></div>
      <div class="bar-group"><div class="bar a" style="height:70%"></div><div class="bar b" style="height:72%"></div></div>
      <div class="bar-group"><div class="bar a" style="height:95%"></div><div class="bar b" style="height:68%"></div></div>
    </div>
  </div>
  <div class="table-area">
    <table>
      <thead><tr><th>Page</th><th>Views</th><th>Uniques</th><th>Avg Time</th><th>Bounce</th></tr></thead>
      <tbody>
        <tr><td>/dashboard</td><td>24,180</td><td>12,403</td><td>4m 12s</td><td>18%</td></tr>
        <tr><td>/projects</td><td>18,420</td><td>9,210</td><td>3m 45s</td><td>24%</td></tr>
        <tr><td>/settings</td><td>8,103</td><td>6,802</td><td>2m 30s</td><td>42%</td></tr>
        <tr><td>/analytics</td><td>6,290</td><td>4,115</td><td>5m 08s</td><td>15%</td></tr>
        <tr><td>/onboarding</td><td>4,810</td><td>4,810</td><td>1m 55s</td><td>35%</td></tr>
      </tbody>
    </table>
  </div>
</main>
</body>
</html>"""


def _build_editor(pname: str, title: str, subtitle: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>{title}</title>
<style>
:root{{--bg:#0a0d1a;--panel:#11172a;--border:#2a3557;--text:#e8eeff;--muted:#9aa7ce;--primary:#7c5cff}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:Inter,system-ui,sans-serif;background:var(--bg);color:var(--text);display:flex;flex-direction:column;height:100vh;overflow:hidden}}
.toolbar{{height:48px;border-bottom:1px solid var(--border);background:rgba(9,13,27,.9);display:flex;align-items:center;padding:0 16px;gap:8px}}
.tool-btn{{height:32px;border-radius:6px;border:1px solid var(--border);background:var(--panel);color:var(--text);padding:0 10px;font-size:12px;cursor:pointer;display:flex;align-items:center;gap:4px}}
.tool-btn.primary{{background:var(--primary);border-color:var(--primary)}}
.divider{{width:1px;height:24px;background:var(--border);margin:0 4px}}
.workspace{{flex:1;display:grid;grid-template-columns:220px 1fr 260px;overflow:hidden}}
.left-panel{{border-right:1px solid var(--border);padding:12px;overflow-y:auto}}
.panel-title{{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px}}
.component-item{{padding:8px 10px;border-radius:6px;border:1px solid var(--border);background:var(--panel);margin-bottom:6px;font-size:13px;cursor:grab;display:flex;gap:8px;align-items:center}}
.canvas-wrap{{display:grid;place-items:center;background:#060a14;overflow:auto}}
.canvas{{width:800px;height:500px;background:var(--panel);border:2px dashed var(--border);border-radius:12px;display:grid;grid-template-rows:50px 1fr;position:relative}}
.canvas-header{{border-bottom:1px solid var(--border);padding:0 14px;display:flex;align-items:center;font-size:14px;color:var(--muted)}}
.canvas-body{{display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:16px}}
.canvas-card{{background:#0c1228;border:1px solid var(--border);border-radius:8px;padding:12px}}
.canvas-card h4{{margin:0 0 4px;font-size:13px}}
.canvas-card p{{margin:0;font-size:11px;color:var(--muted)}}
.right-panel{{border-left:1px solid var(--border);padding:12px;overflow-y:auto}}
.prop-group{{margin-bottom:14px}}
.prop-group label{{display:block;font-size:11px;color:var(--muted);margin-bottom:4px}}
.prop-group input,.prop-group select{{width:100%;height:32px;border-radius:6px;border:1px solid var(--border);background:#0c1228;color:var(--text);padding:0 8px;font-size:13px}}
.color-row{{display:flex;gap:6px}}
.color-swatch{{width:32px;height:32px;border-radius:6px;border:1px solid var(--border);cursor:pointer}}
.status-bar{{height:28px;border-top:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;padding:0 16px;font-size:11px;color:var(--muted)}}
</style>
</head>
<body>
<div class="toolbar">
  <strong style="margin-right:12px">{pname}</strong>
  <div class="divider"></div>
  <button class="tool-btn">&#x21A9; Undo</button><button class="tool-btn">&#x21AA; Redo</button>
  <div class="divider"></div>
  <button class="tool-btn">T Text</button><button class="tool-btn">&#x25FB; Shape</button><button class="tool-btn">&#x1F5BC; Image</button>
  <div style="flex:1"></div>
  <button class="tool-btn">Preview</button>
  <button class="tool-btn primary">Save</button>
</div>
<div class="workspace">
  <div class="left-panel">
    <div class="panel-title">Components</div>
    <div class="component-item">&#x1F4DD; Text Block</div>
    <div class="component-item">&#x1F5BC; Image</div>
    <div class="component-item">&#x25FB; Container</div>
    <div class="component-item">&#x1F4CA; Chart</div>
    <div class="component-item">&#x1F4CB; Table</div>
    <div class="component-item">&#x1F518; Button</div>
    <div class="panel-title" style="margin-top:16px">Layers</div>
    <div class="component-item">Header Section</div>
    <div class="component-item">Hero Banner</div>
    <div class="component-item">Content Grid</div>
    <div class="component-item">Footer</div>
  </div>
  <div class="canvas-wrap">
    <div class="canvas">
      <div class="canvas-header">Artboard &mdash; 1440 &#xD7; 900</div>
      <div class="canvas-body">
        <div class="canvas-card"><h4>Hero Section</h4><p>Main headline and call-to-action</p></div>
        <div class="canvas-card"><h4>Feature Grid</h4><p>Three-column feature showcase</p></div>
        <div class="canvas-card"><h4>Testimonials</h4><p>Customer quotes carousel</p></div>
        <div class="canvas-card"><h4>Pricing Table</h4><p>Plan comparison with CTAs</p></div>
      </div>
    </div>
  </div>
  <div class="right-panel">
    <div class="panel-title">Properties</div>
    <div class="prop-group"><label>Width</label><input type="text" value="800px"/></div>
    <div class="prop-group"><label>Height</label><input type="text" value="500px"/></div>
    <div class="prop-group"><label>Background</label><div class="color-row"><div class="color-swatch" style="background:#11172a"></div><div class="color-swatch" style="background:#7c5cff"></div><div class="color-swatch" style="background:#38c993"></div><div class="color-swatch" style="background:#fff"></div></div></div>
    <div class="prop-group"><label>Border Radius</label><input type="text" value="12px"/></div>
    <div class="prop-group"><label>Opacity</label><input type="range" style="height:auto;width:100%"/></div>
    <div class="panel-title" style="margin-top:16px">Typography</div>
    <div class="prop-group"><label>Font</label><select><option>Inter</option><option>Roboto</option><option>Poppins</option></select></div>
    <div class="prop-group"><label>Size</label><input type="text" value="16px"/></div>
  </div>
</div>
<div class="status-bar"><span>Zoom: 100%</span><span>x: 420 y: 280</span><span>All changes saved</span></div>
</body>
</html>"""


def _build_app(pname: str, title: str, subtitle: str) -> str:
    """Generic application screen — improved to reference the screen title contextually."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>{title}</title>
<style>
:root{{--bg:#0a0d1a;--panel:#11172a;--border:#2a3557;--text:#e8eeff;--muted:#9aa7ce;--primary:#7c5cff}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:Inter,system-ui,sans-serif;background:radial-gradient(1200px 700px at 10% -10%,#1a2455,transparent 60%),var(--bg);color:var(--text);min-height:100vh}}
.top{{height:56px;border-bottom:1px solid var(--border);background:rgba(9,13,27,.9);display:flex;align-items:center;justify-content:space-between;padding:0 22px}}
.btn{{height:38px;border:1px solid var(--border);background:var(--panel);color:var(--text);border-radius:8px;padding:0 14px;font-weight:600;font-size:13px;cursor:pointer}}
.btn.primary{{background:linear-gradient(90deg,#7c5cff,#5e7bff);border:0;color:#fff}}
.layout{{display:grid;grid-template-columns:220px 1fr;min-height:calc(100vh - 56px)}}
.side{{border-right:1px solid var(--border);padding:16px}}
.nav{{padding:10px 12px;border-radius:8px;font-size:14px;color:var(--muted);cursor:pointer;margin-bottom:4px}}
.nav.active{{background:#1a2455;color:var(--text)}}
.main{{padding:22px}}
.intro{{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:16px}}
.intro h2{{margin:0 0 8px}}
.intro p{{margin:0;color:var(--muted);line-height:1.6}}
.panels{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:16px}}
.panel{{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:18px}}
.panel h3{{margin:0 0 10px;font-size:15px}}
.item{{padding:8px 0;border-bottom:1px solid var(--border);font-size:14px;color:var(--muted)}}
.item:last-child{{border-bottom:0}}
@media(max-width:860px){{.layout{{grid-template-columns:1fr}}.panels{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<header class="top"><strong>{pname}</strong><div style="display:flex;gap:8px"><button class="btn">Settings</button><button class="btn primary">New Action</button></div></header>
<div class="layout">
  <aside class="side"><div class="nav active">{title}</div><div class="nav">Dashboard</div><div class="nav">Projects</div><div class="nav">Team</div></aside>
  <main class="main">
    <div class="intro"><h2>{title}</h2><p>{subtitle or "This screen provides the core functionality described above. Use the panels below to manage your workflow."}</p></div>
    <div class="panels">
      <div class="panel"><h3>Quick Actions</h3><div class="item">Create new item</div><div class="item">Import from file</div><div class="item">Share with team</div><div class="item">Export data</div></div>
      <div class="panel"><h3>Recent Updates</h3><div class="item">Configuration updated &mdash; 2h ago</div><div class="item">New member joined &mdash; 5h ago</div><div class="item">Report generated &mdash; 1d ago</div><div class="item">Integration synced &mdash; 2d ago</div></div>
    </div>
    <div class="panel" style="background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:18px"><h3>Details</h3><p style="color:var(--muted);font-size:14px;line-height:1.6">Select an item above to view detailed information, or use the quick actions to get started with this feature.</p></div>
  </main>
</div>
</body>
</html>"""


# Variant → builder dispatch
_BUILDERS: dict[str, callable] = {
    "auth": _build_auth,
    "landing": _build_landing,
    "onboarding": _build_onboarding,
    "dashboard": _build_dashboard,
    "settings": _build_settings,
    "detail": _build_detail,
    "list": _build_list,
    "analytics": _build_analytics,
    "editor": _build_editor,
    "app": _build_app,
}
