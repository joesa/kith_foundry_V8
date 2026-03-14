/**
 * Billing Management Page — view current subscription, usage, and manage
 * via Stripe Customer Portal.  Requires authentication.
 */
import { useEffect, useState, useCallback } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import {
    CreditCard, Zap, BarChart2, Package, ExternalLink,
    CheckCircle, AlertCircle, Clock, ArrowUpRight,
} from "lucide-react";
import { useTheme } from "../../contexts/ThemeContext";
import { useApiFetch } from "../../hooks/useApiFetch";

interface SubscriptionData {
    tier: string;
    status: string;
    is_annual: boolean;
    seat_count: number;
    byok_discount_applied: boolean;
    current_period_end: string | null;
    limits: {
        projects: number | null;
        csuite_runs_mo: number | null;
        design_screens_mo: number | null;
        artifact_sets_mo: number | null;
    };
    usage: {
        billing_month: string;
        csuite_runs: number;
        design_screens: number;
        artifact_sets: number;
        project_count: number;
    };
    packs: Array<{
        pack_type: string;
        remaining: number;
        pack_size: number;
        purchased_at: string;
    }>;
}

const TIER_LABELS: Record<string, string> = {
    free: "Free",
    indie: "Indie",
    pro: "Pro",
    team: "Team",
    enterprise: "Enterprise",
};

const TIER_COLOR: Record<string, string> = {
    free: "from-slate-500 to-slate-600",
    indie: "from-blue-500 to-indigo-600",
    pro: "from-purple-500 to-violet-600",
    team: "from-emerald-500 to-teal-600",
    enterprise: "from-amber-500 to-orange-600",
};

function UsageBar({ value, max, label }: { value: number; max: number | null; label: string }) {
    const pct = max === null ? 0 : Math.min((value / max) * 100, 100);
    const color = pct > 90 ? "bg-red-500" : pct > 70 ? "bg-amber-500" : "bg-purple-500";

    return (
        <div className="mb-3">
            <div className="flex justify-between text-xs mb-1">
                <span>{label}</span>
                <span className="font-mono">
                    {value}{max !== null ? ` / ${max}` : " / ∞"}
                </span>
            </div>
            {max !== null && (
                <div className="h-1.5 rounded-full bg-white/10">
                    <div
                        className={`h-full rounded-full ${color} transition-all duration-500`}
                        style={{ width: `${pct}%` }}
                    />
                </div>
            )}
        </div>
    );
}

