import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { cn } from "../../lib/utils/cn";
import { staggerContainer, cardEntrance, pageTransition } from "../../lib/utils/motion";

const agentFamilies = [
  {
    label: "C-Suite Agents",
    desc: "CEO, CPO, CTO, CDO, CFO, CMO, COO, CISO",
    icon: "groups",
    accentClass: "text-primary",
    bgClass: "bg-primary/10",
  },
  {
    label: "Design Agents",
    desc: "Mode Classifier, UX Architect, Layout Composer",
    icon: "palette",
    accentClass: "text-secondary",
    bgClass: "bg-secondary/10",
  },
  {
    label: "Engineering Agents",
    desc: "Frontend Architect, Code Generator, Patch Validator",
    icon: "terminal",
    accentClass: "text-secondary",
    bgClass: "bg-secondary/10",
  },
  {
    label: "Runtime Agents",
    desc: "Sandbox Provisioner, Policy Agent, Builder",
    icon: "deployed_code",
    accentClass: "text-primary",
    bgClass: "bg-primary/10",
  },
];

const steps = [
  {
    step: "01",
    title: "Design",
    desc: "AI-powered design system generation, mode classification, and layout architecture.",
    icon: "palette",
    accentClass: "text-secondary",
    glowClass: "shadow-[0_0_30px_rgba(100,210,255,0.12)]",
    bgClass: "bg-secondary/10",
  },
  {
    step: "02",
    title: "Build",
    desc: "Multi-agent code generation with patch validation, AST safety, and sandbox builds.",
    icon: "code",
    accentClass: "text-primary",
    glowClass: "shadow-[0_0_30px_rgba(237,103,70,0.12)]",
    bgClass: "bg-primary/10",
  },
  {
    step: "03",
    title: "Deploy",
    desc: "Git integration, automated deployment, and production monitoring.",
    icon: "rocket_launch",
    accentClass: "text-secondary",
    glowClass: "shadow-[0_0_30px_rgba(100,210,255,0.12)]",
    bgClass: "bg-secondary/10",
  },
];

const trustItems = [
  { icon: "lock", label: "AES-256-GCM Encrypted", desc: "All secrets encrypted at rest and in transit" },
  { icon: "shield", label: "Sandboxed Execution", desc: "Every build runs in an isolated runtime container" },
  { icon: "security", label: "No Local Storage", desc: "Credentials never written to client storage" },
  { icon: "verified", label: "Patch Validated", desc: "Every AI code patch verified before apply" },
];

const pricingTiers = [
  {
    name: "Free",
    price: "$0",
    period: "/mo",
    features: ["1 project", "3 C-Suite runs", "5 design screens", "BYOK only"],
    recommended: false,
  },
  {
    name: "Indie",
    price: "$39",
    period: "/mo",
    features: ["5 projects", "20 C-Suite runs", "30 design screens", "3 artifact sets"],
    recommended: false,
  },
  {
    name: "Pro",
    price: "$89",
    period: "/mo",
    features: ["Unlimited projects", "100 C-Suite runs", "150 design screens", "Unlimited artifacts"],
    recommended: true,
  },
  {
    name: "Team",
    price: "$249",
    period: "/mo",
    features: ["Unlimited everything", "100 runs/seat", "150 screens/seat", "Team collaboration"],
    recommended: false,
  },
];

function SectionEyebrow({ children }: { children: React.ReactNode }) {
  return (
    <p className="inline-flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.3em] text-secondary mb-4">
      <span className="w-1 h-1 rounded-full bg-secondary inline-block" />
      {children}
    </p>
  );
}

