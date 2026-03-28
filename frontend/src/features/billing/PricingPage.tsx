/**
 * Public Pricing Page — shows all tiers, add-ons, and discounts.
 * No auth required. Links to /signup or /billing based on auth state.
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { useAuth } from "../../contexts/AuthContext";
import { getApiBaseUrl } from "../../lib/runtimeConfig";
import { cn } from "../../lib/utils/cn";

interface TierPlan {
    tier: string;
    price_monthly_cents: number;
    price_annual_cents: number;
    limits: {
        projects: number | null;
        csuite_runs_mo: number | null;
        design_screens_mo: number | null;
        artifact_sets_mo: number | null;
    };
    byok_required: boolean;
}

interface PlansResponse {
    plans: TierPlan[];
    addons: {
        csuite_runs: { pack_size: number; cents: number };
        design_screens: { pack_size: number; cents: number };
    };
    discounts: { byok_percent: number; annual_percent: number };
}

const TIER_META: Record<string, { label: string; icon: string; highlight: boolean; description: string; features: string[] }> = {
    free: {
        label: "Free",
        icon: "bolt",
        highlight: false,
        description: "Perfect for exploring Kith Foundry with your own API keys.",
        features: [
            "1 project",
            "3 C-Suite analyses/mo",
            "5 design screens/mo",
            "BYOK (Bring Your Own Key)",
            "Community support",
        ],
    },
    indie: {
        label: "Indie",
        icon: "star",
        highlight: false,
        description: "For solo founders building their next big thing.",
        features: [
            "5 projects",
            "20 C-Suite analyses/mo",
            "30 design screens/mo",
            "3 artifact sets/mo",
            "Hosted LLM (no API key needed)",
            "Email support",
        ],
    },
    pro: {
        label: "Pro",
        icon: "bolt",
        highlight: true,
        description: "Unlimited productivity for serious product builders.",
        features: [
            "Unlimited projects",
            "100 C-Suite analyses/mo",
            "150 design screens/mo",
            "Unlimited artifacts",
            "Hosted LLM priority access",
            "Priority support",
            "Fly.io sandbox priority",
        ],
    },
    team: {
        label: "Team",
        icon: "group",
        highlight: false,
        description: "Pro for your whole team. 3–10 seats.",
        features: [
            "Everything in Pro",
            "3–10 team seats",
            "Shared workspace",
            "Team API key management",
            "Priority support",
        ],
    },
    enterprise: {
        label: "Enterprise",
        icon: "business",
        highlight: false,
        description: "Custom scale, white-label, and dedicated infrastructure.",
        features: [
            "Custom seat count",
            "Unlimited everything",
            "White-label option",
            "Dedicated Fly sandbox",
            "Custom SLA & support",
            "Invoice billing",
        ],
    },
};

const fmt = (cents: number): string => {
    if (cents === 0) return "Free";
    return `$${Math.floor(cents / 100)}`;
};

const fmtLimit = (val: number | null): string => {
    if (val === null) return "Unlimited";
    if (val === 0) return "BYOK only";
    return String(val);
};

export default function PricingPage() {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [plans, setPlans] = useState<PlansResponse | null>(null);
    const [annual, setAnnual] = useState(false);

    useEffect(() => {
        fetch(`${getApiBaseUrl()}/api/v1/billing/plans`)
            .then(r => r.json())
            .then(setPlans)
            .catch(() => {});
    }, []);

    const handleSelectPlan = (tier: string) => {
        if (!user) {
            navigate("/signup");
            return;
        }
        if (tier === "free") {
            navigate("/app/billing");
            return;
        }
        if (tier === "enterprise") {
            window.open("mailto:hello@forgeoperator.com?subject=Enterprise%20Inquiry", "_blank");
            return;
        }
        navigate(`/billing?checkout=${tier}&annual=${annual}`);
    };

    return (
        <div className="min-h-screen bg-background text-on-surface px-4 py-12">
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <div className="text-center mb-12">
                    <motion.h1
                        initial={{ opacity: 0, y: -20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="text-4xl md:text-5xl font-black uppercase mb-4"
                        style={{ letterSpacing: "-0.05em" }}
                    >
                        Simple, transparent pricing
                    </motion.h1>
                    <p className="text-on-surface/50 font-black uppercase tracking-widest text-xs mb-8">
                        From solo founders to enterprise teams. Bring your own key for a 20% discount.
                    </p>

                    {/* Annual toggle */}
                    <div className="flex items-center justify-center gap-3">
                        <span className="text-on-surface/50 font-black uppercase tracking-widest text-xs">Monthly</span>
                        <button
                            onClick={() => setAnnual(a => !a)}
                            aria-pressed={annual}
                            className={cn(
                                "relative w-12 h-6 rounded-full transition-colors",
                                annual ? "bg-secondary" : "bg-surface-container"
                            )}
                        >
                            <span className={cn(
                                "absolute top-1 w-4 h-4 bg-white rounded-full shadow transition-all",
                                annual ? "left-7" : "left-1"
                            )} />
                        </button>
                        <span className="text-on-surface/50 font-black uppercase tracking-widest text-xs">
                            Annual{" "}
                            <span className="text-success">
                                (save {plans?.discounts.annual_percent ?? 20}%)
                            </span>
                        </span>
                    </div>
                </div>

                {/* Plan cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4 mb-12">
                    {(plans?.plans ?? Object.keys(TIER_META).map(t => ({
                        tier: t,
                        price_monthly_cents: 0,
                        price_annual_cents: 0,
                        limits: { projects: null, csuite_runs_mo: null, design_screens_mo: null, artifact_sets_mo: null },
                        byok_required: false,
                    }))).map((plan, i) => {
                        const meta = TIER_META[plan.tier] ?? TIER_META.free;
                        const price = annual ? plan.price_annual_cents : plan.price_monthly_cents;
                        const isHighlight = meta.highlight;

                        return (
                            <motion.div
                                key={plan.tier}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: i * 0.06 }}
                                className={cn(
                                    "relative flex flex-col rounded-[var(--radius-module)] p-6",
                                    isHighlight
                                        ? "ember-glow border border-primary-container bg-primary-container/10"
                                        : "steel-gradient ghost-border"
                                )}
                            >
                                {isHighlight && (
                                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-secondary text-on-surface text-[0.6rem] font-black uppercase tracking-widest px-3 py-1 rounded-full">
                                        Most Popular
                                    </div>
                                )}

                                <div className="w-10 h-10 rounded-full bg-primary-container flex items-center justify-center mb-4">
                                    <span className="material-symbols-outlined text-on-primary-container text-lg">{meta.icon}</span>
                                </div>

                                <h3 className="text-xl font-black uppercase mb-1" style={{ letterSpacing: "-0.05em" }}>{meta.label}</h3>
                                <p className="text-xs font-black uppercase tracking-widest text-on-surface/40 mb-4">{meta.description}</p>

                                <div className="mb-6">
                                    <span className="text-3xl font-black" style={{ letterSpacing: "-0.05em" }}>
                                        {fmt(price)}
                                    </span>
                                    {price > 0 && (
                                        <span className="text-xs font-black uppercase tracking-widest text-on-surface/40 ml-1">
                                            /{annual ? "yr" : "mo"}
                                        </span>
                                    )}
                                    {plan.byok_required && (
                                        <p className="text-[0.6rem] font-black uppercase tracking-widest text-on-surface/30 mt-1">BYOK required</p>
                                    )}
                                </div>

                                <ul className="space-y-2 flex-1 mb-6">
                                    {meta.features.map(f => (
                                        <li key={f} className="flex items-center gap-2">
                                            <span className="material-symbols-outlined text-success text-base flex-shrink-0">check_circle</span>
                                            <span className="text-xs font-black uppercase tracking-widest text-on-surface/50">{f}</span>
                                        </li>
                                    ))}
                                </ul>

                                {/* Usage limits mini-table */}
                                <div className="rounded-lg p-3 mb-4 bg-surface-container border border-outline-variant/20 space-y-1">
                                    <div className="flex justify-between">
                                        <span className="text-[0.6rem] font-black uppercase tracking-widest text-on-surface/40">Projects</span>
                                        <span className="text-[0.6rem] font-black uppercase tracking-widest text-on-surface">{fmtLimit(plan.limits.projects)}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-[0.6rem] font-black uppercase tracking-widest text-on-surface/40">C-Suite/mo</span>
                                        <span className="text-[0.6rem] font-black uppercase tracking-widest text-on-surface">{fmtLimit(plan.limits.csuite_runs_mo)}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-[0.6rem] font-black uppercase tracking-widest text-on-surface/40">Screens/mo</span>
                                        <span className="text-[0.6rem] font-black uppercase tracking-widest text-on-surface">{fmtLimit(plan.limits.design_screens_mo)}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-[0.6rem] font-black uppercase tracking-widest text-on-surface/40">Artifact sets/mo</span>
                                        <span className="text-[0.6rem] font-black uppercase tracking-widest text-on-surface">{fmtLimit(plan.limits.artifact_sets_mo)}</span>
                                    </div>
                                </div>

                                <button
                                    onClick={() => handleSelectPlan(plan.tier)}
                                    className={cn(
                                        "w-full py-2.5 rounded-full font-black uppercase tracking-widest text-xs flex items-center justify-center gap-1 transition-all hover:opacity-90",
                                        isHighlight
                                            ? "bg-secondary text-on-surface"
                                            : "bg-surface-container border border-outline-variant/20 hover:border-outline-variant/50 text-on-surface"
                                    )}
                                >
                                    {plan.tier === "enterprise" ? "Contact Sales" : plan.tier === "free" ? "Get Started Free" : "Upgrade"}
                                    <span className="material-symbols-outlined text-sm">chevron_right</span>
                                </button>
                            </motion.div>
                        );
                    })}
                </div>

                {/* Add-ons */}
                <div className="mb-12">
                    <h2 className="text-2xl font-black uppercase text-center mb-6" style={{ letterSpacing: "-0.05em" }}>Usage Add-ons</h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl mx-auto">
                        {plans && [
                            { key: "csuite_runs", label: "C-Suite Runs Pack", desc: `+${plans.addons.csuite_runs.pack_size} C-Suite analyses`, cents: plans.addons.csuite_runs.cents },
                            { key: "design_screens", label: "Design Screens Pack", desc: `+${plans.addons.design_screens.pack_size} design screens`, cents: plans.addons.design_screens.cents },
                        ].map(addon => (
                            <div key={addon.key} className="flex items-center gap-4 steel-gradient ghost-border rounded-[var(--radius-module)] p-4">
                                <div className="w-10 h-10 rounded-full bg-primary-container flex items-center justify-center">
                                    <span className="material-symbols-outlined text-on-primary-container text-lg">add_box</span>
                                </div>
                                <div className="flex-1">
                                    <p className="text-xs font-black uppercase tracking-widest text-on-surface">{addon.label}</p>
                                    <p className="text-[0.6rem] font-black uppercase tracking-widest text-on-surface/40 mt-0.5">{addon.desc}</p>
                                </div>
                                <div className="text-right">
                                    <p className="font-black text-on-surface" style={{ letterSpacing: "-0.05em" }}>${Math.floor(addon.cents / 100)}</p>
                                    <p className="text-[0.6rem] font-black uppercase tracking-widest text-on-surface/40">one-time</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Discount callouts */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl mx-auto mb-12">
                    <div className="steel-gradient ghost-border rounded-[var(--radius-module)] p-4">
                        <p className="text-xs font-black uppercase tracking-widest text-on-surface mb-1">BYOK Discount</p>
                        <p className="text-xs font-black uppercase tracking-widest text-on-surface/40">
                            Bring your own API key on any paid plan and get{" "}
                            <span className="text-success">20% off</span>{" "}
                            automatically applied at checkout.
                        </p>
                    </div>
                    <div className="steel-gradient ghost-border rounded-[var(--radius-module)] p-4">
                        <p className="text-xs font-black uppercase tracking-widest text-on-surface mb-1">Annual Savings</p>
                        <p className="text-xs font-black uppercase tracking-widest text-on-surface/40">
                            Switch to annual billing and save{" "}
                            <span className="text-success">20%</span>{" "}
                            on any paid tier. Pay once, build all year.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