export default function BillingPage() {
    const { theme } = useTheme();
    const apiFetch = useApiFetch();
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();

    const [sub, setSub] = useState<SubscriptionData | null>(null);
    const [loading, setLoading] = useState(true);
    const [portalLoading, setPortalLoading] = useState(false);
    const [packLoading, setPackLoading] = useState<string | null>(null);

    const isDark = theme === "dark";
    const bg = isDark ? "bg-[#0A0A10]" : "bg-[#F8F9FA]";
    const card = isDark ? "bg-[#111118] border-white/10" : "bg-white border-gray-200";
    const text = isDark ? "text-white" : "text-gray-900";
    const textSub = isDark ? "text-gray-400" : "text-gray-500";

    const checkoutStatus = searchParams.get("checkout");
    const packStatus = searchParams.get("pack");

    const fetchSub = useCallback(async () => {
        try {
            const resp = await apiFetch("/api/v1/billing/subscription");
            if (resp.ok) {
                const data = await resp.json();
                setSub(data);
            }
        } catch {}
        finally { setLoading(false); }
    }, [apiFetch]);

    useEffect(() => { fetchSub(); }, [fetchSub]);

    const openPortal = async () => {
        setPortalLoading(true);
        try {
            const resp = await apiFetch("/api/v1/billing/portal", { method: "POST" });
            if (resp.ok) {
                const data = await resp.json();
                window.open(data.portal_url, "_blank");
            } else {
                const err = await resp.json();
                alert(err.detail || "Could not open billing portal.");
            }
        } catch (e) {
            alert("Failed to open billing portal.");
        } finally {
            setPortalLoading(false);
        }
    };

    const purchasePack = async (pack_type: string) => {
        setPackLoading(pack_type);
        try {
            const resp = await apiFetch("/api/v1/billing/pack/checkout", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ pack_type }),
            });
            if (resp.ok) {
                const data = await resp.json();
                window.location.href = data.checkout_url;
            } else {
                const err = await resp.json();
                alert(err.detail || "Could not start pack checkout.");
            }
        } catch {
            alert("Failed to start pack checkout.");
        } finally {
            setPackLoading(null);
        }
    };

    if (loading) {
        return (
            <div className={`min-h-screen ${bg} flex items-center justify-center`}>
                <div className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    const tier = sub?.tier ?? "free";
    const tierColor = TIER_COLOR[tier] ?? TIER_COLOR.free;
    const isPaid = tier !== "free";

    return (
        <div className={`min-h-screen ${bg} ${text} px-4 py-8`}>
            <div className="max-w-4xl mx-auto">

                {/* Status banners */}
                {checkoutStatus === "success" && (
                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="mb-6 flex items-center gap-2 bg-green-500/20 border border-green-500/40 rounded-xl px-4 py-3 text-green-400"
                    >
                        <CheckCircle className="w-5 h-5 flex-shrink-0" />
                        <span>Subscription activated! Your plan has been upgraded.</span>
                    </motion.div>
                )}
                {checkoutStatus === "cancelled" && (
                    <div className="mb-6 flex items-center gap-2 bg-amber-500/20 border border-amber-500/40 rounded-xl px-4 py-3 text-amber-400">
                        <AlertCircle className="w-5 h-5 flex-shrink-0" />
                        <span>Checkout cancelled. Your plan was not changed.</span>
                    </div>
                )}
                {packStatus === "success" && (
                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="mb-6 flex items-center gap-2 bg-blue-500/20 border border-blue-500/40 rounded-xl px-4 py-3 text-blue-400"
                    >
                        <CheckCircle className="w-5 h-5 flex-shrink-0" />
                        <span>Pack purchased! Your extra usage has been added.</span>
                    </motion.div>
                )}

                <div className="flex items-center justify-between mb-8">
                    <h1 className="text-3xl font-bold">Billing & Usage</h1>
                    {isPaid && (
                        <button
                            onClick={openPortal}
                            disabled={portalLoading}
                            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-sm font-medium transition-all"
                        >
                            <CreditCard className="w-4 h-4" />
                            {portalLoading ? "Opening…" : "Manage Subscription"}
                            <ExternalLink className="w-3 h-3" />
                        </button>
                    )}
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-8">
                    {/* Current Plan */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className={`rounded-2xl border ${card} p-6 lg:col-span-1`}
                    >
                        <div className="flex items-center gap-3 mb-4">
                            <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${tierColor} flex items-center justify-center`}>
                                <Zap className="w-5 h-5 text-white" />
                            </div>
                            <div>
                                <p className={`text-xs ${textSub}`}>Current Plan</p>
                                <p className="font-bold text-lg">{TIER_LABELS[tier] ?? tier}</p>
                            </div>
                        </div>

                        <div className={`space-y-2 text-sm mb-4 ${textSub}`}>
                            <div className="flex justify-between">
                                <span>Status</span>
                                <span className={`font-medium ${
                                    sub?.status === "active" || sub?.status === "trialing"
                                        ? "text-green-500"
                                        : "text-red-500"
                                }`}>
                                    {sub?.status ?? "active"}
                                </span>
                            </div>
                            {sub?.is_annual && (
                                <div className="flex justify-between">
                                    <span>Billing</span>
                                    <span className="text-green-500 font-medium">Annual (20% off)</span>
                                </div>
                            )}
                            {sub?.byok_discount_applied && (
                                <div className="flex justify-between">
                                    <span>BYOK Discount</span>
                                    <span className="text-green-500 font-medium">Applied (20% off)</span>
                                </div>
                            )}
                            {sub?.seat_count && sub.seat_count > 1 && (
                                <div className="flex justify-between">
                                    <span>Seats</span>
                                    <span className="font-medium">{sub.seat_count}</span>
                                </div>
                            )}
                            {sub?.current_period_end && (
                                <div className="flex items-center gap-1">
                                    <Clock className="w-3 h-3" />
                                    <span>Renews {new Date(sub.current_period_end).toLocaleDateString()}</span>
                                </div>
                            )}
                        </div>

                        {!isPaid && (
                            <button
                                onClick={() => navigate("/pricing")}
                                className="w-full py-2 rounded-xl bg-purple-600 hover:bg-purple-700 text-white text-sm font-semibold flex items-center justify-center gap-1 transition-all"
                            >
                                Upgrade Plan
                                <ArrowUpRight className="w-4 h-4" />
                            </button>
                        )}
                    </motion.div>

                    {/* Usage */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.05 }}
                        className={`rounded-2xl border ${card} p-6 lg:col-span-2`}
                    >
                        <div className="flex items-center gap-2 mb-4">
                            <BarChart2 className="w-5 h-5 text-purple-500" />
                            <h2 className="font-semibold">Usage — {sub?.usage.billing_month}</h2>
                        </div>
                        <UsageBar
                            label="C-Suite Analyses"
                            value={sub?.usage.csuite_runs ?? 0}
                            max={sub?.limits.csuite_runs_mo ?? null}
                        />
                        <UsageBar
                            label="Design Screens"
                            value={sub?.usage.design_screens ?? 0}
                            max={sub?.limits.design_screens_mo ?? null}
                        />
                        <UsageBar
                            label="Artifact Sets"
                            value={sub?.usage.artifact_sets ?? 0}
                            max={sub?.limits.artifact_sets_mo ?? null}
                        />
                        <UsageBar
                            label="Projects"
                            value={sub?.usage.project_count ?? 0}
                            max={sub?.limits.projects ?? null}
                        />
                        <p className={`text-xs ${textSub} mt-2`}>
                            Reset on the 1st of each month.
                        </p>
                    </motion.div>
                </div>

                {/* Active Packs */}
                {(sub?.packs ?? []).length > 0 && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.1 }}
                        className={`rounded-2xl border ${card} p-6 mb-8`}
                    >
                        <div className="flex items-center gap-2 mb-4">
                            <Package className="w-5 h-5 text-blue-500" />
                            <h2 className="font-semibold">Active Usage Packs</h2>
                        </div>
                        <div className="space-y-2">
                            {sub!.packs.map((p, i) => (
                                <div key={i} className={`flex items-center justify-between p-3 rounded-xl ${isDark ? "bg-white/5" : "bg-gray-50"}`}>
                                    <div>
                                        <p className="text-sm font-medium">
                                            {p.pack_type === "csuite_runs" ? "C-Suite Runs" : "Design Screens"} Pack
                                        </p>
                                        <p className={`text-xs ${textSub}`}>
                                            Purchased {new Date(p.purchased_at).toLocaleDateString()}
                                        </p>
                                    </div>
                                    <div className="text-right">
                                        <p className="font-bold">{p.remaining}</p>
                                        <p className={`text-xs ${textSub}`}>remaining</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </motion.div>
                )}

                {/* Buy Add-on Packs */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.15 }}
                    className={`rounded-2xl border ${card} p-6 mb-8`}
                >
                    <div className="flex items-center gap-2 mb-4">
                        <Package className="w-5 h-5 text-pink-500" />
                        <h2 className="font-semibold">Buy Usage Packs</h2>
                        <span className={`text-xs ${textSub} ml-auto`}>One-time purchase, no expiry</span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {[
                            { type: "csuite_runs", label: "C-Suite Runs", desc: "+25 C-Suite analyses", price: "$9" },
                            { type: "design_screens", label: "Design Screens", desc: "+50 design screens", price: "$9" },
                        ].map(pack => (
                            <div
                                key={pack.type}
                                className={`flex items-center justify-between rounded-xl p-4 border ${isDark ? "border-white/10 hover:border-white/20" : "border-gray-200 hover:border-gray-300"} transition-all`}
                            >
                                <div>
                                    <p className="font-semibold text-sm">{pack.label} Pack</p>
                                    <p className={`text-xs ${textSub}`}>{pack.desc} · {pack.price}</p>
                                </div>
                                <button
                                    onClick={() => purchasePack(pack.type)}
                                    disabled={packLoading === pack.type}
                                    className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm font-semibold rounded-lg transition-all disabled:opacity-50"
                                >
                                    {packLoading === pack.type ? "…" : "Buy"}
                                </button>
                            </div>
                        ))}
                    </div>
                </motion.div>

                {/* Upgrade CTA for free/indie */}
                {(tier === "free" || tier === "indie") && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.2 }}
                        className="rounded-2xl border border-purple-500/30 bg-purple-500/10 p-6 text-center"
                    >
                        <h3 className="text-xl font-bold mb-2">
                            {tier === "free" ? "Unlock unlimited building" : "Go unlimited with Pro"}
                        </h3>
                        <p className={`${textSub} mb-4 text-sm`}>
                            {tier === "free"
                                ? "Upgrade to Indie or Pro and stop hitting limits mid-build."
                                : "Pro gives you unlimited projects, 100 C-Suite runs/mo, and 150 design screens/mo."
                            }
                        </p>
                        <button
                            onClick={() => navigate("/pricing")}
                            className="px-6 py-2.5 bg-purple-600 hover:bg-purple-700 text-white rounded-xl font-semibold text-sm transition-all"
                        >
                            View Plans
                        </button>
                    </motion.div>
                )}
            </div>
        </div>
    );
}