function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background text-on-surface">
      {/* Atmospheric orbs – fixed so they persist across scroll */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden z-0">
        <div className="absolute top-[-10%] left-[-10%] w-[700px] h-[700px] bg-primary/10 rounded-full blur-[100px] animate-drift" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[600px] h-[600px] bg-secondary/10 rounded-full blur-[80px] animate-drift [animation-delay:-5s]" />
      </div>

      {/* ── NAV ─────────────────────────────────────────────────────── */}
      <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-center border-b border-outline-variant/20 bg-surface/80 backdrop-blur-xl">
        <div className="w-full max-w-7xl flex items-center justify-between px-4 md:px-8 h-14">
          <span className="text-primary font-black text-2xl tracking-tighter uppercase">
            FORGE_OS
          </span>

          <div className="hidden md:flex items-center gap-8">
            {["Agents", "How It Works", "Security", "Pricing"].map((label) => (
              <button
                key={label}
                onClick={() =>
                  document
                    .getElementById(label.toLowerCase().replace(/\s+/g, "-"))
                    ?.scrollIntoView({ behavior: "smooth" })
                }
                className="text-[10px] font-black uppercase tracking-widest text-tertiary hover:text-on-surface transition-colors"
              >
                {label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate("/login")}
              className="text-[10px] font-black uppercase tracking-widest text-tertiary hover:text-on-surface transition-colors px-4 py-2 rounded-full border border-outline-variant/30 hover:border-outline-variant"
            >
              Login
            </button>
            <button
              onClick={() => navigate("/signup")}
              className={cn(
                "px-5 py-2 rounded-full text-[10px] font-black uppercase tracking-widest",
                "bg-primary-container text-on-primary-container",
                "shadow-[0_0_20px_rgba(237,103,70,0.15)] hover:brightness-110 transition-all"
              )}
            >
              Sign Up
            </button>
          </div>
        </div>
      </nav>

      {/* ── HERO ────────────────────────────────────────────────────── */}
      <section className="relative z-10 pt-32 pb-0 px-4 md:px-8 lg:px-24 py-40 md:py-60 flex flex-col items-center justify-center text-center overflow-hidden">
        <motion.div
          variants={pageTransition}
          initial="initial"
          animate="animate"
          className="max-w-7xl mx-auto"
        >
          <p className="text-[10px] font-black uppercase tracking-[0.3em] text-secondary mb-6 inline-flex items-center gap-2">
            <span className="w-1 h-1 rounded-full bg-secondary inline-block" />
            The AI Company That Builds Your Product
          </p>

          <h1
            className={cn(
              "font-black uppercase leading-none tracking-tighter",
              "text-7xl sm:text-[10rem] lg:text-[14rem]",
              "text-transparent bg-clip-text bg-gradient-to-r from-primary via-on-surface to-secondary"
            )}
            style={{ letterSpacing: "-0.05em" }}
          >
            FORGE_OS
          </h1>

          <p className="mt-8 text-lg md:text-xl text-tertiary max-w-2xl mx-auto leading-relaxed">
            A coordinated team of specialized AI agents — from C-Suite strategy to code generation —
            working in concert to design, build, and deploy your product.
          </p>

          <div className="mt-10 flex items-center justify-center gap-4 flex-wrap">
            <button
              onClick={() => navigate("/signup")}
              className={cn(
                "inline-flex items-center gap-2 px-8 py-4 rounded-full font-black uppercase tracking-tighter text-sm",
                "bg-primary-container text-on-primary-container",
                "shadow-[0_0_30px_rgba(237,103,70,0.2)] hover:brightness-110 transition-all"
              )}
            >
              Start Building
              <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
            </button>
            <button
              onClick={() =>
                document.getElementById("how-it-works")?.scrollIntoView({ behavior: "smooth" })
              }
              className="inline-flex items-center gap-2 px-8 py-4 rounded-full font-black uppercase tracking-tighter text-sm border border-outline-variant/40 text-on-surface hover:border-outline-variant transition-all"
            >
              See How It Works
            </button>
          </div>
        </motion.div>
      </section>

      {/* ── AGENT FAMILIES ──────────────────────────────────────────── */}
      <section
        id="agents"
        className="relative z-10 px-4 md:px-8 lg:px-24 py-24 md:py-40 border-t border-outline-variant/20"
      >
        <div className="max-w-7xl mx-auto">
          <motion.div
            className="text-center mb-16"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <SectionEyebrow>Collaborative AI Architecture</SectionEyebrow>
            <h2
              className="font-black uppercase text-3xl md:text-5xl text-on-surface"
              style={{ letterSpacing: "-0.05em" }}
            >
              Not a chatbot.
              <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-secondary">
                An AI company.
              </span>
            </h2>
            <p className="text-tertiary mt-4 max-w-xl mx-auto leading-relaxed">
              Multiple expert systems collaborate on your project — each specialized in their domain,
              from executive strategy to production deployment.
            </p>
          </motion.div>

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
          >
            {agentFamilies.map((family) => (
              <motion.div
                key={family.label}
                variants={cardEntrance}
                className={cn(
                  "steel-gradient ghost-border rounded-[var(--radius-module)] p-6 flex flex-col gap-3"
                )}
              >
                <div className={cn("w-10 h-10 rounded-xl flex items-center justify-center", family.bgClass)}>
                  <span className={cn("material-symbols-outlined text-[20px]", family.accentClass)}>
                    {family.icon}
                  </span>
                </div>
                <h3
                  className="font-black uppercase text-sm text-on-surface"
                  style={{ letterSpacing: "-0.03em" }}
                >
                  {family.label}
                </h3>
                <p className="text-xs text-tertiary leading-relaxed">{family.desc}</p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ── DESIGN → BUILD → DEPLOY ─────────────────────────────────── */}
      <section
        id="how-it-works"
        className="relative z-10 px-4 md:px-8 lg:px-24 py-24 md:py-40 border-t border-outline-variant/20"
      >
        <div className="max-w-7xl mx-auto">
          <motion.div
            className="text-center mb-16"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <SectionEyebrow>The Process</SectionEyebrow>
            <h2
              className="font-black uppercase text-3xl md:text-5xl text-on-surface"
              style={{ letterSpacing: "-0.05em" }}
            >
              Design. Build. Deploy.
            </h2>
          </motion.div>

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="grid grid-cols-1 md:grid-cols-3 gap-8"
          >
            {steps.map((item) => (
              <motion.div
                key={item.step}
                variants={cardEntrance}
                className={cn(
                  "steel-gradient ghost-border rounded-[var(--radius-module)] p-8 text-center flex flex-col items-center gap-4",
                  item.glowClass
                )}
              >
                <p className={cn("text-[10px] font-black uppercase tracking-[0.3em]", item.accentClass)}>
                  Step {item.step}
                </p>
                <div className={cn("w-14 h-14 rounded-2xl flex items-center justify-center", item.bgClass)}>
                  <span className={cn("material-symbols-outlined text-[28px]", item.accentClass)}>
                    {item.icon}
                  </span>
                </div>
                <h3
                  className="font-black uppercase text-xl text-on-surface"
                  style={{ letterSpacing: "-0.05em" }}
                >
                  {item.title}
                </h3>
                <p className="text-sm text-tertiary leading-relaxed">{item.desc}</p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ── SECURITY ────────────────────────────────────────────────── */}
      <section
        id="security"
        className="relative z-10 px-4 md:px-8 lg:px-24 py-24 md:py-40 border-t border-outline-variant/20"
      >
        <div className="max-w-7xl mx-auto">
          <motion.div
            className="text-center mb-16"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <SectionEyebrow>Security First</SectionEyebrow>
            <h2
              className="font-black uppercase text-3xl md:text-5xl text-on-surface"
              style={{ letterSpacing: "-0.05em" }}
            >
              Secure by Default
            </h2>
          </motion.div>

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-4xl mx-auto"
          >
            {trustItems.map((item) => (
              <motion.div
                key={item.label}
                variants={cardEntrance}
                className="steel-gradient ghost-border rounded-[var(--radius-module)] p-6 flex items-start gap-4"
              >
                <div className="w-10 h-10 rounded-xl bg-secondary/10 flex items-center justify-center shrink-0">
                  <span className="material-symbols-outlined text-[20px] text-secondary">
                    {item.icon}
                  </span>
                </div>
                <div>
                  <p
                    className="font-black uppercase text-xs text-on-surface mb-1"
                    style={{ letterSpacing: "-0.02em" }}
                  >
                    {item.label}
                  </p>
                  <p className="text-xs text-tertiary leading-relaxed">{item.desc}</p>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ── PRICING ─────────────────────────────────────────────────── */}
      <section
        id="pricing"
        className="relative z-10 px-4 md:px-8 lg:px-24 py-24 md:py-40 border-t border-outline-variant/20"
      >
        <div className="max-w-5xl mx-auto">
          <motion.div
            className="text-center mb-16"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <SectionEyebrow>Pricing</SectionEyebrow>
            <h2
              className="font-black uppercase text-3xl md:text-5xl text-on-surface"
              style={{ letterSpacing: "-0.05em" }}
            >
              Simple, Transparent Pricing
            </h2>
          </motion.div>

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="grid grid-cols-1 md:grid-cols-2 gap-4"
          >
            {pricingTiers.map((tier) => (
              <motion.div
                key={tier.name}
                variants={cardEntrance}
                className={cn(
                  "steel-gradient ghost-border rounded-[var(--radius-module)] p-8 flex flex-col",
                  tier.recommended &&
                    "border-primary/40 shadow-[0_0_40px_rgba(237,103,70,0.1)]"
                )}
              >
                {tier.recommended && (
                  <p className="text-[10px] font-black uppercase tracking-[0.3em] text-primary mb-3">
                    Recommended
                  </p>
                )}
                <h3
                  className="font-black uppercase text-lg text-on-surface"
                  style={{ letterSpacing: "-0.04em" }}
                >
                  {tier.name}
                </h3>
                <div className="mt-2 mb-6 flex items-baseline gap-1">
                  <span
                    className="text-4xl font-black text-on-surface"
                    style={{ letterSpacing: "-0.05em" }}
                  >
                    {tier.price}
                  </span>
                  <span className="text-xs text-tertiary font-black uppercase tracking-widest">
                    {tier.period}
                  </span>
                </div>
                <ul className="space-y-3 flex-1">
                  {tier.features.map((f) => (
                    <li key={f} className="text-xs text-secondary flex items-center gap-2">
                      <span className="w-1 h-1 rounded-full bg-secondary shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
                <button
                  onClick={() => navigate("/signup")}
                  className={cn(
                    "mt-6 w-full py-3 rounded-full font-black uppercase tracking-tighter text-sm transition-all",
                    tier.recommended
                      ? "bg-primary-container text-on-primary-container shadow-[0_0_20px_rgba(237,103,70,0.15)] hover:brightness-110"
                      : "border border-outline-variant/40 text-on-surface hover:border-outline-variant"
                  )}
                >
                  Get Started
                </button>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ── CTA ─────────────────────────────────────────────────────── */}
      <section className="relative z-10 px-4 md:px-8 lg:px-24 py-24 md:py-40 border-t border-outline-variant/20">
        <motion.div
          className="max-w-3xl mx-auto text-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          <SectionEyebrow>Get Started Today</SectionEyebrow>
          <h2
            className="font-black uppercase text-4xl md:text-6xl text-on-surface mb-6"
            style={{ letterSpacing: "-0.05em" }}
          >
            Ready to Build?
          </h2>
          <p className="text-tertiary mb-10 leading-relaxed max-w-xl mx-auto">
            Your AI company is standing by. Submit an idea and watch specialized agents bring it to life.
          </p>
          <button
            onClick={() => navigate("/signup")}
            className={cn(
              "inline-flex items-center gap-2 px-10 py-4 rounded-full font-black uppercase tracking-tighter text-sm",
              "bg-primary-container text-on-primary-container",
              "shadow-[0_0_40px_rgba(237,103,70,0.25)] hover:brightness-110 transition-all"
            )}
          >
            Start Building Now
            <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
          </button>
        </motion.div>
      </section>

      {/* ── FOOTER ──────────────────────────────────────────────────── */}
      <footer className="relative z-10 border-t border-outline-variant/20 px-4 md:px-8 lg:px-24 py-8">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4 flex-wrap">
          <span className="text-[10px] font-black uppercase tracking-[0.5em] text-tertiary">
            &copy; 2026 Kinetic Monolith Industries
          </span>
          <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.3em] text-secondary">
            <span className="material-symbols-outlined text-[14px]">lock</span>
            AES-256-GCM Encrypted
          </div>
        </div>
      </footer>
    </div>
  );
}

export default LandingPage;
