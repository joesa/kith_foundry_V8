/**
 * Public Pricing Page — shows all tiers, add-ons, and discounts.
 * No auth required. Links to /signup or /billing based on auth state.
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Check, Zap, Star, Users, Building2, ChevronRight, Package } from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";
import { useTheme } from "../../contexts/ThemeContext";
import { getApiBaseUrl } from "../../lib/runtimeConfig";

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

const TIER_META: Record<string, { label: string; icon: React.ComponentType<{ className?: string }>; color: string; highlight: boolean; description: string; features: string[] }> = {
    free: {
        label: "Free",
        icon: Zap,
        color: "from-slate-500 to-slate-600",
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
        icon: Star,
        color: "from-blue-500 to-indigo-600",
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
        icon: Zap,
        color: "from-purple-500 to-violet-600",
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
        icon: Users,
        color: "from-emerald-500 to-teal-600",
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
        icon: Building2,
        color: "from-amber-500 to-orange-600",
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
    const { theme } = useTheme();
    const navigate = useNavigate();
    const [plans, setPlans] = useState<PlansResponse | null>(null);
    const [annual, setAnnual] = useState(false);
    const isDark = theme === "dark";

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
            navigate("/billing");
            return;
        }
        if (tier === "enterprise") {
            window.open("mailto:hello@kithfoundry.com?subject=Enterprise%20Inquiry", "_blank");
            return;
        }
        navigate(`/billing?checkout=${tier}&annual=${annual}`);
    };

    const bg = isDark ? "bg-[#0A0A10]" : "bg-[#F8F9FA]";
    const card = isDark ? "bg-[#111118] border-white/10" : "bg-white border-gray-200";
    const text = isDark ? "text-white" : "text-gray-900";
    const sub = isDark ? "text-gray-400" : "text-gray-500";
    const toggleBg = isDark ? "bg-white/10" : "bg-gray-200";

    return (
        <div className={`min-h-screen ${bg} ${text} px-4 py-12`}>
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <div className="text-center mb-12">
                    <motion.h1
                        initial={{ opacity: 0, y: -20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="text-4xl md:text-5xl font-bold mb-4"
                    >
                        Simple, transparent pricing
                    </motion.h1>
                    <p className={`text-xl ${sub} mb-8`}>
                        From solo founders to enterprise teams. Bring your own key for a 20% discount.
                    </p>

                    {/* Annual toggle */}
                    <div className="flex items-center justify-center gap-3">
                        <span className={sub}>Monthly</span>
                        <button
                            onClick={() => setAnnual(a => !a)}
                            className={`relative w-12 h-6 rounded-full transition-all ${annual ? "bg-purple-600" : toggleBg}`}
                        >
                            <span className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-all ${annual ? "left-7" : "left-1"}`} />
                        </button>
                        <span className={sub}>
                            Annual{" "}
                            <span className="text-green-500 font-semibold">
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
                        const Icon = meta.icon;
                        const price = annual ? plan.price_annual_cents : plan.price_monthly_cents;
                        const isHighlight = meta.highlight;

                        return (
                            <motion.div
                                key={plan.tier}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: i * 0.06 }}
                                className={`
                                    relative flex flex-col rounded-2xl border p-6 ${card}
                                    ${isHighlight ? "ring-2 ring-purple-500 shadow-lg shadow-purple-500/20" : ""}
                                `}
                            >
                                {isHighlight && (
                                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-purple-600 text-white text-xs font-bold px-3 py-1 rounded-full">
                                        Most Popular
                                    </div>
                                )}

                                <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${meta.color} flex items-center justify-center mb-4`}>
                                    <Icon className="w-5 h-5 text-white" />
                                </div>

                                <h3 className="text-xl font-bold mb-1">{meta.label}</h3>
                                <p className={`text-sm ${sub} mb-4`}>{meta.description}</p>

                                <div className="mb-6">
                                    <span className="text-3xl font-bold">
                                        {fmt(price)}
                                    </span>
                                    {price > 0 && (
                                        <span className={`text-sm ${sub} ml-1`}>
                                            /{annual ? "yr" : "mo"}
                                        </span>
                                    )}
                                    {plan.byok_required && (
                                        <p className={`text-xs ${sub} mt-1`}>BYOK required</p>
                                    )}
                                </div>

                                <ul className="space-y-2 flex-1 mb-6">
                                    {meta.features.map(f => (
                                        <li key={f} className="flex items-center gap-2 text-sm">
                                            <Check className="w-4 h-4 text-green-500 flex-shrink-0" />
                                            <span className={sub}>{f}</span>
                                        </li>
                                    ))}
                                </ul>

                                {/* Usage limits mini-table */}
                                <div className={`rounded-lg p-3 mb-4 text-xs space-y-1 ${isDark ? "bg-white/5" : "bg-gray-50"}`}>
                                    <div className="flex justify-between">
                                        <span className={sub}>Projects</span>
                                        <span className="font-medium">{fmtLimit(plan.limits.projects)}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className={sub}>C-Suite/mo</span>
                                        <span className="font-medium">{fmtLimit(plan.limits.csuite_runs_mo)}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className={sub}>Screens/mo</span>
                                        <span className="font-medium">{fmtLimit(plan.limits.design_screens_mo)}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className={sub}>Artifact sets/mo</span>
                                        <span className="font-medium">{fmtLimit(plan.limits.artifact_sets_mo)}</span>
                                    </div>
                                </div>

                                <button
                                    onClick={() => handleSelectPlan(plan.tier)}
                                    className={`
                                        w-full py-2.5 rounded-xl font-semibold text-sm flex items-center justify-center gap-1 transition-all
                                        ${isHighlight
                                            ? "bg-purple-600 hover:bg-purple-700 text-white"
                                            : isDark
                                                ? "bg-white/10 hover:bg-white/20 text-white"
                                                : "bg-gray-900 hover:bg-gray-800 text-white"
                                        }
                                    `}
                                >
                                    {plan.tier === "enterprise" ? "Contact Sales" : plan.tier === "free" ? "Get Started Free" : "Upgrade"}
                                    <ChevronRight className="w-4 h-4" />
                                </button>
                            </motion.div>
                        );
                    })}
                </div>

                {/* Add-ons */}
                <div className="mb-12">
                    <h2 className="text-2xl font-bold text-center mb-6">Usage Add-ons</h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl mx-auto">
                        {plans && [
                            { key: "csuite_runs", label: "C-Suite Runs Pack", desc: `+${plans.addons.csuite_runs.pack_size} C-Suite analyses`, cents: plans.addons.csuite_runs.cents },
                            { key: "design_screens", label: "Design Screens Pack", desc: `+${plans.addons.design_screens.pack_size} design screens`, cents: plans.addons.design_screens.cents },
                        ].map(addon => (
                            <div key={addon.key} className={`flex items-center gap-4 rounded-xl border p-4 ${card}`}>
                                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-pink-500 to-rose-600 flex items-center justify-center">
                                    <Package className="w-5 h-5 text-white" />
                                </div>
                                <div className="flex-1">
                                    <p className="font-semibold text-sm">{addon.label}</p>
                                    <p className={`text-xs ${sub}`}>{addon.desc}</p>
                                </div>
                                <div className="text-right">
                                    <p className="font-bold">${Math.floor(addon.cents / 100)}</p>
                                    <p className={`text-xs ${sub}`}>one-time</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Discount callouts */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl mx-auto mb-12">
                    <div className={`rounded-xl border p-4 ${card}`}>
                        <p className="font-bold mb-1">🔑 BYOK Discount</p>
                        <p className={`text-sm ${sub}`}>
                            Bring your own API key on any paid plan and get{" "}
                            <span className="text-green-500 font-semibold">20% off</span>{" "}
                            automatically applied at checkout.
                        </p>
                    </div>
                    <div className={`rounded-xl border p-4 ${card}`}>
                        <p className="font-bold mb-1">📅 Annual Savings</p>
                        <p className={`text-sm ${sub}`}>
                            Switch to annual billing and save{" "}
                            <span className="text-green-500 font-semibold">20%</span>{" "}
                            on any paid tier. Pay once, build all year.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
